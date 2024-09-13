from PyQt5.QtWidgets import QDialog

from tuflow.forms.fv_bc_tide_nc import Ui_ImportFVBCTideDlg
from tuflow.tuflowqgis_library import browse
from tuflow.compatibility_routines import Path

try:
    from netCDF4 import Dataset
except ImportError:
    from tuflow.netCDF4_ import Dataset_ as Dataset


class ImportFVBCTideDlg(QDialog, Ui_ImportFVBCTideDlg):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.btnNS.clicked.connect(lambda: browse(self, 'existing file', 'TUFLOW_Viewer/FVBC_Tide', 'Node String Layer',
                                                  'Shapefile (*.shp *.SHP)', self.leNS))
        self.btnNC.clicked.connect(lambda: browse(self, 'existing file', 'TUFLOW_Viewer/FVBC_Tide', 'NetCDF File',
                                                  'NetCDF (*.nc *.NC)', self.leNC))

    @property
    def node_string_fpath(self):
        return self.leNS.text()

    @property
    def nc_fpath(self):
        return self.leNC.text()

    def accept(self):
        if not self.node_string_fpath:
            self.leNS.setFocus()
            return
        if not self.nc_fpath:
            self.leNC.setFocus()
            return
        super().accept()
