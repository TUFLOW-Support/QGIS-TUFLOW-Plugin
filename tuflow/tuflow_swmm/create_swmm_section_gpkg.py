import os

os.environ['USE_PYGEOS'] = '0'

from pathlib import Path
has_fiona = False
try:
    import fiona
    has_fiona = True
except ImportError:
    pass # defaulted to False
has_gpd = False
try:
    import geopandas as gpd

    has_gpd = True
except ImportError:
    pass  # defaulted to false
import numpy as np
import pandas as pd
from shapely.geometry import Point, LineString, Polygon

from tuflow.tuflow_swmm import swmm_sections

swmm_section_list = swmm_sections.swmm_section_definitions()


def create_section_gdf(section_name, crs):
    # print(swmm_sections)
    section = list(filter(lambda x: x.name == section_name, swmm_section_list))
    # print(section)
    if not section:
        raise ValueError(f"Unable to find section: {section_name}")
    section = section[0]
    # print(section)
    # name, prefix, headings, geo_source = section
    headings = section.get_all_column_names()
    geo_source = section.geometry
    # print(name)
    data = []
    for datatype in section.get_all_column_types():
        data.append(datatype())

    df_section = pd.DataFrame.from_records([data],
                                           columns=headings)

    # Default to empty points
    geo_series = gpd.GeoSeries([Point(0.0, 0.0)], crs=crs)
    if geo_source == swmm_sections.GeometryType.LINKS:
        # print('Section Geometry is LineStrings')
        geo_series = gpd.GeoSeries([LineString()], crs=crs)
    elif geo_source == swmm_sections.GeometryType.SUBCATCHMENTS:
        # print('Section Geometry is Polygons')
        geo_series = gpd.GeoSeries([Polygon()], crs=crs)
    elif geo_source is None:
        # print('Section Geometry is None')
        geo_series = gpd.GeoSeries([None], crs=crs)
    else:
        pass
        # print('Section Geometry is points')

    gdf = gpd.GeoDataFrame(
        df_section,
        geometry=geo_series,
    )

    if section.name in swmm_sections.sections_to_append:
        for prefix, table, merge_col1, merge_col2 in swmm_sections.sections_to_append[section.name]:
            gdf2, layername2 = create_section_gdf(table, crs)
            gdf = gdf.merge(
                gdf2.rename(columns=lambda x: f'{prefix}_{x}'),
                how='left',
                left_on=merge_col1,
                right_on=f'{prefix}_{merge_col2}',
            )
            gdf = gdf.drop(columns=[f'{prefix}_{merge_col2}',
                                    f'{prefix}_geometry'])

    # Add Tag and Description columns
    if section.name in swmm_sections.tag_table_type:
        gdf['Tag'] = None

    if section.name in swmm_sections.tables_with_description:
        gdf['Description'] = None

    if section.prefix != '':
        layer_name = f'{section.prefix}--{section.name}'
    else:
        layer_name = section.name

    return gdf, layer_name


def create_section_from_gdf(section_name, section_crs, gdf_in, column_mapping):
    gdf_template, layername = create_section_gdf(section_name, section_crs)

    gdf_out = gdf_in[column_mapping.keys()].copy(deep=True)
    gdf_out = gdf_out.rename(columns=column_mapping)

    if 'geometry' not in gdf_out:
        gdf_out['geometry'] = gdf_template['geometry']

    gdf_out = gdf_out.set_geometry('geometry')

    # add any columns (with null entries) for columns not in the mapping
    missing_columns = set(gdf_template.columns) - set(gdf_out.columns)
    if missing_columns:
        for missing_col in missing_columns:
            gdf_out[missing_col] = [np.nan] * len(gdf_out)
    # order columns same as the template table
    gdf_out = gdf_out[gdf_template.columns]
    gdf_out.set_crs(section_crs, allow_override=True)

    return gdf_out, layername


def add_swmm_section_to_gpkg(path_geopackage, section_name, crs):
    gdf, layer_name = create_section_gdf(section_name, crs)

    # gdf = gdf.drop(index=0)
    gdf.to_file(path_geopackage, layer=layer_name, driver='GPKG', index=False)

    return layer_name


if __name__ == "__main__":
    pd.set_option('display.max_columns', 500)
    pd.set_option('display.width', 200)

    folder = Path(r"D:\temp")
    gpkg_filename = "test_add_section_gpkg.gpkg"
    section_names = [
        'Conduits',
        'Storage',
    ]
    crs = 'EPSG:32760'

    (folder / gpkg_filename).unlink(True)

    for section_name in section_names:
        print(section_name)
        add_swmm_section_to_gpkg(folder / gpkg_filename, section_name, crs)
