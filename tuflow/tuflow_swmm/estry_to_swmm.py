from pathlib import Path

has_gpd = False
try:
    import geopandas as gpd

    has_gpd = True
except ImportError:
    pass  # defaulted to false
import pandas as pd

from tuflow.tuflow_swmm.create_swmm_section_gpkg import create_section_from_gdf
from tuflow.tuflow_swmm.xs_processing import get_normalized_hw


# Load the pydev pycharm if available
# try:
#    import pydevd_pycharm
# except ModuleNotFoundError:
#    pass


def pit_inlet_dbase_to_df(file_inlet_db, crs, feedback):
    file_inlet_db = Path(file_inlet_db)
    curve_layername = None

    df_main = pd.read_csv(file_inlet_db, sep=',')

    # gdf_curve_template, curve_layername = create_section_gdf('CURVES', crs)
    # print(gdf_curve_template)

    # Make all the columns lowercase to make case-insensitive
    df_main = df_main.rename(columns=lambda x: x.strip().lower())
    # print(df_main)

    # rename colums if necessary
    df_main = df_main.rename(
        columns={
            df_main.columns[2]: 'depth_column',
            df_main.columns[3]: 'flow_column',
        }
    )

    gdf_curves = []
    for row in df_main[['name', 'source', 'depth_column', 'flow_column']].itertuples():
        curve_filename = file_inlet_db.parent / row.source

        # skip lines until we get see the depth column name
        depth_col_num = None
        flow_col_num = None
        df_curve = None
        with open(curve_filename, 'r') as curve_file:
            found = False
            while not found:
                line = curve_file.readline()
                # remove anything after comments
                comment_loc = line.find('!')
                if comment_loc != -1:
                    line = line[:comment_loc]
                line_vals = [x.strip() for x in line.split(',')]
                # print(line_vals)
                depth_col_num = line_vals.index(row.depth_column) if row.depth_column in line_vals else None
                flow_col_num = line_vals.index(row.flow_column) if row.flow_column in line_vals else None
                if depth_col_num or flow_col_num:
                    found = True

            # print(depth_col_num)
            # print(flow_col_num)
            df_curve = pd.read_csv(
                curve_file,
                comment='!',
                skip_blank_lines=False,
                skiprows=0,
                usecols=[depth_col_num, flow_col_num],
                names=[row.depth_column, row.flow_column]
            )
            df_curve['Name'] = row.name

        # print(type(gdf_curve_template))
        # gdf_curve = gdf_curve_template.copy(deep=True)
        # gdf_curve[[
        #    'val1',
        #    'val2',
        # ]] = df_curve[[row.depth_col, row.flow_col]]
        # gdf_curve['Name'] = row.name

        curve_col_mapping = {
            'Name': 'Name',
            row.depth_column: 'xval',
            row.flow_column: 'yval',
        }
        # print(df_curve)

        gdf_curve, curve_layername = create_section_from_gdf('Curves',
                                                             crs,
                                                             df_curve,
                                                             curve_col_mapping)
        gdf_curve['Type'] = gdf_curve['Type'].astype(str)
        gdf_curve.loc[gdf_curve.index[0], 'Type'] = 'RATING'
        # print(type(gdf_curve))
        gdf_curves.append(gdf_curve)

    gdf_curves_merged = pd.concat(gdf_curves)

    feedback.pushInfo(f'Read {len(gdf_curves)} curves.')
    # print(type(gdf_curves_merged))
    # print(gdf_curves_merged)
    return gdf_curves_merged, curve_layername


def create_curves_from_dfs(curve_type, curve_names, df_curves, crs):
    gdf_curves = []

    for curve_name, df in zip(curve_names, df_curves):
        # Can't have spaces
        df['Name'] = curve_name.replace(' ', '_')
        curve_col_mapping = {
            'Name': 'Name',
            df.columns[0]: 'xval',
            df.columns[1]: 'yval',
        }

        gdf_curve, _ = create_section_from_gdf('Curves',
                                               crs,
                                               df,
                                               curve_col_mapping)

        gdf_curve['Type'] = gdf_curve['Type'].astype(str)
        gdf_curve.loc[gdf_curve.index[0], ['Type']] = curve_type
        gdf_curves.append(gdf_curve)

    gdf_curves_merged = pd.concat(gdf_curves)
    # print(gdf_curves_merged)

    return gdf_curves_merged


def array_from_csv(filename, col_headings):
    df_curve = pd.read_csv(
        filename,
        comment='!',
        skip_blank_lines=False,
    )
    df_curve.columns = df_curve.columns.str.lower()
    while len(df_curve) > 0 and not pd.Series(col_headings).isin(df_curve.columns).all():
        df_curve.columns = df_curve.iloc[0]
        df_curve.columns = df_curve.columns.str.lower()
        df_curve = df_curve.tail(-1)
    if len(df_curve) == 0:
        raise ValueError(f'Error column headings {col_headings} not found in file {filename}')
    df_curve = df_curve[col_headings]
    return df_curve.values


def hw_curve_from_xz(filename):
    values = array_from_csv(filename, ['x', 'z'])

    minval, maxval, hw = get_normalized_hw(values)

    df = pd.DataFrame(
        {
            'h': hw[:, 0],
            'w': hw[:, 1],
        }
    )

    return minval, maxval, df


def create_hw_curves2(gdf, filename_ta_tables, crs, feedback):
    # Read in the check file looking for channels
    dfs_hw = {}  # dataframes for channel data by channel name

    with open(filename_ta_tables, "r") as f_ta:
        current_table = None
        current_table_lines = ""

        for line in f_ta:
            if current_table is None:
                if line.startswith('Channel'):
                    current_table = line.split(' ')[1]  # channel name is the second item
            else:
                if line.strip() == '':
                    # current table finished
                    df = pd.read_csv(StringIO(current_table_lines), sep=',', usecols=range(9), skipinitialspace=True)
                    print(df)
                    dfs_hw[current_table] = df
                    current_table = None
                    current_table_lines = ""
                else:
                    current_table_lines += f'\n{line}'

    # Handle last table if one found
    if current_table is not None:
        df = pd.read_csv(StringIO(current_table_lines), sep=',', usecols=range(9), skipinitialspace=True)
        print(df)
        dfs_hw[current_table] = df

    curve_names = []
    max_heights = []
    dfs = []

    # print(gdf['Link'])
    for _, (channel_name, *_) in gdf[['Link']].iterrows():
        print(channel_name)

        df_trim = dfs_hw[channel_name]

        df_trim = df_trim[['Depth', 'Flow Width']].rename(
            columns={
                'Depth': 'Height',
                'Flow Width': 'Width',
            }
        )
        print(df_trim)

        curve_names.append(str(channel_name))
        max_heights.append(df_trim['Height'].max())
        dfs.append(df_trim)

    return curve_names, max_heights, create_curves_from_dfs('SHAPE', curve_names, dfs, crs)
