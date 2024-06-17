has_gpd = False
try:
    import geopandas as gpd

    has_gpd = True
except ImportError:
    pass  # defaulted to false
import numpy as np
import pandas as pd
from pathlib import Path

from tuflow.tuflow_swmm.create_swmm_section_gpkg import create_section_gdf, create_section_from_gdf
from tuflow.tuflow_swmm.gis_to_swmm import gis_to_swmm
from tuflow.tuflow_swmm.swmm_processing_feedback import ScreenProcessingFeedback
from tuflow.tuflow_swmm.swmm_io import write_tuflow_version


def generate_curve(curve_name, coeff, exponent, crs):
    depths = np.array([0.0, 0.05, 0.1, 0.2, 0.5, 1.0, 1.5, 2.0, 5.0, 10.0, 15.0])
    discharges = coeff * np.power(depths, exponent)

    df_curve = pd.DataFrame(
        {
            'Depth': depths,
            'Discharge': discharges,
        }
    )
    df_curve['Name'] = curve_name

    curve_col_mapping = {
        'Name': 'Name',
        'Depth': 'xval',
        'Discharge': 'yval',
    }
    # print(df_curve)

    gdf_curve, curve_layername = create_section_from_gdf('Curves',
                                                         crs,
                                                         df_curve,
                                                         curve_col_mapping)
    gdf_curve['Type'] = gdf_curve['Type'].dropna().astype(str)
    gdf_curve.loc[gdf_curve.index[0], 'Type'] = 'RATING'
    # gdf_curve['Type'].iloc[0] = 'RATING'

    return gdf_curve


def xpswmm_2d_capture_to_swmm_gpd(
        gdf_in,
        field_elev,
        field_2d_capture_flag,
        field_2d_capture_coeff,
        field_2d_capture_exponent,
        connection_width,
        crs,
        swmm_gdfs_layernames,
        feedback=ScreenProcessingFeedback(),
):
    gdf_in['curve_name'] = 'C' + gdf_in[field_2d_capture_coeff].astype(str).str.replace('.', '_') + '-' \
                           + 'E' + gdf_in[field_2d_capture_exponent].astype(str).str.replace('.', '_')

    # Create curves for unique coefficients and exponents
    gdf_unique = gdf_in.drop_duplicates(subset=['curve_name'])

    curves = [
        generate_curve(curve_name,
                       coeff,
                       exponent,
                       crs) for curve_name, coeff, exponent in
        zip(gdf_unique['curve_name'],
            gdf_unique[field_2d_capture_coeff],
            gdf_unique[field_2d_capture_exponent])
    ]

    gdf_curves_merged = pd.concat(curves)

    swmm_gdfs_layernames.append((gdf_curves_merged, 'Curves--Curves'))

    # Create a dummy streets layer
    gdf_streets, streets_layername = create_section_gdf('Streets', crs)
    gdf_street_info = gpd.GeoDataFrame(
        {
            'Name': 'DummyStreet',
            'Tcrown': 10,
            'Hcurb': 0.2,
            'Sx': 4.0,
            'nRoad': 0.016,
            'a': 0.0,
            'W': 0.0,
            'Sides': 1,
            'Tback': 5.0,
            'Sback': 8.0,
            'nBack': 0.016
        },
        index=[0],
        geometry=[None],
        crs=crs,
    )
    gdf_streets = pd.concat([gdf_streets, gdf_street_info], axis=0)
    gdf_streets = gdf_streets[1:]  # Remove dummy row

    swmm_gdfs_layernames.append((gdf_streets, streets_layername))

    # Make the inlet layer
    # don't use unique because we need to use this for inlet usage
    # gdf_inlets = gdf_unique[gdf_unique[field_2d_capture_flag] == 1]
    gdf_inlets = gdf_in[gdf_in[field_2d_capture_flag] == 1]
    if len(gdf_inlets) > 0:
        inlet_q_to_inlets_map = {
            'curve_name': 'Name',
            'geometry': 'geometry',
        }

        gdf_inlets_q, inlets_layername = create_section_from_gdf('Inlets',
                                                                 crs,
                                                                 gdf_inlets,
                                                                 inlet_q_to_inlets_map)
        gdf_inlets_q['Type'] = 'CUSTOM'
        gdf_inlets_q['Custom_Curve'] = gdf_inlets_q['Name']
        gdf_inlets_q['geometry'] = None
        gdf_inlets_q = gdf_inlets_q.drop_duplicates(subset='Custom_Curve')

        swmm_gdfs_layernames.append((gdf_inlets_q, inlets_layername))

    # Make the inlet usage layer
    gdf_inlets['Number'] = 1
    gdf_inlets['CloggedPct'] = 0.0
    gdf_inlets['Conn1D_2D'] = 'SX'
    gdf_inlets['Conn_width'] = connection_width

    xpswmm_to_inlet_usage_map = {
        'curve_name': 'Inlet',
        'Number': 'Number',
        'CloggedPct': 'CloggedPct',
        field_elev: 'Elevation',
        'geometry': 'geometry',
        'Conn1D_2D': 'Conn1D_2D',
        'Conn_width': 'Conn_width'
    }
    gdf_inlet_usage_ext, inlet_usage_ext_layername = \
        create_section_from_gdf('Inlet_Usage_ext',
                                crs,
                                gdf_inlets,
                                xpswmm_to_inlet_usage_map)

    gdf_inlet_usage_ext['StreetXSEC'] = 'DummyStreet'
    gdf_inlet_usage_ext['SlopePct_Long'] = 1.0
    gdf_inlet_usage_ext['Qmax'] = 0.0
    gdf_inlet_usage_ext['aLocal'] = 0.0
    gdf_inlet_usage_ext['wLocal'] = 0.0
    gdf_inlet_usage_ext['Placement'] = 'ON_SAG'

    return gdf_inlet_usage_ext


def xpswmm_2d_capture_to_swmm(
        gis_filename,
        field_node_name,
        field_elev,
        field_2d_capture_flag,
        field_2d_capture_coeff,
        field_2d_capture_exponent,
        connection_width,
        crs,
        output_inp_file,
        output_iu_file,
        feedback=ScreenProcessingFeedback(),
):
    if not has_gpd:
        message = ('This tool requires geopandas: to install please follow instructions on the following webpage: '
                   'https://wiki.tuflow.com/QGIS_Intallation_with_OSGeo4W')
        feedback.reportError(message)
        return

    gdf = gpd.read_file(gis_filename)
    print(gdf)

    gdfs_to_write = []

    gdf_inlet_usage = xpswmm_2d_capture_to_swmm_gpd(
        gdf,
        field_elev,
        field_2d_capture_flag,
        field_2d_capture_coeff,
        field_2d_capture_exponent,
        connection_width,
        crs,
        gdfs_to_write,
        feedback,
    )

    gpkg_inp_file = output_inp_file.with_suffix('.gpkg')

    for gdf_to_write, layer_name in gdfs_to_write:
        gdf_to_write.to_file(gpkg_inp_file,
                             layer=layer_name,
                             driver='GPKG',
                             overwrite=True)

    # Create the TUFLOW-SWMM table information
    write_tuflow_version(gpkg_inp_file)

    gdf_inlet_usage.to_file(output_iu_file,
                            layer='inlet_usage',
                            driver='GPKG')

    gis_to_swmm(gpkg_inp_file,
                output_inp_file)


if __name__ == "__main__":
    pd.set_option('display.max_columns', 500)
    # pd.set_option('display.min_rows', 50)
    pd.set_option('display.max_rows', 50)
    pd.set_option('display.width', 300)
    pd.set_option('max_colwidth', 100)

    folder = Path(r'D:\models\TUFLOW\test_models\SWMM\SanAntonio\BMT\TUFLOW\model\swmm')
    gis_input = folder / 'exported_nodes.mif'

    field_node_name = 'NodeName'
    field_elev = 'GroundElevation'
    field_2d_capture_flag = 'Node2DInflowCaptureFlag'
    field_2d_capture_coeff = '2DInflowCaptureCoefficient'
    field_2d_capture_exponent = '2DInflowCaptureExponent'

    connection_width = 5.0

    crs = 'PROJCRS["unnamed",BASEGEOGCRS["unnamed",DATUM["GRS_80",ELLIPSOID["GRS 80",6378137,298.257222101,LENGTHUNIT["metre",1,ID["EPSG",9001]]]],PRIMEM["Greenwich",0,ANGLEUNIT["degree",0.0174532925199433,ID["EPSG",9122]]]],CONVERSION["Transverse Mercator",METHOD["Transverse Mercator",ID["EPSG",9807]],PARAMETER["Latitude of natural origin",0,ANGLEUNIT["degree",0.0174532925199433],ID["EPSG",8801]],PARAMETER["Longitude of natural origin",147,ANGLEUNIT["degree",0.0174532925199433],ID["EPSG",8802]],PARAMETER["Scale factor at natural origin",0.9996,SCALEUNIT["unity",1],ID["EPSG",8805]],PARAMETER["False easting",500000,LENGTHUNIT["metre",1],ID["EPSG",8806]],PARAMETER["False northing",10000000,LENGTHUNIT["metre",1],ID["EPSG",8807]]],CS[Cartesian,2],AXIS["(E)",east,ORDER[1],LENGTHUNIT["metre",1,ID["EPSG",9001]]],AXIS["(N)",north,ORDER[2],LENGTHUNIT["metre",1,ID["EPSG",9001]]]]'

    output_inp_file = folder / 'test_xp_convert.inp'
    output_iu_file = folder / 'test_iu.gpkg'

    xpswmm_2d_capture_to_swmm(
        gis_input,
        field_node_name,
        field_elev,
        field_2d_capture_flag,
        field_2d_capture_coeff,
        field_2d_capture_exponent,
        connection_width,
        crs,
        output_inp_file,
        output_iu_file,
    )
