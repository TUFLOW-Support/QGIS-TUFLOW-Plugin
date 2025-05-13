# https://stackoverflow.com/questions/29967487/get-progress-back-from-shutil-file-copy-thread
import os
import shutil
from time import sleep

from qgis.PyQt.QtCore import QObject, QThread, pyqtSignal
from qgis.PyQt.QtWidgets import QWidget, QVBoxLayout, QProgressBar, QDialog

# differs from shutil.COPY_BUFSIZE on platforms != Windows
READINTO_BUFSIZE = 1024 * 1024



from ..compatibility_routines import QT_DIALOG_REJECTED


def copy_file_with_progbar(src, dst, parent):
    """
    Copies file with a progress bar.
    Assumes src, dst are not special files (sockets, devices, ...) or anything like that.
    """
    src, dst = str(src), str(dst)  # could be Path object
    size = os.stat(src).st_size
    # To prevent overflows store in KB and make sure it is at least one
    size = max(size // 1024, 1)
    prog_bar = CopyFileProgressBar(src, dst, 0, size, parent)
    if prog_bar.exec() == QT_DIALOG_REJECTED:
        raise RuntimeError(prog_bar.errmsg)
    prog_bar.deleteLater()


class CopyFileProgressBar(QDialog):

    def __init__(self, src: str, dst: str, min_: int, max_: int, parent=None):
        super().__init__(parent)
        self.init_gui(min_, max_)
        self.errmsg = ''
        self.copy = CopyFile(src, dst)
        self.copy.updated.connect(self.set_progress)
        self.copy.finished.connect(self.set_finished)
        self.copy.error.connect(self.set_error)
        self.thread = QThread()
        self.copy.moveToThread(self.thread)
        self.thread.started.connect(self.copy.copy)

    def exec(self):
        self.thread.start()
        super().exec()

    def init_gui(self, min_: int, max_: int):
        self.setWindowTitle('Copying file...')
        self.layout = QVBoxLayout()
        self.prog_bar = QProgressBar()
        self.prog_bar.setRange(min_, max_)
        self.layout.addWidget(self.prog_bar)
        self.setLayout(self.layout)
        self.finished_ = False

    def set_progress(self, prog: int) -> None:
        self.prog_bar.setValue(prog)

    def set_finished(self):
        self.clean_up()
        self.accept()

    def set_error(self, e: Exception):
        self.errmsg = str(e)
        self.clean_up()
        self.reject()

    def clean_up(self):
        self.thread.quit()
        self.finished_ = True


class CopyFile(QObject):

    updated = pyqtSignal(int)
    finished = pyqtSignal()
    error = pyqtSignal(Exception)

    def __init__(self, src: str, dst: str, parent: QWidget = None):
        super().__init__(parent)
        self.src = str(src)
        self.dst = str(dst)

    def copy(self):
        def callback(copied):
            self.updated.emit(copied)
        with open(self.src, 'rb') as fsrc:
            with open(self.dst, 'wb') as fdst:
                try:
                    self.copyfileobj(fsrc, fdst, callback, READINTO_BUFSIZE)
                except Exception as e:
                    self.error.emit(e)
                    return
        self.finished.emit()

    def copyfileobj(self, fsrc, fdst, callback, length=0):
        try:
            # check for optimisation opportunity
            if "b" in fsrc.mode and "b" in fdst.mode and fsrc.readinto:
                return self._copyfileobj_readinto(fsrc, fdst, callback, length)
        except AttributeError:
            # one or both file objects do not support a .mode or .readinto attribute
            pass

        if not length:
            length = shutil.COPY_BUFSIZE

        fsrc_read = fsrc.read
        fdst_write = fdst.write

        copied = 0
        while True:
            buf = fsrc_read(length)
            if not buf:
                break
            fdst_write(buf)
            copied += len(buf) // 1024
            callback(copied)


    def _copyfileobj_readinto(self, fsrc, fdst, callback, length=0):
        """readinto()/memoryview() based variant of copyfileobj().
        *fsrc* must support readinto() method and both files must be
        open in binary mode.
        """
        fsrc_readinto = fsrc.readinto
        fdst_write = fdst.write

        if not length:
            try:
                file_size = os.stat(fsrc.fileno()).st_size
            except OSError:
                file_size = READINTO_BUFSIZE
            length = min(file_size, READINTO_BUFSIZE)

        copied = 0
        with memoryview(bytearray(length)) as mv:
            while True:
                n = fsrc_readinto(mv)
                if not n:
                    print('break')
                    break
                elif n < length:
                    with mv[:n] as smv:
                        fdst.write(smv)
                else:
                    fdst_write(mv)
                copied += n // 1024
                callback(copied)
