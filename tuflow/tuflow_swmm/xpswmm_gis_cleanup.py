import geopandas as gpd
from pathlib import Path
try:
    from shapely.ops import snap
    has_shapely = True
except ImportError:
    has_shapely = False

from tuflow.tuflow_swmm.gis_list_layers import get_gis_layers
from tuflow.tuflow_swmm.swmm_processing_feedback import ScreenProcessingFeedback


def bc_layer_processing(bc_filename: str,
                        bc_layername: str,
                        swmm_gpkg_filename: str,
                        out_bc_filename: str,
                        out_bc_layername: str,
                        feedback=ScreenProcessingFeedback()) -> bool:
    """
    Snaps boundary condition layers to SWMM node layers.
    """
    if not has_shapely:
        feedback.reportError('Shapely not installed and is required for function: bc_layer_processing().',
                             fatalError=True)

    bc_path = Path(bc_filename)
    if not bc_path.exists():
        feedback.reportError(f'BC file does not exist: {bc_filename}', fatalError=True)
        return False

    if bc_layername is not None and\
        bc_layername.lower() not in [x.lower() for x in get_gis_layers(bc_filename)]:
        feedback.reportError(f'BC layer "{bc_layername}" does not exist in {bc_filename}',
                             fatalError=True)
        return False

    gdf_bc = gpd.read_file(bc_filename, layer=bc_layername)

    if gdf_bc.empty:
        return False

    # See if we are a point type
    if gdf_bc['geometry'].geom_type[0] == 'Point':
        # See if we have any non SX boundaries
        gdf_bc_non_sx = gdf_bc[~gdf_bc['Type'].str.upper().str.contains('SX')]
        if len(gdf_bc_non_sx) == 0:
            return False

        gdf_bc_non_sx.to_file(out_bc_filename,
                              layer=out_bc_layername)
    elif gdf_bc['geometry'].geom_type[0] == 'LineString':
        # Snap bc layer to node layers
        node_layers = [
            'Nodes--Junctions',
            'Nodes--Storage',
            'Nodes--Outfalls',
        ]
        for node_layer in node_layers:
            if node_layer not in get_gis_layers(swmm_gpkg_filename):
                continue
            gdf_node = gpd.read_file(swmm_gpkg_filename, layer=node_layer)

            for node_geom in gdf_node['geometry']:
                gdf_bc['geometry'] = gdf_bc['geometry'].apply(
                    lambda x: snap(x, node_geom, 0.1)
                )

        gdf_bc.to_file(out_bc_filename,
                       layer=out_bc_layername)

    return True
