"""
 --------------------------------------------------------
        tuflowqgis_settings - tuflowqgis settings 
        begin                : 2015-05-07
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
"""

from PyQt4.QtCore import QSettings
from qgis.core import QgsProject

class stored():
	def __init__(self):
		self.CRS_ID = None
		self.tf_exe = None
		self.base_dir = None

class TF_Settings():
	def __init__(self):
		self.project_settings = stored()
		self.global_settings = stored()
		self.combined = stored()
		self.settings = QSettings()
		self.project = QgsProject.instance()
	
	def Load(self):
		error = False
		message = None
		
		# load gloabal settings
		try:
			self.global_settings.CRS_ID = self.settings.value("TUFLOW/CRS", "Undefined")
			self.global_settings.tf_exe = self.settings.value("TUFLOW/exe", "Undefined")
			self.global_settings.base_dir = self.settings.value("TUFLOW/dir", "Undefined")
		except:
			error = True
			message = 'Unable to load global setting'
			return error, message		
		#set to None type if not defined
		if self.global_settings.CRS_ID=="Undefined":
			self.global_settings.CRS_ID = None
		if self.global_settings.tf_exe=="Undefined":
			self.global_settings.tf_exe = None
		if self.global_settings.base_dir=="Undefined":
			self.global_settings.base_dir = None
		
		#load project settings
		try:
			self.project_settings.CRS_ID = self.project.readEntry("TUFLOW","CRS","Undefined")[0]
			self.project_settings.tf_exe = self.project.readEntry("TUFLOW","exe","Undefined")[0]
			self.project_settings.base_dir = self.project.readEntry("TUFLOW","dir","Undefined")[0]
		except:
			error = True
			message = 'Unable to load global setting'
			return error, message
		#set to None type if not defined
		if self.project_settings.CRS_ID=="Undefined":
			self.project_settings.CRS_ID = None
		if self.project_settings.tf_exe=="Undefined":
			self.project_settings.tf_exe = None
		if self.project_settings.base_dir=="Undefined":
			self.project_settings.base_dir = None
			
		#normal return
		try:
			self.Combine()
		except:
			message = "Unable to combine global and project settings"
			error = True
		return error, message
		
	def Save_Global(self):
		error = False
		message = None
		try:
			if self.global_settings.CRS_ID: #don't save if None
				self.settings.setValue("TUFLOW/CRS", self.global_settings.CRS_ID)
			if self.global_settings.tf_exe:
				self.settings.setValue("TUFLOW/exe", self.global_settings.tf_exe)
			if self.global_settings.base_dir:
				self.settings.setValue("TUFLOW/dir", self.global_settings.base_dir)
		except:
			error = True
			message = 'Unable to save global settings'
		return error, message
	
	def Save_Project(self):
		error = False
		message = None
		try:
		
			if self.project_settings.CRS_ID:
				self.project.writeEntry("TUFLOW", "CRS", self.project_settings.CRS_ID)
			if self.project_settings.tf_exe:
				self.project.writeEntry("TUFLOW", "exe", self.project_settings.tf_exe)
			if self.project_settings.base_dir:
				self.project.writeEntry("TUFLOW", "dir", self.project_settings.base_dir)
		except:
			error = True
			message = 'Unable to save project data'
		return error, message
		
	def Combine(self): #if project settings use these, else fall back to global settings
		#exe
		if self.project_settings.tf_exe:
			self.combined.tf_exe = self.project_settings.tf_exe
		elif self.global_settings.tf_exe:
			self.combined.tf_exe = self.global_settings.tf_exe
		else:
			self.combined.tf_exe = None
		#CRS
		if self.project_settings.CRS_ID:
			self.combined.CRS_ID = self.project_settings.CRS_ID
		elif self.global_settings.CRS_ID:
			self.combined.CRS_ID = self.global_settings.CRS_ID
		else:
			self.combined.CRS_ID = None
		#dir
		if self.project_settings.base_dir:
			self.combined.base_dir = self.project_settings.base_dir
		elif self.global_settings.base_dir:
			self.combined.base_dir = self.global_settings.base_dir
		else:
			self.combined.base_dir = None
			
	def get_last_exe(self):
		error = False
		last_exe = None
		try:
			last_exe = self.settings.value("TUFLOW/last_exe", "Undefined")
		except:
			last_exe = "Undefined"
		return last_exe
		
	def save_last_exe(self,last_exe):
		error = False
		message = None
		if last_exe:
			try:
				self.settings.setValue("TUFLOW/last_exe", last_exe)
			except:
				error = True
				message = 'Unable to save last executbale to settings'
				#return error, message
		else:
			error = True
			message = 'last exe is None and was not saved.'
			#return error, message
		

	def get_last_mi_folder(self):
		error = False
		last_mi = None
		try:
			last_mi = self.settings.value("TUFLOW/last_mi_folder", "Undefined")
		except:
			last_mi = "Undefined"
		return last_mi
		
	def save_last_mi_folder(self,last_mi):
		error = False
		message = None
		if last_mi:
			try:
				self.settings.setValue("TUFLOW/last_mi_folder", last_mi)
			except:
				error = True
				message = 'Unable to save last executbale to settings'
				#return error, message
		else:
			error = True
			message = 'last mifolder is None and was not saved.'
			#return error, message
			
	def get_last_chk_folder(self):
		error = False
		last_chk = None
		try:
			last_chk = self.settings.value("TUFLOW/last_chk_folder", "Undefined")
		except:
			last_chk = "Undefined"
		return last_chk
		
	def save_last_chk_folder(self,last_chk):
		error = False
		message = None
		if last_chk:
			try:
				self.settings.setValue("TUFLOW/last_chk_folder", last_chk)
			except:
				error = True
				message = 'Unable to save last check folder to settings'
				#return error, message
		else:
			error = True
			message = 'last_chk_folder is None and was not saved.'
			#return error, message
	
	def get_last_run_folder(self):
		error = False
		last_run = None
		try:
			last_run = self.settings.value("TUFLOW/last_run_folder", "Undefined")
		except:
			last_run = "Undefined"
		return last_run
		
	def save_last_run_folder(self,last_run):
		error = False
		message = None
		if last_run:
			try:
				self.settings.setValue("TUFLOW/last_run_folder", last_run)
			except:
				error = True
				message = 'Unable to save last run folder to settings'
				#return error, message
		else:
			error = True
			message = 'last_chk_folder is None and was not saved.'
			
	def get_last_arr_outFolder(self):
		error = False
		last_chk = None
		try:
			last_arr = self.settings.value("TUFLOW/last_arr_outFolder", "Undefined")
		except:
			last_arr = "Undefined"
		return last_arr
		
	def save_last_arr_outFolder(self, last_arr):
		error = False
		message = None
		if last_arr:
			try:
				self.settings.setValue("TUFLOW/last_arr_outFolder", last_arr)
			except:
				error = True
				message = 'Unable to save last output folder to settings'
				#return error, message
		else:
			error = True
			message = 'last_arr_folder is None and was not saved.'
			#return error, message