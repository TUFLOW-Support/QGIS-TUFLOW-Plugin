from qgis.core import QgsMesh, QgsMeshSpatialIndex, QgsGeometryUtils
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMessageBox
from tuflow.canvas_event import *
from tuflow.tuflowqgis_tuviewer.tuflowqgis_turubberband import TuRubberBand
from tuflow.tuflowqgis_library import findMeshIntersects
from tuflow.tuflowqgis_tuviewer.tuflowqgis_turesultsindex import TuResultsIndex
import numpy as np
from matplotlib.collections import PolyCollection
from matplotlib.quiver import Quiver
from matplotlib.colorbar import ColorbarBase
from matplotlib import cm
from matplotlib.colors import Normalize
from mpl_toolkits.axes_grid1 import make_axes_locatable
from datetime import datetime, timedelta
from math import sin, cos, pi



class TuPlot3D():
    """
    Class for handling 3d plotting such as profile and curtain plotting
    """

    def __init__(self, tuPlot):
        self.tuPlot = tuPlot
        self.tuView = tuPlot.tuView
        self.tuResults = self.tuView.tuResults
        self.iface = self.tuView.iface
        self.colSpec = dict(cmap=cm.jet, clim=[0, 40], norm=Normalize(0, 0.5))
        self.collection = None

        self.plotSelectionCurtainFeat = []

    def plotCurtainFromMap(self, vLayer, feat, **kwargs):

        from tuflow.tuflowqgis_tuviewer.tuflowqgis_tuplot import TuPlot


        activeMeshLayers = self.tuResults.tuResults2D.activeMeshLayers  # list
        results = self.tuResults.results  # dict

        # Check that line is a polyline
        if vLayer is not None:  # if none then memory layer
            if vLayer.geometryType() != QgsWkbTypes.LineGeometry:
                return

        # deal with the kwargs
        bypass = kwargs['bypass'] if 'bypass' in kwargs.keys() else False  # bypass clearing any data from plot
        draw = kwargs['draw'] if 'draw' in kwargs.keys() else True
        timestep = kwargs['time'] if 'time' in kwargs.keys() else None  # export kwarg
        featName = kwargs['featName'] if 'featName' in kwargs else None
        resultTypes = kwargs['types'] if 'types' in kwargs.keys() else []  # export kwarg
        update = kwargs['update'] if 'update' in kwargs else False  # update only

        # clear the plot based on kwargs
        if not bypass:
            self.tuPlot.clearPlot2(TuPlot.CrossSection, TuPlot.DataCurtainPlot)

        # initialise plotting variables
        data = []
        labels = []
        types = []
        dataTypes = []
        plotAsCollection = []
        plotAsQuiver = []
        plotAsPatch = []

        for layer in activeMeshLayers:
            # get mesh information and spatial index the mesh
            dp = layer.dataProvider()
            mesh = QgsMesh()
            dp.populateMesh(mesh)
            si = QgsMeshSpatialIndex(mesh)

            # get mesh intersects
            if not update:
                self.inters, self.chainages, self.faces = findMeshIntersects(si, dp, mesh, feat, self.iface.mapCanvas().mapUnits(),
                                                                             self.tuView.project)
                update = True  # turn on update now - allow only one line at the moment

            # loop through result types
            if not resultTypes:  # specified result types can be passed through kwargs (used for batch export not normal plotting)
                resultTypes = self.tuPlot.tuPlotToolbar.getCheckedItemsFromPlotOptions(TuPlot.DataCurtainPlot)
                key = lambda x: 1 if 'vector' in x.lower() else 0
                resultTypes = sorted(resultTypes, key=key)
            for rtype in resultTypes:
                # time
                if not timestep:
                    timestep = self.tuView.tuResults.activeTime
                if timestep == 'Maximum' or timestep == -99999 or timestep == '-99999.000000':
                    isMax = True
                else:
                    isMax = self.tuView.tuResults.isMax(rtype)
                if timestep == 'Minimum' or timestep == 99999 or timestep == '99999.000000':
                    isMin = True
                else:
                    isMin = self.tuView.tuResults.isMin(rtype)

                # get QgsMeshDatasetIndex
                tuResultsIndex = TuResultsIndex(layer.name(), rtype, timestep, isMax, isMin)
                meshDatasetIndex = self.tuView.tuResults.getResult(tuResultsIndex, force_get_time='next lower')
                if not meshDatasetIndex:
                    continue
                elif type(meshDatasetIndex) is dict:
                    continue
                meshDatasetIndex = meshDatasetIndex[-1]

                # collect and arrange data
                if 'vector' in rtype.lower():
                    self.getVectorData(dp, meshDatasetIndex, self.faces, self.chainages, self.inters, update)
                    data.append(self.quiver)
                    plotAsQuiver.append(True)
                    plotAsCollection.append(False)
                else:
                    self.getScalarData(dp, meshDatasetIndex, self.faces, self.chainages, update, rtype)
                    data.append(self.collection)
                    plotAsCollection.append(True)
                    plotAsQuiver.append(False)

                labels.append(rtype)
                types.append(rtype)
                plotAsPatch.append(True)

        dataTypes = [TuPlot.DataCurtainPlot] * len(data)
        self.tuPlot.drawPlot(TuPlot.CrossSection, data, labels, types, dataTypes, draw=True,
                             plot_as_collection=plotAsCollection, plot_as_patch=plotAsPatch,
                             plot_as_quiver=plotAsQuiver)

        return True

    def getScalarData(self, dp, mdi, faces, ch, update, rtype):
        """

        """

        d = []
        x = []
        y = []
        for i, f in enumerate(faces):
            data3d = dp.dataset3dValues(mdi, f, 1)
            vlc = data3d.verticalLevelsCount()
            if vlc:
                vlc = vlc[0]
            else:
                continue
            vl = data3d.verticalLevels()
            v = data3d.values()

            for j in range(vlc):
                x.append([ch[i], ch[i + 1], ch[i + 1], ch[i]])
                y.append([vl[j + 1], vl[j + 1], vl[j], vl[j]])
                if len(v) == 2 * vlc:  # x,y components
                    m = v[j*2] ** 2 + v[j*2 + 1] ** 2
                    m = m ** 0.5
                    d.append(m)
                else:
                    d.append(v[j])

        xy = np.dstack((np.array(x), np.array(y)))
        values = np.array(d)
        #if update and self.collection is not None:  # testing to see if quicker just to update collection
        #    pf = datetime.now()  # profiling
        #    self.collection.set_verts(xy)
        #    self.collection.set_array(values)
        #    self.co_stuff += datetime.now() - pf  # profiling
        #else:
        self.colSpec['clim'] = self.getMinMaxValue(dp, mdi.group())
        self.collection = PolyCollection(xy, array=values, edgecolor='face', label=rtype, **self.colSpec)

    def getVectorData(self, dp, mdi, faces, ch, points, update):
        """

        """

        uc = []
        vc = []
        x = []
        y = []
        for i, f in enumerate(faces):
            data3d = dp.dataset3dValues(mdi, f, 1)
            vlc = data3d.verticalLevelsCount()
            if vlc:
                vlc = vlc[0]
            else:
                continue
            vl = data3d.verticalLevels()
            v = data3d.values()

            # line angle - rotate x,y velocity to local line angle u,v
            a = QgsGeometryUtils.lineAngle(points[i].x(), points[i].y(), points[i+1].x(), points[i+1].y())
            a = pi / 2 - a  # qgis is angle clockwise from north - need to adjust to be counter clockwise from horizontal
            r = np.array([[cos(a), -sin(a)], [sin(a), cos(a)]])  # rotation matrix

            for j in range(vlc):
                x.append((ch[i] + ch[i + 1]) / 2.)
                y.append((vl[j] + vl[j + 1]) / 2.)
                if len(v) == 2 * vlc:  # x,y components
                    vel = np.array([[v[j*2]], [-v[j*2 + 1]]])
                    uc.append(np.dot(r, vel)[0, 0])  # u component needed only
                    vc.append(0)
                else:
                    QMessageBox.critical(self.tuView, "Error", "Should not be here [getVectorData]")
                    return

        xy = np.hstack((x, y))
        self.quiver = [x, y, uc, vc]

    def getMinMaxValue(self, dp, mdgi):
        """

        """

        isMax = self.tuResults.isMinimumResultType
        isMin = self.tuResults.isMinimumResultType
        stripMax = self.tuResults.stripMaximumName
        stripMin = self.tuResults.stripMinimumName

        minimum = 99999
        maximum = -99999
        mdg = dp.datasetGroupMetadata(mdgi)
        name = mdg.name()

        # check dataset
        minimum = min(minimum, mdg.minimum())
        maximum = max(maximum, mdg.maximum())

        # check maximum/minimum datasets (if exist)
        for i in range(dp.datasetGroupCount()):
            n = dp.datasetGroupMetadata(i).name()
            if isMin(n):
                if name == stripMin(n):
                    minimum = min(minimum, dp.datasetGroupMetadata(i).minimum())
            if isMax(n):
                if name == stripMax(n):
                    maximum = max(maximum, dp.datasetGroupMetadata(i).maximum())

        # fail safes
        if minimum == 99999:
            minimum = 0
        if maximum == -99999:
            maximum = 1

        return minimum, maximum


class TuCurtainLine(TuRubberBand):
    """
    Class for handling curtain line graphic
    """

    def __init__(self, tuPlot, plotNo):
        TuRubberBand.__init__(self, tuPlot, plotNo)
        self.colour = Qt.green
        self.symbol = QgsVertexMarker.ICON_DOUBLE_TRIANGLE

    def clearPlot(self, firstPlot):
        """
        Overrides clearPlot method with specific plot clearing settings.
        """

        from tuflow.tuflowqgis_tuviewer.tuflowqgis_tuplot import TuPlot

        if firstPlot:
            self.tuPlot.clearPlot2(TuPlot.CrossSection)
        else:
            self.tuPlot.clearPlot2(TuPlot.CrossSection, TuPlot.DataCurtainPlot)

    def plotFromRubberBand(self, feat, bypass=False):
        """
        Overrides plotFromRubberBand method with specific plotting function.
        """

        return self.tuPlot.tuPlot3D.plotCurtainFromMap(None, feat)

    def unpressButton(self):
        """
        Overrides unpressButton method.
        """

        self.tuPlot.tuPlotToolbar.curtainPlotMenu.menuAction().setChecked(False)


class ColourBar(ColorbarBase):

    def __init__(self, patch, cax, location='right', offset=0.03, thickness=0.025, label=''):
        # Get target axes handle
        if type(patch).__name__ == 'TriContourSet':
            target = patch.ax
        else:
            target = patch.axes
        figure = target.figure

        if offset > 0:
            offset_1 = offset
            offset_2 = 0
        else:
            offset_1 = 0
            offset_2 = offset

        # Determine rectangles for target axes & colour bar axes
        # rec = target.get_position().extents
        # if location == 'bottom':
        #     rec1 = [rec[0], rec[1] + offset_1, rec[2] - rec[0], rec[3] - rec[1] - offset_1]
        #     rec2 = [rec[0], rec[1] + offset_2, rec[2] - rec[0], thickness]
        # elif location == 'top':
        #     rec1 = [rec[0], rec[1], rec[2] - rec[0], rec[3] - rec[1] - offset_1]
        #     rec2 = [rec[0], rec[3] - offset_2, rec[2] - rec[0], thickness]
        # elif location == 'left':
        #     rec1 = [rec[0] + offset_1, rec[1], rec[2] - rec[0] - offset_1, rec[3] - rec[1]]
        #     rec2 = [rec[0] + offset_2, rec[1], thickness, rec[3] - rec[1]]
        # elif location == 'right':
        #     rec1 = [rec[0], rec[1], rec[2] - rec[0] - offset_1, rec[3] - rec[1]]
        #     rec2 = [rec[2] - offset_2, rec[1], thickness, rec[3] - rec[1]]
        # else:  # default to bottom
        #     rec1 = [rec[0], rec[1] + offset_1, rec[2] - rec[0], rec[3] - rec[1] - offset_1]
        #     rec2 = [rec[0], rec[1] + offset_2, rec[2] - rec[0], thickness]

        # rec2[1] = rec[3]

        # target.set_position(rec1)
        # axes = target.figure.add_axes(rec2)

        # Set orientation
        if location == 'bottom' or location == 'top':
            orientation = 'horizontal'
        elif location == 'left' or location == 'right':
            orientation = 'vertical'
        else:  # default bottom
            orientation = 'horizontal'

        # Initialize ColorbarBase
        super(ColourBar, self).__init__(cax, patch.cmap, patch.norm, orientation=orientation)

        # Finish formatting
        # if orientation == 'horizontal':
        #     axes.xaxis.set_ticks_position(location)
        #     axes.xaxis.set_label_position(location)
        #     axes.set_xlabel(label)
        # elif orientation == 'vertical':
        #     axes.yaxis.set_ticks_position(location)
        #     axes.yaxis.set_label_position(location)
        #     axes.set_ylabel(label)
        # else:  # default bottom
        #     axes.xaxis.set_ticks_position(location)
        #     axes.xaxis.set_label_position(location)
        #     axes.set_xlabel(label)