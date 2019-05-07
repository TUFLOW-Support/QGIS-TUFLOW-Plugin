# -*- coding: utf-8 -*-
"""
/***************************************************************************
 flowTrace
                                 A QGIS plugin
 Select line segments upstream of a selected line segment
                              -------------------
        begin                : 2014-02-20
        copyright            : (C) 2014 by Ed B
        email                : boesiii@yahoo.com
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
# Import the PyQt and QGIS libraries
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
# Initialize Qt resources from file resources.py
import resources_rc
# Import the code for the dialog
from flowtracedialog import flowTraceDialog
import os.path
from qgis.gui import QgsMessageBar


class flowTrace:

    def __init__(self, iface):
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value("locale/userLocale")[0:2]
        localePath = os.path.join(self.plugin_dir, 'i18n', 'flowtrace_{}.qm'.format(locale))

        if os.path.exists(localePath):
            self.translator = QTranslator()
            self.translator.load(localePath)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = flowTraceDialog()

    def initGui(self):
        # Create action that will start plugin configuration
        self.action = QAction(
            QIcon(":/plugins/flowtrace/icon.png"),
            u"Flow Trace", self.iface.mainWindow())
        # connect the action to the run method
        self.action.triggered.connect(self.run)

        # Add toolbar button and menu item
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu(u"&Flow Trace", self.action)

    def unload(self):
        # Remove the plugin menu item and icon
        self.iface.removePluginMenu(u"&Flow Trace", self.action)
        self.iface.removeToolBarIcon(self.action)

    # run method that performs all the real work
    def run(self):
        ncheck_area = 0
        ncheck_inv = 0
        QMessageBox.information(None, "Flow Trace", "Press Ok to start Flow Trace")
        #setup final selection list

        
        final_list = []
        #setup temporary selection list
        selection_list = []
        #add tolerance value
        tolerance = 1
        #get current layer
        clayer = self.iface.mapCanvas().currentLayer()
        
        if clayer is None:
            return 
        
        #get provider and info on current layer
        provider = clayer.dataProvider()
        ds = provider.dataSourceUri() #data source
        try:
            self.fpath = os.path.normpath(os.path.dirname(ds))
            tmpfname = str(os.path.basename(ds))
            ind = tmpfname.find('|')
            if (ind>0):
                self.fname = tmpfname[0:ind]
            else:
                self.fname = tmpfname
            self.curr_file = os.path.normpath(os.path.join(self.fpath,self.fname))
            self.basename = os.path.splitext(self.curr_file)[0] #remove file extension
        except:
            QMessageBox.critical(iface.mainWindow(), "Phil Ryan Hacks", 'Unable to get file path to current layer')
        #debug output 
        #msg = 'Input filename: {0}\nInput filepath: {1}\nInput file: {2}'.format(self.fname, self.fpath, self.curr_file)
        #QMessageBox.information(None, "File path info", msg)
        try:
            logfname = self.basename+'_nwk_checks.log'
            msgfname = logfname.replace('.log','.shp')
            logfid = open(logfname,'w')
            logfid.write('Started Flow Trace Log\n')
        except:
            QMessageBox.information(None, "Phil Ryan Hacks", 'Error opening .log file: {0}'.format(logfname))

        #get CRS
        try:
            crs_in = provider.crs()
        except:
            QMessageBox.information(None, "Phil Ryan Hacks", "Hacks Borken getting CRS)")
        
        #check if messages layer is open
        search_name = os.path.splitext(self.fname)[0]+'_nwk_checks'
        #QMessageBox.information(None, "Phil Ryan Hacks", 'search_name: {0}'.format(search_name))
        for name, layer in QgsMapLayerRegistry.instance().mapLayers().iteritems():
            #QMessageBox.information(None, "Phil Ryan Hacks", 'Layer name: {0}'.format(search_layer.name()))
            if layer.name().upper() == search_name.upper():
                QMessageBox.information(None, "Phil Ryan Hacks", 'Output file {0} already open. Closing'.format(search_name))
                try:
                    QgsMapLayerRegistry.instance().removeMapLayer(layer.id())
                except:
                   QMessageBox.information(None, "Phil Ryan Hacks", 'Whelp, that broke something.')
                   return

        #create vector output layer
        try:
            msg_layer = QgsVectorLayer("PointString", "point", "memory")
            msg_prov = msg_layer.dataProvider()
            # add fields
            #msg_fields = { 0 : QgsField("Message", QVariant.String) }
            msg_fields = QgsFields()
            msg_fields.append( QgsField( "notes", QVariant.String ) ) 
            msg_writer = QgsVectorFileWriter(msgfname, "System", msg_fields, QGis.WKBPoint, crs_in, "ESRI Shapefile")
            #msg_writer = QgsVectorFileWriter(msgfname, "System", msg_fields, QGis.WKBPoint, None, "ESRI Shapefile")
            if (msg_writer.hasError() != QgsVectorFileWriter.NoError):
                QMessageBox.critical(iface.mainWindow(), "Phil Ryan Hacks", 'Unable to create file: {0}'.format(msgfname))
                return
            #else:
            #    QMessageBox.information(None, "Phil Ryan Hacks", 'Opened {0}'.format(msgfname))
        except:
            QMessageBox.information(None, "Phil Ryan Hacks", "Hacks Borken creating memory layer)")

        #get selected features
        features = clayer.selectedFeatures()
        #PAR Changes
        try:
            nselect = len(features)
            logfid.write('Original number of selected features: {0}\n'.format(nselect))
            fields = clayer.pendingFields()
        except:
            QMessageBox.information(None, "Phil Ryan Hacks", "Hacks broken nselect")
        #if not clayer.selectedFeatures():
        #   QMessageBox.information(None, "Flow Trace", "No Features Selected")
        #   exit(0)
        
        # get crs for tolerance setting
        crs = self.iface.activeLayer().crs().authid()
        print crs
        if crs == 'EPSG:4269':
            rec = .0001
            tolerance = .0001
        else:
            rec = 1
        #print tolerance
        
            
        
        #iterate thru features to add to lists
        for feature in features:            
            # add selected features to final list
            final_list.append(feature.id())
            # add selected features to selection list for while loop
            selection_list.append(feature.id())
            try:
                f_id = str(fields.field(0).name()) #ID
                f_ty = str(fields.field(1).name()) #Type
                f_us = str(fields.field(6).name()) #US
                f_ds = str(fields.field(7).name()) #DS
                f_wi = str(fields.field(13).name()) #width / diam
                f_he = str(fields.field(14).name()) #height
                f_nu = str(fields.field(15).name()) #number of
                c_id = feature[f_id]
                c_ty = feature[f_ty]
                c_us = feature[f_us]
                c_ds = feature[f_ds]
                c_wi = feature[f_wi]
                c_he = feature[f_he]
                c_nu = feature[f_nu]
                if (c_nu<=0):
                    logfid.write('Warning for channel {0} number of attribute is less than 1'.format(c_id))
                    c_nu = 1
                logfid.write('Original features Attributes:\n')
                logfid.write('  {0}: {1}\n'.format(f_id,c_id))
                logfid.write('  {0}: {1}\n'.format(f_ty,c_ty))
                logfid.write('  {0}: {1}\n'.format(f_us,c_us))
                logfid.write('  {0}: {1}\n'.format(f_ds,c_ds))
                logfid.write('  {0}: {1}\n'.format(f_wi,c_wi))
                logfid.write('  {0}: {1}\n'.format(f_he,c_he))
                logfid.write('  {0}: {1}\n'.format(f_nu,c_nu))
                #calulate area
                if (c_ty.upper() in ('C')):
                    c_area = c_nu*3.141592*((c_wi/2.)**2)
                    logfid.write('  Area based on circular culvert: {0:0.3f}\n'.format(c_area))
                elif (c_ty.upper() in ('R')):
                    c_area = c_nu*c_wi*c_he
                    logfid.write('  Area based on rectangular culvert: {0:0.3f}\n'.format(c_area))
                else:
                    c_area = 0.0
                    logfid.write('Unable to calculate areas for channels other than "C" or "R" types\n')
            except:
                QMessageBox.information(None, "Phil Ryan Hacks", "Hacks Borken getting attribute data.)")
            #get feature geometry
            geom = feature.geometry()
            if geom.type() <> QGis.Line:
                print "Geometry not allowed"
                QMessageBox.information(None, "Flow Trace", "Geometry not allowed, \nPlease select line geometry only.")
                return
            
        
        
        
        #loop thru selection list
        while selection_list:
        
            #get selected features
            request = QgsFeatureRequest().setFilterFid(selection_list[0])
            feature = clayer.getFeatures(request).next()
            cur_id = feature[f_id]
            cur_ty = feature[f_ty]
            cur_us = feature[f_us]
            cur_ds = feature[f_ds]
            cur_wi = feature[f_wi]
            cur_he = feature[f_he]
            cur_nu = feature[f_nu]
            if (cur_nu<=0):
                logfid.write('Warning for channel {0} number of attribute is less than 1'.format(cur_id))
                cur_nu = 1
            logfid.write('Processing channel with ID: {0}\n'.format(cur_id))
            logfid.write('  US invert: {0}\n'.format(cur_us))
            if (cur_ty.upper() in ('C')):
                cur_area = cur_nu*3.141592*((cur_wi/2.)**2)
                logfid.write('  Area based on circular culvert: {0:0.4f}\n'.format(cur_area))
            elif (cur_ty.upper() in ('R')):
                cur_area = cur_nu*cur_wi*cur_he
                logfid.write('  Area based on rectangular culvert: {0:0.4f}\n'.format(cur_area))
            else:
                cur_area = 0.0
                logfid.write('WARNING - Unable to calculate areas for channels other than "C" or "R" types\n')

            
            # get list of nodes
            nodes = feature.geometry().asPolyline()
            
            # get upstream node
            upstream_coord = nodes[0]
                        
            # select all features around upstream coordinate using a bounding box
            rectangle = QgsRectangle(upstream_coord.x() - rec, upstream_coord.y() - rec, upstream_coord.x() + rec, upstream_coord.y() + rec)
            request = QgsFeatureRequest().setFilterRect(rectangle)
            features = clayer.getFeatures(request)
                        
            #iterate thru requested features
            for feature in features:
            
                #get list of nodes
                #print feature.id()
                nodes = feature.geometry().asPolyline()
                
                #get downstream node
                downstream_coord = nodes[-1]
                
                #setup distance
                distance = QgsDistanceArea()
                
                #get distance from downstream node to upstream node
                dist = distance.measureLine(downstream_coord, upstream_coord)
                
                #Below is the distance rounded to 2 decimal places only needed during testing
                #dist = round (distance.measureLine(downstream_coord, upstream_coord), 2)
                
                if dist < tolerance:
                    #add feature to final list
                    final_list.append(feature.id())
                    new_id = feature[f_id]
                    new_ty = feature[f_ty]
                    new_us = feature[f_us]
                    new_ds = feature[f_ds]
                    new_wi = feature[f_wi]
                    new_he = feature[f_he]
                    new_nu = feature[f_nu]
                    if (new_nu<=0):
                        logfid.write('Warning for channel {0} number of attribute is less than 1'.format(new_id))
                        new_nu = 1
                    if (new_ty.upper() in ('C')):
                        new_area = new_nu*3.141592*((new_wi/2.)**2)
                        #logfid.write('  Area based on circular culvert: {0}\n'.format(new_area))
                    elif (new_ty.upper() in ('R')):
                        new_area = new_nu*new_wi*new_he
                        #logfid.write('  Area based on rectangular culvert: {0}\n'.format(cur_area))
                    else:
                        new_area = 0.0
                        logfid.write('WARNING - Unable to calculate areas for channels other than "C" or "R" types\n')
                    logfid.write('  Found Snapped channel with ID: {0}\n'.format(new_id))
                    logfid.write('    DS invert: {0}\n'.format(new_ds))
                    logfid.write('    Area: {0:0.4f}\n'.format(new_area))
                    if (new_ds>-9999 and cur_us>-9999 and new_ds<cur_us):
                    #if (new_ds<cur_us):
                        ncheck_inv = ncheck_inv + 1
                        msg = 'CHECK - Increase in invert between US {0} ({1:0.4f}) and DS {2} ({3:0.4f})\n'.format(new_id,new_ds,cur_id,cur_us)
                        logfid.write(msg)
                        fet = QgsFeature()
                        fet.setGeometry(QgsGeometry.fromPoint(downstream_coord)) 
                        fet.setAttributes([msg])
                        msg_writer.addFeature(fet)
                    if (cur_area<new_area):
                        ncheck_area = ncheck_area + 1
                        msg = 'CHECK - Decrease in area between US {0} ({1:0.4f}) and DS {2} ({3:0.4f})\n'.format(new_id,new_area,cur_id,cur_area)
                        logfid.write(msg)
                        fet = QgsFeature()
                        fet.setGeometry(QgsGeometry.fromPoint(downstream_coord)) 
                        fet.setAttributes([msg])
                        msg_writer.addFeature(fet)
                    
                    #add feature to selection list to keep selecting upstream line segments
                    #selection_list.append(feature.id())
                                        
                    if feature.id() not in selection_list:
                        #add feature to selection list
                        selection_list.append(feature.id())
                
            #remove feature from selection list
            selection_list.pop(0)
            
            
        #select features using final_list           
        clayer.setSelectedFeatures(final_list)
        
        #close the outputs
        logfid.flush()
        logfid.close()
        del msg_writer
        self.iface.addVectorLayer(msgfname, None, "ogr")

        #refresh the canvas
        self.iface.mapCanvas().refresh()
        msg = 'Total Features Selected: {0}\nTotal Decreasing Area Issues: {1}\nTotal Increasing Inverts {2}'.format(len(final_list), ncheck_area, ncheck_inv)
        QMessageBox.information(None, "Flow Trace Complete", msg)
