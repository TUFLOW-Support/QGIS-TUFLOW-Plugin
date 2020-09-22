# -*- coding: utf-8 -*-
"""
/***************************************************************************
 tuflowqgis_menu
                                 A QGIS plugin
 Initialises the TUFLOW menu system
                             -------------------
        begin                : 2013-08-27
        copyright            : (C) 2013 by Phillip Ryan
        email                : support@tuflow.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""
from qgis.core import *
import sys


def name():
    return "TUFLOW"


def description():
    return "A collection of the QGIS plugins for TUFLOW modelling."


def version():
    return "Version 2018-02-AB"


def icon():
    return "tuflow.png"


def qgisMinimumVersion():
    return "3.4"

def author():
    return "Phillip Ryan, Ellis Symons"

def email():
    return "support@tuflow.com"

def openTuview(event, tuflowqgis):
    if Qgis.QGIS_VERSION_INT >= 30400:
        tuviewOpen = QgsProject().instance().readEntry("TUVIEW", "dock_opened")[0]
        if tuviewOpen == 'Open':
            tuflowqgis.openResultsPlottingWindow(showmessage=False)
            tuflowqgis.resultsPlottingDock.loadProject()
            tuflowqgis.resultsPlottingDock.canvas.mapCanvasRefreshed.connect(
                tuflowqgis.resultsPlottingDock.tuResults.tuResults2D.renderMap)
            tuflowqgis.resultsPlottingDock.canvas.mapCanvasRefreshed.connect(
                tuflowqgis.resultsPlottingDock.tuPlot.updateCurrentPlot)
        elif tuviewOpen == 'Close':
            tuflowqgis.openResultsPlottingWindow(showmessage=False)
            tuflowqgis.resultsPlottingDock.setVisible(False)
            tuflowqgis.resultsPlottingDock.loadProject()
            tuflowqgis.resultsPlottingDock.canvas.mapCanvasRefreshed.connect(
                tuflowqgis.resultsPlottingDock.tuResults.tuResults2D.renderMap)
            tuflowqgis.resultsPlottingDock.canvas.mapCanvasRefreshed.connect(
                tuflowqgis.resultsPlottingDock.tuPlot.updateCurrentPlot)

def classFactory(iface):
    # load tuflowqgis_menu class from file tuflowqgis_menu
    from .tuflowqgis_menu import tuflowqgis_menu
    
    menu = tuflowqgis_menu(iface)

    # check if tuview should be opened
    openTuview(None, menu)
    
    # setup signal to capture project opens so tuview can be opened if needed
    conn = QgsProject.instance().readProject.connect(lambda event: openTuview(event, menu))

    menu.addLambdaConnection(conn)
    
    return menu
