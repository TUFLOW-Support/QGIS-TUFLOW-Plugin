from pathlib import Path

from qgis.PyQt.QtCore import QSettings
from qgis.PyQt.QtWidgets import QDialog, QFileDialog
from qgis.core import QgsApplication

if not QSettings().value('TUFLOW/TestCase', False, type=bool):
    from ...forms.FMResImport_Dialog import Ui_FMResDialog
else:
    from tuflow.forms.FMResImport_Dialog import Ui_FMResDialog


class FMImportDialog(QDialog, Ui_FMResDialog):

    def __init__(self, gxy: str | Path, parent = None):
        super().__init__(parent)
        self.setupUi(self)
        self.setup_buttons()
        self.gxy = str(gxy)
        self.start_dir = str(Path(gxy).parent)

        self.btnRemCSV.clicked.connect(self.remove_csv)
        self.pbOK.clicked.connect(self.accept)
        self.pbCancel.clicked.connect(self.reject)

        self.btnBrowseGXY.clicked.connect(self.browse_gxy)
        self.btnBrowseSectionData.clicked.connect(self.browse_dat)
        self.btnBrowseCSV.clicked.connect(self.browse_results)

    @property
    def gxy(self) -> str:
        return self.leGXY.text()

    @gxy.setter
    def gxy(self, val: str):
        self.leGXY.setText(val)

    @property
    def dat(self) -> str:
        return self.leSectionData.text()

    @dat.setter
    def dat(self, val: str):
        self.leSectionData.setText(val)

    @property
    def results(self) -> list[str]:
        return [self.lwCSVFiles.item(x).text() for x in range(self.lwCSVFiles.count())]

    @results.setter
    def results(self, val: list[str]):
        self.lwCSVFiles.clear()
        _ = [self.lwCSVFiles.addItem(x) for x in val]

    def browse_gxy(self, *args):
        file, _ = QFileDialog.getOpenFileName(self, 'GXY File', self.start_dir, 'GXY (*.gxy)')
        if file:
            self.gxy = file

    def browse_dat(self, *args):
        file, _ = QFileDialog.getOpenFileName(self, 'DAT File', self.start_dir, 'DAT (*.dat)')
        if file:
            self.dat = file

    def browse_results(self, *args):
        files, _ = QFileDialog.getOpenFileNames(self, 'Result Files', self.start_dir, 'CSV, ZZN (*.csv *.zzn);;CSV (*.csv);;ZZN (*.zzn)')
        if files:
            self.results = self.results + files

    def setup_buttons(self):
        folIcon = QgsApplication.getThemeIcon('/mActionFileOpen.svg')
        remIcon = QgsApplication.getThemeIcon('/symbologyRemove.svg')

        # browse icon
        self.btnBrowseGXY.setIcon(folIcon)
        self.btnBrowseSectionData.setIcon(folIcon)
        self.btnBrowseCSV.setIcon(folIcon)

        # add / remove icons
        self.btnRemCSV.setIcon(remIcon)

        # tooltips
        self.btnBrowseGXY.setToolTip("Browse to GXY file location")
        self.btnBrowseSectionData.setToolTip("Browse to section (.DAT) file location")
        self.btnBrowseCSV.setToolTip("Browse to CSV file location")
        self.btnRemCSV.setToolTip("Remove selected CSV from list")

    def remove_csv(self):
        selected_items = self.lwCSVFiles.selectedItems()
        selected_indexes = [x for x in range(self.lwCSVFiles.count()) if self.lwCSVFiles.item(x) in selected_items]
        for i in reversed(selected_indexes):
            self.lwCSVFiles.takeItem(i)
