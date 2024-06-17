"""
 --------------------------------------------------------
        tuflowqgis  - tuflowqgis styles
        begin                : 2016-02-15
        copyright            : (C) 2016 by Phillip Ryan
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
"""

import os
import glob
import re

from qgis.core import QgsWkbTypes

class TF_Styles:

	def __init__(self):
		#initialise the class
		self.ftype = []
		self.fname = []
		self.fpath = []
		self.style_folder = os.path.join(os.path.dirname(__file__),'QGIS_Styles')
		#print(self.style_folder)
		

	def Load(self):
		#Loads all the .qml files and sorts by longest first

		error = False
		message = None
		#find all .qml files with glob
		try:
			srch_str = os.path.join(self.style_folder,'*.qml')
			if os.name != 'nt':  # don't need to search for .QML files on windows
				srch_str_2 = os.path.join(self.style_folder,'*.QML')
				lyr_files = glob.glob(srch_str) + glob.glob(srch_str_2)
			else:
				lyr_files = glob.glob(srch_str)
			self.nStyles = len(lyr_files)
		except:
			error = True
			message = ('ERROR - Unable to load .qml file names from folder: '+ srch_str)
			return error, message

		#check we found something
		if not self.nStyles:
			error = True
			message = ('ERROR - No .qml files found that match glob search string: '+self.style_folder)
			return error, message

		#sort by longest first (i.e. check for _zsh_zpt before _zpt)
		try:
			lyr_files.sort(key = lambda s: -len(s))
		except:
			error = True
			message = 'ERROR - Unable to sort qml file names'
			return error, message

		try:
			for slyr in lyr_files:
				#print(slyr)
				self.ftype.append(os.path.split(slyr)[1][:-4])
				self.fname.append(os.path.split(slyr)[1])
				self.fpath.append(slyr)
		except:
			error = True
			message = 'ERROR - unexpected error proccesing .qml files'
			return error, message

		return error, message

	def Find(self, layer_name, cLayer):
		#Find the first style match which matches the layer name
		error = False
		message = None
		matching_layer = None
		
		# Check to see if there is a geometry type in file name (_P, _L, _R)
		has_geom_ext = layer_name[-2:] == '_P' or layer_name[-2:] == '_L' or layer_name[-2:] == '_R'
		if cLayer.geometryType() == QgsWkbTypes.PointGeometry:
			geom_ext = '_P'
		elif cLayer.geometryType() == QgsWkbTypes.LineGeometry:
			geom_ext = '_L'
		elif cLayer.geometryType() == QgsWkbTypes.PolygonGeometry:
			geom_ext = '_R'
		else:
			geom_ext = ''

		if not has_geom_ext:
			layer_name = layer_name + geom_ext
		
		try:
			for i, ftype in enumerate(self.ftype):
				if ftype.startswith('_'):  # check style
					if ftype.lower() in layer_name.lower():
						matching_layer = self.fpath[i]
						return error, message, matching_layer #return after first occurence found
				else:  # input layer
					geom_ext_ = re.findall('_[PLRplr]$', ftype)
					if geom_ext_:
						ftype_ = re.sub('_[PLRplr]$', '', ftype)
						if ftype_.lower() in layer_name.lower() and geom_ext.lower() == geom_ext_[0].lower():
							matching_layer = self.fpath[i]
							return error, message, matching_layer
					else:
						if ftype.lower() in layer_name.lower():
							matching_layer = self.fpath[i]
							return error, message, matching_layer
		except:
			error = True
			message = 'ERROR - unexpected error finding style layer for file: '+layer_name
			#message = 'Debug - ftype' + ftype+'\n Layer Name: '+layer_name
			return error, message, matching_layer

		#non error
		return error, message, matching_layer