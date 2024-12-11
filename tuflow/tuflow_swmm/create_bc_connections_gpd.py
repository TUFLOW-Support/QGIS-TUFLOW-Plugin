import geopandas as gpd

try:
    from shapely import get_coordinates
    from shapely.geometry.linestring import LineString
    from shapely.geometry.point import Point
    has_shapely = True
except ImportError:
    has_shapely = False
    LineString = 'LineString'
    Point = 'Point'

from tuflow.tuflow_swmm.gis_messages import GisMessages
from tuflow.tuflow_swmm.swmm_processing_feedback import ScreenProcessingFeedback
from tuflow.tuflow_swmm.geom_util import get_perp_offset_line_points, get_line_offset_from_point


def fill_bc_data(row,
                 gdf_all_links: gpd.GeoDataFrame,
                 bc_data: dict,
                 offset_dist: float,
                 bc_width: float,
                 outfall_connections: bool,
                 set_z_flag: bool,
                 gis_messages: GisMessages,
                 feedback: any):
    if not has_shapely:
        feedback.reportError('Shapely not installed and is required for function: fill_bc_data().',
                             fatalError=True)

    if outfall_connections:
        # Look for upstream connections and make SX connections
        gdf_upstream_connections = gdf_all_links[gdf_all_links['To Node'] == row.Name]
        if len(gdf_upstream_connections) == 0:
            feedback.pushWarning('Warning: No Upstream link for outfall. SX line has arbitrary orientation.')
            gis_messages.add_message(
                row.geometry,
                'WARNING',
                'No Upstream Link for outfall. SX line has arbitrary orientation.'
            )

            bc_geom = get_line_offset_from_point(row.geometry,
                                                 offset_dist,
                                                 bc_width,
                                                 0.0)
        else:
            bc_geom = get_perp_offset_line_points(gdf_upstream_connections['geometry'].iloc[0],
                                                  offset_dist,
                                                  bc_width,
                                                  False)

        # SX line
        bc_data['geometry'].append(bc_geom)
        bc_data['Type'].append('SX')
        bc_data['Name'].append('')
        bc_data['Flags'].append('Z' if set_z_flag else '')

        # Connection Line
        bc_data['geometry'].append(
            LineString(
                [
                    row['geometry'],
                    Point(bc_geom.coords[0]),
                ]
            )
        )
        bc_data['Type'].append('CN')
        bc_data['Name'].append('')
        bc_data['Flags'].append('Z' if set_z_flag else '')
    else:
        # Look for downstream connections and make HX connections
        gdf_downstream_connections = gdf_all_links[gdf_all_links['From Node'] == row.Name]

        if len(gdf_downstream_connections) == 0:
            feedback.pushWarning('Warning: No Downstream link for HX connection. HX line has arbitrary orientation.')
            gis_messages.add_message(
                row.geometry,
                'WARNING',
                'No Downstream Link for HX connection. HX line has arbitrary orientation.'
            )

            bc_geom = get_line_offset_from_point(row.geometry,
                                                 offset_dist,
                                                 bc_width,
                                                 0.0)
        else:
            bc_geom = get_perp_offset_line_points(gdf_downstream_connections['geometry'].iloc[0],
                                                  offset_dist,
                                                  bc_width,
                                                  True)

        # HX line
        bc_data['geometry'].append(bc_geom)
        bc_data['Type'].append('HX')
        bc_data['Name'].append('')
        bc_data['Flags'].append('Z' if set_z_flag else '')

        # Connection Line1
        bc_data['geometry'].append(
            LineString(
                [
                    row['geometry'],
                    Point(bc_geom.coords[0]),
                ]
            )
        )
        bc_data['Type'].append('CN')
        bc_data['Name'].append('')
        bc_data['Flags'].append('Z' if set_z_flag else '')

        # Connection Line2
        bc_data['geometry'].append(
            LineString(
                [
                    row['geometry'],
                    Point(bc_geom.coords[-1]),
                ]
            )
        )
        bc_data['Type'].append('CN')
        bc_data['Name'].append('')
        bc_data['Flags'].append('Z' if set_z_flag else '')


def create_bc_connections_gpd(
        gdf_all_links: gpd.GeoDataFrame,
        gdf_nodes: gpd.GeoDataFrame,
        outfall_connections: bool,
        offset_dist: float,
        bc_width: float,
        set_z_flag: bool,
        gis_messages: GisMessages,
        feedback=ScreenProcessingFeedback,
) -> gpd.GeoDataFrame or None:
    if len(gdf_all_links) == 0:
        return None

    bc_data = {
        'Type': [],
        'Flags': [],
        'Name': [],
        'geometry': [],
    }
    gdf_nodes.apply(
        fill_bc_data,
        args=(
            gdf_all_links,
            bc_data,
            offset_dist,
            bc_width,
            outfall_connections,
            set_z_flag,
            gis_messages,
            feedback),
        axis=1,
    )

    bc_columns = [
        'Type',
        'Flags',
        'Name',
        'f',
        'D',
        'Td',
        'A',
        'B',
        'geometry',
    ]
    gdf_bc_data = gpd.GeoDataFrame(
        data=bc_data,
        crs=gdf_all_links.crs,
    )
    # Add missing fields
    for field in bc_columns:
        if field not in gdf_bc_data.columns:
            gdf_bc_data[field] = 0
    gdf_bc_data = gdf_bc_data[bc_columns]

    return gdf_bc_data
