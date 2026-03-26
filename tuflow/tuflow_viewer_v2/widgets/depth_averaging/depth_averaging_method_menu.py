from qgis.PyQt.QtWidgets import QWidgetAction
from qgis.PyQt.QtCore import pyqtSignal, QSettings

from ....dataset_menu import DatasetMenu
from .action import DepthAverageWidgetAction
from .single_level import SingleLevelWidgetAction
from .multi_level import MultiLevelWidgetAction
from .depth import DepthWidgetAction
from .sigma import SigmaWidgetAction
from .height import HeightWidgetAction
from .elevation import ElevationWidgetAction

if not QSettings().value('TUFLOW/TestCase', False, type=bool):
    from ....compatibility_routines import is_qt6
else:
    from tuflow.compatibility_routines import is_qt6

if is_qt6:
    from qgis.PyQt.QtGui import QAction
else:
    from qgis.PyQt.QtWidgets import QAction


class DepthAveragingMethodMenu(DatasetMenu):

    changed = pyqtSignal()

    def __init__(self, title, parent=None):
        super().__init__(title, parent)
        self.data_types = []
        self.sep = self.addSeparator()
        self.add_entry_action = QAction('Add Additional...', self)
        self.add_entry_action.triggered.connect(self.add_entry)
        self.addAction(self.add_entry_action)
        self.add_entry()

    def add_entry(self):
        action = self.create_widget_action()
        action.addItems(self.data_types)
        action.removeButtonClicked.connect(self.rem_entry)
        self.insertAction(self.sep, action)
        self.adjustSize()

    def rem_entry(self, entry: QWidgetAction):
        if entry in self.actions():
            checked = entry.isChecked()
            self.removeAction(entry)
            entry.deleteLater()
            self.adjustSize()
            if checked:
                self.changed.emit()

    def set_data_types(self, data_types: list[str]):
        self.data_types = data_types
        for action in self.actions():
            if isinstance(action, DepthAverageWidgetAction):
                cur_text = action.currentText()
                if cur_text not in data_types:
                    cur_text = ''
                action.clear()
                action.addItems(data_types)
                if cur_text:
                    action.setCurrentText(cur_text)
                else:
                    action.setCurrentIndex(-1)


class SingleVerticalLevel(DepthAveragingMethodMenu):

    def __init__(self, title='', parent=None, from_top: bool = True):
        self.from_top = from_top
        super().__init__(title, parent)

    def create_widget_action(self) -> QWidgetAction:
        action = SingleLevelWidgetAction(self.from_top, self)
        action.setMinimum(1)
        action.setMaximum(99)
        action.toggled.connect(self.changed.emit)
        action.currentTextChanged.connect(self.changed.emit)
        action.valueChanged.connect(self.changed.emit)
        return action


class SingleVerticalLevelFromTop(SingleVerticalLevel):

    def __init__(self, title='', parent=None):
        super().__init__('Single Vertical Level (from top)', parent, from_top=True)


class SingleVerticalLevelFromBottom(SingleVerticalLevel):

    def __init__(self, title='', parent=None):
        super().__init__('Single Vertical Level (from bottom)', parent, from_top=False)


class MultiVerticalLevel(DepthAveragingMethodMenu):

    def __init__(self, title='', parent=None, from_top: bool = True):
        self.from_top = from_top
        super().__init__(title, parent)

    def create_widget_action(self) -> QWidgetAction:
        action = MultiLevelWidgetAction(self.from_top, self)
        action.setMinimum(1)
        action.setMaximum(99)
        action.toggled.connect(self.changed.emit)
        action.currentTextChanged.connect(self.changed.emit)
        action.valueChanged.connect(self.changed.emit)
        return action


class MultiVerticalLevelFromTop(MultiVerticalLevel):

    def __init__(self, title='', parent=None):
        super().__init__('Multi Vertical Level (from top)', parent, from_top=True)


class MultiVerticalLevelFromBottom(MultiVerticalLevel):

    def __init__(self, title='', parent=None):
        super().__init__('Multi Vertical Level (from bottom)', parent, from_top=False)


class DepthRelToTop(DepthAveragingMethodMenu):

    def __init__(self, title='', parent=None):
        super().__init__('Depth (relative to surface)', parent)

    def create_widget_action(self) -> QWidgetAction:
        action = DepthWidgetAction(self)
        action.setMinimum(0.)
        action.setMaximum(999.0)
        action.setDecimals(2)
        action.setSingleStep(0.1)
        action.toggled.connect(self.changed.emit)
        action.currentTextChanged.connect(self.changed.emit)
        action.valueChanged.connect(self.changed.emit)
        return action


class Sigma(DepthAveragingMethodMenu):

    def __init__(self, title='', parent=None):
        super().__init__('Sigma', parent)

    def create_widget_action(self) -> QWidgetAction:
        action = SigmaWidgetAction(self)
        action.setMinimum(0.)
        action.setMaximum(1.0)
        action.setDecimals(2)
        action.setSingleStep(0.1)
        action.toggled.connect(self.toggled)
        action.currentTextChanged.connect(self.changed.emit)
        action.valueChanged.connect(self.changed.emit)
        return action

    def toggled(self):
        self.changed.emit()


class HeightRelToBottom(DepthAveragingMethodMenu):

    def __init__(self, title='', parent=None):
        super().__init__('Height (relative to bed level)', parent)

    def create_widget_action(self) -> QWidgetAction:
        action = HeightWidgetAction(self)
        action.setMinimum(0.)
        action.setMaximum(999.0)
        action.setDecimals(2)
        action.setSingleStep(0.1)
        action.toggled.connect(self.changed.emit)
        action.currentTextChanged.connect(self.changed.emit)
        action.valueChanged.connect(self.changed.emit)
        return action


class Elevation(DepthAveragingMethodMenu):

    def __init__(self, title='', parent=None):
        super().__init__('Elevation (relative to model datum)', parent)

    def create_widget_action(self) -> QWidgetAction:
        action = ElevationWidgetAction(self)
        action.setMinimum(-999)
        action.setMaximum(999.0)
        action.setDecimals(2)
        action.setSingleStep(0.1)
        action.toggled.connect(self.changed.emit)
        action.currentTextChanged.connect(self.changed.emit)
        action.valueChanged.connect(self.changed.emit)
        return action
