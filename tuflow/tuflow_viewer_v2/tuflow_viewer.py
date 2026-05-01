import json
import logging
import os
import sys, io
from datetime import datetime
from pathlib import Path

from qgis._core import QgsMapLayer
from qgis.gui import QgisInterface, QgsMapTool, QgsGui
from qgis.core import QgsProject, QgsApplication, QgsVectorLayer
from qgis.PyQt.QtCore import QSettings, pyqtSignal, QObject
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QWidget
from qgis.PyQt import QtWidgets
from qgis.utils import pluginDirectory

from .fmts.copy_on_load_mixin import CopyOnLoadMixin

try:
    from netCDF4 import Dataset
    has_nc = True
except ImportError:
    Dataset = 'Dataset'
    has_nc = False

try:
    from PyQt5.QtCore import Qt
    os.environ['PYQTGRAPH_QT_LIB'] = 'PyQt5'
except ImportError:
    os.environ['PYQTGRAPH_QT_LIB'] = 'PyQt6'

if not QSettings().value('TUFLOW/TestCase', False, type=bool):
    from .fmts import (TuflowViewerOutput)
    from .theme import load_theme
    from .widgets.settings.settings import TuflowViewerSettings
    from .tvdrop_handler import TuflowViewerDropHandler
    from .fmt_importer import get_available_classes
    from .widgets.plot_window import PlotWindow
    from .temporal_controller_widget import temporal_controller
    from .widgets.help_text import HelpText
    from .map_tools.selection_tool import SelectionMapTool
    from ..pt.pytuflow.results import ResultTypeError
    from ..compatibility_routines import is_qt6
    from .context_menu_event_filter import ContextMenuEventFilter
    from .tvctx_handler import TuflowViewerContextMenuProvider
    from .browser import TVBrowserProvider, BrowserEventFilter
else:
    # when running tests, the relative imports above will fail
    from tuflow.tuflow_viewer_v2.fmts import (TuflowViewerOutput, TPC, XMDF)
    from tuflow.tuflow_viewer_v2.theme import load_theme
    from tuflow.tuflow_viewer_v2.widgets.settings.settings import TuflowViewerSettings
    from tuflow.tuflow_viewer_v2.tvdrop_handler import TuflowViewerDropHandler
    from tuflow.tuflow_viewer_v2.fmt_importer import get_available_classes
    from tuflow.tuflow_viewer_v2.widgets.plot_window import PlotWindow
    from tuflow.tuflow_viewer_v2.temporal_controller_widget import temporal_controller
    from tuflow.tuflow_viewer_v2.widgets.help_text import HelpText
    from tuflow.tuflow_viewer_v2.map_tools.selection_tool import SelectionMapTool
    from tuflow.tuflow_viewer_v2.context_menu_event_filter import ContextMenuEventFilter
    from tuflow.tuflow_viewer_v2.tvctx_handler import TuflowViewerContextMenuProvider
    from tuflow.pt.pytuflow.results import ResultTypeError
    from tuflow.compatibility_routines import is_qt6
    from tuflow.tuflow_viewer_v2.browser import TVBrowserProvider, BrowserEventFilter

# noinspection PyUnresolvedReferences
from tuflow.pyqtgraph import setConfigOptions
setConfigOptions(antialias=True)

if is_qt6:
    from qgis.PyQt.QtGui import QAction
else:
    from qgis.PyQt.QtWidgets import QAction


class TuflowViewer(QObject):

    outputs_changed = pyqtSignal(TuflowViewerOutput)
    outputs_removed = pyqtSignal(list)
    viewer_initialising = False

    def __init__(self, iface: QgisInterface, insert_before_action: QAction | None = None):
        TuflowViewer.viewer_initialising = True
        super().__init__()
        self.iface = iface
        self._logger = self._create_logger()
        self._icons = {}
        self.settings = TuflowViewerSettings()
        self.theme = load_theme(self.settings.theme_name)
        self._id_counter = {}

        # Register output handlers - these are the formats that the TuflowViewer class can load - e.g. XMDF, TPC, etc
        self.output_handlers = self._register_output_handlers()

        self._block_on_open_signal = False

        # Register the custom drag-drop handler
        self._drop_handler = TuflowViewerDropHandler()
        # noinspection PyUnreachableCode
        if self.iface:
            # noinspection PyUnresolvedReferences
            self.iface.registerCustomDropHandler(self._drop_handler)

        # register the custom browser item provider
        self._browser_provider = TVBrowserProvider()
        QgsApplication.instance().dataItemProviderRegistry().addProvider(self._browser_provider)
        try:
            self.iface.mainWindow().findChildren(QWidget, 'Browser')[0].refresh()
        except Exception:
            pass

        self._browser_filter = BrowserEventFilter()
        self._browser_tree = self._browser_filter.browser_tree()
        if self._browser_tree:
            self._browser_tree.viewport().installEventFilter(self._browser_filter)

        # register context menu handler
        self._ctx_menu_handler = TuflowViewerContextMenuProvider()
        self._ctx_menu_handler.register_menu()
        self._ctx_menu_handler.register_layers(QgsProject.instance().mapLayers().values())

        # als provide an event filter on the context menu
        self.context_menu_filter = ContextMenuEventFilter()
        if self.iface is not None:
            self.iface.layerTreeView().viewport().installEventFilter(self.context_menu_filter)

        # temporal controller
        self.temporal_settings_initialised = False

        # plot window
        self._plot_windows = {}  # store open plot windows so they can be closed if the tool is unloaded
        self._action_plot_window = QAction(self.icon('time_series', True),
                                           'TUFLOW Viewer Plot Window', self.iface.mainWindow())
        self._action_plot_window.triggered.connect(self._create_plot_window)
        if insert_before_action:
            self.iface.pluginToolBar().insertAction(insert_before_action, self._action_plot_window)

        self._outputs = {}
        self._block_layers_removed_signal = False

        # track temporal controller properties for all results so that new results don't override already loaded results
        self.start_time = None
        self.end_time = None
        self.timestep = None

        # help text
        self.help_text = HelpText()

        # selection map tool
        self.selection_map_tool = SelectionMapTool(None, self.iface.mapCanvas())

        # signals
        QgsProject.instance().layersAdded.connect(self._on_layers_added)
        QgsProject.instance().layersWillBeRemoved.connect(self._on_layers_will_be_removed)
        QgsProject.instance().readProject.connect(self._read_project)
        if self.iface is not None:
            self.iface.mapCanvas().mapToolSet.connect(self._map_tool_changed)

        self.viewer_initialising = False

        # sys.stderr = io.StringIO()
        # import pydevd_pycharm
        # pydevd_pycharm.settrace('localhost', port=50000, stdout_to_server=True, stderr_to_server=True)

    def __del__(self):
        self.unload()

    def __repr__(self):
        if len(self._outputs) < 4:
            outputs = ', '.join([repr(x) for x in self._outputs.values()])
        else:
            outputs = ', '.join([repr(x) for x in list(self._outputs.values())[:4]]) + ', ...'
        return f'<TuflowViewer: {outputs}>'

    def unload(self):
        # unregister the custom drag-drop handler
        # noinspection PyUnreachableCode
        if self.iface is not None:
            # noinspection PyUnresolvedReferences
            try:
                self.iface.unregisterCustomDropHandler(self._drop_handler)
            except (RuntimeError, TypeError):
                pass
            try:
                self.iface.mapCanvas().mapToolSet.disconnect(self._map_tool_changed)
            except (RuntimeError, TypeError):
                pass
            try:
                self.iface.layerTreeView().viewport().removeEventFilter(self.context_menu_filter)
            except Exception:
                pass

        try:
            QgsApplication.instance().dataItemProviderRegistry().removeProvider(self._browser_provider)
            self.iface.mainWindow().findChildren(QWidget, 'Browser')[0].refresh()
        except Exception:
            pass

        try:
            if self._browser_tree:
                self._browser_tree.viewport().removeEventFilter(self._browser_filter)
        except Exception:
            pass

        # unregister context menu handler
        self._ctx_menu_handler.unregister_menu()

        # plot window
        try:
            self._action_plot_window.triggered.disconnect(self._create_plot_window)
        except (RuntimeError, TypeError):
            pass
        self.iface.pluginToolBar().removeAction(self._action_plot_window)
        for id_, w in self._plot_windows.copy().items():
            w.close()
            self._plot_windows.pop(id_)

        # signals
        try:
            QgsProject.instance().layersAdded.disconnect(self._on_layers_added)
        except (RuntimeError, TypeError):
            pass
        try:
            QgsProject.instance().layersWillBeRemoved.disconnect(self._on_layers_will_be_removed)
        except (RuntimeError, TypeError):
            pass
        try:
            QgsProject.instance().readProject.disconnect(self._read_project)
        except (RuntimeError, TypeError):
            pass

    def set_theme(self, theme_name: str):
        theme = load_theme(theme_name)
        if not theme.valid:
            return
        self._logger.debug(f'Setting theme to: {self.settings.theme_name}')
        self.theme = theme
        self.settings.theme_name = theme.theme_name
        for id_, plot_window in self._plot_windows.items():
            plot_window.set_theme(self.theme)

    def icon(self, icon_name: str, use_qgis_theme: bool = False) -> QIcon:
        """Convenience method that returns a QIcon based on a given name. Will automatically load the icon
        from the plugin's icon directory if it hasn't been loaded already.
        """
        dir_ = Path(pluginDirectory('tuflow')) / 'icons'
        theme_name = self.theme.theme_name
        if use_qgis_theme:
            theme_name = QgsApplication.instance().themeName()
            theme_name = theme_name if theme_name else 'Light'
            if theme_name == 'Default':
                theme_name = 'Light'
        theme_dir = dir_ / theme_name
        icon_id = f'{theme_name}/{icon_name}'
        icon = None
        suffix = Path(icon_name).suffix
        pattern = f'{icon_name}.*' if not suffix else icon_name
        if icon_id not in self._icons:
            for file in theme_dir.glob(pattern):
                icon = QIcon(str(file))
                self._icons[icon_id] = icon
                break
            if icon is None:
                for file in dir_.glob(pattern):
                    icon = QIcon(str(file))
                    self._icons[icon_id] = icon
                    break
        return self._icons.get(icon_id)

    def _on_layers_added(self, layers: list):
        """Load results that are not handled by drag-drop handlers - e.g. TUFLOW cross-sections which
        should be loaded once the vector layer is added to the project.
        """
        if self._block_on_open_signal:
            return
        for layer in layers:
            # can be dragged from another QGIS instance or a duplicated layer
            serialized_output = layer.customProperty('tuflow_viewer')
            if serialized_output:
                try:
                    d = json.loads(serialized_output)
                    existing_output = self.output(d['id'])
                    if existing_output and existing_output.LAYER_TYPE != 'Surface':
                        self.output(d['id']).map_layers().append(layer)
                        continue
                    driver = self.get_driver_from_name(d.get('class'))
                    if driver:
                        d['lyrids'] = [layer.id()]
                        serialized_output = json.dumps(d)
                        output = driver.from_json(serialized_output)
                        if existing_output:
                            output.generate_id(output.name)  # regenerate id
                            existing_output.duplicated_outputs.append(output)
                            self._logger.info(f'Added duplicated layer {output.name} to existing output.')
                        else:
                            self.load_output(output)
                        continue
                except Exception:
                    pass

            if not isinstance(layer, QgsVectorLayer):
                continue
            data_source = layer.dataProvider().dataSourceUri()
            driver = self.get_driver_from_file(data_source, auto_load_method='OnOpened')
            if driver:
                try:
                    output = driver(data_source, [layer])
                    self._logger.debug('Successfully loaded output.')
                    self.load_output(output)
                except FileNotFoundError:
                    self._logger.error(f'File not found: {data_source}')  # should not get here since the file was drag/dropped
                except EOFError:
                    self._logger.error(f'File appears empty or incomplete: {data_source}')
                except ResultTypeError:
                    self._logger.error(f'Failed to load file using {driver.__name__}: {data_source}')
                except Exception as e:
                    self._logger.error(f'Unexpected error: {e}')
                return True
            return False

    def load_output(self, output: TuflowViewerOutput):
        """Load an output into the class. The output should already been initialised. Called from the drop handler."""
        self._logger.info(f'Loading output: {output}...')
        if output.DRIVER_NAME in ['NetCDF Grid', 'BC Tables Check']:
            for id_, output_ in self._outputs.items():
                if output_.DRIVER_NAME == output.DRIVER_NAME and output_.fpath == output.fpath:
                    output_.map_layers().extend(output.map_layers())
                    output.map_layers().clear()
                    output = output_
                    break

        self._outputs[output.id] = output

        # record temporal properties
        self.recalculate_temporal_properties()

        # add map layers to project
        from_project = True
        for lyr in output.map_layers():
            from_project = False
            # set a custom property so the layer can be recognised as a TUFLOW Viewer output
            lyr.blockSignals(True)
            lyr.setCustomProperty('tuflow_viewer', output.to_json())  # serialize all info so that it can be loaded if it is dragged into another QGIS instance
            lyr.blockSignals(False)
            if not QgsProject.instance().mapLayer(lyr.id()):  # layer will be already in project if the output is being loaded from a project
                self._block_on_open_signal = True
                QgsProject.instance().addMapLayer(lyr)
                QgsProject.instance().writeEntry('tuflow_viewer', f'output/{output.id}', output.to_json())
                self._block_on_open_signal = False

        if not from_project:
            self.init_temporal_controller(self.start_time, self.end_time, self.timestep)

        self.temporal_settings_initialised = True

        self.outputs_changed.emit(output)
        self._logger.info('Load success.')

    def get_driver_from_file(self, file: str, auto_load_method: str) -> type[TuflowViewerOutput] | None:
        """Checks for a compatible output handler for the file. If found, returns the class."""
        self._logger.debug(f'Checking if {file} is a recognised TUFLOW output format...')
        for name, cls in self.output_handlers.items():
            if cls.AUTO_LOAD_METHOD != auto_load_method:
                continue
            if cls.format_compatible(file):
                if not self.settings.enabled_fmts.get(cls.DRIVER_NAME, False):
                    self._logger.debug('Drag and drop disabled for this format.')
                    return None
                self._logger.debug(f'File is recognised as a {name} file.')
                if cls.__name__ == 'NCGrid' and not has_nc:
                    self._logger.error('NetCDF4 python module not found, cannot load NetCDF Grid files.')
                    return None
                return cls
        return None

    def get_driver_from_name(self, name: str) -> type[TuflowViewerOutput]:
        """Returns the output handler class based on the name."""
        return self.output_handlers.get(name)

    def output(self, output_id: str) -> TuflowViewerOutput:
        """Returns the output class based on a unique id."""
        return self._outputs.get(output_id)

    def outputs(self, name: str = '') -> list[TuflowViewerOutput]:
        """Returns a list of outputs that match the name."""
        return [output for output in self._outputs.values() if output.name == name or name == '']

    def map_layer_to_output(self, layer: QgsMapLayer) -> TuflowViewerOutput | None:
        serialized = layer.customProperty('tuflow_viewer')
        if not serialized:
            return None
        try:
            d = json.loads(serialized)
            output = self.output(d.get('id'))
            if output:
                return output

            # some functions (restore default style) can cause this to break (annoyingly)
            # try and repair
            for id_, output_ in self._outputs.copy().items():
                for layer_ in output_.map_layers():
                    if layer_ == layer:
                        output_._set_custom_property()  # this should set it back to what it should be
                        return output_
            return None
        except json.JSONDecodeError:
            return None

    def result_names(self) -> list[str]:
        names = []
        for output in self._outputs.values():
            if output.name not in names:
                names.append(output.name)
        return names

    def data_types(self, output_names: list[str], filter_by: str) -> list[str]:
        dtypes = []
        for output in self._outputs.values():
            if output.name not in output_names:
                continue
            for dtype in output.data_types(filter_by):
                if dtype not in dtypes:
                    dtypes.append(dtype)
        return dtypes

    def reload_layer(self, layer: QgsMapLayer):
        output = self.map_layer_to_output(layer)
        if not output:
            self._logger.warning(f'Layer ({layer.name() if layer else layer}) is not managed by TUFLOW Viewer, cannot reload.')
            return
        if hasattr(output, 'reload_layer'):
            output.reload_layer(layer, output.copied_files)
        else:
            layer.reload()

    def init_temporal_controller(self, start_time: datetime, end_time: datetime, timestep: float):
        if not self.timestep:
            return
        temporal_controller.show()
        temporal_controller.activate_temporal_navigation()
        temporal_controller.start_time = start_time
        temporal_controller.end_time = end_time
        temporal_controller.timestep = timestep
        temporal_controller.units = 'seconds'

    @staticmethod
    def _create_logger() -> logging.Logger:
        """Sets up logging for TUFLOW Viewer. To get logger in other modules, use logging.getLogger('tuflow_viewer').
        Logging level will be set to DEBUG if the ``set_debug()`` function from the ``tvdeveloper_tools`` module
        has been called with True.

        Returns the logger object.
        """
        from .tvlogging import QgisTuflowLoggingHandler
        tvlogger = logging.getLogger('tuflow_viewer')
        loggers = [tvlogger]
        for logger in loggers:
            for hnd in logger.handlers.copy():
                logger.removeHandler(hnd)
        if QSettings().value('TUFLOW/Debug', False, type=bool):
            hnd = QgisTuflowLoggingHandler(logging.DEBUG)
        else:
            hnd = QgisTuflowLoggingHandler(logging.INFO)
        for logger in loggers:
            if QSettings().value('TUFLOW/Debug', False, type=bool):
                logger.setLevel(logging.DEBUG)
            else:
                logger.setLevel(logging.INFO)
            logger.addHandler(hnd)
        return tvlogger

    def _register_output_handlers(self) -> dict:
        """Loads the output handlers. This will look through python files present in the ``fmts`` directory
        and load the class dynamically if it bases TuflowViewerOutput.

        Returns a dictionary of [class name] = __class__.
        """
        output_handlers = {}
        dir_ = Path(__file__).parent / 'fmts'
        import_loc = 'tuflow.tuflow_viewer_v2.fmts'
        base_class = 'TuflowViewerOutput'
        for handler in get_available_classes(dir_, base_class, import_loc):
            if handler not in output_handlers:
                output_handlers[handler.__name__] = handler
                self._logger.debug('Registered output handler: ' + handler.__name__)
        return output_handlers

    def _on_layers_will_be_removed(self, layers: list[str]):
        """Called when layers are about to be removed from the project. This will check if the layer is an output
        that TUFLOW Viewer is managing and unload it accordingly.
        """
        if self._block_layers_removed_signal:
            return
        removed_outputs = []
        for lyrid in layers:
            lyr = QgsProject.instance().mapLayer(lyrid)
            if not lyr:
                continue
            if lyr.customProperty('tuflow_viewer'):
                try:
                    d = json.loads(lyr.customProperty('tuflow_viewer'))
                    output_id = d['id']
                except json.JSONDecodeError:
                    output_id = lyr.customProperty('tuflow_viewer')
                output = self.output(output_id)
                if not output:
                    # it might be a duplicated layer
                    for output in self._outputs.values():
                        for dup in output.duplicated_outputs.copy():
                            if dup.id == output_id:
                                output.duplicated_outputs.remove(dup)
                if not output:
                    continue
                try:
                    if output.DRIVER_NAME == 'TUFLOW CATCH Json':
                        self._block_layers_removed_signal = True
                        output.pre_close(layers)
                        self._block_layers_removed_signal = False
                    output.map_layers().remove(lyr)
                except Exception:
                    continue
                if not output.map_layers():
                    if output.duplicated_outputs:
                        dup = output.duplicated_outputs.pop(0)
                        self.load_output(dup)
                        dup.duplicated_outputs = output.duplicated_outputs
                        self._logger.info(f'Duplicated layer {dup.name} taking place of original.')
                    self._logger.info(f'Removing output from TUFLOW Viewer: {output}')
                    removed_outputs.append(output.id)
                    output.close()
                    popped = self._outputs.pop(output_id, None)
                    if not popped:
                        self._logger.warning(f'Something has gone wrong, the ID of the output being removed does not match and ID within TUFLOW Viewer: {output}')
                    else:
                        QgsProject.instance().removeEntry('tuflow_viewer', f'output/{output_id}')

        if removed_outputs:
            self.configure_temporal_controller()
            self.outputs_removed.emit(removed_outputs)

    def configure_temporal_controller(self):
        self.recalculate_temporal_properties()
        self.init_temporal_controller(self.start_time, self.end_time, self.timestep)

    def recalculate_temporal_properties(self):
        if not self._outputs:
            self.start_time = None
            self.end_time = None
            self.timestep = None
            self.temporal_settings_initialised = False
            return

        # first check results that have an explicit reference time
        start_time = None
        start_times = [output.start_time for output in self._outputs.values() if output.has_reference_time]
        if start_times:
            start_time = min(start_times)

        # else consider all results
        if not start_time:
            start_times = [output.start_time for output in self._outputs.values() if output.start_time is not None]
            if start_times:
                start_time = min(start_times)

        if start_time is not None:
            self.start_time = start_time

        if start_time is not None:
            for key, output in self._outputs.copy().items():
                if not output.has_reference_time:
                    output.reference_time = start_time
                    try:
                        output.init_temporal_properties()
                    except RuntimeError:
                        self._logger.warning(
                            f'An output is no longer present in QGIS. Most likely it was not removed correctly '
                            f'from TUFLOW Viewer due to a previous warning/error: {output}')
                        self._outputs.pop(key, None)

        end_time = [output.end_time for output in self._outputs.values() if output.end_time is not None]
        if end_time:
            self.end_time = max(end_time)
        timestep = [output.timestep for output in self._outputs.values() if output.timestep is not None]
        if timestep:
            self.timestep = min(timestep) - 0.001  # add a small amount to avoid floating point issues

    def _read_project(self):
        """Loads outputs from the QGIS project file. Called when the QGIS project is loaded."""
        for entry in QgsProject.instance().entryList('tuflow_viewer', 'output'):
            key = f'output/{entry}'
            self._logger.debug(f'Loading output from QGIS project: {key}')
            value = QgsProject.instance().readEntry('tuflow_viewer', key)
            if not value[1]:
                self._logger.error(f'Failed to read entry from QGIS project: {key}')
                continue
            try:
                d = json.loads(value[0])
            except json.JSONDecodeError:
                self._logger.error(f'Failed to decode saved JSON project entry: {value[0]}')
                continue
            driver = self.get_driver_from_name(d.get('class'))
            if not driver:
                self._logger.error('Failed to find output driver for: {0}'.format(entry))
                continue
            try:
                output = driver.from_json(value[0])  # output is loaded slightly differently since the map layer is already in the project
            except Exception as e:
                self._logger.error('Failed to load {0}: {1}'.format(d['name'], e))
                continue
            self.load_output(output)

    def _create_plot_window(self, *args):
        """Creates a new plotting window. Triggered when the time-series icon is clicked in the plugin toolbar."""
        id_ = self._next_plot_id()
        w = PlotWindow(self, id_)
        w.set_theme(self.theme)
        w.closed.connect(self._plot_destroyed)
        self._plot_windows[id_] = w
        w.show()

    def _plot_destroyed(self, w):
        if w in self._plot_windows.values():
            id_ = list(self._plot_windows.keys())[list(self._plot_windows.values()).index(w)]
            self._plot_windows.pop(id_)
            self._reset_plot_id(id_)

    def _map_tool_changed(self, tool: QgsMapTool):
        for w in self._plot_windows.values():
            w.map_tool_changed(tool)

    def _reset_plot_id(self, i: int):
        if i in self._id_counter:
            self._id_counter[i] = False

    def _next_plot_id(self) -> int:
        i, key = None, None
        for key, val in self._id_counter.items():
            if not val:
                i = key
                break
        if i is None:
            if key is None:
                i = 0
            else:
                i = key + 1
        self._id_counter[i] = True
        return i

    def plot_widget(self, window_id: int = 0, view_id: int = 0, tab_id: int = 0):
        window = self._plot_windows.get(window_id)
        if not window:
            raise ValueError(f'Plot window with id {window_id} not found.')
        if view_id == 0:
            view = window.tabWidget_view1
        elif view_id == 1:
            view = window.tabWidget_view2
        else:
            raise ValueError(f'View with id {view_id} not found.')
        plot_widget = view.widget(tab_id)
        if not plot_widget:
            raise ValueError(f'Plot widget with id {tab_id} not found in view {view_id} of window {window_id}.')
        return plot_widget
