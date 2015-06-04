#!/usr/bin/python

############################################################################
#
# splitMI - A simple program to convert MapInfo MID/MIF files into one
# or more shapefiles for each type of object in the MID/MIF. The
# TUFLOW file naming convention of _P, _L and _R for points, lines and
# regions is used.
#
############################################################################
#
# Usage: splitMI <name_of_mif_file_without_extension>
#
############################################################################
#
# Copyright (C) Edenvale Young Associates Ltd. 2013
# Modified by Phillip Ryan, to tie in with TUFLOW QGIS plugin
#
############################################################################
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
############################################################################

import os
import osgeo.osr as osr
import osgeo.ogr as ogr
import string
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *

def split_MI_util(iface, mif_layer, outfolder, prefix):
	# returns message, point shapefile, line shapefile, region shapefile, npts, nlines, nregions
	#QMessageBox.information( iface.mainWindow(),"debug", "into split_MI_util")
	fname_P = None
	fname_L = None
	fname_R = None
	message = None
	npts = 0
	nln = 0
	nrg = 0
	mif = ogr.Open(mif_layer)
	if mif is None:
		message = "Could not open input MIF file: "+mif_layer
		return message, fname_P, fname_L, fname_R, npts, nln, nrg

	miflyr = mif.GetLayer(0)
	spatialReference = miflyr.GetSpatialRef()
	miflyrname = miflyr.GetName()

	driverName = "ESRI Shapefile"
	drv = ogr.GetDriverByName( driverName )
	if drv is None:
		message  = "%s driver not available.\n" % driverName
		return message, fname_P, fname_L, fname_R, npts, nln, nrg

	# Filter into Points
	miflyr.SetAttributeFilter("OGR_GEOMETRY='POINT'")
	npts = miflyr.GetFeatureCount()
	#QMessageBox.information( iface.mainWindow(),"debug", "npts = "+str(npts))
	if npts > 0:
		fname_P = outfolder+"\\"+prefix+"_tmp_P.shp"
		#QMessageBox.information( iface.mainWindow(),"debug", "output name"+fname_P)
		flyr_P = str(prefix)+"_P"
		savename = outfolder+"\\"+flyr_P+".shp"
		odp = drv.CreateDataSource(fname_P)
		#QMessageBox.information( iface.mainWindow(),"debug", "flyr_P = "+str(type(flyr_P)))
		#QMessageBox.information( iface.mainWindow(),"debug", "spatialReference = "+str(type(spatialReference)))
		#QMessageBox.information( iface.mainWindow(),"debug", "ogr.wkbPoint = "+str(type(ogr.wkbPoint)))
		layer = odp.CreateLayer(flyr_P, spatialReference, int(ogr.wkbPoint))
		layerDefinition = layer.GetLayerDefn()
		if odp is None:
			message = "Could not create output file: "+fname_P
			return message, fname_P, fname_L, fname_R, npts, nln, nrg
		try:
			odp.CopyLayer( miflyr, flyr_P)
			odp.Destroy() #flush
			QMessageBox.information( iface.mainWindow(),"debug", "adding layer: "+savename)
			iface.addVectorLayer(savename, flyr_P, "ogr")
		except:
			QMessageBox.information( iface.mainWindow(),"debug", "herea")
			message = "Error copying points into shapefile."
			return message, fname_P, fname_L, fname_R, npts, nln, nrg
	
	# Filter into Lines
	miflyr.SetAttributeFilter("OGR_GEOMETRY='LINESTRING'")
	nln = miflyr.GetFeatureCount()
	if nln > 0:
		fname_L = os.path.join(outfolder, (prefix+"_tmp_L.shp"))
		#flyr_L = os.path.join(outfolder, (prefix+"_L"))
		flyr_L = str(prefix)+"_L"
		savename = outfolder+"\\"+flyr_L+".shp"
		odp = drv.CreateDataSource(fname_L)
		layer = odp.CreateLayer(flyr_L, spatialReference, int(ogr.wkbLineString))
		layerDefinition = layer.GetLayerDefn()
		if odp is None:
			message = "Could not create output file: "+fname_L
			return message, fname_P, fname_L, fname_R, npts, nln, nrg
		try:
			odp.CopyLayer( miflyr, flyr_L)
			odp.Destroy() #flush
			QMessageBox.information( iface.mainWindow(),"debug", "adding layer: "+savename)
			iface.addVectorLayer(savename, flyr_L, "ogr")
		except:
			message = "Error copying lines into shapefile: "+flyr_L
			return message, fname_P, fname_L, fname_R, npts, nln, nrg


	# Filter into regions
	miflyr.SetAttributeFilter("OGR_GEOMETRY='POLYGON'")
	nrg = miflyr.GetFeatureCount()
	if nrg > 0:
		fname_R = os.path.join(outfolder, (prefix+"_tmp_R.shp"))
		#flyr_R = os.path.join(outfolder, (prefix+"_R"))
		flyr_R = str(prefix)+"_R"
		savename = outfolder+"\\"+flyr_R+".shp"
		odp = drv.CreateDataSource(fname_R)
		layer = odp.CreateLayer(flyr_R, spatialReference, int(ogr.wkbPolygon))
		layerDefinition = layer.GetLayerDefn()
		if odp is None:
			message = "Could not create output file: "+fname_R
			return message, fname_P, fname_L, fname_R, npts, nln, nrg
		try:
			odp.CopyLayer( miflyr, flyr_R)
			QMessageBox.information( iface.mainWindow(),"debug", "adding layer: "+savename)
			iface.addVectorLayer(savename, flyr_R, "ogr")
		except:
			message = "Error copying regions into shapefile."
			return message, fname_P, fname_L, fname_R, npts, nln, nrg

	return message, fname_P, fname_L, fname_R, npts, nln, nrg