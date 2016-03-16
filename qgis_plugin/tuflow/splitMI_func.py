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
import sys
#sys.path.append(r'C:\Program Files\QGIS Wien\apps\Python27\Lib\site-packages\osgeo')
#sys.path.append(r'C:\Program Files\QGIS Wien\bin')
import ogr
import string

def splitMI_func(mif_file):

	#mifbase = sys.argv[1]
	#mif_file = r'D:\TUFLOW\Tutorial\zzz_Working_MI\model\mi\1d_bc_M04_001.MIF'
	
	#setup return values
	error = False
	message = None
	points = None
	lines = None
	regions = None
	
	fpath, fname = os.path.split(mif_file)
	mifbase, fext = os.path.splitext(mif_file)

	if fext.upper() != '.MIF':
		message = 'Error input to splitMI_func is not a .MIF file'
		return error, message, points, lines, regions

	mif = ogr.Open(mif_file)
	if mif is None:
		print "Could not open input MIF file.\n"
		sys.exit(1)

	miflyr = mif.GetLayer(0)
	miflyrname = miflyr.GetName()

	driverName = "ESRI Shapefile"
	drv = ogr.GetDriverByName( driverName )
	if drv is None:
		message = "%s driver not available.\n" % driverName
		error = True
		return error, message, points, lines, regions

	# Filter into Points
	miflyr.SetAttributeFilter("OGR_GEOMETRY='POINT'")
	if miflyr.GetFeatureCount() > 0:
		odp = drv.CreateDataSource( "%s_P.shp" % mifbase )
		points = "%s_P.shp" % mifbase
		#return True, 'test', points, lines, regions
		if odp is None:
			message = "Could not create point output file.\n"
			error = True
			return error, message, points, lines, regions

		odp.CopyLayer( miflyr, "%s_P" % mifbase )


	# Filter into Lines
	miflyr.SetAttributeFilter("OGR_GEOMETRY='LINESTRING'")
	if miflyr.GetFeatureCount() > 0:
		odp = drv.CreateDataSource( "%s_L.shp" % mifbase )
		lines = "%s_L.shp" % mifbase
		if odp is None:
			message = "Could not create line output file.\n"
			error = True
			return error, message, points, lines, regions

		odp.CopyLayer( miflyr, "%s_L" % mifbase )


	# Filter into regions
	miflyr.SetAttributeFilter("OGR_GEOMETRY='POLYGON'")
	if miflyr.GetFeatureCount() > 0:
		odr = drv.CreateDataSource( "%s_R.shp" % mifbase )
		regions = "%s_R.shp" % mifbase
		if odr is None:
			message = "Could not create region output file.\n"
			error = True
			return error, message, points, lines, regions

		odr.CopyLayer( miflyr, "%s_R" % mifbase )

	#normal exit
	return error, message, points, lines, regions
