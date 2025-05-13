import os, sys
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
from qgis.PyQt import QtGui
from qgis.core import *
from qgis.PyQt.QtWidgets import *
import io
import numpy as np
import re



from ..compatibility_routines import QT_VERTICAL, QT_EVENT_KEY_PRESS, QT_LEFT_BUTTON, QT_KEY_SEQUENCE_COPY, QT_ITEM_DATA_EDIT_ROLE, QT_HEADER_VIEW_INTERACTIVE, QT_KEY_SEQUENCE_PASTE, QT_ITEM_SELECTION_SELECT, QT_HEADER_VIEW_STRETCH


class SpinBoxDelegate(QStyledItemDelegate):
    
    def __init__(self, parent=None, minimum=-99999, maximum=99999, increment=1, decimals=3):
        QStyledItemDelegate.__init__(self, parent)
        self.minimum = minimum
        self.maximum = maximum
        self.increment = increment
        self.decimals = decimals
        self.editor = {}
    
    def createEditor(self, parent, option, index):
        editor = QDoubleSpinBox(parent)
        loc = (index.row(), index.column())
        if loc in self.editor:
            minimum = self.editor[loc]
        else:
            self.editor[loc] = self.minimum
            minimum = self.minimum
        editor.setFrame(False)
        editor.setMinimum(minimum)
        editor.setMaximum(self.maximum)
        editor.setDecimals(self.decimals)
        editor.setSingleStep(self.increment)
        return editor
    
    def setEditorData(self, editor, index):
        try:
            value = float(index.model().data(index, QT_ITEM_DATA_EDIT_ROLE))
        except ValueError:
            value = 0
        except TypeError:
            value = 0
        editor.setValue(value)
    
    def setModelData(self, editor, model, index):
        editor.interpretText()
        value = '{0:.{1}f}'.format(editor.value(), self.decimals)
        model.setData(index, value, QT_ITEM_DATA_EDIT_ROLE)
    
    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)
        
    def setMinimum(self, minimum, row, col):
        loc = (row, col)
        self.editor[loc] = minimum
    
    def getMinimum(self, row, col):
        loc = (row, col)
        if loc in self.editor:
            return self.editor[loc]
        else:
            return self.minimum

    def paint(self, painter, styleOption, index):
        QStyledItemDelegate.paint(self, painter, styleOption, index)
        oldState = self.parent().blockSignals(True)
        editor = self.createEditor(self.parent(), None, index)
        self.setEditorData(editor, index)
        self.setModelData(editor, index.model(), index)
        self.parent().blockSignals(oldState)


class SpinBoxDelegateMannings(SpinBoxDelegate):
    
    def __init__(self, parent=None):
        SpinBoxDelegate.__init__(self, parent)
    
    def createEditor(self, parent, option, index):
        editor = QDoubleSpinBox(parent)
        editor.setFrame(False)
        editor.setMinimum(0.)
        editor.setMaximum(99999)
        editor.setDecimals(3)
        return editor


class ComboBoxDelegate(QStyledItemDelegate):
    
    def __init__(self, parent=None, items=()):
        QStyledItemDelegate.__init__(self, parent)
        self.items = items
        
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
    
    def createEditor(self, parent, option, index):
        editor = QComboBox(parent)
        editor.setEditable(True)
        editor.clear()
        editor.addItems(self.items)
        return editor
    
    def setEditorData(self, editor, index, showPopup=True):
        txt = index.model().data(index, QT_ITEM_DATA_EDIT_ROLE)
        if txt is None:
            txt = ''
        if type(txt) is float:
            editor.setCurrentText(f'{txt:.03f}')
        else:
            editor.setCurrentText(f'{txt}')

        if showPopup:
            editor.showPopup()
    
    def setModelData(self, editor, model, index):
        txt = editor.currentText()
        if txt != '':
            if txt not in self.items:
                txt = ''
        model.setData(index, txt, QT_ITEM_DATA_EDIT_ROLE)
    
    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)

    def paint(self, painter, styleOption, index):
        QStyledItemDelegate.paint(self, painter, styleOption, index)
        oldState = self.parent().blockSignals(True)
        editor = self.createEditor(self.parent(), None, index)
        self.setEditorData(editor, index, showPopup=False)
        self.setModelData(editor, index.model(), index)
        self.parent().blockSignals(oldState)


class HeaderChannelTable(QHeaderView):
    
    def __init__(self):
        QHeaderView.__init__(self, QT_VERTICAL)
        self.setHighlightSections(True)
        self.setSectionsClickable(True)
        dir = os.path.dirname(os.path.dirname(__file__))
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



class ChannelSectionTable(QTableWidget):
    
    def __init__(self, parent=None):
        QTableView.__init__(self, parent)
        self.setItemDelegate(SpinBoxDelegate(self))
        # self.setItemDelegateForColumn(2, SpinBoxDelegateMannings(self))
        self.setVerticalHeader(HeaderChannelTable())
        self.installEventFilter(self)
        
    def mouseReleaseEvent(self, e):
        QTableWidget.mouseReleaseEvent(self, e)
        if len(self.selectedIndexes()) > 1:
            return
        if e.button() == QT_LEFT_BUTTON:
            QTableWidget.mouseDoubleClickEvent(self, e)

    def eventFilter(self, source, event):
        if (event.type() == QT_EVENT_KEY_PRESS and
                event.matches(QT_KEY_SEQUENCE_PASTE)):
            self.pasteIntoSelection()
            return True
        if (event.type() == QT_EVENT_KEY_PRESS and
                event.matches(QT_KEY_SEQUENCE_COPY)):
            self.copyFromSelection()
            return True

        return QTableWidget.eventFilter(self, source, event)

    def copyFromSelection(self):
        selection = self.selectedIndexes()
        if selection:
            rows = sorted(index.row() for index in selection)
            columns = sorted(index.column() for index in selection)
            rowcount = rows[-1] - rows[0] + 1
            colcount = columns[-1] - columns[0] + 1
            a = [[''] * colcount for _ in range(rowcount)]
            for index in selection:
                row = index.row() - rows[0]
                column = index.column() - columns[0]
                a[row][column] = str(index.data())

            text = '\n'.join(['\t'.join(y) for y in a])
            QApplication.clipboard().setText(text)

    def pasteIntoSelection(self):
        mimeData = QApplication.clipboard().mimeData()
        if not mimeData.hasText():
            return
        try:
            a = np.array([[y for y in re.split(r'\t|\s|,', x.strip())] for x in mimeData.text().strip().split('\n')],
                         dtype=np.float64)
        except ValueError:
            return

        selection = self.selectedIndexes()
        model = self.model()
        if a.shape == (1, 1):
            for index in selection:
                model.setData(model.index(index.row(), index.column()), a[0,0])
                self.update(index)
        else:
            rows = sorted(index.row() for index in selection)
            columns = sorted(index.column() for index in selection)
            nrow = a.shape[0]
            ncol = min(len(set(columns)), a.shape[1])
            # data_len = nrow * ncol
            # if a.shape[1] >= 3 and ncol >= 3 and a.shape[0] > self.rowCount() - rows[0]:
            if a.shape[0] > self.rowCount() - rows[0]:
                self.setRowCount(rows[0] + a.shape[0])
                addSel = QItemSelection(model.index(rows[-1] + 1, columns[0]), model.index(self.rowCount() - 1, columns[-1]))
                self.selectionModel().select(addSel, QT_ITEM_SELECTION_SELECT)
                selection = self.selectedIndexes()
            for i, index in enumerate(selection):
                # if i + 1 > data_len:
                #     break
                # else:
                row = index.row() - rows[0]
                col = index.column() - columns[0]
                if a.shape[0] > row and a.shape[1] > col:
                    model.setData(index, a[row,col])
                else:
                    model.setData(index, 0)
                self.update(index)


class BridgeSectionTable(QTableWidget):
    
    def __init__(self, parent=None):
        QTableView.__init__(self, parent)
        self.setItemDelegate(SpinBoxDelegate(self))
        # self.setItemDelegateForColumn(0, ComboBoxDelegate(self))
        # self.setItemDelegateForColumn(1, ComboBoxDelegate(self))
        self.setItemDelegateForColumn(0, SpinBoxDelegate(self))
        self.setItemDelegateForColumn(1, SpinBoxDelegate(self))
        self.setItemDelegateForColumn(2, SpinBoxDelegate(self))
        self.setItemDelegateForColumn(3, SpinBoxDelegate(self))
        self.setVerticalHeader(HeaderChannelTable())

        self.horizontalHeader().setSectionResizeMode(QT_HEADER_VIEW_INTERACTIVE)
        self.horizontalHeader().resizeSections(QT_HEADER_VIEW_STRETCH)

        self.installEventFilter(self)

    def mouseReleaseEvent(self, e):
        QTableWidget.mouseReleaseEvent(self, e)
        if len(self.selectedIndexes()) > 1:
            return
        if e.button() == QT_LEFT_BUTTON:
            QTableWidget.mouseDoubleClickEvent(self, e)
    
    def customUpdate(self, i):
        text = self.item(i, 0).text()
        if text not in self.itemDelegateForColumn(0).items:
            self.item(i, 0).setText('')
        
        text = self.item(i, 1).text()
        if text not in self.itemDelegateForColumn(1).items:
            self.item(i, 1).setText('')

    def setMinimum(self, minimum, row, col):
        delegate = self.itemDelegateForColumn(col)
        if delegate is not None:
            minimumPrev = delegate.getMinimum(row, col)
            if minimum > minimumPrev:
                if self.item(row, col) is not None:
                    try:
                        if float(self.model().data(self.model().index(row, col))) < minimum:
                            self.item(row, col).setText('{0:.3f}'.format(minimum))
                    except ValueError:
                        pass
            delegate.setMinimum(minimum, row, col)
            
    def findMatchingRowIndexes(self, row, col):
        indexes = []
        delegate = self.itemDelegateForColumn(col)
        if delegate is not None:
            if self.item(row, col) is not None:
                value = self.item(row, col).text()
                for i, item in enumerate(delegate.items):
                    if float(item) == float(value):
                        indexes.append(i)
                        
        return indexes

    def eventFilter(self, source, event):
        if (event.type() == QT_EVENT_KEY_PRESS and
                event.matches(QT_KEY_SEQUENCE_PASTE)):
            self.pasteIntoSelection()
            return True
        if (event.type() == QT_EVENT_KEY_PRESS and
                event.matches(QT_KEY_SEQUENCE_COPY)):
            self.copyFromSelection()
            return True

        return QTableWidget.eventFilter(self, source, event)

    def copyFromSelection(self):
        selection = self.selectedIndexes()
        if selection:
            rows = sorted(index.row() for index in selection)
            columns = sorted(index.column() for index in selection)
            rowcount = rows[-1] - rows[0] + 1
            colcount = columns[-1] - columns[0] + 1
            a = [[''] * colcount for _ in range(rowcount)]
            for index in selection:
                row = index.row() - rows[0]
                column = index.column() - columns[0]
                a[row][column] = index.data()

            text = '\n'.join(['\t'.join(y) for y in a])
            QApplication.clipboard().setText(text)

    def pasteIntoSelection(self):
        mimeData = QApplication.clipboard().mimeData()
        if not mimeData.hasText():
            return
        try:
            a = np.array([[y for y in re.split(r'\t|\s|,', x.rstrip())] for x in mimeData.text().rstrip().split('\n')])
        except ValueError:
            return

        selection = self.selectedIndexes()
        model = self.model()
        if a.shape == (1, 1):
            for index in selection:
                model.setData(model.index(index.row(), index.column()), a[0, 0])
                self.update(index)
        else:
            rows = sorted(index.row() for index in selection)
            columns = sorted(index.column() for index in selection)
            nrow = a.shape[0]
            ncol = min(len(set(columns)), a.shape[1])
            # data_len = nrow * ncol
            # if a.shape[1] >= 4 and ncol >= 4 and a.shape[0] > self.rowCount() - rows[0]:
            if a.shape[0] > self.rowCount() - rows[0]:
                self.setRowCount(rows[0] + a.shape[0])
                addSel = QItemSelection(model.index(rows[-1] + 1, columns[0]), model.index(self.rowCount() - 1, columns[-1]))
                self.selectionModel().select(addSel, QT_ITEM_SELECTION_SELECT)
                selection = self.selectedIndexes()
            for i, index in enumerate(selection):
                # if i + 1 > data_len:
                #     break
                # else:
                row = index.row() - rows[0]
                col = index.column() - columns[0]
                if a.shape[0] > row and a.shape[1] > col:
                    model.setData(index, a[row, col])
                else:
                    model.setData(index, 0)
                self.update(index)


class BridgeCurveTable(ChannelSectionTable):

    def pasteIntoSelection(self):
        return