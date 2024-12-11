from qgis.core import QgsCoordinateReferenceSystem
from qgis.gui import QgsProjectionSelectionWidget, QgsCheckableComboBox

from PyQt5.QtCore import Qt, pyqtSignal, QSize, QEvent
from PyQt5.QtWidgets import (QStyledItemDelegate, QComboBox, QApplication, QStyle, QStyleOptionViewItem, QSpinBox,
                             QDoubleSpinBox, QAbstractItemDelegate, QMenu, QLineEdit)
from PyQt5.QtGui import QAbstractTextDocumentLayout, QTextDocument, QPalette

from tuflow.gui.widgets.checkable_combobox import CheckableComboBox


class RichTextDelegate(QStyledItemDelegate):
    """Delegate for rendering rich text in a table cell."""

    def paint(self, painter, option, index):
        painter.save()

        # Create a QTextDocument to render the rich text
        doc = QTextDocument()
        doc.setHtml(str(index.data()))

        # Adjust the text document's layout to fit the cell
        option = QStyleOptionViewItem(option)
        option.text = str(index.model().data(index, Qt.DisplayRole))
        doc.setTextWidth(option.rect.width())

        # Draw the background
        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())

        # Calculate the vertical position to center the text
        text_height = doc.size().height()
        vertical_offset = (option.rect.height() - text_height) / 2

        # Render the text document
        painter.translate(option.rect.left(), option.rect.top() + vertical_offset)

        # Render the text document
        ctx = QAbstractTextDocumentLayout.PaintContext()
        if option.state & QStyle.State_Selected:
            ctx.palette.setColor(QPalette.Text, option.palette.highlightedText().color())
        doc.documentLayout().draw(painter, ctx)

        painter.restore()

    def sizeHint(self, option, index):
        doc = QTextDocument()
        doc.setHtml(index.data())
        doc.setTextWidth(option.rect.width())
        return QSize(doc.idealWidth(), doc.size().height())


class ComboBoxDelegate(RichTextDelegate):
    """Delegate for rendering a combobox in a table cell."""

    def __init__(self, parent=None, col_idx=-1, items=()):
        QStyledItemDelegate.__init__(self, parent)
        self.items = items
        self.col_idx = col_idx
        self.prev_val = ''

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
        if index.column() != -1 and index.column() != self.col_idx:
            return super().createEditor(parent, option, index)
        editor = QComboBox(parent)
        editor.setEditable(True)
        editor.clear()
        editor.addItems(self.items)
        return editor

    def setEditorData(self, editor, index, showPopup=True):
        if index.column() != -1 and index.column() != self.col_idx:
            super().setEditorData(editor, index)
            return
        txt = index.model().data(index, Qt.EditRole)
        if txt is None:
            txt = ''
        if type(txt) is float:
            editor.setCurrentText(f'{txt:.03f}')
        else:
            editor.setCurrentText(f'{txt}')
        self.prev_val = txt
        if showPopup:
            editor.showPopup()

    def setModelData(self, editor, model, index):
        if index.column() != -1 and index.column() != self.col_idx:
            super().setModelData(editor, model, index)
            return
        txt = editor.currentText()
        if txt not in self.items:
            txt = self.prev_val
        model.setData(index, txt, Qt.EditRole)

    def updateEditorGeometry(self, editor, option, index):
        super().updateEditorGeometry(editor, option, index)
        editor.setGeometry(option.rect)

    def paint(self, painter, styleOption, index):
        if index.column() != -1 and index.column() != self.col_idx:
            super().paint(painter, styleOption, index)
            return
        QStyledItemDelegate.paint(self, painter, styleOption, index)
        oldState = self.parent().blockSignals(True)
        editor = self.createEditor(self.parent(), None, index)
        self.setEditorData(editor, index, showPopup=False)
        self.setModelData(editor, index.model(), index)
        self.parent().blockSignals(oldState)


class MultiComboBoxDelegate(ComboBoxDelegate):

    def createEditor(self, parent, option, index):
        if index.column() != -1 and index.column() != self.col_idx:
            return super().createEditor(parent, option, index)
        editor = CheckableComboBox(parent)
        editor.clear()
        editor.addItems(self.items)
        editor.checkedItemsChanged.connect(lambda: self.commitData.emit(editor))
        return editor

    def setEditorData(self, editor, index, showPopup=True):
        if index.column() != -1 and index.column() != self.col_idx:
            super().setEditorData(editor, index)
            return
        txt = index.model().data(index, Qt.EditRole)
        if txt is None:
            txt = ''
        checked_items = [x.strip() for x in txt.split(',')]
        editor.setCheckedItems(checked_items)

    def setModelData(self, editor, model, index):
        if index.column() != -1 and index.column() != self.col_idx:
            super().setModelData(editor, model, index)
            return
        txt = ', '.join([x for x in editor.checkedItems()])
        model.setData(index, txt, Qt.EditRole)


class SpinBoxDelegate(RichTextDelegate):

    def __init__(self, parent=None, col_idx=-1, minimum=0, maximum=99999, step=1):
        super().__init__(parent)
        self.col_idx = col_idx
        self.minimum = minimum
        self.maximum = maximum
        self.step = step

    def createEditor(self, parent, option, index):
        if index.column() != -1 and index.column() != self.col_idx:
            return super().createEditor(parent, option, index)
        editor = QSpinBox(parent)
        editor.setFrame(False)
        editor.setMinimum(self.minimum)
        editor.setMaximum(self.maximum)
        editor.setSingleStep(self.step)
        return editor

    def setEditorData(self, editor, index):
        if index.column() != -1 and index.column() != self.col_idx:
            super().setEditorData(editor, index)
            return
        try:
            value = int(index.model().data(index, Qt.EditRole))
        except ValueError:
            value = 0
        except TypeError:
            value = 0
        editor.setValue(value)

    def setModelData(self, editor, model, index):
        if index.column() != -1 and index.column() != self.col_idx:
            super().setModelData(editor, model, index)
            return
        editor.interpretText()
        value = str(editor.value())
        model.setData(index, value, Qt.EditRole)

    def updateEditorGeometry(self, editor, option, index):
        super().updateEditorGeometry(editor, option, index)
        editor.setGeometry(option.rect)

    def paint(self, painter, styleOption, index):
        if index.column() != -1 and index.column() != self.col_idx:
            super().paint(painter, styleOption, index)
            return
        QStyledItemDelegate.paint(self, painter, styleOption, index)
        oldState = self.parent().blockSignals(True)
        editor = self.createEditor(self.parent(), None, index)
        self.setEditorData(editor, index)
        self.setModelData(editor, index.model(), index)
        self.parent().blockSignals(oldState)


class DoubleSpinBoxDelegate(SpinBoxDelegate):

    def __init__(self, parent=None, col_idx=-1, minimum=0, maximum=99999, step=1, decimals=2):
        super().__init__(parent, col_idx, minimum, maximum, step)
        self.decimals = decimals

    def setEditorData(self, editor, index):
        if index.column() != -1 and index.column() != self.col_idx:
            super().setEditorData(editor, index)
            return
        try:
            value = float(index.model().data(index, Qt.EditRole))
        except ValueError:
            value = 0.
        except TypeError:
            value = 0.
        editor.setValue(value)

    def setModelData(self, editor, model, index):
        if index.column() != -1 and index.column() != self.col_idx:
            super().setModelData(editor, model, index)
            return
        editor.interpretText()
        value = '{0:.{1}f}'.format(editor.value(), self.decimals)
        model.setData(index, value, Qt.EditRole)

    def createEditor(self, parent, option, index):
        if index.column() != -1 and index.column() != self.col_idx:
            return super().createEditor(parent, option, index)
        editor = QDoubleSpinBox(parent)
        editor.setFrame(False)
        editor.setMinimum(self.minimum)
        editor.setMaximum(self.maximum)
        editor.setSingleStep(self.step)
        editor.setDecimals(self.decimals)
        return editor


class CRSDelegate(RichTextDelegate):

    def __init__(self, parent=None, col_idx=-1):
        super().__init__(parent)
        self.col_idx = col_idx

    def createEditor(self, parent, option, index):
        if index.column() != -1 and index.column() != self.col_idx:
            return super().createEditor(parent, option, index)
        editor = QgsProjectionSelectionWidget(parent)
        editor.crsChanged.connect(lambda: self.commitData.emit(editor))
        return editor

    def setEditorData(self, editor, index):
        if index.column() != -1 and index.column() != self.col_idx:
            super().setEditorData(editor, index)
            return
        txt = index.model().data(index, Qt.EditRole)
        if ' - ' in txt:
            authid, desc = txt.split(' - ')
            crs = QgsCoordinateReferenceSystem(authid)
            editor.setCrs(crs)

    def setModelData(self, editor, model, index):
        if index.column() != -1 and index.column() != self.col_idx:
            super().setModelData(editor, model, index)
            return
        crs = editor.crs()
        txt = f'{crs.authid()} - {crs.description()}'
        model.setData(index, txt, Qt.EditRole)

    def updateEditorGeometry(self, editor, option, index):
        super().updateEditorGeometry(editor, option, index)
        editor.setGeometry(option.rect)

    def paint(self, painter, styleOption, index):
        if index.column() != -1 and index.column() != self.col_idx:
            super().paint(painter, styleOption, index)
            return
        QStyledItemDelegate.paint(self, painter, styleOption, index)
        oldState = self.parent().blockSignals(True)
        editor = self.createEditor(self.parent(), None, index)
        self.setEditorData(editor, index)
        self.setModelData(editor, index.model(), index)
        self.parent().blockSignals(oldState)
