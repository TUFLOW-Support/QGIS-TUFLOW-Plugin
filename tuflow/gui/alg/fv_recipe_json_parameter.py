import json
import re
import typing

from qgis.gui import QgsGui, QgsMessageBar
from qgis.PyQt.QtWidgets import QWidget, QMenu, QTreeWidgetItem
from qgis.PyQt.QtGui import QAction, QColor

from .processing_parameter_json import (QgsProcessingParameterJson, JsonWidget, 
                                        JsonWidgetFactory, JsonWidgetWrapper)

import tuflow.pt.pytuflow as pt


class FVRecipeParameter(QgsProcessingParameterJson):
    """Subclass Json Parameter and customise specifically for
    the FV Recipe Json parameter.
    """
    TYPE = 'FVRecipeJsonParameter'

    def clone(self) -> "FVRecipeParameter":
        copy = FVRecipeParameter(self.name(), self.description())
        copy.setDefaultValue(self.defaultValue())
        copy.setFlags(self.flags())
        return copy

    @classmethod
    def registerWidget(cls) -> None:
        """Register the widget factory. Call once at plugin load time."""
        QgsGui.processingGuiRegistry().addParameterWidgetFactory(
            _FVRecipeWidgetFactory()
        )


class _FVRecipeWidgetWrapper(JsonWidgetWrapper):

    def createWidget(self) -> QWidget:  # noqa: N802
        self.widget = _FVRecipeWidget()
        self.widget.highlight_changes = True
        self.widget.highlight_colour = QColor('#fcd465')
        default = self.parameterDefinition().defaultValue()
        if default:
            self.widget.setValue(str(default))
        return self.widget


class _FVRecipeWidgetFactory(JsonWidgetFactory):

    def parameterType(self) -> str:  # noqa: N802
            return FVRecipeParameter.TYPE
    
    def createWidgetWrapper(self, parameter, type_, parent=None):  # noqa: N802
        return _FVRecipeWidgetWrapper(parameter, type_, parent)

    def compatibleParameterTypes(self) -> list[str]:  # noqa: N802
        return [FVRecipeParameter.TYPE]


def _build_feature_settings(feature_name: str, command_id: str | None = None) -> tuple[str | dict, bool]:
    cull_variables = ('iter', 'model_name')

    manager = pt.project.TemplateManager(engine_type='fv')
    display2name = {x[1]: x[0] for x in manager.list_feature_configs()}
    if feature_name in display2name:
        feature = manager.get_feature_config(display2name[feature_name])
    else:
        feature = manager.get_feature_config(feature_name)

    defaults, engine_defaults = manager.get_defaults()
    defaults.update(engine_defaults)

    d = {'name': feature.get('name', feature_name)}
    allow_multiple = False
    for command_block in feature.get('command_blocks', []):
        if command_id is not None and command_id != command_block.get('id'):
            continue
        if command_block.get('allow_multiple', False):
            allow_multiple = True
        for cmd in command_block.get('commands', []):
            m = re.match(r'^.*\$\{(\w+)\}.*$', cmd)
            if m:
                var = m.group(1)
                if var in cull_variables:
                    continue
                default = [] if cmd.startswith('##ITER:') else ''
                val = defaults.get(var, default)
                d[var] = val

    return d if len(d) > 1 else display2name[feature_name], allow_multiple


class _FVRecipeWidget(JsonWidget):
    """Subclass JsonWidget and add some custom behviour
    
    e.g. Add custom context menu actions.
    """

    def _extend_context_menu(
        self,
        menu: QMenu,
        item: QTreeWidgetItem | None,
        key_path: list[str],
    ):
        if not key_path:
            menu.clear()
            return
        
        if len(key_path) == 1 and key_path[0] in ['display_name', 'description', 'variables', 'features']:
            names = [x.text() for x in menu.actions()]
            if '🗑 Delete' in names:
                menu.removeAction(menu.actions()[names.index('🗑 Delete')])
                names = [x.text() for x in menu.actions()]
            if 'Convert to…' in names:
                menu.removeAction(menu.actions()[names.index('Convert to…')])
            if not [x for x in menu.actions() if not x.isSeparator()]:
                menu.clear()
            if key_path[0] in ['display_name', 'description', 'variables']:
                return

        # FVSED add layer to material block
        feat_idx = self._is_fvsed_mat(key_path)
        if feat_idx != -1:
            fvsed_mat_layer_act = QAction('Add material layer…', menu)
            fvsed_mat_layer_act.triggered.connect(lambda a: self._add_fvsed_mat_layer(a, feat_idx))
            menu.addAction(fvsed_mat_layer_act)
            return

        # FVSED add fraction to layer block inside material block
        feat_idx, mat_layer_idx = self._is_fvsed_mat_layer(key_path)
        if feat_idx != -1 and mat_layer_idx != -1:
            fvsed_mat_frac_layer_act = QAction('Add fraction…', menu)
            fvsed_mat_frac_layer_act.triggered.connect(lambda a: self._add_fvsed_mat_layer_frac(a, feat_idx, mat_layer_idx))
            menu.addAction(fvsed_mat_frac_layer_act)
            return

        # FVPTM add layer to material block
        feat_idx = self._is_fvptm_mat(key_path)
        if feat_idx != -1:
            fvptm_mat_layer_act = QAction('Add material layer…', menu)
            fvptm_mat_layer_act.triggered.connect(lambda a: self._add_fvptm_mat_layer(a, feat_idx))
            menu.addAction(fvptm_mat_layer_act)
            return

        # FVPTM add group to material block
        feat_idx = self._is_fvptm_mat_grp(key_path)
        if feat_idx != -1:
            fvptm_mat_group_act = QAction('Add group…', menu)
            fvptm_mat_group_act.triggered.connect(lambda a: self._add_fvptm_mat_group(a, feat_idx))
            menu.addAction(fvptm_mat_group_act)
            return

        # FVPTM add group to the layer block within a material block
        feat_idx, mat_layer_idx = self._is_fvptm_mat_layer_group(key_path)
        if feat_idx != -1:
            fvptm_mat_layer_group_act = QAction('Add group…', menu)
            fvptm_mat_layer_group_act.triggered.connect(lambda a: self._add_fvptm_mat_layer_group(a, feat_idx, mat_layer_idx))
            menu.addAction(fvptm_mat_layer_group_act)
            return

        # FVPTM add mobility model to group
        feat_idx = self._is_fvptm_group(key_path)
        if feat_idx != -1:
            fvptm_mob_model_act = QAction('Add mobility model…', menu)
            fvptm_mob_model_act.triggered.connect(lambda a: self._add_fvptm_mobility_model(a, feat_idx))
            menu.addAction(fvptm_mob_model_act)
            return

        if len(key_path) != 1:
            return

        # len(key_path) == 1 and key_path[0] == 'features'
        # remove add item action
        menu.clear()
        # add a menu with list of possible features
        feat_acts = [QAction(x, menu) for x in self._get_feature_list()]
        feat_menu = QMenu('Add feature…', menu)
        feat_menu.triggered.connect(self._add_feature)
        feat_menu.addActions(feat_acts)
        menu.addAction(feat_menu.menuAction())

    @staticmethod
    def _is_fvsed_mat(key_path: list[str]) -> int:
        feat_idx = -1
        if len(key_path) == 3 and key_path[0] == 'features' and key_path[2] == 'stm_mat_layers':
            feat_idx = key_path[1]
        try:
            feat_idx = int(feat_idx)
        except (ValueError, TypeError):
            feat_idx = -1
        return feat_idx

    @staticmethod
    def _is_fvsed_mat_layer(key_path: list[str]) -> tuple[int, int]:
        feat_idx, mat_lyr_idx = -1, -1
        if len(key_path) == 5 and key_path[0] == 'features' and key_path[2] == 'stm_mat_layers' and key_path[4] == 'stm_mat_layer_fractions':
            feat_idx = key_path[1]
            mat_lyr_idx = key_path[3]
        elif len(key_path) == 4 and key_path[0] == 'features' and key_path[2] == 'stm_mat_layers' and re.findall(r'^\d+$', str(key_path[3])):
            feat_idx = key_path[1]
            mat_lyr_idx = key_path[3]
        try:
            feat_idx = int(feat_idx)
            mat_lyr_idx = int(mat_lyr_idx)
        except (ValueError, TypeError):
            feat_idx, mat_lyr_idx = -1, -1
        return feat_idx, mat_lyr_idx

    @staticmethod
    def _is_fvptm_mat(key_path: list[str]) -> int:
        feat_idx = -1
        if len(key_path) == 3 and key_path[0] == 'features' and key_path[2] == 'ptm_mat_layers':
            feat_idx = key_path[1]
        try:
            feat_idx = int(feat_idx)
        except (ValueError, TypeError):
            feat_idx = -1
        return feat_idx

    @staticmethod
    def _is_fvptm_mat_grp(key_path: list[str]) -> int:
        feat_idx = -1
        if len(key_path) == 3 and key_path[0] == 'features' and key_path[2] == 'ptm_mat_groups':
            feat_idx = key_path[1]
        try:
            feat_idx = int(feat_idx)
        except (ValueError, TypeError):
            feat_idx = -1
        return feat_idx

    @staticmethod
    def _is_fvptm_mat_layer_group(key_path: list[str]) -> tuple[int, int]:
        feat_idx = -1
        mat_lyr_idx = -1
        if len(key_path) == 5 and key_path[0] == 'features' and key_path[2] == 'ptm_mat_layers' and key_path[4] == 'ptm_mat_groups':
            feat_idx = key_path[1]
            mat_lyr_idx = key_path[3]
        try:
            feat_idx = int(feat_idx)
            mat_lyr_idx = int(mat_lyr_idx)
        except (ValueError, TypeError):
            feat_idx = -1
            mat_lyr_idx = -1
        return feat_idx, mat_lyr_idx

    @staticmethod
    def _is_fvptm_group(key_path: list[str]) -> int:
        feat_idx = -1
        if len(key_path) == 3 and key_path[0] == 'features' and key_path[2] == 'ptm_mobility_models':
            feat_idx = key_path[1]
        try:
            feat_idx = int(feat_idx)
        except (ValueError, TypeError):
            feat_idx = -1
        return feat_idx

    def _add_feature(self, action: QAction):
        val = self.valueAsDict()

        feats = val.get('features')
        if not feats:
            return
        existing_feat_ids = set(map(lambda x: x if isinstance(x, str) else x.get('name'), feats))
        feat_settings, allows_multiple = _build_feature_settings(action.text())
        featid = feat_settings.get('name') if isinstance(feat_settings, dict) else feat_settings
        if not allows_multiple and featid in existing_feat_ids:
            return
        
        feats.append(feat_settings)

        self.setValueFromDict(val, retain_highlights=True, highlight_new=True)

    def _get_feature_list(self) -> list[str]:
        manager = pt.project.TemplateManager(engine_type='fv')
        return [x[1] for x in manager.list_feature_configs()]

    @staticmethod
    def _sedmat_config(config: dict[str, typing.Any], feature_index: int | str, feature_name: str) -> dict[str, typing.Any]:
        from qgis.utils import iface
        feats = config.get('features')
        if not feats:
            if iface:
                iface.messageBar().pushWarning(
                'KeyError', 'features not found in loaded json'
                )
            return {}

        try:
            feature_index = int(feature_index)
        except (ValueError, TypeError):
            if iface:
                iface.messageBar().pushWarning(
                f'ValueError', 'feature index is not an integer: {feature_index}'
                )
            return {}

        mat = feats[feature_index]
        if mat.get('name') != feature_name:
            if iface:
                iface.messageBar().pushWarning(
                f'KeyError', 'fvsed/fvptm material layer can only be added to a material block'
                )
            return {}

        return mat

    @staticmethod
    def _ptmgrp_config(config: dict[str, typing.Any], feature_index: int | str, feature_name: str) -> dict[str, typing.Any]:
        from qgis.utils import iface
        feats = config.get('features')
        if not feats:
            if iface:
                iface.messageBar().pushWarning(
                'KeyError', 'features not found in loaded json'
                )
            return {}

        try:
            feature_index = int(feature_index)
        except (ValueError, TypeError):
            if iface:
                iface.messageBar().pushWarning(
                f'ValueError', 'feature index is not an integer: {feature_index}'
                )
            return {}

        grp = feats[feature_index]
        if grp.get('name') != feature_name:
            if iface:
                iface.messageBar().pushWarning(
                f'KeyError', 'fvptm mobility model can only be added to a group block'
                )
            return {}

        return grp

    def _add_fvsed_mat_layer(self, action: QAction, feature_index: int | str):
        val = self.valueAsDict()
        mat = self._sedmat_config(val, feature_index, 'sedmat')
        if not mat:
            return

        layers = mat.get('stm_mat_layers', [])
        mat_layer, _ = _build_feature_settings(feature_name='sedmat', command_id='fvsed_material_layer')
        if isinstance(mat_layer, dict):
            mat_layer.pop('name')
            mat_layer['stm_mat_layer_id'] = len(layers) + 1
        layers.append(mat_layer)
        mat['stm_mat_layers'] = layers
        mat['stm_mat_nlayers'] = len(layers)

        self.setValueFromDict(val, retain_highlights=True, highlight_new=True)

    def _add_fvsed_mat_layer_frac(self, action: QAction, feature_index: int | str, mat_layer_index: int | str):
        from qgis.utils import iface
        val = self.valueAsDict()
        mat = self._sedmat_config(val, feature_index, 'sedmat')
        if not mat:
            return
        layers = mat.get('stm_mat_layers', [])
        try:
            layer = layers[int(mat_layer_index)]
        except (IndexError, ValueError, TypeError):
            if iface:
                iface.messageBar().pushWarning(
                    f'ValueError', 'material layer index out of bounds: {mat_layer_index}'
                )
            return

        fractions = layer.get('stm_mat_layer_fractions', [])
        frac, _ = _build_feature_settings(feature_name='sedmat', command_id='fvsed_material_layer_frac')
        if isinstance(frac, dict):
            frac.pop('name')
        fractions.append(frac)
        layer['stm_mat_layer_fractions'] = fractions

        self.setValueFromDict(val, retain_highlights=True, highlight_new=True)

    def _add_fvptm_mat_layer(self, action: QAction, feature_index: int | str):
        from qgis.utils import iface
        val = self.valueAsDict()
        mat = self._sedmat_config(val, feature_index, 'ptmmat')
        if not mat:
            return

        layers = mat.get('ptm_mat_layers', [])
        if len(layers) > 0:
            if iface:
                iface.messageBar().pushWarning(
                    f'ValueError', 'PTM module only supports a single active layer, no more layers can be added'
                )
            return

        mat_layer, _ = _build_feature_settings(feature_name='ptmmat', command_id='fvptm_material_layer')
        if isinstance(mat_layer, dict):
            mat_layer.pop('name')
        layers.append(mat_layer)
        mat['ptm_mat_layers'] = layers

        self.setValueFromDict(val, retain_highlights=True, highlight_new=True)

    def _add_fvptm_mat_group(self, action: QAction, feature_index: int | str):
        from qgis.utils import iface
        val = self.valueAsDict()
        mat = self._sedmat_config(val, feature_index, 'ptmmat')
        if not mat:
            return

        groups = mat.get('ptm_mat_groups', [])

        mat_group, _ = _build_feature_settings(feature_name='ptmmat', command_id='fvptm_material_group')
        if isinstance(mat_group, dict):
            mat_group.pop('name')
            for key in mat_group.copy():
                if key.endswith('_model'):
                    mat_group.pop(key)
                if key != 'ptm_grp_id':
                    mat_group[key] = 'none'
        groups.append(mat_group)
        mat['ptm_mat_groups'] = groups

        self.setValueFromDict(val, retain_highlights=True, highlight_new=True)

    def _add_fvptm_mat_layer_group(self, action: QAction, feature_index: int | str, mat_layer_index: int | str):
        from qgis.utils import iface
        val = self.valueAsDict()
        mat = self._sedmat_config(val, feature_index, 'ptmmat')
        if not mat:
            return

        layers = mat.get('ptm_mat_layers', [])
        try:
            layer = layers[int(mat_layer_index)]
        except (IndexError, ValueError, TypeError):
            if iface:
                iface.messageBar().pushWarning(
                    f'ValueError', 'material layer index out of bounds: {mat_layer_index}'
                )
            return

        groups = layer.get('ptm_mat_groups', [])

        mat_group, _ = _build_feature_settings(feature_name='ptmmat', command_id='fvptm_material_group')
        if isinstance(mat_group, dict):
            mat_group.pop('name')
            for key in mat_group.copy():
                if key.endswith('_model'):
                    mat_group.pop(key)
                if key != 'ptm_grp_id':
                    mat_group[key] = 'none'
        groups.append(mat_group)
        layer['ptm_mat_groups'] = groups

        self.setValueFromDict(val, retain_highlights=True, highlight_new=True)

    def _add_fvptm_mobility_model(self, action: QAction, feature_index: int | str):
        val = self.valueAsDict()
        grp = self._ptmgrp_config(val, feature_index, 'ptmgroup')
        if not grp:
            return

        models = grp.get('ptm_mobility_models', [])
        model, _ = _build_feature_settings(feature_name='ptmgroup', command_id='fvptm_mobility_model')
        if isinstance(model, dict):
            model.pop('name')
        models.append(model)
        grp['ptm_mobility_models'] = models

        self.setValueFromDict(val, retain_highlights=True, highlight_new=True)
