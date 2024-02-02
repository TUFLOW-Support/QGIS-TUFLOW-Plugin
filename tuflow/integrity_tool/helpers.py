from abc import ABC, abstractmethod

import math
import re

from qgis.core import QgsWkbTypes, NULL, QgsVectorLayer, QgsVectorLayerJoinInfo, QgsUnitTypes
from qgis.utils import iface

from tuflow_swmm.xs_shapes import get_max_width, get_max_area, get_max_height

has_gpd = False
try:
    import geopandas as gpd

    has_gpd = True
except ImportError:
    pass  # defaulted to false

has_logging = False
try:
    from ..gui.logging import Logging
    has_logging = True
except ImportError:
    pass # defaulted to false

class Helper(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def get_feature_id(self, layer, feature):
        pass

    @abstractmethod
    def get_nwk_type(self, feature):
        pass

    @abstractmethod
    def get_feature_attributes(self, layer, feature):
        # returns a dictionary of attributes
        pass


class EstryHelper(Helper):
    def __init__(self):
        pass

    def get_feature_id(self, layer, feature):
        is_gpkg = layer.storageType() == 'GPKG'
        idcol = 1 if is_gpkg else 0
        return feature.attribute(idcol)

    def get_nwk_type(self, feature):
        gpkg_offset = 0
        if feature.fields().at(0).name() == 'fid':
            # Assume it is a GeoPackage
            gpkg_offset = 1
        return feature.attribute(1+gpkg_offset)

    def get_feature_attributes(self, layer, feature):
        #import pydevd_pycharm
        #pydevd_pycharm.settrace('localhost', port=53110, stdoutToServer=True, stderrToServer=True)
        # returns a dictionary of attributes
        gpkg_offset = 0
        if feature.fields().at(0).name() == 'fid':
            # Assume it is a GeoPackage
            gpkg_offset = 1

        feat_type = feature.attribute(1 + gpkg_offset)

        invertUs = feature.attribute(6 + gpkg_offset)
        invertDs = feature.attribute(7 + gpkg_offset)
        if feat_type and feat_type.lower()[0] == 'b':
            invertDs = invertUs
        if invertUs == NULL:
            invertUs = -99999
        if invertDs == NULL:
            invertDs = -99999

        # size
        width = feature.attribute(13 + gpkg_offset)
        if width == NULL:
            width = 0
        height = feature.attribute(14 + gpkg_offset)
        if height == NULL:
            height = 0
        numberOf = feature.attribute(15 + gpkg_offset)
        if numberOf == 0 or numberOf == NULL:
            numberOf = 1
        height_ = width if feat_type.lower()[0] == 'c' else height
        length = feature.attribute(4 + gpkg_offset) if feature.attribute(4 + gpkg_offset) != NULL \
                                                       and feature.attribute(4 + gpkg_offset) > 0. \
            else feature.geometry().length()

        area = 0.0
        if feat_type.upper() == 'R':
            area = numberOf * width * height
        elif feat_type.upper() == 'C':
            area = numberOf * math.pi * (width / 2.0) ** 2

        atts = {
            'type': feat_type,
            'invertUs': invertUs,
            'invertDs': invertDs,
            'width': width,
            'height': height,
            'numberOf': numberOf,
            'height_': height_,
            'length': length,
            'area': area,
        }
        return atts


class SwmmHelper(Helper):
    def __init__(self):
        # map of dataframes by layer id
        self.curves = {}
    def __del__(self):
        pass

    def get_curve_data(self, layer, feature):
        # See if we cached the dataframe
        df = None
        if layer.id() in self.curves:
            df = self.curves[layer.id()]
        else:
            if layer.storageType() != 'GPKG':
                if has_logging:
                    Logging.error('SWMM network data must be in a valid TUFLOW GeoPackage file')
                else:
                    print('SWMM network data must be in a valid TUFLOW GeoPackage file')
                return
            if not has_gpd:
                message = (
                    'This tool requires geopandas: to install please follow instructions on the following webpage: '
                    'https://wiki.tuflow.com/QGIS_Intallation_with_OSGeo4W')
                if has_logging:
                    Logging.error(message)
                else:
                    print(message)
                return

            filename, layername = str(layer.dataProvider().uri()).split('|')
            filename = filename.split(':', maxsplit=1)[1].strip()
            gdf_curves = gpd.read_file(filename, layer='Curves--Curves')
            gdf_curves['Type'] = gdf_curves['Type'].fillna(method='ffill')
            gdf_curves = gdf_curves[gdf_curves['Type'] == 'SHAPE']
            df = gdf_curves[['Name', 'xval', 'yval']]
            self.curves[layer.id()] = df

        if df is None:
            message = (
                'Error loading custom curve data. Contact support.'
            )
            Logging.error(message)

        return df[df['Name'] == feature['xsec_Curve']]

    def get_nwk_type(self, feature):
        return feature.attribute('xsec_XsecType') if 'xsec_XsecType' in feature.attributeMap() else ''
    def get_feature_id(self, layer, feature):
        return feature.attribute('Name')

    def get_feature_attributes(self, layer, feature):
        if iface is not None:
            use_customary_units = iface.mapCanvas().mapUnits() == QgsUnitTypes.DistanceFeet
        else:
            use_customary_units = False # Happens in unit tests
        # returns a dictionary of attributes
        # print(feature.attributeMap())

        # Default values
        ftype = None
        invertUs = -99999
        invertDs = -99999
        invertOffsetUs = 0.0
        invertOffsetDs = 0.0
        width = 0.0
        height = 0.0
        area = 0.0
        length = 0.0
        numberOf = 1

        # For common types return the ESTRY type abbreviation

        if feature.geometry().type() == QgsWkbTypes.LineGeometry:
            length = feature.attribute('Length')

            ftype = feature.attribute('xsec_XsecType')
            if ftype == 'CIRCULAR':
                ftype = 'c'
            elif ftype in {'RECT_OPEN', 'RECT_CLOSED'}:
                ftype = 'r'

            invertOffsetUs = feature.attribute('InOffset')
            invertOffsetDs = feature.attribute('OutOffset')

            if type(invertOffsetUs) == 'QVariant':
                invertOffsetUs = invertOffsetUs.toFloat() if not invertOffsetUs.isNull() else None
            if type(invertOffsetDs) == 'QVariant':
                invertOffsetDs = invertOffsetDs.toFloat() if not invertOffsetDs.isNull() else None

            if feature.attribute('xsec_XsecType'):
                if feature.attribute('xsec_XsecType').upper() == 'CUSTOM':
                    df = self.get_curve_data(layer, feature)

                    multiplier = feature['xsec_Geom1']
                    width = df['yval'].max()*multiplier
                    height = df['xval'].max()*multiplier
                    # compute area
                    avg_widths = ((df['yval']+df['yval'].shift(1))*0.5)[1:]
                    heights = (df['xval'] - df['xval'].shift(1))[1:]
                    area = sum(avg_widths*heights)*multiplier**2.0
                else:
                    width = get_max_width(feature.attribute('xsec_XsecType'),
                                          use_customary_units,
                                          feature.attribute('xsec_Geom1'),
                                          feature.attribute('xsec_Geom2'),
                                          feature.attribute('xsec_Geom3'),
                                          feature.attribute('xsec_Geom4'))

                    height = get_max_height(feature.attribute('xsec_XsecType'),
                                            use_customary_units,
                                            feature.attribute('xsec_Geom1'),
                                            feature.attribute('xsec_Geom2'),
                                            feature.attribute('xsec_Geom3'),
                                            feature.attribute('xsec_Geom4'))

                    area = get_max_area(feature.attribute('xsec_XsecType'),
                                        use_customary_units,
                                        feature.attribute('xsec_Geom1'),
                                        feature.attribute('xsec_Geom2'),
                                        feature.attribute('xsec_Geom3'),
                                        feature.attribute('xsec_Geom4'))

                numberOf = feature.attribute('xsec_Barrels')

        else:
            # Must be a point type
            ftype = 'Node'
            invertValue = feature.attribute('Elev')
            invertValue = float(invertValue) if invertValue is not None else None
            invertUs = invertDs = invertValue

        atts = {
            'type': ftype,
            'invertUs': invertUs,
            'invertDs': invertDs,
            'invertOffsetUs': invertOffsetUs,
            'invertOffsetDs': invertOffsetDs,
            'width': width,
            'height': height,
            'numberOf': numberOf,
            'height_': height,
            'length': length,
            'area': area,
        }
        return atts

    #def CombineLinksXsecs(self, lay_conduits, lay_xsecs):
    #    join_info = QgsVectorLayerJoinInfo()
    #    join_info.setJoinLayer(lay_xsecs)
    #    join_info.setJoinFieldName('Link')
    #    join_info.setPrefix('xsec_')
    #    join_info.setTargetFieldName('Name')
    #    joined = lay_conduits.addJoin(join_info)
    #    if not joined:
    #        raise ValueError("Unable to join Conduit and XSection Layers")
    #    self.joins.append((lay_conduits, lay_xsecs.id()))
