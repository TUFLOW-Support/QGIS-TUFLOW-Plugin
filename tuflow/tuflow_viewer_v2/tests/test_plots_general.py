import sys
from datetime import datetime

import numpy as np
try:
    import pandas as pd
except ImportError:
    from ...pt.pytuflow._outputs.pymesh.stubs import pandas as pd
from qgis.PyQt.QtCore import QSettings
from qgis.PyQt.QtGui import QColor
from qgis.core import QgsPointXY, QgsGeometry, QgsVectorLayer
from qgis.gui import QgsVertexMarker, QgsRubberBand

from .stubs.qgis_stubs import QGIS  # import so that it's initialised
from ._utils import get_dataset_path, add_result_to_viewer, add_results_to_viewer, TuflowViewerTestCase
from tuflow.tuflow_viewer_v2.fmts import (XMDF, TPC, BCTablesCheck, NCMesh, DAT, FMTS, DATCrossSections, CATCHJson,
                                          NCGrid, GPKG1D)
from tuflow.tuflow_viewer_v2.widgets.tv_plot_widget.time_series_plot_widget import TimeSeriesPlotWidget
from tuflow.tuflow_viewer_v2.widgets.plot_window import PlotWindow
from tuflow.tuflow_viewer_v2.tvinstance import get_viewer_instance
from tuflow.tuflow_viewer_v2.widgets.tv_plot_widget.pyqtgraph_subclass.tuflow_viewer_curve import TuflowViewerCurve

from tuflow.tuflow_viewer_v2.temporal_controller_widget import temporal_controller


class TestPlotsGeneral(TuflowViewerTestCase):
    """General tests for plot widgets. Not unit tests, but just some general full integration tests to check
    that the plots are behaving as expected.
    """

    def test_time_series_plot_map_output(self):
        # load XMDF result
        p = get_dataset_path('run.xmdf', 'result')
        res = XMDF(p)
        with add_result_to_viewer(res):  # context manager so results and layers are unloaded after test
            plot_window = PlotWindow(get_viewer_instance())
            plot = plot_window.tabWidget_view1.widget(0)  # first plot tab within the plot window (default is time-series)

            # data types
            self.assertEqual(4, len(plot.toolbar.data_types()))
            self.assertEqual(res.data_types('timeseries'), plot.toolbar.data_types())

            # result names
            self.assertEqual(['run'], plot.toolbar.result_names())

            # fake a drawn point to get the plot to populate
            wl_action = [x for x in plot.toolbar.data_types_menu.actions() if x.text() == 'water level'][0]
            wl_action.setChecked(True)
            marker = QgsVertexMarker(QGIS.iface.mapCanvas())
            marker.setColor(QColor('#000000'))
            point = [1., 1.]
            marker.setCenter(QgsPointXY(*point))
            plot.draw_tool_updated(marker, new=True)

            # check the drawn menu item has been updated
            self.assertEqual(['Clear', 'Item 1'], [x.text() for x in plot.toolbar.draw_action_menu.actions() if not x.isSeparator()])

            # check the curve has been added to the plot
            curves = [x for x in plot.plot_graph.items() if isinstance(x, TuflowViewerCurve)]
            self.assertEqual(1, len(curves))

            # check the curve properties
            curve = curves[0]
            src_item = curve.src_item
            self.assertEqual('water level', src_item.data_type)
            self.assertEqual('#000000', src_item.colour)
            self.assertEqual(point, src_item.geom)
            self.assertEqual('drawn', src_item.sel_type)

            # check the curve data
            data = res.time_series(point, 'water level').reset_index().to_numpy(dtype=np.float64)
            plot_data = np.column_stack(curve.getData())
            isclose = np.isclose(data, plot_data, equal_nan=True)
            self.assertTrue(isclose.all())

    def test_time_series_plot_time_series(self):
        # load TPC
        p = get_dataset_path('EG15_001.tpc', 'result')
        res = TPC(p)
        with add_result_to_viewer(res):  # context manager so results and layers are unloaded after test
            plot_window = PlotWindow(get_viewer_instance())
            plot = plot_window.tabWidget_view1.widget(0)  # first plot tab within the plot window (default is time-series)

            # data types
            self.assertEqual(9, len(plot.toolbar.data_types()))
            self.assertEqual(res.data_types('timeseries'), plot.toolbar.data_types())

            # select a channel and flow result
            plot.toggle_selection_tool(True)
            q_action = [x for x in plot.toolbar.data_types_menu.actions() if x.text() == 'flow'][0]
            q_action.setChecked(True)
            lyr = [x for x in res.map_layers() if 'PLOT_L' in x.name()][0]
            QGIS.iface.setActiveLayer(lyr)
            ch = list(lyr.getFeatures('"ID" = \'Pipe10\''))[0]
            lyr.selectByIds([ch.id()])

            # check the curve has been added to the plot
            curves = [x for x in plot.plot_graph.items() if isinstance(x, TuflowViewerCurve)]
            self.assertEqual(1, len(curves))

            # check the curve properties
            curve = curves[0]
            src_item = curve.src_item
            self.assertEqual('flow', src_item.data_type)
            self.assertEqual('selection', src_item.sel_type)

            # check the curve data
            data = res.time_series('pipe10', 'flow').reset_index().to_numpy(dtype=np.float64)
            plot_data = np.column_stack(curve.getData())
            isclose = np.isclose(data, plot_data, equal_nan=True)
            self.assertTrue(isclose.all())

            # make another selection just to make sure it's updated properly
            ch = list(lyr.getFeatures('"ID" = \'Pipe1\''))[0]
            lyr.selectByIds([ch.id()])
            curves = [x for x in plot.plot_graph.items() if isinstance(x, TuflowViewerCurve)]
            self.assertEqual(1, len(curves))
            data = res.time_series('pipe1', 'flow').reset_index().to_numpy(dtype=np.float64)
            plot_data = np.column_stack(curves[0].getData())
            isclose = np.isclose(data, plot_data, equal_nan=True)
            self.assertTrue(isclose.all())

            # check flow regime
            r_action = [x for x in plot.toolbar.data_types_menu.actions() if x.text() == 'channel flow regime'][0]
            r_action.setChecked(True)
            plot.update_plot()
            curves = [x for x in plot.plot_graph.items() if isinstance(x, TuflowViewerCurve)]
            self.assertEqual(2, len(curves), "Flow regime test failed")

    # def test_tpc_big_dataset_tmp(self):
    #     # ok if fails in regular testing - tmp test of a bigger dataset bug
    #     p = r"C:\TUFLOW\working\TSC250992\new_data\plot\BAT_N44003_4m_NQ_SGS_C04_1p00_00010m_5090_2100_SSP3_08.tpc"
    #     res = TPC(p)
    #     with add_result_to_viewer(res):
    #         plot_window = PlotWindow(get_viewer_instance())
    #         plot_window.tabWidget_view1.change_tab_to_section(checked=True, tab_idx=0)  # change first tab to section plot
    #         plot = plot_window.tabWidget_view1.widget(0)
    #
    #         plot.toggle_selection_tool(True)
    #         actions = [x for x in plot.toolbar.data_types_menu.actions() if x.text() in ['bed level', 'pipes']]
    #         _ = [x.setChecked(True) for x in actions]
    #         lyr = [x for x in res.map_layers() if 'PLOT_L' in x.name()][0]
    #         QGIS.iface.setActiveLayer(lyr)
    #         ch = list(lyr.getFeatures('"ID" = \'DRKB02PIPE050\''))[0]
    #         temporal_controller.setCurrentTime(datetime(1990, 1, 1, 1, 0, 0))
    #         lyr.selectByIds([ch.id()])
    #
    #         print()

    def test_section_plot_map_output(self):
        p = get_dataset_path('run.xmdf', 'result')
        res = XMDF(p)
        with add_result_to_viewer(res):  # context manager so results and layers are unloaded after test
            plot_window = PlotWindow(get_viewer_instance())
            plot_window.tabWidget_view1.change_tab_to_section(checked=True, tab_idx=0)  # change first tab to section plot
            plot = plot_window.tabWidget_view1.widget(0)

            # data types
            self.assertEqual(10, len(plot.toolbar.data_types()))
            self.assertEqual(res.data_types('section'), plot.toolbar.data_types())

            # result names
            self.assertEqual(['run'], plot.toolbar.result_names())

            # fake a drawn line to get the plot to populate
            wl_action = [x for x in plot.toolbar.data_types_menu.actions() if x.text() == 'max water level'][0]
            wl_action.setChecked(True)
            line = QgsRubberBand(QGIS.iface.mapCanvas())
            line.setColor(QColor('#000000'))
            line.setFillColor(QColor('#000000'))
            points = [[0.5, 0.5], [1.5, 1.5]]
            geom = QgsGeometry.fromPolylineXY([QgsPointXY(x, y) for x, y in points])
            line.setToGeometry(geom)
            plot.draw_tool_updated(line, new=True)

            # check the drawn menu item has been updated
            self.assertEqual(['Clear', 'Item 1'],
                             [x.text() for x in plot.toolbar.draw_action_menu.actions() if not x.isSeparator()])

            # check the curve has been added to the plot
            curves = [x for x in plot.plot_graph.items() if isinstance(x, TuflowViewerCurve)]
            self.assertEqual(1, len(curves))

            # check the curve properties
            curve = curves[0]
            src_item = curve.src_item
            self.assertEqual('max water level', src_item.data_type)
            self.assertEqual('#000000', src_item.colour)
            self.assertEqual(points, src_item.geom)
            self.assertEqual('drawn', src_item.sel_type)

            # check the curve data
            data = res.section(points, 'max water level', 0.).to_numpy(dtype=np.float64)
            plot_data = np.column_stack(curve.getData())
            close = np.isclose(data, plot_data, equal_nan=True)
            self.assertTrue(close.all())

            # clear the drawn item
            plot.clear_drawn_items()
            curves = [x for x in plot.plot_graph.items() if isinstance(x, TuflowViewerCurve)]
            self.assertEqual(0, len(curves))

    def test_section_plot_map_output_nc_mesh(self):
        p = get_dataset_path('fv_res.nc', 'result')
        res = NCMesh(p)
        with add_result_to_viewer(res):  # context manager so results and layers are unloaded after test
            plot_window = PlotWindow(get_viewer_instance())
            plot_window.tabWidget_view1.change_tab_to_section(checked=True, tab_idx=0)  # change first tab to section plot
            plot = plot_window.tabWidget_view1.widget(0)

            # data types
            self.assertEqual(3, len(plot.toolbar.data_types()))
            self.assertEqual(res.data_types('section'), plot.toolbar.data_types())

            # result names
            self.assertEqual(['fv_res'], plot.toolbar.result_names())

            # fake a drawn line to get the plot to populate
            wl_action = [x for x in plot.toolbar.data_types_menu.actions() if x.text() == 'water level'][0]
            wl_action.setChecked(True)
            line = QgsRubberBand(QGIS.iface.mapCanvas())
            line.setColor(QColor('#000000'))
            line.setFillColor(QColor('#000000'))
            points = [[4.5, 4.5], [0.5, 2.5]]
            geom = QgsGeometry.fromPolylineXY([QgsPointXY(x, y) for x, y in points])
            line.setToGeometry(geom)
            temporal_controller.setCurrentTime(datetime(1990, 1, 1, 0, 0, 0))
            plot.draw_tool_updated(line, new=True)

            # check the drawn menu item has been updated
            self.assertEqual(['Clear', 'Item 1'],
                             [x.text() for x in plot.toolbar.draw_action_menu.actions() if not x.isSeparator()])

            # check the curve has been added to the plot
            curves = [x for x in plot.plot_graph.items() if isinstance(x, TuflowViewerCurve)]
            self.assertEqual(1, len(curves))

            # check the curve properties
            curve = curves[0]
            src_item = curve.src_item
            self.assertEqual('water level', src_item.data_type)
            self.assertEqual('#000000', src_item.colour)
            self.assertEqual(points, src_item.geom)
            self.assertEqual('drawn', src_item.sel_type)

            # check the curve data
            data = res.section(points, 'water level', 0.).to_numpy(dtype=np.float64)
            plot_data = np.column_stack(curve.getData())
            close = np.isclose(data, plot_data, equal_nan=True)
            self.assertTrue(close.all())

            # clear the drawn item
            plot.clear_drawn_items()
            curves = [x for x in plot.plot_graph.items() if isinstance(x, TuflowViewerCurve)]
            self.assertEqual(0, len(curves))

    def test_section_plot_time_series(self):
        # load TPC
        p = get_dataset_path('EG15_001.tpc', 'result')
        res = TPC(p)
        with add_result_to_viewer(res):  # context manager so results and layers are unloaded after test
            plot_window = PlotWindow(get_viewer_instance())
            plot_window.tabWidget_view1.change_tab_to_section(checked=True, tab_idx=0)  # change first tab to section plot
            plot = plot_window.tabWidget_view1.widget(0)

            # data types
            self.assertEqual(6, len(plot.toolbar.data_types()))
            dtypes = [x for x in res.data_types('section') if x != 'node flow regime']
            self.assertEqual(dtypes, plot.toolbar.data_types())

            # select a channel and plot bed level, pipes, pits
            plot.toggle_selection_tool(True)
            actions = [x for x in plot.toolbar.data_types_menu.actions() if x.text() in ['bed level', 'pipes', 'pits', 'water level']]
            _ = [x.setChecked(True) for x in actions]
            lyr = [x for x in res.map_layers() if 'PLOT_L' in x.name()][0]
            QGIS.iface.setActiveLayer(lyr)
            ch = list(lyr.getFeatures('"ID" = \'Pipe10\''))[0]
            temporal_controller.setCurrentTime(datetime(1990, 1, 1, 1, 0, 0))
            lyr.selectByIds([ch.id()])

            # check the curve has been added to the plot
            curves = [x for x in plot.plot_graph.items() if isinstance(x, TuflowViewerCurve)]
            self.assertEqual(4, len(curves))

            # check the curve data
            bed_curve = [x for x in curves if x.src_item.data_type == 'bed level'][0]
            pit_curve = [x for x in curves if x.src_item.data_type == 'pits'][0]
            pipe_curve = [x for x in curves if x.src_item.data_type == 'pipes'][0]
            wl_curve = [x for x in curves if x.src_item.data_type == 'water level'][0]
            data = res.section('pipe10', ['bed level', 'pipes', 'pits', 'water level'], 1).iloc[:,3:].to_numpy(dtype=np.float64)
            plot_data = np.column_stack(bed_curve.getData())
            plot_data = np.append(plot_data, np.column_stack(pipe_curve.getDataClean())[:,1:], axis=1)
            plot_data = np.append(plot_data, np.column_stack(pit_curve.getData())[:,1:], axis=1)
            plot_data = np.append(plot_data, np.column_stack(wl_curve.getData())[:,1:], axis=1)
            isclose = np.isclose(data, plot_data, equal_nan=True)
            self.assertEqual(plot_data.shape, data.shape)
            self.assertTrue(isclose.all())

            temporal_controller.setCurrentTime(datetime(1990, 1, 1, 2, 0, 0))  # this triggers replotting
            curves = [x for x in plot.plot_graph.items() if isinstance(x, TuflowViewerCurve)]
            self.assertEqual(4, len(curves))
            wl_curve = [x for x in curves if x.src_item.data_type == 'water level'][0]
            plot_data = np.column_stack(wl_curve.getData())
            data = res.section('pipe10', ['water level'], 2).iloc[:, 3:].to_numpy(dtype=np.float64)
            self.assertEqual(plot_data.shape, data.shape)
            isclose = np.isclose(data, plot_data, equal_nan=True)
            self.assertTrue(isclose.all())

            # make a new selection and make sure it's updated properly
            ch = list(lyr.getFeatures('"ID" IN (\'Pipe10\', \'Pipe11\')'))
            lyr.selectByIds([x.id() for x in ch])
            curves = [x for x in plot.plot_graph.items() if isinstance(x, TuflowViewerCurve)]
            for curve in curves:
                if curve.src_item.data_type == 'water level':
                    self.assertEqual('Pipe10', curve.channel_curves[0].channel_id)

    def test_profile_plot_xmdf(self):
        p = get_dataset_path('run.xmdf', 'result')
        res = XMDF(p)
        with add_result_to_viewer(res):  # context manager so results and layers are unloaded after test
            plot_window = PlotWindow(get_viewer_instance())
            plot_window.tabWidget_view1.change_tab_to_profile(checked=True, tab_idx=0)
            plot = plot_window.tabWidget_view1.widget(0)

            # data types
            self.assertEqual(4, len(plot.toolbar.data_types()))

            # result names
            self.assertEqual(['run'], plot.toolbar.result_names())

            # fake a drawn line to get the plot to populate
            wl_action = [x for x in plot.toolbar.data_types_menu.actions() if x.text() == 'velocity'][0]
            wl_action.setChecked(True)
            marker = QgsVertexMarker(QGIS.iface.mapCanvas())
            marker.setColor(QColor('#000000'))
            point = [0.85, 0.9]
            marker.setCenter(QgsPointXY(*point))
            temporal_controller.setCurrentTime(datetime(1990, 1, 1, 0, 5, 0))
            plot.draw_tool_updated(marker, new=True)

            # check the drawn menu item has been updated
            self.assertEqual(['Clear', 'Item 1'],
                             [x.text() for x in plot.toolbar.draw_action_menu.actions() if not x.isSeparator()])

            # check the curve has been added to the plot
            curves = [x for x in plot.plot_graph.items() if isinstance(x, TuflowViewerCurve)]
            self.assertEqual(1, len(curves))

            # check the curve properties
            curve = curves[0]
            src_item = curve.src_item
            self.assertEqual('velocity', src_item.data_type)
            self.assertEqual('#000000', src_item.colour)
            self.assertEqual(point, src_item.geom)
            self.assertEqual('drawn', src_item.sel_type)

            # check the curve data
            data = res.profile(point, 'velocity', 0.).to_numpy(dtype=np.float64)
            plot_data = np.column_stack(curve.getData())[:,[1, 0]]
            close = np.isclose(data, plot_data, equal_nan=True)
            self.assertTrue(close.all())

            # clear the drawn item
            plot.clear_drawn_items()
            curves = [x for x in plot.plot_graph.items() if isinstance(x, TuflowViewerCurve)]
            self.assertEqual(0, len(curves))

    def test_curtain_plot_nc(self):
        p = get_dataset_path('fv_res.nc', 'result')
        res = NCMesh(p)
        with add_result_to_viewer(res):  # context manager so results and layers are unloaded after test
            plot_window = PlotWindow(get_viewer_instance())
            plot_window.tabWidget_view1.change_tab_to_curtain(checked=True, tab_idx=0)
            plot = plot_window.tabWidget_view1.widget(0)

            # data types
            self.assertEqual(1, len(plot.toolbar.data_types()))

            # result names
            self.assertEqual(['fv_res'], plot.toolbar.result_names())

            # fake a drawn line to get the plot to populate
            wl_action = [x for x in plot.toolbar.data_types_menu.actions() if x.text() == 'velocity'][0]
            wl_action.setChecked(True)
            line = QgsRubberBand(QGIS.iface.mapCanvas())
            line.setColor(QColor('#000000'))
            line.setFillColor(QColor('#000000'))
            points = [[4.5, 4.5], [0.5, 2.5]]
            geom = QgsGeometry.fromPolylineXY([QgsPointXY(x, y) for x, y in points])
            line.setToGeometry(geom)
            temporal_controller.setCurrentTime(datetime(1990, 1, 1, 0, 0, 0))
            plot.draw_tool_updated(line, new=True)

            # check the drawn menu item has been updated
            self.assertEqual(['Clear', 'Item 1'],
                             [x.text() for x in plot.toolbar.draw_action_menu.actions() if not x.isSeparator()])

            # check the curve has been added to the plot
            curves = [x for x in plot.plot_graph.items() if isinstance(x, TuflowViewerCurve)]
            self.assertEqual(1, len(curves))

            # check the curve properties
            curve = curves[0]
            src_item = curve.src_item
            self.assertEqual('velocity', src_item.data_type)
            self.assertEqual('#000000', src_item.colour)
            self.assertEqual(points, src_item.geom)
            self.assertEqual('drawn', src_item.sel_type)

            # check the curve data
            data = res.curtain(points, 'velocity', 0.)
            data.columns = ['x', 'y', 'velocity', 'velocity_local']
            data = data.join(pd.DataFrame(data['velocity'].tolist(), columns=['vel_x', 'vel_y']))
            data['velocity'] = (data['vel_x'] ** 2 + data['vel_y'] ** 2) ** 0.5
            data = data[['x', 'y', 'velocity']].to_numpy()
            plot_data = np.column_stack(curve.getData())
            close = np.isclose(data, plot_data, equal_nan=True)
            self.assertTrue(close.all())

            # clear the drawn item
            plot.clear_drawn_items()
            curves = [x for x in plot.plot_graph.items() if isinstance(x, TuflowViewerCurve)]
            self.assertEqual(0, len(curves))

    def test_curtain_plot_xmdf(self):
        p = get_dataset_path('run.xmdf', 'result')
        res = XMDF(p)
        with add_result_to_viewer(res):  # context manager so results and layers are unloaded after test
            plot_window = PlotWindow(get_viewer_instance())
            plot_window.tabWidget_view1.change_tab_to_curtain(checked=True, tab_idx=0)
            plot = plot_window.tabWidget_view1.widget(0)

            vel_max_action = [x for x in plot.toolbar.data_types_menu.actions() if x.text() == 'max vector velocity'][0]
            vel_max_action.setChecked(True)
            line = QgsRubberBand(QGIS.iface.mapCanvas())
            line.setColor(QColor('#000000'))
            line.setFillColor(QColor('#000000'))
            points = [[0.6, 0.5], [1.6, 1.5]]
            geom = QgsGeometry.fromPolylineXY([QgsPointXY(x, y) for x, y in points])
            line.setToGeometry(geom)
            plot.draw_tool_updated(line, new=True)

            # check the curve has been added to the plot
            curves = [x for x in plot.plot_graph.items() if isinstance(x, TuflowViewerCurve)]
            self.assertEqual(1, len(curves))

    def test_2d_bc_tables(self):
        p = get_dataset_path('EG15_001_bcc_check_R.shp', 'result')
        layer = QgsVectorLayer(str(p), 'EG15_001_bcc_check_R', 'ogr')
        res = BCTablesCheck(p, [layer])

        with add_result_to_viewer(res):
            plot_window = PlotWindow(get_viewer_instance())
            plot = plot_window.tabWidget_view1.widget(0)  # first plot tab within the plot window (default is time-series)

            # data types
            self.assertEqual(3, len(plot.toolbar.data_types()))
            self.assertEqual(sorted(res.data_types('timeseries')), sorted(plot.toolbar.data_types()))

            # select a channel and plot bed level, pipes, pits
            plot.toggle_selection_tool(True)
            actions = [x for x in plot.toolbar.data_types_menu.actions() if x.text() in ['QT']]
            _ = [x.setChecked(True) for x in actions]
            QGIS.iface.setActiveLayer(layer)
            ch = list(layer.getFeatures('"Type" = \'QT\' AND "Source" LIKE \'BC000020:%\''))[0]
            layer.selectByIds([ch.id()])

            # check the curve has been added to the plot
            curves = [x for x in plot.plot_graph.items() if isinstance(x, TuflowViewerCurve)]
            self.assertEqual(1, len(curves))

            data = res.time_series('BC000020', 'QT').to_numpy(dtype=np.float64)
            plot_data = np.column_stack(curves[0].getData())
            close = np.isclose(data, plot_data, equal_nan=True)
            self.assertTrue(close.all())

    def test_dat_time_series(self):
        p = get_dataset_path('small_model_001_h.dat', 'result')
        res = DAT(p)

        with add_result_to_viewer(res):
            plot_window = PlotWindow(get_viewer_instance())
            plot = plot_window.tabWidget_view1.widget(0)  # first plot tab within the plot window (default is time-series)

            wl_action = [x for x in plot.toolbar.data_types_menu.actions() if x.text() == 'water level'][0]
            wl_action.setChecked(True)
            marker = QgsVertexMarker(QGIS.iface.mapCanvas())
            marker.setColor(QColor('#000000'))
            point = [1., 1.]
            marker.setCenter(QgsPointXY(*point))
            plot.draw_tool_updated(marker, new=True)

            # check the curve has been added to the plot
            curves = [x for x in plot.plot_graph.items() if isinstance(x, TuflowViewerCurve)]
            self.assertEqual(1, len(curves))

            # check the curve data
            data = res.time_series(point, 'water level').reset_index().to_numpy(dtype=np.float64)
            plot_data = np.column_stack(curves[0].getData())
            isclose = np.isclose(data, plot_data, equal_nan=True)
            self.assertTrue(isclose.all())

    def test_fm_section(self):
        pzzn = get_dataset_path('FMT_M01_001.zzn', 'result')
        pdat = get_dataset_path('FMT_M01_001.dat', 'result')
        pgxy = get_dataset_path('FMT_M01_001.gxy', 'result')

        res = FMTS(pzzn, pdat, pgxy)

        with add_result_to_viewer(res):
            plot_window = PlotWindow(get_viewer_instance())
            plot_window.tabWidget_view1.change_tab_to_section(checked=True, tab_idx=0)  # change first tab to section plot
            plot = plot_window.tabWidget_view1.widget(0)

            # select a channel and plot bed level, pipes, pits
            plot.toggle_selection_tool(True)
            actions = [x for x in plot.toolbar.data_types_menu.actions() if x.text() in ['bed level', 'water level']]
            _ = [x.setChecked(True) for x in actions]
            lyr = [x for x in res.map_layers() if 'PLOT_P' in x.name()][0]
            QGIS.iface.setActiveLayer(lyr)
            ch = list(lyr.getFeatures('"ID" = \'FC01.08\''))[0]
            temporal_controller.setCurrentTime(datetime(1990, 1, 1, 1, 0, 0))
            lyr.selectByIds([ch.id()])

            # check the curve has been added to the plot
            curves = [x for x in plot.plot_graph.items() if isinstance(x, TuflowViewerCurve)]
            self.assertEqual(2, len(curves))

    def test_fm_section_without_dat(self):
        pzzn = get_dataset_path('FMT_M01_001.zzn', 'result')
        pgxy = get_dataset_path('FMT_M01_001.gxy', 'result')

        res = FMTS(pzzn, None, pgxy, bypass_dialog=True)

        with add_result_to_viewer(res):
            plot_window = PlotWindow(get_viewer_instance())
            plot_window.tabWidget_view1.change_tab_to_section(checked=True, tab_idx=0)  # change first tab to section plot
            plot = plot_window.tabWidget_view1.widget(0)

            # select a channel and plot bed level, pipes, pits
            plot.toggle_selection_tool(True)
            actions = [x for x in plot.toolbar.data_types_menu.actions() if x.text() in ['max water level']]
            _ = [x.setChecked(True) for x in actions]
            lyr = [x for x in res.map_layers() if 'PLOT_P' in x.name()][0]
            QGIS.iface.setActiveLayer(lyr)
            ch = list(lyr.getFeatures('"ID" = \'FC01.08\''))[0]
            lyr.selectByIds([ch.id()])

            # check the curve has been added to the plot
            curves = [x for x in plot.plot_graph.items() if isinstance(x, TuflowViewerCurve)]
            self.assertEqual(1, len(curves))
            self.assertTrue(curves[0].getData()[0].max() > 0)

    def test_dat_cross_sections(self):
        p = get_dataset_path('River_Sections_w_Junctions.dat', 'result')
        res = DATCrossSections(p)

        with add_result_to_viewer(res):
            plot_window = PlotWindow(get_viewer_instance())
            plot_window.tabWidget_view1.change_tab_to_section(checked=True, tab_idx=0)  # change first tab to section plot
            plot = plot_window.tabWidget_view1.widget(0)

            # select a channel and plot bed level, pipes, pits
            plot.toggle_selection_tool(True)
            actions = [x for x in plot.toolbar.data_types_menu.actions() if x.text() in ['xz', 'manning n']]
            _ = [x.setChecked(True) for x in actions]
            lyr = res.map_layers()[0]
            QGIS.iface.setActiveLayer(lyr)
            ch = list(lyr.getFeatures('"Source" = \'DS_2A\''))[0]
            lyr.selectByIds([ch.id()])

            # check the curve has been added to the plot
            curves = [x for x in plot.plot_graph.items() if isinstance(x, TuflowViewerCurve)]
            self.assertEqual(2, len(curves))

    # def test_catch_json_tmp(self):
    #     # this is ok if it fails since I was testing a big dataset
    #     p = r"C:\TUFLOW\working\Cudgen_Creek_002\Cudgen_Creek.tuflow.json"
    #     res = CATCHJson(p)
    #
    #     with add_result_to_viewer(res):
    #         plot_window = PlotWindow(get_viewer_instance())
    #         plot = plot_window.tabWidget_view1.widget(0)
    #
    #         wl_action = [x for x in plot.toolbar.data_types_menu.actions() if x.text() == 'water level'][0]
    #         wl_action.setChecked(True)
    #         marker = QgsVertexMarker(QGIS.iface.mapCanvas())
    #         marker.setColor(QColor('#000000'))
    #         point = [551886, 6866480]
    #         marker.setCenter(QgsPointXY(*point))
    #         plot.draw_tool_updated(marker, new=True)
    #
    #         curves = [x for x in plot.plot_graph.items() if isinstance(x, TuflowViewerCurve)]
    #         self.assertEqual(1, len(curves))
    #
    #         # check the curve data
    #         data = res.time_series(point, 'water level').reset_index().to_numpy(dtype=np.float64)
    #         plot_data = np.column_stack(curves[0].getData())
    #         isclose = np.isclose(data, plot_data, equal_nan=True)
    #         self.assertTrue(isclose.all())

    def test_catch_json_tmp_2(self):
        # this test was to check how many times results were being removed and replotted unnecessarily
        p = get_dataset_path('res.tuflow.json', 'result')
        res = CATCHJson(p)

        with add_result_to_viewer(res):
            plot_window = PlotWindow(get_viewer_instance())
            plot = plot_window.tabWidget_view1.widget(0)

            wl_action = [x for x in plot.toolbar.data_types_menu.actions() if x.text() == 'water level'][0]
            wl_action.setChecked(True)
            marker = QgsVertexMarker(QGIS.iface.mapCanvas())
            marker.setColor(QColor('#000000'))
            point = [1.15, 1.35]
            marker.setCenter(QgsPointXY(*point))
            plot.draw_tool_updated(marker, new=True)

            curves = [x for x in plot.plot_graph.items() if isinstance(x, TuflowViewerCurve)]
            self.assertEqual(1, len(curves))

    def test_nc_grid_time_series(self):
        p = get_dataset_path('small_model_001.nc', 'result')
        res = NCGrid(p, layer_names=['water_level'])

        with add_result_to_viewer(res):
            plot_window = PlotWindow(get_viewer_instance())
            plot = plot_window.tabWidget_view1.widget(0)

            wl_action = [x for x in plot.toolbar.data_types_menu.actions() if x.text() == 'water level'][0]
            wl_action.setChecked(True)
            marker = QgsVertexMarker(QGIS.iface.mapCanvas())
            marker.setColor(QColor('#000000'))
            point = [1.15, 1.35]
            marker.setCenter(QgsPointXY(*point))
            plot.draw_tool_updated(marker, new=True)

            curves = [x for x in plot.plot_graph.items() if isinstance(x, TuflowViewerCurve)]
            self.assertEqual(1, len(curves))

    def test_gpkg_flow_regime(self):
        p = get_dataset_path('EG15_001_TS_1D.gpkg', 'result')
        res = GPKG1D(p)

        with add_result_to_viewer(res):
            plot_window = PlotWindow(get_viewer_instance())
            plot = plot_window.tabWidget_view1.widget(0)

            plot.toggle_selection_tool(True)
            actions = [x for x in plot.toolbar.data_types_menu.actions() if x.text() in ['channel flow regime']]
            _ = [x.setChecked(True) for x in actions]
            lyr = [x for x in res.map_layers() if 'TS_1D_L' in x.name()][0]
            QGIS.iface.setActiveLayer(lyr)
            ch = list(lyr.getFeatures('"ID" = \'Pipe6\''))[0]
            lyr.selectByIds([ch.id()])

            curves = [x for x in plot.plot_graph.items() if isinstance(x, TuflowViewerCurve)]
            self.assertEqual(1, len(curves))

    def test_gpkg1d_long_plot(self):
        p = get_dataset_path('EG15_001_TS_1D.gpkg', 'result')
        res = GPKG1D(p)
        with add_result_to_viewer(res):  # context manager so results and layers are unloaded after test
            plot_window = PlotWindow(get_viewer_instance())
            plot_window.tabWidget_view1.change_tab_to_section(checked=True, tab_idx=0)  # change first tab to section plot
            plot = plot_window.tabWidget_view1.widget(0)

            # select a channel and plot bed level, pipes, pits
            plot.toggle_selection_tool(True)
            actions = [x for x in plot.toolbar.data_types_menu.actions() if x.text() in ['pits']]
            _ = [x.setChecked(True) for x in actions]
            lyr = [x for x in res.map_layers() if 'TS_1D_L' in x.name()][0]
            QGIS.iface.setActiveLayer(lyr)
            ch = list(lyr.getFeatures('"ID" IN (\'Pipe10\', \'Pipe11\') AND format_date("Datetime", \'yyyy-MM-dd HH:mm:ss\') = \'2000-01-01 00:00:00\''))
            temporal_controller.setCurrentTime(datetime(1990, 1, 1, 1, 0, 0))
            lyr.selectByIds([x.id() for x in ch])

            # check the curve has been added to the plot
            curves = [x for x in plot.plot_graph.items() if isinstance(x, TuflowViewerCurve)]
            self.assertEqual(1, len(curves))
