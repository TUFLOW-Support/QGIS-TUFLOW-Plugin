import os
import re
import typing

from PyQt5.QtWidgets import QApplication
from qgis._core import QgsLayerTreeLayer, QgsProject
from qgis.core import QgsMapLayer, QgsVectorLayer, QgsWkbTypes
from qgis.utils import plugins

from .map_layer import file_from_data_source, layer_name_from_data_source
from .file import find_parent_dir, find_highest_matching_file
from ..compatibility_routines import Path

from tuflow.toc.toc import node_to_layer

def get_command_properties(name: str) -> typing.Dict[str, typing.Any]:
    empty_dir = plugins['tuflow'].plugin_dir / 'empty_tooltips'
    found = []
    for file in empty_dir.glob('*.*'):
        if file.stem.lower() in name.lower():
            found.append(file)
    found = sorted(found, key=lambda x: len(x.stem), reverse=True)
    if found:
        file = found[0]
        with open(str(file), 'r') as f:
            return {x.split('==')[0].strip(): x.split('==')[1].strip() for x in f.read().split('\n') if x.strip()}
    return {}


def try_find_control_file(file: Path, cf: str) -> Path:
    if 'tuflow control file' in cf.lower():
        ext = '.tcf'
    elif 'estry control file' in cf.lower():
        ext = '.ecf'
    elif 'geometry control file' in cf.lower():
        ext = '.tgc'
    elif 'bc control file' in cf.lower():
        ext = '.tbc'
    elif re.findall(r'\(.*\)', cf):
        ext = re.findall(r'\(.*\)', cf)[0].strip('()')
    else:
        return
    tf_dir = find_parent_dir(file, 'tuflow')
    model_dir = find_parent_dir(file, 'model')
    if tf_dir and model_dir:
        if len(model_dir.parts) - len(tf_dir.parts) > 3 or len(tf_dir.parts) <= 2:
            root = model_dir.parent
        else:
            root = tf_dir
    elif model_dir:
        root = model_dir.parent
    else:
        root = file.parent.parent.parent
        if ext == '.tcf':
            return root / 'runs' / 'dummy.tcf'
        else:
            return root / 'model' / 'dummy{0}'.format(ext)
    matching_file = find_highest_matching_file(root, '*{0}'.format(ext))
    if matching_file:
        return matching_file
    else:
        if ext == '.tcf':
            return root / 'runs' / 'dummy.tcf'
        else:
            return root / 'model' / 'dummy{0}'.format(ext)


class TuflowCommand:

    def __new__(cls, layer: QgsVectorLayer):
        if layer.storageType() == 'GPKG':
            cls = TuflowCommandGPKG
        elif layer.storageType() == 'ESRI Shapefile':
            cls = TuflowCommandSHP
        elif layer.storageType() == 'MapInfo File':
            cls = TuflowCommandMapinfo
        else:
            return
        self = super().__new__(cls)
        self._init(layer)
        return self

    def __repr__(self):
        return '<{0} {1}>'.format(self.__class__.__name__, self.name)

    def _init(self, layer: QgsVectorLayer) -> None:
        self.valid = False
        self.layer = layer
        self.ds = layer.dataProvider().dataSourceUri()
        self.file = file_from_data_source(self.ds)
        self.name = layer_name_from_data_source(self.ds)
        self.prop = get_command_properties(self.name)
        if not self.prop:
            return
        self.cf = try_find_control_file(self.file, self.prop['location'])
        self.valid = self.cf is not None

    @property
    def command(self) -> str:
        if self.valid:
            return '{0} == {1}'.format(self.command_left, self.command_right)
        return ''

    @property
    def command_right(self) -> str:
        if self.valid:
            relpath = os.path.relpath(self.file, str(self.cf.parent))
            return '{0}'.format(relpath)
        return ''

    @property
    def command_left(self) -> str:
        if self.valid:
            return self.prop['command']
        return ''

    def append(self, layer: QgsVectorLayer) -> bool:
        return False


class TuflowCommandMapinfo(TuflowCommand):
    pass


class TuflowCommandSHP(TuflowCommand):

    def _init(self, layer: QgsVectorLayer) -> None:
        super()._init(layer)
        self._in_right = False
        self.commands = [self]

    def appendable(self, command: 'TuflowCommand') -> bool:
        appendable_types = ['2d_zsh', '2d_bc', '2d_ztin', '2d_vzsh', '2d_bg', '2d_lfcsh', '2d_cyc', '2d_hur']
        for a in appendable_types:
            if a.lower() in self.name.lower() and a.lower() in command.name.lower():
                return True
        return False

    def append(self, layer: QgsVectorLayer) -> bool:
        command = TuflowCommand(layer)
        if self.valid and command.valid and self.appendable(command):
            if len(self.commands) > 1 and type(command) != type(self):
                for c in self.commands:
                    if type(c) == type(command):
                        c.commands.append(command)
                        return True
            self.commands.append(command)
            return True
        return False

    def command_iter(self) -> typing.Generator['TuflowCommand', None, None]:
        d = {QgsWkbTypes.PolygonGeometry: 0, QgsWkbTypes.LineGeometry: 1, QgsWkbTypes.PointGeometry: 2}
        for command in sorted(self.commands, key=lambda x: d[x.layer.geometryType()]):
            yield command

    @property
    def command_right(self) -> str:
        if self.valid:
            if len(self.commands) == 1 or self._in_right:
                return super().command_right
            self._in_right = True
            rhs = ' | '.join([x.command_right for x in self.command_iter()])
            self._in_right = False
            return rhs
        return ''


class TuflowCommandGPKG(TuflowCommandSHP):

    def _init(self, layer: QgsVectorLayer) -> None:
        super()._init(layer)
        self.type = 'path'

    @property
    def command_right(self) -> str:
        if self.valid and self.type == 'name':
            return ' | '.join([x.name for x in self.command_iter()])
        if self.valid and len(self.commands) == 1 and self.file.stem.lower() == self.name.lower():
            return super().command_right
        dbs = [x for x, y in self.db_iter()]
        if self.valid and len(dbs) == 1:
            return '{0} >> {1}'.format(TuflowCommand.command_right.fget(self),
                                       ' && '.join([x.name for x in self.command_iter()]))
        elif self.valid:
            commands = []
            for db, command in self.db_iter():
                relpath = os.path.relpath(db, str(command.cf.parent))
                if isinstance(command, TuflowCommandGPKG):
                    c = '{0} >> {1}'.format(relpath, ' && '.join(self.names(db)))
                else:
                    c = TuflowCommandSHP.command_right.fget(command)
                commands.append(c)
            return ' | '.join(commands)
        return ''

    def db_iter(self) -> typing.Generator[Path, None, None]:
        db = []
        for command in self.command_iter():
            if command.file not in db:
                db.append(command.file)
                yield command.file, command

    def names(self, db: Path) -> typing.List[str]:
        return [x.name for x in self.command_iter() if x.file == db]


def create_tuflow_command(type_: str = 'path') -> str:
    tree_view = plugins['tuflow'].iface.layerTreeView()
    idxs = tree_view.selectionModel().selectedIndexes()
    i = -1
    command_str = ''
    while idxs:
        idx = idxs.pop(0)
        node = tree_view.index2node(idx)
        layer = node_to_layer(node)
        if not layer:
            continue
        i += 1
        command = TuflowCommand(layer)
        if isinstance(command, TuflowCommandGPKG):
            command.type = type_
        while idxs:
            lyr = node_to_layer(tree_view.index2node(idxs[0]))
            if not lyr:
                idxs.pop(0)
                continue
            if command.append(lyr):
                idxs.pop(0)
            else:
                break
        if i == 0:
            command_str = command.command
        else:
            command_str = '{0}\n{1}'.format(command_str, command.command)
    return command_str


def create_tuflow_command_path(a: bool = False) -> None:
    command = create_tuflow_command()
    QApplication.clipboard().setText(command)


def create_tuflow_command_name(a: bool = False) -> None:
    command = create_tuflow_command('name')
    QApplication.clipboard().setText(command)
