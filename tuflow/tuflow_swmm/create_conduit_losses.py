has_gpd = False
try:
    import pandas as pd
    import geopandas as gpd

    has_gpd = True
except ImportError:
    pass  # defaulted to false

import numpy as np
try:
    from shapely.geometry import Point
    has_shapely = True
except ImportError:
    has_shapely = False
    Point = 'Point'

from qgis.core import (QgsFeature,
                       QgsGeometry,
                       QgsPoint)

from tuflow.tuflow_swmm.swmm_processing_feedback import ScreenProcessingFeedback
from tuflow.tuflow_swmm.xs_shapes import is_open_channel


def create_loss_feature(row,
                        new_layer,
                        features_to_add,
                        up_entry_loss,
                        other_entry_loss,
                        down_exit_loss,
                        other_exit_loss,
                        feedback):
    # feedback.pushInfo(row['Name'])
    if not has_shapely:
        feedback.reportError('Shapely not installed and is required for function: create_loss_feature().',
                             fatalError=True)

    new_feat = QgsFeature(new_layer.fields())
    new_geom = QgsGeometry.fromPolyline(
        [QgsPoint(x, y) for x, y in row['polylines'].coords]
    )
    validate_errors = new_geom.validateGeometry()
    if validate_errors:
        feedback.reportError(f'Errors found converting {row["Name"]}: {validate_errors}')
    new_feat.setGeometry(new_geom)

    if not row['HasUpstream'] and \
            str(row['Inlet_us']) == 'nan':
        new_feat.setAttribute('losses_Kentry', up_entry_loss)
    else:
        new_feat.setAttribute('losses_Kentry', other_entry_loss)

    if not row['HasDownstream'] and \
            str(row['Inlet_ds']) == 'nan':
        new_feat.setAttribute('losses_Kexit', down_exit_loss)
    else:
        new_feat.setAttribute('losses_Kexit', other_exit_loss)

    new_feat.setAttribute('losses_Kavg', 0.0)

    atts_to_copy = [
        'Name',
        'From Node',
        'To Node',
        'Length',
        'Roughness',
        'InOffset',
        'OutOffset',
        'InitFlow',
        'MaxFlow',
        'xsec_XsecType',
        'xsec_Geom1',
        'xsec_Geom2',
        'xsec_Geom3',
        'xsec_Geom4',
        'xsec_Barrels',
        'xsec_Culvert',
        'xsec_Curve',
        'xsec_Tsect',
        'xsec_Street',
    ]
    for att in atts_to_copy:
        new_feat.setAttribute(att, row[att])

    features_to_add.append(new_feat)


# Create conduit losses for SWMM Networks
#   First conduit has entrance losses.
#   Last conduit has exit losses.
#   Losses are ignored if connected to an inlet (if provided).
#   Perhaps make more sophisticated in the future looking at adjacent sizes.
def get_conduit_loss_info(
        input_conduit_source,
        input_inlet_layers,
        feedback=ScreenProcessingFeedback()):
    if not has_shapely:
        feedback.reportError('Shapely not installed and is required for function: get_conduit_loss_info().',
                             fatalError=True)

    try:
        if not has_gpd:
            message = ('This tool requires geopandas: to install please follow instructions on the following webpage: '
                       'https://wiki.tuflow.com/QGIS_Intallation_with_OSGeo4W')
            feedback.reportError(message)
            return
        # t0 = timeit.default_timer()

        # convert conduit layer and inlets layer (if exists to gdfs)
        gdf_conduits = gpd.GeoDataFrame.from_features(input_conduit_source.getFeatures())

        gdf_inlets = None
        if input_inlet_layers:
            gdfs_inlets = [gpd.GeoDataFrame.from_features(x.getFeatures()) for x in input_inlet_layers]
            gdf_inlets = pd.concat(gdfs_inlets, axis=0)

        # gdf_inlets = gpd.GeoDataFrame.from_features(input_inlet_source.getFeatures())

        #if 'Inlet' not in gdf_inlets:
        #    feedback.reportError('Invalid inlet usage layer: no column named "Inlet"', True)
        #    raise ValueError('Invalid inlet usage layer')

        gdf_conduits['polylines'] = gdf_conduits['geometry']

        # Handle upstream point
        gdf_conduits['first_point'] = gdf_conduits.geometry.apply(
            lambda x: Point(np.array(x.coords)[0]))
        gdf_conduits['geometry'] = gdf_conduits['first_point']

        if gdf_inlets is not None:
            gdf_joined = gpd.sjoin(gdf_conduits,
                                   gdf_inlets[['geometry', 'Inlet']],
                                   how='left',
                                   predicate='intersects',
                                   rsuffix='_us')
            gdf_joined['Inlet_us'] = gdf_joined['Inlet']
            gdf_joined = gdf_joined.drop(columns=['Inlet'])
        else:
            gdf_joined = gdf_conduits
            gdf_joined['Inlet_us'] = 'nan'
        gdf_joined = gdf_joined.drop_duplicates(subset='Name')

        # Handle downstream point
        gdf_joined['last_point'] = gdf_joined['polylines'].apply(
            lambda x: Point(np.array(x.coords)[-1]))
        gdf_joined['geometry'] = gdf_joined['last_point']
        if gdf_inlets is not None:
            gdf_joined = gpd.sjoin(gdf_joined,
                                   gdf_inlets[['geometry', 'Inlet']],
                                   how='left',
                                   predicate='intersects',
                                   rsuffix='_ds')
            gdf_joined['Inlet_ds'] = gdf_joined['Inlet']
            gdf_joined = gdf_joined.drop(columns={'Inlet'})
            gdf_joined = gdf_joined.drop_duplicates(subset='Name')
        else:
            gdf_joined['Inlet_ds'] = 'nan'

        gdf2 = gdf_joined.merge(gdf_joined[['From Node']],
                                how='left',
                                left_on='To Node',
                                right_on='From Node',
                                suffixes=(None, '_down'))
        gdf2['HasDownstream'] = ~gdf2['From Node_down'].isnull()

        gdf3 = gdf2.merge(gdf2[['To Node']],
                          how='left',
                          left_on='From Node',
                          right_on='To Node',
                          suffixes=(None, '_up'))
        gdf3['HasUpstream'] = ~gdf3['To Node_up'].isnull()

        gdf3 = gdf3.drop_duplicates(subset='Name')

        # See if the conduit is an open channel
        gdf3['IsOpenChannel'] = gdf3['xsec_XsecType'].apply(is_open_channel)

        return gdf3
    except Exception as e:
        feedback.reportError(f'ERROR processing conduit losses: {str(e)}')

    return None
