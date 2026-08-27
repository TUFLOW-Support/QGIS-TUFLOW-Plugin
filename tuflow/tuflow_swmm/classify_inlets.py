"""
classify_inlets.py  (optimized)
------------------
Classifies stormwater inlets as ON GRADE or ON SAG using:
  - Inlet point layer from a GeoPackage
  - DEM (GDAL supported format)
  - Road centerlines from a GeoPackage

Method
------
For each inlet:
  1. Find the nearest road segment.
  2. Project the inlet onto that segment to get its position along the road axis.
  3. Sample DEM elevations at: the inlet, 25 ft upstream, 25 ft downstream.
  4. Classify:
       ON SAG   - inlet elevation is LOWER than BOTH flanking samples
       ON GRADE - inlet elevation is between the two flanking samples
       UNKNOWN  - DEM returned NoData, or inlet is >100 ft from any road

Output
------
  - Output GeoPackage with layers:
      <layer>_classified         : point results
      <layer>_classified_lines   : sample polylines
      2d_bc_<layer>              : SX/CN boundary condition lines
      swmm_iu_<layer>            : updated inlet attributes

"""
from dataclasses import dataclass, field
from pathlib import Path
# import os
import math
# import tempfile
# import warnings

import numpy as np
import geopandas as gpd

from osgeo import gdal
import pyproj
# from osgeo import osr

#import rasterio
#from rasterio.warp import calculate_default_transform, reproject, Resampling
#from rasterio.crs import CRS

from shapely.geometry import Point, LineString
from shapely.ops import substring

from tuflow.tuflow_swmm.swmm_processing_feedback import ScreenProcessingFeedback


# ── data class ────────────────────────────────────────────────────────────────
@dataclass
class InletClassifyResult:
    us_max_elev: float = np.nan
    ds_max_elev: float = np.nan
    min_elev:    float = np.nan
    elev_inlet:  float = np.nan
    label:       str   = "UNKNOWN"
    avg_slope:   float = np.nan
    curve_data:  np.ndarray = field(default_factory=lambda: np.zeros((0,), dtype=float))

@dataclass
class ProcessGPDRessult:
    output_crs: pyproj.CRS | None = None
    gdf_inlets_mod: gpd.GeoDataFrame | None = None
    gdf_bcs: gpd.GeoDataFrame | None = None
    gdf_check_points: gpd.GeoDataFrame | None = None
    gdf_check_xs: gpd.GeoDataFrame | None = None

# ── helpers ───────────────────────────────────────────────────────────────────
def offset_line_through_point(line: LineString, target_point: Point) -> LineString:
    """Offset a LineString so the result passes through target_point."""
    distance_to_line = target_point.distance(line)
    nearest_pt = line.interpolate(line.project(target_point))

    idx = min(
        range(len(line.coords) - 1),
        key=lambda i: Point(nearest_pt).distance(LineString(line.coords[i : i + 2])),
    )
    x1, y1 = line.coords[idx]
    x2, y2 = line.coords[idx + 1]
    px, py = target_point.x, target_point.y

    cross = (x2 - x1) * (py - y1) - (y2 - y1) * (px - x1)
    side  = "left" if cross > 0 else "right"

    offset = line.parallel_offset(distance_to_line, side=side, join_style=2)
    if offset.geom_type == "MultiLineString":
        offset = min(offset.geoms, key=lambda g: g.distance(target_point))
    return offset


# def reproject_dem_if_needed(dem_path: str, inlet_crs: CRS, feedback) -> str:
#     """Reproject DEM to passed in crs if necessary. Returns path to usable file."""
#     with rasterio.open(dem_path) as src:
#         if src.crs and CRS.from_user_input(src.crs) == inlet_crs:
#             feedback.pushInfo("  DEM CRS already in correct projection — no reprojection needed.")
#             return dem_path

#         print(f"  DEM CRS is {src.crs} — reprojecting to {inlet_crs.to_string()} ...")
#         dst_crs = inlet_crs
#         transform, width, height = calculate_default_transform(
#             src.crs, dst_crs, src.width, src.height, *src.bounds
#         )
#         kwargs = src.meta.copy()
#         kwargs.update(crs=dst_crs, transform=transform, width=width, height=height)

#         tmp = tempfile.NamedTemporaryFile(suffix=".tif", delete=False)
#         tmp.close()
#         with rasterio.open(tmp.name, "w", **kwargs) as dst:
#             for i in range(1, src.count + 1):
#                 reproject(
#                     source=rasterio.band(src, i),
#                     destination=rasterio.band(dst, i),
#                     src_transform=src.transform,
#                     src_crs=src.crs,
#                     dst_transform=transform,
#                     dst_crs=dst_crs,
#                     resampling=Resampling.bilinear,
#                 )
#         print(f"  Reprojected DEM saved to: {tmp.name}")
#         return tmp.name

def world_to_pixel(geo_transform, x, y):
    """
    Convert world (map) coordinates to pixel coordinates.
    geo_transform: GDAL GeoTransform tuple
    x, y: World coordinates (e.g., lon, lat in dataset's projection)
    Returns: (pixel_x, pixel_y)
    """
    origin_x = geo_transform[0]
    origin_y = geo_transform[3]
    pixel_width = geo_transform[1]
    pixel_height = geo_transform[5]  # usually negative

    # Calculate pixel coordinates
    pixel_x = int((x - origin_x) / pixel_width)
    pixel_y = int((y - origin_y) / pixel_height)
    return pixel_x, pixel_y

def make_index_wrapper(ds):
    def wrapper(x, y):
        return world_to_pixel(ds.GetGeoTransform(), x, y)
    return wrapper

#rasterio version
#def make_index_wrapper(ds):
#    def wrapper(x, y):
#        return ds.index(x, y)
#    return wrapper

def sample_dem_array(band: np.ndarray, dataset: gdal.Dataset,
                     xs: np.ndarray, ys: np.ndarray) -> np.ndarray:
    """
    Vectorized DEM sampling.  Read the band array ONCE outside this call and
    pass it in; xs/ys are 1-D arrays of coordinates in dataset CRS.
    Returns a float array of the same length; out-of-bounds or nodata -> NaN.
    """
    #rows, cols = dataset.index(xs, ys)
    index_wrapper = make_index_wrapper(dataset)
    vec_index = np.vectorize(index_wrapper, otypes=[int, int])
    rows, cols = vec_index(xs, ys)
    rows = np.asarray(rows, dtype=int)
    cols = np.asarray(cols, dtype=int)

    # h, w = dataset.height, dataset.width
    h, w = band.shape
    valid = (rows >= 0) & (rows < h) & (cols >= 0) & (cols < w)

    result = np.full(len(xs), np.nan, dtype=float)
    if valid.any():
        vals = band[rows[valid], cols[valid]].astype(float)
        result[valid] = vals
    return result


def extract_points_and_elevations(
    band: np.ndarray,
    dataset: gdal.Dataset,
    inlet_pt: Point,
    line: LineString,
    max_offset: float,
    n_points: int,
) -> tuple[np.ndarray, np.ndarray, int]:
    """
    Sample elevations along *line* at regular intervals, both upstream and
    downstream of the projection of inlet_pt.  Returns (pts, elevs, inlet_pos).
    """
    projected_dist = line.project(inlet_pt)
    sample_dist    = max_offset / n_points

    offsets = []
    x = 0.0
    while x < projected_dist - 1e-3:
        offsets.append(x)
        x += sample_dist
    pt_index = len(offsets)          # index of the inlet in the full list
    x = projected_dist
    while x < line.length:
        offsets.append(x)
        x += sample_dist

    if not offsets:
        return np.empty((0, 2)), np.array([]), pt_index

    # Vectorised interpolation along the line
    pts_xy  = np.array([[line.interpolate(o).x, line.interpolate(o).y] for o in offsets])
    elevs   = sample_dem_array(band, dataset, pts_xy[:, 0], pts_xy[:, 1])

    # Drop NaN points (adjusting pt_index for any dropped upstream points)
    nan_mask        = np.isnan(elevs)
    dropped_before  = int(nan_mask[:pt_index].sum())
    pt_index       -= dropped_before

    pts_xy = pts_xy[~nan_mask]
    elevs  = elevs[~nan_mask]

    return pts_xy, elevs, pt_index


def _slope_from_points(distances: np.ndarray, elevs: np.ndarray) -> float:
    """
    Fast linear regression slope (rise/run) using closed-form normal equations.
    Replaces scipy.stats.linregress for small arrays — same result, less overhead.
    """
    n = len(elevs)
    if n < 2:
        return 0.0
    
    sx  = distances.sum()
    sy  = elevs.sum()
    sxy = (distances * elevs).sum()
    sx2 = (distances ** 2).sum()
    denom = n * sx2 - sx * sx
    return float((n * sxy - sx * sy) / denom) if denom != 0.0 else 0.0


def classify(pt_array: np.ndarray, elev_array: np.ndarray, inlet_pos: int, sag_tolerance: float) -> InletClassifyResult:
    result = InletClassifyResult()

    if inlet_pos <= 0 or inlet_pos >= len(elev_array) - 1:
        result.label = "UNKNOWN"
        return result

    result.elev_inlet = elev_array[min(inlet_pos, len(elev_array) - 1)]

    # Find local minimum for curve starting from the inlet_pos
    local_min_l_pos = inlet_pos
    local_min_l = result.elev_inlet

    while local_min_l_pos > 0 and elev_array[local_min_l_pos - 1] < local_min_l:
        local_min_l_pos -= 1
        local_min_l = elev_array[local_min_l_pos]

    local_min_r_pos = inlet_pos
    local_min_r = result.elev_inlet
    while local_min_r_pos < len(elev_array) - 1 and elev_array[local_min_r_pos + 1] < local_min_r:
        local_min_r_pos += 1
        local_min_r = elev_array[local_min_r_pos]
    
    local_min_pos = local_min_r_pos
    local_min = local_min_r
    if local_min_l < local_min_r:
        local_min_pos = local_min_l_pos
        local_min = local_min_l

    # find the maximums upstream and down from the local minimum
    max_idx_us = 0
    if local_min_pos > 0:
        max_idx_us = int(np.argmax(elev_array[:local_min_pos]))
    max_idx_ds = len(elev_array)-1
    if local_min_pos < len(elev_array) - 1:
        max_idx_ds = int(np.argmax(elev_array[local_min_pos + 1:])) + local_min_pos + 1

    result.us_max_elev = elev_array[max_idx_us]
    result.ds_max_elev = elev_array[max_idx_ds]
    result.min_elev    = local_min

    if (
        result.us_max_elev - result.min_elev >= sag_tolerance
        and result.ds_max_elev - result.min_elev >= sag_tolerance
    ):
        result.label = "ON SAG"
    else:
        result.label = "ON GRADE"

    distances = np.hstack([[0.0], np.cumsum(np.linalg.norm(np.diff(pt_array, axis=0), axis=1))])
    result.curve_data = np.vstack([distances, elev_array])

    slope = _slope_from_points(distances, elev_array)
    if slope > 0.0:
        result.us_max_elev, result.ds_max_elev = result.ds_max_elev, result.us_max_elev
        # flip the curve so the higher elevation is always first
        result.curve_data = np.flip(result.curve_data, axis=1)
        new_distances = np.hstack([[0.0], np.cumsum(np.linalg.norm(np.diff(np.flip(pt_array, axis=0), axis=0), axis=1))])
        result.curve_data[0,:] = new_distances[:]

    # offset to put the inlet at x=0 for the cross-section data
    result.curve_data[0,:] -= distances[inlet_pos]
    result.avg_slope = abs(slope) * 100.0

    return result

def write_gpkg_layer(gdf, layer, out_path, feedback):
    gdf.to_file(out_path, layer=layer, driver="GPKG")
    feedback.pushInfo(f"  Saved → {out_path}  (layer: '{layer}')")


def create_xs_gdf(gdf_lines, curve_data, csv_folder, feedback):
    feedback.pushInfo(f'Writing curve data in to: csv_folder')

    csv_path = Path(csv_folder)
    csv_path.mkdir(parents=True, exist_ok=True)

    xs_row = {
        'Source': '',
        'Type': 'XZ',
        'Flags': '',
        'Column_1': 'X',
        'Column_2': 'Z',
        'Column_3': '',
        'Column_4': '',
        'Column_5': '',
        'Column_6': '',
        'Z_Increment': np.nan,
        'Z_Maximum': np.nan,
        'Skew': np.nan,
        'geometry': None
    }
    xs_data = []

    for i, (line_geom, curve) in enumerate(zip(gdf_lines['geometry'], curve_data)):
        if curve is not None:
            csv_filename = csv_path / f"xs_{i+1:04}.csv"
            np.savetxt(csv_filename, curve.T, delimiter=',', header="X,Z", comments="", fmt="%10.5f")
            xs_row['Source'] = f'./csv/xs_{i+1:04}.csv'
        else:
            xs_row['Source'] = None

        xs_row['geometry'] = line_geom
        xs_data.append(xs_row.copy())

    xs_gdf = gpd.GeoDataFrame(xs_data, geometry='geometry', crs=gdf_lines.crs)
    xs_gdf = xs_gdf.dropna(subset=['Source'])

    return xs_gdf


def write_1d_xs_layer(gdf_lines, curve_data, out_path, out_layer, feedback):
    feedback.pushInfo(f'Writing extracted curves in 1d_xs format to: {out_path} >> {out_layer}')

    csv_path = Path(Path(out_path).parent / "csv")
    feedback.pushInfo(f'CSV path: {csv_path}')
    csv_path.mkdir(parents=True, exist_ok=True)

    xs_row = {
        'Source': '',
        'Type': 'XZ',
        'Flags': '',
        'Column_1': 'X',
        'Column_2': 'Z',
        'Column_3': '',
        'Column_4': '',
        'Column_5': '',
        'Column_6': '',
        'Z_Increment': np.nan,
        'Z_Maximum': np.nan,
        'Skew': np.nan,
        'geometry': None
    }
    xs_data = []

    for i, (line_geom, curve) in enumerate(zip(gdf_lines['geometry'], curve_data)):
        csv_filename = csv_path / f"xs_{i+1:04}.csv"
        np.savetxt(csv_filename, curve.T, delimiter=',', header="X,Z", comments="", fmt="%10.5f")

        xs_row['Source'] = f'./csv/xs_{i+1:04}.csv'
        xs_row['geometry'] = line_geom
        xs_data.append(xs_row.copy())

    xs_gdf = gpd.GeoDataFrame(xs_data, geometry='geometry', crs=gdf_lines.crs)
    xs_gdf.to_file(out_path, layer=out_layer)

def process_gdb(
        dem_path: str,
        gdf_inlets: gpd.GeoDataFrame,
        gdf_roads: gpd.GeoDataFrame,
        sample_dist: float,
        max_road: float,
        sag_tolerance: float,
        n_points_extract_each_dir: int,
        sx_line_reverse_distance: float,
        sx_offset: float,
        csv_folder: str,
        feedback = ScreenProcessingFeedback()
) -> ProcessGPDRessult:
    rval = ProcessGPDRessult()

    feedback.pushInfo("\n=== Stormwater Inlet Classifier ===\n")



    # We will work in the DEM projection reprojecting the inlets and road data as needed
    dem = gdal.Open(dem_path)
    if not dem:
        feedback.reportError("ERROR: Unable to load DEM. Make sure the file exists.", True)
        return rval
    dem_crs_wkt = dem.GetProjection()

    # 1. Load inlets
    if gdf_inlets.crs is None:
        feedback.pushWarning("WARNING: Inlet layer has no CRS — assuming same as DEM.")
    else:
        inlet_crs = gdf_inlets.crs
    gdf_inlets = gdf_inlets.to_crs(dem_crs_wkt)
    feedback.pushInfo(f"  {len(gdf_inlets)} inlets.")

    # We will output the data in the inlet crs if it has one otherwise the dem crs
    output_crs = inlet_crs if inlet_crs is not None else dem_crs_wkt

    # 2. Prepare DEM
    #print("\n[2/5] Preparing DEM ...")
    #dem_working = reproject_dem_if_needed(dem_path)
    raster_band = dem.GetRasterBand(1)
    band = raster_band.ReadAsArray().T
    feedback.pushInfo(f'Raster shape: {band.shape}')
    # feedback.pushInfo(f'Raster geo_transform: {dem.GetGeoTransform()}')
    if band is None:
        feedback.reportError("ERROR: Unable to read raster band from DEM.", True)
        return rval
    nd = raster_band.GetNoDataValue()
    band[band==nd] = np.nan   

    # 3. Load roads
    feedback.pushInfo("\nConfiguring road centerlines ...")
    if gdf_roads.crs:
        if inlet_crs is None:
            feedback.pushWarning("WARNING: Roads layer has no CRS - assuming the same as the DEM.")
        else:
            roads = gdf_roads.to_crs(dem_crs_wkt)

    roads = roads.reset_index(drop=True).explode(index_parts=False)
    roads_sindex = roads.sindex
    feedback.pushInfo(f"  {len(roads)} road segments.")

    # 4. Classify each inlet
    feedback.pushInfo("\nClassifying inlets ...")
    results  = []
    lines    = []
    bc_data  = []
    xs_curves = []

    bc_row_template = {
        "Type": "SX", "Flags": "Z", "Name": "",
        "f": np.nan, "D": np.nan, "Td": np.nan,
        "A": np.nan, "B": np.nan, "geometry": None,
    }


    for idx, row in gdf_inlets.iterrows():
        row_results = {
            "inlet_id":        idx,
            "grade_sag":       "UNKNOWN",
            "elev_inlet":   np.nan,
            "elev_up":      np.nan,
            "elev_dn":      np.nan,
            "elev_min":     np.nan,
            "avg_slope":       np.nan,
            "dist_to_road": np.nan,
            "geometry":        None,
        }

        pt = row.geometry
        if pt is None or pt.is_empty:
            results.append(row_results)
            lines.append(None)
            xs_curves.append(None)
            continue
        row_results["geometry"] = pt

        # Nearest road — ask for 1 candidate, flatten safely
        raw = list(roads_sindex.nearest(pt, True, max_road))
        candidate_idx = [i for sub in raw for i in (sub if hasattr(sub, "__iter__") else [sub])]
        candidates = roads.iloc[candidate_idx]
        candidates = candidates.loc[~candidates.index.duplicated(keep='first')]
        if len(candidates) == 0:
            results.append(row_results)
            lines.append(None)
            xs_curves.append(None)
            continue
        dists      = candidates.geometry.distance(pt)
        nearest_i  = dists.idxmin()
        road_seg   = candidates.loc[nearest_i]
        dist    = float(dists[nearest_i])

        row_results["dist_to_road"] = dist

        if dist > max_road:
            results.append(row_results)
            lines.append(None)
            xs_curves.append(None)
            continue

        road_line       = road_seg.geometry
        dist_pt_on_road = road_line.project(pt)

        road_segment = substring(
            road_line,
            max(0.0, dist_pt_on_road - sample_dist),
            min(road_line.length, dist_pt_on_road + sample_dist),
        )
        if isinstance(road_segment, Point):
            feedback.reportError(f"ERROR: Unable to extract road segment for row index: {idx}", False)
            results.append(row_results)
            lines.append(None)
            xs_curves.append(None)
            continue
                        
        gutter_segment = offset_line_through_point(road_segment, pt)

        pt_array, elev_array, inlet_pos = extract_points_and_elevations(
            band, dem, pt, gutter_segment, sample_dist, n_points_extract_each_dir
        )

        cr = classify(pt_array, elev_array, inlet_pos, sag_tolerance)
        row_results.update({
            "inlet_id":      idx,
            "grade_sag":     cr.label,
            "elev_inlet": cr.elev_inlet,
            "elev_up":    cr.us_max_elev,
            "elev_dn":    cr.ds_max_elev,
            "elev_min":   cr.min_elev,
            "avg_slope":     cr.avg_slope,
        })
        results.append(row_results)
        lines.append(LineString(pt_array) if len(pt_array) > 1 else None)

        xs_curves.append(cr.curve_data)

        # SX / CN boundary-condition lines for ON GRADE inlets
        if cr.label == "ON GRADE":
            pt_on_road = road_line.interpolate(dist_pt_on_road)
            d = np.array([pt.x - pt_on_road.x, pt.y - pt_on_road.y])
            d_len = math.hypot(*d)
            if d_len > 0:
                d /= d_len
            bc_pt = Point(
                pt.x + d[0] * sx_line_reverse_distance,
                pt.y + d[1] * sx_line_reverse_distance,
            )
            bc_sx = LineString([pt_on_road, bc_pt]).parallel_offset(sx_offset)

            sx_row = bc_row_template.copy()
            sx_row.update(Type="SX", geometry=bc_sx)
            bc_data.append(sx_row)

            cn_row = bc_row_template.copy()
            cn_row.update(Type="CN", geometry=LineString([pt, Point(bc_sx.coords[-1])]))
            bc_data.append(cn_row)

    # 5. Write outputs

    gdf_check_points = gpd.GeoDataFrame(results, crs=output_crs)
    rval.gdf_check_points = gdf_check_points

    n_sag   = (gdf_check_points["grade_sag"] == "ON SAG").sum()
    n_grade = (gdf_check_points["grade_sag"] == "ON GRADE").sum()
    n_unk   = (gdf_check_points["grade_sag"] == "UNKNOWN").sum()
    feedback.pushInfo(f"\n  Results summary:")
    feedback.pushInfo(f"    ON SAG   : {n_sag}")
    feedback.pushInfo(f"    ON GRADE : {n_grade}")
    feedback.pushInfo(f"    UNKNOWN  : {n_unk}")
    feedback.pushInfo(f"    TOTAL    : {len(gdf_check_points)}")

    out_lines = gdf_check_points.copy()
    out_lines["geometry"] = lines
    # Don't need the information is in the points data and lines written in 1d_xs format
    # write_gpkg_layer(out_lines, layer_name + "_classified_lines", out_path, feedback)

    #write_gpkg_layer(gpd.GeoDataFrame(bc_data, crs=output_crs), "2d_bc_" + layer_name, out_path, feedback)
    if len(bc_data) > 0:
        rval.gdf_bcs = gpd.GeoDataFrame(bc_data, geometry='geometry', crs=output_crs)

    gdf_inlets_out = gdf_inlets.copy()
    gdf_inlets_out.loc[gdf_check_points["grade_sag"] == "ON GRADE", "Placement"] = "ON_GRADE"
    gdf_inlets_out.loc[gdf_check_points["grade_sag"] == "ON SAG",   "Placement"] = "ON_SAG"
    mask_slope = ~gdf_check_points["avg_slope"].isna()
    gdf_inlets_out.loc[mask_slope, "SlopePct_Longitudinal"] = gdf_check_points.loc[mask_slope, "avg_slope"]
    gdf_inlets_out.loc[gdf_check_points["grade_sag"] == "ON GRADE", "Conn1D_2D"] = ""
    gdf_inlets_out[['Qmax', 'aLocal', 'wLocal']] = gdf_inlets_out[['Qmax', 'aLocal', 'wLocal']].fillna(0.0)
    rval.gdf_inlets_mod = gdf_inlets_out
    # write_gpkg_layer(inlets_out, "swmm_iu_" + layer_name, out_path, feedback)

    # write_1d_xs_layer(out_lines, xs_curves, out_path, "1d_xs_" + layer_name, feedback)
    rval.gdf_check_xs = create_xs_gdf(out_lines, xs_curves, csv_folder, feedback)
    rval.output_crs = output_crs

    feedback.pushInfo("\nDone.\n")

    return rval
    


# ── main processing ───────────────────────────────────────────────────────────
def process(
    gpkg_path:   str,
    layer_name:  str,
    dem_path:    str,
    road_gpkg:   str,
    road_layer:  str,
    out_path:    str,
    sample_dist: float,
    max_road: float,
    sag_tolerance: float,
    n_points_extract_each_dir: int,
    sx_line_reverse_distance: float,
    sx_offset: float,
    feedback = ScreenProcessingFeedback()
):
    feedback.pushInfo("\n=== Stormwater Inlet Classifier ===\n")

    gdf_inlets = gpd.read_file(gpkg_path, layer=layer_name)

    gdf_roads = gpd.read_file(road_gpkg, layer=road_layer, columns=['geometry'])

    csv_folder = Path(out_path).parent / 'csv/'
    csv_folder.mkdir(exist_ok=True, parents=True)

    process_result = process_gdb(
        dem_path,
        gdf_inlets,
        gdf_roads,
        sample_dist,
        max_road,
        sag_tolerance,
        n_points_extract_each_dir,
        sx_line_reverse_distance,
        sx_offset,
        str(csv_folder),
        feedback)

    # 5. Write outputs
    feedback.pushInfo("\n[Writing output ...")

    out_gdf = process_result.gdf_check_points
    if out_gdf is not None:
        n_sag   = (out_gdf["grade_sag"] == "ON SAG").sum()
        n_grade = (out_gdf["grade_sag"] == "ON GRADE").sum()
        n_unk   = (out_gdf["grade_sag"] == "UNKNOWN").sum()
        feedback.pushInfo(f"\n  Results summary:")
        feedback.pushInfo(f"    ON SAG   : {n_sag}")
        feedback.pushInfo(f"    ON GRADE : {n_grade}")
        feedback.pushInfo(f"    UNKNOWN  : {n_unk}")
        feedback.pushInfo(f"    TOTAL    : {len(out_gdf)}")

        write_gpkg_layer(out_gdf, layer_name + "_classified", out_path, feedback)

    write_gpkg_layer(process_result.gdf_bcs, "2d_bc_" + layer_name, out_path, feedback)

    write_gpkg_layer(process_result.gdf_inlets_mod, "swmm_iu_" + layer_name, out_path, feedback)

    write_gpkg_layer(process_result.gdf_check_xs, "1d_xs_" + layer_name, out_path, feedback)

    feedback.pushInfo("\nDone.\n")


# ── entry point ───────────────────────────────────────────────────────────────
def main():
    inlet_gpkg  = "D:/models/TUFLOW/ForPresentations/MountVernon/Rev_Tide_20260304_ExAlts_NoResults/model/gis/swmm_iu_MV02_003_P.gpkg"
    inlet_layer = "swmm_iu_mv02_p"
    dem         = "D:/models/TUFLOW/ForPresentations/MountVernon/Rev_Tide_20260304_ExAlts_NoResults_orig/model/gis/grid/MV_DEM.tif"
    out_gpkg    = "D:/models/TUFLOW/ForPresentations/MountVernon/Rev_Tide_20260304_ExAlts_NoResults/model/gis/inlets_classified.gpkg"
    road_gpkg   = "D:/models/TUFLOW/ForPresentations/MountVernon/nys_streets.gpkg"
    road_layer  = "nys_streets"

    sample_dist = 25.0
    max_road_dist = 100.0
    sag_tolerance = 0.1
    n_points_each_dir = 5
    sx_line_reverse_distance = 10.0
    sx_offset = 2.0

    process(inlet_gpkg, 
            inlet_layer, 
            dem, road_gpkg, 
            road_layer, 
            out_gpkg,
            sample_dist,
            max_road_dist,
            sag_tolerance,
            n_points_each_dir,
            sx_line_reverse_distance,
            sx_offset)

if __name__ == "__main__":
    main()