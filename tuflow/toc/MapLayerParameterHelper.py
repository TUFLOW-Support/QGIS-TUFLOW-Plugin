# This file provides a helper class when to use QGisProcessingParameterEnum with map layers which shows the parent
# GeoPackage when necessary
from qgis._core import QgsRasterLayer, QgsMapLayer
from qgis.core import QgsProcessing, QgsVectorLayer, QgsWkbTypes

from tuflow.toc.toc import tuflowqgis_find_layer, findAllVectorLyrsWithGroups


class MapLayerParameterHelper:
    def __init__(self):
        self.mapLayerFilter = None
        self.mapLayerType = None
        self.mapLayerNamesIds = []
        self.mapLayers = []
        self.processingTypeToGeometryType = {
            QgsProcessing.TypeVectorPolygon: QgsWkbTypes.PolygonGeometry,
            QgsProcessing.TypeVectorLine: QgsWkbTypes.LineGeometry,
            QgsProcessing.TypeVectorPoint: QgsWkbTypes.PointGeometry,
        }

    def setMapLayerType(self, mapLayerType: int) -> None:
        self.mapLayerType = mapLayerType

    def setLayerFilter(self, layerFilter) -> None:
        self.mapLayerFilter = layerFilter

    def refreshLayers(self):
        self.mapLayerNamesIds = findAllVectorLyrsWithGroups()
        if self.mapLayerType is not None:
            temp = []
            if self.mapLayerType in [QgsProcessing.TypeVectorAnyGeometry,
                                     QgsProcessing.TypeVectorPolygon,
                                     QgsProcessing.TypeVectorLine,
                                     QgsProcessing.TypeVectorPoint]:
                for lyr_name, lyrid in self.mapLayerNamesIds:
                    layer = tuflowqgis_find_layer(lyrid, search_type='layerid')
                    if isinstance(layer, QgsVectorLayer):
                        if self.mapLayerType == QgsProcessing.TypeVectorAnyGeometry:
                            temp.append((lyr_name, lyrid))
                        elif layer.geometryType() == self.processingTypeToGeometryType[self.mapLayerType]:
                            temp.append((lyr_name, lyrid))
            elif self.mapLayerType in [QgsProcessing.TypeRaster]:
                for lyr_name, lyrid in self.mapLayerNamesIds:
                    layer = tuflowqgis_find_layer(lyrid, search_type='layerid')
                    if isinstance(layer, QgsRasterLayer):
                        temp.append((lyr_name, lyrid))

            self.mapLayerNamesIds = temp

        if self.mapLayerFilter is not None:
            self.mapLayerNamesIds = [x for x in self.mapLayerNamesIds if
                                     self.mapLayerFilter(tuflowqgis_find_layer(x[1], search_type='layerid'))]

    def getMapLayerNames(self) -> list[str]:
        return [x[0] for x in self.mapLayerNamesIds]

    def getLayersFromIndices(self, indices: list[int]) -> list[QgsMapLayer]:
        filtered_list = [self.mapLayerNamesIds[i] for i in indices]
        return [tuflowqgis_find_layer(x[1], search_type='layerid') for x in filtered_list]
