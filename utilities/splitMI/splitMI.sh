#!/bin/bash

############################################################################
#
# splitMI - A simple program to convert MapInfo MID/MIF files into one
# or more shapefiles for each type of object in the MID/MIF. The
# TUFLOW file naming convention of _P, _L and _R for points, lines and
# regions is used.
#
############################################################################
#
# Usage: splitMI <name_of_mif_file_withextension>
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

MIFILE="$1"
FILEBASE="${MIFILE%.MIF}"
FILEBASE="${FILEBASE%.mif}"
FILEBASE="${FILEBASE%.Mif}"

PTFILE="${FILEBASE}_P".shp
LNFILE="${FILEBASE}_L".shp
RGFILE="${FILEBASE}_R".shp

ogr2ogr -where "OGR_GEOMETRY='POINT'" "$PTFILE" "$MIFILE" -skipfailures -nlt POINT 
ogr2ogr -where "OGR_GEOMETRY='LINESTRING'" "$LNFILE" "$MIFILE" -skipfailures -nlt LINESTRING 
ogr2ogr -where "OGR_GEOMETRY='POLYGON'" "$RGFILE" "$MIFILE" -skipfailures -nlt POLYGON 

if [ `stat -c%s $PTFILE` -eq 100 ]
then
    rm $PTFILE
    rm ${PTFILE%.shp}.shx
    rm ${PTFILE%.shp}.prj
    rm ${PTFILE%.shp}.dbf
fi

if [ `stat -c%s $LNFILE` -eq 100 ]
then
    rm $LNFILE
    rm ${LNFILE%.shp}.shx
    rm ${LNFILE%.shp}.prj
    rm ${LNFILE%.shp}.dbf
fi

if [ `stat -c%s $RGFILE` -eq 100 ]
then
    rm $RGFILE
    rm ${RGFILE%.shp}.shx
    rm ${RGFILE%.shp}.prj
    rm ${RGFILE%.shp}.dbf
fi