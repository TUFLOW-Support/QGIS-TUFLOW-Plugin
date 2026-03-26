import typing

from ....tvinstance import get_viewer_instance


if typing.TYPE_CHECKING:
    from ..pyqtgraph_subclass.custom_plot_widget import CustomPlotWidget
    from ..base_plot_widget import TVPlotWidget
    from ...clickable_icon import ClickableIcon


class SupportUI(typing.Protocol):
    plot_graph: 'CustomPlotWidget'
    plot_linker: 'ClickableIcon'


class PlotLinkerMixin:
    """Handles the plot linking functionality:

    Depends on the UI being setup, and does not depend on any other mixins.
    """

    def _init_plot_linker(self: SupportUI):
        self.is_origin_plot = False

        self.plot_linker.setToolTip('Common Axis Linked with Other Plots')

        # plot link toggle
        self.plot_linker.setPixmaps(
            get_viewer_instance().icon('link').pixmap(16, 16),
            get_viewer_instance().icon('link-slash').pixmap(16, 16),
        )
        self.plot_linker.setActive(True)
        self.plot_linker.clicked.connect(self.plot_linker_clicked)

    def _teardown_plot_linker(self: SupportUI):
        try:
            self.plot_linker.clicked.disconnect(self.plot_linker_clicked)
        except Exception:
            pass

    def set_plot_linker_visible(self: SupportUI, visible: bool):
        self.plot_linker.setVisible(visible)

    def link_to_origin_plot(self: SupportUI):
        self.set_linked_plot(self.plot_window.origin_plot(self))

    def set_linked_plot(self: SupportUI, linked_plot_widget: 'TVPlotWidget'):
        if not self.plot_linker.active:
            return
        if linked_plot_widget is self:
            if not self.is_origin_plot:
                self.unlink_plot()
                self.is_origin_plot = True
            return
        self.plot_graph.getViewBox().setXLink(linked_plot_widget.plot_graph)

    def unlink_plot(self: SupportUI):
        self.plot_graph.getViewBox().setXLink(None)
        if self.is_origin_plot:
            self.is_origin_plot = False
            origin = self.plot_window.find_new_origin_plot(self)
            if origin is not None:
                self.plot_window.set_origin_plot(origin)

    def plot_linker_clicked(self: SupportUI, checked: bool):
        if checked:
            self.link_to_origin_plot()
            self.plot_linker.setToolTip('Common Axis Linked with Other Plots')
        else:
            self.unlink_plot()
            self.plot_linker.setToolTip('Not linked with Other Plots')
        self.plot_link_toggled.emit(self, checked)
