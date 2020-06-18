import os
from qgis.core import QgsMesh, QgsMeshSpatialIndex, QgsGeometryUtils
from PyQt5.QtCore import Qt, QVariant
from PyQt5.QtWidgets import QMessageBox
from tuflow.canvas_event import *
from tuflow.tuflowqgis_tuviewer.tuflowqgis_turubberband import TuRubberBand, TuMarker
from tuflow.tuflowqgis_library import (findMeshIntersects, calcMidPoint, writeTempPoints, meshToPolygon,
                                       writeTempPolys, getFaceIndex)
from tuflow.tuflowqgis_tuviewer.tuflowqgis_turesultsindex import TuResultsIndex
from tuflow.tuflowqgis_tuviewer.tuflowqgis_tuplot2d import TuPlot2D
from tuflow.tuflowqgis_tuviewer.tuflowqgis_turesults import TuResults
import numpy as np
from matplotlib.collections import PolyCollection
from matplotlib.quiver import Quiver
from matplotlib.colorbar import ColorbarBase
from matplotlib import cm
from matplotlib.colors import Normalize
from matplotlib.colors import LinearSegmentedColormap
from mpl_toolkits.axes_grid1 import make_axes_locatable
from datetime import datetime, timedelta
from math import sin, cos, pi
import statistics



# bmtblue = {
#     'red':  ((0.0, 1.0, 1.0),
#              (0.5, 26.0 / 255.0, 26.0 / 255.0),
#              (1.0, 0.0, 0.0)),
#     'green': ((0.0, 1.0, 1.0),
#               (0.5, 189.0 / 255.0, 189.0 / 255.0),
#               (1.0, 85.0 / 255.0, 85.0 / 255.0)),
#     'blue': ((0.0, 1.0, 1.0),
#              (0.5, 201.0 / 255.0, 201.0 / 255.0),
#              (1.0, 129.0 / 255.0, 129.0 / 255.0))
# }
# cm_bmtblue = LinearSegmentedColormap('bmt_blue', bmtblue)
# cm.register_cmap(name="bmt_blue", cmap=cm_bmtblue)
#
bmtbluepink = {
    'red':  ((0.0, 0.0, 0.0),
             (0.25, 26.0 / 255.0, 26.0 / 255.0),
             (0.5, 1.0, 1.0),
             (0.75, 241.0 / 255.0, 241.0 / 255.0),
             (1.0, 226.0 / 255.0, 226.0 / 255.0)),
    'green': ((0.0, 85.0 / 255.0, 85.0 / 255.0),
             (0.25, 189.0 / 255.0, 189.0 / 255.0),
             (0.5, 1.0, 1.0),
             (0.75, 120.0 / 255.0, 120.0 / 255.0),
             (1.0, 1.0 / 255.0, 1.0 / 255.0)),
    'blue': ((0.0, 129.0 / 255.0, 129.0 / 255.0),
             (0.25, 201.0 / 255.0, 201.0 / 255.0),
             (0.5, 1.0, 1.0),
             (0.75, 185.0 / 255.0, 185.0 / 255.0),
             (1.0, 119.0 / 255.0, 119.0 / 255.0))
}
cm_bmtbluepink = LinearSegmentedColormap('bmt_blue_pink', bmtbluepink)
cm.register_cmap(name="bmt_blue_pink", cmap=cm_bmtbluepink)
#
# bmtblueyellowred = {
#     'red':  ((0.0, 0.0, 0.0),
#              (0.25, 26.0 / 255.0, 26.0 / 255.0),
#              (0.5, 1.0, 1.0),
#              (0.75, 253.0 / 255.0, 253.0 / 255.0),
#              (1.0, 215.0 / 255.0, 215.0 / 255.0)),
#     'green': ((0.0, 85.0 / 255.0, 85.0 / 255.0),
#              (0.25, 189.0 / 255.0, 189.0 / 255.0),
#              (0.5, 1.0, 1.0),
#              (0.75, 174.0 / 255.0, 174.0 / 255.0),
#              (1.0, 25.0 / 255.0, 25.0 / 255.0)),
#     'blue': ((0.0, 129.0 / 255.0, 129.0 / 255.0),
#              (0.25, 201.0 / 255.0, 201.0 / 255.0),
#              (0.5, 191.0 / 255.0, 191.0 / 255.0),
#              (0.75, 97.0 / 255.0, 97.0 / 255.0),
#              (1.0, 28.0 / 255.0, 28.0 / 255.0))
# }
# cm_bmtblueyellowred = LinearSegmentedColormap('bmt_blue_yellow_red', bmtblueyellowred)
# cm.register_cmap(name="bmt_blue_yellow_red", cmap=cm_bmtblueyellowred)



class TuPlot3D(TuPlot2D):
    """
    Class for handling 3d plotting such as various depth averaging methods, profile and curtain plotting
    """

    def __init__(self, tuPlot):
        TuPlot2D.__init__(self, tuPlot)
        self.colSpec = dict(cmap=cm.jet, clim=[0, 40], norm=Normalize(0, 0.5))
        self.collection = None

        self.plotSelectionCurtainFeat = []
        self.plotSelectionVPFeat = []

    def getAveragingMethods(self, dataType, gmd, resultTypes):
        """

        """

        return self.tuPlot.tuPlotToolbar.getAveragingMethods(dataType, gmd)

    def plotVerticalProfileFromMap(self, vLayer, point, **kwargs):

        from tuflow.tuflowqgis_tuviewer.tuflowqgis_tuplot import TuPlot

        activeMeshLayers = self.tuResults.tuResults2D.activeMeshLayers  # list
        results = self.tuResults.results  # dict

        # Check that layer is points
        if vLayer is not None:  # if none then memory layer
            if vLayer.geometryType() != QgsWkbTypes.PointGeometry:
                return

        if type(point) is QgsFeature:
            point = point.geometry().asPoint()  # if feature is passed in as argument, convert to QgsPointXY

        # deal with the kwargs
        bypass = kwargs['bypass'] if 'bypass' in kwargs.keys() else False  # bypass clearing any data from plot
        plot = kwargs['plot'] if 'plot' in kwargs.keys() else ''
        resultTypes = kwargs['types'] if 'types' in kwargs.keys() else []  # export kwarg
        resultMesh = kwargs['mesh'] if 'mesh' in kwargs.keys() else []  # export kwarg
        timestep = kwargs['time'] if 'time' in kwargs.keys() else None  # export kwarg
        timestepFormatted = kwargs['time_formatted'] if 'time_formatted' in kwargs.keys() else ''
        export = kwargs['export'] if 'export' in kwargs.keys() else None  # 'csv' or 'image'
        exportOut = kwargs['export_location'] if 'export_location' in kwargs.keys() else None
        exportFormat = kwargs['export_format'] if 'export_format' in kwargs.keys() else None
        name = kwargs['name'] if 'name' in kwargs.keys() else None
        draw = kwargs['draw'] if 'draw' in kwargs.keys() else True
        meshRendered = kwargs['mesh_rendered'] if 'mesh_rendered' in kwargs.keys() else True
        plotActiveScalar = kwargs['plot_active_scalar'] if 'plot_active_scalar' in kwargs else False
        featName = kwargs['featName'] if 'featName' in kwargs else None
        markerNo = kwargs['markerNo'] if 'markerNo' in kwargs else 0
        dataType = kwargs['data_type'] if 'data_type' in kwargs else TuPlot.DataVerticalProfile

        # clear the plot based on kwargs
        if bypass:
            pass
        else:
            if not resultTypes:  # specified result types can be passed through kwargs (used for batch export not normal plotting)
                resultTypes = self.tuPlot.tuPlotToolbar.getCheckedItemsFromPlotOptions(dataType)
            if not resultMesh:  # specified result meshes can be passed through kwargs (used for batch export not normal plotting)
                resultMesh = activeMeshLayers
            self.tuPlot.clearPlot2(TuPlot.VerticalProfile, dataType,
                                   last_only=self.tuView.cboSelectType.currentText() == 'From Map Multi',
                                   remove_no=len(resultTypes) * len(resultMesh))

        # Initialise variables
        data = []
        labels = []
        types = []
        dataTypes = []
        plotAsCollection = []
        plotAsQuiver = []
        plotAsPatch = []
        xMagnitudes = []  # used to position arrows relative to scalar magnitudes - not passed into drawplot function
        plotVertMesh = []

        # iterate through all selected results
        if not resultMesh:  # specified result meshes can be passed through kwargs (used for batch export not normal plotting)
            resultMesh = activeMeshLayers
        for layer in resultMesh:  # get plotting for all selected result meshes
            dp = layer.dataProvider()
            mesh = QgsMesh()
            dp.populateMesh(mesh)
            si = QgsMeshSpatialIndex(mesh)

            # get plotting for all checked result types
            if not resultTypes:  # specified result types can be passed through kwargs (used for batch export not normal plotting)
                resultTypes = self.tuPlot.tuPlotToolbar.getCheckedItemsFromPlotOptions(dataType)

                # deal with active scalar plotting
                if plotActiveScalar:
                    if plotActiveScalar == 'active scalar':
                        if self.tuView.tuResults.tuResults2D.activeScalar not in resultTypes:
                            resultTypes += [self.tuView.tuResults.tuResults2D.activeScalar]
                    else:  # do both active scalar and [depth for water level] - tumap specific
                        if plotActiveScalar not in resultTypes:
                            resultTypes.append(plotActiveScalar)
                        if plotActiveScalar == 'Depth' or plotActiveScalar == 'D':
                            if 'Water Level' in self.tuResults.results[layer.name()]:
                                if 'Water Level' not in resultTypes:
                                    resultTypes.append('Water Level')
                            elif 'H' in self.tuResults.results[layer.name()]:
                                if 'H' not in resultTypes:
                                    resultTypes.append('H')

            key = lambda x: 1 if 'vector' in x.lower() else 0
            resultTypes = sorted(resultTypes, key=key)
            for i, rtype in enumerate(resultTypes):
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
                gmd = dp.datasetGroupMetadata(meshDatasetIndex.group())
                if gmd.dataType() == QgsMeshDatasetGroupMetadata.DataOnVertices:
                    onFaces = False
                else:
                    onFaces = True

                # for am in avgmethods:
                types.append(rtype)
                x, y, vm = self.getScalarDataPoint(point, layer, dp, si, mesh, meshDatasetIndex, meshRendered, onFaces,
                                                   isMax, isMin)
                xMagnitudes.append(x)
                data.append((x, y))
                plotAsCollection.append(False)
                plotAsQuiver.append(False)
                plotAsPatch.append(False)
                plotVertMesh.append(False)
                dataTypes.append(TuPlot.DataVerticalProfile)

                # legend label for multi points
                label = self.generateLabel(layer, resultMesh, rtype, markerNo, featName,
                                           activeMeshLayers, None, export, bypass, i, dataType)

                if label is not None:
                    labels.append(label)
                else:
                    labels.append('')

                # vertical mesh - dummy x values (only concerned with y values)
                data.append(([1, 2, 3], vm))
                labels.append('{0} - Vertical Mesh'.format(layer.name()))
                plotVertMesh.append(True)
                plotAsCollection.append(False)
                plotAsQuiver.append(False)
                plotAsPatch.append(False)
                dataTypes.append(TuPlot.DataVerticalMesh)
                types.append('Vertical Mesh')

        # increment point count for multi select
        if bypass:  # multi select click
            self.multiPointSelectCount += 1

        # data = list(zip(xAll, yAll))
        # dataTypes = [dataType] * len(data)
        if data:
            if export is None:  # normal plot i.e. in tuview
                self.tuPlot.drawPlot(TuPlot.VerticalProfile, data, labels, types, dataTypes, draw=draw,
                                     plot_as_collection=plotAsCollection, plot_as_patch=plotAsPatch,
                                     plot_as_quiver=plotAsQuiver, plot_vert_mesh=plotVertMesh)
            elif export == 'image':  # plot through drawPlot however instead of drawing, save figure
                # unique output file name
                outFile = '{0}{1}'.format(os.path.join(exportOut, name), exportFormat)
                iterator = 1
                while os.path.exists(outFile):
                    outFile = '{0}_{2}{1}'.format(os.path.join(exportOut, name), exportFormat, iterator)
                    iterator += 1
                self.tuPlot.drawPlot(TuPlot.VerticalProfile, data, labels, types, dataTypes,
                                     plot_as_collection=plotAsCollection, plot_as_patch=plotAsPatch,
                                     plot_as_quiver=plotAsQuiver, export=outFile, plot_vert_mesh=plotVertMesh)
            elif export == 'csv':  # export to csv, don't plot
                self.tuPlot.exportCSV(TuPlot.TimeSeries, data, labels, types, exportOut, name)
                self.tuPlot.exportCSV(TuPlot.VerticalProfile, data, labels, types, exportOut)
            else:  # catch all other cases and just do normal, although should never be triggered
                self.tuPlot.drawPlot(TuPlot.VerticalProfile, data, labels, types, dataTypes, draw=draw,
                                     plot_as_collection=plotAsCollection, plot_as_patch=plotAsPatch,
                                     plot_as_quiver=plotAsQuiver, plot_vert_mesh=plotVertMesh)

        return True

    def plotCurtainFromMap(self, vLayer, feat, **kwargs):

        from tuflow.tuflowqgis_tuviewer.tuflowqgis_tuplot import TuPlot

        debug = self.tuView.tuOptions.writeMeshIntersects
        activeMeshLayers = self.tuResults.tuResults2D.activeMeshLayers  # list
        results = self.tuResults.results  # dict

        # Check that line is a polyline
        if vLayer is not None:  # if none then memory layer
            if vLayer.geometryType() != QgsWkbTypes.LineGeometry:
                return
            crs = vLayer.sourceCrs()
        else:
            crs = self.tuView.project.crs()

        # deal with the kwargs
        bypass = kwargs['bypass'] if 'bypass' in kwargs.keys() else False  # bypass clearing any data from plot
        draw = kwargs['draw'] if 'draw' in kwargs.keys() else True
        timestep = kwargs['time'] if 'time' in kwargs.keys() else None  # export kwarg
        featName = kwargs['featName'] if 'featName' in kwargs else None
        resultTypes = kwargs['types'] if 'types' in kwargs.keys() else []  # export kwarg
        update = kwargs['update'] if 'update' in kwargs else False  # update only
        # animation stuff
        name = kwargs['name'] if 'name' in kwargs.keys() else None
        export = kwargs['export'] if 'export' in kwargs.keys() else None  # 'csv' or 'image'
        exportOut = kwargs['export_location'] if 'export_location' in kwargs.keys() else None
        exportFormat = kwargs['export_format'] if 'export_format' in kwargs.keys() else None
        plotActiveScalar = kwargs['plot_active_scalar'] if 'plot_active_scalar' in kwargs else False

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
                gmd = dp.datasetGroupMetadata(meshDatasetIndex.group())
                if gmd.dataType() == QgsMeshDatasetGroupMetadata.DataOnVertices:
                    onFaces = False
                else:
                    onFaces = True

                # get mesh intersects
                if not update:
                    self.inters, self.chainages, self.faces = findMeshIntersects(si, dp, mesh, feat, crs,
                                                                                 self.tuView.project)
                    update = True  # turn on update now - allow only one line at the moment
                    if not onFaces:
                        self.points = [calcMidPoint(self.inters[i], self.inters[i+1], crs) for i in range(len(self.inters) - 1)]
                        if debug:
                            writeTempPoints(self.inters, self.tuView.project, crs, self.chainages, 'Chainage', QVariant.Double)
                    else:
                        onFaces = True
                        self.points = self.faces[:]
                        if debug:
                            polys = [meshToPolygon(mesh, mesh.face(x)) for x in self.faces]
                            writeTempPolys(polys, self.tuView.project, crs)
                            writeTempPoints(self.inters, self.tuView.project, crs, self.chainages, 'Chainage',
                                            QVariant.Double)


                # collect and arrange data
                if 'vector' in rtype.lower():
                    self.getVectorDataCurtain(layer, dp, si, mesh, meshDatasetIndex, self.points,
                                              self.chainages, self.inters, update, onFaces, isMax, isMin)
                    data.append(self.quiver)
                    plotAsCollection.append(False)
                    plotAsQuiver.append(True)
                else:
                    self.getScalarDataCurtain(layer, dp, si, mesh, meshDatasetIndex, self.points,
                                              self.chainages, update, rtype, onFaces, isMax, isMin)
                    data.append(self.collection)
                    plotAsCollection.append(True)
                    plotAsQuiver.append(False)

                labels.append(rtype)
                types.append(rtype)
                plotAsPatch.append(True)

        dataTypes = [TuPlot.DataCurtainPlot] * len(data)
        if export is None:
            self.tuPlot.drawPlot(TuPlot.CrossSection, data, labels, types, dataTypes, draw=draw,
                                 plot_as_collection=plotAsCollection, plot_as_patch=plotAsPatch,
                                 plot_as_quiver=plotAsQuiver)
        elif export == 'image':  # plot through drawPlot however instead of drawing, save figure
            # unique output file name
            outFile = '{0}{1}'.format(os.path.join(exportOut, name), exportFormat)
            iterator = 1
            while os.path.exists(outFile):
                outFile = '{0}_{2}{1}'.format(os.path.join(exportOut, name), exportFormat, iterator)
                iterator += 1
            self.tuPlot.drawPlot(TuPlot.CrossSection, data, labels, types, dataTypes, draw=draw,
                                 plot_as_collection=plotAsCollection, plot_as_patch=plotAsPatch,
                                 plot_as_quiver=plotAsQuiver, export=outFile)
        elif export == 'csv':  # export to csv, don't plot
            pass  # for now
        else:
            self.tuPlot.drawPlot(TuPlot.CrossSection, data, labels, types, dataTypes, draw=draw,
                                 plot_as_collection=plotAsCollection, plot_as_patch=plotAsPatch,
                                 plot_as_quiver=plotAsQuiver)

        return True

    def getScalarDataPoint(self, point, layer, dp, si, mesh, mdi, meshRendered, onFaces, isMax, isMin):
        """

        """

        from tuflow.tuflowqgis_tuviewer.tuflowqgis_tuplot import TuPlot

        x, y, vm = [], [], []
        if onFaces:
            if meshRendered:
                data3d = layer.dataset3dValue(mdi, point)
            else:
                faces = si.nearestNeighbor(point, 1)
                face = faces[0] if faces else None
                data3d = dp.dataset3dValues(mdi, face, 1) if face else None

            if isinstance(data3d, QgsMesh3dDataBlock):
                vlc = data3d.verticalLevelsCount()[0] if data3d.verticalLevelsCount() else 0
                x = data3d.values()
                if len(x) == 2 * vlc:  # vector (x, y) -> get magnitude
                    x = [ ( x[i] ** 2 + x[i+1] ** 2 ) ** 0.5 for i in range(0, len(x), 2) ]
                y = data3d.verticalLevels()
                vm = y[:]
                if self.tuView.tuOptions.verticalProfileInterpolated:
                    y = [ ( y[i] + y[i+1] ) / 2. for i in range(0, len(y) - 1) ]  # point halfway between levels
                else:
                    x = sum([[x, x] for x in x], [])
                    y = sum([[x, x] for x in y], [])[1:-1]
        else:
            x = [self.datasetValue(layer, dp, si, mesh, mdi, False, point, 0, TuPlot.DataVerticalProfile, None) for x in range(2)]
            y = self.getBedAndWaterElevation(layer, dp, si, mesh, mdi, False, point, 0, TuPlot.DataVerticalProfile, None,
                                             isMax, isMin)
            vm = y[:]

        return x, y, vm

    def getScalarDataCurtain(self, layer, dp, si, mesh, mdi, faces, ch, update, rtype, onFaces, isMax, isMin):
        """

        """

        from tuflow.tuflowqgis_tuviewer.tuflowqgis_tuplot import TuPlot

        edgecolour = ((0,0,0,1),) if self.tuPlot.verticalMesh_action.isChecked() else 'face'

        d = []
        x = []
        y = []
        xi = 0  # index for chainage - can be different due to null areas
        for i, f in enumerate(faces):
            if onFaces:
                data3d = dp.dataset3dValues(mdi, f, 1)
                vlc = data3d.verticalLevelsCount()
                if vlc:
                    vlc = vlc[0]
                else:
                    continue
                vl = data3d.verticalLevels()
                v = data3d.values()
            else:
                vlc = 1
                v = [self.datasetValue(layer, dp, si, mesh, mdi, False, f, 0, TuPlot.DataCurtainPlot, None)]
                vl = self.getBedAndWaterElevation(layer, dp, si, mesh, mdi, False, f, 0, TuPlot.DataCurtainPlot, None,
                                                  isMax, isMin)

            if not np.isnan(v).any():
                for j in range(vlc):
                    # get correct ch index - this can be different because the first point could be outside mesh
                    if len(self.inters) - 1 >= xi + 1:
                        while getFaceIndex(self.inters[xi], si, mesh, p2=self.inters[xi+1]) is None:
                            xi += 1
                            if len(self.inters) - 1 < xi + 1:
                                break
                    if len(self.inters) - 1 < xi + 1 or getFaceIndex(self.inters[xi], si, mesh, p2=self.inters[xi+1]) is None:
                        break  # don't think it should ever get here

                    x.append([ch[xi], ch[xi + 1], ch[xi + 1], ch[xi]])
                    y.append([vl[j + 1], vl[j + 1], vl[j], vl[j]])
                    if len(v) == 2 * vlc:  # x,y components
                        m = v[j*2] ** 2 + v[j*2 + 1] ** 2
                        m = m ** 0.5
                        d.append(m)
                    else:
                        d.append(v[j])
            xi += 1

        xy = np.dstack((np.array(x), np.array(y)))
        values = np.array(d)
        #if update and self.collection is not None:  # testing to see if quicker just to update collection
        #    pf = datetime.now()  # profiling
        #    self.collection.set_verts(xy)
        #    self.collection.set_array(values)
        #    self.co_stuff += datetime.now() - pf  # profiling
        #else:
        self.colSpec['clim'] = self.getMinMaxValue(dp, mdi.group())
        self.collection = PolyCollection(xy, array=values, edgecolor=edgecolour, label=rtype, **self.colSpec)

    def getVectorDataCurtain(self, layer, dp, si, mesh, mdi, faces, ch, points, update, onFaces, isMax, isMin):
        """

        """

        from tuflow.tuflowqgis_tuviewer.tuflowqgis_tuplot import TuPlot

        uc = []
        vc = []
        x = []
        y = []
        for i, f in enumerate(faces):
            if onFaces:
                data3d = dp.dataset3dValues(mdi, f, 1)
                vlc = data3d.verticalLevelsCount()
                if vlc:
                    vlc = vlc[0]
                else:
                    continue
                vl = data3d.verticalLevels()
                v = data3d.values()
            else:
                vlc = 1
                v = self.datasetValue(layer, dp, si, mesh, mdi, False, f, 0, TuPlot.DataCurtainPlot, None, value='vector')
                if type(v) is tuple:
                    v = v[1:]
                else:
                    v = [v]
                vl = self.getBedAndWaterElevation(layer, dp, si, mesh, mdi, False, f, 0, TuPlot.DataCurtainPlot, None,
                                                  isMax, isMin)

            # line angle - rotate x,y velocity to local line angle u,v
            a = QgsGeometryUtils.lineAngle(points[i].x(), points[i].y(), points[i+1].x(), points[i+1].y())
            a = pi / 2 - a  # qgis is angle clockwise from north - need to adjust to be counter clockwise from horizontal
            r = np.array([[cos(a), -sin(a)], [sin(a), cos(a)]])  # rotation matrix

            if not np.isnan(v).any():
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

        mn, mx = self.getMinMaxValue(dp, mdi.group())
        config = {
            # 'scale': 0.0025,
            'scale': mx,
            "scale_units": 'inches',
            "width": 0.0025,
            "headwidth": 2.5,
            "headlength": 3,
        }
        self.quiver.append(config)
        self.quiver.append(mx/4)

    def getMinMaxValue(self, dp, mdgi):
        """

        """

        isMax = TuResults.isMinimumResultType
        isMin = TuResults.isMinimumResultType
        stripMax = TuResults.stripMaximumName
        stripMin = TuResults.stripMinimumName

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

    def getBedAndWaterElevation(self, layer, dp, si, mesh, mdi, meshRendered, f, ind, dataType, am, isMax, isMin):
        """

        """

        possibleWlNames = ['water level', 'water surface elevation']
        possibleBdNames = ['bed elevation']
        iBedGmd = None  # bed group metadata index
        iWlGmd = None  # water level group metadata index
        for i in range(dp.datasetGroupCount()):
            name = dp.datasetGroupMetadata(i).name()
            if name.lower() in possibleBdNames:
                iBedGmd = i
                continue
            if isMax:
                if TuResults.isMaximumResultType(name):
                    name = TuResults.stripMaximumName(name)
                    if name.lower() in possibleWlNames:
                        iWlGmd = i
            elif isMin:
                if TuResults.isMinimumResultType(name):
                    name = TuResults.stripMinimumName(name)
                    if name.lower() in possibleWlNames:
                        iWlGmd = i
            else:
                if name.lower() in possibleWlNames:
                    iWlGmd = i

        if iBedGmd is None: return [0, 0]
        if iWlGmd is None: return [0, 0]

        bedGmdMdi = QgsMeshDatasetIndex(iBedGmd, 0)  # bed elevation is constant
        wlGmdMdi = None
        rt = dp.datasetMetadata(mdi).time()  # reference time
        for i in range(dp.datasetCount(iWlGmd)):
            tmdi = QgsMeshDatasetIndex(iWlGmd, i)  # test mesh dataset index
            time = dp.datasetMetadata(tmdi).time()
            if time == rt:
                wlGmdMdi =  tmdi
                break

        if wlGmdMdi is None: return [0, 0]

        bed = self.datasetValue(layer, dp, si, mesh, bedGmdMdi, meshRendered, f, ind, dataType, am)
        wl = self.datasetValue(layer, dp, si, mesh, wlGmdMdi, meshRendered, f, ind, dataType, am)
        return [bed, wl]



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


class TuDepthAvRubberBand(TuRubberBand):
    """
    Class for handling curtain line graphic
    """

    def __init__(self, tuPlot, plotNo):
        TuRubberBand.__init__(self, tuPlot, plotNo)
        self.colour = Qt.darkGreen
        self.symbol = QgsVertexMarker.ICON_DOUBLE_TRIANGLE

    def clearPlot(self, firstPlot):
        """
        Overrides clearPlot method with specific plot clearing settings.
        """

        from tuflow.tuflowqgis_tuviewer.tuflowqgis_tuplot import TuPlot


        self.tuPlot.clearPlot2(TuPlot.CrossSection, TuPlot.DataCrossSectionDepAv)

    def plotFromRubberBand(self, feat, bypass=False):
        """
        Overrides plotFromRubberBand method with specific plotting function.
        """

        from tuflow.tuflowqgis_tuviewer.tuflowqgis_tuplot import TuPlot

        return self.tuPlot.tuPlot3D.plotCrossSectionFromMap(None, feat, bypass=bypass, lineNo=len(self.rubberBands),
                                                            data_type=TuPlot.DataCrossSectionDepAv)

    def unpressButton(self):
        """
        Overrides unpressButton method.
        """

        self.tuPlot.tuPlotToolbar.averageMethodCSMenu.menuAction().setChecked(False)


class TuDepthAvPoint(TuMarker):

    def __init__(self, tuPlot, plotNo):
        TuMarker.__init__(self, tuPlot, plotNo)
        self.colour = Qt.darkGreen
        self.symbol = QgsVertexMarker.ICON_CIRCLE
        self.allowLiveTracking = True

    def clearPlot(self, firstTimePlotting: bool, lastOnly: bool = False) -> None:
        """

        """

        from tuflow.tuflowqgis_tuviewer.tuflowqgis_tuplot import TuPlot

        #if firstTimePlotting:
        resultTypes = self.tuPlot.tuPlotToolbar.getCheckedItemsFromPlotOptions(TuPlot.DataTimeSeriesDepAv)
        activeMeshLayers = self.tuView.tuResults.tuResults2D.activeMeshLayers
        self.tuPlot.clearPlot2(TuPlot.TimeSeries, TuPlot.DataTimeSeriesDepAv, last_only=lastOnly,
                               remove_no=len(resultTypes) * len(activeMeshLayers))

    def plotFromMarker(self, point: QgsPointXY, bypass: bool = False) -> bool:
        """

        """

        from tuflow.tuflowqgis_tuviewer.tuflowqgis_tuplot import TuPlot

        return self.tuPlot.tuPlot3D.plotTimeSeriesFromMap(None, point, bypass=bypass, markerNo=len(self.points),
                                                          data_type=TuPlot.DataTimeSeriesDepAv)

    def unpressButton(self) -> None:
        """

        """

        self.tuPlot.tuPlotToolbar.averageMethodTSMenu.menuAction().setChecked(False)


class ColourBar(ColorbarBase):
    """
    Stolen from tfv python library. Modified slightly to use cax - as this lets tight_layout() work.
    """

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