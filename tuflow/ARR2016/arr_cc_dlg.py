from collections import OrderedDict

from PyQt5.QtWidgets import QDialog
from qgis.core import QgsApplication

from tuflow.forms.arr_cc_scenarios import Ui_ARRCCDialog


class ARRCCDialog(Ui_ARRCCDialog, QDialog):

    def __init__(self, parent=None, value=None):
        super(ARRCCDialog, self).__init__(parent)
        self.setupUi(self)
        self.setValue(value)
        self.pbClose.clicked.connect(self.accept)
        self.btnAdd.setIcon(QgsApplication.getThemeIcon('/symbologyAdd.svg'))
        self.btnAdd.clicked.connect(self.add)
        self.btnRem.setIcon(QgsApplication.getThemeIcon('/symbologyRemove.svg'))
        self.btnRem.clicked.connect(self.rem)
        self.table.cellChanged.connect(self.cellChanged)

    def reject(self):
        self.accept()

    def setValue(self, value):
        if not value:
            return
        self.table.setRowCount(len(value))
        for i, (key, val) in enumerate(value.items()):
            self.table.model().setData(self.table.model().index(i, 0), val['horizon'])
            self.table.model().setData(self.table.model().index(i, 1), val['ssp'])
            self.table.model().setData(self.table.model().index(i, 2), val['base'])
            self.table.model().setData(self.table.model().index(i, 3), val['temp'])
            self.table.model().setData(self.table.model().index(i, 4), key)

    @property
    def value(self):
        value = OrderedDict()
        for irow in range(self.table.rowCount()):
            name = self.table.model().data(self.table.model().index(irow, 4))
            d = {}
            d['horizon'] = self.table.model().data(self.table.model().index(irow, 0))
            d['ssp'] = self.table.model().data(self.table.model().index(irow, 1))
            d['base'] = self.table.model().data(self.table.model().index(irow, 2))
            d['temp'] = self.table.model().data(self.table.model().index(irow, 3))
            value[name] = d
        return value

    @value.setter
    def value(self, value):
        self.setValue(value)

    def add(self):
        i = self.table.rowCount()
        self.table.insertRow(i)
        self.table.model().setData(self.table.model().index(i, 0), 'Long-term')
        self.table.model().setData(self.table.model().index(i, 1), 'SSP2-4.5')
        self.table.model().setData(self.table.model().index(i, 2), 0.)
        self.table.model().setData(self.table.model().index(i, 3), -1.)
        self.updateScenName(i)

    def rem(self):
        self.table.removeRow(self.table.currentRow())

    def cellChanged(self, irow, icol):
        if 1 < icol < 4:
            return
        name = self.table.model().data(self.table.model().index(irow, 4))
        if icol < 4 or not name:
            self.updateScenName(irow)
        else:
            self.makeScenNameUnique(name, irow)

    def updateScenName(self, irow):
        horiz = self.table.model().data(self.table.model().index(irow, 0))
        ssp = self.table.model().data(self.table.model().index(irow, 1))
        name = f'{horiz}_{ssp}'
        self.makeScenNameUnique(name, irow)

    def makeScenNameUnique(self, name, irow):
        existing_names = self.getScenNames(exclude_rows=(irow,))
        if name in existing_names:
            name = f'{name}_1'
            while name in existing_names:
                name = f'{name[:-2]}_{int(name[-1]) + 1}'
        self.table.model().setData(self.table.model().index(irow, 4), name)

    def getScenNames(self, exclude_rows=()):
        scen_names = []
        for irow in range(self.table.rowCount()):
            if irow in exclude_rows:
                continue
            scen_name = self.table.model().data(self.table.model().index(irow, 4))
            scen_names.append(scen_name)
        return scen_names
