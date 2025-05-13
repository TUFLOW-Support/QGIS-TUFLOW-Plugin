from qgis.PyQt.QtWidgets import QTableWidget, QTableView

from tuflow.bridge_editor.BridgeEditorTable import ComboBoxDelegate, SpinBoxDelegate


class ArrClimateChangeScenTable(QTableWidget):

    def __init__(self, parent=None):
        QTableView.__init__(self, parent)
        self.setItemDelegateForColumn(0, ComboBoxDelegate(self, ['Near-term', 'Medium-term', 'Long-term', '2030',
                                                                 '2040', '2050', '2060', '2070', '2080', '2090', '2100']))
        self.setItemDelegateForColumn(1, ComboBoxDelegate(self, ['SSP1-2.6', 'SSP2-4.5', 'SSP3-7.0', 'SSP5-8.5']))
        self.setItemDelegateForColumn(2, SpinBoxDelegate(self, 0, 99, 0.1, 1))
        self.setItemDelegateForColumn(3, SpinBoxDelegate(self, -1, 99, 0.1, 1))
