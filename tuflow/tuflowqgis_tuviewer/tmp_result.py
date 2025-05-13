import shutil
from typing import TYPE_CHECKING
import tempfile

from qgis.PyQt.QtWidgets import QMessageBox, QCheckBox, QWidget

from ..compatibility_routines import QT_MESSAGE_BOX_YES, Path, QT_MESSAGE_BOX_QUESTION, QT_MESSAGE_BOX_NO
from ..gui import Logging
from ..utils import copy_file_with_progbar

if TYPE_CHECKING:
    from .tuflowqgis_tuoptions import TuOptions


PREFIX = 'TUFLOW-res-copy-'


class TmpResult:
    """Class for handling the temporary copy of a result file."""

    def __init__(self, fpath: str) -> None:
        self.fpath = Path(fpath)
        self.tmp_dir = None
        self.tmp_file = None
        self.other_files = []  # just in case there is still a dinosaur out there using .dat files and .sup
        self.for_cleaning = []
        self.valid = self.init()

    @staticmethod
    def clear_cache():
        """Clear the temporary result directory."""
        files = []
        for dir_ in Path(tempfile.gettempdir()).glob('{0}*'.format(PREFIX)):
            if dir_.is_dir():
                try:
                    shutil.rmtree(dir_)
                except OSError:
                    files.append(dir_)
        return files

    @staticmethod
    def get_temp_dir(name: str, force_new: bool = False) -> Path:
        """Get the temporary directory for the result file. Check if it already exists."""
        if not force_new:
            for dir_ in Path(tempfile.gettempdir()).glob('{0}*-{1}'.format(PREFIX, name)):
                if dir_.is_dir():
                    return dir_
        return Path(tempfile.mkdtemp(prefix=PREFIX, suffix='-{0}'.format(name)))

    @staticmethod
    def ask_copy_res_dlg(parent: QWidget, options: 'TuOptions' = None) -> bool:
        """Create a dialog box to ask user if they want to create a temporary directory."""
        dlg_ = QMessageBox(QT_MESSAGE_BOX_QUESTION,
                           'Copy Result',
                           'Do you want to create a temporary copy of the results before loading\n'
                           '(This is recommended only if loading results from a running simulation)',
                           QT_MESSAGE_BOX_YES | QT_MESSAGE_BOX_NO,
                           parent)
        if options:
            cb = QCheckBox()
            cb.setText('Don\'t ask again (remember response)')
            dlg_.setCheckBox(cb)
        res = dlg_.exec() == QT_MESSAGE_BOX_YES
        if options and cb.isChecked():
            options.show_copy_mesh_dlg = False
            options.copy_mesh = res
        return res

    def init(self, force_new_loc: bool = False) -> bool:
        """Initialise the temporary result directory."""
        if self.fpath.is_file() and not self.fpath.exists():
            return False
        self.tmp_dir = self.get_temp_dir(self.fpath.stem, force_new_loc)
        self.tmp_file = self.tmp_dir / self.fpath.name
        if not self.tmp_dir.exists():
            return False
        return True

    @staticmethod
    def up_to_date(file: Path, tmp_file: Path) -> bool:
        """Check if the result file needs updating."""
        if file.is_file():
            return tmp_file.exists() and tmp_file.stat().st_size > 0 and tmp_file.stat().st_mtime >= file.stat().st_mtime
        return True

    def copy(self, parent, file = None) -> Path:
        """Copy the result file to the temporary directory."""
        # check if a file already exists and has a size greater than 0 and an earlier modified time
        if file:
            file_ = Path(file)
            tmp_file = self.tmp_dir / file_.name
            if file not in self.other_files:
                self.other_files.append(file_)
        else:
            file_ = self.fpath
            tmp_file = self.tmp_file

        if self.up_to_date(file_, tmp_file):
            return tmp_file

        copy_file_with_progbar(file_, tmp_file, parent)
        return tmp_file

    def update_method(self) -> str:
        """
        Returns the update method:
            REPLACE: overwrite the copied results
            RETARGET: copy new results to new location and retarget datasource
        """
        if self.fpath.suffix.upper() in ['.NC']:
            return 'RETARGET'
        return 'REPLACE'

    def update(self, parent) -> None:
        """Re-copy files if save date is later."""
        if self.update_method() == 'RETARGET' and not self.up_to_date(self.fpath, self.tmp_file):
            if self.tmp_dir not in self.for_cleaning:
                self.for_cleaning.append(self.tmp_dir)
            success = self.init(True)  # re-initialise with new location
            if not success:
                return
        self.copy(parent)
        for file in self.other_files:
            if self.update_method() == 'RETARGET':  # should not get here, only netcdf req. retarget method
                continue
            self.copy(parent, file)

    def datasets(self) -> list[str]:
        return [str(self.tmp_file)] + [str(self.tmp_dir / x) for x in self.other_files]

    def clear_result_cache(self, tmp_dir: Path = None) -> None:
        """Clear the temporary result directory."""
        if tmp_dir is None:
            tmp_dir = self.tmp_dir
        try:
            shutil.rmtree(tmp_dir)
        except OSError:
            pass

    def clean(self):
        for tmp_dir in self.for_cleaning[:]:
            self.clear_result_cache(tmp_dir)
            if not tmp_dir.exists():
                self.for_cleaning.remove(tmp_dir)
