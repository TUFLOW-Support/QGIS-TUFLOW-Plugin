from PyQt5.QtWidgets import QDialog
from PyQt5.QtCore import pyqtSignal


class PlotDialog(QDialog):
    
    resized = pyqtSignal()
    
    def resizeEvent(self, e):
        QDialog.resizeEvent(self, e)
        self.resized.emit()