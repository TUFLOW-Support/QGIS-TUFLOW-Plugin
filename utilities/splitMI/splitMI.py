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

import sys
import ogr
import string

mifbase = sys.argv[1]

mif = ogr.Open("%s.mif" % mifbase)
if mif is None:
    print "Could not open input MIF file.\n"
    sys.exit(1)

miflyr = mif.GetLayer(0)
miflyrname = miflyr.GetName()

driverName = "ESRI Shapefile"
drv = ogr.GetDriverByName( driverName )
if drv is None:
    print "%s driver not available.\n" % driverName
    sys.exit(1)

# Filter into Points
miflyr.SetAttributeFilter("OGR_GEOMETRY='POINT'")
if miflyr.GetFeatureCount() > 0:
    odp = drv.CreateDataSource( "%s_P.shp" % mifbase )
    if odp is None:
        print "Could not create output file.\n"
        sys.exit(1)

    odp.CopyLayer( miflyr, "%s_P" % mifbase )


# Filter into Lines
miflyr.SetAttributeFilter("OGR_GEOMETRY='LINESTRING'")
if miflyr.GetFeatureCount() > 0:
    odp = drv.CreateDataSource( "%s_L.shp" % mifbase )
    if odp is None:
        print "Could not create output file.\n"
        sys.exit(1)

    odp.CopyLayer( miflyr, "%s_L" % mifbase )


# Filter into regions
miflyr.SetAttributeFilter("OGR_GEOMETRY='POLYGON'")
if miflyr.GetFeatureCount() > 0:
    odr = drv.CreateDataSource( "%s_R.shp" % mifbase )
    if odr is None:
        print "Could not create region output file.\n"
        sys.exit(1)

    odr.CopyLayer( miflyr, "%s_R" % mifbase )

