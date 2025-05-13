import re
from qgis.PyQt.QtCore import QObject, pyqtSignal
from qgis.PyQt.QtWidgets import QDialog
from qgis.core import QgsVectorLayer, NULL, QgsWkbTypes, QgsProject, QgsFeature
from ..forms.ui_NullGeometryDialog import Ui_NullGeometryConfirmation


class NullGeometryDialog(QDialog, Ui_NullGeometryConfirmation):

    def __init__(self, parent, html):
        QDialog.__init__(self, parent)
        self.setupUi(self)
        self.teNullGeometry.setHtml(html)
        self.confirmDelete = False

        self.pbConfirm.clicked.connect(self.confirm)
        self.pbCancel.clicked.connect(self.reject)

    def confirm(self):
        self.confirmDelete = True
        self.accept()


class NullGeometry(QObject):

    updated = pyqtSignal()
    finished = pyqtSignal(QObject)

    def __init__(self, iface=None):
        QObject.__init__(self)
        self.iface = iface
        self.gis_layers = []
        self.null_geom_count = 0
        self.gis_layers_containing_null = {}

        self.errMessage = None
        self.errStatus = None

        self.tmpLyrs = []
        self.tmplyr2oldlyr = {}

    def checkForNullGeometries(self, gis_layers, **kwargs):
        self.gis_layers = gis_layers[:]

        # turn off write duplicate errors if this is a collection tool rather than a check
        write_null_geom_errors = kwargs['write_null_geom_errors'] if 'write_null_geom_errors' in kwargs else True

        for gis_layer in self.gis_layers:
            if gis_layer is None or type(gis_layer) is not QgsVectorLayer or not gis_layer.isValid() or gis_layer.geometryType() == QgsWkbTypes.NullGeometry:
                continue

            is_gpkg = gis_layer.storageType() == 'GPKG'
            iid = 1 if is_gpkg else 0

            for feat in gis_layer.getFeatures():
                if feat.geometry().isEmpty():
                    id_ = feat[iid] if feat.fields().count() >= iid + 1 and feat[iid] != NULL and feat[iid].strip() else 'Empty ID'
                    self.null_geom_count += 1
                    if gis_layer.name() not in self.gis_layers_containing_null:
                        self.gis_layers_containing_null[gis_layer.name()] = []
                    self.gis_layers_containing_null[gis_layer.name()].append(id_)

                self.updated.emit()

        if self.null_geom_count and write_null_geom_errors:
            self.errMessage = '{0} feature(s) with empty/null geometry found in input layer(s). Null geometry can cause ' \
                              'errors when running the current tool. ' \
                              'Use \'Empty Geometry\' tool to automate their removal first.'.format(self.null_geom_count)
            self.errStatus = 'Error: empty/null geometry found in input layer(s).'

        self.finished.emit(self)

    def deleteNullGeometry(self):
        layers = [x for x in self.gis_layers if x.name() in self.gis_layers_containing_null]

        for layer in layers:
            if layer.geometryType() == QgsWkbTypes.PointGeometry:
                uri = 'point'
            elif layer.geometryType() == QgsWkbTypes.LineGeometry:
                uri = 'linestring'
            else:
                for _ in range(layer.featureCount()):
                    self.updated.emit()
                continue

            uri = '{0}?crs={1}'.format(uri, layer.crs().authid())

            lyrnames = [x.name() for _, x in QgsProject.instance().mapLayers().items()]
            cnt = 1
            tempLyrName = '{0}_EG{1}'.format(layer.name(), cnt)
            while tempLyrName in lyrnames:
                cnt += 1
                tempLyrName = '{0}_EG{1}'.format(layer.name(), cnt)

            out_lyr = QgsVectorLayer(uri, tempLyrName, 'memory')
            if not out_lyr.isValid():
                self.errMessage = 'Unexpected error occurred creating temporary output layer ' \
                                  ' for {0}'.format(layer.name())
                self.errStatus = 'Error: Unexpected error occurred creating output layer'
                self.finised.emit(self)
                return
            self.tmpLyrs.append(out_lyr)
            self.tmplyr2oldlyr[out_lyr.id()] = layer.id()

            fields = layer.fields()
            if layer.storageType() == 'GPKG':  # temp layer is not a GPKG (ignore fid)
                i = fields.indexFromName('fid')
                fields.remove(i)
            out_lyr.dataProvider().addAttributes(fields)
            out_lyr.updateFields()

            if layer.storageType() == 'GPKG':
                feats = []
                for f in layer.getFeatures():
                    if not f.geometry().isEmpty():
                        f_ = QgsFeature(f)
                        f_.deleteAttribute(i)
                        feats.append(f_)
                out_lyr.dataProvider().addFeatures(feats)
            else:
                out_lyr.dataProvider().addFeatures([x for x in layer.getFeatures() if not x.geometry().isEmpty()])
            out_lyr.updateExtents()

            for _ in range(layer.featureCount()):
                self.updated.emit()

            QgsProject.instance().addMapLayer(out_lyr)

        self.finished.emit(self)
