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
			lyr_files = glob.glob(srch_str)
			self.nStyles = len(lyr_files)
		except:
			error = True
			message = ('ERROR - Unable to load .qml file names from folder: '+srch_str)
			return error, message

		#check we found something
		if (self.nStyles <1):
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
		if layer_name[-2:] == '_P' or layer_name[-2:] == '_L' or layer_name[-2:] == '_R':
			next
		else:
			if cLayer.geometryType() == 0:
				layer_name = layer_name + '_P'
			elif cLayer.geometryType() == 1:
				layer_name = layer_name + '_L'
			elif cLayer.geometryType() == 2:
				layer_name = layer_name + '_R'
		
		try:
			for i, ftype in enumerate(self.ftype):
				if ftype in layer_name:
					matching_layer = self.fpath[i]
					return error, message, matching_layer #return after first occurence found
		except:
			error = True
			message = 'ERROR - unexpected error finding style layer for file: '+layer_name
			#message = 'Debug - ftype' + ftype+'\n Layer Name: '+layer_name
			return error, message, matching_layer

		#non error
		return error, message, matching_layer