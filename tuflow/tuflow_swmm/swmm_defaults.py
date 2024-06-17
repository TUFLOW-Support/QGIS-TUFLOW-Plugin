has_gpd = False
try:
    import geopandas as gpd

    has_gpd = True
except ImportError:
    pass  # defaulted to false
import pandas as pd

from tuflow.tuflow_swmm.create_swmm_section_gpkg import create_section_gdf, create_section_from_gdf


def default_options_table(crs, report_step, min_surfarea):
    option_values = {
        'FLOW_UNITS': 'CMS',
        'INFILTRATION': 'GREEN_AMPT',
        'FLOW_ROUTING': 'DYNWAVE',
        'LINK_OFFSETS': 'DEPTH',
        'FORCE_MAIN_EQUATION': 'H-W',
        'IGNORE_RAINFALL': 'NO',
        'IGNORE_SNOWMELT': 'YES',
        'IGNORE_GROUNDWATER': 'YES',
        'IGNORE_RDII': 'YES',
        'IGNORE_QUALITY': 'YES',
        'ALLOW_PONDING': 'YES',
        'SKIP_STEADY_STATE': 'YES',
        'SYS_FLOW_TOL': '1',
        'LAT_FLOW_TOL': '1',
        'START_DATE': '2000-01-01',
        'START_TIME': '00:00',
        'END_DATE': '2000-01-01',
        'END_TIME': '06:00',
        'REPORT_START_DATE': '2000-01-01',
        'REPORT_START_TIME': '00:00',
        'SWEEP_START': '01/01',
        'SWEEP_END': '01/01',
        'DRY_DAYS': '0',
        'REPORT_STEP': report_step,
        'WET_STEP': '00:00:30',
        'DRY_STEP': '00:30:00',
        'ROUTING_STEP': '30',
        'LENGTHENING_STEP': '1',
        'VARIABLE_STEP': '0',
        'MINIMUM_STEP': '0.001',
        'INERTIAL_DAMPING': 'PARTIAL',
        'NORMAL_FLOW_LIMITED': 'BOTH',
        'MIN_SURFAREA': min_surfarea,
        'MAX_TRIALS': '20',
        'HEAD_TOLERANCE': '0.001',
        'THREADS': '8',
    }
    ar_options = option_values.keys()
    ar_values = option_values.values()

    df_defaults = gpd.GeoDataFrame(
        data={
            'Option': ar_options,
            'Value': ar_values,
        },
        geometry=gpd.GeoSeries([None], crs=crs)
    )
    defaults_mapping = {
        'Option': 'Option',
        'Value': 'Value',
        'geometry': 'geometry',
    }
    gdf_options, options_layername = create_section_from_gdf(
        'Options',
        crs,
        df_defaults,
        defaults_mapping,
    )

    return gdf_options, options_layername


def default_reporting_table(crs):
    option_values = {
        'SUBCATCHMENTS': 'ALL',
        'NODES': 'ALL',
        'LINKS': 'ALL',
    }
    gdf_report, report_layername = create_section_gdf('Report', crs)

    ar_options = option_values.keys()
    ar_values = option_values.values()

    df = gpd.GeoDataFrame(
        data={
            'Format': ar_options,
            'Value': ar_values,
        },
        geometry=gpd.GeoSeries([None], crs=crs),
    )
    gdf_report = pd.concat(
        [
            gdf_report,
            df,
        ],
        axis=0
    )
    gdf_report = gdf_report[1:]

    return gdf_report, report_layername
