# -*- coding: utf-8 -*-

# Crayfish - A collection of tools for TUFLOW and other hydraulic modelling packages
# Copyright (C) 2016 Lutra Consulting

# info at lutraconsulting dot co dot uk
# Lutra Consulting
# 23 Chestnut Close
# Burgess Hill
# West Sussex
# RH15 8HN

# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

import sip
sip.setapi('QVariant', 2)
import copy

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5 import QtGui
from qgis.core import *
from PyQt5.QtWidgets import *

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


class DataSetTreeNode(object):
    """
    types: int -> 1: Scalar
                  2: Vector
                  3: Blank / parent node
                  4: point time series
                  5: line time series
                  6: region time series
                  7: line long plot
                  8: 1D cross section plot
    
    """
    
    def __init__(self, ds_index, ds_name, ds_type, max, min, parentItem):
        self.ds_index = ds_index
        self.ds_name = ds_name
        self.ds_type = ds_type  # see above multi line comment
        self.hasMax = max
        self.hasMin = min
        self.hasFlowRegime = False
        if ds_type == 4 or ds_type == 5:
            if 'flow regime' in ds_name.lower():
                pass
            elif 'flow' in ds_name.lower():
                self.hasFlowRegime = True
            elif 'velocity' in ds_name.lower():
                self.hasFlowRegime = True
            elif 'level' in ds_name.lower():
                self.hasFlowRegime = True
            elif 'energy' in ds_name.lower():
                self.hasFlowRegime = True
        self.isMax = False
        self.isMin = False
        self.isFlowRegime = False
        self.parentItem = parentItem
        self.childItems = []
        self.secondaryActive = False
        self.enabled = True

    def appendChild(self, item):  self.childItems.append(item)
    def child(self, row):         return self.childItems[row]
    def children(self ):          return self.childItems
    def childCount(self):         return len(self.childItems)
    def columnCount(self):        return 1
    def parent(self):             return self.parentItem
    def row(self):  return self.parentItem.childItems.index(self) if self.parentItem else 0
    def toggleSecondaryActive(self): self.secondaryActive = True if not self.secondaryActive else False
    def toggleMaxActive(self): self.isMax = True if not self.isMax else False
    def toggleMinActive(self): self.isMin = True if not self.isMin else False
    def toggleFlowRegime(self): self.isFlowRegime = True if not self.isFlowRegime else False


class DataSetModel(QAbstractItemModel):
    def __init__(self, meshDatasets, timeSeriesDatasets, ds_user_names=None, parent=None, **kwargs) :
        QAbstractItemModel.__init__(self, parent)
        self.rootItem = DataSetTreeNode(None, None, None, None, None, None)
        #self.setMesh(datasets)
        self.ds_user_names = ds_user_names if ds_user_names is not None else {} # key = ds_index,  value = user_name
        self.mapOutputsItem = DataSetTreeNode(0, 'Map Outputs', 3, False, False, self.rootItem)
        self.rootItem.appendChild(self.mapOutputsItem)
        self.timeSeriesItem = DataSetTreeNode(0, 'Time Series', 3, False, False, self.rootItem)
        self.rootItem.appendChild(self.timeSeriesItem)
		
        self.setMesh(meshDatasets)
        self.setTimeSeries(timeSeriesDatasets)

    def setMesh(self, datasets):
        self.c_active = None
        self.v_active = None
        self.ts_active = None
        self.secondary_active = []
        self.name2item = {}
        self.dsindex2item = {}
        
        for i, dataset in enumerate(datasets):
            if len(dataset) == 4:
                ds_name, ds_type, max, min = dataset
            else:
                ds_name, ds_type, max = dataset
                min = False
            item = DataSetTreeNode(i, ds_name, ds_type, max, min, self.mapOutputsItem)
            self.mapOutputsItem.appendChild(item)
            self.dsindex2item[i] = item
            self.name2item[ds_name] = item
		
        #for i,d in enumerate(datasets):
        #    ds_name, ds_type = d
        #    lst = ds_name.split('/')
        #    if len(lst) == 1:  # top-level item
        #      item = DataSetTreeNode(i, ds_name, ds_type, self.rootItem)
        #      self.rootItem.appendChild(item)
        #      self.name2item[ds_name] = item
        #      self.dsindex2item[i] = item
        #    else:
        #    #elif len(lst) == 2: # child item
        #      ds_parent_name, ds_name = lst
        #      itemParent = DataSetTreeNode(i, ds_parent_name, ds_type, self.rootItem)
        #      self.rootItem.appendChild(itemParent)
        #      #self.name2item[ds_parent_name] = item
        #      #if ds_parent_name in self.name2item:
        #      #itemParentDs = self.name2item[ds_parent_name]
        #      itemChild = DataSetTreeNode(i, ds_name, ds_type, itemParent)
        #      itemParent.appendChild(itemChild)
        #      #self.dsindex2item[i] = item
        #      #else:
        #      #  print("ignoring invalid child dataset")
        #      self.name2item[ds_parent_name] = itemParent
        #      self.dsindex2item[i] = itemChild
        #    #else:
        #    #	  print("ignoring too deep child dataset")
		
    def setTimeSeries(self, datasets):
        self.dsindex2item_ts = {}
        self.name2item_ts = {}
        
        for i, dataset in enumerate(datasets):
            if len(dataset) == 4:
                ds_name, ds_type, max, min = dataset
            else:
                ds_name, ds_type, max = dataset
                min = False
            item = DataSetTreeNode(i, ds_name, ds_type, max, min, self.timeSeriesItem)
            self.timeSeriesItem.appendChild(item)
            self.dsindex2item_ts[i] = item
            self.name2item_ts[ds_name] = item
            

    def setEnabled(self, *args):
        """
        Sets which time series type is enabled. Map outputs are always enabled.
        
        :param args: list -> int -> 4: enable point result types
                                    5: enabled line result types
                                    6: enable region result types
        :return: void
        """
        
        for item in self.timeSeriesItem.children():
            if item.ds_type in args:
                item.enabled = True
            else:
                item.enabled = False
    
    def activeContourIndex(self):
        return self.c_active.ds_index if self.c_active is not None else -1

    def setActiveContourIndex(self, index):
        self.setActive("contour", index)

    def activeVectorIndex(self):
        return self.v_active.ds_index if self.v_active is not None else -1

    def setActiveVectorIndex(self, index):
        self.setActive("vector", index)
        
    def setActiveSecondaryIndex(self, parent, index):
        self.setActive("secondary axis", parent, index)

    def setActive(self, name, parent, index):
        if parent == self.mapOutputsItem:
            item = self.dsindex2item[index] if index in self.dsindex2item else None
            ind = self.item2index(item)
        elif parent == self.timeSeriesItem:
            item = self.dsindex2item_ts[index] if index in self.dsindex2item_ts else None
            ind = self.item2index(item)
        else:
            item = None
            
        #old_idx = None
        #if name == "vector":
        #    old_idx = self.item2index(self.v_active)
        #    self.v_active = item
        #elif name == "contour":
        #    old_idx = self.item2index(self.c_active)
        #    self.c_active = item

        #if old_idx is not None:
        #    self.dataChanged.emit(old_idx,old_idx)
        #new_idx = self.item2index(item)
        #if new_idx is not None:
        if item is not None:
            self.dataChanged.emit(ind,ind)
            if name == 'secondary axis':
                item.toggleSecondaryActive()
            elif name == 'max':
                item.toggleMaxActive()
                if item.isMin:
                    item.toggleMinActive()
            elif name == 'min':
                item.toggleMinActive()
                if item.isMax:
                    item.toggleMaxActive()
    
    def setActiveMax(self, parent, index):
        self.setActive('max', parent, index)

    def setActiveMin(self, parent, index):
        self.setActive('min', parent, index)
    
    def isActive(self, index):
        item = index.internalPointer()
        if item is not None:
            if item in self.secondary_active:
                return True
            else:
                return False

    def item2index(self, item):
        if item is None:
            return None
        elif item.parentItem is None:
            return QModelIndex()
        else:
            return self.index(item.row(), 0, self.item2index(item.parentItem))

    def index2item(self, index):
        if index is None or not index.isValid():
          return self.rootItem
        else:
          return index.internalPointer()

    def datasetIndex2item(self, ds_index):
        return self.dsindex2item[ds_index] if ds_index in self.dsindex2item else None

    def rowCount(self, parent=None):
        if parent and parent.column() > 0:
          return 0
        return self.index2item(parent).childCount()

    def columnCount(self, parent=None):
        return 1

    def data(self, index, role):
        
        if not index.isValid():
            return

        item = index.internalPointer()
        if role == Qt.DisplayRole or role == Qt.EditRole:
            # user may have renamed the dataset
            if item.ds_index in self.ds_user_names:
                return self.ds_user_names[item.ds_index]
            return item.ds_name
        if role == Qt.UserRole:
            return item.ds_type
        if role == Qt.UserRole+1:
            return item == self.c_active
        if role == Qt.UserRole+2:
            return item == self.v_active
        if role == Qt.UserRole + 3:
            if not item.enabled:
                return False
            if item.secondaryActive:
                return True
            else:
                return False
        if role == Qt.UserRole+4:
            if item.enabled:
                return True
            else:
                return False
        if role == Qt.UserRole+7:
            if item.enabled:
                return True
            else:
                return False
        if role == Qt.UserRole + 8:
            return item.enabled

    def index(self, row, column, parent=None):
        if parent is None: parent = QModelIndex()
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        if not parent.isValid():
            parentItem = self.rootItem
        else:
            parentItem = parent.internalPointer()

        childItem = parentItem.child(row)
        if childItem:
            return self.createIndex(row, column, childItem)
        else:
            return QModelIndex()

    def parent(self, index):
        if not index.isValid():
            return QModelIndex()

        childItem = index.internalPointer()
        if not childItem:
            return QModelIndex()

        parentItem = childItem.parent()

        if parentItem == self.rootItem:
            return QModelIndex()

        return self.createIndex(parentItem.row(), 0, parentItem)

    def flags(self, index):
        item = index.internalPointer()
        if item.parentItem == self.rootItem:
            return Qt.ItemIsEnabled
        elif item.ds_name == 'None':
            return Qt.NoItemFlags
        elif not item.enabled:
            return Qt.NoItemFlags
        else:
            return Qt.ItemIsEnabled | Qt.ItemIsSelectable #| Qt.ItemIsEditable

    def setData(self, index, value, role):
        """ allows renaming of datasets """

        if not index.isValid():
            return False

        item = index.internalPointer()
        self.ds_user_names[item.ds_index] = value
        self.dataChanged.emit(index, index)
        return True


POS_V, POS_C, POS_2, POS_TS, POS_LP, POS_MAX, POS_MIN = 1, 1, 1, 1, 1, 2, 3   # identifiers of positions of icons in the delegate

class DataSetItemDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        QStyledItemDelegate.__init__(self, parent)
        dir = os.path.dirname(__file__)
        transformer = QTransform()
        transformer.rotate(180)
        self.pix_c  = QPixmap(os.path.join(dir, "icons", "icon_contours.png"))
        self.pix_c0 = QIcon(self.pix_c).pixmap(self.pix_c.width(),self.pix_c.height(), QIcon.Disabled)
        self.pix_v = QPixmap(os.path.join(dir, "icons", "icon_vectors.png"))
        self.pix_v0 = QPixmap(os.path.join(dir, "icons", "icon_vectors_disabled.png"))
        self.pix_2nd = QPixmap(os.path.join(dir, "icons", "2nd_axis_2.png"))
        self.pix_2nd0 = QPixmap(os.path.join(dir, "icons", "2nd_axis_20.png"))
        #self.pix_2nd0 = QIcon(self.pix_2nd).pixmap(self.pix_2nd.width(), self.pix_2nd.height(), QIcon.Disabled)
        #self.pix_2nd0 = QPixmap(os.path.dirname(__file__) + "\\icons\\2nd_axis_disabled.ico")
        self.pix_ts = QPixmap(os.path.join(dir, "icons", "results.png"))
        self.pix_ts0 = QIcon(self.pix_ts).pixmap(self.pix_ts.width(), self.pix_ts.height(), QIcon.Disabled)
        self.pix_lp = QPixmap(os.path.join(dir, "icons", "results_lp.png"))
        self.pix_lp0 = QIcon(self.pix_lp).pixmap(self.pix_lp.width(), self.pix_lp.height(), QIcon.Disabled)
        self.pix_max =  QPixmap(os.path.join(dir, "icons", "max.png"))
        self.pix_max0 = QPixmap(os.path.join(dir, "icons", "max_inactive.png"))
        self.pix_min = QPixmap(os.path.join(dir, "icons", "max.png")).transformed(transformer)
        self.pix_min0 = QPixmap(os.path.join(dir, "icons", "max_inactive.png")).transformed(transformer)
        self.pix_cs = QPixmap(os.path.join(dir, "icons", "CrossSection_2.png"))
        self.pix_cs0 = QIcon(self.pix_cs).pixmap(self.pix_cs.width(), self.pix_cs.height(), QIcon.Disabled)
        #self.pix_max0 = QIcon(self.pix_max).pixmap(self.pix_max.width(), self.pix_max.height(), QIcon.Disabled)
        #self.pix_v0 = QIcon(self.pix_v).pixmap(self.pix_v.width(),self.pix_v.height(), QIcon.Disabled)

    def paint(self, painter, option, index):

        QStyledItemDelegate.paint(self, painter, option, index)
    
        if index.data(Qt.UserRole) == 3:
            return

        elif index.data(Qt.UserRole) == 2:  # also Vector
            av = index.data(Qt.UserRole+2)
            painter.drawPixmap(self.iconRect(option.rect, option.rect.left(), POS_V), self.pix_v)
    
        elif index.data(Qt.UserRole) == 1:
            ac = index.data(Qt.UserRole+1)
            painter.drawPixmap(self.iconRect(option.rect, option.rect.left(), POS_C), self.pix_c)
    
        elif index.data(Qt.UserRole) == 4 or index.data(Qt.UserRole) == 5 or index.data(Qt.UserRole) == 6:
            enabled = index.data(Qt.UserRole + 4)
            painter.drawPixmap(self.iconRect(option.rect, option.rect.left(), POS_TS), self.pix_ts if enabled else self.pix_ts0)

        elif index.data(Qt.UserRole) == 7:
            enabled = index.data(Qt.UserRole + 7)
            painter.drawPixmap(self.iconRect(option.rect, option.rect.left(), POS_LP),
                               self.pix_lp if enabled else self.pix_lp0)

        elif index.data(Qt.UserRole) == 8:
            enabled = index.data(Qt.UserRole + 8)
            painter.drawPixmap(self.iconRect(option.rect, option.rect.left(), POS_C), self.pix_cs if enabled else self.pix_cs0)
	
        secondaryAxis = index.data(Qt.UserRole + 3)
        painter.drawPixmap(self.iconRect(option.rect, option.rect.right(), POS_2), self.pix_2nd if secondaryAxis else self.pix_2nd0)
    
        item = index.internalPointer()
        if item.hasMax:
            if item.enabled and item.isMax:
                painter.drawPixmap(self.iconRect(option.rect, option.rect.right(), POS_MAX), self.pix_max)
            else:
                painter.drawPixmap(self.iconRect(option.rect, option.rect.right(), POS_MAX), self.pix_max0)
        if item.hasMin:
            if item.enabled and item.isMin:
                painter.drawPixmap(self.iconRect(option.rect, option.rect.right(), POS_MIN), self.pix_min)
            else:
                painter.drawPixmap(self.iconRect(option.rect, option.rect.right(), POS_MIN), self.pix_min0)

    def iconRect(self, rect, pos, i):
        """ icon rect for given item rect. i is either POS_C or POS_V """
        iw, ih =  self.pix_c.width(), self.pix_c.height()
        #margin = (rect.height()-ih)/2
        margin = 0
        return QRect(pos - i*(iw + margin), rect.top() + margin, iw, ih)

    def sizeHint(self, option, index):
        hint = QStyledItemDelegate.sizeHint(self, option, index)
        if hint.height() < 16:
            hint.setHeight(16)
        return hint


class DataSetView(QTreeView):

    contourClicked = pyqtSignal(int)
    vectorClicked = pyqtSignal(int)
    secondAxisClicked = pyqtSignal(dict)
    maxClicked = pyqtSignal(dict)
    minClicked = pyqtSignal(dict)
    rightClicked = pyqtSignal(dict)
    doubleClicked = pyqtSignal(dict)
    leftClicked = pyqtSignal(dict)
    
    activeScalarName = None
    activeScalarIdx = None
    activeVectorName = None
    activeVectorIdx = None

    def __init__(self, parent=None):
        QTreeView.__init__(self, parent)

        self.setItemDelegate(DataSetItemDelegate())
        #self.setRootIsDecorated(False)
        self.setHeaderHidden(True)

        self.customActions = []

    def setCustomActions(self, actions):
        self.customActions = actions
        
    #def mouseDoubleClickEvent(self, event):
    #
    #    idx = self.indexAt(event.pos())
    #    if idx.isValid():
    #        vr = self.visualRect(idx)
    #        if self.itemDelegate().iconRect(vr, vr.right(), POS_2).contains(event.pos()):
    #            return
    #        elif self.itemDelegate().iconRect(vr, vr.right(), POS_MAX).contains(event.pos()):
    #            return
    #        else:
    #            self.doubleClicked.emit({'parent': self.model().index2item(idx).parentItem, 'item': self.model().index2item(idx)})
    #    else:
    #        return
    
    def mouseMoveEvent(self, event):
        """Empty implementation to stop drag-selection"""
        pass
        
    def mousePressEvent(self, event):

        processed = False
        idx = self.indexAt(event.pos())
        if idx.isValid():
            vr = self.visualRect(idx)
            if self.itemDelegate().iconRect(vr, vr.right(), POS_2).contains(event.pos()):
                # if idx.data(Qt.UserRole) == 2: # has vector data?
                if self.model().index2item(idx).enabled:
                    self.secondAxisClicked.emit({'parent': self.model().index2item(idx).parentItem,
                                                 'index': self.model().index2item(idx).ds_index})
                    # self.secondAxisClicked.emit(1)
                    processed = True
    
            if self.itemDelegate().iconRect(vr, vr.right(), POS_MAX).contains(event.pos()):
                if self.model().index2item(idx).enabled:
                    if self.model().index2item(idx).hasMax:
                        self.maxClicked.emit({'parent': self.model().index2item(idx).parentItem,
                                              'index': self.model().index2item(idx).ds_index})
                        processed = True

            if self.itemDelegate().iconRect(vr, vr.right(), POS_MIN).contains(event.pos()):
                if self.model().index2item(idx).enabled:
                    if self.model().index2item(idx).hasMin:
                        self.minClicked.emit({'parent': self.model().index2item(idx).parentItem,
                                              'index': self.model().index2item(idx).ds_index})
                        processed = True
        
        # only if the user did not click one of the icons do usual handling
        if not processed:
            QTreeView.mousePressEvent(self, event)
            if event.button() == Qt.LeftButton:
                if idx.isValid():
                    index = self.model().index2item(idx)
                    if index.ds_type == 1:  # scalar
                        if index.ds_name != self.activeScalarName:
                            if self.activeScalarIdx in self.selectionModel().selectedIndexes():
                                self.selectionModel().select(self.activeScalarIdx, QItemSelectionModel.Deselect)
                            self.activeScalarIdx = idx
                            self.activeScalarName = index.ds_name
                        else:
                            self.activeScalarIdx = None
                            self.activeScalarName = None
                    elif index.ds_type == 2:  # vector
                        if index.ds_name != self.activeVectorName:
                            if self.activeVectorIdx in self.selectionModel().selectedIndexes():
                                self.selectionModel().select(self.activeVectorIdx, QItemSelectionModel.Deselect)
                            self.activeVectorIdx = idx
                            self.activeVectorName = index.ds_name
                        else:
                            self.activeVectorIdx = None
                            self.activeVectorName = None
                
                
                self.leftClicked.emit({'modelIndex': idx, 'button': event.button(), 'drag_event': False})

    #def mousePressEvent(self, event):
    #    event2 = QMouseEvent(event)
    #
    #    self.pressEvent = QMouseEvent(event)
    #    self.timer = QTimer()
    #    self.timer.setInterval(200)
    #    self.timer.setSingleShot(True)
    #    self.timer.timeout.connect(lambda: self.delayedMouseEvent(event2))
    #    self.timer.start()

    def contextMenuEvent(self, event):
        #processed = False
        QTreeView.contextMenuEvent(self, event)
        idx = self.indexAt(event.pos())
        if not idx.isValid():
            idx = None
        self.rightClicked.emit({'pos': event.pos(), 'index': idx})
        
        #if len(self.customActions) == 0:
        #    return
        #event.accept()
        #m = QMenu()
        #for a in self.customActions:
        #    m.addAction(a)
        #m.exec_(self.mapToGlobal(event.pos()))
        
    def viewportEvent(self, event):
        if event.type() == QEvent.ToolTip:
            idx = self.indexAt(event.pos())
            if idx.isValid():
                vr = self.visualRect(idx)
                if self.itemDelegate().iconRect(vr, vr.right(), POS_2).contains(event.pos()):
                    # if idx.data(Qt.UserRole) == 2: # has vector data?
                    if self.model().index2item(idx).enabled:
                        if self.model().index2item(idx).parentItem != self.model().rootItem:
                            if self.model().index2item(idx).ds_name != 'None':
                                QToolTip.showText(event.globalPos(), 'Secondary Axis', self, self.itemDelegate().iconRect(vr, vr.right(), POS_MAX))
                    # self.secondAxisClicked.emit(1)
                    processed = True
        
                if self.itemDelegate().iconRect(vr, vr.right(), POS_MAX).contains(event.pos()):
                    if self.model().index2item(idx).enabled:
                        if self.model().index2item(idx).hasMax:
                            QToolTip.showText(event.globalPos(), 'Maximum', self, self.itemDelegate().iconRect(vr, vr.right(), POS_MAX))
        else:
            QTreeView.viewportEvent(self, event)
        
        return event.type()

def test_main():
    datasets = [("Bed Elevation", 0), ("Depth", 1), ("Depth/Max", 1), ("Velocity", 2), ("Unit Flow", 2)]
    v = DataSetView()
    v.setModel(DataSetModel(datasets))
    btn = QToolButton()
    btn.setCheckable(True)
    btn.setChecked(True)
    w = QWidget()
    l = QVBoxLayout()
    l.addWidget(btn)
    l.addWidget(v)
    w.setLayout(l)
    w.show()
    v.setCurrentIndex(v.model().index(0,0))
    return w

if __name__ == '__main__':
    a = QApplication([])
    w = test_main()
    a.exec_()
    del w
