import numpy as np
import sys
import os
import unittest
from qgis.core import (
    QgsApplication, QgsVectorLayer, QgsRasterLayer, QgsPointXY
)
from tuflow.integrity_tool.Enumerators import *
from tuflow.integrity_tool.FeatureData import FeatureData
from tuflow.integrity_tool.DrapeData import DrapeData
from tuflow.integrity_tool.DataCollector import DataCollector
from tuflow.integrity_tool.SnappingTool import SnappingTool
from tuflow.integrity_tool.ContinuityTool import ContinuityTool
from tuflow.integrity_tool.FlowTraceTool import DataCollectorFlowTrace, FlowTraceTool, FlowTracePlot
from tuflow.integrity_tool.PipeDirectionTool import PipeDirectionTool
from tuflow.integrity_tool.helpers import SwmmHelper

# initialise QGIS data providers
argv = [bytes(x, 'utf-8') for x in sys.argv]
qgis = QgsApplication(argv, False)
qgis.initQgis()

# path to test map layers
dir = os.path.dirname(__file__)

# Switch to run for Ellis
# path_dem = r"C:\Users\esymons\Downloads\TUFLOW\model\grid\DEM_SI_Unit_01.flt"
path_dem = r"D:\models\TUFLOW\test_models\SWMM\ExampleModels\urban\TUFLOW\model\grid\DEM_SI_Unit_01.flt"


def test_file_path(geopackage_name, layer):
    return os.path.join(dir, "Swmm", geopackage_name) + '|layername=' + layer


path_pipe_conduits = test_file_path('test_pipes_001.gpkg', 'Links--Conduits')
# XSection info now embedded in Conduits
#path_pipe_xsecs = test_file_path('test_pipes_001.gpkg', 'Links--XSections')

path_junctions = test_file_path('test_pipes_001.gpkg', layer='Nodes--Junctions')
path_outfalls = test_file_path('test_pipes_001.gpkg', layer='Nodes--Outfalls')

# Broken input files
path_pipe_conduits_broken = test_file_path('test_pipes_broken_001.gpkg', 'Links--Conduits')
#path_pipe_xsecs_broken = test_file_path('test_pipes_broken_001.gpkg', 'Links--XSections')

path_junctions_broken = test_file_path('test_pipes_broken_001.gpkg', layer='Nodes--Junctions')
path_outfalls_broken = test_file_path('test_pipes_broken_001.gpkg', layer='Nodes--Outfalls')

path_snapping_output_layer_lines = test_file_path('\\output\\pipes_snapping_out.gpkg', layer='lines')
path_snapping_output_layer_pts = test_file_path('\\output\\pipes_snapping_out.gpkg', layer='lines')

path_pipe_conduits_custom = test_file_path('swmm_throsby_114_storagenode.gpkg', 'Links--Conduits')
path_junctions_custom = test_file_path('swmm_throsby_114_storagenode.gpkg', 'Links--Junctions')

# path_chan_L = os.path.join(dir, "gis", "1d_nwk_M04_channels_001_L.shp")
# path_culv_L = os.path.join(dir, "gis", "1d_nwk_M04_culverts_001_L.shp")
# path_xs = os.path.join(dir, "xs", "1d_xs_M04_creek_001_L.shp")
# path_pipe_L = os.path.join(dir, "gis", "1d_nwk_M07_Pipes_001_L.shp")
# path_pipe_L_broken = os.path.join(dir, "gis", "1d_nwk_M07_Pipes_001_L_Broken.shp")
# path_pits_P = os.path.join(dir, "gis", "1d_nwk_M07_Pits_001_P.shp")
# path_pits_P_broken = os.path.join(dir, "gis", "1d_nwk_M07_Pits_001_P_Broken.shp")
# # path_elwood_pipes = r"C:\Users\Ellis.Symons\Desktop\Ash Wright\temporary\1d_nwk_Elwood_Pipe_L.shp"
# # path_elwood_pits = r"C:\Users\Ellis.Symons\Desktop\Ash Wright\temporary\1d_nwk_Elwood_pits_P.shp"
#
# # QgsMapLayers
dem = QgsRasterLayer(path_dem, "dem_m01")

pipe_conduits_L = QgsVectorLayer(path_pipe_conduits, "Links--Conduits", "ogr")
# pipe_xsecs_L = QgsVectorLayer(path_pipe_xsecs, "Links--XSections", "ogr")
pipe_junctions_P = QgsVectorLayer(path_junctions, "Nodes--Junctions", "ogr")
pipe_outfalls_P = QgsVectorLayer(path_outfalls, "Nodes--Outfalls", "ogr")

# Broken
pipe_conduits_broken_L = QgsVectorLayer(path_pipe_conduits_broken, "Links--Conduits", "ogr")
# pipe_xsecs_broken_L = QgsVectorLayer(path_pipe_xsecs_broken, "Links--XSections", "ogr")
pipe_junctions_broken_P = QgsVectorLayer(path_junctions_broken, "Nodes--Junctions", "ogr")
pipe_outfalls_broken_P = QgsVectorLayer(path_outfalls_broken, "Nodes--Outfalls", "ogr")

# Custom cross-sections
pipe_conduits_custom_L = QgsVectorLayer(path_pipe_conduits_custom, "Links--Conduits", "ogr")
pipe_junctions_custom_P = QgsVectorLayer(path_junctions_custom, "Nodes--Junctions", "ogr")

# chan_L = QgsVectorLayer(path_chan_L, "1d_nwk_M04_channels_001_l")
# culv_L = QgsVectorLayer(path_culv_L, "1d_nwk_M04_culverts_001_L")
# xs = QgsVectorLayer(path_xs, "1d_xs_M04_creek_001_L")
# pipe_L = QgsVectorLayer(path_pipe_L, "1d_nwk_M07_Pipes_001_L")
# pipe_L_broken = QgsVectorLayer(path_pipe_L_broken, "1d_nwk_M07_Pipes_001_L_Broken")
# pits_P = QgsVectorLayer(path_pits_P, "1d_nwk_M07_Pits_001_P")
# pits_P_broken = QgsVectorLayer(path_pits_P_broken, "1d_nwk_M07_Pits_001_P_Broken")
# elwood_pipes = QgsVectorLayer(path_elwood_pipes, "1d_nwk_Elwood_Pipe_L")
# elwood_pits = QgsVectorLayer(path_elwood_pits, "1d_nwk_Elwood_pits_P")

class TestConnectionData(unittest.TestCase):
    def test_pipe_connections(self):
        self.assertTrue(pipe_conduits_L.isValid())

        swmmHelper = SwmmHelper()
        #swmmHelper.CombineLinksXsecs(pipe_conduits_L,
        #                             pipe_xsecs_L)

        dataCollectorLines = DataCollector(None)
        dataCollectorLines.setHelper(swmmHelper)
        dataCollectorLines.collectData([pipe_conduits_L], dem)
        dataCollectorPoints = DataCollector(None)
        dataCollectorPoints.setHelper(swmmHelper)
        dataCollectorPoints.collectData([pipe_junctions_P,
                                         pipe_outfalls_P],
                                        dem,
                                        [pipe_conduits_L],
                                        dataCollectorLines)

        pitConnData = dataCollectorPoints.connections['Pit17']
        self.assertEqual(sorted(pitConnData.linesUs), ['Pipe2', 'Pipe8'])
        self.assertEqual(pitConnData.linesDs, ['Pipe9'])
        self.assertEqual(pitConnData.linesUsUs, [])
        self.assertEqual(pitConnData.linesDsDs, [])

        pipeConnData = dataCollectorLines.connections['Pipe12']
        self.assertEqual(pipeConnData.pointUs, 'Pit8')
        self.assertEqual(pipeConnData.pointDs, 'Pit9')

    # def test_channel_connection(self):
    #     dataCollector = DataCollector(None)
    #     dataCollector.setHelper(SwmmHelper())
    #     dataCollector.collectData([pipe_conduits_L], dem)
    #
    #     connData = dataCollector.connections['FC01.32']
    #     self.assertEqual(sorted(connData.linesUs), ['FC01.33', '__connector__1'])
    #     self.assertEqual(sorted(connData.linesDs), ['FC01.31', '__connector__4'])
    #     self.assertEqual(connData.linesUsUs, [])
    #     self.assertEqual(connData.linesDsDs, [])
    #
    #     connData2 = dataCollector.connections['FC01.12']
    #     self.assertEqual(connData2.linesUs, ['FC01.13'])
    #     self.assertEqual(connData2.linesDs, ['FC01.2_R'])
    #     self.assertEqual(connData2.linesUsUs, [])
    #     self.assertEqual(connData2.linesDsDs, [])


class TestFeatureData(unittest.TestCase):
    def test_line_feature(self):
        swmmHelper = SwmmHelper()
        #swmmHelper.CombineLinksXsecs(pipe_conduits_L,
        #                             pipe_xsecs_L)

        featureData = None
        fid = 99999
        for f in pipe_conduits_L.getFeatures():
            featureData = FeatureData(swmmHelper, pipe_conduits_L, f)
            if featureData.id.lower() == 'pipe10':
                fid = f.id()
                break

        self.assertIsNotNone(featureData)
        self.assertEqual(featureData.id.lower(), 'pipe10')
        self.assertEqual(featureData.geomType, GEOM_TYPE.Line)
        self.assertEqual(featureData.layer.name(), "Links--Conduits")
        self.assertEqual(featureData.fid, fid)
        startVertex = QgsPointXY(293087.8447572238, 6178086.82393496)
        self.assertEqual(featureData.startVertex, startVertex)
        endVertex = QgsPointXY(293120.012276807, 6178092.347037379)
        self.assertEqual(featureData.endVertex, endVertex)
        self.assertEqual(featureData.type.lower(), 'c')
        self.assertEqual(featureData.invertUs, -99999)
        self.assertEqual(featureData.invertDs, -99999)
        self.assertAlmostEqual(featureData.invertOffsetUs, 0.0)
        self.assertAlmostEqual(featureData.invertOffsetDs, 0.18175)
        self.assertEqual(featureData.width, 0.6)
        self.assertEqual(featureData.height, 0.6)
        self.assertEqual(featureData.numberOf, 1)

    def test_point_feature(self):
        swmmHelper = SwmmHelper()

        featureData = None
        fid = 99999
        for f in pipe_junctions_P.getFeatures():
            featureData = FeatureData(swmmHelper, pipe_junctions_P, f)
            if featureData.id.lower() == 'pit9':
                fid = f.id()
                break

        self.assertIsNotNone(featureData)
        self.assertEqual(featureData.id.lower(), 'pit9')
        self.assertEqual(featureData.geomType, GEOM_TYPE.Point)
        self.assertEqual(featureData.layer.name(), "Nodes--Junctions")
        self.assertEqual(featureData.fid, fid)
        startVertex = QgsPointXY(293147.9909382345, 6178097.150920755)
        self.assertEqual(featureData.startVertex, startVertex)
        self.assertEqual(featureData.endVertex, startVertex)
        self.assertEqual(featureData.type.lower(), 'node')
        self.assertEqual(featureData.invertUs, 40.80769)
        self.assertEqual(featureData.invertDs, 40.80769)
        self.assertEqual(featureData.width, 0)
        self.assertEqual(featureData.height, 0)
        self.assertEqual(featureData.numberOf, 1)

    def test_custom_shape(self):
        swmmHelper = SwmmHelper()

        featureData = None
        fid = 99999
        for f in pipe_conduits_custom_L.getFeatures():
            featureData = FeatureData(swmmHelper, pipe_conduits_custom_L, f)
            if featureData.id.lower() == 'tc_b_0320':
                fid = f.id()
                break

        self.assertIsNotNone(featureData)
        self.assertEqual(featureData.id.lower(), 'tc_b_0320')
        self.assertEqual(featureData.geomType, GEOM_TYPE.Line)
        self.assertEqual(featureData.layer.name(), "Links--Conduits")
        self.assertEqual(featureData.fid, fid)
        self.assertEqual(featureData.type.lower(), 'custom')
        self.assertEqual(featureData.invertUs, -99999)
        self.assertEqual(featureData.invertDs, -99999)
        self.assertAlmostEqual(featureData.invertOffsetUs, 0.0)
        self.assertAlmostEqual(featureData.invertOffsetDs, 0.0)
        self.assertAlmostEqual(featureData.width, 2.81)
        self.assertAlmostEqual(featureData.height, 0.645)
        self.assertAlmostEqual(featureData.area, 1.330)
        self.assertAlmostEqual(featureData.numberOf, 1)

class TestDrapeData(unittest.TestCase):

    def test_line_drape(self):
        drapeData = None
        chainages = None
        elevations = None
        directions = None

        swmmHelper = SwmmHelper()
        #swmmHelper.CombineLinksXsecs(pipe_conduits_L,
        #                             pipe_xsecs_L)

        featureData = None
        fid = 99999
        for f in pipe_conduits_L.getFeatures():
            featureData = FeatureData(swmmHelper, pipe_conduits_L, f)
            if featureData.id.lower() == 'pipe2':
                fid = f.id()
                drapeData = DrapeData(None, "test", pipe_conduits_L, f, dem)
                break

        self.assertIsNotNone(drapeData)
        chainages = [0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0, 6.5, 7.0, 7.5, 8.0, 8.5, 9.0, 9.5,
                     10.0, 10.5, 11.0, 11.5, 12.0, 12.5, 13.0, 13.5, 14.0, 14.5, 14.716734118643839]
        self.assertEqual(drapeData.chainages, chainages)
        directions = [None, 259.6951535300408, 259.6951535300408, 259.6951535300408, 259.6951535300408,
                      259.6951535300408, 259.6951535300408, 259.6951535300408, 259.6951535300408, 259.6951535300408,
                      259.6951535300408, 259.6951535300408, 259.6951535300408, 259.6951535300408, 259.6951535300408,
                      259.6951535300408, 259.6951535300408, 259.6951535300408, 259.6951535300408, 259.6951535300408,
                      259.6951535300408, 259.6951535300408, 259.6951535300408, 259.6951535300408, 259.6951535300408,
                      259.6951535300408, 259.69515352347827, 259.6951535300408, 259.69515352347827, 259.69515352347827,
                      259.69515352435235]
        self.assertEqual(len(drapeData.directions), len(directions))
        for computed, result in zip(drapeData.directions, directions):
            if result is None:
                self.assertIsNone(computed)
            else:
                self.assertAlmostEqual(computed,result, 2)
        #self.assertEqual(drapeData.directions, directions)

        elevations = [43.776, 43.7742, 43.7777, 43.776, 43.776, 43.7742, 43.7724, 43.7765, 43.7742, 43.773, 43.7724,
                      43.7712, 43.7701, 43.7748, 43.7736, 43.7712, 43.7695, 43.7677, 43.7659, 43.7712, 43.7701,
                      43.7689, 43.7677, 43.7665, 43.7718, 43.7706, 43.7701, 43.7689, 43.7677, 43.7683, 43.7742]
        self.assertEqual(len(drapeData.elevations), len(elevations))
        for computed, result in zip(drapeData.elevations, elevations):
            if result is None:
                self.assertIsNone(computed)
            else:
                self.assertAlmostEqual(computed,result, 2)

    def test_point_drape(self):
        drapeData = None
        chainages = None
        elevations = None
        points = None

        swmmHelper = SwmmHelper()

        featureData = None
        fid = 99999
        for f in pipe_junctions_P.getFeatures():
            featureData = FeatureData(swmmHelper, pipe_junctions_P, f)
            if featureData.id.lower() == 'pit9':
                fid = f.id()
                drapeData = DrapeData(None, "Test", pipe_junctions_P, f, dem)
                break

        # directions = []
        # for f in pits_P.getFeatures():
        #     if f.attribute(0).lower() == 'pit9':
        #         drapeData = DrapeData(None, "Test", pits_P, f, dem)

        self.assertIsNotNone(drapeData)
        self.assertEqual(drapeData.chainages, [0])
        self.assertEqual(drapeData.directions, None)
        np.testing.assert_almost_equal(drapeData.elevations, [42.682], 4)
        startVertex = QgsPointXY(293147.9909382345, 6178097.150920755)
        self.assertEqual(drapeData.points, [startVertex])

class TestUnsnappedConnections(unittest.TestCase):

    def test_unsnapped_objects(self):
        swmmHelper = SwmmHelper()
        #swmmHelper.CombineLinksXsecs(pipe_conduits_broken_L,
        #                             pipe_xsecs_L)

        dataCollectorLines = DataCollector(None)
        dataCollectorLines.setHelper(swmmHelper)
        dataCollectorLines.collectData([pipe_conduits_broken_L], dem)
        dataCollectorPoints = DataCollector(None)
        dataCollectorPoints.setHelper(swmmHelper)
        dataCollectorPoints.collectData([pipe_junctions_broken_P,
                                         pipe_outfalls_P],
                                        dem,
                                        [pipe_conduits_broken_L],
                                        dataCollectorLines)

        # dataCollectorLines = DataCollector(None)
        # dataCollectorLines.collectData([pipe_L_broken], dem)
        # dataCollectorPoints = DataCollector(None)
        # dataCollectorPoints.collectData([pits_P_broken], dem, [pipe_L_broken], dataCollectorLines)

        # Because SWMM doesn't have X connectors, there are more unsapped vertices than ESTRY
        self.assertEqual(len(dataCollectorLines.unsnappedVertexes), 12)
        self.assertEqual(dataCollectorLines.unsnappedVertexes[3].id, 'Pipe19')
        self.assertEqual(dataCollectorLines.unsnappedVertexes[3].vertex, VERTEX.Last)
        self.assertEqual(dataCollectorLines.unsnappedVertexes[3].closestVertex.id, 'Pipe5')
        self.assertEqual(len(dataCollectorPoints.unsnappedVertexes), 3)
        self.assertEqual(dataCollectorPoints.unsnappedVertexes[1].id, 'Pit7')
        self.assertEqual(dataCollectorPoints.unsnappedVertexes[1].distanceToClosest, 1.1485081024527481)
        self.assertEqual(dataCollectorPoints.unsnappedVertexes[1].closestVertex.id, "Pipe10")

# Do snapping tool later. SWMM has some complications (multiple layers need to move). Junctions vs Outfalls. etc
# class TestSnappingTool(unittest.TestCase):
#
#     def test_snapping_tool(self):
#         swmmHelper = SwmmHelper()
#         swmmHelper.CombineLinksXsecs(pipe_conduits_broken_L,
#                                      pipe_xsecs_L)
#
#         dataCollectorLines = DataCollector(None)
#         dataCollectorLines.setHelper(swmmHelper)
#         dataCollectorLines.collectData([pipe_conduits_broken_L], dem)
#         dataCollectorPoints = DataCollector(None)
#         dataCollectorPoints.setHelper(swmmHelper)
#         dataCollectorPoints.collectData([pipe_junctions_broken_P,
#                                          pipe_outfalls_P],
#                                         dem,
#                                         [pipe_conduits_broken_L],
#                                         dataCollectorLines)
#
#         write_file = True
#         if write_file:
#             out_layer_lines = path_snapping_output_layer_lines
#         else:
#             out_layer_lines = None
#
#         snappingToolLines = SnappingTool(dataCollector=dataCollectorLines, dataCollectorPoints=dataCollectorPoints,
#                                          outputLyr=out_layer_lines)
#
#         if write_file:
#             out_layer_pts = path_snapping_output_layer_pts
#         else:
#             out_layer_pts = snappingToolLines.outputLyr
#         snappingToolPoints = SnappingTool(dataCollector=dataCollectorPoints, outputLyr=out_layer_pts,
#                                           dataCollectorLines=dataCollectorLines)
#
#         self.assertTrue(snappingToolLines.outputLyr.isValid())
#         self.assertEqual(snappingToolLines.outputLyr.featureCount(), 6)
#
#         snappingToolLines.autoSnap(2)
#         self.assertTrue(snappingToolLines.outputLyr.isValid())
#         self.assertEqual(snappingToolLines.outputLyr.featureCount(), 8)
#         lyr = snappingToolLines.tmpLyrs[0]
#         allFeatures = {f.attribute(0): f for f in lyr.getFeatures()}
#         feat = allFeatures['Pipe5']
#         feat2 = allFeatures['Pipe19']
#         point1 = feat.geometry().asMultiPolyline()[0][0]
#         point2 = feat2.geometry().asMultiPolyline()[0][-1]
#         self.assertEqual(point1, point2)
#
#         snappingToolPoints.autoSnap(2)
#         self.assertTrue(snappingToolPoints.outputLyr.isValid())
#         self.assertTrue((snappingToolPoints.outputLyr.featureCount()), 10)
#         lyrP = snappingToolPoints.tmpLyrs[0]
#         allFeaturesP = {f.attribute(0): f for f in lyrP.getFeatures()}
#         feat3 = allFeaturesP['Pit15']
#         point3 = feat3.geometry().asPoint()
#         point4 = feat.geometry().asMultiPolyline()[0][-1]
#         self.assertEqual(point3, point4)

# class TestXs(unittest.TestCase):
#
#     def test_xs(self):
#         dataCollector = DataCollector(None)
#         dataCollector.collectData([chan_L], tables=[xs])
#
#         feature1 = dataCollector.features['FC01.40']
#         self.assertEqual(feature1.invertUs, 48.543999999999997)
#         self.assertEqual(feature1.invertDs, 45.984000000000002)
#
#         feature2 = dataCollector.features['FC01.37']
#         self.assertEqual(feature2.invertUs, 44.6067)
#         self.assertEqual(feature2.invertDs, 44.3078)
#
#         feature3 = dataCollector.features['FC_weir1']
#         self.assertEqual(feature3.invertUs, 44.7724)
#         self.assertEqual(feature3.invertDs, 44.7724)

class TestContinuity(unittest.TestCase):
    def test_area(self):
        swmmHelper = SwmmHelper()
        #swmmHelper.CombineLinksXsecs(pipe_conduits_broken_L,
        #                             pipe_xsecs_L)

        dataCollectorLines = DataCollector(None)
        dataCollectorLines.setHelper(swmmHelper)
        dataCollectorLines.collectData([pipe_conduits_broken_L], dem)
        dataCollectorPoints = DataCollector(None)
        dataCollectorPoints.setHelper(swmmHelper)
        dataCollectorPoints.collectData([pipe_junctions_broken_P,
                                         pipe_outfalls_P],
                                        dem,
                                        [pipe_conduits_broken_L],
                                        dataCollectorLines)
        #dataCollectorLines.updateLineInverts(dataCollectorPoints)

        # dataCollector = DataCollector(None)
        # dataCollector.collectData([pipe_L_broken], dem=dem)
        # dataCollectorP = DataCollector(None)
        # dataCollectorP.collectData([pits_P_broken], lines=[pipe_L_broken], lineDataCollector=dataCollector, dem=dem)

        continuityCheck = ContinuityTool(dataCollector=dataCollectorLines, limitAngle=90, limitCover=0.5, limitArea=20,
                                         checkArea=True, checkAngle=True, checkInvert=True, checkCover=True)
        self.assertEqual(len(continuityCheck.flaggedAreas), 2)
        self.assertEqual(len(continuityCheck.flaggedInverts), 1)
        #self.assertEqual(len(continuityCheck.flaggedGradients), 2)
        self.assertEqual(len(continuityCheck.flaggedAngles), 1)
        self.assertEqual(len(continuityCheck.flaggedCover), 3)
        self.assertTrue(continuityCheck.outputLyr.isValid())
        self.assertEqual(continuityCheck.outputLyr.featureCount(), 8)


class TestFlowTrace(unittest.TestCase):

    def test_flowtrace(self):
        flowTrace_L = DataCollectorFlowTrace()
        flowTrace_P = DataCollectorFlowTrace()

        flowTrace_L.helper = SwmmHelper()
        flowTrace_P.helper = SwmmHelper()

        for f in pipe_conduits_L.getFeatures():
            if f.attribute('Name') == 'Pipe11':
                break
        flowTrace_L.collectData([pipe_conduits_L], startLocs=[(pipe_conduits_L.name(), f.id())], flowTrace=True)
        flowTrace_P.collectData([pipe_junctions_P, pipe_outfalls_P],
                                flowTrace=True, lines=[pipe_conduits_L], lineDataCollector=flowTrace_L)
        self.assertEqual(flowTrace_L.ids, ['Pipe11', 'Pipe12', 'Pipe10', 'Pipe9', 'Pipe8', 'Pipe2', 'Pipe7'])
        self.assertEqual(flowTrace_P.ids, ['Pit10', 'Pit9', 'Pit8', 'Pit7', 'Pit17', 'Pit18', 'Pit6', 'Pit19'])
        self.assertEqual(flowTrace_L.features['Pipe9'].invertUs, 41.31778)

        flowTraceTool = FlowTraceTool(dataCollector=flowTrace_L, limitAngle=90, limitCover=0.5, limitArea=20,
                                      checkArea=True, checkAngle=True, checkInvert=True, checkCover=True)
        #plot = FlowTracePlot(None, flowTraceTool)

    # def test_flowtrace_channel(self):
    #     flowTrace_L = DataCollectorFlowTrace()
    #
    #     for f in pipe_conduits_L.getFeatures():
    #         if f.attribute('Name') == 'Pipe16':
    #             break
    #     flowTrace_L.collectData([chan_L, culv_L], startLocs=[(chan_L.name(), f.id())], flowTrace=True, tables=[xs])
    #     flowTraceTool = FlowTraceTool(dataCollector=flowTrace_L, limitAngle=90, limitCover=0.5, limitArea=20,
    #                                   checkArea=True, checkAngle=True, checkInvert=True, checkCover=True)
    #
    #     x1ConnData = flowTrace_L.connections['__connector__1']
    #     self.assertEqual(x1ConnData.linesUs, ['FC_weir1'])
    #     self.assertEqual(x1ConnData.linesDs, ['FC01.32'])
    #     self.assertEqual(x1ConnData.linesUsUs, [])
    #     self.assertEqual(x1ConnData.linesDsDs, ['FC01.33'])
    #
    #     x2ConnData = flowTrace_L.connections['__connector__2']
    #     self.assertEqual(x2ConnData.linesUs, ['FC01.34'])
    #     self.assertEqual(x2ConnData.linesDs, ['FC_weir1'])
    #     self.assertEqual(x2ConnData.linesUsUs, ['FC01.33'])
    #     self.assertEqual(x2ConnData.linesDsDs, [])
    #
    #     x3ConnData = flowTrace_L.connections['__connector__3']
    #     self.assertEqual(x3ConnData.linesUs, ['TEST'])
    #     self.assertEqual(x3ConnData.linesDs, ['FC01.30'])
    #     self.assertEqual(x3ConnData.linesUsUs, [])
    #     self.assertEqual(x3ConnData.linesDsDs, ['FC01.31'])
    #
    #     x4ConnData = flowTrace_L.connections['__connector__4']
    #     self.assertEqual(x4ConnData.linesUs, ['FC01.32'])
    #     self.assertEqual(x4ConnData.linesDs, ['TEST'])
    #     self.assertEqual(x4ConnData.linesUsUs, ['FC01.31'])
    #     self.assertEqual(x4ConnData.linesDsDs, [])


#
# class TestPipeDirection(unittest.TestCase):
#
#     def test_byGradient(self):
#         pipeDirectionTool = PipeDirectionTool()
#         pipeDirectionTool.byGradient([pipe_L_broken])
#
#         self.assertTrue(pipeDirectionTool.outputLyr.isValid())
#         self.assertEqual(pipeDirectionTool.outputLyr.featureCount(), 2)
#
#     def test_byContinuity(self):
#         dataCollector = DataCollector()
#         dataCollector.collectData([pipe_L_broken])
#         pipeDirectionTool = PipeDirectionTool()
#         pipeDirectionTool.byContinuity([pipe_L_broken], dataCollector)
#
#         self.assertTrue(pipeDirectionTool.outputLyr.isValid())
#         self.assertEqual(pipeDirectionTool.outputLyr.featureCount(), 1)

if __name__ == '__main__':
    unittest.main()
