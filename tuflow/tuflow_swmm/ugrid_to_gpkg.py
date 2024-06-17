has_gpd = False
try:
    import geopandas as gpd

    has_gpd = True
except ImportError:
    pass  # defaulted to false
import h5py
import numpy as np
import pandas as pd
from pathlib import Path
import datetime
from shapely.geometry import Point, LineString

def ugrid_to_gpkg(in_filename,
                  out_filename):

    node_dsets = [
        'Depth',
        'Flood Losses',
        'Lateral Inflow',
        'Net Lateral Inflow',
        'Storage Volume',
        'Total Inflow',
        'Water Level',
    ]

    channel_dsets = [
        'Channel Capacity',
        'Channel Depth',
        'Channel Volume',
        'Flow',
                'Velocity',
    ]

    with h5py.File(in_filename, "r") as f:
        print(f.keys())

        node_x = f['mesh_node_x'][:]
        node_y = f['mesh_node_y'][:]
        print(len(node_x))

        times = f['time'][:]
        print(times)
        print(len(times))

        df_nodes = pd.DataFrame(data=
        {
            'NodeNum': range(len(node_x)),
            'x': node_x,
            'y': node_y,
            'z': f['elevation'][:],
        }
                     )
        print(df_nodes)

        df_times = pd.DataFrame(data=
        {
            'Time': times,
        }
        )
        df_times['Datetime'] = df_times['Time'].apply(lambda x: datetime.datetime(2000,1, 1) +
                                                datetime.timedelta(hours=x))
        print(df_times)

        df_combined = pd.merge(df_nodes, df_times, how='cross')
        print(df_combined)

        for node_dset in node_dsets:
            h5dset = f[node_dset]
            values = h5dset[:]
            print(values)
            print(len(values))
            print(len(values[0]))

            df_combined[node_dset] = np.array(values).flatten('F')

        print(df_combined)
        gdf_combined = gpd.GeoDataFrame(
            df_combined,
            geometry=gpd.points_from_xy(df_combined['x'],
                                        df_combined['y'])
        )
        gdf_combined.to_file(out_filename, layer='Nodes', driver='GPKG')


        # Do the lines
        connectivity = f['edge_node_connectivity'][:]
        lines = []
        for conn_line in connectivity:
            # print(conn_line.tolist())
            line = LineString([Point(node_x[i-1], node_y[i-1]) for i in conn_line.tolist()])
            lines.append(line)
        print(lines)

        df_lines = pd.DataFrame(
            data={
                'Num':range(len(lines))
            }
        )
        gdf_lines = gpd.GeoDataFrame(df_lines, geometry=lines)

        gdf_lines_combined = pd.merge(gdf_lines, df_times, how='cross')

        for chan_dset in channel_dsets:
            h5dset = f[chan_dset]
            values = h5dset[:]
            print(values)
            print(len(values))
            print(len(values[0]))

            gdf_lines_combined[chan_dset] = np.array(values).flatten('F')

        print(gdf_lines_combined)

        gdf_lines_combined.to_file(out_filename, layer='Channels', driver='GPKG')


if __name__ == "__main__":
    pd.set_option('display.max_columns', 500)
    # pd.set_option('display.min_rows', 50)
    pd.set_option('display.max_rows', 50)
    pd.set_option('display.width', 300)
    pd.set_option('max_colwidth', 100)

    in_filename = Path(r"D:\models\TUFLOW\test_models\SWMM\ExampleModels\urban\TUFLOW\results\urban_HPC_SWMM_________swmm_ugrid.nc")
    out_filename = in_filename.with_suffix('.gpkg')

    ugrid_to_gpkg(in_filename, out_filename)

