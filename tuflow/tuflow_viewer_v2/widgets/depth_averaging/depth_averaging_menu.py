from qgis.PyQt.QtCore import pyqtSignal, QSettings

if not QSettings().value('TUFLOW/TestCase', False, type=bool):
    from ....dataset_menu import DatasetMenu
else:
    from tuflow.dataset_menu import DatasetMenu

from .depth_averaging_method_menu import (SingleVerticalLevelFromTop, SingleVerticalLevelFromBottom,
                                          MultiVerticalLevelFromTop, MultiVerticalLevelFromBottom, DepthRelToTop,
                                          Sigma, HeightRelToBottom, Elevation)

METHODS = [
            SingleVerticalLevelFromTop,
            SingleVerticalLevelFromBottom,
            MultiVerticalLevelFromTop,
            MultiVerticalLevelFromBottom,
            Sigma,
            DepthRelToTop,
            HeightRelToBottom,
            Elevation,
        ]


class DepthAveragingMenu(DatasetMenu):

    changed = pyqtSignal()

    def __init__(self, title: str, parent=None):
        super().__init__(title, parent)
        self.menus = self.init_averaging_menus(parent)

    def init_averaging_menus(self, parent) -> list[DatasetMenu]:
        """Initialises all the depth averaging types/menus using a SpinboxMenu for each depth averaging method."""
        menus = []
        for method in METHODS:
            menu = method(self)
            menu.menuAction().setCheckable(True)
            menu.menuAction().setChecked(False)
            menu.changed.connect(self.changed.emit)
            menu.menuAction().toggled.connect(self.changed.emit)
            menus.append(menu)
            self.addMenu(menu)

        return menus

    def set_data_types(self, data_types: list[str]):
        for menu in self.menus:
            menu.set_data_types(data_types)
