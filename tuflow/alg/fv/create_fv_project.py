from typing import Any
from pathlib import Path
import os
import sys
import json
import numpy as np
import subprocess

from qgis.PyQt import QtCore, QtWidgets

from qgis.core import Qgis, QgsMessageLog
from qgis.core import (QgsProcessingContext, QgsProcessingFeedback, QgsProcessingAlgorithm, QgsProcessingParameterString,
                       QgsProcessingParameterFile, QgsProcessingParameterCrs, QgsProcessingParameterEnum,
                       QgsProcessingParameterDefinition, QgsProcessingMultiStepFeedback,
                       QgsProcessingParameterBoolean)

from tuflow.gui.alg.processing_parameter_json import QgsProcessingParameterJson
from tuflow.gui.alg.fv_recipe_json_parameter import FVRecipeParameter
from tuflow.gui.alg.processing_parameter_enum import CustomProcessingParameterEnum
from tuflow.gui.alg.processing_parameter_button_group import QgsProcessingParameterButtonGroup
import tuflow.pt.pytuflow as pt
from tuflow.utils.project import ProjectConfig


# Initialise the templates
_manager = pt.project.TemplateManager(engine_type='fv')
_manager.init_cache(force=False)

# Initialise the defaults
try:
    _defaults, _engine_defaults = _manager.get_defaults()
except json.JSONDecodeError as e:
    QgsMessageLog.logMessage(f"Failed to load create_fv_project defaults due to json decode errorem: {e}", 'TUFLOW', level=Qgis.Warning)
    _defaults, _engine_defaults = {}, {}
_defaults = json.dumps({**_defaults, **_engine_defaults})

def _re_get_defaults():
    global _defaults
    try:
        _defaults, _engine_defaults = _manager.get_defaults()
    except json.JSONDecodeError as e:
        from qgis.utils import iface
        if iface:
            iface.messageBar().pushWarning(
            'JSON decode error', f'Cannot load defaults - invalid json syntax: {e}'
            )
        return
    
    _defaults = json.dumps({**_defaults, **_engine_defaults})

# Initialse features
_features = [x[0] for x in _manager.list_feature_configs()]

def _reget_features():
    global _features
    _features = [x[0] for x in _manager.list_feature_configs()]

# Initialise recipes
_recipes = [x for x in _manager.list_recipes()]  # list[tuple] - list of [id, display_name, description]

def _re_get_recipes():
    global _recipes
    _recipes = [x for x in _manager.list_recipes()]

CONSTRUCT_METHODS = ['From feature selection', 'From recipe']

FOLDER = Qgis.ProcessingFileParameterBehavior.Folder if Qgis.QGIS_VERSION_INT >= 33600 else Qgis.ProcessingFileParameterBehavior.Folder
FLAG_ADVANCED = Qgis.ProcessingParameterFlag.Advanced if Qgis.QGIS_VERSION_INT >= 33600 else QgsProcessingParameterDefinition.FlagAdvanced


def _python_env():
    # ensure correct plugin path is on the sys.path
    from qgis.utils import plugin_paths
    env = os.environ
    python_path = env['PYTHONPATH'].split(';' if os.name == 'nt' else ':')
    if plugin_paths:
        plugin_path = [x for x in plugin_paths if 'profiles' in Path(x).parts]
        if plugin_path:
            plugin_path = plugin_path[0]
            pytuflow_path = os.path.join(plugin_path, 'tuflow', 'pt')
            plugin_path_found = False  
            pytuflow_path_found = False  
            i = len(python_path)
            for p in reversed(python_path):
                i -= 1
                if p == plugin_path:
                    plugin_path_found = True
                    continue
                if p == pytuflow_path:
                    pytuflow_path_found = True
                    continue
                parts = Path(p).parts
                if 'QGIS' in parts and 'profiles' in parts and parts[-1] == 'plugins':
                    python_path.pop(i)
            if not plugin_path_found:
                python_path.append(plugin_path)
            if not pytuflow_path_found:
                python_path.append(pytuflow_path)
    env['PYTHONPATH'] = (';' if os.name == 'nt' else ':').join(python_path)
    return env


class _RecipeCache:
    def __init__(self, settings: str, modified: set[tuple[str, ...]]):
        self.settings = settings
        self.modified = modified


class CreateFVProject(QgsProcessingAlgorithm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cached_recipe_settings = {}
        self._curr_recipe_name = ''

    def initAlgorithm(self, configuration: dict[str | None, Any] = ...) -> None:
        # setup buttons first
        self.btn_defaults = QtWidgets.QPushButton('Open defaults folder')
        self.btn_defaults.clicked.connect(lambda: os.startfile(_manager._cache_dir.parent))  # nosec B606
        self.btn_features = QtWidgets.QPushButton('Open features folder')
        self.btn_features.clicked.connect(lambda: os.startfile(_manager._cache_features_dir))  # nosec B606
        self.btn_recipes = QtWidgets.QPushButton('Open presets folder')
        self.btn_recipes.clicked.connect(lambda: os.startfile(_manager._cache_recipes))  # nosec B606
        self.btn_reload = QtWidgets.QPushButton('Reload all folders')
        self.btn_reset_defaults = QtWidgets.QPushButton('Reset defaults')
        self.btn_reset_recipe = QtWidgets.QPushButton('Reset active preset')
        self.btn_init_templates = QtWidgets.QPushButton('Re-initialise templates')
        self.btn_init_templates.clicked.connect(self._reinit_templates)


        self.addParameter(
            QgsProcessingParameterString(
                'NAME',
                self.tr('Model name'),
                defaultValue=None,
                optional=False
            )
        )
        self.addParameter(
            QgsProcessingParameterFile(
                'OUTPUT_DIRECTORY',
                self.tr('Output directory'),
                behavior=FOLDER,
                defaultValue=None,
                optional=False
            )
        )
        self.addParameter(
                    QgsProcessingParameterBoolean(
                        'OVERWRITE',
                        'Overwrite existing',
                        defaultValue=False,
                    )
                )
        self.addParameter(
            QgsProcessingParameterCrs(
                'CRS',
                self.tr('Model CRS'),
                defaultValue=None,
                optional=False
            )
        )
        self.addParameter(
            QgsProcessingParameterBoolean(
                'SAVE_GLOBAL_SETTINGS',
                'Save settings globally',
                defaultValue=False,
            )
        )
        # self.addParameter(
        #     QgsProcessingParameterEnum(
        #         'CONSTRUCT_METHOD',
        #         self.tr('Template construction method'),
        #         options=CONSTRUCT_METHODS,
        #         defaultValue=1
        #     )
        # )

        # param = CustomProcessingParameterEnum(
        #     'FEATURES',
        #     self.tr('Select features'),
        #     options=_features,
        #     allowMultiple=True,
        #     defaultValue=None,
        #     optional=True
        # )
        # meta = param.metadata()
        # meta['callbacks'] = [
        #     {'control': 'CONSTRUCT_METHOD', 'callback': self._costruct_method_changed},
        #     {'control': 'BUTTON_GROUP', 'callback': self._reload_available_features},
        # ]
        # param.setMetadata(meta)
        # self.addParameter(param)

        recipe_display_names = [x[1] for x in _recipes]
        param = CustomProcessingParameterEnum(
            'RECIPES',
            self.tr('Select preset'),
            options=recipe_display_names,
            allowMultiple=False,
            defaultValue=recipe_display_names[0] if recipe_display_names else None
        )
        meta = param.metadata()
        meta['callbacks'] = [
            # {'control': 'CONSTRUCT_METHOD', 'callback': self._costruct_method_changed},
            {'control': 'BUTTON_GROUP', 'callback': self._reload_available_recipes},
        ]
        param.setMetadata(meta)
        self.addParameter(param)

        self.addParameter(
            QgsProcessingParameterButtonGroup(
                'BUTTON_GROUP',
                '',
                buttons = [[self.btn_defaults, self.btn_features, self.btn_recipes], 
                           [self.btn_reload, self.btn_reset_defaults, self.btn_reset_recipe, self.btn_init_templates]]
            )
        )

        param = FVRecipeParameter(
            'RECIPE_SETTINGS',
            self.tr('Preset settings'),
            defaultValue='{}'
        )
        meta = param.metadata()
        meta['callbacks'] = [ 
            # {'control': 'CONSTRUCT_METHOD', 'callback': self._costruct_method_changed},
            {'control': 'RECIPES', 'callback': self._recipe_changed},
            {'control': 'BUTTON_GROUP', 'callback': self._reset_recipe},
            {'control': 'BUTTON_GROUP', 'callback': self._reload_available_recipe_settings},
        ]
        param.setMetadata(meta)
        self.addParameter(param)

        param = QgsProcessingParameterJson(
            'DEFAULTS',
            self.tr('FV defaults'),
            defaultValue=_defaults
        )
        meta = param.metadata()
        meta['callbacks'] = [
            {'control': 'BUTTON_GROUP', 'callback': self._reload_available_defaults},
            {'control': 'BUTTON_GROUP', 'callback': self._reset_defaults},
        ]
        param.setMetadata(meta)
        param.setFlags(param.flags() | FLAG_ADVANCED)
        self.addParameter(param)

    def processAlgorithm(self, parameters: dict[str | None, Any], context: QgsProcessingContext, feedback: QgsProcessingFeedback | None) -> dict[str, Any]:
        multi_feedback = QgsProcessingMultiStepFeedback(7, feedback)
        multi_feedback.setCurrentStep(0)

        # Main parameters
        name = self.parameterAsString(parameters, 'NAME', context)
        out_dir = self.parameterAsFile(parameters, 'OUTPUT_DIRECTORY', context)
        crs = self.parameterAsCrs(parameters, 'CRS', context)
        crs_authid = crs.authid()
        overwrite = self.parameterAsBool(parameters, 'OVERWRITE', context)
        save_globally = self.parameterAsBool(parameters, 'SAVE_GLOBAL_SETTINGS', context)
        defaults = self.parameterAsString(parameters, 'DEFAULTS', context)

        # save project
        config = ProjectConfig(
            name,
            out_dir,
            crs,
            gis_format='shp',  # dummy
            save_settings_globally=save_globally
        )
        config.write_qgs_project()

        # constr_method = CONSTRUCT_METHODS[self.parameterAsEnum(parameters, 'CONSTRUCT_METHOD', context)]
        constr_method = 'From recipe'

        args = ['python3', '-m', 'pytuflow.project', 'create']
        multi_feedback.pushInfo('Constructing command...')
        multi_feedback.pushFormattedMessage('<pre>{0}</pre>'.format(' '.join(args)), '{0}'.format(' '.join(args)))
        multi_feedback.setCurrentStep(1)

        mandatory = [
            '--engine', 'fv',
            '--name', name,
            '--output-dir', str(out_dir),
            '--crs', str(crs_authid),
            '-y' if overwrite else '-n'
        ]
        args.extend(mandatory)
        multi_feedback.pushInfo('')
        multi_feedback.pushInfo('Adding mandatory arguments')
        for a, b in zip(mandatory[::2], mandatory[1::2]):
            multi_feedback.pushFormattedMessage(f'<pre>  {a} {b} \\</pre>',f'{a} {b}  \\')
        multi_feedback.pushFormattedMessage(f'<pre>  {mandatory[-1]} \\</pre>',f'{mandatory[-1]}  \\')
        multi_feedback.setCurrentStep(2)

        multi_feedback.pushInfo('')
        if constr_method == 'From feature selection':
            multi_feedback.pushInfo('Adding selected features...')
            idx = self.parameterAsEnums(parameters, 'FEATURES', context)
            if not idx:
                multi_feedback.pushInfo('No features selected')
            else:
                _reget_features()
                feat_list = np.array(_features)[idx].tolist()
                feats = ['--features'] + feat_list
                args.extend(feats)
                feat_str = ' '.join(feat_list)
                multi_feedback.pushFormattedMessage(f'<pre>  --features {feat_str}</pre>', f'--features  {feat_str}')
        else:
            multi_feedback.pushInfo('Adding selected configuration...')
            recipe = self.parameterAsString(parameters, 'RECIPE_SETTINGS', context)
            recipe_pretty = json.dumps(json.loads(recipe), indent=2).replace('\n', '<br>')
            args.extend(['--recipe', recipe])
            multi_feedback.pushFormattedMessage('<pre>  --recipe</pre>', '--recipe')
            multi_feedback.pushFormattedMessage(f'<pre>{recipe_pretty}</pre>', recipe)
        multi_feedback.setCurrentStep(3)

        args.extend(['--defaults', defaults])
        multi_feedback.pushInfo('')
        multi_feedback.pushInfo('Adding defaults...')
        multi_feedback.pushFormattedMessage('<pre>  --defaults  \\</pre>', '--defaults  \\')
        multi_feedback.pushFormattedMessage(f'<pre>    {defaults}</pre>', defaults)
        multi_feedback.setCurrentStep(4)

        multi_feedback.pushInfo('')
        multi_feedback.pushInfo('Setting up python environment')
        env = _python_env()
        kwargs = {}
        if os.name == 'nt':
            kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
        run = subprocess.run(['python', '-c', 'import sys\nfor p in sys.path:\n  print(p)'], env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)  # nosec B603 B607
        if run.stderr:
            multi_feedback.reportError(run.stderr)
            return {}
        for line in run.stdout.splitlines():
            multi_feedback.pushInfo(line)

        multi_feedback.pushInfo('')
        multi_feedback.pushInfo('Running pytuflow-project...')
        multi_feedback.setCurrentStep(5)

        kwargs = {'stdout': subprocess.PIPE, 'stderr': subprocess.STDOUT, 'bufsize': 0, 'universal_newlines': True, 'text': True, 'env': env}
        if os.name == 'nt':
            kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW

        multi_feedback.pushInfo('')
        with subprocess.Popen(args, **kwargs) as proc:  # nosec B603
            for line in proc.stdout:
                multi_feedback.pushInfo(str(line).strip('\n'))

                # Stop the algorithm if cancel button has been clicked
                if multi_feedback.isCanceled():
                    proc.terminate()

        multi_feedback.setCurrentStep(6)
        if proc.stderr:
            multi_feedback.reportError(str(proc.stderr))

        multi_feedback.pushInfo('')
        return {}

    def name(self) -> str:
        return 'Create TUFLOW FV Project'
    
    def displayName(self) -> str:
        return self.tr(self.name())

    def group(self) -> str:
        return self.tr(self.groupId())

    def groupId(self) -> str:
        return ''

    def shortHelpString(self) -> str:
        folder = Path(os.path.realpath(__file__)).parent
        help_filename = folder / 'help' / 'html' / 'create_fv_project.html'
        if not help_filename.exists():
            return ''
        return self.tr(help_filename.read_text(errors='ignore').replace('\n', '<p>'))

    def shortDescription(self) -> str:
        return self.tr('Creates a TUFLOW FV Project with empties and templates.')

    def createInstance(self) -> 'CreateFVProject':
        return CreateFVProject()

    def tr(self, string):
        return QtCore.QCoreApplication.translate('Processing', string)

    @staticmethod
    def _costruct_method_changed(calling_wrapper, changed_wrapper, wrappers):
        enabled = changed_wrapper.widgetValue() == 0
        if calling_wrapper.parameterDefinition().name() in ['RECIPES', 'RECIPE_SETTINGS']:
            enabled = not enabled
        calling_wrapper.wrappedWidget().setVisible(enabled)
        if calling_wrapper.wrappedLabel():
            calling_wrapper.wrappedLabel().setVisible(enabled)

    def _cache_current_recipe_settings(self, recipe_name: str, json_widget_wrapper):
        if not recipe_name:
            return
        settings = json_widget_wrapper.widgetValue()
        modified = json_widget_wrapper.widget._modified_paths()
        self._cached_recipe_settings[recipe_name] = _RecipeCache(settings, modified)

    def _restore_cached_recipe_settings(self, recipe_name: str, json_widget_wrapper):
        cached = self._cached_recipe_settings.get(recipe_name)
        if not cached:
            return
        json_widget_wrapper.setWidgetValue(cached.settings,  QgsProcessingContext())
        json_widget_wrapper.widget._restore_modified(cached.modified, json_widget_wrapper.widget.highlight_colour)

    def _recipe_changed(self, calling_wrapper, changed_wrapper, wrappers):
        # cache current recipe settings
        self._cache_current_recipe_settings(self._curr_recipe_name, calling_wrapper)
        try:
            recipe_name = _recipes[changed_wrapper.widgetValue()][0] if changed_wrapper.widgetValue() >= 0 else ''
        except Exception:
            recipe_name = ''
        if not recipe_name:
            calling_wrapper.setWidgetValue('{}')
        elif recipe_name in self._cached_recipe_settings:
            self._restore_cached_recipe_settings(recipe_name, calling_wrapper)
        else:
            recipe = _manager.get_recipe(recipe_name)
            calling_wrapper.setWidgetValue(json.dumps(recipe), QgsProcessingContext())
        self._curr_recipe_name = recipe_name

    @staticmethod
    def _reload_available_features(calling_wrapper, changed_wrapper, wrappers):
        if not hasattr(changed_wrapper, 'last_button_clicked'):
            return
        if changed_wrapper.last_button_clicked != 'Reload all folders':
            return
        _reget_features()
        calling_wrapper.setOptions(_features)

    @staticmethod
    def _reload_available_recipes(calling_wrapper, changed_wrapper, wrappers):
        if not hasattr(changed_wrapper, 'last_button_clicked'):
            return
        if changed_wrapper.last_button_clicked != 'Reload all folders':
            return
        _re_get_recipes()
        calling_wrapper.setOptions([x[1] for x in _recipes])

    @staticmethod
    def _reload_available_defaults(calling_wrapper, changed_wrapper, wrappers):
        """Reload the defaults. It will maintain any changed values by the user. The purpose
        is to load and new defaults."""
        if not hasattr(changed_wrapper, 'last_button_clicked'):
            return
        if changed_wrapper.last_button_clicked != 'Reload all folders':
            return
        _re_get_defaults()

        try:
            new_defaults = json.loads(_defaults)
        except json.JSONDecodeError:
            from qgis.utils import iface
            if iface:
                iface.messageBar().pushWarning(
                'JSON decode error', 'Cannot load new defaults - invalid json syntax'
                )
            return

        try:
            old_defaults = json.loads(calling_wrapper.widgetValue())
        except json.JSONDecodeError:
            from qgis.utils import iface
            if iface:
                iface.messageBar().pushWarning(
                'JSON decode error', 'Cannot load current defaults - invalid json syntax'
                )
            return

        for key, val in new_defaults.items():
            new_defaults[key] = old_defaults.get(key, val)

        modified = calling_wrapper.widget._modified_paths()
        calling_wrapper.widget.setValueFromDict(new_defaults)
        calling_wrapper.widget._restore_modified(modified, calling_wrapper.widget.highlight_colour)

    @staticmethod
    def _reload_available_recipe_settings(calling_wrapper, changed_wrapper, wrappers):
        if not hasattr(changed_wrapper, 'last_button_clicked'):
            return
        if changed_wrapper.last_button_clicked != 'Reload all folders':
            return

        try:
            old_settings = json.loads(calling_wrapper.widgetValue())
        except json.JSONDecodeError:
            from qgis.utils import iface
            if iface:
                iface.messageBar().pushWarning(
                'JSON decode error', 'Cannot load current recipe settings - invalid json syntax'
                )
            return
        
        _re_get_recipes()
        wrapper = [x for x in wrappers if x.parameterDefinition().name() == 'RECIPES']
        if wrapper:
            wrapper = wrapper[0]
            try:
                recipe_name = _recipes[wrapper.widgetValue()][0] if wrapper.widgetValue() >= 0 else ''
            except (IndexError, TypeError):
                recipe_name = ''
        else:
            recipe_name = ''
        if not recipe_name:
            calling_wrapper.setWidgetValue('{}')

        new_settings = _manager.get_recipe(recipe_name)

        def combine_settings(old, new):
            if isinstance(new, dict) and isinstance(old, dict):
                for key, val in new.items():
                    old_val = old.get(key, val)
                    old_is_iter = not isinstance(old_val, (float, int, str))
                    new_is_iter = not isinstance(val, (float, int, str))
                    if new_is_iter and old_is_iter:
                        combine_settings(old_val, val)
                    elif new_is_iter:
                        pass
                    else:
                        new[key] = old_val

            elif isinstance(new, (list, tuple)) and isinstance(old, (list, tuple)):
                new = list(new)
                for i in range(len(new)):
                    val = new[i]
                    old_val = old[i] if len(old) > i else val
                    old_is_iter = not isinstance(old_val, (float, int, str))
                    new_is_iter = not isinstance(val, (float, int, str))
                    if new_is_iter and old_is_iter:
                        combine_settings(old_val, val)
                    elif new_is_iter:
                        pass
                    else:
                        new[i] = old_val

        combine_settings(old_settings, new_settings)

        modified = calling_wrapper.widget._modified_paths()
        calling_wrapper.widget.setValueFromDict(new_settings)
        calling_wrapper.widget._restore_modified(modified, calling_wrapper.widget.highlight_colour)

    @staticmethod
    def _reset_defaults(calling_wrapper, changed_wrapper, wrappers):
        if not hasattr(changed_wrapper, 'last_button_clicked'):
            return
        if changed_wrapper.last_button_clicked != 'Reset defaults':
            return
        calling_wrapper.setWidgetValue(_defaults, QgsProcessingContext())

    def _reset_recipe(self, calling_wrapper, changed_wrapper, wrappers):
        if not hasattr(changed_wrapper, 'last_button_clicked'):
            return
        if changed_wrapper.last_button_clicked != 'Reset active recipe':
            return
        wrapper = [x for x in wrappers if x.parameterDefinition().name() == 'RECIPES']
        if wrapper:
            wrapper = wrapper[0]
            try:
                recipe_name = _recipes[wrapper.widgetValue()][0] if wrapper.widgetValue() >= 0 else ''
            except (IndexError, TypeError):
                recipe_name = ''
        else:
            recipe_name = ''

        if not recipe_name:
            calling_wrapper.setWidgetValue('{}')
        
        recipe = _manager.get_recipe(recipe_name)
        calling_wrapper.setWidgetValue(json.dumps(recipe), QgsProcessingContext())

    def _reinit_templates(self):
        ret = QtWidgets.QMessageBox.question(
            None, 
            're-initialise templates', 
            'Re-initialising template can override any changes you have made to the cached templates. Are you sure you want to re-initialise the templates?'
        )
        if ret == QtWidgets.QMessageBox.StandardButton.No:
            return

        args = ['python3', '-m', 'pytuflow.project', 'init-templates', '--engine', 'fv', '--force']
        env = _python_env()
        kwargs = {}
        if os.name == 'nt':
            kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
        run = subprocess.run(args, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)  # nosec B603

        if run.stderr:
            QtWidgets.QMessageBox.critical(None, 're-initialise templates', f'Error occurred: {run.stderr}')
            return

        QtWidgets.QMessageBox.information(
            None, 
            're-initialise templates', 
            'Successfully re-initialised template files. Click "Reload all folders" button to reload the dialog.'
        )
