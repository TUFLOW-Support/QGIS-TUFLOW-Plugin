from pathlib import Path

from qgis.core import QgsDataItem, Qgis, QgsMimeDataUtils
from qgis.PyQt import QtGui

from . import (pytuflow, Logging, get_pytuflow_class, TuflowDataItemBaseMixin, RunFilters, TuflowLayerItem,
               BROWSER_LAYER_TYPE, TuflowTableItem, get_browser_helper)


class ControlFileItem(QgsDataItem, TuflowDataItemBaseMixin):
    """QgsDataItem class representing TUFLOW control files."""

    def __init__(self, path, parent=None, inp=None, trd_path=None):
        path = Path(path).resolve()
        super().__init__(Qgis.BrowserItemType.Custom, parent, Path(path).name, str(path), 'tuflow_plugin')
        self._init_tuflow_data_item_base_mixin(self.path(), inp)
        self._init_filter_state()
        self.cf = None
        self.set_tooltip()
        self.setState(Qgis.BrowserItemState.NotPopulated)
        self.setCapabilitiesV2(Qgis.BrowserItemCapability.Fertile
                               | Qgis.BrowserItemCapability.RefreshChildrenWhenItemIsRefreshed
                               )
        self.file_refs = {}
        self.trd_path = trd_path
        self.cur_trd = None

    def equal(self, other):
        return False

    def sortKey(self):
        return self.sort_key()

    def hasChildren(self):
        return True

    def icon(self):
        if self.state() == Qgis.BrowserItemState.Populating:
            return QgsDataItem.icon(self)  # returns loading icon while populating
        try:
            path = Path(__file__).parents[2] / 'icons' / 'TUFLOW.ico'
            icon = QtGui.QIcon(str(path))
            return self.apply_icon_overlays(icon)
        except Exception:
            return QtGui.QIcon()

    def hasDragEnabled(self):
        return True

    def actions(self, parent):
        actions = []
        actions.extend(self.tuflow_base_actions(parent))
        browser_helper = get_browser_helper()
        if browser_helper:
            action_populate = QtGui.QAction('Populate Children', parent)
            action_populate.triggered.connect(lambda x=self: browser_helper.populate_children(self))
            actions.append(action_populate)

        return actions

    def mimeUris(self):
        u = QgsMimeDataUtils.Uri()
        u.layerType = 'custom'
        u.providerKey = 'tuflow_plugin'
        u.name = self.name()
        u.uri = self.path()
        return [u]

    def createChildren(self):
        try:
            children = self._create_children(self)
        except Exception:
            return []

        try:
            if not self.inp:
                control_file_class = get_pytuflow_class(self._path)
                if control_file_class is None:
                    return children
                self.cf = control_file_class(self.path())
                run_filter = RunFilters().filter(self.path())
                if run_filter:
                    try:
                        self.cf = self.cf.context(run_filter)
                    except Exception as e:
                        Logging.warning(f'Failed to apply run filter to control file in QGIS Browser: {e}', silent=True)
                        self.add_warnings([f'Failed to apply run filter: {run_filter}: {e}'])
                        return children
            elif self.trd_path:
                self.cf = self._inp.parent
            else:
                self.cf = [x for x in self._inp.cf if x.fpath == Path(self.path()).resolve()][0]
        except Exception:
            return children

        if self.inp and isinstance(self._inp, pytuflow.BuildState) and RunFilters().filter(self._path):
            run_filter = RunFilters().filter(self._path)
            try:
                self.cf = self.cf.context(run_filter)
            except Exception as e:
                Logging.warning(f'Failed to apply run filter to control file in QGIS Browser: {e}', silent=True)
                self.add_warnings([f'Failed to apply run filter: {run_filter}: {e}'])
                return children

        desired_inputs = [
            pytuflow.const.INPUT.GIS,
            pytuflow.const.INPUT.GRID,
            pytuflow.const.INPUT.CF,
            pytuflow.const.INPUT.DB,
            pytuflow.const.INPUT.DB_MAT,
        ]

        if self.trd_path:
            func = lambda x: x.TUFLOW_TYPE in desired_inputs and x.trd_input == self.inp[0]
        else:
            func = lambda x: x.TUFLOW_TYPE in desired_inputs

        for inp in self.cf.find_input(recursive=False, callback=func):
            if inp.trd and not self.trd_path:
                if self.cur_trd == inp.trd:
                    continue
                self.cur_trd = inp.trd
                inp = inp.trd_input
            elif self.cur_trd:
                self.cur_trd = None

            if inp.TUFLOW_TYPE in [pytuflow.const.INPUT.CF, pytuflow.const.INPUT.TRD]:
                try:
                    for file in inp.files:
                        file = file.resolve()
                        if file in self.file_refs:
                            data_item = self.file_refs[file]
                            data_item.add_input(inp)
                            continue
                        try:
                            data_item = ControlFileItem(str(file), None, inp, self.cur_trd)
                        except Exception as e:
                            Logging.warning(f'Failed to create ControlFileDataItem for {file} in QGIS Browser: {e}', silent=True)
                            continue

                        data_item.dataChanged.connect(self.add_warnings_from_child)
                        data_item.setState(Qgis.BrowserItemState.NotPopulated)
                        children.append(data_item)
                        self.file_refs[file] = data_item
                except Exception as e:
                    pass
            elif inp.TUFLOW_TYPE in [pytuflow.const.INPUT.GIS, pytuflow.const.INPUT.GRID]:
                try:
                    for file in inp.files:
                        file = pytuflow.TuflowPath(file)
                        if file.suffix.lower() == '.prj':
                            file_shp = file.with_suffix('.shp')
                            if file.exists() and not file_shp.exists():
                                continue
                            file = file_shp
                        if file in self.file_refs:
                            data_item = self.file_refs[file]
                            data_item.add_input(inp)
                            continue
                        if not file.exists():
                            layer_type = Qgis.BrowserLayerType.Vector if inp.TUFLOW_TYPE == pytuflow.const.INPUT.GIS else Qgis.BrowserLayerType.Raster
                            try:
                                lyrname = file.lyrname if file.lyrname else file.stem
                                data_item = TuflowLayerItem(None, lyrname, str(file), 'tuflow_plugin', inp, layer_type)
                            except Exception as e:
                                Logging.warning(f'Failed to create TuflowLayerDataItem for {file} in QGIS Browser: {e}', silent=True)
                                continue
                            data_item.dataChanged.connect(self.add_warnings_from_child)
                            data_item.setState(Qgis.BrowserItemState.NotPopulated)
                            children.append(data_item)
                            self.file_refs[file] = data_item
                        elif file.is_vector_gis():
                            for geom in file.geometry_types():
                                if file.suffix.lower() == '.gpkg':
                                    uri = f'{file.dbpath}|layername={file.lyrname}'
                                elif file.suffix.lower() == '.mif':
                                    uri = f'{file.dbpath}|geometrytype={geom}'
                                elif file.suffix.lower() == '.mid':
                                    uri = '{0}|geometrytype={1}'.format(file.dbpath.with_suffix('.mif'), geom)
                                elif file.suffix.lower() == '.prj':
                                    uri = '{0}|geometrytype={1}'.format(file.dbpath.with_suffix('.shp'), geom)
                                else:
                                    uri = str(file.dbpath)
                                try:
                                    data_item = TuflowLayerItem(None, file.lyrname, uri, 'ogr', inp, BROWSER_LAYER_TYPE.get(geom, Qgis.BrowserLayerType.Vector))
                                except Exception as e:
                                    Logging.warning(f'Failed to create TuflowLayerDataItem for {file} in QGIS Browser: {e}', silent=True)
                                    continue
                                data_item.dataChanged.connect(self.add_warnings_from_child)
                                data_item.setState(Qgis.BrowserItemState.NotPopulated)
                                children.append(data_item)
                                self.file_refs[file] = data_item
                        elif file.is_raster_gis():
                            if file.suffix.lower() == '.gpkg':
                                uri = f'GPKG:{file.dbpath}:{file.lyrname}'
                                lyrname = file.lyrname
                            else:
                                uri = str(file.dbpath)
                                lyrname = file.stem
                            try:
                                data_item = TuflowLayerItem(None, lyrname, uri, 'gdal', inp, Qgis.BrowserLayerType.Raster)
                            except Exception as e:
                                Logging.warning(f'Failed to create TuflowLayerDataItem for {file} in QGIS Browser: {e}', silent=True)
                                continue
                            data_item.dataChanged.connect(self.add_warnings_from_child)
                            data_item.setState(Qgis.BrowserItemState.NotPopulated)
                            children.append(data_item)
                            self.file_refs[file] = data_item
                except Exception as e:
                    pass
            elif inp.TUFLOW_TYPE in [pytuflow.const.INPUT.DB, pytuflow.const.INPUT.DB_MAT]:
                try:
                    for file in inp.files:
                        file = file.resolve()
                        if file in self.file_refs:
                            data_item = self.file_refs[file]
                            data_item.add_input(inp)
                            continue
                        if file.suffix.lower() == '.csv':
                            try:
                                data_item = TuflowLayerItem(None, file.name, str(file), 'ogr', inp, Qgis.BrowserLayerType.Table)
                            except Exception as e:
                                Logging.warning(f'Failed to create TuflowLayerDataItem for {file} in QGIS Browser: {e}', silent=True)
                                continue
                        else:
                            try:
                                data_item = TuflowTableItem(Qgis.BrowserItemType.Custom, None, file.name, str(file), 'tuflow_plugin', inp)
                            except Exception as e:
                                Logging.warning(f'Failed to create TuflowTableItem for {file} in QGIS Browser: {e}', silent=True)
                                continue
                        data_item.dataChanged.connect(self.add_warnings_from_child)
                        data_item.setState(Qgis.BrowserItemState.NotPopulated)
                        data_item.setCapabilitiesV2(data_item.capabilities2() | Qgis.BrowserItemCapability.ItemRepresentsFile)
                        children.append(data_item)
                        self.file_refs[file] = data_item
                except Exception as e:
                    pass

        return children
