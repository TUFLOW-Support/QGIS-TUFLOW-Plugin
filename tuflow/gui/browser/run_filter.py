from qgis.core import QgsDataItem
from qgis.PyQt import QtWidgets

import threading
lock = threading.Lock()


class Singleton(type):

    _instance = None

    def __call__(cls, *args, **kwargs):
        with lock:
            if cls._instance is None:
                cls._instance = super(Singleton, cls).__call__(*args, **kwargs)
            return cls._instance


class RunFilters(metaclass=Singleton):

    def __init__(self):
        self.filters = {}

    def add_filter(self, path: str, run_filter: str):
        self.filters[path] = run_filter

    def clear_filter(self, path: str):
        self.filters.pop(path, None)

    def filter(self, path: str):
        return self.filters.get(path, None)

    @staticmethod
    def populate_children_delayed(data_item: QgsDataItem, path: str):
        from .control_file_browser_item import ControlFileDataItem
        for child in data_item.children():
            if isinstance(child, ControlFileDataItem) and child.path() == path:
                child.populate_children(child)


class RunFilterDialog(QtWidgets.QDialog):

    def __init__(self, parent=None, current_filter=''):
        super().__init__(parent)
        self.setWindowTitle('Add Run Filter')
        self.setModal(True)
        self.resize(400, 100)

        layout = QtWidgets.QVBoxLayout(self)

        self.filter_input = QtWidgets.QLineEdit(self)
        self.filter_input.setText(current_filter)
        layout.addWidget(QtWidgets.QLabel('Enter run filter (e.g. -s1 5m -s2 D01):', self))
        layout.addWidget(self.filter_input)

        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel, self
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
