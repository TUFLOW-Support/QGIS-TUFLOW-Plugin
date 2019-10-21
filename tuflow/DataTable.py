import os, sys
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5 import QtGui
from qgis.core import *
from qgis.gui import QgsCheckableComboBox
from PyQt5.QtWidgets import *
from .tuflowqgis_library import browse


class TableComboBox(QComboBox):
    
    def showPopup(self):
        self.view().setMinimumWidth(self.view().sizeHintForColumn(0))
        QComboBox.showPopup(self)


class TableCheckableComboBox(TableComboBox):
    
    checkedItemsChanged = pyqtSignal(list)
    
    def __init__(self, parent=None):
        TableComboBox.__init__(self, parent)
        self.view().pressed.connect(self.handleItemPressed)
        self._changed = False
        
    def handleItemPressed(self, index):
        item = self.model().itemFromIndex(index)
        if item.checkState() == Qt.Checked:
            item.setCheckState(Qt.Unchecked)
        else:
            item.setCheckState(Qt.Checked)
        self._changed = True
        
    def hidePopup(self):
        if not self._changed:
            TableComboBox.hidePopup(self)
        else:
            self._changed = False
            
    def checkedItems(self):
        checkedItems = []
        for i in range(self.count()):
            item = self.model().item(i, 0)
            if item.checkState() == Qt.Checked:
                checkedItems.append(self.itemText(i))
        
        return checkedItems
    
    def setCheckedItems(self, items: list):
        for i in range(self.count()):
            item = self.model().item(i, 0)
            if self.itemText(i) in items:
                item.setCheckState(Qt.Checked)
            else:
                item.setCheckState(Qt.Unchecked)
                
    def addItems(self, Iterable, p_str=None):
        QComboBox.addItems(self, Iterable)
        for i in range(self.count()):
            item = self.model().item(i, 0)
            item.setCheckState(Qt.Unchecked)
        self.setCurrentIndex(-1)


class ComboBoxBrowseDelegate(QStyledItemDelegate):
    
    def __init__(self, parent=None, items=(), signalProperties=None):
        QStyledItemDelegate.__init__(self, parent)
        self.items = items
        self.signalProperties = signalProperties

    def addItem(self, item):
        self.items.append(item)

    def addItems(self, items):
        self.items += items

    def setItems(self, items):
        self.items = items

    def clear(self):
        self.items.clear()

    def removeItem(self, i):
        self.items.pop(i)
        
    def setSignalProperties(self, signalProperties):
        self.signalProperties = signalProperties

    def createEditor(self, parent, option, index):
        cbo = TableComboBox(parent)
        cbo.setEditable(True)
        cbo.clear()
        cbo.addItems(self.items)

        btn = QToolButton()
        btn.setIcon(QgsApplication.getThemeIcon('/mActionFileOpen.svg'))
        btn.setToolTip('Input Result File')
        if self.signalProperties is not None:
            btn.clicked.connect(lambda: browse(self.signalProperties['parent'],
                                               self.signalProperties['browse type'],
                                               self.signalProperties['key'],
                                               self.signalProperties['title'],
                                               self.signalProperties['file types'],
                                               index))

        inputWidget = QWidget(parent)
        hbox = QHBoxLayout()
        hbox.addWidget(btn)
        hbox.addWidget(cbo)
        hbox.setContentsMargins(0, 0, 0, 0)
        hbox.setSpacing(0)
        inputWidget.setLayout(hbox)
        editor = inputWidget
        return editor

    def setEditorData(self, editor, index):
        txt = index.model().data(index, Qt.EditRole)
        if txt is None:
            txt = ''
        editor.layout().itemAt(1).widget().setCurrentText(txt)

    def setModelData(self, editor, model, index):
        txt = editor.layout().itemAt(1).widget().currentText()
        model.setData(index, txt, Qt.EditRole)

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)


class LineEditBrowseDelegate(QStyledItemDelegate):
    
    def __init__(self, parent=None, signalProperties=None):
        QStyledItemDelegate.__init__(self, parent)
        self.signalProperties = signalProperties
        
    def setSignalProperties(self, signalProperties):
        self.signalProperties = signalProperties
    
    def createEditor(self, parent, option, index):
        le = QLineEdit(parent)
        le.setFrame(False)
        
        btn = QToolButton()
        btn.setIcon(QgsApplication.getThemeIcon('/mActionFileOpen.svg'))
        btn.setToolTip('Input Result File')
        if self.signalProperties is not None:
            btn.clicked.connect(lambda: browse(self.signalProperties['parent'],
                                               self.signalProperties['browse type'],
                                               self.signalProperties['key'],
                                               self.signalProperties['title'],
                                               self.signalProperties['file types'],
                                               index))
        
        inputWidget = QWidget(parent)
        hbox = QHBoxLayout()
        hbox.addWidget(btn)
        hbox.addWidget(le)
        hbox.setContentsMargins(0, 0, 0, 0)
        hbox.setSpacing(0)
        inputWidget.setLayout(hbox)
        editor = inputWidget
        return editor
    
    def setEditorData(self, editor, index):
        txt = index.model().data(index, Qt.EditRole)
        if txt is None:
            txt = ''
        editor.layout().itemAt(1).widget().setText(txt)
    
    def setModelData(self, editor, model, index):
        txt = editor.layout().itemAt(1).widget().text()
        model.setData(index, txt, Qt.EditRole)
    
    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)


class ComboBoxDelegate(QStyledItemDelegate):
    
    def __init__(self, parent=None, items=(), default=None):
        QStyledItemDelegate.__init__(self, parent)
        self.items = []
        self.itemsInRows = {}  # row: items
        self.default = default
   
    def setItems(self, row=None, items=(), default=None):
        if row is None:
            self.items = items
        else:
            self.itemsInRows[row] = items
        
        if default is not None:
            self.default = default
    
    def clear(self):
        self.items.clear()
    
    def createEditor(self, parent, option, index):
        editor = TableComboBox(parent)
        editor.setEditable(True)
        editor.clear()
        if self.itemsInRows:
            if index.row() in self.itemsInRows:
                editor.addItems(self.itemsInRows[index.row()])
        else:
            editor.addItems(self.items)
            
        return editor
    
    def setEditorData(self, editor, index):
        txt = index.model().data(index, Qt.EditRole)
        editor.setCurrentText(txt)
        editor.showPopup()
    
    def setModelData(self, editor, model, index):
        txt = editor.currentText()
        if txt == '':
            txt = model.data(index, Qt.EditRole)
        model.setData(index, txt, Qt.EditRole)
    
    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)


class CheckableComboBoxDelegate(QStyledItemDelegate):
    
    def __init__(self, parent=None, items=()):
        QStyledItemDelegate.__init__(self, parent)
        self.items = []
        self.itemsInRows = {}  # row: items
        self.currentCheckedItems = {}  # row: [checkedItems]
    
    def setItems(self, row=None, items=()):
        if row is None:
            self.items = items
        else:
            self.itemsInRows[row] = items
    
    def clear(self):
        self.items.clear()
    
    def createEditor(self, parent, option, index):
        editor = TableCheckableComboBox(parent)
        editor.setEditable(True)
        editor.clear()
        if self.itemsInRows:
            if index.row() in self.itemsInRows:
                editor.addItems(self.itemsInRows[index.row()])
        else:
            editor.addItems(self.items)
        if index.row() in self.currentCheckedItems:
            editor.setCheckedItems(self.currentCheckedItems[index.row()])
        else:
            editor.setCheckedItems([])

        return editor
    
    def setEditorData(self, editor, index):
        txt = index.model().data(index, Qt.EditRole)
        editor.setCurrentText(txt)
        editor.showPopup()
    
    def setModelData(self, editor, model, index):
        currentCheckedItems = editor.checkedItems()
        self.currentCheckedItems[index.row()] = currentCheckedItems
        txt = ';;'.join(currentCheckedItems)
        model.setData(index, txt, Qt.EditRole)
    
    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)
        
    def checkedItems(self, row):
        if row in self.currentCheckedItems:
            return self.currentCheckedItems[row]
        else:
            return []


class HeaderTable(QHeaderView):
    
    def __init__(self):
        QHeaderView.__init__(self, Qt.Vertical)
        self.setHighlightSections(True)
        self.setSectionsClickable(True)
        dir = os.path.dirname(__file__)
        cursorIcon = os.path.join(dir, "icons", "HorizontalArrowCursor.png")
        pix_cursor = QPixmap(cursorIcon)
        pix_cursor_scaled = pix_cursor.scaledToHeight(10)
        self.cursor = QCursor(pix_cursor_scaled)
    
    def enterEvent(self, a0):
        QHeaderView.enterEvent(self, a0)
        QApplication.setOverrideCursor(self.cursor)
    
    def leaveEvent(self, a0):
        QHeaderView.leaveEvent(self, a0)
        QApplication.restoreOverrideCursor()


class TuViewTable(QTableWidget):
    
    def __init__(self, parent=None):
        QTableWidget.__init__(self, parent)
        self.setVerticalHeader(HeaderTable())
        #self.setEditTriggers(QAbstractItemView.AllEditTriggers)
        
    #def mouseReleaseEvent(self, e):
    #    QTableWidget.mousePressEvent(self, e)
    #    index = self.indexAt(e.pos())
    #    if index.isValid():
    #        if e.button() == Qt.LeftButton:
    #            QTableWidget.mouseDoubleClickEvent(self, e)
            

class MapExportTable(TuViewTable):
    
    def __init__(self, parent=None):
        TuViewTable.__init__(self, parent)
        self.setItemDelegateForColumn(0, ComboBoxBrowseDelegate(self))
        self.setItemDelegateForColumn(1, ComboBoxDelegate(self))
        self.setItemDelegateForColumn(2, ComboBoxDelegate(self))
        self.setItemDelegateForColumn(3, ComboBoxDelegate(self))
        self.setItemDelegateForColumn(4, LineEditBrowseDelegate(self))
        
            
class PlotItemsTable(TuViewTable):
    
    def __init__(self, parent=None):
        TuViewTable.__init__(self, parent)
        self.setItemDelegateForColumn(0, ComboBoxDelegate(self))
        self.setItemDelegateForColumn(1, CheckableComboBoxDelegate(self))
        self.setItemDelegateForColumn(2, ComboBoxDelegate(self))
        
        
class GraphicItemsTable(TuViewTable):
    
    def __init__(self, parent=None):
        TuViewTable.__init__(self, parent)
        self.setItemDelegateForColumn(2, ComboBoxDelegate(self))
        
        
class ImageItemsTable(TuViewTable):
    
    def __init__(self, parent=None):
        TuViewTable.__init__(self, parent)
        self.setItemDelegateForColumn(0, LineEditBrowseDelegate(self))
        self.setItemDelegateForColumn(1, ComboBoxDelegate(self))
        
        
class PlotManagerTable(TuViewTable):
    
    def __init__(self, parent=None):
        TuViewTable.__init__(self, parent)
        self.setItemDelegateForColumn(1, ComboBoxDelegate(self))
