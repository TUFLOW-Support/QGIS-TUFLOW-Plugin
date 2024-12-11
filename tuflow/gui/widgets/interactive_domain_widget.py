import math

import numpy as np
from PyQt5.QtCore import Qt, QObject, pyqtSignal
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSpinBox, QDoubleSpinBox, QLabel,
                             QSpacerItem, QSizePolicy, QApplication, QMenu, QAction, QToolButton)
from PyQt5.QtGui import QIcon, QColor
from qgis.core import (QgsPointXY, QgsGeometry, QgsApplication, QgsMapLayer, QgsProject, QgsSettings, QgsLayerTreeNode,
                       QgsRectangle)
from qgis.gui import QgsMapCanvas, QgsMessageBar, QgsColorButton

from tuflow.gui.interactive_rect_map_tool import InteractiveRectMapTool
from tuflow.compatibility_routines import Path
from tuflow.utils.create_grid_commands import ExtentCalculator
from tuflow.toc.toc import node_to_layer


class InteractiveDomainWidget(QWidget):

    domainChanged = pyqtSignal()

    def __init__(self, map_canvas, parent=None):
        super().__init__(parent)
        self.setWindowTitle('TUFLOW Model Domain')
        self.layout = QVBoxLayout()

        self.msg_bar = QgsMessageBar()
        self.layout.addWidget(self.msg_bar)

        self.domain_input_widget = DomainInputWidget()
        self.color = self.domain_input_widget.btn_color.color()
        self.layout.addWidget(self.domain_input_widget)

        self.map_canvas = map_canvas  # the QGIS map canvas
        self.canvas_widget = QWidget()
        self.canvas = QgsMapCanvas(self.canvas_widget)  # the tool's canvas
        self.canvas.setCanvasColor(Qt.white)
        self.canvas.enableAntiAliasing(True)
        self.layout.addWidget(self.canvas)
        self.setLayout(self.layout)
        self.canvas.setLayers(map_canvas.layers())
        if not self.canvas.layers():
            self.log_warning('No layers in canvas')
        self.canvas.setExtent(self.canvas.fullExtent())

        self.map_tool = InteractiveRectMapTool(self.canvas, self.color)

        self.project = QgsProject.instance()
        self.layer_tree_root = self.project.layerTreeRoot()
        self._newly_added_layers = None
        self.project.layersAdded.connect(self.layers_added)
        self.layer_tree_root.visibilityChanged.connect(self.layer_visibility_changed)
        self.layer_tree_root.layerOrderChanged.connect(self.layer_order_changed)

        self.domain_input_widget.editToggled.connect(self.edit_toggled)
        self.domain_input_widget.cleared.connect(self.map_tool.clear)
        self.domain_input_widget.zoomFullTriggered.connect(self.zoom_full_extent)
        self.map_tool.updated.connect(self.domain_updated)
        self.domain_input_widget.domainPropertiesChanged.connect(self.update_domain)
        self.domain_input_widget.domainAngleChanged.connect(self.update_angle)
        self.domain_input_widget.propertiesRounded.connect(self.round_values)
        self.domain_input_widget.domainToLayerExtent.connect(self.set_domain_to_layer_extent)
        self.domain_input_widget.colorChanged.connect(self.set_color)
        self.domain_input_widget.copyCommandsTriggered.connect(self.copy_domain_commands_to_clipboard)

    @property
    def x_size(self):
        return self.domain_input_widget.sb_x_size.value()

    @x_size.setter
    def x_size(self, value):
        self.domain_input_widget.sb_x_size.setValue(value)

    @property
    def y_size(self):
        return self.domain_input_widget.sb_y_size.value()

    @y_size.setter
    def y_size(self, value):
        self.domain_input_widget.sb_y_size.setValue(value)

    @property
    def origin_x(self):
        return self.domain_input_widget.sb_origin_x.value()

    @origin_x.setter
    def origin_x(self, value):
        self.domain_input_widget.sb_origin_x.setValue(value)

    @property
    def origin_y(self):
        return self.domain_input_widget.sb_origin_y.value()

    @origin_y.setter
    def origin_y(self, value):
        self.domain_input_widget.sb_origin_y.setValue(value)

    @property
    def angle(self):
        return math.radians(self.domain_input_widget.sb_angle.value())

    @angle.setter
    def angle(self, value):
        self.domain_input_widget.sb_angle.setValue(math.degrees(value))

    def log_info(self, msg):
        self.msg_bar.pushMessage( 'TUFLOW Domain', msg, level=0)

    def log_warning(self, msg):
        self.msg_bar.pushMessage('TUFLOW Domain', msg, level=1)

    def log_error(self, msg):
        self.msg_bar.pushMessage('TUFLOW Domain', msg, level=2)

    def edit_toggled(self, b):
        if b:
            self.canvas.setMapTool(self.map_tool)
        else:
            self.canvas.unsetMapTool(self.map_tool)

    def layers_added(self, layers):
        if self._newly_added_layers:
            self._newly_added_layers.extend(layers)
        else:
            self._newly_added_layers = layers
        self.domain_input_widget.set_layers_in_extent_menu()

    def layer_visibility_changed(self, node, visibility=None):
        visibility = node.isVisible() if visibility is None else visibility
        if node.nodeType() == QgsLayerTreeNode.NodeGroup:
            for nd in node.children():
                self.layer_visibility_changed(nd, visibility)
        else:
            layer = node_to_layer(node)
            if layer:
                lyrs = self.canvas.layers()
                if visibility:
                    if layer in self.layer_tree_root.layerOrder():
                        i = self.layer_tree_root.layerOrder().index(layer)
                    else:
                        i = 0
                    lyrs.insert(i, layer)
                elif layer in lyrs:
                    lyrs.remove(layer)
                self.canvas.setLayers(lyrs)

    def layer_order_changed(self):
        lyrs = self.canvas.layers()
        new_lyrs = []
        for lyr in self.layer_tree_root.layerOrder():
            if lyr in lyrs:
                new_lyrs.append(lyr)
                continue
            if self._newly_added_layers and lyr in self._newly_added_layers:
                new_lyrs.append(lyr)
                self._newly_added_layers.remove(lyr)
                if not self._newly_added_layers:
                    self._newly_added_layers = None
        self.canvas.setLayers(new_lyrs)
        if not lyrs and new_lyrs:
            self.zoom_full_extent()

    def domain_updated(self):
        self.domain_input_widget.blockSignals(True)
        self.angle = self.map_tool.angle
        self.origin_x = self.map_tool.origin_x
        self.origin_y = self.map_tool.origin_y
        self.x_size = self.map_tool.width
        self.y_size = self.map_tool.height
        self.domain_input_widget.blockSignals(False)
        self.domainChanged.emit()

    def update_domain(self):
        self.map_tool.origin_x = self.origin_x
        self.map_tool.origin_y = self.origin_y
        self.map_tool.width = self.x_size
        self.map_tool.height = self.y_size
        self.map_tool.angle = self.angle
        self.map_tool.update(self.create_geometry())
        self.domainChanged.emit()

    def set_domain(self, origin_x, origin_y, width, height, angle):
        self.domain_input_widget.blockSignals(True)
        self.origin_x = origin_x
        self.origin_y = origin_y
        self.x_size = width
        self.y_size = height
        self.angle = angle
        self.update_domain()
        self.domain_input_widget.blockSignals(False)

    def update_angle(self):
        if not self.map_tool.valid():
            return
        self.domain_input_widget.blockSignals(True)
        c = self.map_tool.centre()
        geom = QgsGeometry.fromPointXY(QgsPointXY(c.x() - self.x_size / 2, c.y() - self.y_size / 2))
        geom.rotate(-math.degrees(self.angle), c)
        self.origin_x = geom.asPoint().x()
        self.origin_y = geom.asPoint().y()
        self.update_domain()
        self.domain_input_widget.blockSignals(False)

    def create_geometry(self):
        # create rectangle in anti-clockwise order
        p1 = QgsPointXY(self.origin_x, self.origin_y)
        p2 = QgsPointXY(self.origin_x + self.x_size, self.origin_y)
        p3 = QgsPointXY(self.origin_x + self.x_size, self.origin_y + self.y_size)
        p4 = QgsPointXY(self.origin_x, self.origin_y + self.y_size)
        p5 = QgsPointXY(p1)
        geom = QgsGeometry.fromMultiPolygonXY([[[p1, p2, p3, p4, p5]]])
        geom.rotate(-math.degrees(self.angle), p1)
        return geom

    def round_values(self, rounding_precision):
        self.origin_x = round(self.origin_x / rounding_precision) * rounding_precision
        self.origin_y = round(self.origin_y / rounding_precision) * rounding_precision
        self.x_size = round(self.x_size / rounding_precision) * rounding_precision
        self.y_size = round(self.y_size / rounding_precision) * rounding_precision

    def set_domain_to_layer_extent(self, layer):
        self.domain_input_widget.blockSignals(True)
        centre = layer.extent().center()
        extent_calculator = ExtentCalculator(-math.degrees(self.angle), centre)
        if layer.type() == QgsMapLayer.VectorLayer:
            verts = [v for f in layer.getFeatures() for v in f.geometry().vertices()]
        else:
            verts = QgsGeometry.fromWkt(layer.extent().asWktPolygon()).asPolygon()[0][:-1]
        for vert in verts:
            extent_calculator.process_vertex(vert)
        self.origin_x, self.origin_y = extent_calculator.get_origin()
        self.x_size, self.y_size = extent_calculator.get_grid_size()
        self.update_domain()
        self.domain_input_widget.blockSignals(False)

    def set_color(self, color):
        QgsSettings().setValue('/tuflow/create_domain_color', color.name())
        self.color = color
        self.map_tool.set_color(color)
        self.canvas.refresh()

    def zoom_full_extent(self):
        rect = self.canvas.fullExtent()
        if self.map_tool.valid():
            rect.combineExtentWith(self.create_geometry().boundingBox())
            rect = rect.buffered(max(rect.width(), rect.height()) * 0.1)
        self.canvas.setExtent(rect)
        self.canvas.refresh()

    def create_domain_commands(self):
        text = (f'Origin == {self.origin_x:.2f}, {self.origin_y:.2f}\n'
                f'Orientation Angle == {math.degrees(self.angle):.2f}\n'
                f'Grid Size (X,Y) == {self.x_size:.2f}, {self.y_size:.2f}\n')
        return text

    def copy_domain_commands_to_clipboard(self):
        QApplication.clipboard().setText(self.create_domain_commands())
        self.log_info('Domain commands copied to clipboard')


class CustomRoundingAction(QAction):

    triggeredCustom = pyqtSignal(int)

    def __init__(self, rounding_precision, *args, **kwargs):
        self.rounding_precision = rounding_precision
        super().__init__(*args, **kwargs)
        self.triggered.connect(lambda: self.triggeredCustom.emit(self.rounding_precision))


class CustomLayerAction(QAction):

    triggeredCustom = pyqtSignal(QgsMapLayer)

    def __init__(self, layer, *args, **kwargs):
        self.layer = layer
        super().__init__(*args, **kwargs)
        self.triggered.connect(lambda: self.triggeredCustom.emit(self.layer))


class DomainInputWidget(QWidget):

    editToggled = pyqtSignal(bool)
    cleared = pyqtSignal()
    domainPropertiesChanged = pyqtSignal()
    domainAngleChanged = pyqtSignal()
    propertiesRounded = pyqtSignal(int)
    domainToLayerExtent = pyqtSignal(QgsMapLayer)
    colorChanged = pyqtSignal(QColor)
    zoomFullTriggered = pyqtSignal()
    copyCommandsTriggered = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout()

        # origin X, Y inputs
        self.label1 = QLabel('Origin X:')
        self.sb_origin_x = QDoubleSpinBox()
        self.sb_origin_x.setDecimals(2)
        self.sb_origin_x.setSingleStep(10.)
        self.sb_origin_x.setRange(0., 10000000000.)
        self.label2 = QLabel('Origin Y:')
        self.sb_origin_y = QDoubleSpinBox()
        self.sb_origin_y.setDecimals(2)
        self.sb_origin_y.setSingleStep(10.)
        self.sb_origin_y.setRange(0., 10000000000.)
        self.label0 = QLabel('Angle:')
        self.sb_angle = QDoubleSpinBox()
        self.sb_angle.setDecimals(2)
        self.sb_angle.setSingleStep(1.)
        self.sb_angle.setSuffix('°')
        self.sb_angle.setRange(-1000, 1000.)
        self.hlayout1 = QHBoxLayout()
        self.hlayout1.addWidget(self.label1)
        self.hlayout1.addWidget(self.sb_origin_x)
        self.hlayout1.addWidget(self.label2)
        self.hlayout1.addWidget(self.sb_origin_y)
        self.hlayout1.addWidget(self.label0)
        self.hlayout1.addWidget(self.sb_angle)
        self.hlayout1.addStretch(1)

        # x, y size inputs
        self.label3 = QLabel('X Size:')
        self.sb_x_size = QDoubleSpinBox()
        self.sb_x_size.setDecimals(2)
        self.sb_x_size.setSingleStep(10.)
        self.sb_x_size.setRange(0., 10000000000.)
        self.label4 = QLabel('Y Size:')
        self.sb_y_size = QDoubleSpinBox()
        self.sb_y_size.setDecimals(2)
        self.sb_y_size.setSingleStep(10.)
        self.sb_y_size.setRange(0., 10000000000.)
        self.hlayout2 = QHBoxLayout()
        self.hlayout2.addWidget(self.label3)
        self.hlayout2.addWidget(self.sb_x_size)
        self.hlayout2.addWidget(self.label4)
        self.hlayout2.addWidget(self.sb_y_size)
        self.hlayout2.addStretch(1)

        # tool buttons
        self.btn_edit = QToolButton()
        self.btn_edit.setToolTip('Start drawing or editing the domain')
        self.btn_edit.setIcon(QgsApplication.getThemeIcon('/mActionToggleEditing.svg'))
        self.btn_edit.setCheckable(True)
        self.btn_clear = QToolButton()
        self.btn_clear.setToolTip('Clear the domain')
        self.btn_clear.setIcon(QgsApplication.getThemeIcon('/mActionDeleteSelectedFeatures.svg'))
        self.btn_zoom_to_extent = QToolButton()
        self.btn_zoom_to_extent.setToolTip('Zoom to Extent of Visible Layers')
        self.btn_zoom_to_extent.setIcon(QgsApplication.getThemeIcon('/mActionZoomFullExtent.svg'))
        self.btn_layer_extent = QToolButton()
        self.btn_layer_extent.setToolTip('Set domain to layer extent (retains user angle)')
        self.btn_layer_extent.setIcon(QgsApplication.getThemeIcon('/mActionRectangleExtent.svg'))
        self.menu_layers = QMenu()
        self.set_layers_in_extent_menu()
        self.btn_layer_extent.setMenu(self.menu_layers)
        self.btn_layer_extent.setPopupMode(QToolButton.InstantPopup)
        self.menu_round_values = QMenu()
        self.menu_round_values.addActions(
            [CustomRoundingAction(1, 'Nearest 1', self.menu_round_values),
             CustomRoundingAction(10, 'Nearest 10', self.menu_round_values),
             CustomRoundingAction(100, 'Nearest 100', self.menu_round_values),
             CustomRoundingAction(1_000, 'Nearest 1000', self.menu_round_values)]
        )
        self.btn_round_values = QToolButton()
        self.btn_round_values.setToolTip('Round Domain Parameters')
        self.btn_round_values.setIcon(QIcon(str(Path(__file__).parents[2] / 'icons' / 'reduce-decimal-places-svgrepo-com.svg')))
        self.btn_round_values.setMenu(self.menu_round_values)
        self.btn_round_values.setPopupMode(QToolButton.InstantPopup)
        self.btn_copy = QToolButton()
        self.btn_copy.setToolTip('Copy Domain Attributes to Clipboard')
        self.btn_copy.setIcon(QgsApplication.getThemeIcon('/mActionEditCopy.svg'))
        self.btn_color = QgsColorButton()
        self.btn_color.setColor(QColor(QgsSettings().value('/tuflow/create_domain_color', '#000')))
        self.hlayout3 = QHBoxLayout()
        self.hlayout3.addWidget(self.btn_edit)
        self.hlayout3.addWidget(self.btn_clear)
        self.hlayout3.addWidget(self.btn_zoom_to_extent)
        self.hlayout3.addWidget(self.btn_layer_extent)
        self.hlayout3.addWidget(self.btn_round_values)
        self.hlayout3.addWidget(self.btn_copy)
        self.hlayout3.addWidget(self.btn_color)

        self.hlayout3.addStretch(0)

        # add them together
        self.layout.addLayout(self.hlayout1)
        self.layout.addLayout(self.hlayout2)
        self.layout.addLayout(self.hlayout3)
        self.setLayout(self.layout)

        # signals
        self.btn_edit.toggled.connect(self.editToggled.emit)
        self.btn_clear.clicked.connect(self.cleared)
        self.sb_origin_x.valueChanged.connect(self.domainPropertiesChanged.emit)
        self.sb_origin_y.valueChanged.connect(self.domainPropertiesChanged.emit)
        self.sb_angle.valueChanged.connect(self.domainAngleChanged.emit)
        self.sb_x_size.valueChanged.connect(self.domainPropertiesChanged.emit)
        self.sb_y_size.valueChanged.connect(self.domainPropertiesChanged.emit)
        for action in self.menu_round_values.actions():
            action.triggeredCustom.connect(self.propertiesRounded.emit)
        self.btn_color.colorChanged.connect(self.colorChanged.emit)
        self.btn_zoom_to_extent.clicked.connect(self.zoomFullTriggered.emit)
        self.btn_copy.clicked.connect(self.copyCommandsTriggered.emit)

    def set_layers_in_extent_menu(self):
        self.menu_layers.clear()
        for layer in QgsProject.instance().mapLayers().values():
            action = CustomLayerAction(layer, layer.name(), self.menu_layers)
            self.menu_layers.addAction(action)
            action.triggeredCustom.connect(self.domainToLayerExtent.emit)
