# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_tuflowqgis_plt_test.ui'
#
# Created: Tue Jan 19 11:20:11 2016
#      by: PyQt4 UI code generator 4.11.1
#
# WARNING! All changes made in this file will be lost!

from qgis.PyQt import QtCore, QtGui
from qgis.PyQt.QtWidgets import *

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QApplication.translate(context, text, disambig)


from ..compatibility_routines import QT_SIZE_POLICY_PREFERRED, QT_FRAME_STYLED_PANEL, QT_SIZE_POLICY_EXPANDING, QT_ELIDE_NONE, QT_SIZE_POLICY_FIXED, QT_FRAME_RAISED, QT_SIZE_POLICY_MINIMUM


class Ui_tuflowqgis_plt_test(object):
    def setupUi(self, tuflowqgis_plt_test):
        tuflowqgis_plt_test.setObjectName(_fromUtf8("tuflowqgis_plt_test"))
        tuflowqgis_plt_test.resize(1032, 606)
        self.dockWidgetContents = QWidget()
        sizePolicy = QSizePolicy(QT_SIZE_POLICY_EXPANDING, QT_SIZE_POLICY_EXPANDING)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.dockWidgetContents.sizePolicy().hasHeightForWidth())
        self.dockWidgetContents.setSizePolicy(sizePolicy)
        self.dockWidgetContents.setObjectName(_fromUtf8("dockWidgetContents"))
        self.verticalLayout_3 = QVBoxLayout(self.dockWidgetContents)
        self.verticalLayout_3.setObjectName(_fromUtf8("verticalLayout_3"))
        self.tabWidget = QTabWidget(self.dockWidgetContents)
        self.tabWidget.setAutoFillBackground(True)
        self.tabWidget.setTabPosition(QTabWidget.North)
        self.tabWidget.setTabShape(QTabWidget.Rounded)
        self.tabWidget.setElideMode(QT_ELIDE_NONE)
        self.tabWidget.setUsesScrollButtons(True)
        self.tabWidget.setObjectName(_fromUtf8("tabWidget"))
        self.tab_1 = QWidget()
        sizePolicy = QSizePolicy(QT_SIZE_POLICY_EXPANDING, QT_SIZE_POLICY_EXPANDING)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.tab_1.sizePolicy().hasHeightForWidth())
        self.tab_1.setSizePolicy(sizePolicy)
        self.tab_1.setObjectName(_fromUtf8("tab_1"))
        self.gridlayout = QGridLayout(self.tab_1)
        self.gridlayout.setObjectName(_fromUtf8("gridlayout"))
        self._2 = QHBoxLayout()
        self._2.setObjectName(_fromUtf8("_2"))
        self.gridLayout = QGridLayout()
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.widget_save_buttons = QWidget(self.tab_1)
        self.widget_save_buttons.setObjectName(_fromUtf8("widget_save_buttons"))
        self.horizontalLayout_3 = QHBoxLayout(self.widget_save_buttons)
        self.horizontalLayout_3.setMargin(0)
        self.horizontalLayout_3.setObjectName(_fromUtf8("horizontalLayout_3"))
        self.stackedWidget = QStackedWidget(self.widget_save_buttons)
        self.stackedWidget.setObjectName(_fromUtf8("stackedWidget"))
        self.page = QWidget()
        self.page.setObjectName(_fromUtf8("page"))
        self.horizontalLayout_4 = QHBoxLayout(self.page)
        self.horizontalLayout_4.setObjectName(_fromUtf8("horizontalLayout_4"))
        self.butSaveAs = QPushButton(self.page)
        self.butSaveAs.setObjectName(_fromUtf8("butSaveAs"))
        self.horizontalLayout_4.addWidget(self.butSaveAs)
        self.cbxSaveAs = QComboBox(self.page)
        self.cbxSaveAs.setObjectName(_fromUtf8("cbxSaveAs"))
        self.cbxSaveAs.addItem(_fromUtf8(""))
        self.cbxSaveAs.addItem(_fromUtf8(""))
        self.cbxSaveAs.addItem(_fromUtf8(""))
        self.cbxSaveAs.addItem(_fromUtf8(""))
        self.horizontalLayout_4.addWidget(self.cbxSaveAs)
        spacerItem = QSpacerItem(0, 20, QT_SIZE_POLICY_EXPANDING, QT_SIZE_POLICY_MINIMUM)
        self.horizontalLayout_4.addItem(spacerItem)
        self.stackedWidget.addWidget(self.page)
        self.horizontalLayout_3.addWidget(self.stackedWidget)
        spacerItem1 = QSpacerItem(1, 20, QT_SIZE_POLICY_EXPANDING, QT_SIZE_POLICY_MINIMUM)
        self.horizontalLayout_3.addItem(spacerItem1)
        self.label = QLabel(self.widget_save_buttons)
        self.label.setObjectName(_fromUtf8("label"))
        self.horizontalLayout_3.addWidget(self.label)
        self.comboBox = QComboBox(self.widget_save_buttons)
        sizePolicy = QSizePolicy(QT_SIZE_POLICY_MINIMUM, QT_SIZE_POLICY_FIXED)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.comboBox.sizePolicy().hasHeightForWidth())
        self.comboBox.setSizePolicy(sizePolicy)
        self.comboBox.setObjectName(_fromUtf8("comboBox"))
        self.comboBox.addItem(_fromUtf8(""))
        self.comboBox.addItem(_fromUtf8(""))
        self.horizontalLayout_3.addWidget(self.comboBox)
        self.gridLayout.addWidget(self.widget_save_buttons, 1, 0, 1, 1)
        self.frame_for_plot = QFrame(self.tab_1)
        sizePolicy = QSizePolicy(QT_SIZE_POLICY_PREFERRED, QT_SIZE_POLICY_PREFERRED)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(self.frame_for_plot.sizePolicy().hasHeightForWidth())
        self.frame_for_plot.setSizePolicy(sizePolicy)
        self.frame_for_plot.setFrameShape(QT_FRAME_STYLED_PANEL)
        self.frame_for_plot.setFrameShadow(QT_FRAME_RAISED)
        self.frame_for_plot.setObjectName(_fromUtf8("frame_for_plot"))
        self.verticalLayout_9 = QVBoxLayout(self.frame_for_plot)
        self.verticalLayout_9.setObjectName(_fromUtf8("verticalLayout_9"))
        self.gridLayout.addWidget(self.frame_for_plot, 0, 0, 1, 1)
        self._2.addLayout(self.gridLayout)
        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.tableView = QTableView(self.tab_1)
        sizePolicy = QSizePolicy(QT_SIZE_POLICY_PREFERRED, QT_SIZE_POLICY_EXPANDING)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.tableView.sizePolicy().hasHeightForWidth())
        self.tableView.setSizePolicy(sizePolicy)
        self.tableView.setMinimumSize(QtCore.QSize(10, 10))
        self.tableView.setObjectName(_fromUtf8("tableView"))
        self.verticalLayout.addWidget(self.tableView)
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.listWidget = QListWidget(self.tab_1)
        self.listWidget.setObjectName(_fromUtf8("listWidget"))
        self.horizontalLayout.addWidget(self.listWidget)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.pushButton = QPushButton(self.tab_1)
        self.pushButton.setMinimumSize(QtCore.QSize(10, 20))
        self.pushButton.setObjectName(_fromUtf8("pushButton"))
        self.verticalLayout.addWidget(self.pushButton)
        self.pushButton_2 = QPushButton(self.tab_1)
        self.pushButton_2.setMinimumSize(QtCore.QSize(10, 20))
        self.pushButton_2.setAutoRepeat(False)
        self.pushButton_2.setAutoDefault(False)
        self.pushButton_2.setDefault(False)
        self.pushButton_2.setFlat(False)
        self.pushButton_2.setObjectName(_fromUtf8("pushButton_2"))
        self.verticalLayout.addWidget(self.pushButton_2)
        self._2.addLayout(self.verticalLayout)
        self.gridlayout.addLayout(self._2, 1, 0, 1, 1)
        self.tabWidget.addTab(self.tab_1, _fromUtf8(""))
        self.verticalLayout_3.addWidget(self.tabWidget)
        tuflowqgis_plt_test.setWidget(self.dockWidgetContents)

        self.retranslateUi(tuflowqgis_plt_test)
        self.tabWidget.setCurrentIndex(0)
        self.stackedWidget.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(tuflowqgis_plt_test)

    def retranslateUi(self, tuflowqgis_plt_test):
        tuflowqgis_plt_test.setWindowTitle(_translate("tuflowqgis_plt_test", "TUFLOW Results Viewer", None))
        self.butSaveAs.setText(_translate("tuflowqgis_plt_test", "Save as", None))
        self.cbxSaveAs.setItemText(0, _translate("tuflowqgis_plt_test", "PDF", None))
        self.cbxSaveAs.setItemText(1, _translate("tuflowqgis_plt_test", "PNG", None))
        self.cbxSaveAs.setItemText(2, _translate("tuflowqgis_plt_test", "SVG", None))
        self.cbxSaveAs.setItemText(3, _translate("tuflowqgis_plt_test", "print (PS)", None))
        self.label.setText(_translate("tuflowqgis_plt_test", "Selection", None))
        self.comboBox.setItemText(0, _translate("tuflowqgis_plt_test", "Temporary polyline", None))
        self.comboBox.setItemText(1, _translate("tuflowqgis_plt_test", "Selected polyline", None))
        self.pushButton.setText(_translate("tuflowqgis_plt_test", "Remove Layer", None))
        self.pushButton_2.setText(_translate("tuflowqgis_plt_test", "Add Layer", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_1), _translate("tuflowqgis_plt_test", "&Graph", None))

