import re
from json import JSONDecodeError
import json
from random import randrange

from PyQt5.QtGui import QColor
from qgis.core import (QgsVectorLayer, QgsSymbol, QgsRendererCategory, QgsCategorizedSymbolRenderer, QgsWkbTypes,
                       QgsExpression, QgsExpressionContext, QgsExpressionContextUtils)
from qgis.utils import plugins

from .logging import Logging
from ..compatibility_routines import Path


def apply_tf_style(e: bool = False) -> None:
    lyr = plugins['tuflow'].iface.activeLayer()
    styling = Styling(lyr)
    styling.apply_styling(lyr)


def apply_tf_style_message_ids(e: bool = False) -> None:
    lyr = plugins['tuflow'].iface.activeLayer()
    styling = Styling(lyr, 'msgs')
    styling.apply_styling(lyr)


class Styling:

    def __new__(cls, layer: QgsVectorLayer, sub_folder: str = ''):
        from ..utils import layer_name_from_data_source
        name = layer_name_from_data_source(layer.dataProvider().dataSourceUri())
        style_file = None
        if StylingQML.style_file(layer, name, sub_folder):
            cls = StylingQML
            style_file = StylingQML.style_file(layer, name, sub_folder)
        elif StylingCategorized.style_file(layer, name, sub_folder):
            cls = StylingCategorized
            style_file = StylingCategorized.style_file(layer, name, sub_folder)
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

    @staticmethod
    def style_file(layer: QgsVectorLayer, name: str, sub_folder: str = '') -> Path:
        for file in StylingQML.styling_folder(sub_folder).glob('*.qml'):
            if file.stem.lower() in name.lower():
                return file

    def apply_styling(self, layer: QgsVectorLayer) -> None:
        layer.loadNamedStyle(str(self._style_file))
        layer.triggerRepaint()


class StylingCategorized(Styling):

    @staticmethod
    def styling_folder(sub_folder: str = ''):
        if sub_folder:
            return Styling.styling_folder() / 'cat' / sub_folder
        return Styling.styling_folder() / 'cat'

    @staticmethod
    def style_file(layer: QgsVectorLayer, name: str, sub_folder: str = '') -> Path:
        for file in StylingCategorized.styling_folder(sub_folder).glob('*.json'):
            geom = re.findall(r'_[PLR]$', file.stem, flags=re.IGNORECASE)
            if geom:
                template = re.sub(r'_[PLR]$', '', file.stem, flags=re.IGNORECASE)
                geom = geom[0].upper()
            else:
                template = file.stem
                geom = ''
            if template.lower() in name.lower():
                if not geom:
                    return file
                elif geom == '_P' and layer.geometryType() == QgsWkbTypes.PointGeometry:
                    return file
                elif geom =='_L' and layer.geometryType() == QgsWkbTypes.LineGeometry:
                    return file
                elif geom == '_R' and layer.geometryType() == QgsWkbTypes.PolygonGeometry:
                    return file

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

    def unique_values(self, layer:QgsVectorLayer, field_name: str = '', field_index: int = -1, field_expression: str = ''):
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
                if value not in unique_values:
                    unique_values.append(value)
            return sorted(unique_values)

        return []

    def apply_styling(self, layer: QgsVectorLayer) -> None:
        if not self.rules:
            return
        if 'field_index' in self.rules:
            i = 1 if layer.storageType() == 'GPKG' else 0
            self.rules['field_name'] = layer.fields()[i].name()
            unique_values = self.unique_values(layer, field_index=i)
        elif 'field_name' in self.rules:
            unique_values = self.unique_values(layer, field_name=self.rules['field_name'])
        elif 'field_expression' in self.rules:
            self.rules['field_name'] = self.rules['field_expression']
            unique_values = self.unique_values(layer, field_expression=self.rules['field_expression'])
            print(unique_values)
        else:
            return
        categories = []
        for value in unique_values:
            c = QColor(randrange(0,256), randrange(0,256), randrange(0,256))
            symbol = self.create_symbol(layer, self.rules, c, False)
            cat = QgsRendererCategory(value, symbol, str(value))
            categories.append(cat)

        renderer = QgsCategorizedSymbolRenderer(self.rules['field_name'], categories)
        layer.setRenderer(renderer)
        layer.triggerRepaint()

    def create_symbol(self, layer:QgsVectorLayer, prop: dict, color: QColor, sub_symbol: bool):
        main_symbol = None
        for i, symbol_prop in enumerate(prop.get('symbols', [prop])):
            if symbol_prop.get('class') and symbol_prop['class'] == 'geometry_default':
                symbol = QgsSymbol.defaultSymbol(layer.geometryType())
            elif symbol_prop.get('class'):
                exec('from qgis.core import ' + prop['class'])
                cls = eval(symbol_prop['class'])
                symbol = cls()
            else:
                symbol = None
            if i == 0:
                main_symbol = symbol
            layer_style = symbol_prop['layer_style'].copy()
            if layer_style.get('color') and layer_style['color'] == '${color}':
                layer_style['color'] = color
            if layer_style.get('color_border') and layer_style['color_border'] == '${color}':
                layer_style['color_border'] = color
            exec('from qgis.core import ' + symbol_prop['symbol_layer_class'])
            cls = eval(symbol_prop['symbol_layer_class'])
            symbol_layer = cls.create(layer_style)
            if symbol:
                symbol.changeSymbolLayer(0, symbol_layer)
            if symbol_prop.get('sub_symbol'):
                sub_symbol = self.create_symbol(layer, symbol_prop['sub_symbol'], color, True)
                symbol_layer.setSubSymbol(sub_symbol)
            if i > 0:
                main_symbol.appendSymbolLayer(symbol_layer)

        return main_symbol
