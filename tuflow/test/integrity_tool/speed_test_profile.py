import sys
import os
from qgis.core import QgsApplication, QgsVectorLayer
from ..integrity_tool.FlowTraceTool import DataCollectorFlowTrace, FlowTraceTool, FlowTracePlot

# initialise QGIS data providers
argv = [bytes(x, 'utf-8') for x in sys.argv]
qgis = QgsApplication(argv, False)
qgis.initQgis()

# path to test map layers
path_elwood_pipes = r"C:\Users\Ellis.Symons\Desktop\Ash Wright\temporary\1d_nwk_Elwood_Pipe_L.shp"
path_elwood_pits = r"C:\Users\Ellis.Symons\Desktop\Ash Wright\temporary\1d_nwk_Elwood_pits_P.shp"

# QgsVectorLayers
elwood_pipes = QgsVectorLayer(path_elwood_pipes, "1d_nwk_Elwood_Pipe_L")
elwood_pits = QgsVectorLayer(path_elwood_pits, "1d_nwk_Elwood_pits_P")

if __name__ == '__main__':
    if elwood_pipes.isValid():
        flowTrace_L = DataCollectorFlowTrace()
        flowTrace_P = DataCollectorFlowTrace()

        for f in elwood_pipes.getFeatures():
            if f.attribute(0) == '15311':
                break
        flowTrace_L.collectData([elwood_pipes], startLocs=[(elwood_pipes.name(), f.id())], flowTrace=True)
        flowTrace_P.collectData([elwood_pits], flowTrace=True, lines=[elwood_pipes], lineDataCollector=flowTrace_L)
        flowTraceTool = FlowTraceTool(dataCollector=flowTrace_L, limitAngle=90, limitCover=0.5, limitArea=20,
                                      checkArea=True, checkAngle=True, checkInvert=True, checkCover=True)
        plot = FlowTracePlot(None, flowTraceTool)