from PyQt5.QtCore import Qt
from qgis._core import QgsProject
from qgis.core import Qgis

from nc_grid_data_provider import NetCDFGrid, LoadError
from tuflow.tuflowqgis_dialog import tuflowqgis_scenarioSelection_dialog

try:
    from pathlib import Path
except ImportError:
    from pathlib_ import Path_ as Path


class TuResultsNcGrid:

    def __init__(self, tuView=None):
        self.tuView = tuView
        self.iface = tuView.iface
        self.results = {}

    def importResults(self, inFileNames, **kwargs):
        qv = Qgis.QGIS_VERSION_INT
        if qv < 31600:
            print('Not supported for earlier QGIS versions before version 3.16')
            return

        # disconnect incoming signals for load step
        skipConnect = False
        try:
            self.tuView.project.layersAdded.disconnect(self.tuView.layersAdded)
        except:
            skipConnect = True

        for j, f in enumerate(inFileNames):
            if 'layers' in kwargs:
                selected_layers = kwargs['layers']
            else:
                layers = [x for x in NetCDFGrid.nc_grid_layers(f)]
                if not layers:
                    if not NetCDFGrid.capable():
                        raise LoadError(
                            'NetCDF4 Python library not installed. Please see the following wiki page for more information:<p>'
                            '<a href="https://wiki.tuflow.com/index.php?title=TUFLOW_Viewer_-_Load_Results_-_NetCDF_Grid"'
                            '<span style=" text-decoration: underline; color:#0000ff;">wiki.tuflow.com/index.php?title=TUFLOW_Viewer_-_Load_Results_-_NetCDF_Grid'
                            '</span></a>')
                    if not NetCDFGrid.is_nc_grid(f):
                        raise LoadError('Format is not recognised as a NetCDF raster.')
                dlg = tuflowqgis_scenarioSelection_dialog(self.iface, f, layers)
                dlg.setWindowTitle('Layer Selection')
                dlg.exec_()
                if not dlg.status:
                    return
                selected_layers = dlg.scenarios

            for layer in selected_layers:
                # Load
                mLayer, name = self._load_file(f, layer)

                self.tuView.tuResults.updateDateTimes()

                if mLayer is None or name is None:
                    if not skipConnect:
                        self.tuView.project.layersAdded.connect(self.tuView.layersAdded)
                    return False

                # Open layer in map
                self.tuView.project.addMapLayer(mLayer)
                mLayer.nameChanged.connect(lambda: self.tuView.tuResults.tuResults2D.layerNameChanged(mLayer, name,
                                                                         mLayer.name()))  # if name is changed can capture this in indexing

                # add to result list widget
                names = []
                for i in range(self.tuView.OpenResults.count()):
                    if self.tuView.OpenResults.item(i).text() not in names:
                        names.append(self.tuView.OpenResults.item(i).text())
                if name not in names:
                    self.tuView.OpenResults.addItem(name)  # add to widget
                k = self.tuView.OpenResults.findItems(name, Qt.MatchRecursive)[0]
                k.setSelected(True)
                self.tuView.resultChangeSignalCount = 0  # reset signal count back to 0

        # connect load signals
        if not skipConnect:
            self.tuView.project.layersAdded.connect(self.tuView.layersAdded)

        return True

    def _load_file(self, filename, layer_name):
        display_name = '{0} - {1}'.format(Path(filename).stem, layer_name)
        uri = 'NetCDF:{0}:{1}'.format(filename, layer_name)
        try:
            nc_grid = NetCDFGrid(uri, display_name)
        except LoadError as e:
            print(e)
            return

        defaultRefTime = self.tuView.tuOptions.zeroTime
        self.tuView.tuResults.results[display_name] = {}

        # populate resdata
        timekey2time = self.tuView.tuResults.timekey2time  # dict
        zeroTime = nc_grid.reference_time
        if self.tuView.OpenResults.count() == 0:
            self.tuView.tuOptions.zeroTime = zeroTime
            if self.iface is not None:
                self.tuView.tuOptions.timeSpec = self.iface.mapCanvas().temporalRange().begin().timeSpec()
                self.tuView.tuResults.loadedTimeSpec = self.iface.mapCanvas().temporalRange().begin().timeSpec()
            else:
                self.tuView.tuOptions.timeSpec = 1
                self.tuView.tuResults.loadedTimeSpec = 1

        timesteps = nc_grid.times  # relative time
        for t in timesteps:
            timekey2time['{0:.6f}'.format(t)] = t

        self.tuView.tuResults.results[display_name]["_nc_grid"] = {
            'times': {'{0:.6f}'.format(x): [x] for x in timesteps},
            'referenceTime': nc_grid.reference_time}

        # add to internal storage
        self.results[display_name] = [nc_grid, timesteps]

        # load first step
        self.updateActiveTime()

        return nc_grid, display_name

    def layerNameChanged(self, old_name, new_name):
        if old_name in self.results:
            self.results[new_name] = self.results[old_name]
            del self.results[old_name]

    def updateActiveTime(self, date=None):
        if date is None:
            active_date = self.tuView.tuResults.activeTime
        else:
            active_date = date

        nc_grid = None
        selectedResults = [x.text() for x in self.tuView.OpenResults.selectedItems()]
        for res_name, data in self.results.items():
            nc_grid = data[0]

            if res_name not in selectedResults or active_date is None:
                time_index = None
            else:
                # find closest
                for time_index, date in enumerate(nc_grid.timesteps('absolute')):
                    if date == active_date:
                        break
                    if date > active_date:
                        if time_index == 0:
                            break
                        else:
                            diff = abs((date - active_date).total_seconds())
                            if diff > 0.01:
                                time_index -= 1
                            break

            # update nc grid band
            if nc_grid is not None:
                legint = QgsProject.instance().layerTreeRoot()
                node = legint.findLayer(nc_grid.id())
                band = time_index + 1 if time_index is not None else None
                if band is None and node is not None:
                    node.setItemVisibilityChecked(False)
                else:
                    if node is not None:
                        node.setItemVisibilityChecked(True)
                    nc_grid.update_band(band)
                nc_grid.triggerRepaint()

    def removeResults(self, resList, **kwargs):
        """
        Removes the Particles results from the indexed results and ui.

        :param resList: list -> str result name e.g. M01_5m_001
        :return: bool -> True for successful, False for unsuccessful
        """

        remove_layer = kwargs['remove_layer'] if 'remove_layer' in kwargs else True

        results = self.tuView.tuResults.results

        try:
            self.tuView.project.layersWillBeRemoved.disconnect(self.tuView.layersRemoved)
        except:
            pass

        for res in resList:
            if res in self.results:
                if res in results:
                    del results[res]
                layer = self.results[res][0]
                if remove_layer:
                    try:
                        self.tuView.project.removeMapLayer(layer.id())
                        del layer
                    except:
                        pass

                del self.results[res]

            for i in range(self.tuView.OpenResults.count()):
                item = self.tuView.OpenResults.item(i)
                if item is not None and item.text() == res:
                    if res not in results:
                        self.tuView.OpenResults.takeItem(i)

        if self.tuView.canvas is not None:
            self.tuView.canvas.refresh()
        self.tuView.tuResults.updateResultTypes()
        self.tuView.project.layersWillBeRemoved.connect(self.tuView.layersRemoved)

        return True

    def active_grids(self):
        selectedResults = [x.text() for x in self.tuView.OpenResults.selectedItems()]
        for res_name, data in self.results.items():
            if res_name in selectedResults:
                yield data[0]

    def grids(self):
        for res_name, data in self.results.items():
            yield data[0]
