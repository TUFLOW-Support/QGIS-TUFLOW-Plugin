# RDJ - I started this file intending to add menu options for TUFLOW-SWMM. However, I put it on hold. This code
# is here if I decide to investigate later

from qgis.gui import QgsLayerTreeViewMenuProvider

#import pydevd_pycharm
#pydevd_pycharm.settrace('localhost', port=53110, stdoutToServer=True, stderrToServer=True)

class SwmmMenuProvider(QgsLayerTreeViewMenuProvider):
    def __init__(self, view):
        QgsLayerTreeViewMenuProvider.__init__(self)
        self.view = view
        self.defaultActions = view.defaultActions()

    def createContextMenu(self):
        m = super(SwmmMenuProvider, self).createContextMenu()

        return m
        # if not self.view.currentLayer():
        #     return None
        # m = QMenu()
        # m.addAction("Open layer properties", self.openLayerProperties)
        # m.addSeparator()
        #
        # if type(self.view.currentLayer()) == QgsVectorLayer:
        #     m.addAction("Show Feature Count", self.featureCount)
        #     m.addAction("Another vector-specific action", self.vectorAction)
        # elif type(self.view.currentLayer()) == QgsRasterLayer:
        #     m.addAction("Zoom 100%", self.zoom100)
        #     m.addAction("Another raster-specific action", self.rasterAction)
        # return m

    def openLayerProperties(self):
        iface.showLayerProperties(self.view.currentLayer())

    def featureCount(self):
        self.defaultActions.actionShowFeatureCount().trigger()

    def vectorAction(self):
        pass

class tuflowswmm_menu:
    def __init__(self, iface):
        self.iface = iface
        pass

    def initGui(self):
        pass # TODO