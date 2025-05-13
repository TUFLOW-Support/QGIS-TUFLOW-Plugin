from qgis.PyQt.QtWidgets import QDialog
from qgis.PyQt.QtCore import pyqtSignal


class PlotDialog(QDialog):
    
    resized = pyqtSignal()
    
    def resizeEvent(self, e):
        QDialog.resizeEvent(self, e)
        self.resized.emit()