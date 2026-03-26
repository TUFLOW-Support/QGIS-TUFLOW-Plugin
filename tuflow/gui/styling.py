import re
from json import JSONDecodeError
import json
from random import randrange

from qgis.PyQt.QtGui import QColor
from qgis.core import (QgsVectorLayer, QgsSymbol, QgsRendererCategory, QgsCategorizedSymbolRenderer, QgsWkbTypes,
                       QgsExpression, QgsExpressionContext, QgsExpressionContextUtils, Qgis, QgsGraduatedSymbolRenderer,
                       QgsRenderContext, QgsRuleBasedRenderer, QgsStyle, QgsSimpleLineSymbolLayer,
                       QgsMarkerLineSymbolLayer, QgsSimpleMarkerSymbolLayer, QgsSimpleMarkerSymbolLayerBase,
                       QgsMarkerSymbol, QgsSimpleFillSymbolLayer)
from qgis.utils import plugins

from .logging import Logging
from ..compatibility_routines import Path, QT_STYLE_DOTTED_PEN, QT_STYLE_DASHED_PEN
from ..utils.map_layer import set_vector_temporal_properties, file_from_data_source, layer_name_from_data_source
from .temporal_controller import (turn_on_temporal_controller_animated_nav, refresh_temporal_controller_range,
                                  set_temporal_controller_time_interval)
from ..tuflow_results_gpkg import ResData_GPKG


def apply_tf_style(e: bool = False, layer: QgsVectorLayer = None, style: str = '') -> None:
    if not layer:
        layer = plugins['tuflow'].iface.activeLayer()
    styling = Styling(layer, style=style)
    styling.apply_styling(layer)


def apply_tf_style_message_ids(e: bool = False) -> None:
    lyr = plugins['tuflow'].iface.activeLayer()
    styling = Styling(lyr, 'msgs')
    styling.apply_styling(lyr)


def apply_tf_style_gpkg_ts(lyr: QgsVectorLayer, type_: str, field_name: str):
    styling = Styling(lyr, layer_name=type_)
    if type_ != field_name and isinstance(styling, StylingGraduated):
        styling.rules['field_name'] = field_name
    styling.apply_styling(lyr)


def apply_tf_style_temporal(type_name: str, lyr: QgsVectorLayer = None, skip_temporal_init: bool = False):
    tuflow = plugins['tuflow']
    if not lyr:
        lyr = tuflow.iface.activeLayer()
    subset_str = _styling_subset_string(lyr.subsetString(), False)
    lyr.setSubsetString(subset_str)
    res_name = re.sub(r'_[PLR]$', '', lyr.name(), flags=re.IGNORECASE)
    if skip_temporal_init or (tuflow.resultsPlottingDockOpened and res_name in tuflow.resultsPlottingDock.tuResults.tuResults1D.results1d):
        # just apply styling - temporal settings should already be active
        apply_tf_style_gpkg_ts(lyr, type_name, type_name)
    else:
        # setup layer temporal properties and style
        set_vector_temporal_properties(lyr, True)
        turn_on_temporal_controller_animated_nav(tuflow.iface)
        refresh_temporal_controller_range(tuflow.iface)
        db = file_from_data_source(lyr.dataProvider().dataSourceUri())
        lyr_name = layer_name_from_data_source(lyr.dataProvider().dataSourceUri())
        res = ResData_GPKG()
        err, msg = res.Load(str(db))
        if err:
            Logging.error('Error loading results', msg)
            return
        _ = res.get_reference_time()
        dt = res.timestep_interval(lyr_name, type_name)
        if dt > 0.:
            dt *= 3600.  # convert to seconds
            set_temporal_controller_time_interval(tuflow.iface, dt, res.units)
        res.close()
        apply_tf_style_gpkg_ts(lyr, type_name, type_name)


def apply_tf_style_static(field_name: str):
    from qgis.utils import iface
    lyr = iface.activeLayer()
    subset_str = _styling_subset_string(lyr.subsetString(), True)
    lyr.setSubsetString(subset_str)
    res_name = re.sub(r'_[PLR]$', '', lyr.name(), flags=re.IGNORECASE)
    set_vector_temporal_properties(lyr, False)
    styling = Styling(lyr, layer_name=f'gpkg_ts_{field_name}')
    styling.apply_styling(lyr)


def _styling_subset_string(subset_str, static) -> str:
    """
    Routine to go between temporal and static styling using subset string.

    The subset string purpose is to limit the static styling to only one timestep.
    """
    # basic scenario - toggling between static/temporal
    if static:
        if not subset_str:
            return 'TimeID = 1'
    else:
        if not subset_str or subset_str.strip() == 'TimeID = 1':
            return ''

    # more complicated where a subset string already exists that the user has defined for other reasons
    # string "TimeID = " from subset string
    if re.findall(r'(?:and)?\s+timeid\s+=\s+\d+\s*', subset_str, flags=re.IGNORECASE):
        subset_str = re.sub(r'(?:and)?\s+timeid\s+=\d+\s*', '', subset_str, flags=re.IGNORECASE)
    elif re.findall(r'\s*timeid\s+=\s+\d+\s+(?:and\s*)?', subset_str, flags=re.IGNORECASE):
        subset_str = re.sub(r'\s*timeid\s+=\s+\d+\s+(?:and\s*)?', '', subset_str, flags=re.IGNORECASE)
    elif re.findall(r'\s*timeid\s+=\s+\d+', subset_str, flags=re.IGNORECASE):
        subset_str = re.sub(r'\s*timeid\s+=\s+\d+', '', subset_str, flags=re.IGNORECASE)

    if static:
        if subset_str:
            return f'{subset_str} and TimeID = 1'
        return 'TimeID = 1'
    return subset_str



class Styling:

    def __new__(cls, layer: QgsVectorLayer, sub_folder: str = '', layer_name: str = '', style: str = ''):
        from ..utils import layer_name_from_data_source
        if layer_name:
            name = layer_name
        else:
            name = layer_name_from_data_source(layer.dataProvider().dataSourceUri())
            if name.startswith('memory?'):
                name = layer.name()
        style_file = None
        if style == 'QML' or (not style and StylingQML.style_file(layer, name, sub_folder)):
            cls = StylingQML
            style_file = StylingQML.style_file(layer, name, sub_folder)
        elif style == 'Categorized' or (not style and StylingCategorized.style_file(layer, name, sub_folder)):
            cls = StylingCategorized
            style_file = StylingCategorized.style_file(layer, name, sub_folder)
        elif style == 'Graduated' or (not style and StylingGraduated.style_file(layer, name, sub_folder)):
            cls = StylingGraduated
            style_file = StylingGraduated.style_file(layer, name, sub_folder)
        elif style == 'Dynamic' or (not style and StylingDynamic.dynamic_class(layer, name)):
            cls = StylingDynamic.dynamic_class(layer, name)
            style_file = ''
        self = super().__new__(cls)
        self._init(name, style_file)
        return self

    def __repr__(self):
        return f'<{self.__class__.__name__} {self.name}>'

    def _init(self, name: str, style_file: Path) -> None:
        self.name = name
        self._style_file = style_file

    @staticmethod
    def styling_folder(sub_folder: str = ''):
        if sub_folder:
            return plugins['tuflow'].plugin_dir / 'QGIS_Styles' / sub_folder
        return plugins['tuflow'].plugin_dir / 'QGIS_Styles'

    def apply_styling(self, layer: QgsVectorLayer) -> None:
        pass



class StylingQML(Styling):
    NAME = 'QML'

    @staticmethod
    def style_file(layer: QgsVectorLayer, name: str, sub_folder: str = '') -> Path:
        for file in StylingQML.styling_folder(sub_folder).glob('*.qml'):
            if file.stem.lower() in name.lower():
                return file

    def apply_styling(self, layer: QgsVectorLayer) -> None:
        custom_properties = layer.customProperties()
        layer.loadNamedStyle(str(self._style_file))
        layer.setCustomProperties(custom_properties)
        layer.triggerRepaint()


class StylingCategorized(Styling):
    NAME = 'Categorized'

    @staticmethod
    def styling_folder(sub_folder: str = ''):
        if sub_folder:
            return Styling.styling_folder() / 'cat' / sub_folder
        return Styling.styling_folder() / 'cat'

    @staticmethod
    def style_file(layer: QgsVectorLayer, name: str, sub_folder: str = '') -> Path:
        for file in StylingCategorized.styling_folder(sub_folder).glob('*.json'):
            if StylingCategorized.is_match(file, layer, name):
                return file

    @staticmethod
    def is_match(file: Path, layer: QgsVectorLayer, name: str) -> bool:
        geom = re.findall(r'_[PLR]$', file.stem, flags=re.IGNORECASE)
        if geom:
            template = re.sub(r'_[PLR]$', '', file.stem, flags=re.IGNORECASE)
            geom = geom[0].upper()
        else:
            template = file.stem
            geom = ''
        if template.lower() in name.lower():
            if not geom:
                return True
            elif geom == '_P' and layer.geometryType() == QgsWkbTypes.PointGeometry:
                return True
            elif geom == '_L' and layer.geometryType() == QgsWkbTypes.LineGeometry:
                return True
            elif geom == '_R' and layer.geometryType() == QgsWkbTypes.PolygonGeometry:
                return True
        return False

    def _init(self, name: str, style_file: Path) -> None:
        super()._init(name, style_file)
        self.rules = self.load_renderer_file(self._style_file)

    def load_renderer_file(self, style_file: Path):
        try:
            with style_file.open() as f:
                return json.load(f)
        except JSONDecodeError as e:
            Logging.error('Error loading categorized style file', str(e))
            return

    def replace_variables(self, properties: dict, values: dict, recursive: bool = False) -> None:
        for key, value in properties.copy().items():
            if not isinstance(value, str) and not recursive:
                continue
            if isinstance(value, str) and value in values:
                properties[key] = values[value]
            elif isinstance(value, dict):
                self.replace_variables(properties[value], values, recursive)
            elif isinstance(value, list):
                for v in properties[value]:
                    if isinstance(v, dict):
                        self.replace_variables(v, values, recursive)

    def import_(self, name) -> object:
        cls = name.split(' ')[-1]
        exec('from qgis.core import ' + cls)
        return eval(cls)

    def load_imports(self, properties: dict) -> None:
        for key, value in properties.copy().items():
            if isinstance(value, str) and '$import' in value:
                properties[key] = self.import_(value)
            elif isinstance(value, dict):
                self.load_imports(properties[key])
            elif isinstance(value, list):
                for v in properties[key]:
                    if isinstance(v, dict):
                        self.load_imports(v)

    def get_unique_values(self, properties: dict, layer: QgsVectorLayer):
        unique_values = []
        if 'field_index' in properties:
            i = 1 if layer.storageType() == 'GPKG' else 0
            properties['field_name'] = layer.fields()[i].name()
            unique_values = self.get_unique_values_helper(layer, field_index=i)
        elif 'field_name' in properties:
            unique_values = self.get_unique_values_helper(layer, field_name=properties['field_name'])
        elif 'field_expression' in properties:
            self.rules['field_name'] = properties['field_expression']
            unique_values = self.get_unique_values_helper(layer, field_expression=properties['field_expression'])
        return unique_values

    def get_unique_values_helper(self, layer:QgsVectorLayer, field_name: str = '', field_index: int = -1, field_expression: str = ''):
        if field_name:
            i = layer.fields().indexFromName(field_name)
            return layer.dataProvider().uniqueValues(i)
        elif field_index > -1:
            return layer.dataProvider().uniqueValues(field_index)
        elif field_expression:
            unique_values = []
            expression = QgsExpression(field_expression)
            context = QgsExpressionContext()
            context.appendScopes(QgsExpressionContextUtils.globalProjectLayerScopes(layer))
            for feat in layer.getFeatures():
                context.setFeature(feat)
                value = expression.evaluate(context)
                if value is not None and value not in unique_values:
                    unique_values.append(value)
            return sorted(unique_values)

        return []

    def apply_styling(self, layer: QgsVectorLayer) -> None:
        if not self.rules:
            return
        self.replace_variables(self.rules, {'${name}': self.name})
        self.load_imports(self.rules)
        unique_values = self.get_unique_values(self.rules, layer)
        if not unique_values:
            return
        categories = []
        for value in unique_values:
            if self.rules.get('random_color') or 'color' not in self.rules:
                c = QColor(randrange(0,256), randrange(0,256), randrange(0,256))
            else:
                c = QColor(self.rules['color'])
            symbol = self.create_symbol(layer, self.rules, c, False)
            cat = QgsRendererCategory(value, symbol, str(value))
            categories.append(cat)

        renderer = QgsCategorizedSymbolRenderer(self.rules['field_name'], categories)
        layer.setRenderer(renderer)
        layer.triggerRepaint()

    def create_symbol(self, layer:QgsVectorLayer, prop: dict, color: QColor, sub_symbol: bool):
        main_symbol = None
        for i, symbol_prop in enumerate(prop.get('symbols', [prop])):
            layer_style = symbol_prop['layer_style'].copy()
            self.replace_variables(layer_style, {'${name}': self.name, '${color}': color}, recursive=True)
            if symbol_prop.get('class') and symbol_prop['class'] == 'geometry_default':
                symbol = QgsSymbol.defaultSymbol(layer.geometryType())
            elif symbol_prop.get('class'):
                cls = symbol_prop['class']
                symbol = cls()
            else:
                symbol = None
            if i == 0:
                main_symbol = symbol
            cls = symbol_prop['symbol_layer_class']
            symbol_layer = cls.create(layer_style)
            if symbol:
                symbol.changeSymbolLayer(0, symbol_layer)
            if symbol_prop.get('sub_symbol'):
                sub_symbol = self.create_symbol(layer, symbol_prop['sub_symbol'], color, True)
                symbol_layer.setSubSymbol(sub_symbol)
            if i > 0:
                main_symbol.appendSymbolLayer(symbol_layer)

        return main_symbol


class StylingGraduated(StylingCategorized):
    NAME = 'Graduated'

    @staticmethod
    def styling_folder(sub_folder: str = ''):
        if sub_folder:
            return Styling.styling_folder() / 'grad' / sub_folder
        return Styling.styling_folder() / 'grad'

    @staticmethod
    def style_file(layer: QgsVectorLayer, name: str, sub_folder: str = '') -> Path:
        for file in StylingGraduated.styling_folder(sub_folder).glob('*.json'):
            if StylingGraduated.is_match(file, layer, name):
                return file

    def get_field_name(self, properties: dict, layer: QgsVectorLayer):
        if 'field_index' in properties:
            i = 1 if layer.storageType() == 'GPKG' else 0
            properties['field_name'] = layer.fields()[i].name()
        elif 'field_name' in properties:
            pass
        elif 'field_expression' in properties:
            properties['field_name'] = properties['field_expression']
        return properties.get('field_name')

    def apply_styling(self, layer: QgsVectorLayer) -> None:
        if not self.rules:
            return

        # initialise properties
        self.replace_variables(self.rules, {'${name}': self.name})
        self.load_imports(self.rules)
        if self.rules.get('random_color') or 'color' not in self.rules:
            c = QColor(randrange(0, 256), randrange(0, 256), randrange(0, 256))
        else:
            c = QColor(self.rules['color'])

        field_name = self.get_field_name(self.rules, layer)
        if not field_name:
            return
        renderer = QgsGraduatedSymbolRenderer(field_name)
        if 'symbols' in self.rules:
            symbol = self.create_symbol(layer, self.rules, c, False)
            renderer.setSourceSymbol(symbol)
        if 'classification_method' in self.rules:
            cls = self.rules['classification_method']
            renderer.setClassificationMethod(cls())
        if 'graduated_method' in self.rules:
            enum = eval(self.rules['graduated_method'])
            renderer.setGraduatedMethod(enum)
        if renderer.graduatedMethod() == Qgis.GraduatedMethod.Size:
            min_symbol_size = self.rules.get('min_symbol_size', 0.26)
            max_symbol_size = self.rules.get('max_symbol_size', 2.)
        else:
            color_ramp_name = self.rules.get('color_ramp_name', 'Spectral')
            color_ramp = QgsStyle().defaultStyle().colorRamp(color_ramp_name)
            if self.rules.get('color_ramp_inverted', False):
                color_ramp.invert()
            renderer.setSourceColorRamp(color_ramp)
        n = self.rules.get('number_of_classifications', 5)
        renderer.updateClasses(layer, n)
        if renderer.graduatedMethod() == Qgis.GraduatedMethod.Size:  # corrects categorised symbol colours
            renderer.setSymbolSizes(min_symbol_size, max_symbol_size)
            for symbol in renderer.symbols(QgsRenderContext()):
                symbol.setColor(c)
        else:  # corrects categorised symbol colours
            for symbol in renderer.symbols(QgsRenderContext()):
                for symbol_layer in symbol.symbolLayers():
                    if symbol_layer.subSymbol():
                        for symbol_layer_ in symbol_layer.subSymbol().symbolLayers():
                            symbol_layer_.setStrokeColor(symbol_layer_.fillColor())
        layer.setRenderer(renderer)
        layer.triggerRepaint()


class StylingFM(Styling):
    NAME = 'FM'

    def apply_styling(self, layer: QgsVectorLayer) -> None:
        # generates a rule based renderer
        field_name = ''
        try:
            field_names = [x.name() for x in [f for f in layer.getFeatures()][0].fields()]
            upstrm_type = 'Upstrm_Type' if 'Upstrm_Type' in field_names else 'Upstrm_Typ'
        except (IndexError, AttributeError):
            upstrm_type = 'Upstrm_Type'
        if layer.geometryType() == QgsWkbTypes.LineGeometry:
            field_name = upstrm_type
        elif layer.geometryType() == QgsWkbTypes.PointGeometry:
            field_name = 'Unit_Type'
        if not field_name:
            return
        if layer.geometryType() == QgsWkbTypes.LineGeometry:
            renderer = self.rule_based_renderer(layer, field_name)
        else:
            renderer = self.categorized_renderer(layer, field_name)

        layer.setRenderer(renderer)
        layer.triggerRepaint()

    def categorized_renderer(self, layer, field_name):
        categories = []
        vals = layer.dataProvider().fieldNameIndex(field_name)
        unique_values = layer.dataProvider().uniqueValues(vals)
        for unique_value in unique_values:
            symbol = QgsSymbol.defaultSymbol(layer.geometryType())
            layer_style = {}
            color = '%d, %d, %d' % (randrange(0, 256), randrange(0, 256), randrange(0, 256))
            layer_style['color'] = color
            layer_style['outline'] = '#000000'
            symbol_layer = QgsSimpleMarkerSymbolLayer.create(layer_style)
            if unique_value.lower() == 'river':
                symbol_layer.setShape(QgsSimpleMarkerSymbolLayerBase.Diamond)
                symbol_layer.setSize(2.5)
                symbol_layer.setStrokeWidth(0.4)
                symbol_layer.setStrokeColor(QColor(50, 87, 128))
                symbol_layer.setFillColor(QColor(100, 153, 208))
            elif 'bdy' in unique_value.lower():
                symbol_layer.setShape(QgsSimpleMarkerSymbolLayerBase.Square)
                symbol_layer.setSize(2.5)
                symbol_layer.setStrokeWidth(0.)
                symbol_layer.setStrokeColor(QColor(35, 35, 35))
                symbol_layer.setFillColor(QColor(randrange(0, 256), randrange(0, 256), randrange(0, 256)))
            else:
                symbol_layer.setShape(QgsSimpleMarkerSymbolLayerBase.Circle)
                symbol_layer.setSize(2.0)
                symbol_layer.setStrokeWidth(0.)
                symbol_layer.setStrokeColor(QColor(35, 35, 35))
                symbol_layer.setFillColor(QColor(randrange(0, 256), randrange(0, 256), randrange(0, 256)))
            symbol.changeSymbolLayer(0, symbol_layer)
            category = QgsRendererCategory(unique_value, symbol, str(unique_value))
            categories.append(category)

        return QgsCategorizedSymbolRenderer(field_name, categories)

    def rule_based_renderer(self, layer, field_name):
        vals = layer.dataProvider().fieldNameIndex(field_name)
        unique_values = layer.dataProvider().uniqueValues(vals)
        unique_values2 = [x.upper() for x in unique_values if
                          x.upper() != 'SPILL' and x.upper() != 'JUNCTION' and x.upper() != 'INTERPOLATE']

        try:
            field_names = [x.name() for x in [f for f in layer.getFeatures()][0].fields()]
            upstrm_type = 'Upstrm_Type' if 'Upstrm_Type' in field_names else 'Upstrm_Typ'
            dnstrm_type = 'Dnstrm_Type' if 'Upstrm_Type' in field_names else 'Dnstrm_Typ'
        except (IndexError, AttributeError):
            upstrm_type = 'Upstrm_Type'
            dnstrm_type = 'Dnstrm_Type'
        spill_exists = 'SPILL' in [x.upper() for x in unique_values]
        junct_exists = 'JUNCTION' in [x.upper() for x in unique_values]
        intp_exists = 'INTERPOLATE' in [x.upper() for x in unique_values]
        expressions = [
            f'"{upstrm_type}" ILIKE \'{x}\' and {upstrm_type} NOT ILIKE \'%BDY%\' and {dnstrm_type} NOT ILIKE \'%BDY%\''
            for x in unique_values2]
        if spill_exists:
            expressions = [f'{x} and "{dnstrm_type}" NOT ILIKE \'SPILL\'' for x in expressions]
        if junct_exists:
            expressions = [f'{x} and "{dnstrm_type}" NOT ILIKE \'JUNCTION\'' for x in expressions]
        if intp_exists:
            expressions = [f'{x} and "{dnstrm_type}" NOT ILIKE \'INTERPOLATE\'' for x in expressions]
        expressions.insert(0, f'"{upstrm_type}" ILIKE \'%BDY%\' or "{dnstrm_type}" ILIKE \'%BDY%\'')
        symbol = QgsSymbol.defaultSymbol(layer.geometryType())
        renderer = QgsRuleBasedRenderer(symbol)
        root_rule = renderer.rootRule()
        for j, exp in enumerate(expressions):
            i = j - 1
            layer_style = {}
            color = '%d, %d, %d' % (randrange(0, 256), randrange(0, 256), randrange(0, 256))
            layer_style['color'] = color
            layer_style['outline'] = '#000000'
            symbol = QgsSymbol.defaultSymbol(layer.geometryType())
            rule = root_rule.children()[0].clone()
            if j == 0:
                rule.setLabel('BDY')
                rule.setFilterExpression(exp)
                symbol_layer = QgsSimpleLineSymbolLayer.create(layer_style)
                symbol_layer.setWidth(0.5)
                symbol_layer.setStrokeColor(QColor(227, 26, 28))
                symbol_layer.setPenStyle(QT_STYLE_DASHED_PEN)
                symbol_layer2 = None
            else:
                rule.setLabel(unique_values2[i])
                rule.setFilterExpression(exp)
                if unique_values2[i].lower() == 'lateral':
                    symbol_layer = QgsSimpleLineSymbolLayer.create(layer_style)
                    symbol_layer.setWidth(0.25)
                    color = QColor(randrange(0, 256), randrange(0, 256), randrange(0, 256))
                    symbol_layer.setStrokeColor(color)
                    symbol_layer.setPenStyle(QT_STYLE_DOTTED_PEN)
                    symbol_layer2 = None
                elif 'bdy' in unique_values2[i].lower():
                    continue
                else:
                    symbol_layer = QgsSimpleLineSymbolLayer.create(layer_style)
                    symbol_layer.setWidth(0.5)
                    symbol_layer2 = QgsMarkerLineSymbolLayer.create({'placement': 'lastvertex'})
                    layer_style['color_border'] = color
                    marker_symbol = QgsSimpleMarkerSymbolLayer.create(layer_style)
                    marker_symbol.setShape(QgsSimpleMarkerSymbolLayerBase.ArrowHeadFilled)
                    marker_symbol.setSize(4)
                    marker = QgsMarkerSymbol()
                    marker.changeSymbolLayer(0, marker_symbol)
                    symbol_layer2.setSubSymbol(marker)
                if symbol_layer is not None:
                    symbol.changeSymbolLayer(0, symbol_layer)
                    if symbol_layer2 is not None:
                        symbol.appendSymbolLayer(symbol_layer2)
            rule.setSymbol(symbol)
            root_rule.appendChild(rule)
        if spill_exists:
            symbol = QgsSymbol.defaultSymbol(layer.geometryType())
            exp = f'"{upstrm_type}" ILIKE \'SPILL\' or  "{dnstrm_type}" ILIKE \'SPILL\''
            rule = root_rule.children()[0].clone()
            rule.setLabel('SPILL')
            rule.setFilterExpression(exp)
            symbol_layer = QgsSimpleLineSymbolLayer.create(layer_style)
            symbol_layer.setWidth(0.25)
            color = QColor(randrange(0, 256), randrange(0, 256), randrange(0, 256))
            symbol_layer.setStrokeColor(color)
            symbol_layer.setPenStyle(QT_STYLE_DOTTED_PEN)
            symbol_layer2 = None
            if symbol_layer is not None:
                symbol.changeSymbolLayer(0, symbol_layer)
                if symbol_layer2 is not None:
                    symbol.appendSymbolLayer(symbol_layer2)
            rule.setSymbol(symbol)
            root_rule.appendChild(rule)
        if junct_exists:
            symbol = QgsSymbol.defaultSymbol(layer.geometryType())
            exp = f'("{upstrm_type}" ILIKE \'JUNCTION\' or "{dnstrm_type}" ILIKE \'JUNCTION\') AND "{upstrm_type}" NOT ILIKE \'SPILL\' AND "{dnstrm_type}" NOT ILIKE \'SPILL\''
            rule = root_rule.children()[0].clone()
            rule.setLabel('CONN')
            rule.setFilterExpression(exp)
            symbol_layer = QgsSimpleLineSymbolLayer.create(layer_style)
            symbol_layer.setWidth(0.25)
            color = QColor(35, 35, 35)
            symbol_layer.setColor(color)
            symbol_layer2 = None
            if symbol_layer is not None:
                symbol.changeSymbolLayer(0, symbol_layer)
                if symbol_layer2 is not None:
                    symbol.appendSymbolLayer(symbol_layer2)
            rule.setSymbol(symbol)
            root_rule.appendChild(rule)
        if intp_exists:
            layer_style = {}
            color = '%d, %d, %d' % (randrange(0, 256), randrange(0, 256), randrange(0, 256))
            layer_style['color'] = color
            layer_style['outline'] = '#000000'
            symbol = QgsSymbol.defaultSymbol(layer.geometryType())
            exp = f'("{upstrm_type}" ILIKE \'INTERPOLATE\' or "{dnstrm_type}" ILIKE \'INTERPOLATE\') AND "{upstrm_type}" NOT ILIKE \'SPILL\' AND "{dnstrm_type}" NOT ILIKE \'SPILL\''
            rule = root_rule.children()[0].clone()
            rule.setLabel('INTERPOLATE')
            rule.setFilterExpression(exp)
            symbol_layer = QgsSimpleLineSymbolLayer.create(layer_style)
            symbol_layer.setWidth(0.5)
            symbol_layer2 = QgsMarkerLineSymbolLayer.create({'placement': 'lastvertex'})
            layer_style['color_border'] = color
            marker_symbol = QgsSimpleMarkerSymbolLayer.create(layer_style)
            marker_symbol.setShape(QgsSimpleMarkerSymbolLayerBase.ArrowHeadFilled)
            marker_symbol.setSize(4)
            marker = QgsMarkerSymbol()
            marker.changeSymbolLayer(0, marker_symbol)
            symbol_layer2.setSubSymbol(marker)
            if symbol_layer is not None:
                symbol.changeSymbolLayer(0, symbol_layer)
                if symbol_layer2 is not None:
                    symbol.appendSymbolLayer(symbol_layer2)
            rule.setSymbol(symbol)
            root_rule.appendChild(rule)
        root_rule.removeChildAt(0)
        return renderer


class StylingDynamic(Styling):
    NAME = 'Dynamic'
    SUPPORTED = {
        r'_FM_PLOT_[PLR]': StylingFM
    }

    @staticmethod
    def dynamic_class(layer: QgsVectorLayer, name: str) -> type[Styling] | None:
        for supported, cls in StylingDynamic.SUPPORTED.items():
            if re.findall(supported, name, flags=re.IGNORECASE):
                return cls
        return None
