import sys
import os
from qgis.core import QgsApplication, QgsVectorLayer
from ..integrity_tool.DataCollector import DataCollector


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
        dataCollector = DataCollector()
        dataCollector.collectData([elwood_pipes])
    
    
    