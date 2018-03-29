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

from tuflowqgis_menu import tuflowqgis_menu

def name():
    return "TUFLOW"


def description():
    return "A collection of the QGIS plugins for TUFLOW modelling."


def version():
    return "Version 2017-06-AD"


def icon():
    return "icon.png"


def qgisMinimumVersion():
    return "2.0"

def author():
    return "Phillip Ryan"

def email():
    return "support@tuflow.com"

def classFactory(iface):
    # load tuflowqgis_menu class from file tuflowqgis_menu
    return tuflowqgis_menu(iface)
