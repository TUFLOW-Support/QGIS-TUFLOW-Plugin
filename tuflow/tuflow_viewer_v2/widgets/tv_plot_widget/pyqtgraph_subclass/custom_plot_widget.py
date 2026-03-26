from qgis.PyQt.QtCore import QSettings

if not QSettings().value('TUFLOW/TestCase', False, type=bool):
    from .....pyqtgraph import PlotWidget
else:
    from tuflow.pyqtgraph import PlotWidget

from .custom_view_box import CustomViewBox


class CustomPlotWidget(PlotWidget):

    def __init__(self, parent=None, background='default', plotItem=None, **kargs):
        view_box = CustomViewBox(enableMenu=True)
        super().__init__(parent, background, plotItem, viewBox=view_box, **kargs)

    def messageBar(self):
        if self.parent() and hasattr(self.parent(), 'messageBar'):
            return self.parent().messageBar()
