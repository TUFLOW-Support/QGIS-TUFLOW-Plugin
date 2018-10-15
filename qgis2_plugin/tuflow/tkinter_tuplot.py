# TuPLOT External Tkinter program.
# Build: 2017-11-AA Development
# Author: PR, ES

# ArcGIS and QGIS use identical versions

import os
import sys
import ctypes
current_path = os.path.dirname(__file__)
pythonV = sys.version_info[0]

# Relevant in QGIS only
if pythonV == 2:
	try:
		from Tkinter import *
		import ttk
		from tkFileDialog import askopenfilename
		from tkFileDialog import asksaveasfile
	except:
		sys.path.append(os.path.join(current_path, 'tkinter\\DLLs'))
		sys.path.append(os.path.join(current_path, 'tkinter\\libs'))
		sys.path.append(os.path.join(current_path, 'tkinter\\Lib'))
		sys.path.append(os.path.join(current_path, 'tkinter\\Lib\\lib-tk'))
		from Tkinter import *
		import ttk
		from tkFileDialog import askopenfilename
		from tkFileDialog import asksaveasfile
elif pythonV == 3:
	try:
		from tkinter import *
		import tkinter.ttk as ttk
		from tkinter.filedialog import askopenfilename
		from tkinter.filedialog import asksaveasfile
	except:
		sys.path.append(os.path.join(current_path, '_tk\\DLLs'))
		sys.path.append(os.path.join(current_path, '_tk\\libs'))
		sys.path.append(os.path.join(current_path, '_tk\\Lib'))
		from tkinter import *
		import tkinter.ttk as ttk
		from tkinter.filedialog import askopenfilename
		from tkinter.filedialog import asksaveasfile

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2TkAgg
from matplotlib.figure import Figure
from matplotlib.patches import Patch
from matplotlib.patches import Polygon
from matplotlib.backend_bases import key_press_handler
import numpy
import GIS_int
import TUFLOW_results
from collections import OrderedDict
from list_visible_windows import *
from minimise_window import *


class TuPLOT():
	"""TuPLOT is a standalone graphing program that is intended for use with TUFLOW. It requires
	2 files - an interface file (.int) and a TUFLOW Plot Control file (.tpc)"""
	
	def __init__(self):
		self.res = []
		self.ts_types_All = None
		self.ts_types_P = None
		self.ts_types_L = None
		self.ts_types_R = None
		self.IDs = []
		self.time_ndp = 4 #number of decimal places for legend entries, changed when results added
		self.ax2_exists = False

		#self.dict_1D{''} #

	def get_int_fname(self):
		"""Lets the user set the interface file. The interface file can be created 
		from any GIS program (ArcGIS, QGIS, Mapinfo etc). This file lists the geometry
		type and the selected features that are used by TuPLOT"""
		
		try:
			prev_name = int_file.get()
		except:
			prev_name = 'No int file set yet.'
		name = askopenfilename()
		if len(name) > 1:
			saveDate.set(os.path.getmtime(name))
		else:
			name = prev_name
		int_file.set(name)
		tp.load_int_fname()
		
	def init_save_date(self, parentPID, parentHWND):
		"""This function polls the interface file's save date. If a change in save date
		is found, it will update the StrVar 'saveDate' so that tkinter trace method will be
		activated."""
		self.PID = os.getpid()  # get Process ID of TUPLOT window
		# get ID of Window Handler (HWND) - use python ctypes
		openWindows = list_windows()  
		for window in openWindows:
			if window[1] == self.PID:
				self.HWND = window[0]
		self.windowStatus = str(GetWindowPlacement(self.HWND).showCmd)  # get status of tuplot window(minimized or not minimized)
		self.parentPID = parentPID  # process ID of parent process (QGIS or ArcGIS)
		self.parentHWND = parentHWND  # window handler ID of parent process (QGIS or ArcGIS)
		user32 = ctypes.windll.LoadLibrary('user32.dll')
		user32.SetParent(self.HWND, self.parentHWND)
		self.parentWindowStatus = str(GetWindowPlacement(self.parentHWND).showCmd)  # get status of parent window (minimized or not minimized)
		tp.polling_routine()  # start polling routine that monitors a number of parameters

			
	def polling_routine(self):
		"""This function monitors:
		parent process PID in open applications - check if it's still running
		parent window status - whether it is minimised or not
		tuplot window status - whether user has minimized it, or is minimised because parent process has been minimised
		iterface file save date - check if it has been changed
		"""
		open_pids = list_pids()  # obtain list of process id of programs that are open
		if self.parentPID in open_pids:  # check if parent pid is in list of open programs
			# parent process still running so check save date of .int file
			try:  # sometimes you can be unlucky and exit parent process here which will cause crash
				new_parentWindowStatus = str(GetWindowPlacement(self.parentHWND).showCmd)  # ctypes
				new_windowStatus = str(GetWindowPlacement(self.HWND).showCmd)  # ctypes
			except:  # probably means parent process has been killed, so kill tuplot
				LB_status.insert(0, 'parent process terminated')
				tp.close_TuPLOT()
				root.destroy()
			if new_parentWindowStatus != self.parentWindowStatus:  # check if parent process has changed
				if new_parentWindowStatus == 'SW_SHOW_MINIMIZED':  # if minimized, minimize tuplot as well
					ShowWindow(self.HWND, SHOWCMD.SW_MINIMIZE)
					self.parentWindowStatus = new_parentWindowStatus
					if new_windowStatus == 'SW_SHOW_MINIMIZED':  # if tuplot was already minimized, keep it that way when qgis is returned
						self.windowStatus = new_windowStatus
				elif self.parentWindowStatus == 'SW_SHOW_MINIMIZED' and self.windowStatus != 'SW_SHOW_MINIMIZED':
					ShowWindow(self.HWND, SHOWCMD.SW_RESTORE)
					self.parentWindowStatus = new_parentWindowStatus
			if new_windowStatus != 'SW_SHOW_MINIMIZED' and self.windowStatus == 'SW_SHOW_MINIMIZED':  # if tuplot is manually maximised change status
				self.windowStatus = new_windowStatus
			intFile = str(int_file.get())
			if len(intFile) > 1:  # check there is a current interface file
				newSaveDate = os.path.getmtime(intFile)
				if str(newSaveDate) != saveDate.get(): # check if save date has changed
					saveDate.set(os.path.getmtime(intFile))
					LB_status.insert(0, 'selected elements updated')
			root.after(100, tp.polling_routine) # polling routine
		else:  # parent process has been terminated, close tuplot
			LB_status.insert(0, 'parent process terminated')
			tp.close_TuPLOT()
			root.destroy()

	def add_legend_cb(self, frame, rowpos, colpos):
		"""tkinter check button for graph legend. On change will run the next function below
		to update plot."""
		
		self.legend_var = StringVar()
		self.CB_legend = ttk.Checkbutton(frame, text='Legend',
			variable = self.legend_var,
			onvalue='ON', offvalue='OFF', command=tp.legend_status_changed)
		self.CB_legend.grid(column=colpos, row=rowpos, sticky=N+S+E+W)
		
	def legend_status_changed(self):
		"""Function to update plot when legend check button is clicked."""
		
		LB_status.insert(0, 'Legend switched {0}'.format(self.legend_var.get()))
		tp.update_plot()
		
	def add_second_ax_cb(self, frame, rowpos, colpos, listBox):
		"""tkinter check button for secondary axis. On change will run the next function below
		to update plot."""
		
		self.secondAx_var = StringVar()
		self.CB_secondAx = ttk.Checkbutton(frame, text='Secondary Axis',
			variable = self.secondAx_var,
			onvalue='ON', offvalue='OFF', command=lambda: tp.secondAx_status_changed(listBox))
		self.CB_secondAx.grid(column=colpos, row=rowpos, sticky=N+S+E+W)
		
	def secondAx_status_changed(self, listBox):
		"""Function to update plot when legend check button is clicked."""
		
		#LB_status.insert(0, 'Secondary axis switched {0}'.format(self.secondAx_var.get()))
		if self.secondAx_var.get() == 'OFF':
			listBox.configure(state=DISABLED)
		else:
			listBox.configure(state=NORMAL)
			
			# Populate list box with result types
			LB_dat_type_ax2.delete(0, END)
			if self.plot_type_combo.get() == 'Long Profile':
				LB_dat_type_ax2.insert(0, 'Not available for LP')
			else:
				res_vars = []
				try:
					if self.GIS.Geom == self.GIS.GeomPoint:
						res_vars = self.ts_types_P
					elif self.GIS.Geom == self.GIS.GeomLine:
						res_vars = self.ts_types_L
					elif self.GIS.Geom == self.GIS.GeomRegion:
						res_vars = self.ts_types_R
					else:
						res_vars = self.ts_types_All
				except: #not interface file loaded
					res_vars = self.ts_types_All
					LB_status.insert(0, 'Warning no interface file open')
				#populate the list
				if res_vars:
					for res_var in res_vars:
						LB_dat_type_ax2.insert(END, res_var)
				else:
					LB_dat_type.insert(END, 'ERROR - No results available to plot')
					
		tp.update_plot()
		
	def add_cbMedianRes(self, frame, rowpos, colpos):
		"""tkinter check button for graph legend. On change will run the next function below
		to update plot."""
		
		self.medianRes_var = StringVar()
		self.cbMedianRes = ttk.Checkbutton(frame, text='Show Median Result', variable = self.medianRes_var, 
		                                   onvalue='ON', offvalue='OFF', command=tp.update_plot)
		self.cbMedianRes.grid(column=colpos, row=rowpos, sticky=N+S+E+W, pady=[6,0])
		
	def add_cbMeanRes(self, frame, rowpos, colpos):
		"""tkinter check button for graph legend. On change will run the next function below
		to update plot."""
		
		self.meanRes_var = StringVar()
		self.cbMeanRes = ttk.Checkbutton(frame, text='Show Mean Result', variable=self.meanRes_var, onvalue='ON', 
		                                 offvalue='OFF', command=tp.update_plot)
		self.cbMeanRes.grid(column=colpos, row=rowpos, sticky=N+S+E+W)

	def set_results_variable_ts(self):
		"""Function that sets the result type list for time series type."""
		
		LB_status.insert(0, 'Updating results variable list.')
		LB_dat_type.delete(0, END)
		LB_dat_type_ax2.delete(0, END)
		res_vars = []
		try:
			if self.GIS.Geom == self.GIS.GeomPoint:
				res_vars = self.ts_types_P
			elif self.GIS.Geom == self.GIS.GeomLine:
				res_vars = self.ts_types_L
			elif self.GIS.Geom == self.GIS.GeomRegion:
				res_vars = self.ts_types_R
			else:
				res_vars = self.ts_types_All
		except: #not interface file loaded
			res_vars = self.ts_types_All
			LB_status.insert(0, 'Warning no interface file open')
		#populate the list
		if res_vars:
			for res_var in res_vars:
				LB_dat_type.insert(END, res_var)
				LB_dat_type_ax2.insert(END, res_var)
		else:
			LB_dat_type.insert(END, 'ERROR - No results available to plot')
		LB_dat_type.selection_set(0)

	def set_results_variable_lp(self):
		"""Function that sets the result type list for long profile type."""
		
		LB_status.insert(0, 'Updating results variable list.')
		LB_dat_type.delete(0, END)
		LB_dat_type_ax2.delete(0, END)
		LB_dat_type_ax2.insert(0, 'Not available for LP')
		res_vars = []
		try:
			if (self.ts_types_P.count('Level') > 0):
				res_vars.append('Max Water Level')
				res_vars.append('Water Level at Time')
			if (self.ts_types_P.count('Energy Level') > 0):
				res_vars.append('Max Energy Level')
				res_vars.append('Energy Level at Time')
			res_vars.append('Bed Level')
			res_vars.append('Culvert Dimensions (if any)')
			res_vars.append('Pit Ground Levels (if any)')
			res_vars.append('Adverse Gradients (if any)')
			res_vars.append('Left Bank Obvert')
			res_vars.append('Right Bank Obvert')
			for res_var in res_vars:
				LB_dat_type.insert(END, res_var)
		except:
			LB_status.insert(0, 'ERROR - updating LP results variable list.')
		LB_dat_type.selection_set(0)
			
	def create_plot_type_combo(self, vert_frame, pos):
		"""ttk combo box for plot type (time series or long profile.When changed will
		run 2 functions below to update plot."""
		
		self.plot_type_value = StringVar()
		#self.plot_type_value.trace('w',tp.plot_type_changed)
		self.plot_type_combo = ttk.Combobox(vert_frame, state="readonly", textvariable=self.plot_type_value)
		self.plot_type_combo['values'] = ('Timeseries')
		self.plot_type_combo.current(0)
		self.plot_type_combo.grid(column=0, row=pos, sticky=N+S+E+W)
		self.plot_type_combo.bind("<<ComboboxSelected>>", tp.plot_type_changed) #note lack of () in call to tp.plot_type_changed

	def update_plot_type_combo(self):
		"""Function to update available options in plot type combobox if interface file is updated."""
		
		LB_status.insert(0, 'Updating plot type combo')
		self.plot_type_combo.delete(0, END)
		if (self.GIS.Geom == self.GIS.GeomLine) or (self.GIS.Geom == self.GIS.GeomMulti):
			self.plot_type_combo['values'] = ('Timeseries', 'Long Profile')
		else:
			self.plot_type_combo['values'] = ('Timeseries')
		self.plot_type_combo.current(0)

	def plot_type_changed(self, eventObject):
		"""Function that runs when the plot type combobox (time series of long profile)
		is updated with a new selection."""
		
		# add message to status dialog
		LB_status.insert(0, 'Plot type changed to {0}'.format(self.plot_type_combo.get()))

		# Check if new selection is time series or long profile
		if (self.plot_type_combo.get() == 'Timeseries'):
			tp.set_results_variable_ts()
		elif (self.plot_type_combo.get() == 'Long Profile'):
			#LB_status.insert(0,'update lp')
			tp.set_results_variable_lp()
			id1 = None
			id2 = None
			error = False
			message = None
			if len(self.res) == 0:
				LB_status.insert(0, 'ERROR - No results open yet')
				return
			if len(self.IDs)==0:
				LB_status.insert(0, 'ERROR - Elements selected or no interface file open')
				return
			if len(self.IDs)==1:
				if self.Doms[0] == '1D':
					id1 = self.IDs[0]
				else:
					error = True
					message = 'Selected object is not 1D channel - type: '+ self.Doms[0]
			if len(self.IDs) >= 2:
				if (len(self.IDs) > 2):
					LB_status.insert(0, 'WARNING - More than 2 objects selected.  Using only 2.')
				if self.Doms[0]=='1D' and self.Doms[1] == '1D':
					id1 = self.IDs[0]
					id2 = self.IDs[1]
				else:
					error = True
					message = 'Selected objects are not 1D channels - types: '+ self.Doms[0] + ' and ' + self.Doms[0]

			if error:
				LB_status.insert(0, message)
				return

			#update the connectivity
			for res in self.res:
				res.LP.connected = False
				res.LP.static = False

				# get channel connectivity
				error, message = res.LP_getConnectivity(id1, id2)
				if error:
					LB_status.insert(0, message)
					return

				#get static, maximums, bed levels etc
				error, message = res.LP_getStaticData()
				if error:
					LB_status.insert(0, message)
					return
		
		tp.update_plot()
		#print (eventObject)
		
	def update_lp(self):
		"""Function that updates the long profile when feature selection changes (only updates if long profile is
		selected in the combobox and the new selected feature is a line type."""
		
		#tp.set_results_variable_lp()
		id1 = None
		id2 = None
		error = False
		message = None
		if len(self.res) == 0:
			LB_status.insert(0, 'ERROR - No results open yet')
			return
		if len(self.IDs)==0:
			LB_status.insert(0, 'ERROR - Elements selected or no interface file open')
			return
		if len(self.IDs)==1:
			if self.Doms[0] == '1D':
				id1 = self.IDs[0]
			else:
				error = True
				message = 'Selected object is not 1D channel - type: '+ self.Doms[0]
		if len(self.IDs) >= 2:
			if (len(self.IDs) > 2):
				LB_status.insert(0, 'WARNING - More than 2 objects selected.  Using only 2.')
			if self.Doms[0]=='1D' and self.Doms[1] == '1D':
				id1 = self.IDs[0]
				id2 = self.IDs[1]
			else:
				error = True
				message = 'Selected objects are not 1D channels - types: '+ self.Doms[0] + ' and ' + self.Doms[0]
        
		if error:
			LB_status.insert(0, message)
			return
        
		#update the connectivity
		for res in self.res:
			res.LP.connected = False
			res.LP.static = False
        
			# get channel connectivity
			error, message = res.LP_getConnectivity(id1, id2)
			if error:
				LB_status.insert(0, message)
				return
        
			#get static, maximums, bed levels etc
			error, message = res.LP_getStaticData()
			if error:
				LB_status.insert(0, message)
				return
		
		tp.update_plot()
		#print (eventObject)

	def load_int_fname(self, *args):
		"""Load interface file function. Runs when interface file is updated (or button in plot gui
		is pressed). Loads the interface file. The *args is required when the trace method is pointing
		to this function (trace method is observing the saveDate and running this function if saveDate changes."""
		
		# first steps are used later so the result list isn't updated if same geometry type
		global geomType
		try:
			prevGeomType = geomType
			prevPlotType = self.plot_type_combo.get()
		except:
			prevGeomType = 0
			prevPlotType = 0
		
		# begin load interface file routine
		LB_selected.delete(0, END)
		fname = int_file.get()
		if os.path.isfile(fname):
			self.GIS = GIS_int.INT()
			self.GIS.load(fname)
			LB_status.insert(0, 'Loaded {0}'.format(fname))
			LB_status.insert(0, 'Found {0} Plot IDs'.format(len(self.GIS.ID_att)))
			self.IDs = self.GIS.ID_att
			self.Doms = self.GIS.Doms
			self.Type_Att = self.GIS.Type_Att
			self.Source_Att = self.GIS.Source_Att
			for id in self.IDs: #add to list box
				LB_selected.insert(END, id)
			if self.GIS.Geom == self.GIS.GeomNone:
				LB_status.insert(0, 'Warning - No Geometry detected')
			elif self.GIS.Geom == self.GIS.GeomPoint:
				LB_status.insert(0,'Point geometry detected in .int file')
			elif self.GIS.Geom == self.GIS.GeomLine:
				LB_status.insert(0,'Line geometry detected in .int file')
			elif self.GIS.Geom == self.GIS.GeomRegion:
				LB_status.insert(0,'Region geometry detected in .int file')
			elif self.GIS.Geom == self.GIS.GeomMulti:
				LB_status.insert(0,'Multiple geometry detected in .int file')
			elif self.GIS.Geom == self.GIS.GeomUnknown:
				LB_status.insert(0,'Warning - Unknown geometry detected in .int file')
		else:
			LB_status.insert(0, 'interface File doesnt exist: {0}'.format(fname))
			return
		
		# check if the same geometry as previous
		geomType = self.GIS.Geom
		if geomType != prevGeomType:
			tp.set_results_variable_ts() #update the results variable list
			tp.update_plot_type_combo() #update the plot type options
		else:
			# check if long profile is selected, because then it needs updating
			if prevPlotType == 'Long Profile':
				tp.update_lp()
		tp.update_plot() #call a plot update

	def create_fig(self):
		"""Function to load up plot properties for matplotlib."""
		
		self.fig = Figure(figsize=(5,5), dpi=100)
		self.ax1 = self.fig.add_subplot(111)
		self.ax1.plot([1, 2, 3, 4, 5, 6, 7, 8], [5, 6, 1, 3, 8, 9, 3, 5])
		#self.fig.tight_layout()
		self.canvas = FigureCanvasTkAgg(tp.fig, self.mainframe)
		self.canvas.show()
		self.canvas.get_tk_widget().grid(column=0, row=2, columnspan = 3, sticky=N+S+E+W)
		
	def exportCsv(self):
		if LB_selected.size() == 0:
			LB_status.insert(0, 'No elements selected. Won\'t export')
			return
		if self.plot_type_combo.get() == "Timeseries":
			# Create data headers
			resultIds = []
			for i in range(LB_selected.size()):
				resultId = LB_selected.get(i)
				resultIds.append(resultId)
			resultTypes = []
			reslist_str = list(LB_dat_type.curselection())
			for i in reslist_str:
				resultType = LB_dat_type.get(i)
				resultTypes.append(resultType)
			dataHeader = ''
			for resultId in resultIds:
				for resultType in resultTypes:
					dataHeader += '{0}_{1},'.format(resultId, resultType)
			
			# Get data
			data = self.ax1.lines[0].get_data()[0]  # write X axis first
			data = numpy.reshape(data, [len(data), 1])
			for line in self.ax1.lines:
				dataY = line.get_data()[1]
				dataY = numpy.reshape(dataY, [len(dataY), 1])
				data = numpy.append(data, dataY, axis=1)
			
			# Save data out
			saveFile = asksaveasfile(mode='w', defaultextension='.csv')
			if saveFile is not None:
				#file = open(saveFile, 'w')
				saveFile.write('Time (hr),{0}\n'.format(dataHeader))
				for i, row in enumerate(data):
					saveFile.write('{0}\n'.format(",".join(map(str, data[i].tolist()))))
				saveFile.close()
				LB_status.insert(0, 'Finished saving file.')
		
		elif self.plot_type_combo.get() == 'Long Profile':
			# Create data headers
			resultTypes = []
			reslist_str = list(LB_dat_type.curselection())
			for i in reslist_str:
				resultType = LB_dat_type.get(i)
				resultTypes.append(resultType)
			dataHeader = ''
			for resultType in resultTypes:
				dataHeader += 'Chainage (m),{0},'.format(resultType)
	
			# Get data
			maxLen = 0
			for line in self.ax1.lines:  # Get max data length so one numpy array can be set up
				maxLen = max(maxLen, len(line.get_data()[0]))
			data = numpy.zeros([maxLen, 1]) * numpy.nan
			for line in self.ax1.lines:
				lineX = numpy.reshape(line.get_data()[0], [len(line.get_data()[0]), 1])
				lineY = numpy.reshape(line.get_data()[1], [len(line.get_data()[1]), 1])
				if len(lineX) < maxLen:  # if data is less than max length, pad with nan values
					diff = maxLen - len(lineX)
					fill = numpy.zeros([diff, 1]) * numpy.nan
					lineX = numpy.append(lineX, fill)
					lineX = numpy.reshape(lineX, [maxLen, 1])
					lineY = numpy.append(lineY, fill)
					lineY = numpy.reshape(lineY, [maxLen, 1])
				data = numpy.append(data, lineX, axis=1)
				data = numpy.append(data, lineY, axis=1)
			data = numpy.delete(data, 0, axis=1)
	
			# Save data out
			saveFile = asksaveasfile(mode='w', defaultextension='.csv')
			if saveFile is not None:
				#file = open(saveFile, 'w')
				saveFile.write('{0}\n'.format(dataHeader))
				for i, row in enumerate(data):
					line = ''
					for j, value in enumerate(row):
						if not numpy.isnan(data[i][j]):
							line += '{0},'.format(data[i][j])
						else:
							line += '{0},'.format('')
					line += '\n'
					saveFile.write(line)
				saveFile.close()
				LB_status.insert(0, 'Finished saving file.')

	def current_time_changed(self, eventObject):
		"""Function that runs when user selects new time in 'Current Time' dialog."""
		
		LB_status.insert(0, 'Current time changed')
		tp.update_plot()
		
	def result_variable_changed(self, eventObject):
		"""Function that runs when user selects new result variable in 'Result Variable' dialog."""
		
		LB_status.insert(0, 'Result variable changed')
		tp.update_plot()
		
	def result_file_changed(self, eventObject):
		"""Function that runs when user selects new result file in 'Result Files' dialog"""
		
		LB_status.insert(0, 'Result file changed')
		tp.update_plot()
		
	def update_plot(self):
		"""Function that updates the plot to show new selections / options. A lot of other functions point
		to this function so be careful!."""
		
		LB_status.insert(0, 'Starting update_plot {0}'.format(self.plot_type_combo.get()))

		self.ax1.cla()
		artists = []
		labels = []
		if self.ax2_exists:
			if self.secondAx_var.get() == 'ON' and self.plot_type_combo.get() == "Timeseries":
				self.axis2.cla()
			else:
				LB_status.insert(0,'dual axis not needed')
				try:
					self.fig.delaxes(self.axis2)
					self.ax2_exists = False
				except:
					LB_status.insert(0, "Error deleting axis2\n Please contact support@tuflow.com")
		
		#ititialise limits
		xmin = 999999.
		xmax = -999999.
		ymin = 999999.
		ymax = -999999.

		#compile list of selected results files
		reslist_str = list(LB_res.curselection()) #compile list of selected results comes back as string
		if len(reslist_str) == 0:
			LB_status.insert(0, 'ERROR - No results files open/selected')
			return
		if(LB_res.get(0) == 'No results loaded yet'):
			LB_status.insert(0, 'ERROR - No results files open/selected')
			return
		else: #convert to int
			reslist = []
			for res_str in reslist_str:
				reslist.append(int(res_str))
			nRes = len(reslist)
		#compile list of selected variables to plot
		typeids = list(LB_dat_type.curselection())
		if len(typeids) == 0:
			LB_status.insert(0, 'ERROR - No result variable selected')
			return
		typenames = []
		for i in typeids:
			typenames.append(LB_dat_type.get(i))
			#LB_status.insert(0,'dat {0}'.format(LB_dat_type.get(i)))
			
		# Secondary  Axis
		typeids2 = list(LB_dat_type_ax2.curselection())
		typenames2 = []
		for i in typeids2:
			typenames2.append(LB_dat_type_ax2.get(i))
			
		#check if median is required
		calc_median = False
		if self.medianRes_var.get() == 'ON':
			calc_median = True
			if nRes < 3:
				calc_median = False
				LB_status.insert(0, 'Warning - Median requires at least three results selected')
			if len(self.IDs) != 1:
				calc_median = False
				LB_status.insert(0, 'Warning - Median only valid for a single output location')
			if self.plot_type_combo.get() != "Timeseries":
				calc_median = False
				LB_status.insert(0,'Warning - Median only valid for a timeseries plot type')
			if len(typenames) != 1:
				calc_median = False
				LB_status.insert(0,'Warning - Median only valid for a single output parameter')
				
		#check if mean is required
		calc_mean = False
		meanAbove = False
		if self.meanRes_var.get() == 'ON':
			calc_mean = True
			if nRes < 3:
				calc_mean = False
				LB_status.insert(0, 'Warning - Mean requires at least three results selected')
			if len(self.IDs) != 1:
				calc_mean = False
				LB_status.insert(0, 'Warning - Mean only valid for a single output location')
			if self.plot_type_combo.get() != "Timeseries":
				calc_mean = False
				LB_status.insert(0, 'Warning - Mean only valid for a timeseries plot type')
			if len(typenames) != 1:
				calc_mean = False
				LB_status.insert(0, 'Warning - Mean only valid for a single output parameter')
			if meanValue.get() == 'meanAbove':
				meanAbove = True
				LB_status.insert(0, 'Using 1st value above mean.')
			elif meanValue.get() == 'meanClosest':
				meanAbove = False
				LB_status.insert(0, 'Using closest value to mean.')
				
		#numpy array for calculation of median / mean
		if calc_median or calc_mean:
			try:
				max_vals = numpy.zeros([nRes])
			except:
				LB_status.insert(0, 'Error - setting up numpy array for mean/median.')
				calc_median = False
				calc_mean = False

		#copy from QGIS
		nres_used = 0
		for resno in reslist:
			nres_used = nres_used + 1
			res = self.res[resno]
			name = res.displayname
			
			# Long Profile plots
			if self.plot_type_combo.get() == "Long Profile":
				#LB_status.insert(0,'to do // create long profile')
				plot = True
				if res.LP.connected and res.LP.static:
					LB_status.insert(0, 'add this profile')
					#update the limits
					xmin = 0.0 # should always start at 0
					tmp_xmax = max(res.LP.dist_nodes)
					xmax = max(xmax,tmp_xmax)
					tmp_ymin = min(res.LP.node_bed)
					ymin = min(ymin, tmp_ymin)

					# plot max water level
					if typenames.count('Max Water Level') != 0:
						a, = self.ax1.plot(res.LP.dist_chan_inverts, res.LP.Hmax)
						artists.append(a)
						label = 'Max Water Level'
						if nRes > 1:
							labels.append(label + " - " + name)
						else:
							labels.append(label)
						self.ax1.hold(True)
						ymax = max(ymax, max(res.LP.Hmax))

					#plot LP water level at time
					if typenames.count('Water Level at Time') != 0:
						label = 'Water Level at Time'
						try:
							tInd = int(list(LB_time.curselection())[0]) #assume only one line selected
							curT = float(LB_time.get(tInd))
						except:
							LB_status.insert(0, 'ERROR - getting current time')
							return
						error, message = res.LP_getData('Head', curT, 0.01)
						if error:
							LB_status.insert(0, 'ERROR - Extracting temporal data for LP')
							LB_status.insert(0, message)
						else:
							a, = self.ax1.plot(res.LP.dist_chan_inverts, res.LP.Hdata)
							artists.append(a)
							labels.append('Water Level at ({0:.{1}f})'.format(curT,self.time_ndp))
							if nRes > 1:
								labels.append(label + " - " + name)
							else:
								labels.append(label)
							self.ax1.hold(True)
							ymax = max(ymax, max(res.LP.Hdata))

					# plot max energy level
					if typenames.count('Max Energy Level') != 0:
						a, = self.ax1.plot(res.LP.dist_chan_inverts, res.LP.Emax)
						artists.append(a)
						label = 'Max Energy Level'
						if nRes > 1:
							labels.append(label + " - " + name)
						else:
							labels.append(label)
						self.ax1.hold(True)
						ymax = max(ymax, max(res.LP.Hmax))

					#plot LP energy level at time
					if typenames.count('Energy Level at Time') != 0:
						try:
							tInd = int(list(LB_time.curselection())[0]) #assume only one line selected
							curT = float(LB_time.get(tInd))
						except:
							LB_status.insert(0, 'ERROR - getting current time')
							return
						error, message = res.LP_getData('Energy', curT, 0.01)
						if error:
							LB_status.insert(0, 'ERROR - Extracting temporal data for LP')
							LB_status.insert(0, message)
						else:
							a, = self.ax1.plot(res.LP.dist_chan_inverts, res.LP.Edata)
							artists.append(a)
							labels.append('Energy Level at ({0:.{1}f})'.format(curT, self.time_ndp))
							if nRes > 1:
								labels.append(label + " - " + name)
							else:
								labels.append(label)
							self.ax1.hold(True)
							ymax = max(ymax, max(res.LP.Hdata))


					#plot bed
					if typenames.count('Bed Level') != 0 and nres_used == len(reslist):
						a, = self.ax1.plot(res.LP.dist_chan_inverts, res.LP.chan_inv)
						artists.append(a)
						label = 'Bed Level'
						if nRes > 1:
							labels.append(label + " - " + name)
						else:
							labels.append(label)
						self.ax1.hold(True)
						ymax = max(ymax, max(res.LP.chan_inv))

					# culvert dimensions (if any)
					if typenames.count('Culvert Dimensions (if any)') != 0 and nres_used == len(reslist):
						for verts in res.LP.culv_verts:
							if verts:
								poly = Polygon(verts, facecolor='0.9', edgecolor='0.5')
								self.ax1.add_patch(poly)
								
					#plot LB
					if typenames.count('Left Bank Obvert') != 0 and nres_used == len(reslist):
						a, = self.ax1.plot(res.LP.dist_chan_inverts, res.LP.chan_LB)
						artists.append(a)
						label = 'Left Bank'
						if nRes > 1:
							labels.append(label + " - " + name)
						else:
							labels.append(label)
						self.ax1.hold(True)
						ymax = max(ymax, max(res.LP.chan_LB))

					#plot RB
					if typenames.count('Right Bank Obvert') != 0 and nres_used == len(reslist):
						a, = self.ax1.plot(res.LP.dist_chan_inverts, res.LP.chan_RB)
						artists.append(a)
						label = 'Right Bank'
						if nRes > 1:
							labels.append(label + " - " + name)
						else:
							labels.append(label)
						self.ax1.hold(True)
						ymax = max(ymax, max(res.LP.chan_RB))

					#plot adverse sections
					if typenames.count('Adverse Gradients (if any)') != 0:
						#adverse water levels
						if res.LP.adverseH.nLocs > 0:
							a, = self.ax1.plot(res.LP.adverseH.chainage, res.LP.adverseH.elevation, marker='o', linestyle='None', color='r')
							artists.append(a)
							labels.append("Adverse Water Level")
							if(self.legend_var.get() == ON): #legend is on:
								for i in range(res.LP.adverseH.nLocs):
									self.ax1.text(res.LP.adverseH.chainage[i], res.LP.adverseH.elevation[i]+0.25, res.LP.adverseH.node[i], rotation=90, verticalalignment='bottom', fontsize=12)
							else:
								LB_status.insert(0, 'Turn on legend to get more information about adverse grades')
							self.ax1.hold(True)
						#adverse energy levels
						if res.LP.adverseE.nLocs > 0:
							a, = self.ax1.plot(res.LP.adverseE.chainage, res.LP.adverseE.elevation, marker='o', linestyle='None', color='y')
							artists.append(a)
							labels.append("Adverse Energy Level")
							if(self.legend_var.get() == 'ON'): #legend is on:
								for i in range(res.LP.adverseE.nLocs):
									self.ax1.text(res.LP.adverseE.chainage[i], res.LP.adverseE.elevation[i]+0.25, res.LP.adverseE.node[i], rotation=90, verticalalignment='bottom', fontsize=12)
							else:
								LB_status.insert(0, 'Turn on legend to get more information about adverse grades')
							self.ax1.hold(True)

			# Time series plot type
			elif self.plot_type_combo.get() == "Timeseries":
				breakloop = False
				for i, ydataid in enumerate(self.IDs):
					if ydataid:
						for typename in typenames:
							found = False
							message = 'ERROR - Unable to extract data'
							if typename == 'Current Time':
								break #jump to next data type
							if not breakloop:
								if res.formatVersion == 2: #2015
									dom = self.Doms[i]
									#source = self.Source_Att[i].upper()
									#if (dom == '2D'):
									#	if typename.upper().find('STRUCTURE FLOWS')>= 0 and source=='QS':
									#		typename = 'QS'
									#	elif typename.upper().find('STRUCTURE LEVELS')>= 0 and source=='HU':
									#		typename = 'HU'
									#	elif typename.upper().find('STRUCTURE LEVELS')>= 0 and source=='HD':
									#		typename = 'HD'
									try:
										found, ydata, message = res.getTSData(ydataid, dom, typename, 'Geom')
										xdata = res.times
									except:
										LB_status.insert(0, 'ERROR - Extracting results')
										LB_status.insert(0, 'res = ' + res.displayname)
										LB_status.insert(0, 'ID: ' + ydataid)
										LB_status.insert(0, 'i: ' + str(i))
									if calc_median or calc_mean:
										try:
											max_vals[nres_used-1] = ydata.max()
										except:
											if calc_median:
												calc_median = False
												LB_status.insert(0,'ERROR - Calcuating Median, suppressing median output')
											if calc_mean:
												calc_mean = False
												LB_status.insert(0,'ERROR - Calcuating mean, suppressing mean output')
								else:
									found = False
									message = 'Unexpected Format Version:' + str(res.formatVersion)
								if not found:
									LB_status.insert(0,message)
									message = "No data for " + ydataid + " ("+dom+") - " + typename
									LB_status.insert(0, message)
								else:
									if (len(reslist) > 1):
										label = res.displayname + ": " + ydataid + "("+dom+") - " + typename
									else:
										label = ydataid + " ("+dom+") - " + typename
									if len(xdata) == len(ydata):
										a, = self.ax1.plot(xdata, ydata)
										artists.append(a)
										labels.append(label)
										self.ax1.hold(True)
									else:
										LB_status.insert(0, 'ERROR - Size of x and y data doesnt match')
										
				# Secondary axis
				if self.secondAx_var.get() == 'ON':
					sel_datTypeAx2 = list(LB_dat_type_ax2.curselection())
					if len(sel_datTypeAx2) > 0:
						if not self.ax2_exists:
							self.axis2 = self.ax1.twinx()
							self.ax2_exists = True
						LB_status.insert(0, 'plotting secondary axis')
						breakloop = False
						for i, ydataid in enumerate(self.IDs):
							if ydataid:
								for typename in typenames2:
									found = False
									message = 'ERROR - Unable to extract data'
									if typename == 'Current Time':
										break #jump to next data type
									if not breakloop:
										if res.formatVersion == 2: #2015
											dom = self.Doms[i]
											#source = self.Source_Att[i].upper()
											#if (dom == '2D'):
											#	if typename.upper().find('STRUCTURE FLOWS')>= 0 and source=='QS':
											#		typename = 'QS'
											#	elif typename.upper().find('STRUCTURE LEVELS')>= 0 and source=='HU':
											#		typename = 'HU'
											#	elif typename.upper().find('STRUCTURE LEVELS')>= 0 and source=='HD':
											#		typename = 'HD'
											try:
												found, ydata, message = res.getTSData(ydataid, dom, typename, 'Geom')
												xdata = res.times
											except:
												LB_status.insert(0, 'ERROR - Extracting results')
												LB_status.insert(0, 'res = ' + res.displayname)
												LB_status.insert(0, 'ID: ' + ydataid)
												LB_status.insert(0, 'i: ' + str(i))
										else:
											found = False
											message = 'Unexpected Format Version:' + str(res.formatVersion)
										if not found:
											LB_status.insert(0,message)
											message = "No data for " + ydataid + " ("+dom+") - " + typename
											LB_status.insert(0, message)
										else:
											if (len(reslist) > 1):
												label = res.displayname + ": " + ydataid + "("+dom+") - " + typename + " (Axis 2)"
											else:
												label = ydataid + " ("+dom+") - " + typename + " (Axis 2)"
											if len(xdata) == len(ydata):
												a2, = self.axis2.plot(xdata, ydata, marker='x')
												artists.append(a2)
												labels.append(label)
												#self.axis2.hold(True)
											else:
												LB_status.insert(0, 'ERROR - Size of x and y data doesnt match')

		#add "current time"
		if (typenames.count('Current Time') > 0):
			try:
				ax1y1, ax1y2 = self.ax1.get_ylim() #get current limits
				tInd = int(list(LB_time.curselection())[0]) #assume only one line selected
				curT = float(LB_time.get(tInd))
				a, = self.ax1.plot([curT,curT], [-9e37, 9e37], color='red', linewidth=2)
				artists.append(a)
				labels.append('Current time ({0:.{1}f})'.format(curT, self.time_ndp))
				self.ax1.set_ylim([ax1y1, ax1y2])
			except:
				LB_status.insert(0, 'Unable to add current time')
				

		#add median data
		if calc_median:
			try:
				argsort = max_vals.argsort()
				med_rnk = int(nRes/2) #+1 not requried as python uses 0 rank
				med_ind = argsort[med_rnk]
				res = self.res[med_ind]
				if res.formatVersion == 2:
					name = res.displayname
					ydataid  = self.IDs[0] #only works for 1 ID
					typename = typenames[0] #and 1 data type
					dom = self.Doms[0]
					source = self.Source_Att[0].upper()
					found, ydata, message = res.getTSData(ydataid,dom,typename, 'Geom')
					if not found:
						LB_status.insert(0,'ERROR - Extracting median data.')
					else:
						xdata = res.times
						label = 'Median - {0}'.format(name)
						a, = self.ax1.plot(xdata, ydata,color='black',linewidth=3,linestyle=':')
						artists.append(a)
						labels.append(label)
			except:
				LB_status.insert(0,'ERROR - Adding Median data, skipping')
				
		#add mean data (2017-06-AD)
		if calc_mean:
			try:
				argsort = max_vals.argsort()
				meanVal = max_vals.mean()
				ms = numpy.sort(max_vals)
				if meanAbove:
					ms_ind = ms.searchsorted(meanVal,side='right')
				else:
					ms_ind = (numpy.abs(ms-meanVal)).argmin()
				mean_ind = argsort[ms_ind]
				LB_status.insert(0,'Mean value is {0}, rank index is {1}'.format(meanVal, ms_ind+1))
				res = self.res[mean_ind]
				if res.formatVersion == 2:
					name = res.displayname
					ydataid  = self.IDs[0] #only works for 1 ID
					typename = typenames[0] #and 1 data type
					dom = self.Doms[0]
					source = self.Source_Att[0].upper()
					found, ydata, message = res.getTSData(ydataid,dom,typename, 'Geom')
					if not found:
						LB_status.insert(0,'ERROR - Extracting median data.')
					else:
						xdata = res.times
						label = 'Mean - {0}'.format(name)
						a, = self.ax1.plot(xdata, ydata,color='blue',linewidth=3,linestyle=':')
						artists.append(a)
						labels.append(label)
			except:
				LB_status.insert(0,'ERROR - Adding Mean data, skipping')

		#If legend checkbox is on
		if(self.legend_var.get() == 'ON'): #legend is on:
			self.ax1.legend(artists, labels, loc=legend_position.get())
		self.ax1.grid(True)
		self.canvas.draw() #redraw

	def load_res(self):
		"""Function that loads .tpc results."""
		
		#Lb1.insert(END,'loading res')
		global tpcArg
		LB_status.insert(0, 'Adding Results')
		res = TUFLOW_results.ResData()
		if len(tpcArg) < 1: # only used once at beginning if .tpc file is selected in GIS program
			inFileName = askopenfilename()
		else:
			inFileName = tpcArg
		LB_status.insert(0, 'Loading results {0}'.format(inFileName))
		error, message = res.Load(inFileName)
		if error:
			LB_status.insert(0, message)
		else:
			LB_status.insert(0, 'Loaded')
			self.res.append(res)
			tp.update_res_list()

		#update the results that are available in the files
		self.ts_types_P = []
		self.ts_types_L = []
		self.ts_types_R = []
		tmp_list = []
		for res in self.res:
			for restype in res.Types:
				#self.lwStatus.insertItem(0,'debug: res: '+res.displayname+', type: '+restype)
				restype = restype.replace('1D ', '')
				restype = restype.replace('2D ', '')
				if restype.upper() == 'LINE FLOW':
					restype = 'Flows' #don't differentiate between 1D and 2D flows
				if restype.upper() == 'POINT WATER LEVEL':
					restype = 'Water Levels' #don't differentiate between 1D and 2D water levels
				tmp_list.append(restype)
			if res.Channels: #bug fix which would not load results with no 1D
				if res.Channels.nChan > 0: #
					tmp_list.append('US Levels')
					tmp_list.append('DS Levels')

		#get unique results types within all results files open
		unique_res = list(OrderedDict.fromkeys(tmp_list))
		for restype in unique_res:
			#self.lwStatus.insertItem(0,'Debug: '+restype)
			if restype.upper() in ('WATER LEVELS'):
				self.ts_types_P.append('Level')
			elif restype.upper() in ('ENERGY LEVELS'):
				self.ts_types_P.append('Energy Level')
			elif restype.upper() in ('POINT VELOCITY'):
				self.ts_types_P.append('Velocity')
			elif restype.upper() in ('POINT X-VEL'):
				self.ts_types_P.append('VX')
			elif restype.upper() in ('POINT Y-VEL'):
				self.ts_types_P.append('VY')
			elif restype.upper() in ('FLOWS'):
				self.ts_types_L.append('Flows')
			elif restype.upper() in ('VELOCITIES'):
				self.ts_types_L.append('Velocities')
			elif restype.upper() in ('LINE FLOW AREA'):
				self.ts_types_L.append('Flow Area')
			elif restype.upper() in ('LINE INTEGRAL FLOW'):
				self.ts_types_L.append('Flow Integral')
			elif restype.upper() in ('US LEVELS'):
				self.ts_types_L.append('US Levels')
			elif restype.upper() in ('DS LEVELS'):
				self.ts_types_L.append('DS Levels')
			elif restype.upper() in ('DS LEVELS'):
				self.ts_types_L.append('DS Levels')
			elif restype.upper() in ('LINE STRUCTURE FLOW'):
				self.ts_types_L.append('Structure Flows')
			elif restype.upper() in ('STRUCTURE LEVELS'):
				self.ts_types_L.append('Structure Levels')
			elif restype.upper() in ('REGION AVERAGE WATER LEVEL'): #2017-09-AA
				self.ts_types_R.append('Average Level')
			elif restype.upper() in ('REGION MAX WATER LEVEL'): #2017-09-AA
				self.ts_types_R.append('Max Level')
			elif restype.upper() in ('REGION FLOW INTO'): #2017-09-AA
				self.ts_types_R.append('Flow Into')
			elif restype.upper() in ('REGION FLOW OUT OF'): #2017-09-AA
				self.ts_types_R.append('Flow Out')
			elif restype.upper() in ('REGION VOLUME'): #2017-09-AA
				self.ts_types_R.append('Volume')
			elif restype.upper() in ('REGION SINK/SOURCE'): #2017-09-AA
				self.ts_types_R.append('Sink/Source')
			else:
				self.lwStatus.insertItem(0, 'ERROR unhandled type: ' + restype)
				self.lwStatus.item(0).setTextColor(self.qred)

		#add current time
		if len(self.ts_types_P) > 0:
			self.ts_types_P.append('Current Time')
		else:
			self.ts_types_P = [] #none of this data in results
		if len(self.ts_types_L) > 0:
			self.ts_types_L.append('Current Time')
		else:
			self.ts_types_L = [] #none of this data in results
		if len(self.ts_types_R) > 0:
			self.ts_types_R.append('Current Time')
		else:
			self.ts_types_R = [] #none of this data in results
		#all ts types
		unique_res = list(OrderedDict.fromkeys(self.ts_types_P,self.ts_types_L))
		self.ts_types_All = list(OrderedDict.fromkeys(self.ts_types_P + self.ts_types_L + self.ts_types_R))
		
		tpcArg = '' # change to empty string so next time 'Add Results' is selected it doesn't bypass openfile dialog selection

		# update the results variable list
		tp.set_results_variable_ts()

		#update the times available
		tp.update_time_list()
		
		tp.update_plot()
		

	def update_time_list(self):
		"""Populate the 'Current Time' dialog with list of times."""
		
		LB_time.delete(0, END)
		try:
			times = self.res[0].times
			if len(times) > 1:
				self.dt_hr = times[1] - times[0] # to work out precision
				if self.dt_hr < 0.001:
					self.time_ndp = 4
				elif self.dt_hr < 0.01:
					self.time_ndp = 3
				elif self.dt_hr < 0.1:
					self.time_ndp = 2
				elif self.dt_hr < 1.:
					self.time_ndp = 1
				else:
					self.time_ndp = 0
			for time in times:
				LB_time.insert(END, '{0:.{1}f}'.format(time, self.time_ndp))
			LB_time.selection_set(0)
		except:
			LB_status.insert(0, 'WARNING - Unable to populate times, check results loaded.')

	def close_res(self):
		"""Closes selected results."""
		
		selectedResults = list(LB_res.curselection()) # compile list of selected results
		for item in reversed(selectedResults):
			LB_status.insert(0, 'Removing result {0}'.format(LB_res.get(item)))
			self.res.pop(item)
			LB_res.delete(item)

	def clear_status(self):
		"""Function that clears the status box."""
		
		LB_status.delete(0, END)
		LB_status.insert(0, 'Status cleared')

	def update_res_list(self):
		"""Updates the 'Results File' dialog."""
		
		LB_status.insert(0, 'Updating results list')
		LB_res.delete(0, END)
		for res in self.res:
			LB_res.insert(END, res.displayname)
		#LB_status.insert(0,'done')
		LB_res.selection_set(0, END)
		
	def close_TuPLOT(self):
		"""Clean up after TuPLOT if closed. Mainly deleting .int file."""
		
		if len(int_file.get()) > 0:
			if os.path.splitext(int_file.get())[1].upper() == '.INT':
				os.remove(int_file.get())
			
	def handle_focus(eventObject):
		if event.widget == window:
			root.focus_set()
			mainframe.focus_set()


if __name__ == "__main__":
	tp = TuPLOT()
	
	root = Tk()
	frame= ttk.Frame(root, borderwidth=2, relief="ridge")
	Grid.rowconfigure(root, 0, weight=1)
	Grid.columnconfigure(root, 0, weight=1)
	frame.grid(column=0, row=0, sticky=N+S+E+W)
	root.title("TuPLOT 2018-03-AB")
	toolbar_frame = ttk.Frame(root, borderwidth=2, relief="groove")
	mainframe = ttk.Frame(root, borderwidth=2, relief="groove")
	mainframe.grid(sticky=N+S+E+W, column=0, row=0)
	mainframe.rowconfigure(0, weight=1)
	mainframe.rowconfigure(1, weight=1)
	mainframe.rowconfigure(2, weight=100, minsize=20)
	mainframe.rowconfigure(3, weight=1)
	mainframe.columnconfigure(0, weight=1, minsize=60)
	mainframe.columnconfigure(1, weight=1, minsize=20)
	mainframe.columnconfigure(2, weight=10, minsize=60)
	tp.mainframe = mainframe
	
	# Initialise string variables for bindings
	int_file = StringVar()
	saveDate = StringVar()
	saveDate.trace("w", tp.load_int_fname)
	
	# row 4 add a graph
	tp.create_fig()
	
	# add toolbar
	toolbar = NavigationToolbar2TkAgg(tp.canvas, toolbar_frame )
	toolbar_frame.grid(column=0, row=4, columnspan = 3, sticky=N+S+E+W)
	tp.canvas.get_tk_widget().grid(column=2, row=2, rowspan=2, sticky=N+S+E+W)
	
	#create 1st vertical frame for options
	vert_frame1 = ttk.Frame(mainframe, borderwidth=2, relief="groove")
	ttk.Label(vert_frame1, text="Results Files").grid(column=0, row=0, sticky=N+W)
	LB_res = Listbox(vert_frame1, height=5, selectmode='extended', exportselection=0) #selectmode options see http://effbot.org/tkinterbook/listbox.htm
	LB_res.insert(1, 'No results loaded yet')
	LB_res.bind("<<ListboxSelect>>", tp.result_file_changed)
	LB_res.grid(column=0, row=1, sticky=N+S+E+W)
	ttk.Button(vert_frame1, text="Add Results", command=tp.load_res).grid(column=0, row=2, sticky=N+W+E,pady=[10,0]) #pad above
	ttk.Button(vert_frame1, text="Close Results", command=tp.close_res).grid(column=0, row=3, sticky=N+W+E)
	ttk.Label(vert_frame1, text="Plot Type").grid(column=0, row=4, sticky=N+W, pady=[10,0])
	tp.create_plot_type_combo(vert_frame1, 5) #create the drob box (frame,position)
	ttk.Label(vert_frame1, text="Result Variable").grid(column=0, row=6, sticky=N+W, pady=[10,0])
	LB_dat_type = Listbox(vert_frame1, height=8, selectmode='extended', exportselection=0) #selectmode options see http://effbot.org/tkinterbook/listbox.htm
	LB_dat_type.insert(END, 'No results open yet')
	LB_dat_type.bind("<<ListboxSelect>>", tp.result_variable_changed)
	LB_dat_type.selection_set(0)
	LB_dat_type.grid(column=0, row=7, sticky=N+S+E+W)
	LB_dat_type_ax2 = Listbox(vert_frame1, height=6, selectmode='extended', exportselection=0) #selectmode options see http://effbot.org/tkinterbook/listbox.htm
	LB_dat_type_ax2.bind("<<ListboxSelect>>", tp.result_variable_changed)
	LB_dat_type_ax2.grid(column=0, row=9, sticky=N+S+E+W)
	LB_dat_type_ax2.configure(state=DISABLED)
	tp.add_second_ax_cb(vert_frame1, 8, 0, LB_dat_type_ax2)
	vert_frame1.columnconfigure(0, weight=1)
	vert_frame1.rowconfigure(0, weight=0)
	vert_frame1.rowconfigure(1, weight=1)
	vert_frame1.rowconfigure(2, weight=0)
	vert_frame1.rowconfigure(3, weight=0)
	vert_frame1.rowconfigure(4, weight=0)
	vert_frame1.rowconfigure(5, weight=0)
	vert_frame1.rowconfigure(6, weight=0)
	vert_frame1.rowconfigure(7, weight=1)
	vert_frame1.rowconfigure(8, weight=0)
	vert_frame1.grid(column=0, row=2, sticky=N+S+E+W)
	
	#create 2nd vertical frame for options
	vert_frame2 = ttk.Frame(mainframe, borderwidth=2, relief="groove")
	ttk.Label(vert_frame2, text="Selected Elements").grid(column=0, row=0, sticky=N+W)
	LB_selected = Listbox(vert_frame2, height=1, selectmode='extended', exportselection=0) #selectmode options see http://effbot.org/tkinterbook/listbox.htm
	LB_selected.insert(1, 'Nothing selected or not linked to GIS')
	LB_selected.grid(column=0, row=1, sticky=N+S+E+W)
	tp.add_cbMedianRes(vert_frame2, 2, 0)
	tp.add_cbMeanRes(vert_frame2, 3, 0)
	meanValue = StringVar()
	meanAbove = ttk.Radiobutton(vert_frame2, text='Result Above Mean', variable=meanValue, value='meanAbove', command=tp.update_plot).grid(column=0, row=4, sticky=N+S+E+W, padx=[10,0], pady=0)
	meanClosest = ttk.Radiobutton(vert_frame2, text='Result Closest Mean', variable=meanValue, value='meanClosest', command=tp.update_plot).grid(column=0, row=5, sticky=N+S+E+W, padx=[10,0], pady=0)
	meanValue.set('meanAbove')
	ttk.Label(vert_frame2, text="Current Time").grid(column=0, row=6, sticky=N+W, pady=[10,0])
	LB_time = Listbox(vert_frame2, height=5, selectmode='browse', exportselection=0) #selectmode options see http://effbot.org/tkinterbook/listbox.htm
	LB_time.bind("<<ListboxSelect>>", tp.current_time_changed) #note lack of () in call to tp.plot_type_changed)
	LB_time.grid(column=0, row=7, sticky=N+S+E+W)

	vert_frame2.columnconfigure(0, weight=1)
	vert_frame2.rowconfigure(0, weight=0)
	vert_frame2.rowconfigure(1, weight=1)
	vert_frame2.rowconfigure(2, weight=0)
	vert_frame2.rowconfigure(3, weight=0)
	vert_frame2.rowconfigure(4, weight=0)
	vert_frame2.rowconfigure(5, weight=0)
	vert_frame2.rowconfigure(6, weight=0)
	vert_frame2.rowconfigure(7, weight=2)
	vert_frame2.grid(column=1, row=2,rowspan=1, sticky=N+S+E+W)
	
	#create horizontal frame for GIS interface file
	horz_frame1 = ttk.Frame(mainframe, borderwidth=2, relief="groove")
	ttk.Label(horz_frame1, text="GIS Interface File").grid(column=0, row=0, sticky=N+W)
	int_file_disp = ttk.Entry(horz_frame1, width=40, textvariable=int_file)
	int_file_disp.grid(column=1, row=0, sticky=N+S+E+W)
	ttk.Button(horz_frame1, text="Set Interface File", command=tp.get_int_fname).grid(column=2, row=0, sticky=N+S+E+W, padx=[10,0])
	ttk.Button(horz_frame1, text="Load Interface", command=tp.load_int_fname).grid(column=3, row=0, sticky=N+W+E)
	horz_frame1.columnconfigure(0, weight=0,minsize=20)
	horz_frame1.columnconfigure(1, weight=10,minsize=20)
	horz_frame1.columnconfigure(2, weight=1,minsize=20)
	horz_frame1.columnconfigure(3, weight=1,minsize=20)
	horz_frame1.grid(column=0, row=0, columnspan = 3, sticky=N+S+E+W)
	
	# create status frame
	status_frame = ttk.Frame(mainframe, borderwidth=2, relief="groove")
	ttk.Label(status_frame, text="Status dialog").grid(column=0, row=4, sticky=N+W,pady=[10,0])
	LB_status = Listbox(status_frame,height=6, selectmode='single', exportselection=0) #selectmode options see http://effbot.org/tkinterbook/listbox.htm
	LB_status.insert(END, 'Started')
	LB_status.grid(column=0, row=5, sticky=N+S+E+W)
	ttk.Button(status_frame, text="Clear Status", command=tp.clear_status).grid(column=0, row=6, sticky=N+W+E)
	status_frame.columnconfigure(0, weight=1)
	status_frame.rowconfigure(0, weight=0)
	status_frame.rowconfigure(1, weight=1)
	status_frame.rowconfigure(2, weight=0)
	status_frame.grid(column=0, row=3, columnspan = 2, sticky=N+S+E+W)
	
	#create horizontal frame for plot options
	horz_frame2 = ttk.Frame(mainframe, borderwidth=2, relief="groove")
	ttk.Button(horz_frame2, text="Update Plot", command=tp.update_plot).grid(column=0, row=0, sticky=N+W+E)
	tp.add_legend_cb(horz_frame2, 0, 1)
	legend_position = StringVar()
	RB_leg_auto = ttk.Radiobutton(horz_frame2, text='Auto', variable=legend_position, value='best', state='selected', command=tp.legend_status_changed).grid(column=2, row=0, sticky=N+S+E+W)
	RB_leg_ul = ttk.Radiobutton(horz_frame2, text='UL', variable=legend_position, value='upper left', command=tp.legend_status_changed).grid(column=3, row=0, sticky=N+S+E+W)
	RB_leg_ur = ttk.Radiobutton(horz_frame2, text='UR', variable=legend_position, value='upper right', command=tp.legend_status_changed).grid(column=4, row=0, sticky=N+S+E+W)
	RB_leg_ll = ttk.Radiobutton(horz_frame2, text='LL', variable=legend_position, value='lower left', command=tp.legend_status_changed).grid(column=5, row=0, sticky=N+S+E+W)
	RB_leg_lr = ttk.Radiobutton(horz_frame2, text='LR', variable=legend_position, value='lower right', command=tp.legend_status_changed).grid(column=6, row=0, sticky=N+S+E+W)
	legend_position.set('best')
	ttk.Button(horz_frame2, text="Export plot to csv", command=tp.exportCsv).grid(column=7, row=0, sticky=N+W+E)
	horz_frame2.columnconfigure(0, weight=3, minsize=20)
	horz_frame2.columnconfigure(1, weight=1, minsize=20)
	horz_frame2.columnconfigure(2, weight=1, minsize=20)
	horz_frame2.columnconfigure(3, weight=1, minsize=20)
	horz_frame2.columnconfigure(4, weight=1, minsize=20)
	horz_frame2.columnconfigure(5, weight=1, minsize=20)
	horz_frame2.columnconfigure(6, weight=1, minsize=20)
	horz_frame2.columnconfigure(7, weight=1, minsize=20)
	horz_frame2.grid(column=0, row=1, columnspan = 3, sticky=N+S+E+W)
	
	# routine to deal with arguments
	for i, arg in enumerate(sys.argv):
		if i == 0:
			continue
		elif os.path.splitext(arg)[1].upper() == '.INT':
			int_file.set(os.path.abspath(arg))
		elif os.path.splitext(arg)[1].upper() == '.TPC':
			tpcArg = os.path.abspath(arg)
			tp.load_res()
		elif os.path.splitext(arg)[1].upper() == '.PID':
			parentPID = int(os.path.splitext(arg)[0])
			openWindows = list_windows()
			for window in openWindows:
				if window[1] == parentPID:
					parentHWND = window[0]
			
	tp.init_save_date(parentPID, parentHWND)
	root.lift()
	root.attributes("-topmost", True) # keeps the window at the top
	root.mainloop()
	tp.close_TuPLOT()
