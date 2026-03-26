from qgis.PyQt.QtWidgets import (QTabWidget, QTabBar, QLabel, QWidget, QToolButton, QMenu,
                                 QRadioButton, QButtonGroup, QWidgetAction)
from qgis.PyQt.QtCore import QPoint, pyqtSignal, QSettings
from qgis.PyQt.QtGui import QIcon

from ..tvinstance import get_viewer_instance
from .menu_button import MenuButton
from .tv_plot_widget.base_plot_widget import TVPlotWidget
from .tv_plot_widget.time_series_plot_widget import TimeSeriesPlotWidget
from .tv_plot_widget.section_plot_widget import SectionPlotWidget
from .tv_plot_widget.profile_plot_widget import ProfilePlotWidget
from .tv_plot_widget.curtain_plot_widget import CurtainPlotWidget
from .radio_button_action import RadioButtonAction
from ..theme import TuflowViewerTheme

if not QSettings().value('TUFLOW/TestCase', False, type=bool):
    from ...compatibility_routines import is_qt6, QT_TOP_RIGHT_CORNER, QT_CUSTOM_CONTEXT_MENU
else:
    from tuflow.compatibility_routines import is_qt6, QT_TOP_RIGHT_CORNER, QT_CUSTOM_CONTEXT_MENU

if is_qt6:
    from qgis.PyQt.QtGui import QAction
else:
    from qgis.PyQt.QtWidgets import QAction


class CustomTabWidget(QTabWidget):

    plot_linking_changed = pyqtSignal(TVPlotWidget, bool)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.name = 'view1'
        self._plot_window = None

        # Close tab signal
        self.tabCloseRequested.connect(self.remove_tab)

        # new tab signal
        self.add_timeseries_plot_action = QAction(get_viewer_instance().icon('time_series.svg'), 'Time Series Plot', self)
        self.add_timeseries_plot_action.triggered.connect(self.add_time_series_tab)
        self.add_section_plot_action = QAction(get_viewer_instance().icon('cross_section.svg'), 'Section Plot', self)
        self.add_section_plot_action.triggered.connect(self.add_section_tab)
        self.add_profile_plot_action = QAction(get_viewer_instance().icon('profile_plot.svg'), 'Profile Plot', self)
        self.add_profile_plot_action.triggered.connect(self.add_profile_tab)
        self.add_curtain_plot_action = QAction(get_viewer_instance().icon('curtain_plot.svg'), 'Curtain Plot', self)
        self.add_curtain_plot_action.triggered.connect(self.add_curtain_tab)
        plot_options = [
            self.add_timeseries_plot_action,
            self.add_section_plot_action,
            self.add_profile_plot_action,
            self.add_curtain_plot_action,
        ]

        self.add_btn = MenuButton(get_viewer_instance().icon('add'), 'Add Tab', self)
        self.add_btn.setAutoRaise(True)
        self.add_btn.addActions(plot_options)

        self.add_btn_corner = MenuButton(get_viewer_instance().icon('add'), 'Add Tab', self)
        self.add_btn_corner.setAutoRaise(True)
        self.add_btn_corner.setVisible(False)
        self.add_btn_corner.addActions([self.add_timeseries_plot_action, self.add_section_plot_action])
        self.setCornerWidget(self.add_btn_corner, QT_TOP_RIGHT_CORNER)

        self.move_add_btn()

        # context menu
        self._cur_idx = -1
        self.setContextMenuPolicy(QT_CUSTOM_CONTEXT_MENU)
        self.customContextMenuRequested.connect(self.show_context_menu)

    @property
    def plot_window(self):
        """Get the plot window."""
        return self._plot_window

    @plot_window.setter
    def plot_window(self, plot_window):
        """Set the plot window."""
        self._plot_window = plot_window
        for i in range(self.count()):
            self.widget(i).plot_window = plot_window

    def set_theme(self, theme: TuflowViewerTheme):
        self.add_btn.setIcon(get_viewer_instance().icon('add'))
        self.add_btn_corner.setIcon(get_viewer_instance().icon('add'))
        self.add_timeseries_plot_action.setIcon(get_viewer_instance().icon('time_series.svg'))
        self.add_section_plot_action.setIcon(get_viewer_instance().icon('cross_section.svg'))
        self.add_profile_plot_action.setIcon(get_viewer_instance().icon('profile_plot.svg'))
        self.add_curtain_plot_action.setIcon(get_viewer_instance().icon('curtain_plot.svg'))
        for i in range(self.count()):
            self.widget(i).set_theme(theme)
            if self.widget(i).PLOT_TYPE == 'Timeseries':
                self.setTabIcon(i, get_viewer_instance().icon('time_series.svg'))
            elif self.widget(i).PLOT_TYPE == 'Section':
                self.setTabIcon(i, get_viewer_instance().icon('cross_section.svg'))
            elif self.widget(i).PLOT_TYPE == 'Profile':
                self.setTabIcon(i, get_viewer_instance().icon('profile_plot.svg'))
            elif self.widget(i).PLOT_TYPE == 'Curtain':
                self.setTabIcon(i, get_viewer_instance().icon('curtain_plot.svg'))

    def resizeEvent(self, event):
        """Resize the widget and make sure the plus button is in the correct location."""
        super().resizeEvent(event)
        self.move_add_btn()

    def tabLayoutChange(self):
        """This virtual handler is called whenever the tab layout changes.
        If anything changes make sure the plus button is in the correct location.
        """
        super().tabLayoutChange()
        self.move_add_btn()

    def remove_tab(self, index):
        if self.name == 'view1' and index == 0 and self.count() == 1 and not self.plot_window.tabWidget_view2.isVisible():
            self.plot_window.reject()
            return
        if self.widget(index).is_origin_plot:
            self.plot_window.find_new_origin_plot(self.widget(index))
        self.widget(index).close()
        self.removeTab(index)
        if self.count() == 0:
            self.hide()
            if self.name == 'view1':
                self.plot_window.switch_tab_view_order()
        self.move_add_btn()
        self.set_plot_linking_icon_enabled()

    def move_add_btn(self):
        size = self.tabBar().sizeHint().width()
        height = self.tabBar().geometry().top() + self.tabBar().sizeHint().height() // 2 - self.add_btn.sizeHint().height() // 2
        space = self.width()
        self.add_btn.move(size, height)
        if size +  + self.add_btn.width() < space:
            self.add_btn_corner.setVisible(False)
            self.add_btn.setVisible(True)
            self.add_btn.move(size, height)
        else:
            self.add_btn.setVisible(False)
            self.add_btn_corner.setVisible(True)

    def all_tab_plot_types(self) -> list[str]:
        plot_types = []
        for i in range(self.count()):
            w = self.widget(i)
            plot_types.append(w.PLOT_TYPE)
        return plot_types

    def set_plot_linking_icon_enabled(self):
        """Adjust the visibility of the plot linking icon based on the number of tabs of the same type."""
        a = self.plot_window.tabWidget_view1.all_tab_plot_types() if self.plot_window.tabWidget_view1.isVisible() else []
        b = self.plot_window.tabWidget_view2.all_tab_plot_types() if self.plot_window.tabWidget_view2.isVisible() else []
        ab = a + b
        for plot_widget in [self.plot_window.tabWidget_view1, self.plot_window.tabWidget_view2]:
            for i in range(plot_widget.count()):
                w = plot_widget.widget(i)
                if not isinstance(w, TVPlotWidget):
                    continue
                if w.PLOT_TYPE in ab and ab.count(w.PLOT_TYPE) > 1:
                    w.set_plot_linker_visible(True)
                else:
                    w.set_plot_linker_visible(False)

    def add_tab_common(self, idx: int):
        self.widget(idx).plot_window = self.plot_window
        self.widget(idx).draw_menu_updated()
        self.widget(idx).plot_link_toggled.connect(self.plot_linking_changed.emit)
        self.widget(idx).link_to_origin_plot()
        self.plot_window.connect(self.widget(idx))
        self.set_plot_linking_icon_enabled()

    def add_tab(self, widget: QWidget, label: str, icon: QIcon):
        index = self.addTab(widget, label)
        self.setTabIcon(index, icon)
        self.setCurrentIndex(index)
        self.widget(index).plot_link_toggled.connect(self.plot_linking_changed.emit)
        self.move_add_btn()

    def add_time_series_tab(self):
        index = self.addTab(TimeSeriesPlotWidget(self), 'Time Series')
        self.add_tab_common(index)
        self.setTabIcon(index, get_viewer_instance().icon('time_series.svg'))
        self.setCurrentIndex(index)
        self.move_add_btn()

    def add_section_tab(self):
        index = self.addTab(SectionPlotWidget(self), 'Section')
        self.add_tab_common(index)
        self.setTabIcon(index, get_viewer_instance().icon('cross_section.svg'))
        self.setCurrentIndex(index)
        self.move_add_btn()

    def add_profile_tab(self):
        index = self.addTab(ProfilePlotWidget(self), 'Profile')
        self.add_tab_common(index)
        self.setTabIcon(index, get_viewer_instance().icon('profile_plot.svg'))
        self.setCurrentIndex(index)
        self.move_add_btn()

    def add_curtain_tab(self):
        index = self.addTab(CurtainPlotWidget(self), 'Curtain')
        self.add_tab_common(index)
        self.setTabIcon(index, get_viewer_instance().icon('curtain_plot.svg'))
        self.setCurrentIndex(index)
        self.move_add_btn()

    def change_tab_to_time_series(self, checked: bool):
        if not checked or self._cur_idx == -1:
            return
        idx = self._cur_idx
        self.setTabVisible(idx, False)
        self.widget(idx).close()
        self.widget(idx).deleteLater()
        idx = self.insertTab(idx, TimeSeriesPlotWidget(self), 'Time Series')
        self.add_tab_common(idx)
        self.setTabIcon(idx, get_viewer_instance().icon('time_series.svg'))
        self.setCurrentIndex(idx)
        self.move_add_btn()

    def change_tab_to_section(self, checked: bool, tab_idx: int = -1):
        if not checked or (self._cur_idx == -1 and tab_idx == -1):
            return
        idx = self._cur_idx if tab_idx == -1 else tab_idx
        self.setTabVisible(idx, False)
        self.widget(idx).close()
        self.widget(idx).deleteLater()
        idx = self.insertTab(idx, SectionPlotWidget(self), 'Section')
        self.add_tab_common(idx)
        self.setTabIcon(idx, get_viewer_instance().icon('cross_section.svg'))
        self.setCurrentIndex(idx)
        self.move_add_btn()
        self.set_plot_linking_icon_enabled()

    def change_tab_to_profile(self, checked: bool, tab_idx: int = -1):
        if not checked or (self._cur_idx == -1 and tab_idx == -1):
            return
        idx = self._cur_idx if tab_idx == -1 else tab_idx
        self.setTabVisible(idx, False)
        self.widget(idx).close()
        self.widget(idx).deleteLater()
        idx = self.insertTab(idx, ProfilePlotWidget(self), 'Profile')
        self.add_tab_common(idx)
        self.setTabIcon(idx, get_viewer_instance().icon('profile_plot.svg'))
        self.setCurrentIndex(idx)
        self.move_add_btn()
        self.set_plot_linking_icon_enabled()

    def change_tab_to_curtain(self, checked: bool, tab_idx: int = -1):
        if not checked or (self._cur_idx == -1 and tab_idx == -1):
            return
        idx = self._cur_idx if tab_idx == -1 else tab_idx
        self.setTabVisible(idx, False)
        self.widget(idx).close()
        self.widget(idx).deleteLater()
        idx = self.insertTab(idx, CurtainPlotWidget(self), 'Curtain')
        self.add_tab_common(idx)
        self.setTabIcon(idx, get_viewer_instance().icon('curtain_plot.svg'))
        self.setCurrentIndex(idx)
        self.move_add_btn()
        self.set_plot_linking_icon_enabled()

    def show_context_menu(self, pos: QPoint):
        idx = self.tabBar().tabAt(pos)
        if idx == -1:
            return

        self._cur_idx = idx
        current_widget = self.widget(idx)

        menu = QMenu(self)

        if self.name == 'view2' or self.count() > 1:
            move_to_other_view_action = QAction('Move to other view', self)
            move_to_other_view_action.triggered.connect(lambda: self.move_to_other_view(idx))
            menu.addAction(move_to_other_view_action)
            menu.addSeparator()

        rb_time_series = RadioButtonAction('Time Series', self)
        rb_time_series.setIcon(get_viewer_instance().icon('time_series.svg'))
        if current_widget.PLOT_TYPE == 'Timeseries':
            rb_time_series.setChecked(True)
        rb_time_series.toggled.connect(self.change_tab_to_time_series)
        menu.addAction(rb_time_series)

        rb_section = RadioButtonAction('Section', self)
        rb_section.setIcon(get_viewer_instance().icon('cross_section.svg'))
        if current_widget.PLOT_TYPE == 'Section':
            rb_section.setChecked(True)
        rb_section.toggled.connect(self.change_tab_to_section)
        menu.addAction(rb_section)

        rb_profile = RadioButtonAction('Profile', self)
        rb_profile.setIcon(get_viewer_instance().icon('profile_plot.svg'))
        if current_widget.PLOT_TYPE == 'Profile':
            rb_profile.setChecked(True)
        rb_profile.toggled.connect(self.change_tab_to_profile)
        menu.addAction(rb_profile)

        rb_curtain = RadioButtonAction('Curtain', self)
        rb_curtain.setIcon(get_viewer_instance().icon('curtain_plot.svg'))
        if current_widget.PLOT_TYPE == 'Curtain':
            rb_curtain.setChecked(True)
        rb_curtain.toggled.connect(self.change_tab_to_curtain)
        menu.addAction(rb_curtain)

        grp = QButtonGroup(self)
        grp.addButton(rb_time_series.button())
        grp.addButton(rb_section.button())
        grp.addButton(rb_profile.button())
        grp.addButton(rb_curtain.button())

        menu.popup(self.mapToGlobal(pos))

    def move_to_other_view(self, idx: int):
        tab_widget = self.plot_window.tabWidget_view2 if self.name == 'view1' else self.plot_window.tabWidget_view1
        w = self.widget(idx)
        label = self.tabText(idx)
        icon = self.tabIcon(idx)
        self.removeTab(idx)
        tab_widget.add_tab(w, label, icon)
        tab_widget.show()
        if self.plot_window.view2_first_show:
            self.plot_window.split_view_equally()
            self.plot_window.view2_first_show = False

        self.move_add_btn()

        if self.name == 'view2' and self.count() == 0:
            self.hide()
