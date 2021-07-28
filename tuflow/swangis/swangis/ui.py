# general imports
import sys
import abc
import configparser

# local module imports
if __name__ == 'tuflow.swangis.swangis.ui':  # called from tuflow plugin
    from tuflow.swangis.swangis.swan import *
    from tuflow.swangis.swangis.api import *
else:
    from swangis.swan import *
    from swangis.api import *

# PyQt5 imports
from PyQt5.QtWidgets import QComboBox, QFileDialog, QDockWidget, QAction, QGroupBox, QDateEdit, QMessageBox, \
                            QLabel, QPushButton, QLineEdit, QWidget, QVBoxLayout, QHBoxLayout, QListWidget, \
                            QListWidgetItem, QDialog
from PyQt5.QtCore import Qt, QThread, QObject, pyqtSignal, QMimeData, QSettings
from PyQt5.QtGui import QIcon

# Helpful notes:
# Useful statement for debugging: QMessageBox.information(None, "DEBUG:", str(message))
# list of icons located here: https://github.com/qgis/QGIS/tree/master/images/themes/default

def buildVLWidget(name=None, spacing=None, margin=None, addTo=None):
    """Helper function for building vertical laid out widget"""
    widget = QWidget()
    layout = QVBoxLayout()
    widget.setLayout(layout)

    if name is not None:
        widget.setObjectName(name)
    if spacing is not None:
        layout.setSpacing(spacing)
    if addTo is not None:
        addTo.addWidget(widget)
    if margin is not None:
        widget.setContentsMargins(*margin)
    else:
        widget.setContentsMargins(0, 0, 0, 0)
        layout.setContentsMargins(0, 0, 0, 0)

    return widget, layout


def buildHLWidget(name=None, spacing=None, margin=None, addTo=None):
    """Helper function for building horizontal laid out widget"""
    widget = QWidget()
    layout = QHBoxLayout()
    widget.setLayout(layout)

    if name is not None:
        widget.setObjectName(name)
    if spacing is not None:
        layout.setSpacing(spacing)
    if addTo is not None:
        addTo.addWidget(widget)
    if margin is not None:
        widget.setContentsMargins(*margin)
    else:
        widget.setContentsMargins(0, 0, 0, 0)
        layout.setContentsMargins(0, 0, 0, 0)

    return widget, layout


def buildLabelWidget(label='', width=None, height=None, alignment=None, addTo=None):
    """Helper function for building labels"""
    widget = QLabel(label)
    widget.setObjectName('Label')

    if alignment is None:
        alignment=Qt.AlignCenter
    widget.setAlignment(alignment)

    if height is not None:
        widget.setMinimumHeight(height)
        widget.setMaximumHeight(height)
    if width is not None:
        widget.setMinimumWidth(width)
        widget.setMaximumWidth(width)
    if addTo is not None:
        addTo.addWidget(widget)

    return widget


def buildButtonWidget(label=None, width=None, height=None, icon=None, addTo=None):
    """Helper function for building buttons"""
    widget = QPushButton()

    if label is not None:
        widget.setText(label)
    if height is not None:
        widget.setMinimumHeight(height)
        widget.setMaximumHeight(height)
    if width is not None:
        widget.setMinimumWidth(width)
        widget.setMaximumWidth(width)
    if addTo is not None:
        addTo.addWidget(widget)
    if icon is not None:
        widget.setIcon(icon)

    return widget


def buildLineEditWidget(label='', width=None, height=None, addTo=None):
    """Helper function for building buttons"""
    widget = QLineEdit(label)

    if height is not None:
        widget.setMinimumHeight(height)
        widget.setMaximumHeight(height)
    if width is not None:
        widget.setMinimumWidth(width)
        widget.setMaximumWidth(width)
    if addTo is not None:
        addTo.addWidget(widget)

    return widget


class DateInputUI:

    def __init__(self, label):
        """Constructor function"""

        # protected attributes
        self._label = label

        # built the UI
        self.__build_ui__()

    def __build_ui__(self):
        # create and format base widget
        self.baseWidget, self.baseLayout = buildHLWidget(spacing=1)

        # create and format label widget
        self.labelWidget = buildLabelWidget(label=self._label, addTo=self.baseLayout,
                                            width=60, alignment=Qt.AlignCenter)

        # create date edit widget
        self.dateEditWidget = QDateEdit()
        self.baseLayout.addWidget(self.dateEditWidget)

    def getInput(self):
        return self.dateEditWidget.text()


class PointInputUI:

    def __init__(self):
        self.__build_ui__()

    def __build_ui__(self):
        # add X and Y inputs
        self.baseWidget, self.baseLayout = buildHLWidget(spacing=15)

        self.xLabel = buildLabelWidget('X: ', addTo=self.baseLayout)
        self.xWidget = buildLineEditWidget(addTo=self.baseLayout)

        self.yLabel = buildLabelWidget('Y: ', addTo=self.baseLayout)
        self.yWidget = buildLineEditWidget(addTo=self.baseLayout)

    def getInput(self):
        x, y = float(self.xWidget.text()), float(self.yWidget.text())

        return [x, y]


class TextInputUI:
    def __init__(self, label='', width=None, addTo=None):

        # store attributes
        self._label = label
        self._width = width
        self._addTo = addTo

        # build the UI
        self.__build_ui__()

    def __build_ui__(self):
        self.baseWidget, self.baseLayout = buildHLWidget(spacing=1)
        self.labelWidget = buildLabelWidget(self._label, width=self._width, addTo=self.baseLayout)
        self.lineEditWidget = buildLineEditWidget(addTo=self.baseLayout)

        if self._addTo is not None:
            self._addTo.addWidget(self.baseWidget)

    def getInput(self):
        return self.lineEditWidget.text()


class FolderInputUI:
    """Class for folder line item input"""

    def __init__(self, label):
        """Constructor function"""

        # protected attributes
        self._label = label

        # build the UI
        self.__build_ui__()

    def __build_ui__(self):
        """Builds the UI with Qt widgets"""

        # create and format base widget
        self.baseWidget, self.baseLayout = buildVLWidget(spacing=1)

        # create and format label widget
        self.labelWidget = buildLabelWidget(label=self._label, addTo=self.baseLayout,
                                            width=120, alignment=Qt.AlignLeft)

        # create and format input widget
        self.inputWidget, self.inputLayout = buildHLWidget(addTo=self.baseLayout)

        # create and format button widget
        self.buttonWidget = buildButtonWidget(width=20, label='...', addTo=self.inputLayout)

        # connect set with dialog signal with button slot
        self.buttonWidget.clicked.connect(self.setWithDialog)

        # create line edit widget
        self.lineEditWidget = buildLineEditWidget(addTo=self.inputLayout)

    def setWithDialog(self):
        # get previous directory if available
        lastDirectory = QSettings().value("SWANGIS/lastDirectory")

        # use last path if valid
        if lastDirectory != '':
            directory = lastDirectory
        # use root directory
        else:
            directory = os.path.abspath(os.sep)

        folder = QFileDialog.getExistingDirectory(directory=directory)

        if folder != '':
            self.lineEditWidget.setText(folder)
            QSettings().setValue("SWANGIS/lastDirectory", folder)

    def getInput(self):
        string = self.lineEditWidget.text()
        if string == b'None' or string == '':
            string = None

        return string


class OpenFileInputUI:
    """Class for file line item input"""

    def __init__(self, label='input', filter='All files (*.*)'):
        """Constructor function"""

        # protected attributes
        self._label = label
        self._filter = filter

        # build the UI
        self.__build_ui__()

    def __build_ui__(self):
        """Builds the UI with Qt widgets"""

        # create and format base widget
        self.baseWidget, self.baseLayout = buildVLWidget(spacing=1)

        # create and format label widget
        self.labelWidget = buildLabelWidget(label=self._label, addTo=self.baseLayout,
                                            width=160, alignment=Qt.AlignLeft)

        # create and format input widget
        self.inputWidget, self.inputLayout = buildHLWidget(addTo=self.baseLayout)

        # create and format button widget
        self.buttonWidget = buildButtonWidget(width=20, label='...', addTo=self.inputLayout)

        # connect set with dialog signal with button slot
        self.buttonWidget.clicked.connect(self.setWithDialog)

        # create line edit widget
        self.lineEditWidget = buildLineEditWidget(addTo=self.inputLayout)

    def setWithDialog(self):
        # get previous directory if available
        lastDirectory = QSettings().value("SWANGIS/lastDirectory")

        # use last path if valid
        if lastDirectory != '':
            directory = lastDirectory
        # use root directory
        else:
            directory = os.path.abspath(os.sep)

        file = QFileDialog.getOpenFileName(directory=directory, filter=self._filter)[0]
        newDirectory = os.path.split(file)[0]

        if file != '':
            self.lineEditWidget.setText(file)
            QSettings().setValue("SWANGIS/lastDirectory", newDirectory)

    def getInput(self):
        string = self.lineEditWidget.text()
        if string == b'None' or string == '':
            string = None

        return string


class SaveFileInputUI:
    """Class for file line item input"""

    def __init__(self, label, filter):
        """Constructor function"""

        # protected attributes
        self._label = label
        self._filter = filter

        # build the UI
        self.__build_ui__()

    def __build_ui__(self):
        """Builds the UI with Qt widgets"""

        # create and format base widget
        self.baseWidget, self.baseLayout = buildVLWidget(spacing=1)

        # create and format label widget
        self.labelWidget = buildLabelWidget(label=self._label, addTo=self.baseLayout,
                                            width=160, alignment=Qt.AlignLeft)

        # create and format input widget
        self.inputWidget, self.inputLayout = buildHLWidget(addTo=self.baseLayout)

        # create and format button widget
        self.buttonWidget = buildButtonWidget(width=20, label='...', addTo=self.inputLayout)

        # connect set with dialog signal with button slot
        self.buttonWidget.clicked.connect(self.setWithDialog)

        # create line edit widget
        self.lineEditWidget = buildLineEditWidget(addTo=self.inputLayout)

    def setWithDialog(self):
        # get previous directory if available
        lastDirectory = QSettings().value("SWANGIS/lastDirectory")

        # use last path if valid
        if lastDirectory != '':
            directory = lastDirectory
        # use root directory
        else:
            directory = os.path.abspath(os.sep)

        file = QFileDialog.getSaveFileName(directory=os.path.curdir, filter=self._filter)[0]
        newDirectory = os.path.split(file)[0]

        if file != '':
            self.lineEditWidget.setText(file)
            QSettings().setValue("SWANGIS/lastDirectory", newDirectory)

    def getInput(self):
        string = self.lineEditWidget.text()
        if string == b'None' or string == '':
            string = None

        return string


class LayerInputUI:
    """Class for drop down list input"""

    def __init__(self, label='input', keys=None, filter='All files (*.*)'):
        """Constructor function"""

        # protected attributes
        self._label = label
        self._keys = keys
        self._filter = filter

        # build the UI
        self.__build_ui__()

    def __build_ui__(self):
        """Builds the UI with Qt widgets"""

        # create and format base widget
        self.baseWidget, self.baseLayout = buildVLWidget(spacing=1)

        # create and format label widget
        self.labelWidget = buildLabelWidget(label=self._label, addTo=self.baseLayout,
                                            width=120, alignment=Qt.AlignLeft)

        # create and format input widget
        self.inputWidget, self.inputLayout = buildHLWidget(addTo=self.baseLayout)

        # create and format button widget
        self.dialogButtonWidget = buildButtonWidget(width=20, label='...', addTo=self.inputLayout)

        # create drop down list widget
        self.comboWidget = QComboBox()
        self.comboWidget.setEditable(True)
        self.inputLayout.addWidget(self.comboWidget)

        # connect the slots (handlers) to Qt signals (events)
        self.dialogButtonWidget.clicked.connect(self.setWithDialog)
        self.comboWidget.activated.connect(self.setWithCombo)

        # override show popup method of combo box with wrapper to enable updates
        self.comboWidget.showPopup = self.wrapShowPopUp

    def wrapShowPopUp(self):
        self.updateComboItems()
        QComboBox.showPopup(self.comboWidget)

    def updateComboItems(self):
        """Updates the selectable items"""

        # remove existing items
        self.comboWidget.clear()

        # get list of items as (name, layer)
        items = list()
        for layer in getLayers(self._keys):
            items.append((layer.name(), layer))

        # add new list of items
        for args in items:
            self.comboWidget.addItem(*args)

    def setWithDialog(self):
        # get previous directory if available
        lastDirectory = QSettings().value("SWANGIS/lastDirectory")

        # use last path if valid
        if lastDirectory != '':
            directory = lastDirectory
        # use root directory
        else:
            directory = os.path.abspath(os.sep)

        # get the file path from the dialogue
        file = QFileDialog.getOpenFileName(directory=directory, filter=self._filter)[0]
        newDirectory = os.path.split(file)[0]

        # add the layer to QGIS
        layer = addLayer(file)

        if layer is not None:
            # insert the new layer as the first item in list
            self.comboWidget.insertItem(0, layer.name(), layer)

            # set current item to the new layer (first item)
            self.comboWidget.setCurrentIndex(0)

            # update last directory
            QSettings().setValue("SWANGIS/lastDirectory", newDirectory)

    def setWithCombo(self):
        pass

    def getInput(self):
        index = self.comboWidget.currentIndex()
        layer = self.comboWidget.itemData(index)

        return layer


class LayersInputUI:

    def __init__(self, label='Label', keys=None, filter='All files (*.*)'):

        # protected attributes
        self._label = label
        self._keys = keys
        self._filter = filter

        # build the UI
        self.__build_ui__()

    def __build_ui__(self):
        # create the base widget and layout
        self.baseWidget, self.baseLayout = buildVLWidget(spacing=1)

        # add a layer input UI that allows selection of raster and mesh layers
        self.layerInputUI = LayerInputUI(self._label, self._keys, self._filter)
        self.baseLayout.addWidget(self.layerInputUI.baseWidget)

        # add Qlist below the layer input UI
        self.listWidget = QListWidget()
        self.listWidget.setMaximumHeight(80)
        self.baseLayout.addWidget(self.listWidget)

        # add add layer button to the layer input UI
        self.addLayerButton = buildButtonWidget(icon=getIcon('mActionAdd.svg'), width=20,
                                                addTo=self.layerInputUI.inputLayout)
        self.addLayerButton.clicked.connect(self.addCurrentLayer)

        # add remove layer button to the layer input UI
        self.removeLayerButton = buildButtonWidget(icon=getIcon('mActionRemove.svg'), width=20,
                                                   addTo=self.layerInputUI.inputLayout)
        self.removeLayerButton.clicked.connect(self.removeCurrentLayer)

    def addCurrentLayer(self):
        # get the layer input from UI
        layer = self.layerInputUI.getInput()

        # check if no layer selected
        if layer is None:
            return # do nothing

        # create list item, with name and parent list
        item = QListWidgetItem(layer.name(), self.listWidget)

        # set the data of the item to the layer
        item.setData(Qt.UserRole, layer)

    def removeCurrentLayer(self):
        # get index of current item in list widget
        index = self.listWidget.row(self.listWidget.currentItem())

        # remove item at index
        self.listWidget.takeItem(index)

    def addLayers(self, layers):
        for layer in layers:
            # create list item, with name and parent list
            item = QListWidgetItem(layer.name(), self.listWidget)

            # set the data of the item to the layer
            item.setData(Qt.UserRole, layer)

    def clearLayers(self):
        self.listWidget.clear()

    def getInput(self):
        # return list of layer objects in list widget
        return [self.listWidget.item(ii).data(Qt.UserRole) for ii in range(self.listWidget.count())]


class GridInputUI:

    def __init__(self, layer, fid):

        # public attributes
        self.layer = layer  # QgsVectorLayer
        self.fid = fid  # Feature ID
        self.editable = layer.isEditable()

        # protected member attributes
        self._grid = None  # SwanGrid
        self._mesh = None  # QgsMeshLayer

        # build the UI
        self.__build_ui__()

        # build the grid
        self.__build_grid__()

    def __build_ui__(self):
        # set up the base widget
        self.rowWidget, self.rowLayout = buildHLWidget()

        # add tag line edit
        self.nameInput = buildLineEditWidget(width=100, addTo=self.rowLayout)
        self.nameInput.editingFinished.connect(self.nameChange)
        self.nameInput.setEnabled(self.editable)

        # add rotation line edit
        self.rotationInput = buildLineEditWidget(width=60, addTo=self.rowLayout)
        self.rotationInput.editingFinished.connect(self.rotationChange)
        self.rotationInput.setEnabled(self.editable)

        # add dx line edit
        self.dxInput = buildLineEditWidget(width=80, addTo=self.rowLayout)
        self.dxInput.editingFinished.connect(self.dxChange)
        self.dxInput.setEnabled(self.editable)

        # add dy line edit
        self.dyInput = buildLineEditWidget(width=80, addTo=self.rowLayout)
        self.dyInput.editingFinished.connect(self.dyChange)
        self.dyInput.setEnabled(self.editable)

        # add nc label
        self.ncInput = buildLineEditWidget(width=60, addTo=self.rowLayout)
        self.ncInput.editingFinished.connect(self.ncChange)
        self.ncInput.setEnabled(self.editable)

    def __build_grid__(self):
        # get feature attributes
        attributes = getAttributes(self.layer, self.fid)

        # create and store grid object
        self._grid = SwanGrid(attributes['Name'], attributes['Geometry'], attributes['Rotation'],
                              attributes['X Length'], attributes['Y Length'], srs=attributes['SRS'])

        # synchronise the feature, row widget and mesh with grid
        self.synchronise()

    def toggleEdit(self):
        self.editable = not self.editable
        self.nameInput.setEnabled(self.editable)
        self.rotationInput.setEnabled(self.editable)
        self.dxInput.setEnabled(self.editable)
        self.dyInput.setEnabled(self.editable)
        self.ncInput.setEnabled(self.editable)

    def toggleRequired(self):
        if self._mesh is not None:
            flags = getLayerFlags(self._mesh)
            flags['isRequired'] = not flags['isRequired']
            setLayerFlags(self._mesh, **flags)

    def getGridName(self):
        return self._grid.getName()

    def getGridBoundary(self):
        return self._grid.getPolygon()

    def getGridRotation(self):
        rotation = self._grid.getRotation()
        if rotation is not None:
            return round(float(rotation), 2)
        else:
            return None

    def getGridDx(self):
        dx = self._grid.getDx()
        if dx is not None:
            return round(float(dx), 6)
        else:
            return None

    def getGridDy(self):
        dy = self._grid.getDy()
        if dy is not None:
            return round(float(dy), 6)
        else:
            return None

    def getGridNc(self):
        return self._grid.getNv()

    def getNameInput(self):
        """Simple function to handle name input"""
        return self.nameInput.text()

    def getRotationInput(self):
        """Simple function to handle rotation input"""
        text = self.rotationInput.text()
        if text == '':
            return None
        else:
            return round(float(text), 2)

    def getDxInput(self):
        """Simple function to handle dx input"""
        text = self.dxInput.text()
        if text == '':
            return None
        else:
            return round(float(text), 6)

    def getDyInput(self):
        """Simple function to handle dy input"""
        text = self.dyInput.text()
        if text == '':
            return None
        else:
            return round(float(text), 6)

    def getNcInput(self):
        """Simple function to handle nc input"""
        text = self.ncInput.text()
        if text == '':
            return None
        else:
            return int(text)

    def nameChange(self):
        try:  # update grid if valid input
            name = self.getNameInput()
            if name != self.getGridName():
                self._grid.setName(name)
                self.synchronise()
        except (ValueError, AttributeError):
            pass  # do nothing

    def rotationChange(self):
        try:  # update grid if valid input
            rotation = self.getRotationInput()
            if rotation != self.getGridRotation():
                self._grid.setRotation(rotation)
                self.synchronise()

        except (ValueError, AttributeError):
            pass

    def dxChange(self):
        try:  # update grid if valid input
            dx = self.getDxInput()
            if dx != self.getGridDx():
                self._grid.setDx(dx)
                self.synchronise()
        except (ValueError, AttributeError):
            pass  # do nothing

    def dyChange(self):
        try:  # update grid if valid input
            dy = self.getDyInput()
            if dy != self.getGridDy():
                self._grid.setDy(dy)
                self.synchronise()
        except (ValueError, AttributeError):
            pass  # do nothing

    def ncChange(self):
        try:  # update grid if valid input
            nc = self.getNcInput()
            if nc != self.getGridNc():
                self._grid.setNv(nc)
                self.synchronise()
        except (ValueError, AttributeError):
            pass  # do nothing

    def updateText(self):
        # pass grid data to various line edit widgets
        stuff = \
            [
                [self.nameInput.setText, '{}', self.getGridName()],
                [self.rotationInput.setText, '{:.2f}', self.getGridRotation()],
                [self.dxInput.setText, '{:.6f}', self.getGridDx()],
                [self.dyInput.setText, '{:.6f}', self.getGridDy()],
                [self.ncInput.setText, '{:d}', self.getGridNc()],
            ]

        for (setter, fString, value) in stuff:
            if value is not None:
                setter(fString.format(value))
            else:
                setter('')

    def updateFeature(self):
        # pass grid data to matching feature,
        # note: np dtypes are not handled! must be native python types
        values = [self.fid, self.getGridName(), self.getGridRotation(),
                  self.getGridDx(), self.getGridDy(), self.getGridNc()]
        setAttributes(self.layer, self.fid, values)

    def updateMesh(self):
        # set default visibility
        visible = True

        # remove old mesh, remember if visible
        if self._mesh is not None:
            # toggle mesh layer flags
            setLayerFlags(self._mesh, isRequired=False)

            # remember visibility, getVisibility has weird 'None' return bug ...
            visible = QgsProject.instance().layerTreeRoot().findLayer(self._mesh.id()).isVisible()

            # remove mesh from QGIS map canvas
            clearMesh(self._mesh)

            # remove reference to mesh
            self._mesh = None

        # create a new mesh for grid
        if self._grid.isDefined():
            self._mesh = createMesh(self._grid.getName(), self._grid.getNodes(), self._grid.getFaces())
            # self._mesh.setCrs(self._mesh.crs().fromEpsgId(self._grid.getEpsg()))
            QgsProject.instance().layerTreeRoot().findLayer(self._mesh.id()).setItemVisibilityChecked(visible)

            # toggle mesh layer flags
            setLayerFlags(self._mesh, isRequired=True)


    def synchronise(self):
        self.updateText()
        self.updateFeature()
        self.updateMesh()

    def delete(self):
        # remove base widget from the parent widget
        self.rowWidget.setParent(None)

        # remove the mesh
        if self._mesh is not None:
            clearMesh(self._mesh)


class GridLayerInputUI:
    """Class for drop down list input"""

    def __init__(self):
        """Constructor function"""

        # protected attributes
        self._gridUIs = list()
        self._layer = None

        # build the UI
        self.__build_ui__()

        # hack to stop memory layer being saved (opted to use other method)
        getProject().writeProject.connect(self.whenProjectWritten)
        getProject().projectSaved.connect(self.whenProjectSaved)

    def __build_ui__(self):
        """Builds the UI with Qt widgets"""

        # create and format base widget
        self.baseWidget, self.baseLayout = buildVLWidget(spacing=2)

        # create and format label widget
        self.labelWidget = buildLabelWidget(label='Grid Layer Input', addTo=self.baseLayout,
                                            width=120, alignment=Qt.AlignLeft)
        # create and format input widget
        self.inputWidget, self.inputLayout = buildHLWidget(addTo=self.baseLayout)

        # create and format button widget
        self.dialogButtonWidget = buildButtonWidget(width=20, label='...', addTo=self.inputLayout)
        self.dialogButtonWidget.clicked.connect(self.setLayerWithDialog)

        # create drop down list widget
        self.comboWidget = QComboBox()
        self.comboWidget.setEditable(True)
        self.comboWidget.activated.connect(self.setLayerWithCombo)
        self.inputLayout.addWidget(self.comboWidget)

        # override show popup method of combo box with wrapper to enable updates
        self.comboWidget.showPopup = self.wrapShowPopUp

        # add create domain layer button to input widget
        self.addButtonWidget = buildButtonWidget(icon=getIcon('mActionAddPolygon.svg'),
                                                 width=20, addTo=self.inputLayout)
        self.addButtonWidget.clicked.connect(self.createlayer)

        # add a space between layer input and table
        self.baseLayout.addSpacing(10)

        # create 'table' widget and add to input layout
        self.tableWidget, self.tableLayout = buildVLWidget(spacing=10, addTo=self.baseLayout)

        # specify header layout and add to table widget
        self.headerWidget, self.headerLayout = buildHLWidget(addTo=self.tableLayout)

        # create a header from label widgets
        self.headerLabels = list()
        self.headerLabels.append(buildLabelWidget(label='Name', width=100, addTo=self.headerLayout))
        self.headerLabels.append(buildLabelWidget(label='Rotation', width=60, addTo=self.headerLayout))
        self.headerLabels.append(buildLabelWidget(label='X Step', width=80, addTo=self.headerLayout))
        self.headerLabels.append(buildLabelWidget(label='Y Step', width=80, addTo=self.headerLayout))
        self.headerLabels.append(buildLabelWidget(label='Num. Points', width=60, addTo=self.headerLayout))

    def wrapShowPopUp(self):
        self.updateComboItems()
        QComboBox.showPopup(self.comboWidget)

    def updateComboItems(self):
        """Updates the selectable items"""

        # remove existing items
        self.comboWidget.clear()

        # get list of items as (name, layer)
        items = list()
        for layer in getSwanDomainLayers():
            items.append((layer.name(), layer))

        # append a None option
        items.append(('None', None))

        # add new list of items
        for args in items:
            self.comboWidget.addItem(*args)

    def setLayerWithDialog(self):
        # get previous directory if available
        lastDirectory = QSettings().value("SWANGIS/lastDirectory")

        # use last path if valid
        if lastDirectory != '':
            directory = lastDirectory
        # use root directory
        else:
            directory = os.path.abspath(os.sep)

        # get the file path from the dialogue
        file = QFileDialog.getOpenFileName(directory=directory, filter="shp(*.shp)")[0]
        newDirectory = os.path.split(file)[0]

        # add the layer to QGIS
        layer = addLayer(file)

        if layer is not None:
            # insert the new layer as the first item in list
            self.comboWidget.insertItem(0, layer.name(), layer)

            # set current item to the new layer (first item)
            self.comboWidget.setCurrentIndex(0)

            # update last folder
            QSettings().setValue("SWANGIS/lastDirectory", newDirectory)

    def setLayerWithCombo(self):
        index = self.comboWidget.currentIndex()
        layer = self.comboWidget.itemData(index)

        self.setLayer(layer)

    def createlayer(self):
        file = QFileDialog.getSaveFileName(directory=os.path.curdir, filter="shp(*.shp)")[0]

        if file != '':
            createSwanDomainLayer(file)

    def setLayer(self, layer):
        # if same as current layer
        if layer == self._layer:
            return  # do nothing

        # else ...

        # disconnect slots from current layer
        if self._layer is not None:
            self._layer.featureAdded.disconnect(self.whenFeatureAdded)
            self._layer.featureDeleted.disconnect(self.whenFeatureDeleted)
            self._layer.geometryChanged.disconnect(self.whenFeatureEdited)
            self._layer.editingStarted.disconnect(self.toggleEdit)
            self._layer.editingStopped.disconnect(self.toggleEdit)

            # toggle current layer flags
            self.toggleRequired()

        # set the layer attribute
        self._layer = layer

        # connect slots to new layer
        if self._layer is not None:
            self._layer.featureAdded.connect(self.whenFeatureAdded)
            self._layer.featureDeleted.connect(self.whenFeatureDeleted)
            self._layer.geometryChanged.connect(self.whenFeatureEdited)
            self._layer.editingStarted.connect(self.toggleEdit)
            self._layer.editingStopped.connect(self.toggleEdit)

            # toggle current layer flags
            self.toggleRequired()

        # clear the current grid UIs
        self.deleteGridUIs()

        # build new grid UIs
        self.buildGridUIs()

    def getLayer(self):
        return self._layer

    def sortGridUIs(self):
        """Helper function to sort grid UIs based on nesting"""
        inside = inWhichPolygon([ui.getGridBoundary() for ui in self._gridUIs])
        index = np.argsort(np.sum(inside, axis=1))
        self._gridUIs = list(np.array(self._gridUIs)[index])

    def buildGridUIs(self):
        # if new layer is none
        if self._layer is None:
            return  # do nothing

        # else ...

        # get features from the current layer
        features = getFeatures(self._layer)

        # create a new grid UI for each feature
        self._gridUIs = [GridInputUI(self._layer, f.id()) for f in features]

        # sort grids on nesting (outer to inner)
        self.sortGridUIs()

        # build UI for each grid\feature
        for gridUI in self._gridUIs:
            self.tableLayout.addWidget(gridUI.rowWidget)

    def deleteGridUIs(self):
        while len(self._gridUIs) > 0:
            self._gridUIs.pop(0).delete()

    def toggleEdit(self):
        for gridUI in self._gridUIs:
            gridUI.toggleEdit()

    def toggleRequired(self):
        if self._layer is not None:
            flags = getLayerFlags(self._layer)
            print(flags.keys())
            flags['isRequired'] = not flags['isRequired']
            setLayerFlags(self._layer, **flags)

            for g in self._gridUIs:
                g.toggleRequired()

    def whenFeatureAdded(self, fid):
        # create a grid UI for new feature
        self._gridUIs.append(GridInputUI(self._layer, fid))

        # sort grids on nesting (outer to inner)
        self.sortGridUIs()

        # remove then add UIs
        for gridUI in self._gridUIs:
            gridUI.rowWidget.setParent(None)
        # build UI for each grid\feature
        for gridUI in self._gridUIs:
            self.tableLayout.addWidget(gridUI.rowWidget)

        # reset active layer
        setActiveLayer(self._layer)

    def whenFeatureDeleted(self, fid):
        for ii in range(len(self._gridUIs)):
            if self._gridUIs[ii].fid == fid:
                self._gridUIs.pop(ii).delete()
                return

        # reset active layer
        setActiveLayer(self._layer)

    def whenFeatureEdited(self, fid):
        geometry = getGeometry(self._layer, fid)
        for ii in range(len(self._gridUIs)):
            if self._gridUIs[ii].fid == fid:
                self._gridUIs[ii]._grid.setPolygon(geometry)
                self._gridUIs[ii].synchronise()

        # reset active layer
        setActiveLayer(self._layer)

    def whenProjectWritten(self):
        """Before project is saved"""
        self.toggleRequired()

    def whenProjectSaved(self):
        """After project is saved"""
        self.toggleRequired()

    def getInput(self):
        return self.getLayer()


class ConfigurationUI:

    def __init__(self):
        """Constructor function"""

        # create default configuration
        self._config = SwanConfig()

        # stash a save file
        self._saveFile = None

        # built the UI
        self.__build_ui__()

    def __build_ui__(self):
        # create and format base widget
        self.baseWidget, self.baseLayout = buildHLWidget(spacing=1)

        # add a file input UI to the base widget
        self.fileInputUI = OpenFileInputUI('Configuration File Input', "ini(*.ini)")
        self.baseLayout.addWidget(self.fileInputUI.baseWidget)

        # add a button to the base widget for 'quick setup'
        self.editorButton = buildButtonWidget(icon=getIcon('mActionOptions.svg'), addTo=self.fileInputUI.inputLayout)
        self.editorButton.clicked.connect(self._openEditor)

        # create and format pop-up editor widget
        self.editorWidget = QDialog()
        self.editorLayout = QVBoxLayout()
        self.editorWidget.setLayout(self.editorLayout)

        # add tool bar to the editor widget
        self.toolWidget, self.toolLayout = buildHLWidget(spacing=1, addTo=self.editorLayout)

        # add a label to the tool bar
        buildLabelWidget('SWAN Configuration', addTo=self.toolLayout)
        self.toolLayout.addStretch()

        # add buttons to tool bar
        self.loadButton = buildButtonWidget(icon=getIcon('mActionFileOpen.svg'), addTo=self.toolLayout)
        self.saveAsButton = buildButtonWidget(icon=getIcon('mActionFileSaveAs.svg'), addTo=self.toolLayout)
        self.saveButton = buildButtonWidget(icon=getIcon('mActionFileSave.svg'), addTo=self.toolLayout)

        # connect handlers to buttons
        self.loadButton.pressed.connect(self._loadConfiguration)
        self.saveAsButton.pressed.connect(self._saveConfigurationAs)
        self.saveButton.pressed.connect(self._saveConfiguration)

        # add all configuration text inputs
        for name in self._config.parameters:
            setattr(self, name, TextInputUI(name, 80, self.editorLayout))

        # update text inputs from default
        self._updateInput()

        # add a stretch to the end
        self.editorLayout.addStretch()

    # protected member functions
    def _openEditor(self):
        self.editorWidget.show()

    def _updateInput(self):
        """Helper function to pass data from object to input"""
        for name in self._config.parameters:
            getattr(self, name).lineEditWidget.setText(str(getattr(self._config, name)))

    def _updateConfig(self):
        """Helper function to pass data from input to object"""
        for name in self._config.parameters:
            setattr(self._config, name, SwanConfig.convertType(getattr(self, name).getInput()))

    def _loadConfiguration(self):
        # get file path from dialog
        file = QFileDialog.getOpenFileName(directory=os.path.curdir, filter="ini(*.ini)")[0]

        # if valid file
        if file != '':
            # set the line edit widget text
            self.fileInputUI.lineEditWidget.setText(file)

            # read new config from file
            self._config = SwanConfig().read(file)

            # update the input widgets
            self._updateInput()

    def _saveConfigurationAs(self):
        # get file path from
        file = QFileDialog.getSaveFileName(directory=os.path.curdir, filter="ini(*.ini)")[0]

        # if valid file
        if file != '':
            # set the line edit widget text
            self.fileInputUI.lineEditWidget.setText(file)

            # store the output file path
            self._saveFile = file

            # save configuration to file
            self._saveConfiguration()

    def _saveConfiguration(self):
            # update the config from inputs
            self._updateConfig()

            # write the configuration to file
            self._config.write(self._saveFile)

    # public member functions
    def getInput(self):
        # return the configuration file path
        return self.fileInputUI.getInput()


class BuilderUI:

    def __init__(self):
        # store save file
        self._saveFile = None

        # build the UI
        self.__build_ui__()

    def __build_ui__(self):
        # create the dock widget
        self.dockWidget = QDockWidget()

        # create base widget and specify layout
        self.baseWidget = QGroupBox('Model Builder')
        self.baseLayout = QVBoxLayout(self.baseWidget)
        self.baseLayout.setContentsMargins(10, 10, 10, 10)
        self.dockWidget.setWidget(self.baseWidget)

        # add the toolbar buttons
        self.toolWidget, self.toolLayout = buildHLWidget(spacing=1)
        self.baseLayout.addWidget(self.toolWidget)

        self.loadButton = buildButtonWidget(icon=getIcon('mActionFileOpen.svg'), addTo=self.toolLayout)
        self.saveAsButton = buildButtonWidget(icon=getIcon('mActionFileSaveAs.svg'), addTo=self.toolLayout)
        self.saveButton = buildButtonWidget(icon=getIcon('mActionFileSave.svg'), addTo=self.toolLayout)

        self.toolLayout.addStretch()

        # self.closeButton = buildButtonWidget(icon=getIcon('mActionRemove.svg'), addTo=self.toolLayout)

        self.loadButton.clicked.connect(self.loadBuild)
        self.saveAsButton.clicked.connect(self.saveBuildAs)
        self.saveButton.clicked.connect(self.saveBuild)
        # self.closeButton.clicked.connect(self.delete)

        # add project folder input UI
        self.swanFolderUI = FolderInputUI('SWAN Folder Input')
        self.baseLayout.addWidget(self.swanFolderUI.baseWidget)

        # add configuration input UI
        self.configFileUI = ConfigurationUI()
        self.baseLayout.addWidget(self.configFileUI.baseWidget)

        # add domain input UI
        self.gridLayerUI = GridLayerInputUI()
        self.baseLayout.addWidget(self.gridLayerUI.baseWidget)

        # add a space between domain UI and date UIs
        self.baseLayout.addSpacing(10)

        # add DTM raster layer input UI
        self.bathLayerUI = LayersInputUI('Bathymetry Layer Input', ['raster', 'mesh'])
        self.baseLayout.addWidget(self.bathLayerUI.baseWidget)

        # add wind file input UI
        self.windFileUI = OpenFileInputUI('Wind File Input', "nc(*.nc);;csv(*.csv)")
        self.baseLayout.addWidget(self.windFileUI.baseWidget)

        # add wave file input UI
        self.waveFileUI = OpenFileInputUI('Wave File Input', "nc(*.nc)")
        self.baseLayout.addWidget(self.waveFileUI.baseWidget)

        # add date input UIs
        self.dateWidget, self.dateLayout = buildHLWidget(spacing=15)
        self.dateUI = (DateInputUI('Start Date: '), DateInputUI('End Date: '))

        self.dateLayout.addWidget(self.dateUI[0].baseWidget)
        self.dateLayout.addWidget(self.dateUI[1].baseWidget)

        self.baseLayout.addWidget(self.dateWidget)

        # add create simulation button
        self.buildRunButton = buildButtonWidget('Build Run', addTo=self.baseLayout)
        self.buildRunButton.clicked.connect(self.buildRun)

        # add a stretch to the end of the base layout
        self.baseLayout.addStretch(5)

        # add handler when dock widget destroyed
        # self.dockWidget.destroyed.connect(self.delete)

    def loadBuild(self):
        """Simple wrapper for ConfigParser.read() method"""

        # get file from dialogue
        file = QFileDialog.getOpenFileName(directory=os.path.curdir, filter="ini(*.ini)")[0]

        # if no file selected, do nothing
        if file == '':
            return None

        # instantiate configparser object
        cp = configparser.ConfigParser()
        cp.optionxform = str

        # read build paths from file
        cp.read(file)

        # populate SWAN folder input UI
        if 'rootFolder' in cp['SWAN BUILD']:
            self.swanFolderUI.lineEditWidget.setText(cp['SWAN BUILD']['rootFolder'])

        # clear data in bathymetry layer input UI
        self.bathLayerUI.clearLayers()

        # populate bathymetry layer input UI
        if 'bottomSource' in cp['SWAN BUILD']:
            layers, files = [], cp['SWAN BUILD']['bottomSource'].split('\n')[1:]

            for file in files:
                if not isLayer(file):
                    layers.append(addLayer(file))
                else:
                    layers.append(getLayer(file))

            self.bathLayerUI.addLayers(layers)

        # populate wind file input UI
        if 'windSource' in cp['SWAN BUILD']:
            self.windFileUI.lineEditWidget.setText(cp['SWAN BUILD']['windSource'])

        # populate wave file input UI
        if 'waveSource' in cp['SWAN BUILD']:
            self.waveFileUI.lineEditWidget.setText(cp['SWAN BUILD']['waveSource'])

        # populate grid layer input UI
        if 'gridSource' in cp['SWAN BUILD']:
            if not isLayer(cp['SWAN BUILD']['gridSource']):
                layer = addLayer(cp['SWAN BUILD']['gridSource'])
            else:
                layer = getLayer(cp['SWAN BUILD']['gridSource'])
            self.gridLayerUI.setLayer(layer)

        # populate the configuration file UI
        if 'configSource' in cp['SWAN BUILD']:
            self.configFileUI.fileInputUI.lineEditWidget.setText(cp['SWAN BUILD']['configSource'])

    def saveBuildAs(self):
        """Simple wrapper for ConfigParser.write() method"""

        # get file from dialogue
        file = QFileDialog.getSaveFileName(directory=os.path.curdir, filter="ini(*.ini)")[0]

        # return if file not valid
        if file == '':
            return

        # set the save file path
        self._saveFile = file

        # save the build
        self.saveBuild()

    def saveBuild(self):
        # check to see save file set
        if self._saveFile is None:
            self.saveBuildAs()

        # get input from the UIs
        swanFolder, templateSource, configSource, gridSource, bottomSource, windSource, waveSource = self.getInput()

        # instantiate ConfigParser object
        cp = configparser.ConfigParser()
        cp.optionxform = str

        cp['SWAN BUILD'] = {}
        if swanFolder is not None:
            cp['SWAN BUILD']['rootFolder'] = swanFolder
        if configSource is not None:
            cp['SWAN BUILD']['configSource'] = configSource
        if gridSource is not None:
            cp['SWAN BUILD']['gridSource'] = gridSource
        if len(bottomSource) != 0:
            cp['SWAN BUILD']['bottomSource'] = '\n\t' + '\n\t'.join(bottomSource)
        if windSource is not None:
            cp['SWAN BUILD']['windSource'] = windSource
        if waveSource is not None:
            cp['SWAN BUILD']['waveSource'] = waveSource

        # save it to specified destination
        with open(self._saveFile, 'w') as f:
            cp.write(f)

    def checkBuild(self):
        # error checking and messaging, potentially could move this to the actual builder class.

        # this could potentially be written to a build log

        # create empty error message
        errorMessage, fatal = None, False

        # 1. check that the current layer is not being edited
        if self.gridLayerUI.getLayer().isEditable():
            errorMessage, fatal = "Please finish editing active grid layer. All changes must be saved " \
                                  "to the grid layer file before build can proceed.", True

        # 2. check that the saved grid layer file has a projection
        if self.gridLayerUI.getInput() is not None:
            # get grid source
            gridSource = self.gridLayerUI.getInput().source().split('|')[0]
            gridSource = gridSource.replace('\\', '/')

            # create dummy data source handle
            ds = None

            # find driver and get data source handle
            for ii in range(ogr.GetDriverCount()):
                driver = ogr.GetDriver(ii)
                ds = driver.Open(gridSource)

                # break loop when found
                if ds is not None:
                    break

            # get layer and srs handle
            layer = ds.GetLayer()
            srs = layer.GetSpatialRef()

            # check srs is not none
            if srs is None:
                errorMessage, fatal = 'Grid layer shapefile has no projection. Please save a new version with a ' \
                                      'valid projection.', True

        if errorMessage is not None:
            QMessageBox.information(None, "Build Error:", str(errorMessage))

        # 3. Non-fatal, check that wind and wave times cover run time

        # 4. Non-fatal, check rotation is zero if projection is spherical

        return fatal

    def buildRun(self):
        # check for errors in the build
        if not self.checkBuild():
            builder = SwanBuilder(*self.getInput())

            timeStart = datenum(self.dateUI[0].getInput(), '%d/%m/%Y')
            timeEnd = datenum(self.dateUI[1].getInput(), '%d/%m/%Y')

            builder.buildRun(timeStart, timeEnd)

    def getInput(self):
        # get the swan folder path
        swanFolder = self.swanFolderUI.getInput()
        if swanFolder is not None:
            swanFolder = swanFolder.replace('\\', '/')

        # get the template source file path
        templateSource = os.path.dirname(__file__) + '\\template'
        templateSource = templateSource.replace('\\', '/')

        # get the configuration source file path
        configSource = self.configFileUI.getInput()
        if configSource is not None:
            configSource = configSource.replace('\\', '/')

        # get grid source file path
        if self.gridLayerUI.getInput() is not None:
            gridSource = self.gridLayerUI.getInput().source().split('|')[0]
            gridSource = gridSource.replace('\\', '/')
        else:
            gridSource = None

        # get bottom source as list of file paths
        bottomSource = [layer.source().split('|')[0] for layer in self.bathLayerUI.getInput()]
        bottomSource = [string.replace('\\', '/') for string in bottomSource]

        # get wind source file path
        windSource = self.windFileUI.getInput()
        if windSource is not None:
            windSource = windSource.replace('\\', '/')

        # get wave source file path
        waveSource = self.waveFileUI.getInput()
        if waveSource is not None:
            waveSource = waveSource.replace('\\', '/')

        return swanFolder, templateSource, configSource, gridSource, bottomSource, windSource, waveSource


class ConvertMat2NcUI:

    def __init__(self):
        # build the ui
        self.__build_ui__()

    def __build_ui__(self):
        # create base widget and specify layout
        self.baseWidget = QGroupBox('Convert MAT to netCDF4')
        self.baseLayout = QVBoxLayout(self.baseWidget)
        self.baseLayout.setContentsMargins(10, 10, 10, 10)

        # add SWAN result file input UI
        self.inputUI = OpenFileInputUI('MAT SWAN Result File Input', "mat(*.mat)")
        self.baseLayout.addWidget(self.inputUI.baseWidget)

        # add the convert format button
        self.convertButton = buildButtonWidget('Convert', addTo=self.baseLayout)
        self.convertButton.clicked.connect(self.convertMat2Nc)

        # add a stretch to the end of the base layout
        self.baseLayout.addStretch(5)

    def convertMat2Nc(self):
        matFile = self.inputUI.getInput()
        ncFile = matFile.replace('.mat', '.nc')
        convertMat2Nc(matFile, ncFile)


class ExtractSwanTsUI:

    def __init__(self):
        # build the ui
        self.__build_ui__()

    def __build_ui__(self):
        # create base widget and specify layout
        self.baseWidget = QGroupBox('SWAN Time Series Extractor')
        self.baseLayout = QVBoxLayout(self.baseWidget)
        self.baseLayout.setContentsMargins(10, 10, 10, 10)

        # add SWAN result file input UI
        self.inputUI = OpenFileInputUI('NetCDF4 SWAN Result File Input', "nc(*.nc)")
        self.baseLayout.addWidget(self.inputUI.baseWidget)

        # add output file input UI
        self.outputUI = SaveFileInputUI('Output Time Series File Input', "csv(*.csv)")
        self.baseLayout.addWidget(self.outputUI.baseWidget)

        # add points file input UI
        self.pointsUI = OpenFileInputUI('Points File Input', "csv(*.csv)")
        self.baseLayout.addWidget(self.pointsUI.baseWidget)

        # add the download button
        self.extractButton = buildButtonWidget('Extract', addTo=self.baseLayout)
        self.extractButton.clicked.connect(self.extractSwanTs)

        # add a stretch to the end of the base layout
        self.baseLayout.addStretch(5)

    def extractSwanTs(self):
        inFile = self.inputUI.getInput()
        outFile = self.outputUI.getInput()
        pointsFile = self.pointsUI.getInput()

        extractSwanTs(inFile, outFile, pointsFile)


class ExtractEraTsUI:

    def __init__(self):
        # build the ui
        self.__build_ui__()

    def __build_ui__(self):
        # create base widget and specify layout
        self.baseWidget = QGroupBox('ERA5 Time Series Extractor')
        self.baseLayout = QVBoxLayout(self.baseWidget)
        self.baseLayout.setContentsMargins(10, 10, 10, 10)

        # add SWAN result file input UI
        self.inputUI = OpenFileInputUI('NetCDF4 ERA5 File Input', "nc(*.nc)")
        self.baseLayout.addWidget(self.inputUI.baseWidget)

        # add output file input UI
        self.outputUI = SaveFileInputUI('Output Time Series File Input', "csv(*.csv)")
        self.baseLayout.addWidget(self.outputUI.baseWidget)

        # add points file input UI
        self.pointsUI = OpenFileInputUI('Points File Input', "csv(*.csv)")
        self.baseLayout.addWidget(self.pointsUI.baseWidget)

        # add the download button
        self.extractButton = buildButtonWidget('Extract', addTo=self.baseLayout)
        self.extractButton.clicked.connect(self.extractEraTs)

        # add a stretch to the end of the base layout
        self.baseLayout.addStretch(5)

    def extractEraTs(self):
        inFile = self.inputUI.getInput()
        outFile = self.outputUI.getInput()
        pointsFile = self.pointsUI.getInput()

        extractEraTs(inFile, outFile, pointsFile)


class PostProcessingUI:

    def __init__(self):
        # build the ui
        self.__build_ui__()

    def __build_ui__(self):
        # create the dock widget
        self.dockWidget = QDockWidget()

        # create base widget and set layout
        self.baseWidget, self.baseLayout = buildVLWidget()
        self.dockWidget.setWidget(self.baseWidget)

        # add convert result file format UI
        self.convertMat2NcUI = ConvertMat2NcUI()
        self.baseLayout.addWidget(self.convertMat2NcUI.baseWidget)

        # add extract SWAN time series UI
        self.extractSwanTsUI = ExtractSwanTsUI()
        self.baseLayout.addWidget(self.extractSwanTsUI.baseWidget)

        # add extract SWAN time series UI
        self.extractEraTsUI = ExtractEraTsUI()
        self.baseLayout.addWidget(self.extractEraTsUI.baseWidget)

        # add a stretch to the end of the base layout
        self.baseLayout.addStretch(5)


class PluginMenuUI:

    def __init__(self, iface):
        self.iface = iface

        self.builderAction = None
        self.builderUI = None

        self.processingAction = None
        self.processingUI = None

        # hack to reset plugin when project changed
        getProject().cleared.connect(self.clearBuilderUI)

    def initGui(self):
        self.builderAction = QAction("Model Builder", self.iface.mainWindow())
        self.builderAction.triggered.connect(self.runBuilderUI)
        self.iface.addPluginToMenu("&SWAN GIS Tools (beta)", self.builderAction)

        self.processingAction = QAction("Post Processing", self.iface.mainWindow())
        self.processingAction.triggered.connect(self.runProcessingUI)
        self.iface.addPluginToMenu("&SWAN GIS Tools (beta)", self.processingAction)

    def runBuilderUI(self):
        if self.builderUI is None:
            self.builderUI = BuilderUI()
            self.iface.mainWindow().addDockWidget(Qt.RightDockWidgetArea, self.builderUI.dockWidget)
        else:
            self.builderUI.dockWidget.setVisible(True)

    def runProcessingUI(self):
        if self.processingUI is None:
            self.processingUI = PostProcessingUI()
            self.iface.mainWindow().addDockWidget(Qt.RightDockWidgetArea, self.processingUI.dockWidget)
        else:
            self.processingUI.dockWidget.setVisible(True)

    def clearBuilderUI(self):
        # remove the builder UI if active and save project
        if self.builderUI is not None:
            self.iface.removeDockWidget(self.builderUI.dockWidget)
            self.builderUI.dockWidget.setParent(None)
            self.builderUI.gridLayerUI.setLayer(None)
            self.builderUI = None

    def clearProcessingUI(self):
        # remove the processing UI if active
        if self.processingUI is not None:
            self.processingUI.dockWidget.close()
            self.iface.removeDockWidget(self.processingUI.dockWidget)
            self.processingUI = None

    def unload(self):
        # clear the builder UI
        self.clearBuilderUI()

        # clear the processing UI
        self.clearProcessingUI()

        # remove the actions from the menu
        self.iface.removePluginMenu("&SWAN GIS Tools (beta)", self.builderAction)
        self.iface.removePluginMenu("&SWAN GIS Tools (beta)", self.processingAction)