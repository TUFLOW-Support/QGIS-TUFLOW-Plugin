# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_tuflowqgis_1d_xs.ui'
#
# Created: Mon Oct 28 08:41:38 2013
#      by: PyQt4 UI code generator 4.10.3
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class Ui_tuflowqgis_1d_xs(object):
    def setupUi(self, tuflowqgis_1d_xs):
        tuflowqgis_1d_xs.setObjectName(_fromUtf8("tuflowqgis_1d_xs"))
        tuflowqgis_1d_xs.resize(701, 424)
        self.dockWidgetContents = QtGui.QWidget()
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.dockWidgetContents.sizePolicy().hasHeightForWidth())
        self.dockWidgetContents.setSizePolicy(sizePolicy)
        self.dockWidgetContents.setObjectName(_fromUtf8("dockWidgetContents"))
        self.verticalLayout_3 = QtGui.QVBoxLayout(self.dockWidgetContents)
        self.verticalLayout_3.setObjectName(_fromUtf8("verticalLayout_3"))
        self.tabWidget = QtGui.QTabWidget(self.dockWidgetContents)
        self.tabWidget.setAutoFillBackground(True)
        self.tabWidget.setTabPosition(QtGui.QTabWidget.North)
        self.tabWidget.setTabShape(QtGui.QTabWidget.Rounded)
        self.tabWidget.setElideMode(QtCore.Qt.ElideNone)
        self.tabWidget.setUsesScrollButtons(True)
        self.tabWidget.setObjectName(_fromUtf8("tabWidget"))
        self.tab_1 = QtGui.QWidget()
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.tab_1.sizePolicy().hasHeightForWidth())
        self.tab_1.setSizePolicy(sizePolicy)
        self.tab_1.setObjectName(_fromUtf8("tab_1"))
        self.gridlayout = QtGui.QGridLayout(self.tab_1)
        self.gridlayout.setObjectName(_fromUtf8("gridlayout"))
        self._2 = QtGui.QHBoxLayout()
        self._2.setObjectName(_fromUtf8("_2"))
        self.gridLayout = QtGui.QGridLayout()
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.frame_for_plot = QtGui.QFrame(self.tab_1)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.frame_for_plot.sizePolicy().hasHeightForWidth())
        self.frame_for_plot.setSizePolicy(sizePolicy)
        self.frame_for_plot.setFrameShape(QtGui.QFrame.StyledPanel)
        self.frame_for_plot.setFrameShadow(QtGui.QFrame.Raised)
        self.frame_for_plot.setObjectName(_fromUtf8("frame_for_plot"))
        self.verticalLayout_9 = QtGui.QVBoxLayout(self.frame_for_plot)
        self.verticalLayout_9.setObjectName(_fromUtf8("verticalLayout_9"))
        self.gridLayout.addWidget(self.frame_for_plot, 0, 0, 1, 1)
        self._2.addLayout(self.gridLayout)
        self.verticalLayout = QtGui.QVBoxLayout()
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.label = QtGui.QLabel(self.tab_1)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label.sizePolicy().hasHeightForWidth())
        self.label.setSizePolicy(sizePolicy)
        self.label.setObjectName(_fromUtf8("label"))
        self.verticalLayout.addWidget(self.label)
        self.lvXSID = QtGui.QListWidget(self.tab_1)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.lvXSID.sizePolicy().hasHeightForWidth())
        self.lvXSID.setSizePolicy(sizePolicy)
        self.lvXSID.setMinimumSize(QtCore.QSize(10, 10))
        self.lvXSID.setMaximumSize(QtCore.QSize(300, 16777215))
        self.lvXSID.setObjectName(_fromUtf8("lvXSID"))
        self.verticalLayout.addWidget(self.lvXSID)
        self.cbRoughness = QtGui.QCheckBox(self.tab_1)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.cbRoughness.sizePolicy().hasHeightForWidth())
        self.cbRoughness.setSizePolicy(sizePolicy)
        self.cbRoughness.setObjectName(_fromUtf8("cbRoughness"))
        self.verticalLayout.addWidget(self.cbRoughness)
        self.pbClearSelection = QtGui.QPushButton(self.tab_1)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pbClearSelection.sizePolicy().hasHeightForWidth())
        self.pbClearSelection.setSizePolicy(sizePolicy)
        self.pbClearSelection.setMinimumSize(QtCore.QSize(10, 20))
        self.pbClearSelection.setObjectName(_fromUtf8("pbClearSelection"))
        self.verticalLayout.addWidget(self.pbClearSelection)
        self.pbLoadAll = QtGui.QPushButton(self.tab_1)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pbLoadAll.sizePolicy().hasHeightForWidth())
        self.pbLoadAll.setSizePolicy(sizePolicy)
        self.pbLoadAll.setMinimumSize(QtCore.QSize(10, 20))
        self.pbLoadAll.setAutoRepeat(False)
        self.pbLoadAll.setAutoDefault(False)
        self.pbLoadAll.setDefault(False)
        self.pbLoadAll.setFlat(False)
        self.pbLoadAll.setObjectName(_fromUtf8("pbLoadAll"))
        self.verticalLayout.addWidget(self.pbLoadAll)
        self._2.addLayout(self.verticalLayout)
        self.gridlayout.addLayout(self._2, 1, 0, 1, 1)
        self.cbShowLegend = QtGui.QCheckBox(self.tab_1)
        self.cbShowLegend.setObjectName(_fromUtf8("cbShowLegend"))
        self.gridlayout.addWidget(self.cbShowLegend, 0, 0, 1, 1)
        self.tabWidget.addTab(self.tab_1, _fromUtf8(""))
        self.verticalLayout_3.addWidget(self.tabWidget)
        tuflowqgis_1d_xs.setWidget(self.dockWidgetContents)

        self.retranslateUi(tuflowqgis_1d_xs)
        self.tabWidget.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(tuflowqgis_1d_xs)

    def retranslateUi(self, tuflowqgis_1d_xs):
        tuflowqgis_1d_xs.setWindowTitle(_translate("tuflowqgis_1d_xs", "TUFLOW 1D Section Viewer", None))
        self.label.setText(_translate("tuflowqgis_1d_xs", "Cross Sections Selected", None))
        self.cbRoughness.setText(_translate("tuflowqgis_1d_xs", "Display Roughness", None))
        self.pbClearSelection.setText(_translate("tuflowqgis_1d_xs", "Clear Selection", None))
        self.pbLoadAll.setText(_translate("tuflowqgis_1d_xs", "Load All", None))
        self.cbShowLegend.setText(_translate("tuflowqgis_1d_xs", "Show Legend", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_1), _translate("tuflowqgis_1d_xs", "&Graph", None))

