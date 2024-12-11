"""
 --------------------------------------------------------
        tuflowqgis_library - tuflowqgis operation functions
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
"""

import sys, re
import os.path
import tempfile
import shutil
import zipfile
from datetime import datetime, timedelta
import subprocess
from time import sleep

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from qgis.gui import *
from qgis.core import *
from qgis.utils import plugins
from PyQt5.QtWidgets import *
from PyQt5.QtXml import *
from PyQt5.QtNetwork import QNetworkRequest
from qgis.core import QgsNetworkAccessManager
from math import *
import numpy
import glob  # MJS 11/02

from tuflow.toc.toc import tuflowqgis_find_layer

from .utm.utm import from_latlon, to_latlon
from .__version__ import version
import ctypes
from typing import Tuple, List
import matplotlib.gridspec as gridspec
from matplotlib.quiver import Quiver
from matplotlib.collections import PolyCollection
import xml.etree.ElementTree as ET
import colorsys
import locale
import codecs
from shutil import copyfile
# import processing
import requests
from collections import OrderedDict

from .tuflowqgis_styles import TF_Styles

try:
    from pathlib import Path
except ImportError:
    from pathlib_ import Path_ as Path
import sqlite3
from osgeo import ogr, gdal

from dataclasses import dataclass, field
try:
    import processing
except ImportError:
    pass
import webbrowser

# from .utils.map_layer import layer_name_from_data_source


# --------------------------------------------------------
#    tuflowqgis Utility Functions
# --------------------------------------------------------
# build_vers = build_vers
# build_type = 'release' #release / developmental

class NC_Error:
    NC_NOERR = 0
    NC_EBADID = -33
    NC_ENOTVAR = -49
    NC_EBADDIM = -46
    NC_EPERM = -37
    NC_ENFILE = -34
    NC_ENOMEM = -61
    NC_EHDFERR = -101
    NC_EDIMMETA = -106

    @staticmethod
    def message(error):
        error2message = {
            NC_Error.NC_NOERR: "No error",
            NC_Error.NC_EBADID: "Invalid ncid",
            NC_Error.NC_ENOTVAR: "Invalid Variable ID",
            NC_Error.NC_EBADDIM: "Invalid Dimension ID",
            NC_Error.NC_EPERM: "Attempting to create a netCDF file in a directory where you do not have permission to open files",
            NC_Error.NC_ENFILE: "Too many files open",
            NC_Error.NC_ENOMEM: "Out of memory",
            NC_Error.NC_EHDFERR: "HDF5 error. (NetCDF-4 files only.)",
            NC_Error.NC_EDIMMETA: "Error in netCDF-4 dimension metadata. (NetCDF-4 files only.)"
        }

        if error in error2message:
            return error2message[error]
        else:
            return "code {0}".format(error)


class NcDim():

    def __init__(self):
        self.id = -1
        self.name = ""
        self.len = 0

    def print_(self):
        return 'id: {0}, name: {1}, len: {2}'.format(self.id, self.name, self.len)


class NcVar():

    def __init__(self):
        self.id = -1
        self.name = ""
        self.type = -1
        self.nDims = 0
        self.dimIds = ()
        self.dimNames = ()
        self.dimLens = ()

    def print_(self):
        return 'id: {0}, name: {1}, type: {2}, nDim: {3}, dims: ({4})'.format(self.id, self.name, self.type, self.nDims,
                                                                              ', '.join(self.dimNames))


def get_latest_dev_plugin_version():
    try:
        from tuflow.ARR2016.downloader import Downloader
        downloader = Downloader('https://downloads.tuflow.com/Private_Download/QGIS_TUFLOW_Plugin/VERSION')
        downloader.download()
        if not downloader.ok():
            raise Exception()
        return downloader.data.strip()
    except Exception:
        pass
    return 'Unable to determine latest dev version'


def about(window):
    from .forms.ui_AboutDialog import Ui_AboutDialog
    class AboutDialog(QDialog, Ui_AboutDialog):
        def __init__(self, iface, plugin_version):
            QDialog.__init__(self)
            self.setupUi(self)
            self.iface = iface
            self.textEdit.setText('{0}\t: {1}\n'
                                  '{6}\t: {7}\n'
                                  '{2}\t\t: {3}\n'
                                  '{4}\t\t: {5}'
                                  .format("TUFLOW Plugin Version", plugin_version, "QGIS Version", Qgis.QGIS_VERSION,
                                          "Python Version", sys.version.split('(')[0].strip(),
                                          "Latest Plugin Dev Version", get_latest_dev_plugin_version()))
            self.pbClose.clicked.connect(self.accept)
            self.pbCopyText.clicked.connect(self.copy)

        def copy(self):
            clipboard = QApplication.clipboard()
            clipboard.setText(self.textEdit.toPlainText())

    build_type, build_vers = version()
    dialog = AboutDialog(window, build_vers)
    dialog.exec_()


def tuflowqgis_duplicate_file(qgis, layer, savename, keepform):
    if (layer == None) and (layer.type() != QgsMapLayer.VectorLayer):
        return "Invalid Vector Layer " + layer.name()

    # Create output file
    if len(savename) <= 0:
        return "Invalid output filename given"

    if QFile(savename).exists():
        if not QgsVectorFileWriter.deleteShapeFile(savename):
            return "Failure deleting existing shapefile: " + savename

    outfile = QgsVectorFileWriter(vectorFileName=savename, fileEncoding="System",
                                  fields=layer.dataProvider().fields(), geometryType=layer.wkbType(),
                                  srs=layer.dataProvider().sourceCrs(), driverName="ESRI Shapefile")

    if (outfile.hasError() != QgsVectorFileWriter.NoError):
        return "Failure creating output shapefile: " + unicode(outfile.errorMessage())

    # delete prj file and replace with empty prj - ensures it is exactly the same
    correct_prj = '{0}.prj'.format(os.path.splitext(layer.dataProvider().dataSourceUri())[0])
    new_prj = '{0}.prj'.format(os.path.splitext(savename)[0])
    try:
        copyfile(correct_prj, new_prj)
    except:
        pass

    # Iterate through each feature in the source layer
    feature_count = layer.dataProvider().featureCount()

    # feature = QgsFeature()
    # layer.dataProvider().select(layer.dataProvider().attributeIndexes())
    # layer.dataProvider().rewind()
    for f in layer.getFeatures():
        # while layer.dataProvider().nextFeature(feature):
        outfile.addFeature(f)

    del outfile

    # create qml from input layer
    if keepform:
        qml = savename.replace('.shp', '.qml')
        if QFile(qml).exists():
            return "QML File for output already exists."
        else:
            layer.saveNamedStyle(qml)

    return None


def duplicate_database(iface, layer, db, layername, incrementDatabase, incrementDatabaseLayers):
    if layer is None or not isinstance(layer, QgsVectorLayer):
        name = layer.name() if layer is not None else ''
        return 'Invalid vector layer {0}'.format(name)

    if incrementDatabase:
        # copy all layers to new database except incremented layer
        db_old = layer.dataProvider().dataSourceUri()
        db_old, layername_old = re.split(re.escape(r'|layername='), db_old, flags=re.IGNORECASE)
        dbLayer = QgsVectorLayer(db_old, 'db', 'ogr')
        if not dbLayer.isValid():
            return 'Error opening old database - not a valid layer: {0}'.format(db_old)
        for table in dbLayer.dataProvider().subLayers():
            tablename = table.split('!!::!!')[1]
            if tablename in incrementDatabaseLayers:
                # if tablename != layername_old:
                layername = incrementDatabaseLayers[tablename]
                options = QgsVectorFileWriter.SaveVectorOptions()
                if os.path.exists(db):
                    options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer
                else:
                    options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteFile
                options.layerName = layername
                options.driverName = 'GPKG'
                layer_temp = QgsVectorLayer('{0}|layername={1}'.format(db_old, tablename), 'temp', 'ogr')
                if not layer_temp.crs().isValid():
                    ds = ogr.GetDriverByName('GPKG').Open(db_old)
                    if ds is not None:
                        lyr = ds.GetLayer(tablename)
                        if lyr is not None:
                            crs = QgsCoordinateReferenceSystem(lyr.GetSpatialRef().ExportToWkt())
                            if crs.isValid():
                                layer_temp.setCrs(crs)
                            lyr = None
                        ds = None
                if not layer_temp.isSpatial():
                    if layer_temp.crs().isValid():
                        crs = layer_temp.crs().authid()
                        layer_temp = QgsVectorLayer('point?crs={0}'.format(crs), tablename, 'memory')
                try:
                    if Qgis.QGIS_VERSION_INT >= 31030:
                        error = QgsVectorFileWriter.writeAsVectorFormatV2(layer_temp, db,
                                                                          QgsCoordinateTransformContext(), options)
                        if error[0] != QgsVectorFileWriter.NoError:
                            return 'Error writing layer to database: {0} | {1}\n{2}'.format(db, tablename, error[1])
                    else:
                        err, msg = QgsVectorFileWriter.writeAsVectorFormat(layer_temp, db, 'SYSTEM', layer.crs(),
                                                                           options.driverName)
                        if err:
                            return 'Error writing layer to database: {0} | {1}\n{2}'.format(db, tablename, msg)
                except Exception as e:
                    return 'Error writing layer to database: {0} | {1}: {2}. Try updating QGIS version to fix this issue.'.format(
                        db, tablename, e)

    else:
        options = QgsVectorFileWriter.SaveVectorOptions()
        if os.path.exists(db):
            options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer
        else:
            options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteFile
        options.layerName = layername
        options.driverName = 'GPKG'
        try:
            if Qgis.QGIS_VERSION_INT >= 31030:
                error = QgsVectorFileWriter.writeAsVectorFormatV2(layer, db, QgsCoordinateTransformContext(), options)
                if error[0] != QgsVectorFileWriter.NoError:
                    return 'Error creating new layer: {0} | {1}\n{2}'.format(db, layername, error[1])
            else:
                err, msg = QgsVectorFileWriter.writeAsVectorFormat(layer, db, 'SYSTEM', layer.crs(),
                                                                   options.driverName)
                if err:
                    return 'Error writing layer to database: {0} | {1}\n{2}'.format(db, layername, msg)
        except Exception as e:
            return 'Error writing layer to database: {0} | {1}: {2}. Try updating QGIS version to fix this issue.'.format(
                db, layername, e)

    return None


def tuflowqgis_create_tf_dir(dialog, crs, basepath, engine, tutorial, gisFormat='SHP'):
    if crs is None:
        return "No CRS specified"

    if basepath is None:
        return "Invalid location specified"

    parent_folder_name = "TUFLOWFV" if engine == 'flexible mesh' else "TUFLOW"
    # linux case sensitive tuflow directory
    for p in os.walk(basepath):
        for d in p[1]:
            if d.lower() == parent_folder_name.lower():
                parent_folder_name = d
                break
        break

    # Create folders, ignore top level (e.g. model, as these are create when the subfolders are created)
    TUFLOW_Folders = ["bc_dbase",
                      "check",
                      "model{0}gis{0}empty".format(os.sep),
                      "results",
                      "runs{0}log".format(os.sep)]
    if engine == 'flexible mesh':
        TUFLOW_Folders.append("model{0}geo".format(os.sep))
    for x in TUFLOW_Folders:
        tmppath = os.path.join(basepath, parent_folder_name, x)
        if os.path.isdir(tmppath):
            print("Directory Exists")
        else:
            print("Creating Directory")
            os.makedirs(tmppath)

    # Write Projection.prj Create a file ('w' for write, creates if doesnt exit)
    prjname = os.path.join(basepath, parent_folder_name, "model", "gis", "projection.{0}".format(gisFormat.lower()))
    if len(prjname) <= 0:
        return "Error creating projection filename"

    if QFile(prjname).exists():
        # return "Projection file already exists: "+prjname
        reply = QMessageBox.question(dialog, "Create TUFLOW Empty Files", "Projection File Already Exists\n"
                                                                          "Do You Want To Overwrite The Existing File?",
                                     QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
        if reply == QMessageBox.Cancel:
            return "user cancelled"
        elif reply == QMessageBox.No:
            return
        # elif reply == QMessageBox.Yes:
        # 	fields = QgsFields()
        # 	fields.append( QgsField( "notes", QVariant.String ) )
        # 	outfile = QgsVectorFileWriter(prjname, "System", fields, 1, crs, "ESRI Shapefile")
        #
        # 	if outfile.hasError() != QgsVectorFileWriter.NoError:
        # 		return "Failure creating output shapefile: " + outfile.errorMessage()
    # else:
    # if gisFormat == 'SHP':
    # 	fields = QgsFields()
    # 	fields.append( QgsField( "notes", QVariant.String ) )
    # 	outfile = QgsVectorFileWriter(prjname, "System", fields, 1, crs, "ESRI Shapefile")
    #
    # 	if outfile.hasError() != QgsVectorFileWriter.NoError:
    # 		return "Failure creating output shapefile: " + outfile.errorMessage()
    # else:
    uri = "point?crs={0}&field=notes:string".format(crs.authid())
    layer = QgsVectorLayer(uri, 'projection', 'memory')
    options = QgsVectorFileWriter.SaveVectorOptions()
    if os.path.exists(prjname) and gisFormat == 'GPKG':
        options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer
    else:
        options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteFile
        if gisFormat == 'GPKG':
            out_lyr_uri = '{0}|layername={1}'.format(prjname, 'projection')
        else:
            out_lyr_uri = prjname
        open_layer = tuflowqgis_find_layer(out_lyr_uri, search_type='datasource')
        if open_layer is not None:
            QgsProject.instance().removeMapLayer(open_layer.id())
            open_layer = None
    options.layerName = 'projection'
    if gisFormat == 'GPKG':
        options.driverName = 'GPKG'
    else:
        options.driverName = 'ESRI Shapefile'

    if Qgis.QGIS_VERSION_INT >= 32000:
        outfile = QgsVectorFileWriter.writeAsVectorFormatV3(layer, prjname, QgsCoordinateTransformContext(),
                                                            options)
        if outfile[0] != QgsVectorFileWriter.NoError:
            msg = outfile[1]
            return msg
    elif Qgis.QGIS_VERSION_INT >= 31030:
        outfile = QgsVectorFileWriter.writeAsVectorFormatV2(layer, prjname, QgsCoordinateTransformContext(),
                                                            options)
        if outfile[0] != QgsVectorFileWriter.NoError:
            msg = outfile[1]
            return msg
    else:
        err, msg = QgsVectorFileWriter.writeAsVectorFormat(layer, prjname, 'SYSTEM', layer.crs(),
                                                           options.driverName, datasourceOptions=['OVERWRITE=YES'])
        if err != 0:
            return msg

    # del outfile

    # Write .tcf file
    ext = '.fvc' if engine == 'flexible mesh' else '.tcf'
    runfile = os.path.join(basepath, parent_folder_name, "runs", "Create_Empties{0}".format(ext))
    create_empty_tcf(runfile, gisFormat, tutorial)


def create_empty_tcf(tcf_path, gis_format, tutorial_model):
    with open(tcf_path, 'w') as f:
        f.write("GIS FORMAT == {0}\n".format(gis_format))
        if gis_format == 'SHP':
            f.write("SHP Projection == ..{0}model{0}gis{0}projection.prj\n".format(os.sep))
        else:
            f.write("GPKG Projection == ..{0}model{0}gis{0}projection.gpkg\n".format(os.sep))
        if tutorial_model:
            f.write("Tutorial Model == ON\n")
        f.write("Write Empty GIS Files == ..{0}model{0}gis{0}empty\n".format(os.sep))


def tuflowqgis_import_empty_tf(qgis, basepath, runID, empty_types, points, lines, regions, dialog,
                               databaseOption='separate', databaseLoc='', convert=False):
    if (len(empty_types) == 0):
        return "No Empty File specified"

    if (basepath == None):
        return "Invalid location specified"

    if ((not points) and (not lines) and (not regions)):
        return "No Geometry types selected"

    geom_type = []
    if (points):
        geom_type.append('_P')
    if (lines):
        geom_type.append('_L')
    if (regions):
        geom_type.append('_R')

    empty_folder = 'empty'
    for p in os.walk(os.path.dirname(basepath)):
        for d in p[1]:
            if d.lower() == empty_folder:
                empty_folder = d
                break
        break
    gis_folder = basepath.replace('/', os.sep).replace('{0}{1}'.format(os.sep, d), '')
    # Create folders, ignore top level (e.g. model, as these are create when the subfolders are created)
    i = 0
    yestoall = False
    for type in empty_types:
        for geom in geom_type:
            search_string = os.path.join(basepath,
                                         "{0}_empty_pts*".format(type.replace('_pts', ''))) if '_pts' in type else \
                os.path.join(basepath, "{0}_empty*".format(type))
            fpaths = glob.glob(search_string)
            if not fpaths:
                continue
            # fpath = os.path.join(basepath, "{0}_empty{1}.shp".format(type, geom))
            # fpath = fpaths[0]
            for fpath in fpaths:
                if re.findall(r'(\.gpkg)|({0}\.shp)$'.format(geom), fpath.strip(), re.IGNORECASE):
                    break
                # QMessageBox.information(qgis.mainWindow(),"Creating TUFLOW directory", fpath)
            if (os.path.isfile(fpath)):
                # isgpkg = os.path.splitext(fpath.lower())[1] == '.gpkg' \
                #          or (os.path.splitext(fpath.lower())[1] == '.shp' and convert)
                isgpkg = os.path.splitext(fpath.lower())[1] == '.gpkg'
                if isgpkg:
                    lyrname_ = '{0}{1}'.format(Path(fpath).with_suffix('').name, geom)
                    uri = '{0}|layername={1}'.format(fpath, lyrname_)
                    ext = '.gpkg'
                else:
                    uri = fpath
                    lyrname_ = Path(fpath).with_suffix('').name
                    if convert:
                        ext = '.gpkg'
                    else:
                        ext = '.shp'

                layer = QgsVectorLayer(uri, "tmp", "ogr")
                attributes = layer.dataProvider().fields()
                name = '{0}_{1}{2}{3}'.format(type, runID, geom, ext)
                savename = os.path.join(gis_folder, name)
                layername = os.path.splitext(os.path.basename(savename))[0]
                if isgpkg or convert:
                    if databaseOption == 'grouped':
                        name = '{0}_{1}{2}'.format(type, runID, os.path.splitext(fpath)[1])
                        savename = os.path.join(gis_folder, name)
                    elif databaseOption == 'one':
                        if databaseLoc:
                            savename = databaseLoc
                        if i == 0:
                            databaseLoc = savename  # if user doesn't specify, use the first database for the rest

                empty_file_ = fpath
                fpath = savename
                if isgpkg or convert:
                    uri = '{0}|layername={1}'.format(fpath, lyrname_)
                    ext = '.gpkg'
                else:
                    uri = fpath
                    ext = '.shp'
                if isgpkg or convert:
                    if Path(fpath).exists() and layername.lower() in [x.lower() for x in
                                                                      get_table_names(fpath)] and not yestoall:
                        answer = QMessageBox.question(dialog, 'Layer Already Exists',
                                                      '{0} already exists in {1}\nOverwrite existing layer?'.format(
                                                          layername, Path(fpath).name),
                                                      QMessageBox.Yes | QMessageBox.YesToAll | QMessageBox.No | QMessageBox.Cancel)
                        if answer == QMessageBox.Yes:
                            pass
                        elif answer == QMessageBox.YesToAll:
                            yestoall = True
                        elif answer == QMessageBox.No:
                            return 'pass'
                        elif answer == QMessageBox.Cancel:
                            return
                else:
                    if Path(fpath).exists() and not yestoall:
                        answer = QMessageBox.question(dialog, 'Layer Already Exists',
                                                      '{0} already exists\nOverwrite existing file?'.format(fpath),
                                                      QMessageBox.Yes | QMessageBox.YesToAll | QMessageBox.No | QMessageBox.Cancel)
                        if answer == QMessageBox.Yes:
                            pass
                        elif answer == QMessageBox.YesToAll:
                            yestoall = True
                        elif answer == QMessageBox.No:
                            return 'pass'
                        elif answer == QMessageBox.Cancel:
                            return

                # if QFile(savename).exists() and not isgpkg:
                # 	overwriteExisting = QMessageBox.question(dialog, "Import Empty",
                # 	                                         'Output file already exists\nOverwrite existing file?',
                # 	                                         QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
                # 	if overwriteExisting != QMessageBox.Yes:
                # 		# QMessageBox.critical(qgis.mainWindow(),"Info", ("File Exists: {0}".format(savename)))
                # 		#message = 'Unable to complete utility because file already exists'
                # 		return 1
                # outfile = QgsVectorFileWriter(QString(savename), QString("System"),
                if geom.upper() == '_P':
                    uri = 'point?crs={0}'.format(layer.crs().authid())
                elif geom.upper() == '_L':
                    uri = 'linestring?crs={0}'.format(layer.crs().authid())
                else:
                    uri = 'polygon?crs={0}'.format(layer.crs().authid())
                outlayer = QgsVectorLayer(uri, layername, 'memory')
                outlayer.dataProvider().addAttributes(attributes)
                outlayer.updateFields()
                # outfile = QgsVectorFileWriter(vectorFileName=savename, fileEncoding="System",
                # 	fields=layer.dataProvider().fields(), geometryType=layer.wkbType(), srs=layer.dataProvider().sourceCrs(), driverName="ESRI Shapefile")
                options = QgsVectorFileWriter.SaveVectorOptions()
                if os.path.exists(savename) and (isgpkg or convert):
                    options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer
                else:
                    options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteFile
                    if isgpkg or convert:
                        out_lyr_uri = '{0}|layername={1}'.format(savename, outlayer.name())
                    else:
                        out_lyr_uri = savename
                    open_layer = tuflowqgis_find_layer(out_lyr_uri, search_type='datasource')
                    if open_layer is not None:
                        QgsProject.instance().removeMapLayer(open_layer.id())
                        open_layer = None
                options.layerName = layername
                if isgpkg or convert:
                    options.driverName = 'GPKG'
                else:
                    options.driverName = 'ESRI Shapefile'

                try:
                    if Qgis.QGIS_VERSION_INT >= 31030:
                        outfile = QgsVectorFileWriter.writeAsVectorFormatV2(outlayer, savename,
                                                                            QgsCoordinateTransformContext(), options)
                    else:
                        err, msg = QgsVectorFileWriter.writeAsVectorFormat(outlayer, savename, 'SYSTEM', outlayer.crs(),
                                                                           options.driverName,
                                                                           datasourceOptions=['OVERWRITE=YES'])
                except AttributeError:
                    QMessageBox.critical(qgis.mainWindow(), 'Save new file',
                                         'Error creating new file. Try upgrading QGIS version to fix this error.')
                    return
                except Exception as e:
                    QMessageBox.critical(qgis.mainWindow(), 'Save new file', 'Error creating new file: {0}'.format(e))
                    return

                if Qgis.QGIS_VERSION_INT >= 31030:
                    if outfile[0] != QgsVectorFileWriter.NoError:
                        QMessageBox.critical(qgis.mainWindow(), "Info", ("Error Creating: {0}\n{1}".format(*outfile)))
                        continue
                else:
                    if err:
                        QMessageBox.critical(qgis.mainWindow(), "Info",
                                             ("Error Creating: {0}\n{1}".format(savename, msg)))
                        continue
                # del outfile

                # delete prj file and replace with empty prj - ensures it is exactly the same
                if not isgpkg and not convert:
                    correct_prj = '{0}.prj'.format(os.path.splitext(empty_file_)[0])
                    new_prj = '{0}.prj'.format(os.path.splitext(savename)[0])
                    try:
                        copyfile(correct_prj, new_prj)
                    except Exception as e:
                        pass

                if isgpkg or convert:
                    uri = '{0}|layername={1}'.format(savename, layername)
                else:
                    uri = savename
                open_layer = tuflowqgis_find_layer(layername)
                if open_layer is None or open_layer.dataProvider().dataSourceUri().lower() != uri.lower():
                    qgis.addVectorLayer(uri, layername, "ogr")

                i += 1

    return None


def tuflowqgis_get_selected_IDs(qgis, layer):
    QMessageBox.information(qgis.mainWindow(), "Info", "Entering tuflowqgis_get_selected_IDs")
    IDs = []
    if (layer == None) and (layer.type() != QgsMapLayer.VectorLayer):
        return None, "Invalid Vector Layer " + layer.name()

    dataprovider = layer.dataProvider()
    idx = dataprovider.fieldNameIndex('ID')
    QMessageBox.information(qgis.mainWindow(), "IDX", str(idx))
    if (idx == -1):
        QMessageBox.critical(qgis.mainWindow(), "Info", "ID field not found in current layer")
        return None, "ID field not found in current layer"

    for feature in layer.selectedFeatures():
        id = feature.attributeMap()[idx].toString()
        IDs.append(id)
    return IDs, None


def check_python_lib(qgis):
    error = False
    py_modules = []
    try:
        py_modules.append('numpy')
        import numpy
    except:
        error = True
        QMessageBox.critical(qgis.mainWindow(), "Error", "python library 'numpy' not installed.")
    try:
        py_modules.append('csv')
        import csv
    except:
        error = True
        QMessageBox.critical(qgis.mainWindow(), "Error", "python library 'csv' not installed.")
    try:
        py_modules.append('matplotlib')
        import matplotlib
    except:
        error = True
        QMessageBox.critical(qgis.mainWindow(), "Error", "python library 'matplotlib' not installed.")
    try:
        py_modules.append('PyQt5')
        import PyQt5
    except:
        error = True
        QMessageBox.critical(qgis.mainWindow(), "Error", "python library 'PyQt4' not installed.")
    try:
        py_modules.append('osgeo.ogr')
        import osgeo.ogr as ogr
    except:
        error = True
        QMessageBox.critical(qgis.mainWindow(), "Error", "python library 'osgeo.ogr' not installed.")
    try:
        py_modules.append('glob')
        import glob
    except:
        error = True
        QMessageBox.critical(qgis.mainWindow(), "Error", "python library 'glob' not installed.")
    try:
        py_modules.append('os')
        import os
    except:
        error = True
        QMessageBox.critical(qgis.mainWindow(), "Error", "python library 'os' not installed.")
    msg = 'Modules tested: \n'
    for mod in py_modules:
        msg = msg + mod + '\n'
    QMessageBox.information(qgis.mainWindow(), "Information", msg)

    if error:
        return True
    else:
        return None


class RunTuflow(QObject):

    error = pyqtSignal(str)
    finished = pyqtSignal(str)

    def __init__(self, tfexe, runfile, capture_output, callback):
        super().__init__()
        self.capture_output = capture_output
        self.callback = callback
        self.tfexe = tfexe
        self.runfile = runfile
        self.isfv = Path(tfexe).stem.lower() == 'tuflowfv'
        self.args = [tfexe, '-b', runfile] if not self.isfv else [tfexe, runfile]
        self.proc = None
        self.timer = None
        self.stdout = []
        self.BUFFER_SIZE = 4096

    def run(self):
        if not os.path.exists(self.tfexe):
            self.error.emit("TUFLOW exe not found: {0}".format(self.tfexe))
            return
        if not os.path.exists(self.runfile):
            self.error.emit("TUFLOW Control File (tcf, fvc) not found: {0}".format(self.runfile))
            return
        cwd = os.path.dirname(self.runfile) if self.isfv else None
        try:
            if self.capture_output:
                self.setup_timer()
                self.timer.start()
                self.proc = subprocess.Popen(self.args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                             creationflags=subprocess.CREATE_NO_WINDOW, cwd=cwd)
            else:
                self.proc = subprocess.Popen(self.args, cwd=cwd)
        except:
            self.error.emit("Unexpected error occurred starting TUFLOW\nargs: {0}".format(self.args))
            self.destroy()

    def setup_timer(self):
        self.timer = QTimer()
        self.timer.setInterval(1000)
        self.timer.setSingleShot(False)
        self.timer.timeout.connect(self.check_proc)

    def check_proc(self):
        stdout = self.proc.stdout.read(self.BUFFER_SIZE)
        self.stdout.append(stdout)
        if self.proc.poll() is not None:
            if self.callback:
                try:
                    _ = self.callback(True)
                except:
                    pass
            text = b''.join(self.stdout).decode('utf-8')
            self.finished.emit(text)
            self.destroy()
        else:
            if self.callback:
                try:
                    kill = self.callback(False)
                except:
                    kill = True
                if kill:
                    self.proc.terminate()
                    self.destroy()

    def terminate(self):
        self.destroy()

    def destroy(self):
        if self.timer is not None:
            self.timer.stop()
            self.timer.deleteLater()
        if self.proc is not None:
            self.proc.terminate()
            self.proc = None



def run_tuflow(qgis, tfexe, runfile):
    # QMessageBox.Information(qgis.mainWindow(),"debug", "Running TUFLOW - tcf: "+tcf)
    try:
        from subprocess import Popen
        dir, ext = os.path.splitext(runfile)
        dir = os.path.dirname(dir)
        fname = os.path.basename(runfile)
        tfarg = [tfexe, '-b',runfile] if ext[-1] == '.tcf' else [tfexe, runfile]
        if ext.lower() == ".tcf":
            tfarg = [tfexe, '-b', runfile]
        elif ext.lower() == '.fvc':
            tfarg = [tfexe, fname]
            os.chdir(dir)
        else:
            return "Error input file extension is not TCF or FVC"
        # tfarg = [tfexe, '-b', runfile]
        tf_proc = Popen(tfarg)
        # if tf_proc.poll() is not None:
        #     _, stderr = tf_proc.communicate()
        #     return str(stderr)
    # tf_proc = Popen(tfarg, cwd=os.path.dirname(runfile))
    except:
        return "Error occurred starting TUFLOW"
    # QMessageBox.Information(qgis.mainWindow(),"debug", "TUFLOW started")
    return None


# def config_set(project, tuflow_folder, tfexe, projection):
#     message = None
#     try:
#         f = open(config_file, 'w')
#         f.write('TUFLOW Folder ==' + tuflow_folder + '\n')
#         f.write('TUFLOW Exe ==' + tfexe + '\n')
#         f.write('PROJECTION ==' + proj + '\n')
#         f.flush()
#         f.close()
#     except:
#         message = "Unable to write TUFLOW config file: " + config_file
#
#     return message


def extract_all_points(qgis, layer, col):
    # QMessageBox.Information(qgis.mainWindow(),"debug", "starting to extract points")
    try:
        iter = layer.getFeatures()
        npt = 0
        x = []
        y = []
        z = []
        for feature in iter:
            npt = npt + 1
            geom = feat.geometry()
            # QMessageBox.Information(qgis.mainWindow(),"debug", "x = "+str(geom.x())+", y = "+str(geom.y()))
            x.append(geom.x())
            y.append(geom.y())
            zt = feature.attributeMap()[col]
            # QMessageBox.Information(qgis.mainWindow(),"debug", "z = "+str(zt))
            z.append(zt)
        return x, y, z, message
    except:
        return None, None, None, "Error extracting point data"


def get_file_ext(fname):
    try:
        ind = fname.find('|')
        if (ind > 0):
            fname = fname[0:ind]
    except:
        return None, None, "Error trimming filename"
    try:
        ind = fname.rfind('.')
        if (ind > 0):
            fext = fname[ind + 1:]
            fext = fext.upper()
            fname_noext = fname[0:ind]
            return fext, fname_noext, None
        else:
            return None, None, "Could not find . in filename"
    except:
        return None, None, "Error trimming filename"


def load_project(project):
    message = None
    try:
        tffolder = project.readEntry("configure_tuflow", "folder", "Not yet set")[0]
    except:
        message = "Error - Reading from project file."
        QMessageBox.information(qgis.mainWindow(), "Information", message)

    try:
        tfexe = project.readEntry("configure_tuflow", "exe", "Not yet set")[0]
    except:
        message = "Error - Reading from project file."
        QMessageBox.information(qgis.mainWindow(), "Information", message)

    try:
        tf_prj = project.readEntry("configure_tuflow", "projection", "Undefined")[0]
    except:
        message = "Error - Reading from project file."
        QMessageBox.information(qgis.mainWindow(), "Information", message)

    error = False
    if (tffolder == "Not yet set"):
        error = True
        QMessageBox.information(qgis.mainWindow(), "Information", "Not set tffolder")
    if (tfexe == "Not yet set"):
        error = True
        QMessageBox.information(qgis.mainWindow(), "Information", "Not set tfexe")
    if (tf_prj == "Undefined"):
        error = True
        QMessageBox.information(qgis.mainWindow(), "Information", "tf_prj")
    if error:
        message = "Project does not appear to be configured.\nPlease run TUFLOW >> Editing >> Configure Project from the plugin menu."

    return message, tffolder, tfexe, tf_prj


#  tuflowqgis_import_check_tf added MJS 11/02
def tuflowqgis_import_check_tf(qgis, basepath, runID, showchecks):
    # import check file styles using class
    tf_styles = TF_Styles()
    error, message = tf_styles.Load()
    if error:
        QMessageBox.critical(qgis.mainWindow(), "Error", message)
        return message

    if basepath is None:
        return "Invalid location specified"

    # Get all the check files in the given directory
    check_files = glob.glob(basepath + '/*' + runID + '*.shp') + glob.glob(basepath + '/*' + runID + '*.mif') + \
                  glob.glob(basepath + '/*' + runID + '*.SHP') + glob.glob(basepath + '/*' + runID + '*.MIF') + \
                  glob.glob(basepath + '/*' + runID + '*.gpkg')

    check_files_lower = [x.lower() for x in check_files]
    check_files_temp = []
    check_files_lower_temp = []
    for i, cf in enumerate(check_files_lower):
        if os.path.splitext(cf)[1].lower() == '.gpkg':
            for lyr_name in get_table_names(cf):
                uri = '{0}|layername={1}'.format(check_files[i], lyr_name)
                if uri.lower() not in check_files_lower_temp:
                    check_files_lower_temp.append(uri.lower())
                    check_files_temp.append(uri)
        else:
            if cf not in check_files_lower_temp:
                check_files_lower_temp.append(cf)
                check_files_temp.append(check_files[i])
    check_files = check_files_temp[:]

    if len(check_files) > 100:
        QMessageBox.critical(qgis.mainWindow(), "Info", (
            "You have selected over 100 check files. You can use the RunID to reduce this selection."))
        return "Too many check files selected"

    # if not check_files:
    #	check_files = glob.glob(basepath +  '\*'+ runID +'*.mif')
    #	if len(check_files) > 0:
    #		return ".MIF Files are not supported, only .SHP files."
    #	else:
    #		return "No check files found for this RunID in this location."

    # Get the legend interface (qgis.legendInterface() no longer supported)
    legint = QgsProject.instance().layerTreeRoot()

    # Add each layer to QGIS and style
    if not check_files:
        return "No check files found to import"
    for chk in check_files:
        if re.findall(re.escape(r'.gpkg|layername='), chk, flags=re.IGNORECASE):
            fname = re.split(re.escape(r'.gpkg|layername='), chk, flags=re.IGNORECASE)[-1]
        else:
            pfft, fname = os.path.split(chk)
            fname = fname[:-4]
        layer = qgis.addVectorLayer(chk, fname, "ogr")
        if layer is None:  # probably a mif file with 2 geometry types, have to redefine layer object
            for layer_name, layer_object in QgsProject.instance().mapLayers().items():
                if fname in layer_name:
                    layer = layer_object
        renderer = region_renderer(layer)
        if renderer:  # if the file requires a attribute based rendered (e.g. BC_Name for a _sac_check_R)
            layer.setRenderer(renderer)
            layer.triggerRepaint()
        else:  # use .qml style using tf_styles
            error, message, slyr = tf_styles.Find(fname, layer)  # use tuflow styles to find longest matching
            if error:
                QMessageBox.critical(qgis.mainWindow(), "ERROR", message)
                return message
            if slyr:  # style layer found:
                layer.loadNamedStyle(slyr)
                # if os.path.split(slyr)[1][:-4] == '_zpt_check':
                #	legint.setLayerVisible(layer, False)   # Switch off by default
                # elif '_uvpt_check' in fname or '_grd_check' in fname:
                #	legint.setLayerVisible(layer, False)
                # if not showchecks:
                #	legint.setLayerVisible(layer, False)
                for item in legint.children():
                    if 'zpt check' in item.name().lower() or 'uvpt check' in item.name().lower() or 'grd check' in item.name().lower() or \
                            'zpt_check' in item.name().lower() or 'uvpt_check' in item.name().lower() or 'grd_check' in item.name().lower():
                        item.setItemVisibilityChecked(False)
                    elif not showchecks:
                        item.setItemVisibilityChecked(False)

    message = None  # normal return
    return message


#  region_renderer added MJS 11/02
def region_renderer(layer):
    from random import randrange
    registry = QgsSymbolLayerRegistry()
    symbol_layer = None
    symbol_layer2 = None
    renderer = None
    symbol = None

    # check if layer needs a renderer
    # fsource = layer.source() #includes full filepath and extension
    # fname = os.path.split(fsource)[1][:-4] #without extension

    if re.findall(re.escape(r'.gpkg|layername='), layer.dataProvider().dataSourceUri(), flags=re.IGNORECASE):
        fname = re.split(re.escape(r'.gpkg|layername='), layer.dataProvider().dataSourceUri(), flags=re.IGNORECASE)[1]
    else:
        fname = os.path.splitext(os.path.basename(layer.dataProvider().dataSourceUri()))[0]
    if layer.dataProvider().name() == 'memory':
        fname = layer.name()

    fname = fname.lower()

    if '_bcc_check_r' in fname.lower():
        field_name = 'Source'
    elif '_1d_to_2d_check_R' in fname.lower():
        field_name = 'Primary_No'
    elif '_2d_to_2d_r' in fname.lower():
        field_name = 'Primary_No'
    elif '_sac_check_r' in fname.lower():
        field_name = 'BC_Name'
    elif '2d_bc' in fname.lower() or '2d_mat' in fname.lower() or '2d_soil' in fname.lower() or '1d_bc' in fname.lower():
        i = 0
        for field in layer.fields():
            if field.name() == 'fid':
                continue
            if i == 0:
                field_name = field.name()
            i += 1
    elif '1d_nwk' in fname.lower() or '1d_nwkb' in fname.lower() or '1d_nwke' in fname.lower() or '1d_mh' in fname.lower() or '1d_pit' in fname.lower() or \
            '1d_nd' in fname.lower():
        i = 0
        field_name = None
        for field in layer.fields():
            if field.name() == 'fid':
                continue
            if i == 1:
                field_name = field.name()
            i += 1
    # elif re.findall(r'_FM_PLOT_[PLR]', fname, flags=re.IGNORECASE):
    elif re.findall(r'((_FM_PLOT_[PLR])|_raw_(nodes|links)_)', fname, flags=re.IGNORECASE):
        try:
            field_names = [x.name() for x in [f for f in layer.getFeatures()][0].fields()]
            upstrm_type = 'Upstrm_Type' if 'Upstrm_Type' in field_names else 'Upstrm_Typ'
        except (IndexError, AttributeError):
            upstrm_type = 'Upstrm_Type'
        if layer.geometryType() == QgsWkbTypes.LineGeometry:
            field_name = upstrm_type
        elif layer.geometryType() == QgsWkbTypes.PointGeometry:
            field_name = 'Unit_Type'
    elif '2d_qnl' in fname.lower():
        field_name = layer.fields()[1].name() if '.gpkg|layername=' in layer.dataProvider().dataSourceUri() else \
            layer.fields()[0].name()
    else:  # render not needed
        return None

    # Thankyou Detlev  @ http://gis.stackexchange.com/questions/175068/apply-symbol-to-each-feature-categorized-symbol

    # get unique values
    vals = layer.dataProvider().fieldNameIndex(field_name)
    unique_values = layer.dataProvider().uniqueValues(vals)
    # QgsMessageLog.logMessage('These values have been identified: ' + vals, "TUFLOW")
    if re.findall(r'((_FM_PLOT_[PLR])|_raw_(nodes|links)_)', fname,
                  flags=re.IGNORECASE) and layer.geometryType() == QgsWkbTypes.LineGeometry:
        unique_values2 = [x.upper() for x in unique_values if
                          x.upper() != 'SPILL' and x.upper() != 'JUNCTION' and x.upper() != 'INTERPOLATE']
        try:
            field_names = [x.name() for x in [f for f in layer.getFeatures()][0].fields()]
            upstrm_type = 'Upstrm_Type' if 'Upstrm_Type' in field_names else 'Upstrm_Typ'
            dnstrm_type = 'Dnstrm_Type' if 'Upstrm_Type' in field_names else 'Dnstrm_Typ'
        except (IndexError, AttributeError):
            upstrm_type = 'Upstrm_Type'
            dnstrm_type = 'Dnstrm_Type'
        spillExists = 'SPILL' in [x.upper() for x in unique_values]
        junctExists = 'JUNCTION' in [x.upper() for x in unique_values]
        intpExists = 'INTERPOLATE' in [x.upper() for x in unique_values]
        expressions = [
            f'"{upstrm_type}" ILIKE \'{x}\' and {upstrm_type} NOT ILIKE \'%BDY%\' and {dnstrm_type} NOT ILIKE \'%BDY%\''
            for x in unique_values2]
        if spillExists:
            expressions = [f'{x} and "{dnstrm_type}" NOT ILIKE \'SPILL\'' for x in expressions]
        if junctExists:
            expressions = [f'{x} and "{dnstrm_type}" NOT ILIKE \'JUNCTION\'' for x in expressions]
        if intpExists:
            expressions = [f'{x} and "{dnstrm_type}" NOT ILIKE \'INTERPOLATE\'' for x in expressions]
        expressions.insert(0, f'"{upstrm_type}" ILIKE \'%BDY%\' or "{dnstrm_type}" ILIKE \'%BDY%\'')
        # if spillExists and junctExists:
        # 	expressions = [f'"Upstrm_Type" ILIKE \'{x}\' and  "Dnstrm_Type" NOT ILIKE \'SPILL\'' \
        # 	               f' and "Dnstrm_Type" NOT ILIKE \'JUNCTION\'' for x in unique_values2]
        # elif spillExists:
        # 	expressions = [f'"Upstrm_Type" ILIKE \'{x}\' and  "Dnstrm_Type" NOT ILIKE \'SPILL\'' for x in unique_values2]
        # elif junctExists:
        # 	expressions = [f'"Upstrm_Type" ILIKE \'{x}\' and  "Dnstrm_Type" NOT ILIKE \'JUNCTION\'' for x in unique_values2]
        # else:
        # 	expressions = [f'"Upstrm_Type" ILIKE \'{x}\'' for x in unique_values2]
        symbol = QgsSymbol.defaultSymbol(layer.geometryType())
        renderer = QgsRuleBasedRenderer(symbol)
        root_rule = renderer.rootRule()
        for j, exp in enumerate(expressions):
            i = j - 1
            layer_style = {}
            color = '%d, %d, %d' % (randrange(0, 256), randrange(0, 256), randrange(0, 256))
            layer_style['color'] = color
            layer_style['outline'] = '#000000'
            symbol = QgsSymbol.defaultSymbol(layer.geometryType())
            rule = root_rule.children()[0].clone()
            if j == 0:
                rule.setLabel('BDY')
                rule.setFilterExpression(exp)
                symbol_layer = QgsSimpleLineSymbolLayer.create(layer_style)
                symbol_layer.setWidth(0.5)
                symbol_layer.setStrokeColor(QColor(227, 26, 28))
                symbol_layer.setPenStyle(Qt.DashLine)
                symbol_layer2 = None
            else:
                # rule.setLabel(unique_values2[i-1])
                rule.setLabel(unique_values2[i])
                rule.setFilterExpression(exp)
                if unique_values2[i].lower() == 'lateral':
                    symbol_layer = QgsSimpleLineSymbolLayer.create(layer_style)
                    symbol_layer.setWidth(0.25)
                    color = QColor(randrange(0, 256), randrange(0, 256), randrange(0, 256))
                    symbol_layer.setStrokeColor(color)
                    symbol_layer.setPenStyle(Qt.DotLine)
                    symbol_layer2 = None
                elif 'bdy' in unique_values2[i].lower():
                    continue
                # symbol_layer = QgsSimpleLineSymbolLayer.create(layer_style)
                # symbol_layer.setWidth(0.5)
                # symbol_layer.setStrokeColor(QColor(227, 26, 28))
                # symbol_layer.setPenStyle(Qt.DashLine)
                # symbol_layer2 = None
                else:
                    symbol_layer = QgsSimpleLineSymbolLayer.create(layer_style)
                    symbol_layer.setWidth(0.5)
                    symbol_layer2 = QgsMarkerLineSymbolLayer.create({'placement': 'lastvertex'})
                    layer_style['color_border'] = color
                    markerSymbol = QgsSimpleMarkerSymbolLayer.create(layer_style)
                    markerSymbol.setShape(QgsSimpleMarkerSymbolLayerBase.ArrowHeadFilled)
                    markerSymbol.setSize(4)
                    marker = QgsMarkerSymbol()
                    marker.changeSymbolLayer(0, markerSymbol)
                    symbol_layer2.setSubSymbol(marker)
                if symbol_layer is not None:
                    symbol.changeSymbolLayer(0, symbol_layer)
                    if symbol_layer2 is not None:
                        symbol.appendSymbolLayer(symbol_layer2)
            rule.setSymbol(symbol)
            root_rule.appendChild(rule)
        if spillExists:
            symbol = QgsSymbol.defaultSymbol(layer.geometryType())
            exp = f'"{upstrm_type}" ILIKE \'SPILL\' or  "{dnstrm_type}" ILIKE \'SPILL\''
            rule = root_rule.children()[0].clone()
            rule.setLabel('SPILL')
            rule.setFilterExpression(exp)
            symbol_layer = QgsSimpleLineSymbolLayer.create(layer_style)
            symbol_layer.setWidth(0.25)
            color = QColor(randrange(0, 256), randrange(0, 256), randrange(0, 256))
            symbol_layer.setStrokeColor(color)
            symbol_layer.setPenStyle(Qt.DotLine)
            symbol_layer2 = None
            if symbol_layer is not None:
                symbol.changeSymbolLayer(0, symbol_layer)
                if symbol_layer2 is not None:
                    symbol.appendSymbolLayer(symbol_layer2)
            rule.setSymbol(symbol)
            root_rule.appendChild(rule)
        if junctExists:
            symbol = QgsSymbol.defaultSymbol(layer.geometryType())
            exp = f'("{upstrm_type}" ILIKE \'JUNCTION\' or "{dnstrm_type}" ILIKE \'JUNCTION\') AND "{upstrm_type}" NOT ILIKE \'SPILL\' AND "{dnstrm_type}" NOT ILIKE \'SPILL\''
            rule = root_rule.children()[0].clone()
            rule.setLabel('CONN')
            rule.setFilterExpression(exp)
            symbol_layer = QgsSimpleLineSymbolLayer.create(layer_style)
            symbol_layer.setWidth(0.25)
            color = QColor(35, 35, 35)
            symbol_layer.setColor(color)
            symbol_layer2 = None
            if symbol_layer is not None:
                symbol.changeSymbolLayer(0, symbol_layer)
                if symbol_layer2 is not None:
                    symbol.appendSymbolLayer(symbol_layer2)
            rule.setSymbol(symbol)
            root_rule.appendChild(rule)
        if intpExists:
            layer_style = {}
            color = '%d, %d, %d' % (randrange(0, 256), randrange(0, 256), randrange(0, 256))
            layer_style['color'] = color
            layer_style['outline'] = '#000000'
            symbol = QgsSymbol.defaultSymbol(layer.geometryType())
            exp = f'("{upstrm_type}" ILIKE \'INTERPOLATE\' or "{dnstrm_type}" ILIKE \'INTERPOLATE\') AND "{upstrm_type}" NOT ILIKE \'SPILL\' AND "{dnstrm_type}" NOT ILIKE \'SPILL\''
            rule = root_rule.children()[0].clone()
            rule.setLabel('INTERPOLATE')
            rule.setFilterExpression(exp)
            symbol_layer = QgsSimpleLineSymbolLayer.create(layer_style)
            symbol_layer.setWidth(0.5)
            symbol_layer2 = QgsMarkerLineSymbolLayer.create({'placement': 'lastvertex'})
            layer_style['color_border'] = color
            markerSymbol = QgsSimpleMarkerSymbolLayer.create(layer_style)
            markerSymbol.setShape(QgsSimpleMarkerSymbolLayerBase.ArrowHeadFilled)
            markerSymbol.setSize(4)
            marker = QgsMarkerSymbol()
            marker.changeSymbolLayer(0, markerSymbol)
            symbol_layer2.setSubSymbol(marker)
            if symbol_layer is not None:
                symbol.changeSymbolLayer(0, symbol_layer)
                if symbol_layer2 is not None:
                    symbol.appendSymbolLayer(symbol_layer2)
            rule.setSymbol(symbol)
            root_rule.appendChild(rule)
        root_rule.removeChildAt(0)
        return renderer
    elif field_name is None and '1d_nwk' in fname.lower():
        color = '%d, %d, %d' % (randrange(0, 256), randrange(0, 256), randrange(0, 256))
        layer_style = {}
        layer_style['color'] = color
        layer_style['outline'] = '#000000'
        symbol = QgsSymbol.defaultSymbol(layer.geometryType())
        symbol_layer = QgsSimpleFillSymbolLayer.create(layer_style)
        if layer.geometryType() == QgsWkbTypes.LineGeometry:
            symbol_layer = QgsSimpleLineSymbolLayer.create(layer_style)
            symbol_layer.setWidth(1)
            symbol_layer2 = QgsMarkerLineSymbolLayer.create({'placement': 'lastvertex'})
            layer_style['color_border'] = color
            markerSymbol = QgsSimpleMarkerSymbolLayer.create(layer_style)
            markerSymbol.setShape(QgsSimpleMarkerSymbolLayerBase.ArrowHeadFilled)
            markerSymbol.setSize(5)
            marker = QgsMarkerSymbol()
            marker.changeSymbolLayer(0, markerSymbol)
            symbol_layer2.setSubSymbol(marker)
        elif layer.geometryType() == QgsWkbTypes.PointGeometry:
            symbol_layer = QgsSimpleMarkerSymbolLayer.create(layer_style)
            symbol_layer.setSize(1.5)
            symbol_layer.setShape(QgsSimpleMarkerSymbolLayerBase.Square)
        if symbol_layer is not None:
            symbol.changeSymbolLayer(0, symbol_layer)
            if symbol_layer2 is not None:
                symbol.appendSymbolLayer(symbol_layer2)
        return QgsSingleSymbolRenderer(symbol)
    else:
        # define categories
        categories = []
        for unique_value in unique_values:
            # initialize the default symbol for this geometry type
            symbol = QgsSymbol.defaultSymbol(layer.geometryType())

            # configure a symbol layer
            layer_style = {}
            color = '%d, %d, %d' % (randrange(0, 256), randrange(0, 256), randrange(0, 256))
            layer_style['color'] = color
            layer_style['outline'] = '#000000'
            symbol_layer = QgsSimpleFillSymbolLayer.create(layer_style)
            if '2d_bc' in fname.lower():
                if layer.geometryType() == QgsWkbTypes.LineGeometry:
                    # QMessageBox.information(qgis.mainWindow(), "DEBUG", 'line 446')
                    symbol_layer = QgsSimpleLineSymbolLayer.create(layer_style)
                    symbol_layer.setWidth(1)
                elif layer.geometryType() == QgsWkbTypes.PointGeometry:
                    symbol_layer = QgsSimpleMarkerSymbolLayer.create(layer_style)
                    symbol_layer.setSize(2)
                    symbol_layer.setShape(QgsSimpleMarkerSymbolLayerBase.Circle)
            elif '1d_nwk' in fname.lower() or '1d_nwkb' in fname.lower() or '1d_nwke' in fname.lower() or '1d_pit' in fname.lower() or '1d_nd' in fname.lower():
                if layer.geometryType() == QgsWkbTypes.LineGeometry:
                    # QMessageBox.information(qgis.mainWindow(), "DEBUG", 'line 446')
                    symbol_layer = QgsSimpleLineSymbolLayer.create(layer_style)
                    symbol_layer.setWidth(1)
                    symbol_layer2 = QgsMarkerLineSymbolLayer.create({'placement': 'lastvertex'})
                    layer_style['color_border'] = color
                    markerSymbol = QgsSimpleMarkerSymbolLayer.create(layer_style)
                    markerSymbol.setShape(QgsSimpleMarkerSymbolLayerBase.ArrowHeadFilled)
                    markerSymbol.setSize(5)
                    marker = QgsMarkerSymbol()
                    marker.changeSymbolLayer(0, markerSymbol)
                    symbol_layer2.setSubSymbol(marker)
                # symbol_layer.changeSymbolLayer(0, symbol_layer2)
                # markerMeta = registry.symbolLayerMetadata("MarkerLine")
                # markerLayer = markerMeta.createSymbolLayer({'width': '0.26', 'color': color, 'rotate': '1', 'placement': 'lastvertex'})
                # subSymbol = markerLayer.subSymbol()
                # subSymbol.deleteSymbolLayer(0)
                # triangle = registry.symbolLayerMetadata("SimpleMarker").createSymbolLayer({'name': 'filled_arrowhead', 'color': color, 'color_border': color, 'offset': '0,0', 'size': '4', 'angle': '0'})
                # subSymbol.appendSymbolLayer(triangle)
                elif layer.geometryType() == QgsWkbTypes.PointGeometry:
                    symbol_layer = QgsSimpleMarkerSymbolLayer.create(layer_style)
                    symbol_layer.setSize(1.5)
                    if unique_value == 'NODE':
                        symbol_layer.setShape(QgsSimpleMarkerSymbolLayerBase.Circle)
                    else:
                        symbol_layer.setShape(QgsSimpleMarkerSymbolLayerBase.Square)
            elif '2d_qnl' in fname.lower():
                symbol_layer = QgsSimpleFillSymbolLayer.create(layer_style)
                layer.setOpacity(0.25)
            elif '2d_mat' in fname.lower():
                symbol_layer = QgsSimpleFillSymbolLayer.create(layer_style)
                layer.setOpacity(0.25)
            elif '2d_soil' in fname.lower():
                symbol_layer = QgsSimpleFillSymbolLayer.create(layer_style)
                layer.setOpacity(0.25)
            elif '1d_bc' in fname.lower():
                if layer.geometryType() == QgsWkbTypes.PointGeometry:
                    symbol_layer = QgsSimpleMarkerSymbolLayer.create(layer_style)
                    symbol_layer.setSize(1.5)
                    symbol_layer.setShape(QgsSimpleMarkerSymbolLayerBase.Circle)
                else:
                    layer_style['style'] = 'no'
                    symbol_layer = QgsSimpleFillSymbolLayer.create(layer_style)
                    color = QColor(randrange(0, 256), randrange(0, 256), randrange(0, 256))
                    symbol_layer.setStrokeColor(color)
                    symbol_layer.setStrokeWidth(1)
            elif re.findall(r'((_FM_PLOT_[PLR])|_raw_(nodes|links)_)', fname, flags=re.IGNORECASE):
                if layer.geometryType() == QgsWkbTypes.LineGeometry:
                    # shouldn't get here anymore
                    if unique_value.lower() == 'lateral' or unique_value.lower() == 'spill':
                        symbol_layer = QgsSimpleLineSymbolLayer.create(layer_style)
                        symbol_layer.setWidth(0.25)
                        color = QColor(randrange(0, 256), randrange(0, 256), randrange(0, 256))
                        symbol_layer.setStrokeColor(color)
                        symbol_layer.setPenStyle(Qt.DotLine)
                        symbol_layer2 = None
                    elif 'bdy' in unique_value.lower():
                        symbol_layer = QgsSimpleLineSymbolLayer.create(layer_style)
                        symbol_layer.setWidth(0.5)
                        symbol_layer.setStrokeColor(QColor(227, 26, 28))
                        symbol_layer.setPenStyle(Qt.DashLine)
                        symbol_layer2 = None
                    else:
                        symbol_layer = QgsSimpleLineSymbolLayer.create(layer_style)
                        symbol_layer.setWidth(0.5)
                        symbol_layer2 = QgsMarkerLineSymbolLayer.create({'placement': 'lastvertex'})
                        layer_style['color_border'] = color
                        markerSymbol = QgsSimpleMarkerSymbolLayer.create(layer_style)
                        markerSymbol.setShape(QgsSimpleMarkerSymbolLayerBase.ArrowHeadFilled)
                        markerSymbol.setSize(4)
                        marker = QgsMarkerSymbol()
                        marker.changeSymbolLayer(0, markerSymbol)
                        symbol_layer2.setSubSymbol(marker)
                elif layer.geometryType() == QgsWkbTypes.PointGeometry:
                    symbol_layer = QgsSimpleMarkerSymbolLayer.create(layer_style)
                    if unique_value.lower() == 'river':
                        symbol_layer.setShape(QgsSimpleMarkerSymbolLayerBase.Diamond)
                        symbol_layer.setSize(2.5)
                        symbol_layer.setStrokeWidth(0.4)
                        symbol_layer.setStrokeColor(QColor(50, 87, 128))
                        symbol_layer.setFillColor(QColor(100, 153, 208))
                    elif 'bdy' in unique_value.lower():
                        symbol_layer.setShape(QgsSimpleMarkerSymbolLayerBase.Square)
                        symbol_layer.setSize(2.5)
                        symbol_layer.setStrokeWidth(0.)
                        symbol_layer.setStrokeColor(QColor(35, 35, 35))
                        symbol_layer.setFillColor(QColor(randrange(0, 256), randrange(0, 256), randrange(0, 256)))
                    else:
                        symbol_layer.setShape(QgsSimpleMarkerSymbolLayerBase.Circle)
                        symbol_layer.setSize(2.0)
                        symbol_layer.setStrokeWidth(0.)
                        symbol_layer.setStrokeColor(QColor(35, 35, 35))
                        symbol_layer.setFillColor(QColor(randrange(0, 256), randrange(0, 256), randrange(0, 256)))
            else:
                symbol_layer = QgsSimpleFillSymbolLayer.create(layer_style)

            # replace default symbol layer with the configured one
            if symbol_layer is not None:
                symbol.changeSymbolLayer(0, symbol_layer)
                if symbol_layer2 is not None:
                    symbol.appendSymbolLayer(symbol_layer2)

            # create renderer object
            category = QgsRendererCategory(unique_value, symbol, str(unique_value))
            # entry for the list of category items
            categories.append(category)

        # create renderer object
        return QgsCategorizedSymbolRenderer(field_name, categories)


def graduatedRenderer(layer):
    symbol = QgsSymbol.defaultSymbol(layer.geometryType())
    symbol.setColor(Qt.red)
    grad_rend = QgsGraduatedSymbolRenderer('Magnitude')
    grad_rend.setSourceSymbol(symbol)
    grad_rend.setGraduatedMethod(QgsGraduatedSymbolRenderer.GraduatedSize)
    grad_rend.updateClasses(layer, QgsGraduatedSymbolRenderer.Mode.Quantile, 5)
    grad_rend.setSymbolSizes(2., 5.)

    return grad_rend


def is1dIntegrityToolOutput(layer):
    field_mapping = [('Warning', QVariant.String), ('Message', QVariant.String),
                     ('Tool', QVariant.String), ('Magnitude', QVariant.Double)]
    len_ = len(field_mapping)

    return layer is not None and isinstance(layer, QgsVectorLayer) and layer.isValid() and \
        'output' in layer.name() and [(x.name(), x.type()) for x in layer.fields()][:len_] == field_mapping


def tuflowqgis_apply_check_tf(qgis):
    # apply check file styles to all open shapefiles
    error = False
    message = None

    # load style layers using tuflowqgis_styles
    tf_styles = TF_Styles()
    error, message = tf_styles.Load()
    if error:
        return error, message

    for layer_name, layer in QgsProject.instance().mapLayers().items():
        if layer.type() == QgsMapLayer.VectorLayer:
            if re.findall(re.escape(r'.gpkg|layername='), layer.dataProvider().dataSourceUri(), flags=re.IGNORECASE):
                layer_fname = \
                    re.split(re.escape(r'.gpkg|layername='), layer.dataProvider().dataSourceUri(), flags=re.IGNORECASE)[
                        1]
            else:
                layer_fname = os.path.splitext(os.path.basename(layer.dataProvider().dataSourceUri()))[0]

            error, message, slyr = tf_styles.Find(layer_fname, layer)  # use tuflow styles to find longest matching
            if error:
                return error, message
            if re.findall(r'((_FM_PLOT_[PLR])|_raw_(nodes|links)_)', layer_fname, flags=re.IGNORECASE):
                slyr = False  # flood modeller
            if slyr:  # style layer found:
                layer.loadNamedStyle(slyr)
                layer.triggerRepaint()
            elif is1dIntegrityToolOutput(layer):
                renderer = graduatedRenderer(layer)
                if renderer:
                    layer.setRenderer(renderer)
                    layer.triggerRepaint()
            else:
                renderer = region_renderer(layer)
                if renderer:  # if the file requires a attribute based rendered (e.g. BC_Name for a _sac_check_R)
                    layer.setRenderer(renderer)
                    layer.triggerRepaint()
    return error, message


def tuflowqgis_apply_check_tf_clayer(qgis, **kwargs):
    error = False
    message = None
    try:
        canvas = qgis.mapCanvas()
    except:
        canvas = None
    # error = True
    # message = "ERROR - Unexpected error trying to  QGIS canvas layer."
    # return error, message
    try:
        if 'layer' in kwargs.keys():
            cLayer = kwargs['layer']
        else:
            if canvas is None:
                error = True
                message = "ERROR - Unexpected error trying to  QGIS canvas layer."
                return error, message
            cLayer = canvas.currentLayer()
    except:
        error = True
        message = "ERROR - Unable to get current layer, ensure a selection is made"
        return error, message

    # load style layers using tuflowqgis_styles
    tf_styles = TF_Styles()
    error, message = tf_styles.Load()
    if error:
        return error, message

    if cLayer is not None and cLayer.type() == QgsMapLayer.VectorLayer:
        if re.findall(re.escape(r'.gpkg|layername='), cLayer.dataProvider().dataSourceUri(), flags=re.IGNORECASE):
            layer_fname = \
                re.split(re.escape(r'.gpkg|layername='), cLayer.dataProvider().dataSourceUri(), flags=re.IGNORECASE)[1]
        else:
            layer_fname = os.path.splitext(os.path.basename(cLayer.dataProvider().dataSourceUri()))[0]
        if cLayer.dataProvider().name() == 'memory':
            layer_fname = cLayer.name()

        error, message, slyr = tf_styles.Find(layer_fname, cLayer)  # use tuflow styles to find longest matching
        if re.findall(r'((_FM_PLOT_[PLR])|_raw_(nodes|links)_)', layer_fname, flags=re.IGNORECASE):
            slyr = False  # flood modeller
        if error:
            return error, message
        if slyr:  # style layer found:
            cLayer.loadNamedStyle(slyr)
            cLayer.triggerRepaint()
        elif is1dIntegrityToolOutput(cLayer):
            renderer = graduatedRenderer(cLayer)
            if renderer:
                cLayer.setRenderer(renderer)
                cLayer.triggerRepaint()
        else:
            renderer = region_renderer(cLayer)
            if renderer:  # if the file requires a attribute based rendered (e.g. BC_Name for a _sac_check_R)
                cLayer.setRenderer(renderer)
                cLayer.triggerRepaint()

    return error, message


def ts_attname_to_float(name):
    return float(name.replace('_', '.').strip('t'))


def tuflowqgis_apply_stability_style_clayer(iface):
    error = False
    message = None

    if iface is None:
        return error, message

    layer = iface.activeLayer()
    if not isinstance(layer, QgsVectorLayer):
        return error, message

    return tuflowqgis_apply_stability_style(layer)


def tuflowqgis_apply_stability_style(layer):
    error = False
    msg = ''

    name = layer.dataProvider().dataSourceUri()
    if re.findall(re.escape(r'.gpkg|layername='), name, flags=re.IGNORECASE):
        name = re.split(re.escape(r'.gpkg|layername='), name, flags=re.IGNORECASE)[-1]
        name = name.split('|')[0]
    elif re.findall(f'^memory', name):
        name = layer.name()
    else:
        name = name.split('|')[0]
        name = Path(name).stem

    if not re.findall(r'_[PLR]$', name, flags=re.IGNORECASE):
        if layer.geometryType() == QgsWkbTypes.PointGeometry:
            name = '{0}_P'.format(name)
        elif layer.geometryType() == QgsWkbTypes.LineGeometry:
            name = '{0}_L'.format(name)
        elif layer.geometryType() == QgsWkbTypes.PolygonGeometry:
            name = '{0}_R'.format(name)

    found_style = None
    folder = Path(__file__).parent / 'QGIS_Styles' / 'stability'
    for file in folder.glob('*.qml'):
        if re.findall(r'{0}$'.format(file.stem), name, flags=re.IGNORECASE):
            found_style = str(file)
            break

    if not found_style:
        return error, msg

    layer.loadNamedStyle(found_style)
    layer.triggerRepaint()

    return error, msg


def tuflowqgis_increment_fname(infname, use_regex=True):
    if use_regex:
        pattern = r'\d{2,3}[A-z]?(?=(?:_[PLR]$|$))'
        file_stem = Path(infname).stem
        regex_find_version = re.findall(pattern, file_stem, flags=re.IGNORECASE)
        if regex_find_version:
            version = regex_find_version[0]
            if re.findall(r'[A-z]', version):
                v = re.findall(r'\d{2,3}', version)[0]
            else:
                v = version
            text_length = len(v)
            new_version = '{0:0{1}d}'.format(int(v) + 1, text_length)
            outfname = re.sub(pattern, new_version, file_stem, flags=re.IGNORECASE)
        else:
            geom = re.findall(r'_[PLR]$', file_stem, flags=re.IGNORECASE)
            if geom:
                outfname = '{0}_001{1}'.format(file_stem, geom[0])
            else:
                outfname = '{0}_001'.format(file_stem)
        outfname = str(Path(infname).parent / '{0}{1}'.format(outfname, Path(infname).suffix))
        return outfname

    # check for file extension (shapefile only, not expecting .mif)
    fext = ''
    if infname[-4:].upper() == '.SHP':
        fext = infname[-4:]
        fname = infname[0:-4]
    else:
        fname = infname

    # check for TUFLOW geometry suffix
    geom = ''
    if fname[-2:].upper() == '_P':
        tmpstr = fname[0:-2]
        geom = fname[-2:]
    elif fname[-2:].upper() == '_L':
        tmpstr = fname[0:-2]
        geom = fname[-2:]
    elif fname[-2:].upper() == '_R':
        tmpstr = fname[0:-2]
        geom = fname[-2:]
    else:
        tmpstr = fname

    # try to find version as integer at end of string
    rind = tmpstr.rfind('_')
    if rind >= 0:
        verstr = tmpstr[rind + 1:]
        ndig = len(verstr)
        lstr = tmpstr[0:rind + 1]
        try:
            verint = int(verstr)
            verint = verint + 1
            newver = str(verint)
            newverstr = newver.zfill(ndig)
            outfname = lstr + newverstr + geom + fext
        except:
            outfname = tmpstr
    else:
        outfname = tmpstr

    return outfname


def tuflowqgis_insert_tf_attributes(qgis, inputLayer, basedir, runID, template, lenFields, dialog, output_db):
    message = None

    if inputLayer.geometryType() == QgsWkbTypes.PointGeometry:
        geomType = '_P'
        g = 'point'
    elif inputLayer.geometryType() == QgsWkbTypes.PolygonGeometry:
        geomType = '_R'
        g = 'polygon'
    else:
        geomType = '_L'
        g = 'linestring'

    # empty_folder = 'empty'
    # for p in os.walk(os.path.dirname(basedir)):
    # 	for d in p[1]:
    # 		if d.lower() == empty_folder:
    # 			empty_folder = d
    # 			break
    # 	break
    # gis_folder = basedir.replace('/', os.sep).replace('{0}{1}'.format(os.sep, d), '')
    basedir = Path(basedir)
    gis_folder = basedir.parent

    template = '1d_nwke' if lenFields >= 10 and template.lower() == '1d_nwk' else template
    empty_type = '{0}_empty_pts'.format(template) if '_pts' in template.lower() else '{0}_empty'.format(template)
    empty_file = [x for x in basedir.glob(f'{empty_type}*') if x.suffix.lower() in ['.shp', '.gpkg']][0]
    empty_ext = empty_file.suffix.lower()
    isgpkg = is_database(inputLayer)
    out_ext = '.gpkg' if isgpkg or output_db else '.shp'
    layername = '{0}_{1}{2}'.format(template, runID, geomType)
    if out_ext == '.gpkg':
        output_db = Path(output_db) if output_db else (gis_folder / layername).with_suffix('.gpkg')
        out_path = str(output_db)
        fpath = '{0}|layername={1}'.format(output_db, layername)
    else:
        fpath = str((gis_folder / layername).with_suffix('.shp'))
        out_path = fpath

    if out_ext == '.gpkg':
        if output_db.exists() and layername.lower() in [x.lower() for x in get_table_names(output_db)]:
            answer = QMessageBox.question(dialog, 'Output Exists',
                                          '{0} already exists in {1}.\nOverwrite existing?'.format(layername,
                                                                                                   output_db.name),
                                          QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
            if answer == QMessageBox.Cancel:
                return None
            elif answer == QMessageBox.No:
                return 'pass'
    else:
        if Path(fpath).exists():
            answer = QMessageBox.question(dialog, 'Output Exists',
                                          '{0} already exists.\nOverwrite existing?'.format(fpath),
                                          QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
            if answer == QMessageBox.Cancel:
                return None
            elif answer == QMessageBox.No:
                return 'pass'

    if empty_ext == '.gpkg':
        empty_name = get_table_names(empty_file)[0]
        empty_fpath = '{0}|layername={1}'.format(empty_file, empty_name)
    else:
        empty_name = empty_file.with_suffix('').name
        empty_fpath = str(empty_file)
    empty_layer = QgsVectorLayer(empty_fpath, empty_name, 'ogr')
    if not empty_layer.isValid():
        return 'Could not load empty layer'
    crs = empty_layer.sourceCrs()
    uri = '{0}?crs={1}'.format(g, crs.authid())
    unique_names = []
    renamed_fields = []
    for field in empty_layer.fields():
        if field.name().lower() == 'fid':
            continue
        unique_names.append(field.name())
        if field.type() == QVariant.LongLong:
            type_name = 'int8'
        else:
            type_name = field.typeName()
        uri = '{0}&field={1}:{2}({3},{4})'.format(uri, field.name(), type_name, field.length(), field.precision())
    for field in inputLayer.fields():
        if field.name().lower() == 'fid':
            continue
        if field.name() in unique_names:
            counter = 1
            new_name = '{0}_{1}'.format(counter, field.name())
            while new_name in unique_names:
                counter += 1
                new_name = '{0}_{1}'.format(counter, field.name())
        else:
            new_name = field.name()
        unique_names.append(new_name)
        renamed_fields.append(new_name)
        if field.type() == QVariant.LongLong:
            type_name = 'int8'
        else:
            type_name = field.typeName()
        uri = '{0}&field={1}:{2}({3},{4})'.format(uri, new_name, type_name, field.length(), field.precision())

    out_lyr = QgsVectorLayer(uri, layername, 'memory')
    if not out_lyr.isValid():
        return 'error initialising output layer in memory'

    feats = []
    for feat in inputLayer.getFeatures():
        try:
            f = QgsFeature()
            f.setGeometry(feat.geometry())
            f.setFields(out_lyr.fields())
            i = 0
            for field in inputLayer.fields():
                if field.name().lower() == 'fid':
                    continue
                f[renamed_fields[i]] = feat[field.name()]
                i += 1
            feats.append(f)
        except Exception as e:
            return 'Error copying feature: {0}'.format(e)
    try:
        out_lyr.dataProvider().truncate()
        out_lyr.dataProvider().addFeatures(feats)
        out_lyr.updateExtents()
    except Exception as e:
        return 'Error copying features: {0}'.format(e)

    options = QgsVectorFileWriter.SaveVectorOptions()
    if out_ext == '.gpkg' and output_db.exists():
        options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer
    else:
        options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteFile
        open_layer = tuflowqgis_find_layer(layername)
        if out_ext == '.shp' and open_layer is not None:
            QgsProject.instance().removeMapLayer(open_layer.id())
            open_layer = None
    options.layerName = layername
    options.driverName = 'GPKG' if out_ext == '.gpkg' else 'ESRI Shapefile'
    try:
        if Qgis.QGIS_VERSION_INT >= 31030:
            error = QgsVectorFileWriter.writeAsVectorFormatV2(out_lyr, out_path, QgsCoordinateTransformContext(),
                                                              options)
            if error[0] != QgsVectorFileWriter.NoError:
                if out_ext == '.gpkg':
                    return 'Error writing out {0} | {1}\n{2}'.format(output_db, layername, error[1])
                else:
                    return 'Error writing out {0}\n{1}'.format(fpath, error[1])
        else:
            err, msg = QgsVectorFileWriter.writeAsVectorFormat(out_lyr, out_path, 'SYSTEM', out_lyr.crs(),
                                                               options.driverName)
            if err:
                if out_ext == '.gpkg':
                    return 'Error writing out {0} | {1}\n{2}'.format(output_db, layername, msg)
                else:
                    return 'Error writing out {0}\n{1}'.format(fpath, msg)
    except Exception as e:
        if out_ext == '.gpkg':
            return 'Error writing out {0} | {1}: {2}. Try updating QGIS to latest version to fix this issue.'.format(
                output_db, layername, e)
        else:
            return 'Error writing out {0}: {1}. Try updating QGIS to latest version to fix this issue.'.format(fpath, e)

    open_layer = tuflowqgis_find_layer(layername)
    if open_layer is None or open_layer.dataProvider().dataSourceUri().lower() != fpath.lower():
        qgis.addVectorLayer(fpath, layername, "ogr")

    return


# Create new vector file from template with appended attribute fields
# if template == '1d_nwk':
# 	if lenFields >= 10:
# 		template2 = '1d_nwke'
# 		fpath = os.path.join(basedir, '{0}_empty{1}.shp'.format(template2, geomType))
# 	else:
# 		fpath = os.path.join(basedir, '{0}_empty{1}.shp'.format(template, geomType))
# else:
# 	fpath = os.path.join(basedir, '{0}_empty{1}.shp'.format(template, geomType))
# if os.path.isfile(fpath):
# 	layer = QgsVectorLayer(fpath, "tmp", "ogr")
# 	name = '{0}_{1}{2}.shp'.format(template, runID, geomType)
# 	savename = os.path.join(gis_folder, name)
# 	if QFile(savename).exists():
# 		overwriteExisting = QMessageBox.question(dialog, "Import Empty",
# 		                                         'Output file already exists\nOverwrite existing file?',
# 		                                         QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
# 		if overwriteExisting != QMessageBox.Yes:
# 		#QMessageBox.critical(qgis.mainWindow(),"Info", ("File Exists: {0}".format(savename)))
# 			message = 'Unable to complete utility because file already exists'
# 			return 1
# 	outfile = QgsVectorFileWriter(vectorFileName=savename, fileEncoding="System",
# 	                              fields=layer.dataProvider().fields(), geometryType=layer.wkbType(),
# 	                              srs=layer.dataProvider().sourceCrs(), driverName="ESRI Shapefile",)
#
# 	if outfile.hasError() != QgsVectorFileWriter.NoError:
# 		QMessageBox.critical(qgis.mainWindow(),"Info", ("Error Creating: {0}".format(savename)))
# 		message = 'Error writing output file. Check output location and output file.'
# 		return message
#
# 	# delete prj file and replace with empty prj - ensures it is exactly the same
# 	correct_prj = '{0}.prj'.format(os.path.splitext(inputLayer.dataProvider().dataSourceUri())[0])
# 	new_prj = '{0}.prj'.format(os.path.splitext(savename)[0])
# 	try:
# 		copyfile(correct_prj, new_prj)
# 	except:
# 		pass
#
# 	outfile = QgsVectorLayer(savename, name[:-4], "ogr")
# 	outfile.dataProvider().addAttributes(inputLayer.dataProvider().fields())

# Get attribute names of input layers
# layer_attributes = [field.name() for field in layer.fields()]
# inputLayer_attributes = [field.name() for field in inputLayer.fields()]

# Create 2D attribute value list and add features to new file
# 	row_list = []
# 	for feature in inputLayer.getFeatures():
# 		row = [''] * len(layer_attributes)
# 		for attr in inputLayer_attributes:
# 			row.append(feature[attr])
# 		row_list.append(row)
# 		outfile.dataProvider().addFeatures([feature])
#
# 	# correct field values
# 	for i, feature in enumerate(outfile.getFeatures()):
# 		row_dict = {}
# 		for j in range(len(row_list[0])):
# 			row_dict[j] = row_list[i][j]
# 		outfile.dataProvider().changeAttributeValues({i: row_dict})
#
# 	qgis.addVectorLayer(savename, name[:-4], "ogr")
#
# return message

def get_tuflow_labelName(layer):
    fsource = layer.source()  # includes full filepath and extension
    fname = os.path.split(fsource)[1][:-4]  # without extension

    if '1d_bc' in fname or '2d_bc' in fname:
        field_name1 = layer.fields().field(0).name()
        field_name2 = layer.fields().field(2).name()
        field_name = "'Name: ' + \"{0}\" + '\n' + 'Type: ' + \"{1}\"".format(field_name2, field_name1)
    elif '1d_mh' in fname or '1d_nd' in fname or '1d_pit' in fname:
        field_name1 = layer.fields().field(0).name()
        field_name2 = layer.fields().field(1).name()
        field_name = "'ID: ' + \"{0}\" + '\n' + 'Type: ' + \"{1}\"".format(field_name1, field_name2)
    elif '1d_nwk' in fname:
        field_name1 = layer.fields().field(0).name()
        field_name2 = layer.fields().field(1).name()
        field_name3 = layer.fields().field(13).name()
        field_name4 = layer.fields().field(14).name()
        field_name = "'ID: ' + \"{0}\" + '\n' + 'Type: ' + \"{1}\"".format(field_name1, field_name2)
    elif '2d_fc_' in fname:
        field_name1 = layer.fields().field(0).name()
        field_name2 = layer.fields().field(1).name()
        field_name3 = layer.fields().field(2).name()
        field_name4 = layer.fields().field(5).name()
        field_name = "'Type: ' + \"{0}\" + '\n' + 'Invert: ' + if(\"{1}\">-1000000, to_string(\"{1}\"), \"{1}\") +" \
                     "'\n' + 'Obvert: ' + if(\"{2}\">-100, to_string(\"{2}\"), \"{2}\") + '\n' + 'FLC: ' + " \
                     "if(\"{3}\">=0, to_string(\"{3}\"), \"{3}\")".format(field_name1, field_name2, field_name3,
                                                                          field_name4)
    elif '2d_fcsh' in fname:
        field_name1 = layer.fields().field(0).name()
        field_name2 = layer.fields().field(1).name()
        field_name3 = layer.fields().field(5).name()
        field_name4 = layer.fields().field(6).name()
        field_name = "'Invert: ' + if(\"{0}\">-1000000, to_string(\"{0}\"), \"{0}\") + '\n' + 'Obvert: ' + " \
                     "if(\"{1}\">-100, to_string(\"{1}\"), \"{1}\") + '\n'" \
                     " + 'pBlockage: ' + if(\"{2}\">-100, to_string(\"{2}\"), \"{2}\") + '\n' + 'FLC: ' + " \
                     "if(\"{3}\">=0, to_string(\"{3}\"), \"{3}\")".format(field_name1, field_name2, field_name3,
                                                                          field_name4)
    elif '2d_lfcsh' in fname:
        field_name1 = layer.fields().field(0).name()
        field_name2 = layer.fields().field(4).name()
        field_name3 = layer.fields().field(5).name()
        field_name4 = layer.fields().field(6).name()
        field_name5 = layer.fields().field(7).name()
        field_name6 = layer.fields().field(8).name()
        field_name7 = layer.fields().field(9).name()
        field_name8 = layer.fields().field(10).name()
        field_name9 = layer.fields().field(11).name()
        field_name10 = layer.fields().field(12).name()
        field_name = "'Invert: ' + if(\"{0}\">-1000000, to_string(\"{0}\"), \"{0}\") + '\n' + 'L1 Obvert: ' + " \
                     "if(\"{1}\">-100, to_string(\"{1}\"), \"{1}\") + '\n'" \
                     " + 'L1 pBlockage: ' + if(\"{2}\">-100, to_string(\"{2}\"), \"{2}\") + '\n' + 'L1 FLC: ' + " \
                     "if(\"{3}\">=0, to_string(\"{3}\"), \"{3}\") + '\n' + 'L2 Depth: ' + " \
                     "if(\"{4}\">=0, to_string(\"{4}\"), \"{4}\") + '\n' + 'L2 pBlockage: ' + " \
                     "if(\"{5}\">=0, to_string(\"{5}\"), \"{5}\") + '\n' + 'L2 FLC: ' + " \
                     "if(\"{6}\">=0, to_string(\"{6}\"), \"{6}\") + '\n' + 'L3 Depth: ' + " \
                     "if(\"{7}\">=0, to_string(\"{7}\"), \"{7}\") + '\n' + 'L3 pBlockage: ' + " \
                     "if(\"{8}\">=0, to_string(\"{8}\"), \"{8}\") + '\n' + 'L3 FLC: ' + " \
                     "if(\"{9}\">=0, to_string(\"{9}\"), \"{9}\")".format(field_name1, field_name2, field_name3,
                                                                          field_name4, field_name5, field_name6,
                                                                          field_name7, field_name8, field_name9,
                                                                          field_name10)
    elif '2d_po' in fname or '2d_lp' in fname:
        field_name1 = layer.fields().field(0).name()
        field_name2 = layer.fields().field(1).name()
        field_name = "'Type: ' + \"{0}\" + '\n' + 'Label: ' + \"{1}\"".format(field_name1, field_name2)
    elif '2d_sa_rf' in fname:
        field_name1 = layer.fields().field(0).name()
        field_name2 = layer.fields().field(1).name()
        field_name3 = layer.fields().field(2).name()
        field_name4 = layer.fields().field(3).name()
        field_name5 = layer.fields().field(4).name()
        field_name = "'Name: ' + \"{0}\" + '\n' + 'Catchment Area: ' + if(\"{1}\">0, to_string(\"{1}\"), \"{1}\") + " \
                     "'\n' + 'Rain Gauge: ' + \"{2}\" + '\n' + 'IL: ' + if(\"{3}\">=0, to_string(\"{3}\"), \"{3}\") " \
                     " + '\n' + 'CL: ' + if(\"{4}\">=0, to_string(\"{4}\"), \"{4}\")".format(field_name1, field_name2,
                                                                                             field_name3, field_name4,
                                                                                             field_name5)
    elif '2d_sa_tr' in fname:
        field_name1 = layer.fields().field(0).name()
        field_name2 = layer.fields().field(1).name()
        field_name3 = layer.fields().field(2).name()
        field_name4 = layer.fields().field(3).name()
        field_name = "'Name: ' + \"{0}\" + '\n' + 'Trigger Type: ' + \"{1}\" + '\n' + 'Trigger Location: ' + \"{2}\"" \
                     "+ '\n' + 'Trigger Value: ' + if(\"{3}\">=0, to_string(\"{3}\"), \"{3}\")".format(field_name1,
                                                                                                       field_name2,
                                                                                                       field_name3,
                                                                                                       field_name4)
    elif '2d_vzsh' in fname:
        field_name1 = layer.fields().field(0).name()
        field_name2 = layer.fields().field(3).name()
        field_name3 = layer.fields().field(4).name()
        field_name4 = layer.fields().field(5).name()
        field_name5 = layer.fields().field(6).name()
        field_name6 = layer.fields().field(7).name()
        field_name = "'Z: ' + if(\"{0}\">-1000000, to_string(\"{0}\"), \"{0}\") + '\n' + 'Shape Options: ' + \"{1}\"" \
                     "+ '\n' + 'Trigger 1: ' + \"{2}\" + '\n' + 'Trigger 2: ' + \"{3}\" + '\n' + 'Trigger Value: ' " \
                     "+ if(\"{4}\">0, to_string(\"{4}\"), \"{4}\") + '\n' + 'Period: ' + " \
                     "if(\"{5}\">0, to_string(\"{5}\"), \"{5}\")".format(field_name1, field_name2, field_name3,
                                                                         field_name4, field_name5, field_name6)
    elif '2d_zshr' in fname:
        field_name1 = layer.fields().field(0).name()
        field_name2 = layer.fields().field(3).name()
        field_name3 = layer.fields().field(4).name()
        field_name4 = layer.fields().field(5).name()
        field_name5 = layer.fields().field(6).name()
        field_name = "'Z: ' + if(\"{0}\">-1000000, to_string(\"{0}\"), \"{0}\") + '\n' + 'Shape Options: ' + \"{1}\"" \
                     "+ '\n' + 'Route Name: ' + \"{2}\" + '\n' + 'Cut Off Type: ' + \"{3}\" + '\n' + " \
                     "'Cut Off Values: ' + if(\"{4}\">-1000000, to_string(\"{4}\"), \"{4}\")".format(field_name1,
                                                                                                     field_name2,
                                                                                                     field_name3,
                                                                                                     field_name4,
                                                                                                     field_name5)
    elif '2d_zsh' in fname:
        if layer.geometryType() == QgsWkbTypes.PointGeometry:
            field_name1 = layer.fields().field(0).name()
            field_name = "'{0}: ' + if(\"{0}\">-1000000, to_string(\"{0}\"), \"{0}\")".format(field_name1)
        elif layer.geometryType() == QgsWkbTypes.LineGeometry:
            field_name1 = layer.fields().field(0).name()
            field_name2 = layer.fields().field(2).name()
            field_name = "'Z: ' + if(\"{0}\">-1000000, to_string(\"{0}\"), \"{0}\") + '\n' + 'Shape Width: ' + " \
                         "if(\"{1}\">-1000000, to_string(\"{1}\"), \"{1}\")".format(field_name1, field_name2)
        elif layer.geometryType() == QgsWkbTypes.PolygonGeometry:
            field_name1 = layer.fields().field(0).name()
            field_name2 = layer.fields().field(3).name()
            field_name = "'Z: ' + if(\"{0}\">-1000000, to_string(\"{0}\"), \"{0}\") + '\n' + 'Shape Options: ' + " \
                         "\"{1}\"".format(field_name1, field_name2)
    elif '_RCP' in fname:
        field_name1 = layer.fields().field(0).name()
        field_name2 = layer.fields().field(1).name()
        field_name3 = layer.fields().field(2).name()
        field_name4 = layer.fields().field(3).name()
        field_name5 = layer.fields().field(4).name()
        field_name = "'Route Name: ' + if(\"{0}\">-1000000, to_string(\"{0}\"), \"{0}\") + '\n' + 'Cut Off Value: ' " \
                     "+ if(\"{1}\">-1000000, to_string(\"{1}\"), \"{1}\") + '\n' + 'First Cut Off Time: ' + " \
                     "if(\"{2}\">-1000000, to_string(\"{2}\"), \"{2}\") + '\n' + 'Last Cutoff Time: ' + " \
                     "if(\"{3}\">-1000000, to_string(\"{3}\"), \"{3}\") + '\n' + 'Duration of Cutoff: ' + " \
                     "if(\"{4}\">-1000000, to_string(\"{4}\"), \"{4}\")".format(field_name1, field_name2, field_name3,
                                                                                field_name4, field_name5)
    elif '1d_mmH_P' in fname:
        field_name = ""
        for i, field in enumerate(layer.fields()):
            if i == 0 or i == 1 or i == 3:
                field_name1 = "'{0}: ' + if(\"{0}\">-1000000, to_string(\"{0}\"), \"{0}\")".format(field.name())
                if i != 3:
                    field_name = field_name + field_name1 + "+ '\n' +"
                else:
                    field_name = field_name + field_name1
    elif '1d_mmQ_P' in fname or '1d_mmV_P' in fname:
        field_name = ""
        for i, field in enumerate(layer.fields()):
            if i == 0 or i == 1 or i == 2 or i == 4 or i == 5:
                field_name1 = "'{0}: ' + if(\"{0}\">-1000000, to_string(\"{0}\"), \"{0}\")".format(field.name())
                if i != 5:
                    field_name = field_name + field_name1 + "+ '\n' +"
                else:
                    field_name = field_name + field_name1
    elif '1d_ccA_L' in fname:
        field_name = ""
        for i, field in enumerate(layer.fields()):
            if i == 0 or i == 1:
                field_name1 = "'{0}: ' + if(\"{0}\">-1000000, to_string(\"{0}\"), \"{0}\")".format(field.name())
                if i != 1:
                    field_name = field_name + field_name1 + "+ '\n' +"
                else:
                    field_name = field_name + field_name1
    else:
        field_name1 = layer.fields().field(0).name()
        field_name = "'{0}: ' + if(\"{0}\">-1000000, to_string(\"{0}\"), \"{0}\")".format(field_name1)
    return field_name


def get_1d_nwk_labelName(layer, type):
    field_name1 = layer.fields().field(0).name()
    field_name2 = layer.fields().field(1).name()
    field_name3 = layer.fields().field(13).name()
    field_name4 = layer.fields().field(14).name()
    # QMessageBox.information(qgis.mainWindow(),"Info", ("{0}".format(field_name2)))
    if type == 'C':
        field_name = "'ID: ' + \"{0}\" + '\n' + 'Type: ' + \"{1}\" + '\n' + 'Width: ' + " \
                     "if(\"{2}\">=0, to_string(\"{2}\"), \"{2}\")".format(field_name1, field_name2, field_name3)
    elif type == 'R':
        field_name = "'ID: ' + \"{0}\" + '\n' + 'Type: ' + \"{1}\" + '\n' + 'Width: ' + " \
                     "if(\"{2}\">=0, to_string(\"{2}\"), \"{2}\") + '\n' + 'Height: ' + " \
                     "if(\"{3}\">=0, to_string(\"{3}\"), \"{3}\")".format(field_name1, field_name2, field_name3,
                                                                          field_name4)
    else:
        field_name = "'ID: ' + \"{0}\" + '\n' + 'Type: ' + \"{1}\"".format(field_name1, field_name2)

    return field_name


def stripComments(text: str) -> str:
    """
    Strips comments as per TUFLOW convention from text.

    :param text: str input text
    :return: str output text
    """

    new_text = text
    char = ['!', '#']
    for c in char:
        new_text = new_text.split(c)[0].strip()

    return new_text


def stripCommand(text: str) -> (str, str):
    """
    Strips command from text.

    :param text: str
    :return: str, str
    """

    comm, val = '', ''

    new_text = stripComments(text)
    comp = new_text.split('==')
    if len(comp) == 2:
        comm, val = comp
        comm = comm.strip()
        val = val.strip()
    elif len(comp) == 1:
        comm = comp[0]
        comm = comm.strip()

    return comm, val


def getTuflowLayerType(layerName: str) -> (str, str):
    """
    Gets the layer TUFLOW type from the layer name.
    Returns TUFLOW type and geometry type e.g. "1d_nwk". "L"

    :param layerName: str layer name or source
    :return: str TUFLOW layer type, str geometry type
    """

    tuflowLayerType = ''
    geomType = ''

    # get name - separate extension and file path if needed
    # name = os.path.splitext(os.path.basename(layerName))[0]
    name = layerName

    # first see if it is a check layer
    pattern = r'_check(_[PLR])?$'  # will match '_check' or '_check_P' (P or L or R) only if it is at the end of the string
    check = re.search(pattern, name, flags=re.IGNORECASE)
    if check is not None:
        tuflowLayerType = 'check'
    else:  # not a check file so maybe an input or result layer
        # find 0d_ or 1d_ or 2d_ part of layer name
        pattern = r'^[0-2]d_'
        for i, match in enumerate(re.finditer(pattern, name, flags=re.IGNORECASE)):
            if i == 0:  # just use the first matched instance
                tuflowLayerType = match[0]  # 0d_ or 1d_ or 2d_
                reSplit = re.split(pattern, layerName, flags=re.IGNORECASE)
                nSplit = reSplit[1].split('_')
                ltype = nSplit[0]  # e.g. nwk
                tuflowLayerType += ltype  # e.g. 1d_nwk

                # special case for 2d_sa as this could be 2d_sa_tr or 2d_sa_rf
                specialCases = ['2d_sa_rf', '2d_sa_tr']
                if len(nSplit) >= 2:
                    for sc in specialCases:
                        tempName = tuflowLayerType + '_' + nSplit[1]
                        if sc.lower() == tempName.lower():
                            tuflowLayerType = tempName

                break  # just use the first matched instance

        # PLOT or FM_PLOT
        pattern = r'_FM_PLOT_[PLR]'
        if re.findall(pattern, layerName, flags=re.IGNORECASE):
            tuflowLayerType = '_FM_PLOT'

        # messages
        pattern = r'_messages'
        if re.findall(pattern, layerName, flags=re.IGNORECASE):
            tuflowLayerType = 'messages'

    # get geometry type
    if tuflowLayerType:
        layer = tuflowqgis_find_layer(layerName)
        if layer is not None:
            if isinstance(layer, QgsVectorLayer):
                if layer.geometryType() == QgsWkbTypes.PointGeometry:
                    geomType = 'P'
                elif layer.geometryType() == QgsWkbTypes.LineGeometry:
                    geomType = 'L'
                elif layer.geometryType() == QgsWkbTypes.PolygonGeometry:
                    geomType = 'R'

    return tuflowLayerType, geomType


def findLabelPropertyMatch(files: list, layerType: str, geomType: str, layerName: str) -> (str, str):
    """
    Returns matching file if found.

    :param files: list [ str filepath ]
    :param layerType: str e.g. '1d_nwk'
    :param geomType: str e.g. 'P'
    :param layerName: str layer name or source
    :return: str file path
    """

    # get name - separate extension and file path if needed
    # name = os.path.splitext(os.path.basename(layerName))[0]
    name = layerName

    # initialise match variable
    match = ''

    # if layer is a check layer or not a tuflow layer loop through file and just find first name match
    if layerType == 'check' or layerType == '' or layerType == 'messages':
        for labelProperty in files:
            if os.path.splitext(os.path.basename(labelProperty))[0].lower() in name.lower():
                match = labelProperty
    else:  # is a tuflow layer (input or result) so do a few additional checks (mainly to handle specific geometry types)
        # first check if there is geom specific match e.g. 1d_nwk_P
        searchString = '{0}_{1}'.format(layerType, geomType)
        for labelProperty in files:
            if os.path.splitext(os.path.basename(labelProperty))[0].lower() == searchString.lower():
                match = labelProperty
                break
        # if no match then search for the type without geometry e.g. 1d_nwk
        if not match:
            searchString = layerType
            for labelProperty in files:
                if os.path.splitext(os.path.basename(labelProperty))[0].lower() == searchString.lower():
                    match = labelProperty
                    break
    # if still no match use default.txt if available
    if not match:
        for labelProperty in files:
            if os.path.splitext(os.path.basename(labelProperty))[0].lower() == 'default':
                match = labelProperty
                break
    # finally check if there is an override.txt
    override = ''
    for labelProperty in files:
        if os.path.splitext(os.path.basename(labelProperty))[0].lower() == 'override':
            override = labelProperty
            break

    return match, override


def assignLabelProperty(property: dict, command: str, value: str) -> bool:
    """
    Assign label property based on command and value

    :param property: dict of label properties
    :param command: str
    :param value: str
    :return: bool was a valid command
    """

    if command.lower() == 'buffer':
        property['buffer'] = True if value.lower() == 'on' else False
    elif command.lower() == 'box':
        property['box'] = True if value.lower() == 'on' else False
    elif command.lower() == 'attribute name':
        property['use_attribute_name'] = True if value.lower() == 'on' else False
    elif command.lower() == 'label attributes':
        try:
            property['label_attributes'] = [int(x.strip()) for x in value.split('|')]
        except ValueError:
            pass
    elif command.lower() == 'point placement':
        property['point_placement'] = value.lower()
    elif command.lower() == 'line placement':
        property['line_placement'] = value.lower()
    elif command.lower() == 'region placement':
        property['region_placement'] = value.lower()
    elif command.lower() == 'offset x,y' or command.lower() == 'offset x, y' or command.lower() == 'offsetx,y':
        try:
            property['offsetXY'] = [float(x.strip()) for x in value.split(',')]
            if len(property['offsetXY']) == 1:
                property['offsetXY'] = (property['offsetXY'][0], property['offsetXY'][0])
            elif not property['offsetXY']:
                property['offsetXY'] = (2, 2)  # back to default
        except ValueError:
            pass
    elif command.lower() == 'rule':
        property['rule_strictness'] = value.lower()
    else:
        return False

    return True


def parseLabelProperties(fpath: str, override: str = '', rule_based: bool = False,
                         rule: str = '', isOverride: bool = False, **kwargs) -> dict:
    """
    reads layer properties from txt file and returns a dict object

    :param fpath: str full path to text file
    :param rule_based: bool whether this is a rule based subset
    :param rule: str rule name e.g. 2 | C
    :return: dict of properties
    """

    d = kwargs['d'] if 'd' in kwargs else None

    # hardcoded defaults
    if d is None:
        d = {
            'rule_based': {},
            'rule_strictness': 'loose',
            'buffer': True,
            'box': False,
            'use_attribute_name': True,
            'label_attributes': [1],
            'point_placement': 'cartographic',
            'line_placement': 'parallel',
            'region_placement': 'centroid',
            'offsetXY': (2, 2),
            'only_rule_based': False,
        }

    isOnlyRuleBased = False if not isOverride else d['only_rule_based']
    if os.path.exists(fpath):
        if not rule_based:  # not looking for a specific labelling rule
            # first sweep pick up rule-based labelling names
            with open(fpath, 'r') as fo:
                rule_names = []
                for line in fo:
                    comm, val = stripCommand(line)
                    if comm.lower() == 'attribute':
                        if len(val.split('|')) >= 2:
                            try:
                                int(val.split('|')[0])
                            except ValueError:
                                continue
                            if val not in rule_names:
                                rule_names.append(val)
                                isOnlyRuleBased = True  # there is a rule so switch this to true for now
            # collect rule based properties into dictionary and add to dictionary
            for rule_name in rule_names:
                if rule_name in d['rule_based']:
                    d_rule = parseLabelProperties(fpath, rule_based=True, rule=rule_name, d=d['rule_based'][rule_name])
                else:
                    d_rule = parseLabelProperties(fpath, rule_based=True, rule=rule_name)
                    d['rule_based'][rule_name] = d_rule
            # pick up non rule based labels
            with open(fpath, 'r') as fo:
                read = True
                for line in fo:
                    comm, val = stripCommand(line)
                    if comm.lower() == 'attribute':
                        read = False
                    elif comm.lower() == 'end attribute':
                        read = True
                    else:
                        if read:
                            if assignLabelProperty(d, comm, val):
                                isOnlyRuleBased = False  # switch this back to false since there are some defaults
                            if isOverride:
                                for rule_name, d_rule in d['rule_based'].items():
                                    if rule_name not in rule_names:
                                        assignLabelProperty(d_rule, comm, val)
        else:  # only pick up properties for specific rule
            with open(fpath, 'r') as fo:
                read = False
                for line in fo:
                    comm, val = stripCommand(line)
                    if comm.lower() == 'attribute':
                        if val.lower() == rule.lower():
                            read = True
                    elif comm.lower() == 'end attribute':
                        read = False
                    else:
                        if read:
                            assignLabelProperty(d, comm, val)
        # check if there is only rule based or if there are also default values i.e. an 'else' rule
        d['only_rule_based'] = isOnlyRuleBased
        if not isOnlyRuleBased and d['rule_based']:
            # copy defaults into a rule called 'else'
            rule = {
                'rule_based': {},
                'rule_strictness': d['rule_strictness'],
                'buffer': d['buffer'],
                'box': d['box'],
                'use_attribute_name': d['use_attribute_name'],
                'label_attributes': d['label_attributes'][:],
                'point_placement': d['point_placement'],
                'line_placement': d['line_placement'],
                'region_placement': d['region_placement'],
                'offsetXY': d['offsetXY'][:],
                'only_rule_based': d['only_rule_based'],
            }
            d['rule_based']['else'] = rule

    # pick up values from override
    if override:
        parseLabelProperties(override, d=d, isOverride=True)

    return d


def findCustomLabelProperties(layerName: str) -> dict:
    """
    Finds custom label properties from "layer_labelling" folder if available
    and collect properties into dictionary.
    If not found sets default properties based on default settings or hardcoded
    defaults.
    If override.txt exists, properties in this will override other settings

    :param layerName: str layer name or source
    :return: dict labelling properties
    """

    properties = {}

    layerType, geomType = getTuflowLayerType(layerName)

    dir = os.path.join(os.path.dirname(__file__), "layer_labelling")
    if os.path.exists(dir):
        labelPropertyFiles = glob.glob(os.path.join(dir, "*.txt"))
        matchingFile, override = findLabelPropertyMatch(labelPropertyFiles, layerType, geomType, layerName)
        properties = parseLabelProperties(matchingFile, override)

    return properties


def setupLabelFormat(isExpression: bool = True, isBuffer: bool = True) -> QgsPalLayerSettings:
    label = QgsPalLayerSettings()
    format = QgsTextFormat()
    buffer = QgsTextBufferSettings()
    buffer.setEnabled(isBuffer)
    format.setBuffer(buffer)
    label.setFormat(format)
    label.isExpression = isExpression
    label.multilineAlign = 0
    label.drawLabels = True

    return label


def getLabelFieldName(layer: QgsVectorLayer, properties: dict) -> str:
    """
    Returns field name expression for labelling

    :param layer: QgsVectorLayer
    :param properties: dict
    :return: str field name expression
    """

    qv = Qgis.QGIS_VERSION_INT

    add = 0
    if re.findall(re.escape(r'.gpkg|layername='), layer.dataProvider().dataSourceUri(), re.IGNORECASE):
        add = 1

    fields = layer.fields()

    if qv >= 32600:
        get_field = lambda i: fields[i]
    else:
        get_field = lambda i: fields.field(i)

    a = []
    for i in properties['label_attributes']:
        i = min(i, fields.size() - 1)
        # if fields.size() >= i:
        if properties['use_attribute_name']:
            a.append("'{0}: ' + if ( \"{0}\" IS NULL, '', to_string( \"{0}\" ) )".format(get_field(i - 1 + add).name()))
        else:
            a.append("if ( \"{0}\" IS NULL, '', to_string( \"{0}\" ) )".format(get_field(i - 1 + add).name()))

    fieldName = r" + '\n' + ".join(a)

    return fieldName


def setupLabelFilterExpression(layer: QgsVectorLayer, rule_name: str, strictness: str) -> str:
    """
    Sets up label filter expression based on the rule name and the vector layer

    :param layer: QgsVectorLayer
    :param rule_name: str
    :return: str expression
    """

    expression = ''
    try:
        attNo = rule_name.split('|')[0].strip()
        attVal = '|'.join(rule_name.split('|')[1:]).strip()  # incase the name itself has '|' in it e.g. in 2d_SA
        attVals = [x.strip() for x in attVal.split(';')]
        attNo = int(attNo)
    except IndexError:
        # rule_name isn't properly setup with a vertical bar
        if rule_name.lower() != 'else':
            return expression
    except ValueError:
        # rule_name isn't properly setup using an integer as first value then attribute value e.g. 2 | C
        if rule_name.lower() != 'else':
            return expression

    if rule_name.lower() == 'else':
        expression = 'ELSE'
    else:
        fields = layer.fields()
        if fields.size() >= attNo:  # indexing starts at 1 for labelling properties
            field_name = fields.field(attNo - 1).name()
            cond = 'ILIKE'
            cond_helper = '' if strictness.lower() == 'strict' else '%'
            exp = []
            for a in attVals:
                e = "\"{0}\" {2} '{3}{1}{3}'".format(field_name, a.lower(), cond, cond_helper)
                exp.append(e)
            expression = ' OR '.join(exp)

    return expression


def setLabelProperties(label: QgsPalLayerSettings, properties: dict, layer: QgsVectorLayer) -> None:
    """
    Sets the label settings object to the user defined settings.

    :param label: QgsPalLayerSettings
    :param properties: dict user settings / properties
    :param layer: QgsVectorLayer
    :return: None
    """
    qv = Qgis.QGIS_VERSION_INT

    format = QgsTextFormat()

    # buffer
    buffer = QgsTextBufferSettings()
    buffer.setEnabled(properties['buffer'])
    format.setBuffer(buffer)

    # background
    background = QgsTextBackgroundSettings()
    background.setEnabled(properties['box'])
    background.setSizeType(QgsTextBackgroundSettings.SizeBuffer)
    background.setSize(QSizeF(0.5, 0.5))
    background.setStrokeColor(QColor(Qt.black))
    background.setStrokeWidth(0.1)
    format.setBackground(background)

    # placement
    if layer.geometryType() == QgsWkbTypes.PointGeometry:
        if qv < 32600:
            p = QgsPalLayerSettings.OrderedPositionsAroundPoint
        else:
            p = Qgis.LabelPlacement.OrderedPositionsAroundPoint
        d = properties['offsetXY'][0]
        offsetX = 0
        offsetY = 0
    elif layer.geometryType() == QgsWkbTypes.LineGeometry:
        if qv < 32600:
            p = QgsPalLayerSettings.Horizontal if properties['line_placement'].lower() == 'horizontal' else QgsPalLayerSettings.Line
        else:
            p = Qgis.LabelPlacement.Horizontal if properties['line_placement'].lower() == 'horizontal' else Qgis.LabelPlacement.Line
        d = properties['offsetXY'][0]
        offsetX = 0
        offsetY = 0
    elif layer.geometryType() == QgsWkbTypes.PolygonGeometry:
        if qv < 32600:
            p = QgsPalLayerSettings.OverPoint
        else:
            p = Qgis.LabelPlacement.OverPoint
        d = d = properties['offsetXY'][0]
        offsetX = properties['offsetXY'][0]
        offsetY = properties['offsetXY'][1]
    else:
        p = 0  # shouldn't occur

    # field name
    fieldName = getLabelFieldName(layer, properties)

    # apply
    label.fieldName = fieldName
    label.setFormat(format)
    label.isExpression = True
    label.placement = p
    label.dist = d
    label.xOffset = properties['offsetXY'][0]
    label.yOffset = properties['offsetXY'][1]
    if qv >= 32600:
        label.multilineAlign = Qgis.LabelMultiLineAlignment.Left
    else:
        label.multilineAlign = 0
    label.drawLabels = True


def tuflowqgis_apply_autoLabel_clayer(qgis: QgisInterface):
    error = False
    message = None
    canvas = qgis.mapCanvas()
    cLayer = canvas.currentLayer()

    if isinstance(cLayer, QgsVectorLayer):
        if not cLayer.labelsEnabled():
            labelProperties = findCustomLabelProperties(cLayer.name())
            if labelProperties['rule_based']:  # use QgsRuleBasedLabeling class
                labelAll = QgsPalLayerSettings()
                ruleAll = QgsRuleBasedLabeling.Rule(labelAll)
                for rule_name, prop in labelProperties['rule_based'].items():
                    label = QgsPalLayerSettings()
                    rule = QgsRuleBasedLabeling.Rule(label)
                    expression = setupLabelFilterExpression(cLayer, rule_name, prop['rule_strictness'])
                    rule.setFilterExpression(expression)
                    setLabelProperties(label, prop, cLayer)
                    ruleAll.appendChild(rule)
                labeling = QgsRuleBasedLabeling(ruleAll)
            else:  # use QgsVectorLayerSimpleLabeling class
                label = QgsPalLayerSettings()
                setLabelProperties(label, labelProperties, cLayer)
                labeling = QgsVectorLayerSimpleLabeling(label)

            cLayer.setLabeling(labeling)
            cLayer.setLabelsEnabled(True)
            cLayer.triggerRepaint()
        else:
            cLayer.setLabelsEnabled(False)

        canvas.refresh()

    return error, message


def find_waterLevelPoint(selection, plotLayer):
    """Finds snapped PLOT_P layer to selected XS layer

    QgsFeatureLayer selection: current selection in map window
    QgsVectorLayer plotLayer: PLOT_P layer
    """

    message = ''
    error = False
    intersectedPoints = []
    intersectedLines = []
    plotP = None
    plotL = None

    if plotLayer is None:
        error = True
        message = 'Could not find result gis layers.'
        return intersectedPoints, intersectedLines, message, error

    for plot in plotLayer:
        if '_PLOT_P' in plot.name():
            plotP = plot
        elif '_PLOT_L' in plot.name():
            plotL = plot
    if plotP is None and plotL is None:
        error = True
        message = 'Could not find result gis layers.'
        return intersectedPoints, intersectedLines, message, error

    for xSection in selection:
        if plotP is not None:
            found_intersect = False
            for point in plotP.getFeatures():
                if point.geometry().intersects(xSection.geometry()):
                    intersectedPoints.append(point['ID'].strip())
                    found_intersect = True
            if found_intersect:
                intersectedLines.append(None)
                continue
            else:
                intersectedPoints.append(None)
                if plotL is not None:
                    for line in plotL.getFeatures():
                        if line.geometry().intersects(xSection.geometry()):
                            intersectedLines.append(line['ID'].strip())
                            found_intersect = True
                if not found_intersect:
                    intersectedLines.append(None)
        else:
            intersectedPoints.append(None)
            if plotL is not None:
                found_intersect = False
                for line in plotL.getFeatures():
                    if line.geometry().intersects(xSection.geometry()):
                        intersectedLines.append(line['ID'].strip())
                        found_intersect = True
            if not found_intersect:
                intersectedLines.append(None)

    return intersectedPoints, intersectedLines, message, error


def getDirection(point1, point2, **kwargs):
    """
    Returns the direction the from the first point to the second point.

    :param point1: QgsPoint
    :param point2: QgsPoint
    :param kwargs: dict -> key word arguments
    :return: float direction (0 - 360 deg)
    """

    from math import atan, pi

    if 'x' in kwargs.keys():
        x = kwargs['x']
    else:
        x = point2.x() - point1.x()
    if 'y' in kwargs.keys():
        y = kwargs['y']
    else:
        y = point2.y() - point1.y()

    if x == y:
        if x > 0 and y > 0:  # first quadrant
            angle = 45.0
        elif x < 0 and y > 0:  # second quadrant
            angle = 135.0
        elif x < 0 and y < 0:  # third quadrant
            angle = 225.0
        elif x > 0 and y < 0:  # fourth quadrant
            angle = 315.0
        else:
            angle = None  # x and y are both 0 so point1 == point2

    elif abs(x) > abs(y):  # y is opposite, x is adjacent
        if x > 0 and y == 0:  # straight right
            angle = 0.0
        elif x > 0 and y > 0:  # first quadrant
            a = atan(abs(y) / abs(x))
            angle = a * 180.0 / pi
        elif x < 0 and y > 0:  # seond quadrant
            a = atan(abs(y) / abs(x))
            angle = 180.0 - (a * 180.0 / pi)
        elif x < 0 and y == 0:  # straight left
            angle = 180.0
        elif x < 0 and y < 0:  # third quadrant
            a = atan(abs(y) / abs(x))
            angle = 180.0 + (a * 180.0 / pi)
        elif x > 0 and y < 0:  # fourth quadrant
            a = atan(abs(y) / abs(x))
            angle = 360.0 - (a * 180.0 / pi)
        else:
            angle = None  # should never arise

    elif abs(y) > abs(x):  # x is opposite, y is adjacent
        if x > 0 and y > 0:  # first quadrant
            a = atan(abs(x) / abs(y))
            angle = 90.0 - (a * 180.0 / pi)
        elif x == 0 and y > 0:  # straighth up
            angle = 90.0
        elif x < 0 and y > 0:  # second quadrant
            a = atan(abs(x) / abs(y))
            angle = 90.0 + (a * 180.0 / pi)
        elif x < 0 and y < 0:  # third quadrant
            a = atan(abs(x) / abs(y))
            angle = 270.0 - (a * 180.0 / pi)
        elif x == 0 and y < 0:  # straight down
            angle = 270.0
        elif x > 0 and y < 0:  # fourth quadrant
            a = atan(abs(x) / abs(y))
            angle = 270.0 + (a * 180.0 / pi)
        else:
            angle = None  # should never arise

    else:
        angle = None  # should never arise

    return angle


def lineToPoints(feat, spacing, mapUnits, **kwargs):
    """
    Takes a line and converts it to points with additional vertices inserted at the max spacing

    :param feat: QgsFeature - Line to be converted to points
    :param spacing: float - max spacing to use when converting line to points
    :return: List, List - QgsPoint, Chainages
    """

    message = ""
    if feat.geometry().wkbType() == QgsWkbTypes.LineString or \
            feat.geometry().wkbType() == QgsWkbTypes.LineStringZ or \
            feat.geometry().wkbType() == QgsWkbTypes.LineStringM or \
            feat.geometry().wkbType() == QgsWkbTypes.LineStringZM:
        geom = feat.geometry().asPolyline()
    elif feat.geometry().wkbType() == QgsWkbTypes.MultiLineString or \
            feat.geometry().wkbType() == QgsWkbTypes.MultiLineStringZ or \
            feat.geometry().wkbType() == QgsWkbTypes.MultiLineStringM or \
            feat.geometry().wkbType() == QgsWkbTypes.MultiLineStringZM:
        mGeom = feat.geometry().asMultiPolyline()
        geom = []
        for g in mGeom:
            for p in g:
                geom.append(p)
    elif feat.geometry().wkbType() == QgsWkbTypes.Unknown:
        if 'inlcude_error_messaging' in kwargs:
            if kwargs['inlcude_error_messaging']:
                if feat.attributes():
                    id = feat.attributes()[0]
                    message = 'Feature with {0} = {1} (FID = {2}) has unknown geometry type, check input feature is valid.'.format(
                        feat.fields().names()[0], feat.attributes()[0], feat.id())
                else:
                    message = 'Feature with FID = {0} has unknown geometry type, check input feature is valid.'.format(
                        feat.id())
                return None, None, None, message
        return None, None, None
    else:
        if 'inlcude_error_messaging' in kwargs:
            if kwargs['inlcude_error_messaging']:
                if feat.attributes():
                    id = feat.attributes()[0]
                    message = 'Feature with {0} = {1} is not a line geometry type, check input feature is valid.'.format(
                        feat.fields().names()[0], feat.attributes()[0])
                else:
                    message = 'Feature with fid = {0} is not a line geometry type, check input feature is valid.'.format(
                        feat.id())
                return None, None, None, message
        return None, None, None
    pPrev = None
    points = []  # X, Y coordinates of point in line
    chainage = 0
    chainages = []  # list of chainages along the line that the points are located at
    directions = []  # list -> direction between the previous point and the current point
    for i, p in enumerate(geom):
        usedPoint = False  # point has been used and can move onto next point
        while not usedPoint:
            if i == 0:
                points.append(p)
                chainages.append(chainage)
                pPrev = p
                directions.append(None)  # no previous point so cannot have a direction
                usedPoint = True
            else:
                length = calculateLength(p, pPrev, mapUnits)
                if length is None:
                    if 'inlcude_error_messaging' in kwargs:
                        if kwargs['inlcude_error_messaging']:
                            return None, None, None, message
                    return None, None, None
                if length < spacing:
                    points.append(p)
                    chainage += length
                    chainages.append(chainage)
                    directions.append(getDirection(pPrev, p))
                    pPrev = p
                    usedPoint = True
                else:
                    # angle = asin((p.y() - pPrev.y()) / length)
                    # x = pPrev.x() + (spacing * cos(angle)) if p.x() - pPrev.x() >= 0 else pPrev.x() - (spacing * cos(angle))
                    # y = pPrev.y() + (spacing * sin(angle))
                    # newPoint = QgsPoint(x, y)
                    newPoint = createNewPoint(p, pPrev, length, spacing, mapUnits)
                    points.append(newPoint)
                    chainage += spacing
                    chainages.append(chainage)
                    directions.append(getDirection(pPrev, newPoint))
                    pPrev = newPoint

    if 'inlcude_error_messaging' in kwargs:
        if kwargs['inlcude_error_messaging']:
            return points, chainages, directions, message
    return points, chainages, directions


def getPathFromRel(dir, relPath, **kwargs):
    """
    return the full path from a relative reference

    :param dir: string -> directory
    :param relPath: string -> relative path
    :return: string - full path
    """

    if len(relPath) >= 2:
        if relPath[1] == ':':
            return relPath
        relPath = relPath.replace('/', os.sep)
        if relPath[:2] == "\\\\":
            return relPath

    outputDrive = kwargs['output_drive'] if 'output_drive' in kwargs.keys() else None
    variables_on = kwargs['variables_on'] if 'variables_on' in kwargs else False

    _components = relPath.split(os.sep)
    components = []
    for c in _components:
        components += c.split('\\')
    path = dir

    if outputDrive:
        components[0] = outputDrive

    for c in components:
        if c == '..':
            path = os.path.dirname(path)
        elif c == '.':
            continue
        else:
            found = False
            for p in os.walk(path):
                for d in p[1]:  # directory
                    if c.lower() == d.lower():
                        path = os.path.join(path, d)
                        found = True
                        break
                if found:
                    break
                for f in p[2]:  # files
                    if c.lower() == f.lower():
                        path = path = os.path.join(path, f)
                        found = True
                        break
                if found:
                    break
                # not found if it reaches this point
                path = os.path.join(path, c)
                break

    return path


def checkForOutputDrive(tcf, scenarios=()):
    """
    Checks for an output drive.

    :param tcf: str full tcf filepath
    :return: str output drive
    """

    drive = None
    read = True
    with open(tcf, 'r') as fo:
        for f in fo:
            if 'if scenario' in f.lower():
                ind = f.lower().find('if scenario')
                if '!' not in f[:ind]:
                    command, scenario = f.split('==', 1)
                    command = command.strip()
                    scenario = scenario.split('!')[0]
                    scenario = scenario.strip()
                    scenarios_ = scenario.split('|')
                    found = False
                    if scenarios == 'all':
                        found = True
                    else:
                        for scenario in scenarios_:
                            scenario = scenario.strip()
                            if scenario in scenarios:
                                found = True
                    if found:
                        read = True
                    else:
                        read = False
            if 'end if' in f.lower():
                ind = f.lower().find('end if')
                if '!' not in f[:ind]:
                    read = True
            if not read:
                continue
            if 'output drive' in f.lower():  # check if there is an 'if scenario' command
                ind = f.lower().find('output drive')  # get index in string of command
                if '!' not in f[:ind]:  # check to see if there is an ! before command (i.e. has been commented out)
                    command, drive = f.split('==', 1)  # split at == to get command and value
                    command = command.strip()  # strip blank spaces and new lines \n
                    drive = drive.split('!')[
                        0]  # split string by ! and take first entry i.e. remove any comments after command
                    drive = drive.strip()  # strip blank spaces and new lines \n

    return drive


def getOutputFolderFromTCF(tcf, **kwargs):
    """
    Looks for output folder command in tcf, 1D output folder in tcf, start 2D domain in tcf, and output folder in ecf

    :param tcf: str full tcf filepath
    :return: list -> str full file path to output folder [ 1d, 2d ]
    """

    outputDrive = kwargs['output_drive'] if 'output_drive' in kwargs.keys() else None
    variables = kwargs['variables'] if 'variables' in kwargs else {}
    scenarios = kwargs['scenarios'] if 'scenarios' in kwargs else []
    events = kwargs['events'] if 'events' in kwargs else []

    outputFolder1D = []
    outputFolder2D = []

    read = True
    try:
        with open(tcf, 'r') as fo:
            for f in fo:
                if 'if scenario' in f.lower():
                    ind = f.lower().find('if scenario')
                    if '!' not in f[:ind]:
                        command, scenario = f.split('==', 1)
                        command = command.strip()
                        scenario = scenario.split('!')[0]
                        scenario = scenario.strip()
                        scenarios_ = scenario.split('|')
                        found = False
                        if scenarios == 'all':
                            found = True
                        else:
                            for scenario in scenarios_:
                                scenario = scenario.strip()
                                if scenario in scenarios:
                                    found = True
                        if found:
                            read = True
                        else:
                            read = False
                if 'end if' in f.lower():
                    ind = f.lower().find('end if')
                    if '!' not in f[:ind]:
                        read = True
                if not read:
                    continue

                # check for 1D domain heading
                if 'start 1d domain' in f.lower():
                    ind = f.lower().find('start 1d domain')  # get index in string of command
                    if '!' not in f[:ind]:  # check to see if there is an ! before command (i.e. has been commented out)
                        subread = True
                        for subline in fo:
                            if 'end 1d domain' in subline.lower():
                                ind = subline.lower().find('end 1d domain')  # get index in string of command
                                if '!' not in subline[
                                              :ind]:  # check to see if there is an ! before command (i.e. has been commented out)
                                    break
                            if 'if scenario' in f.lower():
                                ind = f.lower().find('if scenario')
                                if '!' not in f[:ind]:
                                    command, scenario = f.split('==', 1)
                                    command = command.strip()
                                    scenario = scenario.split('!')[0]
                                    scenario = scenario.strip()
                                    scenarios_ = scenario.split('|')
                                    found = False
                                    if scenarios == 'all':
                                        found = True
                                    else:
                                        for scenario in scenarios_:
                                            scenario = scenario.strip()
                                            if scenario in scenarios:
                                                found = True
                                    if found:
                                        subread = True
                                    else:
                                        subread = False
                            if 'end if' in f.lower():
                                ind = f.lower().find('end if')
                                if '!' not in f[:ind]:
                                    subread = True
                            if not subread:
                                continue
                            if 'output folder' in subline.lower():  # check if there is an 'if scenario' command
                                ind = subline.lower().find('output folder')  # get index in string of command
                                if '!' not in subline[
                                              :ind]:  # check to see if there is an ! before command (i.e. has been commented out)
                                    command, folder = subline.split('==')  # split at == to get command and value
                                    command = command.strip()  # strip blank spaces and new lines \n
                                    folder = folder.split('!')[
                                        0]  # split string by ! and take first entry i.e. remove any comments after command
                                    folder = folder.strip()  # strip blank spaces and new lines \n
                                    folders = getAllFolders(os.path.dirname(tcf), folder, variables,
                                                            scenarios, events, outputDrive)
                                    outputFolder1D += folders

                # normal output folder
                if 'output folder' in f.lower():  # check if there is an 'if scenario' command
                    ind = f.lower().find('output folder')  # get index in string of command
                    if '!' not in f[:ind]:  # check to see if there is an ! before command (i.e. has been commented out)
                        command, folder = f.split('==', 1)  # split at == to get command and value
                        command = command.strip()  # strip blank spaces and new lines \n
                        folder = folder.split('!')[
                            0]  # split string by ! and take first entry i.e. remove any comments after command
                        folder = folder.strip()  # strip blank spaces and new lines \n
                        folders = getAllFolders(os.path.dirname(tcf), folder, variables, scenarios, events, outputDrive)
                        if '1D' in command:
                            # folder = getPathFromRel(os.path.dirname(tcf), folder, output_drive=outputDrive)
                            outputFolder1D += folders
                        else:
                            # folder = getPathFromRel(os.path.dirname(tcf), folder, output_drive=outputDrive)
                            outputFolder2D += folders

                # check for output folder in ECF
                if 'estry control file' in f.lower():
                    ind = f.lower().find('estry control file')
                    if '!' not in f[:ind]:
                        if 'estry control file auto' in f.lower():
                            path = '{0}.ecf'.format(os.path.splitext(tcf)[0])
                        command, relPath = f.split('==', 1)
                        command = command.strip()
                        relPath = relPath.split('!')[0]
                        relPath = relPath.strip()
                        files = getAllFolders(os.path.dirname(tcf), relPath, variables, scenarios, events, outputDrive)
                        # path = getPathFromRel(os.path.dirname(tcf), relPath, output_drive=outputDrive)
                        for file in files:
                            outputFolder1D += getOutputFolderFromTCF(file)  # check for output folder in TRD
                    if 'read file' in f.lower():
                        ind = f.lower().find('read file')
                        if '!' not in f[:ind]:
                            command, relPath = f.split('==', 1)
                            command = command.strip()
                            relPath = relPath.split('!')[0]
                            relPath = relPath.strip()
                            files = getAllFolders(os.path.dirname(tcf), relPath, variables, scenarios, events,
                                                  outputDrive)
                            for file in files:
                                res1D, res2D = getOutputFolderFromTCF(file, scenarios=scenarios, events=events,
                                                                      variables=variables, output_drive=outputDrive)
                                outputFolder1D += res1D
                                outputFolder2D += res2D

        if outputFolder2D is not None:
            if outputFolder1D is None:
                outputFolder1D = outputFolder2D[:]
    except Exception as e:
        pass

    return [outputFolder1D, outputFolder2D]


def getResultPathsFromTCF(fpath, **kwargs):
    """
    Get the result path locations from TCF

    :param fpaths: str full file path to tcf
    :return: str XMDF, str TPC
    """

    scenarios = kwargs['scenarios'] if 'scenarios' in kwargs.keys() else []
    events = kwargs['events'] if 'events' in kwargs.keys() else []
    outputZones = kwargs['output_zones'] if 'output_zones' in kwargs else []

    results2D = []
    results1D = []
    messages = []

    # check for output drive
    outputDrive = checkForOutputDrive(fpath, scenarios)

    # check for variables
    variables, error = getVariableNamesFromTCF(fpath, scenarios)
    if error:
        return results1D, results2D, messages

    # get output folders
    outputFolder1D, outputFolder2D = getOutputFolderFromTCF(fpath, variables=variables, output_drive=outputDrive,
                                                            scenarios=scenarios, events=events)
    outputFolders2D = []
    if outputZones:
        for opz in outputZones:
            if 'output folder' in opz:
                outputFolders2D.append(opz['output folder'])
            else:
                for opf2D in outputFolder2D:
                    outputFolders2D.append(os.path.join(opf2D, opz['name']))
    else:
        outputFolders2D += outputFolder2D

    # get 2D output
    basename = os.path.splitext(os.path.basename(fpath))[0]

    # split out event and scenario wildcards
    basenameComponents2D = basename.split('~')
    basenameComponents2D += scenarios
    basenameComponents2D += events
    for i, x in enumerate(basenameComponents2D):
        x = x.lower()
        if x == 's' or x == 's1' or x == 's2' or x == 's3' or x == 's4' or x == 's5' or x == 's5' or x == 's6' or \
                x == 's7' or x == 's8' or x == 's9' or x == 'e' or x == 'e1' or x == 'e2' or x == 'e3' or x == 'e4' or \
                x == 'e5' or x == 'e6' or x == 'e7' or x == 'e8' or x == 'e9':
            basenameComponents2D.pop(i)
    basenameComponents1D = basenameComponents2D[:]
    for opz in outputZones:  # only 2D results are output to output zone folder
        basenameComponents2D.append('{' + '{0}'.format(opz['name']) + '}')

    # search in folder for files that match name, scenarios, and events
    for opf2D in outputFolders2D:

        if opf2D is not None:
            if os.path.exists(opf2D):

                # if there are scenarios or events will have to do it the long way since i don't know what hte output name will be
                # if scenarios or events or outputZones:
                # try looking for xmdf and dat files
                for file in os.listdir(opf2D):
                    name, ext = os.path.splitext(file)
                    if ext.lower() == '.xmdf' or ext.lower() == '.dat':
                        matches = True
                        for x in basenameComponents2D:
                            if x.lower() not in name.lower():
                                matches = False
                                break
                        if matches:
                            results2D.append(os.path.join(opf2D, file))
                if not results2D:
                    messages.append("Could not find any matching mesh files for {0} in folder {1}".format(basename,
                                                                                                          opf2D))

            else:
                messages.append("2D output folder does not exist: {0}".format(opf2D))

    # get 1D output
    for opf2D in outputFolder2D:
        if opf2D is not None:
            outputFolderTPC = os.path.join(opf2D, 'plot')
            if os.path.exists(outputFolderTPC):
                matches = False
                for file in os.listdir(outputFolderTPC):
                    name, ext = os.path.splitext(file)
                    if ext.lower() == '.tpc':
                        matches = True
                        for x in basenameComponents1D:
                            if x not in name:
                                matches = False
                                break
                        if matches:
                            if check1DResultsForData(os.path.join(outputFolderTPC, file)):
                                results1D.append(os.path.join(outputFolderTPC, file))
                            break
        #	if not results1D:
        #		messages.append("Could not find any matching TPC files for {0} in folder {1}".format(basename,
        #		                                                                                     opf2D))
    # else:
    #	messages.append('Plot folder does not exist: {0}'.format(opf2D))

    return results1D, results2D, messages


def check1DResultsForData(tpc):
    """
    Checks to see if there is any 1D result data

    :param tpc: str full path to TPC file
    :return: bool True if there is data, False if there isn't
    """

    if Path(tpc).suffix.lower() == '.tpc':
        with open(tpc, 'r') as fo:
            for line in fo:
                if '==' not in line:
                    continue
                command, value = line.split('==', 1)
                if 'number 1d' in command.lower():
                    property, value = line.split('==')
                    value = int(value.split('!')[0].strip())
                    if value > 0:
                        return True
                elif 'number reporting location' in command.lower():
                    property, value = line.split('==')
                    value = int(value.split('!')[0].strip())
                    if value > 0:
                        return True
                elif '2d' in command.lower():
                    return True
    elif Path(tpc).suffix.lower() == '.gpkg':
        from .tuflow_results_gpkg import ResData_GPKG
        res = ResData_GPKG()
        err, msg = res.Load(tpc)
        b = False
        if err:
            return False
        try:
            b = res.gis_point_feature_count + res.gis_line_feature_count + res.gis_region_feature_count
            b = bool(b)
        except Exception as e:
            pass
        finally:
            res.close()
            return b

    return False


def loadLastFolder(layer, key):
    """
    Load the last folder location for user browsing

    :param layer: QgsVectorLayer or QgsMeshLayer or QgsRasterLayer
    :param key: str -> key value for settings
    :return: str
    """

    settings = QSettings()
    lastFolder = str(settings.value(key, os.sep))
    if len(lastFolder) > 0:  # use last folder if stored
        fpath = lastFolder
    else:
        if layer:  # if layer selected use the path to this
            dp = layer.dataProvider()
            ds = dp.dataSourceUri()
            fpath = os.path.dirname(ds)
        else:  # final resort to current working directory
            fpath = os.getcwd()

    return fpath


def loadSetting(key):
    """
    Load setting based on key.

    :param key: str
    :return: QVariant
    """

    settings = QSettings()
    savedSetting = settings.value(key)

    return savedSetting


def saveSetting(key, value):
    """
    Save setting using key

    :param key: str
    :param value: QVariant
    :return:
    """

    settings = QSettings()
    settings.setValue(key, value)


def getScenariosFromControlFile(controlFile, processedScenarios):
    """

    :param controlFile: string - control file location
    :param processedScenarios: list - list of already processed scenarios
    :return: list - processed and added scenarios
    """

    message = ''

    try:
        with open(controlFile, 'r') as fo:
            for f in fo:
                if 'if scenario' in f.lower():  # check if there is an 'if scenario' command
                    ind = f.lower().find('if scenario')  # get index in string of command
                    if '!' not in f[:ind]:  # check to see if there is an ! before command (i.e. has been commented out)
                        command, scenario = f.split('==', 1)  # split at == to get command and value
                        command = command.strip()  # strip blank spaces and new lines \n
                        scenario = scenario.split('!')[
                            0]  # split string by ! and take first entry i.e. remove any comments after command
                        scenario = scenario.strip()  # strip blank spaces and new lines \n
                        scenarios = scenario.split('|')  # split scenarios by | in case there is more than one specified
                        for scenario in scenarios:  # loop through scenarios and add to list if not already there
                            scenario = scenario.strip()
                            if scenario not in processedScenarios:
                                processedScenarios.append(scenario)
    except FileNotFoundError:
        return "File not found: {0}".format(controlFile), processedScenarios
    except IOError:
        return "Could not open file: {0}".format(controlFile), processedScenarios
    except Exception:
        return "Unexpected error when reading file: {0}".format(controlFile), processedScenarios

    return "", processedScenarios


def getScenariosFromTCF_v2(control_file, scenarios, events, settings=None):
    from .convert_tuflow_model_gis_format.conv_tf_gis_format.helpers.parser import get_commands
    from .convert_tuflow_model_gis_format.conv_tf_gis_format.helpers.settings import ConvertSettings
    from .convert_tuflow_model_gis_format.conv_tf_gis_format.helpers.file import TuflowPath

    if settings is None:
        control_file = TuflowPath(control_file)
        settings_ = ConvertSettings(*['-tcf', control_file, '-rf', control_file.parent])
        settings_.read_tcf()
    else:
        settings_ = settings.copy_settings(control_file, settings.output_folder)

    for command in get_commands(control_file, settings_):
        if command.is_start_define() and 'SCENARIO' in command.command:
            s = [x.strip() for x in command.value_orig.split('|') if
                 x.upper().strip() not in [y.upper() for y in scenarios]]
            scenarios.extend(s)
        elif command.is_start_define() and 'EVENT' in command.command and 'IF' in command.command:
            e = [x.strip() for x in command.value_orig.split('|') if
                 x.upper().strip() not in [y.upper() for y in events]]
            events.extend(e)
        elif command.is_control_file():
            for file in command.iter_files(settings_):
                cf = file.resolve()
                getScenariosFromTCF_v2(cf, scenarios, events, settings_)
        elif command.is_read_file():
            for file in command.iter_files(settings_):
                cf = file.resolve()
                getScenariosFromTCF_v2(cf, scenarios, events, settings_)


def getScenariosFromTcf(tcf):
    """

    :param tcf: string - tcf location
    :param iface: QgisInterface
    :return: bool error
    :return: string message
    :return: list scenarios
    """

    messages = []
    error = False
    scenarios = []
    variables, error = getVariableNamesFromTCF(tcf, 'all')
    if error:
        message = '\n'.join(messages)
        return True, message, scenarios
    dir = os.path.dirname(tcf)
    msg, scenarios = getScenariosFromControlFile(tcf, scenarios)
    if msg:
        error = True
        messages.append(msg)
    with open(tcf, 'r') as fo:
        for f in fo:
            if 'estry control file' in f.lower():
                ind = f.lower().find('estry control file')
                if '!' not in f[:ind]:
                    if 'estry control file auto' in f.lower():
                        path = '{0}.ecf'.format(os.path.splitext(tcf)[0])
                        if os.path.exists(path):
                            msg, scenarios = getScenariosFromControlFile(path, scenarios)
                            if msg:
                                error = True
                                messages.append(msg)
                        else:
                            error = True
                            messages.append("File not found: {0}".format(path))
                    else:
                        command, relPath = f.split('==', 1)
                        command = command.strip()
                        relPath = relPath.split('!')[0]
                        relPath = relPath.strip()
                        paths = getAllFolders(dir, relPath, variables, scenarios, [])
                        for path in paths:
                            msg, scenarios = getScenariosFromControlFile(path, scenarios)
                            if msg:
                                error = True
                                messages.append(msg)
            if 'geometry control file' in f.lower():
                ind = f.lower().find('geometry control file')
                if '!' not in f[:ind]:
                    command, relPath = f.split('==', 1)
                    command = command.strip()
                    relPath = relPath.split('!')[0]
                    relPath = relPath.strip()
                    paths = getAllFolders(dir, relPath, variables, scenarios, [])
                    for path in paths:
                        msg, scenarios = getScenariosFromControlFile(path, scenarios)
                        if msg:
                            error = True
                            messages.append(msg)
            if 'bc control file' in f.lower():
                ind = f.lower().find('bc control file')
                if '!' not in f[:ind]:
                    command, relPath = f.split('==', 1)
                    command = command.strip()
                    relPath = relPath.split('!')[0]
                    relPath = relPath.strip()
                    paths = getAllFolders(dir, relPath, variables, scenarios, [])
                    for path in paths:
                        msg, scenarios = getScenariosFromControlFile(path, scenarios)
            if 'event control file' in f.lower():
                ind = f.lower().find('event control file')
                if '!' not in f[:ind]:
                    command, relPath = f.split('==', 1)
                    command = command.strip()
                    relPath = relPath.split('!')[0]
                    relPath = relPath.strip()
                    paths = getAllFolders(dir, relPath, variables, scenarios, [])
                    for path in paths:
                        msg, scenarios = getScenariosFromControlFile(path, scenarios)
                        if msg:
                            error = True
                            messages.append(msg)
            if 'read file' in f.lower():
                ind = f.lower().find('read file')
                if '!' not in f[:ind]:
                    command, relPath = f.split('==', 1)
                    command = command.strip()
                    relPath = relPath.split('!')[0]
                    relPath = relPath.strip()
                    paths = getAllFolders(dir, relPath, variables, scenarios, [])
                    for path in paths:
                        msg, scenarios = getScenariosFromControlFile(path, scenarios)
                        if msg:
                            error = True
                            messages.append(msg)
            if 'read operating controls file' in f.lower():
                ind = f.lower().find('read operating controls file')
                if '!' not in f[:ind]:
                    command, relPath = f.split('==', 1)
                    command = command.strip()
                    relPath = relPath.split('!')[0]
                    relPath = relPath.strip()
                    paths = getAllFolders(dir, relPath, variables, scenarios, [])
                    for path in paths:
                        msg, scenarios = getScenariosFromControlFile(path, scenarios)
                        if msg:
                            error = True
                            messages.append(msg)
            if 'quadtree control file' in f.lower():
                ind = f.lower().find('quadtree control file')
                if '!' not in f[:ind]:
                    command, relPath = f.split('==', 1)
                    command = command.strip()
                    relPath = relPath.split('!')[0]
                    relPath = relPath.strip()
                    if relPath.lower() == 'single level':
                        continue
                    paths = getAllFolders(dir, relPath, variables, scenarios, [])
                    for path in paths:
                        msg, scenarios = getScenariosFromControlFile(path, scenarios)
                        if msg:
                            error = True
                            messages.append(msg)
    message = '\n'.join(messages)
    return error, message, scenarios


def getEventsFromTEF(tef):
    """
    Extracts all the events from a tef.

    :param tef: str full filepath to tef
    :return: list -> str event names
    """

    events = []

    with open(tef, 'r') as fo:
        for f in fo:
            if 'define event' in f.lower():
                ind = f.lower().find('define event')
                if '!' not in f[:ind]:
                    command, event = f.split('==', 1)
                    command = command.strip()
                    event = event.split('!')[0]
                    event = event.strip()
                    events.append(event)

    return events


def getEventsFromTCF(tcf):
    """
    Extracts all the events from a TCF file.

    :param tcf: str full filepath to tcf
    :return: list -> str event names
    """

    dir = os.path.dirname(tcf)
    events = []

    with open(tcf, 'r') as fo:
        for f in fo:
            if 'event file' in f.lower():
                ind = f.lower().find('event file')
                if '!' not in f[:ind]:
                    command, relPath = f.split('==', 1)
                    command = command.strip()
                    relPath = relPath.split('!')[0]
                    relPath = relPath.strip()
                    path = getPathFromRel(dir, relPath)
                    if os.path.exists(path):
                        events = getEventsFromTEF(path)

    return events


def getVariableFromControlFile(controlFile, variable, **kwargs):
    """
    Get variable value from control file

    :param controlFile: str full filepath to control file
    :param variable: str variable name
    :return: str variable value
    """

    chosen_scenario = kwargs['scenario'] if 'scenario' in kwargs.keys() else None

    value = None
    with open(controlFile, 'r') as fo:
        for f in fo:
            if chosen_scenario:
                if 'if scenario' in f.lower():  # check if there is an 'if scenario' command
                    ind = f.lower().find('if scenario')  # get index in string of command
                    if '!' not in f[:ind]:  # check to see if there is an ! before command (i.e. has been commented out)
                        command, scenario = f.split('==', 1)  # split at == to get command and value
                        command = command.strip()  # strip blank spaces and new lines \n
                        scenario = scenario.split('!')[
                            0]  # split string by ! and take first entry i.e. remove any comments after command
                        scenario = scenario.strip()  # strip blank spaces and new lines \n
                        scenarios = scenario.split('|')  # split scenarios by | in case there is more than one specified
                        if chosen_scenario in scenarios:
                            for sub_f in fo:
                                if 'set variable' in sub_f.lower():  # check if there is an 'if scenario' command
                                    ind = sub_f.lower().find('set variable')  # get index in string of command
                                    if '!' not in sub_f[
                                                  :ind]:  # check to see if there is an ! before command (i.e. has been commented out)
                                        command, local_value = sub_f.split('==',
                                                                           1)  # split at == to get command and value
                                        command = command.strip()  # strip blank spaces and new lines \n
                                        if variable in command:
                                            value = local_value.split('!')[
                                                0]  # split string by ! and take first entry i.e. remove any comments after command
                                            value = value.strip()  # strip blank spaces and new lines \n
                                if 'if scenario' in sub_f.lower() or 'else' in sub_f.lower() or 'end if' in sub_f.lower():
                                    break
            else:
                if 'set variable' in f.lower():  # check if there is an 'if scenario' command
                    ind = f.lower().find('set variable')  # get index in string of command
                    if '!' not in f[:ind]:  # check to see if there is an ! before command (i.e. has been commented out)
                        command, local_value = f.split('==', 1)  # split at == to get command and value
                        command = command.strip()  # strip blank spaces and new lines \n
                        if variable in command:
                            value = local_value.split('!')[
                                0]  # split string by ! and take first entry i.e. remove any comments after command
                            value = value.strip()  # strip blank spaces and new lines \n

    return value


def getVariableFromTCF(tcf, variable_name, **kwargs):
    """
    Get a variable value from TCF

    :param tcf: str full filepath to TCF
    :param variable_name: str variable name can be with or without chevrons
    :return: str variable value
    """

    scenario = kwargs['scenario'] if 'scenario' in kwargs.keys() else None

    message = 'Could not find the following files:\n'
    error = False
    dir = os.path.dirname(tcf)
    value = None
    variable = variable_name.strip('<<').strip('>>')

    # start with self
    value = getVariableFromControlFile(tcf, variable)
    if value is not None:
        return error, message, value

    with open(tcf, 'r') as fo:
        for f in fo:
            if 'estry control file' in f.lower():
                ind = f.lower().find('estry control file')
                if '!' not in f[:ind]:
                    if 'estry control file auto' in f.lower():
                        path = '{0}.ecf'.format(os.path.splitext(tcf)[0])
                    else:
                        command, relPath = f.split('==', 1)
                        command = command.strip()
                        relPath = relPath.split('!')[0]
                        relPath = relPath.strip()
                        path = getPathFromRel(dir, relPath)
                    if os.path.exists(path):
                        value = getVariableFromControlFile(path, variable)
                        if value is not None:
                            return error, message, value
                    else:
                        error = True
                        message += '{0}\n'.format(path)
            if 'geometry control file' in f.lower():
                ind = f.lower().find('geometry control file')
                if '!' not in f[:ind]:
                    command, relPath = f.split('==', 1)
                    command = command.strip()
                    relPath = relPath.split('!')[0]
                    relPath = relPath.strip()
                    path = getPathFromRel(dir, relPath)
                    if os.path.exists(path):
                        value = getVariableFromControlFile(path, variable)
                        if value is not None:
                            return error, message, value
                    else:
                        error = True
                        message += '{0}\n'.format(path)
            if 'bc control file' in f.lower():
                ind = f.lower().find('bc control file')
                if '!' not in f[:ind]:
                    command, relPath = f.split('==', 1)
                    command = command.strip()
                    relPath = relPath.split('!')[0]
                    relPath = relPath.strip()
                    path = getPathFromRel(dir, relPath)
                    if os.path.exists(path):
                        value = getVariableFromControlFile(path, variable)
                        if value is not None:
                            return error, message, value
                    else:
                        error = True
                        message += '{0}\n'.format(path)
            if 'event control file' in f.lower():
                ind = f.lower().find('event control file')
                if '!' not in f[:ind]:
                    command, relPath = f.split('==', 1)
                    command = command.strip()
                    relPath = relPath.split('!')[0]
                    relPath = relPath.strip()
                    path = getPathFromRel(dir, relPath)
                    if os.path.exists(path):
                        value = getVariableFromControlFile(path, variable)
                        if value is not None:
                            return error, message, value
                    else:
                        error = True
                        message += '{0}\n'.format(path)
            if 'read file' in f.lower():
                ind = f.lower().find('read file')
                if '!' not in f[:ind]:
                    command, relPath = f.split('==', 1)
                    command = command.strip()
                    relPath = relPath.split('!')[0]
                    relPath = relPath.strip()
                    path = getPathFromRel(dir, relPath)
                    if os.path.exists(path):
                        value = getVariableFromControlFile(path, variable, scenario=scenario)
                        if value is not None:
                            return error, message, value
                    else:
                        error = True
                        message += '{0}\n'.format(path)
            if 'read operating controls file' in f.lower():
                ind = f.lower().find('read operating controls file')
                if '!' not in f[:ind]:
                    command, relPath = f.split('==', 1)
                    command = command.strip()
                    relPath = relPath.split('!')[0]
                    relPath = relPath.strip()
                    path = getPathFromRel(dir, relPath)
                    if os.path.exists(path):
                        value = getVariableFromControlFile(path, variable)
                        if value is not None:
                            return error, message, value
                    else:
                        error = True
                        message += '{0}\n'.format(path)
            if 'quadtree control file' in f.lower():
                ind = f.lower().find('quadtree control file')
                if '!' not in f[:ind]:
                    command, relPath = f.split('==', 1)
                    command = command.strip()
                    relPath = relPath.split('!')[0]
                    relPath = relPath.strip()
                    if relPath.lower() == 'single level':
                        continue
                    path = getPathFromRel(dir, relPath)
                    if os.path.exists(path):
                        value = getVariableFromControlFile(path, variable)
                        if value is not None:
                            return error, message, value
                    else:
                        error = True
                        message += '{0}\n'.format(path)
    return error, message, value


def getCellSizeFromTGC(tgc):
    """
    Extracts teh cell size from TGC

    :param tgc: str full filepath to TGC
    :return: float cell size
    """
    cellSize = None
    error = True
    variable = False
    with open(tgc, 'r') as fo:
        for f in fo:
            if 'cell size' in f.lower():
                ind = f.lower().find('cell size')
                if '!' not in f[:ind]:
                    command, size = f.split('==', 1)
                    command = command.strip()
                    size = size.split('!')[0]
                    size = size.strip()
                    try:
                        float(size)
                        cellSize = size
                        error = False
                        variable = False
                    except ValueError:
                        # could be a variable <<cell_size>>
                        if '<<' in size and '>>' in size:
                            cellSize = size
                            error = False
                            variable = True
                        else:
                            cellSize = None
                            error = True
                            variable = False
                    except:
                        cellSize = None
                        error = True
                        variable = False

    return cellSize, variable, error


def getCellSizeFromTCF(tcf, **kwargs):
    """
    Extracts the cell size from TCF.

    :param tcf: str full filepath to tcf
    :return: float cell size
    """

    scenario = kwargs['scenario'] if 'scenario' in kwargs.keys() else None

    dir = os.path.dirname(tcf)
    cellSize = None

    with open(tcf, 'r') as fo:
        for f in fo:
            if 'geometry control file' in f.lower():
                ind = f.lower().find('geometry control file')
                if '!' not in f[:ind]:
                    command, relPath = f.split('==', 1)
                    command = command.strip()
                    relPath = relPath.split('!')[0]
                    relPath = relPath.strip()
                    path = getPathFromRel(dir, relPath)
                    if os.path.exists(path):
                        cellSize, variable, error = getCellSizeFromTGC(path)
                        if not error:
                            if not variable:
                                cellSize = float(cellSize)
                                return cellSize  # return as float
                            else:
                                error, message, cellSize = getVariableFromTCF(tcf, cellSize, scenario=scenario)
                                if not error:
                                    try:
                                        cellSize = float(cellSize)
                                        return cellSize
                                    except ValueError:
                                        return None
                                    except:
                                        return None
                                else:
                                    return None
                        else:
                            return None


def getOutputZonesFromTCF(tcf, **kwargs):
    """
    Extracts available output zones from TCF

    :param tcf: str full file path to file
    :param kwargs: dict
    :return: list -> dict -> { name: str, output folder: str }
    """

    dir = os.path.dirname(tcf)
    outputZones = kwargs['output_zones'] if 'output_zones' in kwargs else []
    variables = kwargs['variables'] if 'variables' in kwargs else []

    with open(tcf, 'r') as fo:
        for f in fo:
            if 'define output zone' in f.lower():
                ind = f.lower().find('define output zone')
                if '!' not in f[:ind]:
                    outputProp = {}
                    command, name = f.split('==', 1)
                    command = command.strip()
                    name = name.split('!')[0].strip()
                    if name not in outputProp:
                        outputProp['name'] = name
                    for subf in fo:
                        if 'end define' in subf.lower():
                            subind = subf.lower().find('end define')
                            if '!' not in subf[:subind]:
                                break
                        elif 'output folder' in subf.lower():
                            subind = subf.lower().find('output folder')
                            if '!' not in subf[:subind]:
                                command, relPath = subf.split('==', 1)
                                command = command.strip()
                                relPath = relPath.split('!')[0].strip()
                                path = getPathFromRel(dir, relPath)
                                outputProp['output folder'] = path
                    outputZones.append(outputProp)
            if 'read file' in f.lower():
                ind = f.lower().find('read file')
                if '!' not in f[:ind]:
                    command, relPath = f.split('==', 1)
                    command = command.strip()
                    relPath = relPath.split('!')[0]
                    relPath = relPath.strip()
                    path = getPathFromRel(dir, relPath)
                    if os.path.exists(path):
                        outputZones = getOutputZonesFromTCF(path, output_zones=outputZones)

    return outputZones


def removeLayer(lyr):
    """
    Removes the layer from the TOC once only. This is for when it the same layer features twice in the TOC.

    :param lyr: QgsVectorLayer
    :return: void
    """

    if lyr is not None:
        legint = QgsProject.instance().layerTreeRoot()

        # grab all nodes that are QgsMapLayers - get to node bed rock i.e. not a group
        nodes = []
        for child in legint.children():
            children = [child]
            while children:
                nd = children[0]
                if nd.children():
                    children += nd.children()
                else:
                    nodes.append(nd)
                children = children[1:]
        # now loop through nodes and turn on/off visibility based on settings
        for i, child in enumerate(nodes):
            lyrName = lyr.name()
            childName = child.name()
            if child.name() == lyr.name() or child.name() == '{0} Point'.format(
                    lyr.name()) or child.name() == '{0} LineString'.format(
                lyr.name()) or child.name() == '{0} Polygon'.format(lyr.name()):
                legint.removeChildNode(child)


def getVariableNamesFromControlFile(controlFile, variables, scenarios=()):
    """
    Gets all variable names and values from control file based on seleected scenarios.

    :param controlFile: str full path to control file
    :param variables: dict already collected variables
    :param scenarios: list -> str scenario name
    :return: dict { variable name: [ value list ] }
    """

    read = True
    with open(controlFile, 'r') as fo:
        try:
            for f in fo:
                if 'if scenario' in f.lower():
                    ind = f.lower().find('if scenario')
                    if '!' not in f[:ind]:
                        command, scenario = f.split('==', 1)
                        command = command.strip()
                        scenario = scenario.split('!')[0]
                        scenario = scenario.strip()
                        scenarios_ = scenario.split('|')
                        found = False
                        if scenarios == 'all':
                            found = True
                        else:
                            for scenario in scenarios_:
                                scenario = scenario.strip()
                                if scenario in scenarios:
                                    found = True
                        if found:
                            read = True
                        else:
                            read = False
                elif 'end if' in f.lower():
                    ind = f.lower().find('end if')
                    if '!' not in f[:ind]:
                        read = True
                elif not read:
                    continue
                elif 'set variable' in f.lower():
                    ind = f.lower().find('set variable')
                    if '!' not in f[:ind]:
                        command, value = f.split('==', 1)
                        command = command.strip()
                        variable = command[12:].strip()
                        value = value.split('!')[0]
                        value = value.strip()
                        if variable.lower() not in variables:
                            variables[variable.lower()] = []
                        variables[variable.lower()].append(value)
        except UnicodeDecodeError:
            msgBox = QMessageBox()
            msgBox.setIcon(QMessageBox.Critical)
            msgBox.setWindowTitle("Load Results")
            msgBox.setTextFormat(Qt.RichText)
            msgBox.setText(
                "Encoding error:<br>{0}<br><a href='https://wiki.tuflow.com/index.php?title=TUFLOW_Viewer#Loading_Results'>wiki.tuflow.com/index.php?title=TUFLOW_Viewer#Loading_Results</a>".format(
                    controlFile))
            msgBox.exec()
            return {}, True

    return variables, False


def getVariableNamesFromTCF(tcf, scenarios=()):
    """
    Gets all variable names and values from tcf based on selected scenarios

    :param tcf: str full path to control file
    :param scenarios: list -> str scenario name
    :return: dict { variable name: [ value list ] }
    """

    dir = os.path.dirname(tcf)
    variables = {}
    # first look for variables in tcf
    variables, error = getVariableNamesFromControlFile(tcf, variables, scenarios)
    if error:
        return {}, True
    # then look for variables in other control files
    read = True
    with open(tcf, 'r') as fo:
        try:
            for f in fo:
                if 'if scenario' in f.lower():
                    ind = f.lower().find('if scenario')
                    if '!' not in f[:ind]:
                        command, scenario = f.split('==', 1)
                        command = command.strip()
                        scenario = scenario.split('!')[0]
                        scenario = scenario.strip()
                        scenarios_ = scenario.split('|')
                        found = False
                        if scenarios == 'all':
                            found = True
                        else:
                            for scenario in scenarios_:
                                scenario = scenario.strip()
                                if scenario in scenarios:
                                    found = True
                        if found:
                            read = True
                        else:
                            read = False
                if 'end if' in f.lower():
                    ind = f.lower().find('end if')
                    if '!' not in f[:ind]:
                        read = True
                if not read:
                    continue
                if 'estry control file' in f.lower():
                    ind = f.lower().find('estry control file')
                    if '!' not in f[:ind]:
                        if 'estry control file auto' in f.lower():
                            path = '{0}.ecf'.format(os.path.splitext(tcf)[0])
                        else:
                            command, relPath = f.split('==', 1)
                            command = command.strip()
                            relPath = relPath.split('!')[0]
                            relPath = relPath.strip()
                            path = getPathFromRel(dir, relPath)
                            if os.path.exists(path):
                                variables, error = getVariableNamesFromControlFile(path, variables, scenarios)
                                if error:
                                    return {}, True
                if 'geometry control file' in f.lower():
                    ind = f.lower().find('geometry control file')
                    if '!' not in f[:ind]:
                        command, relPath = f.split('==', 1)
                        command = command.strip()
                        relPath = relPath.split('!')[0]
                        relPath = relPath.strip()
                        path = getPathFromRel(dir, relPath)
                        if os.path.exists(path):
                            variables, error = getVariableNamesFromControlFile(path, variables, scenarios)
                            if error:
                                return {}, True
                if 'bc control file' in f.lower():
                    ind = f.lower().find('bc control file')
                    if '!' not in f[:ind]:
                        command, relPath = f.split('==', 1)
                        command = command.strip()
                        relPath = relPath.split('!')[0]
                        relPath = relPath.strip()
                        path = getPathFromRel(dir, relPath)
                        if os.path.exists(path):
                            variables, error = getVariableNamesFromControlFile(path, variables, scenarios)
                            if error:
                                return {}, True
                if 'event control file' in f.lower():
                    ind = f.lower().find('event control file')
                    if '!' not in f[:ind]:
                        command, relPath = f.split('==', 1)
                        command = command.strip()
                        relPath = relPath.split('!')[0]
                        relPath = relPath.strip()
                        path = getPathFromRel(dir, relPath)
                        if os.path.exists(path):
                            variables, error = getVariableNamesFromControlFile(path, variables, scenarios)
                            if error:
                                return {}, True
                if 'read file' in f.lower():
                    ind = f.lower().find('read file')
                    if '!' not in f[:ind]:
                        command, relPath = f.split('==', 1)
                        command = command.strip()
                        relPath = relPath.split('!')[0]
                        relPath = relPath.strip()
                        path = getPathFromRel(dir, relPath)
                        if os.path.exists(path):
                            variables, error = getVariableNamesFromControlFile(path, variables, scenarios)
                            if error:
                                return {}, True
                if 'read operating controls file' in f.lower():
                    ind = f.lower().find('read operating controls file')
                    if '!' not in f[:ind]:
                        command, relPath = f.split('==', 1)
                        command = command.strip()
                        relPath = relPath.split('!')[0]
                        relPath = relPath.strip()
                        path = getPathFromRel(dir, relPath)
                        if os.path.exists(path):
                            variables, error = getVariableNamesFromControlFile(path, variables, scenarios)
                            if error:
                                return {}, True
                if 'quadtree control file' in f.lower():
                    ind = f.lower().find('quadtree control file')
                    if '!' not in f[:ind]:
                        command, relPath = f.split('==', 1)
                        command = command.strip()
                        relPath = relPath.split('!')[0]
                        relPath = relPath.strip()
                        if relPath.lower() == 'single level':
                            continue
                        path = getPathFromRel(dir, relPath)
                        if os.path.exists(path):
                            variables, error = getVariableNamesFromControlFile(path, variables, scenarios)
                            if error:
                                return {}, True
                if 'quadtree control file' in f.lower():
                    ind = f.lower().find('quadtree control file')
                    if '!' not in f[:ind]:
                        command, relPath = f.split('==')
                        command = command.strip()
                        relPath = relPath.split('!')[0]
                        relPath = relPath.strip()
                        if relPath.lower() == 'single level':
                            continue
                        path = getPathFromRel(dir, relPath)
                        if os.path.exists(path):
                            variables, error = getVariableNamesFromControlFile(path, variables, scenarios)
                            if error:
                                return {}, True
        except UnicodeDecodeError:
            msgBox = QMessageBox()
            msgBox.setIcon(QMessageBox.Critical)
            msgBox.setWindowTitle("Load Results")
            msgBox.setTextFormat(Qt.RichText)
            msgBox.setText(
                "Encoding error:<br>{0}<br><a href='https://wiki.tuflow.com/index.php?title=TUFLOW_Viewer#Loading_Results'>wiki.tuflow.com/index.php?title=TUFLOW_Viewer#Loading_Results</a>".format(
                    controlFile))
            msgBox.exec()
            return {}, True

    return variables, False


def loadGisFile(iface, path, group, processed_paths, processed_layers, error, log, crs, visible=True):
    """
    Load GIS file (vector or raster). If layer is already is processed_paths, layer won't be loaded again.

    :param iface: QgsInterface
    :param path: str full path to file
    :param group: QgsNodeTreeGroup
    :param processed_paths: list -> str file paths already processed
    :param processed_layers: list -> QgsMapLayer
    :param error: bool
    :param log: str
    :return: list -> str processed path, list -> QgsMapLayer, bool, str
    """

    ext = os.path.splitext(path)[1]
    if '|layername=' in path:
        try:
            db, layer = path.split('|layername=')
            if os.path.exists(db):
                layers = get_table_names(db)
                if layer.lower() in [x.lower() for x in layers]:
                    layer = layers[[x.lower() for x in layers].index(layer.lower())]
                    p = '{0}|layername={1}'.format(db, layer)
                    try:
                        lyr = iface.addVectorLayer(p, layer, 'ogr')
                        loaded = True
                    except:
                        loaded = False
                    if not loaded:
                        try:
                            lyr = iface.addRasterLayer(p, layer, 'gdal')
                            loaded = True
                        except:
                            loaded = False
                    assert (loaded)
                    group.addLayer(lyr)
                    processed_paths.append(path)
                    processed_layers.append(lyr)
                    if crs is None:
                        crs = lyr.crs()
                else:
                    error = True
                    log += '{0}\n'.format(path)
            else:
                error = True
                log += '{0}\n'.format(path)
        except Exception as e:
            error = True
            log += '{0}\n'.format(path)
    elif ext.lower() == '.mid':
        path = '{0}.mif'.format(os.path.splitext(path)[0])
        ext = '.mif'
    elif ext.lower() == '.shp':
        try:
            if os.path.exists(path):
                lyr = iface.addVectorLayer(path, os.path.basename(os.path.splitext(path)[0]),
                                           'ogr')
                group.addLayer(lyr)
                processed_paths.append(path)
                processed_layers.append(lyr)
                if crs is None:
                    crs = lyr.crs()
            else:
                error = True
                log += '{0}\n'.format(path)
        except Exception as e:
            error = True
            log += '{0}\n'.format(path)
    elif ext.lower() == '.mif':
        try:
            if os.path.exists(path):
                # lyr = iface.addVectorLayer(path, os.path.basename(os.path.splitext(path)[0]),
                #                            'ogr')
                lyrName = os.path.basename(os.path.splitext(path)[0])
                dblyr = QgsVectorLayer(path, lyrName)
                tablenames = [x.split('!!::!!')[1:] for x in dblyr.dataProvider().subLayers()]
                for table in tablenames:
                    if 'point' in table[2].lower():
                        lyrName_ = '{0}_P'.format(lyrName)
                    elif 'line' in table[2].lower():
                        lyrName_ = '{0}_L'.format(lyrName)
                    else:
                        lyrName_ = '{0}_R'.format(lyrName)
                    uri = "{0}|layername={1}|geometrytype={2}".format(path, table[0], table[2])
                    lyr = QgsVectorLayer(uri, lyrName_, 'ogr')
                    QgsProject.instance().addMapLayer(lyr)
                    for name, layer in QgsProject.instance().mapLayers().items():
                        # if lyrName in layer.name():
                        if lyrName_ in layer.name():
                            group.addLayer(layer)
                            processed_paths.append(path)
                            processed_layers.append(layer)
            else:
                error = True
                log += '{0}\n'.format(path)
        except:
            error = True
            log += '{0}\n'.format(path)
    elif ext.lower() == '.asc' or ext.lower() == '.flt' or ext.lower() == '.dem' or ext.lower() == '.txt' or ext.lower() == '.tif' or ext.lower() == '.hdr':
        if ext.lower() == '.hdr':
            path = '{0}.flt'.format(os.path.splitext(path)[0])
        try:
            if os.path.exists(path):
                lyr = iface.addRasterLayer(path, os.path.basename(os.path.splitext(path)[0]),
                                           'gdal')
                group.addLayer(lyr)
                processed_paths.append(path)
                processed_layers.append(lyr)
                # check raster crs
                lyrCrs = lyr.crs()
                if lyrCrs.srsid() != crs.srsid():
                    if not os.path.exists("{0}.prj".format(os.path.splitext(path)[0])):
                        lyr.setCrs(crs)
            else:
                error = True
                log += '{0}\n'.format(path)
        except:
            error = True
            log += '{0}\n'.format(path)
    else:
        error = True
        log += '{0}\n'.format(path)

    try:
        if lyr.isValid():
            nd = QgsProject.instance().layerTreeRoot().findLayer(lyr.id())
            nd.setItemVisibilityChecked(visible)
    except Exception as e:
        pass

    return processed_paths, processed_layers, error, log, crs


class LoadGisFiles(QObject):
    start_layer_load = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, model_file_layers, prog_bar):
        QObject.__init__(self)
        self.prog_bar = prog_bar
        self.model_file_layers = model_file_layers
        self.err = False
        self.msg = ''

    def init_prog_bar(self):
        self._prog_text = self.prog_bar.layout().itemAt(0).widget()
        self._prog_bar = self.prog_bar.layout().itemAt(1).widget()
        self.prog = 0
        QgsApplication.processEvents()

    def update_progress(self, lyr_name):
        self._prog_text.setText('Loading: {0}'.format(lyr_name))
        self.prog += 1
        self._prog_bar.setValue(self.prog)
        QgsApplication.processEvents()

    def loadLayersIntoWorkspace(self, root, layers, options=None, insert_before=None):
        # lyrs = QgsProject.instance().addMapLayers(layers, False)
        files_failed = []
        i = -1
        if insert_before:
            try:
                i = insert_before.parent().children().index(insert_before)
            except ValueError:
                i = -1
        for lyr in layers:
            try:
                lyrname = '('.join(lyr.split('(')[1:]).split(',')[1].strip()
            except Exception as e:
                print(lyr)
                print('ERROR: {0}'.format(e))
                continue
            self.start_layer_load.emit(lyrname)
            self.update_progress(lyrname)
            maplyr = eval(lyr)
            if not maplyr.isValid():
                files_failed.append(lyrname)
                continue
            QgsProject.instance().addMapLayer(maplyr, False)
            tuflowqgis_apply_check_tf_clayer(None, layer=maplyr)
            if insert_before and i != -1:
                root.insertChildNode(i, QgsLayerTreeLayer(maplyr))
                i += 1
            else:
                root.addChildNode(QgsLayerTreeLayer(maplyr))
            if options is not None and options.load_raster_method == 'invisible' and isinstance(maplyr, QgsRasterLayer):
                node = root.findLayer(maplyr.id())
                node.setItemVisibilityChecked(False)

        return files_failed

    def loadGisFiles(self):
        from .convert_tuflow_model_gis_format.conv_tf_gis_format.helpers.gis import (ogr_iter_geom, get_database_name,
                                                                                     ogr_format,
                                                                                     ogr_format_2_ext,
                                                                                     ogr_geometry_name,
                                                                                     ogr_basic_geom_type,
                                                                                     GIS_SHP, gdal_format, GRID_GPKG,
                                                                                     GIS_UNKNOWN)
        options = LoadTcfOptions()
        root = QgsProject.instance().layerTreeRoot()
        group = None
        layers = []
        layers_order_key = {}
        gis_files = []
        self.err = False
        files_failed = []
        self.init_prog_bar()
        for cf in self.model_file_layers:
            swmm_inp = False
            for gis_file in cf.gis():
                for i, swmm_inp_lyrs in enumerate(cf.swmm_inp_lyrs):
                    if gis_file in swmm_inp_lyrs:
                        swmm_inp = True
                        break
                gis_file_ = gis_file
                QgsApplication.processEvents()
                if str(gis_file) in gis_files:
                    continue
                db, lyrname = get_database_name(gis_file)
                fmt = ogr_format(gis_file)
                if fmt == GIS_UNKNOWN:
                    continue
                is_prj = False
                if fmt == GIS_SHP and Path(db).suffix.lower() == '.prj':
                    is_prj = True
                    db = str(Path(db).with_suffix('.shp'))
                    gis_file = f'{db} >> {lyrname}'
                ext = ogr_format_2_ext(fmt)
                for geom in ogr_iter_geom(gis_file):
                    if geom is None:
                        if not is_prj:
                            self.err = True
                            if gis_file.suffix.lower() != '.gpkg':
                                db, lyr = get_database_name(gis_file)
                                files_failed.append(str(db))
                            else:
                                files_failed.append(str(gis_file))
                        # continue

                    if geom is not None:
                        geom = ogr_basic_geom_type(geom, True)
                    layer_uri = f'{db}|layername={lyrname}'
                    if ext.lower() == '.mif' and geom is not None:
                        geom_name = ogr_geometry_name(geom)
                        if geom_name:
                            layer_uri = f'{layer_uri}|geometrytype={geom_name}'
                    lyr = "QgsVectorLayer(r'{0}', '{1}', 'ogr')".format(layer_uri, lyrname)
                    # if not lyr.isValid():
                    # 	files_failed.append(layer_uri)
                    # 	self.err = True
                    # 	continue

                    layers.append(lyr)
                    i = self.model_file_layers.index(cf, gis_file_)
                    layers_order_key[lyr] = i
                gis_files.append(str(gis_file))

            if options.load_raster_method != 'no':
                for grid_file in cf.grid():
                    for i, swmm_inp_lyrs in enumerate(cf.swmm_inp_lyrs):
                        if grid_file in swmm_inp_lyrs:
                            swmm_inp = True
                            break
                    if str(grid_file) in gis_files:
                        continue
                    db, lyrname = get_database_name(grid_file)
                    fmt = gdal_format(grid_file)
                    if fmt == GRID_GPKG:
                        layer_uri = f'GPKG:{db}:{lyrname}'
                    else:
                        layer_uri = db

                    lyr = "QgsRasterLayer(r'{0}', '{1}', 'gdal')".format(layer_uri, lyrname)
                    # if not lyr.isValid():
                    # 	files_failed.append(layer_uri)
                    # 	self.err = True
                    # 	continue

                    layers.append(lyr)
                    i = self.model_file_layers.index(cf, grid_file)
                    layers_order_key[lyr] = i
                    gis_files.append(str(grid_file))

            for table_layer in cf.table():
                for i, swmm_inp_lyrs in enumerate(cf.swmm_inp_lyrs):
                    if table_layer in swmm_inp_lyrs:
                        swmm_inp = True
                        break
                db, lyrname = get_database_name(table_layer)
                layer_uri = f'{db}|layername={lyrname}|geometrytype=None|uniqueGeometryType=yes'
                lyr = "QgsVectorLayer(r'{0}', '{1}', 'ogr')".format(layer_uri, lyrname)
                layers.append(lyr)
                i = self.model_file_layers.index(cf, table_layer)
                layers_order_key[lyr] = i
                gis_files.append(str(table_layer))

            if options.grouped and not swmm_inp:
                group = root.addGroup(cf.name)
                layers = sortLayers(layers, options, layers_order_key)
                failed_lyrs = self.loadLayersIntoWorkspace(group, layers, options)
                if failed_lyrs:
                    self.err = True
                    files_failed.extend(failed_lyrs)
                layers.clear()
                layers_order_key.clear()
                gis_files.clear()
            if swmm_inp:
                first_group = None
                for i, inp_name in enumerate(cf.swmm_inp_name):
                    if options.grouped:
                        if not group or group.name() != cf.name:
                            group = root.addGroup(cf.name)
                        inp_group = group.addGroup(inp_name)
                    else:
                        inp_group = root.addGroup(inp_name)
                    if not first_group:
                        first_group = inp_group
                    layers_ = []
                    for lyr in cf.swmm_inp_lyrs[i]:
                        i = gis_files.index(str(lyr))
                        layers_.append(layers.pop(i))
                        gis_files.pop(i)
                    failed_lyrs = self.loadLayersIntoWorkspace(inp_group, layers_, options)
                    if failed_lyrs:
                        self.err = True
                        files_failed.extend(failed_lyrs)
                if layers and options.grouped:
                    layers = sortLayers(layers, options, layers_order_key)
                    failed_lyrs = self.loadLayersIntoWorkspace(group, layers, options, insert_before=first_group)
                    layers.clear()
                    layers_order_key.clear()
                    gis_files.clear()
                swmm_inp = False

        if not options.grouped:
            layers = sortLayers(layers, options, layers_order_key)
            failed_lyrs = self.loadLayersIntoWorkspace(root, layers, options)
            if failed_lyrs:
                self.err = True
                files_failed.extend(failed_lyrs)

        self.msg = 'Failed to load the following layers:\n{0}'.format('\n'.join(files_failed))
        self.finished.emit()


class ControlFileLayers(QObject):
    layer_added = pyqtSignal(str)

    def __init__(self, control_file):
        QObject.__init__(self)
        self.name = control_file.name
        self._paths_gis = []
        self._paths_grid = []
        self._paths_table = []
        self._paths_all = []
        self.swmm_inp_lyrs = []
        self.swmm_inp_lyrs_exploded = []
        self.swmm_inp_name = []

    def _get_name(self, path):
        if '>>' in path.name:
            db, lyr = [x.strip() for x in path.name.split('>>')]
        else:
            db, lyr = path.name, path.name
        if Path(db).suffix.lower() == '.gpkg':
            name = path.name
        else:
            name = db

        return name

    def index(self, path):
        paths_all = [str(p) for p in self._paths_all]
        if str(path) in paths_all:
            return paths_all.index(str(path))
        else:
            return -1

    def count(self):
        return len(self._paths_grid) + len(self._paths_gis) + len(self._paths_table)

    def add_lyr(self, path):
        self._paths_all.append(path)

    def add_gis(self, path):
        self._paths_gis.append(path)
        self.layer_added.emit(self._get_name(path))

    def add_grid(self, path):
        self._paths_grid.append(path)
        self.layer_added.emit(self._get_name(path))

    def add_table(self, path):
        self._paths_table.append(path)
        self.layer_added.emit(self._get_name(path))

    def gis(self):
        for p in self._paths_gis:
            yield p

    def grid(self):
        for p in self._paths_grid:
            yield p

    def table(self):
        for p in self._paths_table:
            yield p


class ModelFileLayers(QObject):
    layer_added = pyqtSignal(str)

    def __init__(self):
        QObject.__init__(self)
        self._cfs = []

    def __iter__(self):
        order = {'.tcf': 0, '.ecf': 1, '.tbc': 2, '.tgc': 3, '.qcf': 4, 'toc': 5, 'trfcf': 6, 'trfc': 6, '': 7, None: 7}
        for cf in sorted(self._cfs, key=lambda x: order.get(Path(x.name).suffix.lower()) if order.get(
                Path(x.name).suffix.lower()) is not None else 100):
            yield cf

    def index(self, cf, path):
        if cf not in self._cfs:
            return -1
        i = self._cfs.index(cf)
        cf_ = self._cfs[i]
        count = sum(x.count() for x in self._cfs[:i])
        return count + cf.index(path)

    def count(self):
        return sum(x.count() for x in self._cfs)

    def add(self, cf):
        self._cfs.append(cf)
        cf.layer_added.connect(self.layer_added_)

    def layer_added_(self, e):
        self.layer_added.emit(e)


class LoadGisFromControlFile(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, model_file_layers, control_file, settings=None, scenarios=(), events=()):
        QObject.__init__(self)
        self.model_file_layers = model_file_layers
        self.control_file = control_file
        self.settings = settings
        self.scenarios = scenarios + events

    def loadGisFromControlFile_v2(self):
        from .convert_tuflow_model_gis_format.conv_tf_gis_format.helpers.control_file import get_commands
        from .convert_tuflow_model_gis_format.conv_tf_gis_format.helpers.settings import ConvertSettings
        from .convert_tuflow_model_gis_format.conv_tf_gis_format.helpers.file import TuflowPath
        from .compatibility_routines import GPKG

        try:

            control_file = TuflowPath(self.control_file)
            cf_lyrs = ControlFileLayers(control_file)
            self.model_file_layers.add(cf_lyrs)

            if self.settings is None:
                settings_ = ConvertSettings(*['-tcf', control_file, '-rf', control_file.parent, '-use_scenarios'])
                settings_.read_tcf(self.scenarios)
                self.settings = settings_
            else:
                settings_ = self.settings.copy_settings(control_file, self.settings.output_folder)

            for command in get_commands(control_file, settings_):
                if command.in_scenario_block() and not command.in_scenario_block(settings_.scenarios):
                    continue

                elif command.is_spatial_database_command():
                    settings_.process_spatial_database_command(command.value)

                elif command.is_control_file() or command.is_read_file():
                    if command.is_quadtree_single_level():
                        continue
                    i = -1
                    for i, file in enumerate(command.iter_files(settings_)):
                        cf = file.resolve()
                        load_gis = LoadGisFromControlFile(self.model_file_layers, cf, settings_)
                        load_gis.loadGisFromControlFile_v2()
                    if i == -1:
                        self.settings.no_files_copied.append((settings_.control_file.suffix[1:].upper(), command.original_text.strip()))

                elif command.is_read_gis():
                    if command.in_output_zone_block() and not command.in_output_zone_block(settings_.output_zones):
                        continue

                    i = -1
                    for type_ in command.iter_geom(settings_):
                        if type_ == 'VALUE':
                            continue
                        for i, file in enumerate(command.iter_files(settings_)):
                            if type_ == 'GRID':
                                cf_lyrs.add_grid(file)
                            else:
                                cf_lyrs.add_gis(file)
                            cf_lyrs.add_lyr(file)
                    if i == -1:
                        self.settings.no_files_copied.append((settings_.control_file.suffix[1:].upper(), command.original_text.strip()))

                elif command.is_read_grid():
                    if command.is_rainfall_grid_nc():
                        # TODO
                        continue

                    i = -1
                    for type_ in command.iter_grid(settings_):
                        for i, file in enumerate(command.iter_files(settings_)):
                            if type_ == 'GRID':
                                cf_lyrs.add_grid(file)
                            else:
                                cf_lyrs.add_gis(file)
                            cf_lyrs.add_lyr(file)
                    if i == -1:
                        self.settings.no_files_copied.append((settings_.control_file.suffix[1:].upper(), command.original_text.strip()))

                elif command.is_read_projection():
                    i = -1
                    for i, file in enumerate(command.iter_files(settings_)):
                        if command.command == 'TIF PROJECTION':
                            # cf_lyrs.add_grid(file)
                            cf_lyrs.layer_added.emit('')  # in case the progress bar requires the counts to be the same
                            pass
                        else:
                            cf_lyrs.add_gis(file)
                            cf_lyrs.add_lyr(file)
                    if i == -1:
                        self.settings.no_files_copied.append((settings_.control_file.suffix[1:].upper(), command.original_text.strip()))

                elif command.is_rainfall_grid_csv():
                    # TODO
                    continue

                elif command.is_read_swmm_inp():
                    if command.value.name in cf_lyrs.swmm_inp_name:
                        continue
                    cf_lyrs.swmm_inp_name.append(command.value.name)
                    if settings_.projection_wkt:
                        crs = QgsCoordinateReferenceSystem(settings_.projection_wkt)
                    else:
                        from qgis.utils import iface
                        crs = QgsProject.instance().crs()
                    output_path = str(command.value_.with_suffix('.gpkg'))
                    cont = False
                    if not os.path.exists(output_path):
                        try:
                            inputs = {
                                'INPUT': command.value_expanded_path,
                                'INPUT_CRS': crs,
                                'INPUT_tags_to_filter': '',
                                'INPUT_gpkg_output_filename': output_path,
                            }
                            output = processing.run("TUFLOW:TUFLOWConvertSWMMinpToGpkg", inputs)
                        except:
                            pass
                        finally:
                            if not os.path.exists(output_path):
                                cf_lyrs.swmm_inp_name.pop()
                                cont = True
                    if cont:
                        continue
                    lyr_name = None
                    swmm_inp_lyrs = []
                    for i, lyr in enumerate(GPKG(output_path).vector_layers()):
                        lyr_name = TuflowPath(f'{output_path} >> {lyr}')
                        swmm_inp_lyrs.append(lyr_name)
                        cf_lyrs.add_gis(lyr_name)
                        cf_lyrs.add_lyr(lyr_name)
                    for i, lyr in enumerate(GPKG(output_path).non_spatial_layers()):
                        lyr_name = TuflowPath(f'{output_path} >> {lyr}')
                        swmm_inp_lyrs.append(lyr_name)
                        cf_lyrs.add_table(lyr_name)
                        cf_lyrs.add_lyr(lyr_name)
                    cf_lyrs.swmm_inp_lyrs.append(swmm_inp_lyrs)

            self.finished.emit()

        except Exception as e:
            self.error.emit(str(e))


def loadGisFromControlFile(controlFile, iface, processed_paths, processed_layers, scenarios, variables, crs,
                           dbTCF, dbCCF, **kwargs):
    """
    Opens all vector layers from the specified tuflow control file

    :param controlFile: string - file location
    :param iface: QgisInterface
    :return: bool, string
    """

    error = False
    log = ''
    dir = os.path.dirname(controlFile)
    root = QgsProject.instance().layerTreeRoot()
    group = root.addGroup(os.path.basename(controlFile))
    read = True
    with open(controlFile, 'r') as fo:
        for f in fo:
            if 'if scenario' in f.lower():
                ind = f.lower().find('if scenario')
                if '!' not in f[:ind] and '#' not in f[:ind]:
                    command, scenario = f.split('==', 1)
                    command = command.strip()
                    scenario = scenario.split('!')[0].split('#')[0]
                    scenario = scenario.strip()
                    scenarios_ = scenario.split('|')
                    found = False
                    for scenario in scenarios_:
                        scenario = scenario.strip()
                        if scenario in scenarios:
                            found = True
                    if found:
                        read = True
                    else:
                        read = False
            if 'else' in f.lower():
                ind = f.lower().find('else')
                if '!' not in f[:ind] and '#' not in f[:ind]:
                    if '==' in f.lower():
                        command, scenario = f.split('==', 1)
                    else:
                        command = f.lower()
                    command = command.strip()
                    command = command.split('!')[0].split('#')[0]
                    if 'if scenario' not in command.lower():
                        read = True
            if 'end if' in f.lower():
                ind = f.lower().find('end if')
                if '!' not in f[:ind] and '#' not in f[:ind]:
                    read = True
            if not read:
                continue
            if 'read' in f.lower() or 'create tin zpts' in f.lower():
                if 'read' in f.lower():
                    ind = f.lower().find('read')
                else:
                    ind = f.lower().find('create')
                if '!' not in f[:ind] and '#' not in f[:ind]:
                    if not re.findall(r'read material(s)? file', f, flags=re.IGNORECASE) \
                            and not re.findall(r'read soil(s)? file', f, flags=re.IGNORECASE) \
                            and 'read file' not in f.lower() and 'read operating controls file' not in f.lower():
                        command, relPath = f.split('==', 1)
                        command = command.strip()
                        is_raster = 'read grid' in command.lower()
                        relPath = relPath.split('!')[0].split('#')[0]
                        relPath = relPath.strip()
                        relPaths = relPath.split("|")
                        for relPath in relPaths:
                            relPath = relPath.strip()
                            paths = getAllFolders(dir, relPath, variables, scenarios, [], db=dbCCF)
                            for path in paths:
                                if path not in processed_paths:
                                    if is_raster and 'load_rasters' in kwargs and kwargs['load_rasters'] == 'no':
                                        continue
                                    invisible = is_raster and 'load_rasters' in kwargs and kwargs[
                                        'load_rasters'] == 'invisible'
                                    visible = not invisible
                                    processed_paths, processed_layers, error, log, crs = \
                                        loadGisFile(iface, path, group, processed_paths, processed_layers, error, log,
                                                    crs, visible)
            elif 'spatial database' in f.lower() and 'output' not in f.lower():
                ind = f.lower().find('spatial database')
                if '!' not in f[:ind] and '#' not in f[:ind]:
                    command, relPath = f.split('==', 1)
                    command = command.strip()
                    relPath = relPath.split('!')[0].split('#')[0]
                    relPath = relPath.strip()

                    if relPath.lower() == 'off':
                        dbTCF = None
                        dbCCF = None
                    elif relPath.lower() == 'tcf':
                        if type(dbTCF) is list:
                            dbCCF = dbTCF[:]
                        else:
                            dbCCF = dbTCF
                    else:
                        paths = getAllFolders(dir, relPath, variables, scenarios, [])
                        dbCCF = [x for x in paths if os.path.exists(x)]
                        if 'is_tcf' in kwargs and kwargs['is_tcf']:
                            dbTCF = dbCCF[:]

    lyrs = [c.layer() for c in group.children()]
    lyrs_sorted = sorted(lyrs, key=lambda x: x.name().lower())
    for i, lyr in enumerate(lyrs_sorted):
        treeLyr = group.insertLayer(i, lyr)
        treeLyr.setItemVisibilityChecked(
            QgsProject.instance().layerTreeRoot().findLayer(lyr.id()).itemVisibilityChecked())
    group.removeChildren(len(lyrs), len(lyrs))

    return error, log, processed_paths, processed_layers, crs, dbTCF, dbCCF


def openGisFromTcf(tcf, iface, scenarios=(), load_rasters=True):
    """
    Opens all vector layers from the tuflow model from the TCF

    :param tcf: string - TCF location
    :param iface: QgisInterface
    :return: void - opens all files in qgis window
    """

    dir = os.path.dirname(tcf)
    crs = None

    # get variable names and corresponding values
    variables, error = getVariableNamesFromTCF(tcf, scenarios)
    if error:
        return

    processed_paths = []
    processed_layers = []
    couldNotReadFile = False
    message = 'Could not open file:\n'
    dbTCF = None
    dbCCF = None
    error, log, pPaths, pLayers, crs, dbTCF, dbCCF = loadGisFromControlFile(tcf, iface, processed_paths,
                                                                            processed_layers,
                                                                            scenarios, variables, crs, dbTCF, dbCCF,
                                                                            is_tcf=True, load_rasters=load_rasters)
    processed_paths += pPaths
    processed_layers += pLayers
    if error:
        couldNotReadFile = True
        message += log
    read = True
    with open(tcf, 'r') as fo:
        for f in fo:
            if 'if scenario' in f.lower():
                ind = f.lower().find('if scenario')
                if '!' not in f[:ind] and '#' not in f[:ind]:
                    command, scenario = f.split('==', 1)
                    command = command.strip()
                    scenario = scenario.split('!')[0].split('#')[0]
                    scenario = scenario.strip()
                    scenarios_ = scenario.split('|')
                    found = False
                    for scenario in scenarios_:
                        scenario = scenario.strip()
                        if scenario in scenarios:
                            found = True
                    if found:
                        read = True
                    else:
                        read = False
            if 'else' in f.lower():
                ind = f.lower().find('else')
                if '!' not in f[:ind] and '#' not in f[:ind]:
                    if '==' in f.lower():
                        command, scenario = f.split('==', 1)
                    else:
                        command = f.lower()
                    command = command.strip()
                    command = command.split('!')[0].split('#')[0]
                    if 'if scenario' not in command.lower():
                        read = True
            if 'end if' in f.lower():
                ind = f.lower().find('end if')
                if '!' not in f[:ind] and '#' not in f[:ind]:
                    read = True
            if not read:
                continue
            if 'estry control file' in f.lower():
                ind = f.lower().find('estry control file')
                if '!' not in f[:ind] and '#' not in f[:ind]:
                    if 'estry control file auto' in f.lower():
                        path = '{0}.ecf'.format(os.path.splitext(tcf)[0])
                        error, log, pPaths, pLayers, crs, dbTCF, dbCCF = loadGisFromControlFile(path, iface,
                                                                                                processed_paths,
                                                                                                processed_layers,
                                                                                                scenarios, variables,
                                                                                                crs,
                                                                                                dbTCF, dbCCF,
                                                                                                load_rasters=load_rasters)
                        processed_paths += pPaths
                        processed_layers += pLayers
                        if error:
                            couldNotReadFile = True
                            message += log
                    else:
                        command, relPath = f.split('==', 1)
                        command = command.strip()
                        relPath = relPath.split('!')[0].split('#')[0]
                        relPath = relPath.strip()
                        paths = getAllFolders(dir, relPath, variables, scenarios, [])
                        for path in paths:
                            error, log, pPaths, pLayers, crs, dbTCF, dbCCF = loadGisFromControlFile(path, iface,
                                                                                                    processed_paths,
                                                                                                    processed_layers,
                                                                                                    scenarios,
                                                                                                    variables, crs,
                                                                                                    dbTCF, dbCCF,
                                                                                                    load_rasters=load_rasters)
                            processed_paths += pPaths
                            processed_layers += pLayers
                            if error:
                                couldNotReadFile = True
                                message += log
            if 'geometry control file' in f.lower():
                ind = f.lower().find('geometry control file')
                if '!' not in f[:ind] and '#' not in f[:ind]:
                    command, relPath = f.split('==', 1)
                    command = command.strip()
                    relPath = relPath.split('!')[0].split('#')[0]
                    relPath = relPath.strip()
                    paths = getAllFolders(dir, relPath, variables, scenarios, [])
                    for path in paths:
                        error, log, pPaths, pLayers, crs, dbTCF, dbCCF = loadGisFromControlFile(path, iface,
                                                                                                processed_paths,
                                                                                                processed_layers,
                                                                                                scenarios, variables,
                                                                                                crs,
                                                                                                dbTCF, dbCCF,
                                                                                                load_rasters=load_rasters)
                        processed_paths += pPaths
                        processed_layers += pLayers
                        if error:
                            couldNotReadFile = True
                            message += log
            if 'bc control file' in f.lower():
                ind = f.lower().find('bc control file')
                if '!' not in f[:ind] and '#' not in f[:ind]:
                    command, relPath = f.split('==', 1)
                    command = command.strip()
                    relPath = relPath.split('!')[0].split('#')[0]
                    relPath = relPath.strip()
                    paths = getAllFolders(dir, relPath, variables, scenarios, [])
                    for path in paths:
                        error, log, pPaths, pLayers, crs, dbTCF, dbCCF = loadGisFromControlFile(path, iface,
                                                                                                processed_paths,
                                                                                                processed_layers,
                                                                                                scenarios, variables,
                                                                                                crs,
                                                                                                dbTCF, dbCCF,
                                                                                                load_rasters=load_rasters)
                        processed_paths += pPaths
                        processed_layers += pLayers
                        if error:
                            couldNotReadFile = True
                            message += log
            if 'event control file' in f.lower():
                ind = f.lower().find('event control file')
                if '!' not in f[:ind] and '#' not in f[:ind]:
                    command, relPath = f.split('==', 1)
                    command = command.strip()
                    relPath = relPath.split('!')[0].split('#')[0]
                    relPath = relPath.strip()
                    paths = getAllFolders(dir, relPath, variables, scenarios, [])
                    for path in paths:
                        error, log, pPaths, pLayers, crs, dbTCF, dbCCF = loadGisFromControlFile(path, iface,
                                                                                                processed_paths,
                                                                                                processed_layers,
                                                                                                scenarios, variables,
                                                                                                crs,
                                                                                                dbTCF, dbCCF,
                                                                                                load_rasters=load_rasters)
                        processed_paths += pPaths
                        processed_layers += pLayers
                        if error:
                            couldNotReadFile = True
                            message += log
            if 'read file' in f.lower():
                ind = f.lower().find('read file')
                if '!' not in f[:ind] and '#' not in f[:ind]:
                    command, relPath = f.split('==', 1)
                    command = command.strip()
                    if 'material' in command.lower() or 'soil' in command.lower():
                        continue
                    relPath = relPath.split('!')[0].split('#')[0]
                    relPath = relPath.strip()
                    paths = getAllFolders(dir, relPath, variables, scenarios, [])
                    for path in paths:
                        error, log, pPaths, pLayers, crs, dbTCF, dbCCF = loadGisFromControlFile(path, iface,
                                                                                                processed_paths,
                                                                                                processed_layers,
                                                                                                scenarios, variables,
                                                                                                crs,
                                                                                                dbTCF, dbCCF,
                                                                                                load_rasters=load_rasters)
                        processed_paths += pPaths
                        processed_layers += pLayers
                        if error:
                            couldNotReadFile = True
                            message += log
            if 'read operating controls file' in f.lower():
                ind = f.lower().find('read operating controls file')
                if '!' not in f[:ind] and '#' not in f[:ind]:
                    command, relPath = f.split('==', 1)
                    command = command.strip()
                    relPath = relPath.split('!')[0].split('#')[0]
                    relPath = relPath.strip()
                    paths = getAllFolders(dir, relPath, variables, scenarios, [])
                    for path in paths:
                        error, log, pPaths, pLayers, crs, dbTCF, dbCCF = loadGisFromControlFile(path, iface,
                                                                                                processed_paths,
                                                                                                processed_layers,
                                                                                                scenarios, variables,
                                                                                                crs,
                                                                                                dbTCF, dbCCF,
                                                                                                load_rasters=load_rasters)
                        processed_paths += pPaths
                        processed_layers += pLayers
                        if error:
                            couldNotReadFile = True
                            message += log
            if 'rainfall control file' in f.lower():
                ind = f.lower().find('rainfall control file')
                if '!' not in f[:ind] and '#' not in f[:ind]:
                    command, relPath = f.split('==', 1)
                    command = command.strip()
                    relPath = relPath.split('!')[0].split('#')[0]
                    relPath = relPath.strip()
                    paths = getAllFolders(dir, relPath, variables, scenarios, [])
                    for path in paths:
                        error, log, pPaths, pLayers, crs, dbTCF, dbCCF = loadGisFromControlFile(path, iface,
                                                                                                processed_paths,
                                                                                                processed_layers,
                                                                                                scenarios, variables,
                                                                                                crs,
                                                                                                dbTCF, dbCCF,
                                                                                                load_rasters=load_rasters)
                        processed_paths += pPaths
                        processed_layers += pLayers
                        if error:
                            couldNotReadFile = True
                            message += log
            if 'quadtree control file' in f.lower():
                ind = f.lower().find('rainfall control file')
                if '!' not in f[:ind] and '#' not in f[:ind]:
                    command, relPath = f.split('==', 1)
                    command = command.strip()
                    relPath = relPath.split('!')[0].split('#')[0]
                    relPath = relPath.strip()
                    if relPath.lower() == 'single level':
                        continue
                    paths = getAllFolders(dir, relPath, variables, scenarios, [])
                    for path in paths:
                        error, log, pPaths, pLayers, crs, dbTCF, dbCCF = loadGisFromControlFile(path, iface,
                                                                                                processed_paths,
                                                                                                processed_layers,
                                                                                                scenarios, variables,
                                                                                                crs,
                                                                                                dbTCF, dbCCF,
                                                                                                load_rasters=load_rasters)
                        processed_paths += pPaths
                        processed_layers += pLayers
                        if error:
                            couldNotReadFile = True
                            message += log
    for layer in processed_layers:
        removeLayer(layer)
    if couldNotReadFile:
        QMessageBox.information(iface.mainWindow(), "Message", message)
    else:
        QMessageBox.information(iface.mainWindow(), "Message", "Successfully Loaded All TUFLOW Layers")


def applyMatplotLibArtist(line, artist):
    if artist:
        if type(line) is PolyCollection:
            if type(artist) is PolyCollection:
                line.setcmap(artist.cmap)
                line.set_clim(artist.norm.vmin, artist.norm.vmax)
            elif type(artist) is dict:
                line.set_cmap(artist['cmap'])
                line.set_clim(artist['vmin'], artist['vmax'])
        elif type(artist) is dict:
            line.set_color(artist['color'])
            line.set_linewidth(artist['linewidth'])
            line.set_linestyle(artist['linestyle'])
            line.set_drawstyle(artist['drawstyle'])
            line.set_marker(artist['marker'])
            line.set_markersize(artist['markersize'])
            line.set_markeredgecolor(artist['markeredgecolor'])
            line.set_markerfacecolor(artist['markerfacecolor'])
        else:
            line.set_color(artist.get_color())
            line.set_linewidth(artist.get_linewidth())
            line.set_linestyle(artist.get_linestyle())
            line.set_drawstyle(artist.get_drawstyle())
            line.set_marker(artist.get_marker())
            line.set_markersize(artist.get_markersize())
            line.set_markeredgecolor(artist.get_markeredgecolor())
            line.set_markerfacecolor(artist.get_markerfacecolor())


def saveMatplotLibArtist(artist):
    a = {}
    if type(artist) is PolyCollection:
        a['vmin'] = artist.norm.vmin
        a['vmax'] = artist.norm.vmax
        a['cmap'] = artist.cmap
    else:
        a['color'] = artist.get_color()
        a['linewidth'] = artist.get_linewidth()
        a['linestyle'] = artist.get_linestyle()
        a['drawstyle'] = artist.get_drawstyle()
        a['marker'] = artist.get_marker()
        a['markersize'] = artist.get_markersize()
        a['markeredgecolor'] = artist.get_markeredgecolor()
        a['markerfacecolor'] = artist.get_markerfacecolor()

    return a


def getMean(values, **kwargs):
    """
    Returns the mean value and the position to the closest or next higher.

    :param values: list -> float
    :param kwargs: dict
    :return: float mean value, int index
    """

    import statistics

    method = kwargs['event_selection'] if 'event_selection' in kwargs.keys() else None

    if not values:
        return None, None

    mean = statistics.mean(values)
    valuesOrdered = sorted(values)

    index = None
    if method.lower() == 'next higher':
        for i, v in enumerate(valuesOrdered):
            if i == 0:
                vPrev = v
            if v == mean:
                index = values.index(v)
                break
            elif vPrev < mean and v > mean:
                index = values.index(v)
                break
            else:
                vPrev = v
    elif method.lower() == 'closest':
        difference = 99999
        for i, v in enumerate(values):
            diff = abs(v - mean)
            difference = min(difference, diff)
            if diff == difference:
                index = i
    else:
        index = None

    return mean, int(index)


def getUnit(resultType, canvas, **kwargs):
    """
    Returns units based on result type name and the map canvas units. If unrecognised returns blank.

    :param resultType: str
    :param canvas: QgsMapCanvas
    :return: str unit
    """

    units = {
        'level': ('m RL', 'ft RL', ''),
        'bed level': ('m RL', 'ft RL', ''),
        'left bank obvert': ('m RL', 'ft RL', ''),
        'right bank obvert': ('m RL', 'ft RL', ''),
        'us levels': ('m RL', 'ft RL', ''),
        'ds levels': ('m RL', 'ft RL', ''),
        'bed elevation': ('m RL', 'ft RL', ''),
        'flow': ('m3/s', 'ft3/s', ''),
        'atmospheric pressure': ('hPA', 'hPa', ''),
        'bed shear stress': ('N/m2', 'lbf/ft2', 'pdl/ft2', ''),
        'depth': ('m', 'ft', ''),
        'velocity': ('m/s', 'ft/s', ''),
        'cumulative infiltration': ('mm', 'inches', ''),
        'depth to groundwater': ('m', 'ft', ''),
        'water level': ('m RL', 'ft RL', ''),
        'infiltration rate': ('mm/hr', 'in/hr', ''),
        'mb1': ('%', '%', ''),
        'mb2': ('%', '%', ''),
        'unit flow': ('m2/s', 'ft2/s', ''),
        'cumulative rainfall': ('mm', 'inches', ''),
        'rfml': ('mm', 'inches', ''),
        'rainfall rate': ('mm/hr', 'in/hr', ''),
        'stream power': ('W/m2', 'lbf/ft2', 'pdl/ft2', ''),
        'sink': ('m3/s', 'ft3/s', ''),
        'source': ('m3/s', 'ft3/s', '')
    }

    # determine units i.e. metric, imperial, or unknown / blank
    if canvas is not None:
        if canvas.mapUnits() == QgsUnitTypes.DistanceMeters or canvas.mapUnits() == QgsUnitTypes.DistanceKilometers or \
                canvas.mapUnits() == QgsUnitTypes.DistanceCentimeters or canvas.mapUnits() == QgsUnitTypes.DistanceMillimeters:  # metric
            u, m = 0, 'm'
        elif canvas.mapUnits() == QgsUnitTypes.DistanceFeet or canvas.mapUnits() == QgsUnitTypes.DistanceNauticalMiles or \
                canvas.mapUnits() == QgsUnitTypes.DistanceYards or canvas.mapUnits() == QgsUnitTypes.DistanceMiles:  # imperial
            u, m = 1, 'ft'
        else:  # use blank
            u, m = -1, ''
    else:
        u, m = -1, ''

    unit = ''
    if resultType is not None:
        for key, item in units.items():
            if key in resultType.lower():
                unit = item[u]
                break
            elif resultType.lower() in key:
                unit = item[u]
                break

    if 'return_map_units' in kwargs.keys():
        if kwargs['return_map_units']:
            return m

    return unit


def interpolate(a, b, c, d, e):
    """
    Linear interpolation

    :param a: known mid point
    :param b: known lower value
    :param c: known upper value
    :param d: unknown lower value
    :param e: unknown upper value
    :return: float
    """

    a = float(a) if type(a) is not datetime else a
    b = float(b) if type(b) is not datetime else b
    c = float(c) if type(c) is not datetime else c
    d = float(d) if type(d) is not datetime else d
    e = float(e) if type(e) is not datetime else e

    return (e - d) / (c - b) * (a - b) + d


def roundSeconds(dateTimeObject, prec):
    """rounds datetime object to nearest second"""

    newDateTime = dateTimeObject

    a = 500000  # 0.5s
    b = 1000000  # 1.0s
    if prec > 0:
        a = a / (10 ** prec)
        b = b / (10 ** prec)
    ms = newDateTime.microsecond - floor(newDateTime.microsecond / b) * b
    if ms >= a:
        newDateTime = newDateTime + timedelta(microseconds=b)

    return newDateTime - timedelta(microseconds=ms)


def roundSeconds2(t, prec):
    """Takes float input in hours and rounds to prec (no. of decimal places of seconds component)"""
    dt = timedelta(hours=t)
    a = 500000  # 0.5s
    b = 1000000  # 1.0s
    if prec > 0:
        a = a / (10 ** prec)
        b = b / (10 ** prec)
    ms = dt.microseconds - floor(dt.microseconds / b) * b
    # if dt.microseconds - ms >= a:
    if ms >= a:
        dt = dt + timedelta(microseconds=b)
    # ms = dt.microseconds - floor(dt.microseconds / b) * b
    return (dt - timedelta(microseconds=ms)).total_seconds()


def convertStrftimToTuviewftim(strftim):
    """

    :param strftim: str standard datetime string format e.g. %d/%m/%Y %H:%M:%S
    :return: str user friendly style time string format used in tuview (similar to excel) e.g. DD/MM/YYYY hh:mm:ss
    """

    tvftim = strftim
    tvftim = tvftim.replace('%a', 'DDD')
    tvftim = tvftim.replace('%A', 'DDDD')
    tvftim = tvftim.replace('%b', 'MMM')
    tvftim = tvftim.replace('%B', 'MMMM')
    tvftim = tvftim.replace('%d', 'DD')
    tvftim = tvftim.replace('%#d', 'D')
    tvftim = tvftim.replace('%H', 'hh')
    tvftim = tvftim.replace('%#H', 'h')
    tvftim = tvftim.replace('%I', 'hh')
    tvftim = tvftim.replace('%#I', 'h')
    tvftim = tvftim.replace('%m', 'MM')
    tvftim = tvftim.replace('%#m', 'M')
    tvftim = tvftim.replace('%M', 'mm')
    tvftim = tvftim.replace('%#M', 'm')
    tvftim = tvftim.replace('%p', 'AM/PM')
    tvftim = tvftim.replace('%S', 'ss')
    tvftim = tvftim.replace('%#S', 's')
    tvftim = tvftim.replace('%y', 'YY')
    tvftim = tvftim.replace('%Y', 'YYYY')

    return tvftim


def checkConsecutive(letter, string):
    """
    check if a particular letter only appears consecutively - used for date formatting i.e. DD/MM/YYYY not D/M/DD
    or something silly like that. will ignore AM/PM

    :param letter:
    :param string:
    :return:
    """

    f = string.replace('am', '')
    f = f.replace('AM', '')
    f = f.replace('pm', '')
    f = f.replace('PM', '')
    for i in range(f.count(letter)):
        if i == 0:
            indPrev = f.find(letter)
        else:
            ind = f[indPrev + 1:].find(letter)
            if ind != 0:
                return False
            indPrev += 1

    return True


def replaceString(string, letter, replacement):
    """
    substitute to the replace function for the specific purpose of ignoring AM/PM when replacing 'M' or 'm' in strings.

    :param string: str string to search through
    :param letter: str string to search for
    :param replacement: str string to use as replacement
    :return: str after search and replace
    """

    newstring = []
    for i, c in enumerate(string):
        if i == 0:
            if c == letter:
                newstring.append(replacement)
            else:
                newstring.append(c)
        else:
            if c == letter:
                if string[i - 1].lower() == 'a' or string[i - 1].lower() == 'p' or string[i - 1] == '#' or string[
                    i - 1] == '%':
                    newstring.append(c)
                else:
                    newstring.append(replacement)
            else:
                newstring.append(c)
    return ''.join(newstring)


def convertStrftimToStrformat(strftim):
    """

    :param strftim: str standard datetime string format e.g. %d/%m/%Y %H:%M:%S
    :return: str standard formatting e.g. {0:%d}/{0:%m}/{0:%Y} {0:%H}:{0:%M}:{0:%S}
    """

    strformat = strftim
    strformat = strformat.replace('%a', '{0:%a}')
    strformat = strformat.replace('%A', '{0:%A}')
    strformat = strformat.replace('%b', '{0:%b}')
    strformat = strformat.replace('%B', '{0:%B}')
    strformat = strformat.replace('%d', '{0:%d}')
    strformat = strformat.replace('%#d', '{0:%#d}')
    strformat = strformat.replace('%H', '{0:%H}')
    strformat = strformat.replace('%#H', '{0:%#H}')
    strformat = strformat.replace('%I', '{0:%I}')
    strformat = strformat.replace('%#I', '{0:%#I}')
    strformat = strformat.replace('%m', '{0:%m}')
    strformat = strformat.replace('%#m', '{0:%#m}')
    strformat = strformat.replace('%M', '{0:%M}')
    strformat = strformat.replace('%#M', '{0:%#M}')
    strformat = strformat.replace('%p', '{0:%p}')
    strformat = strformat.replace('%S', '{0:%S}')
    strformat = strformat.replace('%#S', '{0:%#S}')
    strformat = strformat.replace('%y', '{0:%y}')
    strformat = strformat.replace('%Y', '{0:%Y}')

    return strformat


def convertTuviewftimToStrftim(tvftim):
    """


    :param tvftim: str user friendly style time string format used in tuview (similar to excel) e.g. DD/MM/YYYY hh:mm:ss
    :return: str strftim standard datetime string format e.g. %d/%m/%Y %H:%M:%S
    """

    strftim = tvftim
    for c in tvftim:
        if c != 'D' and c.upper() != 'M' and c != 'Y' and c != 'h' and c != 's' and c != ' ' and c != '/' and c != ':' \
                and c != '\\' and c != '-' and c != '|' and c != ';' and c != ',' and c != '.' and c != '&' and c != '*' \
                and c != '_' and c != '=' and c != '+' and c != '[' and c != ']' and c != '{' and c != '}' and c != "'" \
                and c != '"' and c != '<' and c != '>' and c != '(' and c != ')':
            if c.lower() == 'a' or c.lower() == 'p':
                ind = strftim.find('a')
                if ind != -1:
                    if strftim[ind + 1].lower() != 'm':
                        return '', ''
                ind = strftim.find('p')
                if ind != -1:
                    if strftim[ind + 1].lower() != 'm':
                        return '', ''
            else:
                return '', ''

    f = strftim.find('Y')
    if f != -1:
        if checkConsecutive('Y', tvftim):
            count = tvftim.count('Y')
            replace = 'Y' * count
            if count == 1:
                strftim = strftim.replace(replace, '%y')
            elif count == 2:
                strftim = strftim.replace(replace, '%y')
            elif count == 3:
                strftim = strftim.replace(replace, '%Y')
            elif count >= 4:
                strftim = strftim.replace(replace, '%Y')
    f = strftim.find('M')
    if f != -1:
        if checkConsecutive('M', tvftim):
            temp = tvftim.replace('AM', '')
            temp = temp.replace('PM', '')
            count = temp.count('M')
            replace = 'M' * count
            if count == 1:
                strftim = replaceString(strftim, replace, '%#m')
            elif count == 2:
                strftim = strftim.replace(replace, '%m')
            elif count == 3:
                strftim = strftim.replace(replace, '%b')
            elif count >= 4:
                strftim = strftim.replace(replace, '%B')
    f = strftim.find('D')
    if f != -1:
        if checkConsecutive('D', tvftim):
            count = tvftim.count('D')
            replace = 'D' * count
            if count == 1:
                strftim = strftim.replace(replace, '%#d')
            elif count == 2:
                strftim = strftim.replace(replace, '%d')
            elif count == 3:
                strftim = strftim.replace(replace, '%a')
            elif count >= 4:
                strftim = strftim.replace(replace, '%A')
    f = strftim.find('h')
    if f != -1:
        if checkConsecutive('h', tvftim):
            replacement = 'H'
            if 'am' in tvftim.lower() or 'pm' in tvftim.lower():
                replacement = 'I'
            count = tvftim.count('h')
            replace = 'h' * count
            if count == 1:
                strftim = strftim.replace(replace, '%#{0}'.format(replacement))
            elif count >= 2:
                strftim = strftim.replace(replace, '%{0}'.format(replacement))
    f = strftim.find('m')
    if f != -1:
        if checkConsecutive('m', tvftim):
            temp = tvftim.replace('am', '')
            temp = temp.replace('pm', '')
            count = temp.count('m')
            replace = 'm' * count
            if count == 1:
                strftim = replaceString(strftim, replace, '%#M')
            elif count >= 2:
                strftim = strftim.replace(replace, '%M')
    f = strftim.find('s')
    if f != -1:
        if checkConsecutive('s', tvftim):
            count = tvftim.count('s')
            replace = 's' * count
            if count == 1:
                strftim = strftim.replace(replace, '%#S')
            elif count >= 2:
                strftim = strftim.replace(replace, '%S')
    f = strftim.lower().find('am/pm')
    if f != -1:
        strftim = strftim.replace('AM/PM', '%p')
        strftim = strftim.replace('am/pm', '%p')
    f = strftim.lower().find('am')
    if f != -1:
        strftim = strftim.replace('AM', '%p')
        strftim = strftim.replace('am', '%p')
    f = strftim.lower().find('pm')
    if f != -1:
        strftim = strftim.replace('PM', '%p')
        strftim = strftim.replace('pm', '%p')

    strformat = convertStrftimToStrformat(strftim)

    return strftim, strformat


def getPropertiesFrom2dm(file):
    """Get some basic properties from TUFLOW classic 2dm file"""

    cellSize = 1
    wllVerticalOffset = 0
    origin = ()
    orientation = 0
    gridSize = ()

    count = 0
    with open(file, 'r') as fo:
        for line in fo:
            if 'MESH2D' in line.upper():
                components = line.split(' ')
                properties = []
                for c in components:
                    if c != '':
                        properties.append(c)
                if len(components) >= 3:
                    origin = (float(properties[1]), float(properties[2]))
                if len(properties) >= 4:
                    orientation = float(properties[3])
                if len(properties) >= 6:
                    gridSize = (int(properties[4]), int(properties[5]))
                if len(properties) >= 8:
                    cellSize = min(float(properties[6]), float(properties[7]))
                if len(properties) >= 9:
                    wllVerticalOffset = float(properties[8])
                return cellSize, wllVerticalOffset, origin, orientation, gridSize
            if count > 10:  # should be at the start and don't want to waste time if there is an error
                return cellSize, wllVerticalOffset, origin, orientation, gridSize
            count += 1

    return cellSize, wllVerticalOffset, origin, orientation, gridSize


def bndryBinProperties(file):
    """
    Get xf file precision 4 or 8

    :param file: str full path to file
    return: int xf version, int precision, int number of rows, int number of columns, int boundary file type
    """

    xf_iparam = -1
    xf_fparam = -1
    xf_iparam_1 = -1  # xf file version
    xf_iparam_2 = -1  # precision (4 or 8)
    xf_iparam_3 = -1  # number of rows
    xf_iparam_4 = -1  # number of columns
    xf_iparam_5 = -1  # 1 = csv, 2 = ts1

    with open(file, 'rb') as fo:
        for line in fo:
            for i in range(0, len(line), 4):  # data located at either a multiple of 4 or 8
                a = line[i]
                if i == 0:
                    xf_iparam_1 = a
                elif i == 4 and a == 4:
                    xf_iparam_2 = a
                elif i == 4 and a == 8 and xf_iparam_2 == -1:
                    xf_iparam_2 = a

                if xf_iparam_2 > -1:
                    if i == 4 * 2:
                        xf_iparam_3 = a  # number of rows

                    if i == 4 * 3:
                        xf_iparam_4 = a  # number of columns

                    if i == 4 * 4:
                        xf_iparam_5 = a  # 1 = csv, 2 = ts1
                        break
            break

    return xf_iparam_1, xf_iparam_2, xf_iparam_3, xf_iparam_4, xf_iparam_5


def bndryBinHeaders(file, ncol, precision):
    """
    Get header names from boundary xf file

    :param file: str full path to file
    :param ncol: int number of columns
    :param precision: int 4 or 8
    :return: list -> str column header name
    """

    headers = []
    array_size = 20
    char_size = 1000

    with open(file, 'rb') as fo:
        for line in fo:
            start = (array_size * 4) + (array_size * precision) + (ncol * 4)
            for j in range(ncol):
                bname = line[start:start + char_size]
                name = bname.decode('ascii')
                name = name.strip()
                if name:
                    headers.append(name)
                start += char_size

    return headers


def bndryBinData(file, ncol, nrow, precision):
    """
    Get data from boundary xf file

    :param file: str full path to file
    :param ncol: int number of columns
    :param nrow: int number of rows
    :param precision: int 4 or 8
    :return: ndarray
    """

    array_size = 20
    header_size = 1000
    # start = int(40 + ncol + (ncol * header_size) / precision)
    start = int(((array_size * 4) + (array_size * precision) + (ncol * 4) + (ncol * header_size)) / precision)
    end = int(start + (ncol * nrow))
    data_type = numpy.float32 if precision == 4 else numpy.float64
    shape = (nrow, ncol)
    data = numpy.zeros(shape)  # dummy data

    with open(file, 'rb') as fo:
        extract = numpy.fromfile(fo, dtype=data_type, count=end)

    for i in range(ncol):
        d = extract[start:start + nrow]
        d = numpy.reshape(d, (nrow, 1))
        if i == 0:
            data = d
        else:
            data = numpy.append(data, d, 1)
        start += nrow

    return data


def readBndryBin(file):
    """
    Reads TUFLOW bounadry csv .xf file

    :param file: str full path to file
    :return list -> str column header, ndarray
    """

    # get xf file properties
    xf_iparam_1, xf_iparam_2, xf_iparam_3, xf_iparam_4, xf_iparam_5 = bndryBinProperties(file)

    # get headers
    headers = bndryBinHeaders(file, xf_iparam_4, xf_iparam_2)

    # get data values
    data = bndryBinData(file, xf_iparam_4, xf_iparam_3, xf_iparam_2)

    return headers, data


def changeDataSource(iface, layer, newDataSource, isgpkg):
    """
    Changes map layer datasource - like arcmap

    :param iface: QgsInterface
    :param layer: QgsMapLayer
    :param newSource: str full file path
    :return: void
    """

    name = layer.name()
    if isgpkg:
        newName = re.split(re.escape(r'.gpkg|layername='), newDataSource, flags=re.IGNORECASE)[1]
    else:
        newName = os.path.basename(os.path.splitext(newDataSource)[0])

    if Qgis.QGIS_VERSION_INT >= 32000:
        layer.setDataSource(newDataSource, newName, 'ogr')
    else:
        # create dom document to store layer properties
        doc = QDomDocument("styles")
        element = doc.createElement("maplayer")
        layer.writeLayerXml(element, doc, QgsReadWriteContext())

        # change datasource
        element.elementsByTagName("datasource").item(0).firstChild().setNodeValue(newDataSource)
        layer.readLayerXml(element, QgsReadWriteContext())

    # reload layer
    layer.reload()
    reload_data(layer)  # force reload

    # rename layer in layers panel
    legint = QgsProject.instance().layerTreeRoot()
    legint.findLayer(layer.id()).setName(newName)

    # refresh map and legend
    layer.triggerRepaint()
    iface.layerTreeView().refreshLayerSymbology(layer.id())


def copyLayerStyle(iface, layerCopyFrom, layerCopyTo):
    """
    Copies styling from one layer to another.

    :param layerCopyFrom: QgsMapLayer
    :param layerCopyTo: QgsMapLayer
    :return: void
    """

    # create dom document to store layer style
    doc = QDomDocument("styles")
    element = doc.createElement("maplayer")
    errorCopy = ''
    errorRead = ''
    layerCopyFrom.writeStyle(element, doc, errorCopy, QgsReadWriteContext())

    # set style to new layer
    layerCopyTo.readStyle(element, errorRead, QgsReadWriteContext())

    # refresh map and legend
    layerCopyTo.triggerRepaint()
    iface.layerTreeView().refreshLayerSymbology(layerCopyTo.id())


def getAllFilePaths(dir):
    """
    Get all file paths in directory including any subdirectories in parent directory.

    :param dir: str full path to directory
    :return: dict -> { lower case file path: actual case sensitive file path }
    """

    files = {}
    for r in os.walk(dir):
        for f in r[2]:
            file = os.path.join(r[0], f)
            files[file.lower()] = file

    return files


def getOSIndependentFilePath(dir, folders):
    """
    Returns a case sensitive file path from a case insenstive file path. Assumes dir is already correct.

    :param dir: str full path to working directory
    :param folders: str or list -> subfolders and file
    :return: str full case sensitive file path
    """

    if type(folders) is list:
        folders = os.sep.join(folders)

    return getPathFromRel(dir, folders)


def getOpenTUFLOWLayers(layer_type='input_types'):
    """
    Returns a list of open tuflow layer types, tuflow layers, or tuflow check layers

    :param layer_type: str layer type - options: 'input_all', 'input_types' or 'check_all'
    :return: list -> str layer name
    """

    tuflowLayers = []
    for name, layer in QgsProject.instance().mapLayers().items():
        if layer.type() == 0:  # vector layer
            pattern = r'_check(_[PLR])?$'  # will match '_check' or '_check_P' (P or L or R) only if it is at the end of the string
            name = os.path.splitext(layer.name())[0]  # make sure there is no file path extension
            search = re.search(pattern, name, flags=re.IGNORECASE)
            if search is not None:
                if layer_type == 'check_all':
                    tuflowLayers.append(layer.name())
            else:  # not a check file
                # find 0d_ or 1d_ or 2d_ part of layer name
                pattern = r'^[0-2]d_'
                search = re.search(pattern, name, flags=re.IGNORECASE)
                if search is not None:
                    if layer_type == 'input_all':
                        tuflowLayers.append(layer.name())
                    elif layer_type == 'input_types':
                        components = layer.name().split('_')
                        tuflow_type = '_'.join(components[:2]).lower()

                        # special case for 2d_sa as this could be 2d_sa_tr or 2d_sa_rf
                        specialCases = ['2d_sa_rf', '2d_sa_tr']
                        if len(components) >= 3:
                            for sc in specialCases:
                                tempName = tuflow_type + '_' + components[2]
                                if sc.lower() == tempName.lower():
                                    tuflow_type = tempName

                        if tuflow_type not in tuflowLayers:
                            tuflowLayers.append(tuflow_type)

    return sorted(tuflowLayers)


def getMapLayersFromRoot(root):
    # grab all nodes that are QgsMapLayers - get to node bed rock i.e. not a group
    nodes = []
    for child in root.children():
        children = [child]
        while children:
            nd = children[0]
            if nd.children():
                children += nd.children()
            else:
                nodes.append(nd)
            children = children[1:]

    return nodes


def turnLayersOnOff(settings):
    """
    Turn layers in the workspace on/off based on settings. If layer is not specified in settings, left as 'current'.

    :param settings: dict -> { 'layer': 'on' or 'current' or 'off' }
    :return: void
    """

    legint = QgsProject.instance().layerTreeRoot()

    # grab all nodes that are QgsMapLayers - get to node bed rock i.e. not a group
    nodes = legint.findLayers()

    # now loop through nodes and turn on/off visibility based on settings
    for nd in nodes:
        if nd.name() in settings:
            if settings[nd.name()] == 'on':
                if not nd.itemVisibilityChecked():
                    nd.setItemVisibilityChecked(True)
                parent = nd.parent()
                while parent:
                    if not parent.itemVisibilityChecked():

                        children = getMapLayersFromRoot(parent)
                        for child in children:
                            if child.name() in settings:
                                if settings[child.name()] == 'on':
                                    child.setItemVisibilityChecked(True)
                                else:
                                    child.setItemVisibilityChecked(False)
                            else:
                                child.setItemVisibilityChecked(False)

                        parent.setItemVisibilityChecked(True)
                    parent = parent.parent()
            elif settings[nd.name()] == 'off':
                if nd.itemVisibilityChecked():
                    nd.setItemVisibilityChecked(False)


def sorting_key(layer):
    name = layer.name().lower()
    name = re.sub(r'_[plr]^', '', name)


class Layer:

    def __init__(self, layer):
        if isinstance(layer, QgsMapLayer):
            self.name = layer.name()
            if isinstance(layer, QgsVectorLayer):
                self.geom_type = layer.geometryType()
            else:
                self.geom_type = QgsWkbTypes.PointGeometry
        else:
            self.name = layer.split(',')[1].strip(" \t\n'")
            uri = layer.split(',')[0].split('(')[1].strip(" \t\n'")
            if re.findall(r'_p$', uri, flags=re.IGNORECASE):
                self.geom_type = QgsWkbTypes.PointGeometry
            elif re.findall(r'_l$', uri, flags=re.IGNORECASE):
                self.geom_type = QgsWkbTypes.LineGeometry
            elif re.findall(r'_r$', uri, flags=re.IGNORECASE):
                self.geom_type = QgsWkbTypes.PolygonGeometry
            else:
                self.geom_type = QgsWkbTypes.PointGeometry


def sorting_alg(layers):
    lyr_wo_geom = [re.sub(r'_[plr]$', '', Layer(x).name, flags=re.IGNORECASE) for x in layers]
    key = {QgsWkbTypes.PointGeometry: 0, QgsWkbTypes.LineGeometry: 1, QgsWkbTypes.PolygonGeometry: 2}
    lyr_w_geom = [f'{lyrname}_{key[Layer(lyr).geom_type]}' for lyr, lyrname in zip(layers, lyr_wo_geom) if
                  'QgsVectorLayer' in str(lyr)]
    lyr_w_geom.extend([f'{Layer(x).name}_3' for x in layers if 'QgsVectorLayer' not in str(x)])
    key = {lyr: name.lower() for lyr, name in zip(layers, lyr_w_geom)}
    return sorted(layers, key=lambda x: key[x])


def sortLayers(layers, options=None, sort_key=None):
    vlayers = [x for x in layers if 'QgsVectorLayer' in str(x)]
    rlayers = [x for x in layers if 'QgsRasterLayer' in str(x)]
    mlayers = [x for x in layers if 'QgsMeshLayer' in str(x)]
    zlayers = [x for x in layers if x not in vlayers and x not in rlayers and x not in mlayers]  # any leftovers

    if options is not None and options.order_method == 'control_file' and sort_key is not None:
        layers_sorted = sorted(layers, key=lambda x: sort_key[x])
        return list(reversed(layers_sorted))
    elif options is not None and options.order_method == 'control_file_group_rasters' and sort_key is not None:
        vlayers = list(reversed(sorted(vlayers, key=lambda x: sort_key[x])))
        rlayers = list(reversed(sorted(rlayers, key=lambda x: sort_key[x])))
        mlayers = list(reversed(sorted(mlayers, key=lambda x: sort_key[x])))
        zlayers = list(reversed(sorted(zlayers, key=lambda x: sort_key[x])))
        return vlayers + rlayers + mlayers + zlayers
    else:
        vlayers = sorting_alg(vlayers)
        rlayers = sorting_alg(rlayers)
        mlayers = sorting_alg(mlayers)
        zlayers = sorting_alg(zlayers)
        return vlayers + rlayers + mlayers + zlayers


def sortNodesInGroup(group, nodes=None):
    """
    Sorts layers in a qgstree group alphabetically. DEMs will be put at bottom and Meshes will be just above DEMs.

    :param nodes: list -> QgsLayerTreeNode
    :param parent: QgsLayerTreeNode
    :return: void
    """

    if nodes is None:
        tree_layers = group.findLayers()
    else:
        tree_layers = nodes[:]
    lyr2node = {x.layer(): x for x in tree_layers}
    lyrs_sorted = sortLayers(list(lyr2node.keys()))
    nodes_sorted = [lyr2node[x] for x in lyrs_sorted]

    for node in reversed(nodes_sorted):
        clone = node.clone()
        group.insertChildNode(0, clone)
        parent = node.parent()
        parent.removeChildNode(node)


# # first sort nodes alphabetically by name
# nodes_sorted = sorted(nodes, key=lambda x: x.name().lower())
#
# # then move rasters and mesh layers to end
# rasters = []
# meshes = []
# empty = []  # layer that have failed to load or are not there i.e. (?)
# for node in nodes_sorted:
# 	layer = tuflowqgis_find_layer(node.name())
# 	if layer is not None:
# 		if isinstance(layer, QgsRasterLayer):  # raster
# 			rasters.append(node)
# 		elif isinstance(layer, QgsMeshLayer):  # mesh
# 			meshes.append(node)
# 	else:
# 		empty.append(node)
# for mesh in meshes:
# 	nodes_sorted.remove(mesh)
# 	nodes_sorted.append(mesh)
# for raster in rasters:
# 	nodes_sorted.remove(raster)
# 	nodes_sorted.append(raster)
#
# # finally order layers in panel based on sorted list
# unique = {}
# for i, node in enumerate(nodes_sorted):
# 	if node not in empty:
# 		layer = tuflowqgis_find_layer(node.name())
# 		repeated = False
# 		if layer.source() in unique:
# 			if unique[layer.source()][0] == layer.type():
# 				if layer.type() == QgsMapLayer.VectorLayer:
# 					if unique[layer.source()][1] == layer.geometryType():
# 						repeated = True
# 		if not repeated:
# 			node_new = QgsLayerTreeLayer(layer)
# 			node_new.setItemVisibilityChecked(node.itemVisibilityChecked())
# 			parent.insertChildNode(i, node_new)
# 			node.parent().removeChildNode(node)
# 			if layer.type() == QgsMapLayer.VectorLayer:
# 				unique[layer.source()] = (layer.type(), layer.geometryType())
# 			else:
# 				unique[layer.source()] = (layer.type(), -1)
# 		else:
# 			node.parent().removeChildNode(node)
# 	else:
# 		# if node is empty, remove from map
# 		node.parent().removeChildNode(node)


def sortLayerPanel(sort_locally=False):
    """
    Sort layers alphabetically in layer panel. Option to sort locally i.e. if layers
    have been grouped they will be kept in groups and sorted. Otherwise layers will be removed from the groups and
    sorted. DEMs will be put at bottom and Meshes will be just above DEMs.

    :param sort_locally: bool
    :return: void
    """

    legint = QgsProject.instance().layerTreeRoot()
    nodes = None
    groups = legint.findGroups(True)
    if not groups:
        groups = [legint]

    if not sort_locally:
        nodes = sum([x.findLayers() for x in groups], [])
        groups = [legint]

    for group in groups:
        sortNodesInGroup(group, nodes=nodes)

    if not sort_locally:
        for group in legint.findGroups():
            legint.removeChildNode(group)


# # grab all nodes that are QgsMapLayers - get to node bed rock i.e. not a group
# nodes = legint.findLayers()
#
# if sort_locally:
# 	# get all groups
# 	groups = []
# 	groupedNodes = []
# 	for node in nodes:
# 		parent = node.parent()
# 		if parent not in groups:
# 			groups.append(parent)
# 			groupedNodes.append([node])
# 		else:
# 			i = groups.index(parent)
# 			groupedNodes[i].append(node)
#
# # sort by group
# if sort_locally:
# 	for i, group in enumerate(groups):
# 		sortNodesInGroup(groupedNodes[i], group)
# else:
# 	sortNodesInGroup(nodes, legint)
# 	# delete now redundant groups in layer panel
# 	groups = legint.findGroups()
# 	for group in groups:
# 		legint.removeChildNode(group)


def getAllFolders(dir, relPath, variables, scenarios, events, output_drive=None, db=None):
    """
    Gets all possible existing folder combinations from << >> wild cards and possible options.

    :param dir: str path to directory
    :param relPath: str relative path
    :param variables: dict { IL: [ '5m' ] }
    :param scenarios: list -> str scenario name
    :param events: list -> str event name
    :param output_drive: str
    :return: list -> str file path
    """

    folders = []
    count = 0
    rpath = relPath
    for c in rpath.replace('\\', os.sep).split(os.sep):
        if re.findall(r'\.gpkg\s*>>', c, flags=re.IGNORECASE):
            if re.split(r'\.gpkg\s*>>', c, flags=re.IGNORECASE)[0].find('<<') > -1:
                count += 1
        else:
            if c.find('<<') > -1:
                count += 1
    dirs = [dir]
    if count == 0:
        if db is not None and os.path.splitext(relPath)[-1] == '':
            for d in db:
                for lyr in relPath.split('&&'):
                    layers = get_table_names(d)
                    if lyr.strip().lower() in [x.lower() for x in layers]:
                        lyr = layers[[x.lower() for x in layers].index(lyr.strip().lower())]
                        folders.append('{0}|layername={1}'.format(d, lyr))
        elif '.gpkg' in os.path.splitext(relPath)[-1].lower():
            if '>>' in os.path.splitext(relPath)[-1]:
                d, lyrs = os.path.splitext(relPath)[-1].split('>>')
                d = '{0}{1}'.format(getPathFromRel(dir, os.path.splitext(relPath)[0], output_drive=output_drive),
                                    d.strip())
                if os.path.exists(d):
                    layers = get_table_names(d)
                    for lyr in lyrs.strip().split('&&'):
                        if lyr.strip().lower() in [x.lower() for x in layers]:
                            lyr = layers[[x.lower() for x in layers].index(lyr.strip().lower())]
                            folders.append('{0}|layername={1}'.format(d, lyr))
            else:
                d = getPathFromRel(dir, relPath, output_drive=output_drive)
                lyr = os.path.basename(os.path.splitext(relPath)[0])
                if os.path.exists(d):
                    layers = get_table_names(d)
                    if lyr.strip().lower() in [x.lower() for x in layers]:
                        lyr = layers[[x.lower() for x in layers].index(lyr.strip().lower())]
                        folders.append('{0}|layername={1}'.format(d, lyr))
        else:
            folders.append(getPathFromRel(dir, relPath, output_drive=output_drive))
    else:
        for m in range(count):
            i = rpath.find('<<')
            j = rpath[i:].find('>>') + i
            vname = rpath[i:j + 2]  # variable name
            path_components = rpath.replace('\\', os.sep).split(os.sep)
            for k, pc in enumerate(path_components):
                if vname in pc:
                    break

            # what happens if there are multiple <<variables>> in path component e.g. ..\<<~s1~>>_<<~s2~>>\2d
            vname2 = []
            # j2 = j + 2
            j2 = 0
            # k2 = 0
            if pc.count('<<') > 1:
                for n in range(pc.count('<<')):
                    # if n > 0:  # ignore first instance since this is already vname
                    # k2 += j2
                    i2 = rpath[j2:].find('<<') + j2
                    j2 = rpath[i2:].find('>>') + i2 + 2
                    if n > 0:
                        vname2.append(rpath[i2:j2])
                vnames = [vname] + vname2
            else:
                vnames = [vname]

            # get all possible combinations
            combinations = getVariableCombinations(vnames, variables, scenarios, events)

            new_relPath = os.sep.join(path_components[:k + 1])
            if db is not None and os.path.splitext(new_relPath)[-1] == '':
                for d in db:
                    layers = get_table_names(d)
                    for combo in combinations:
                        p = new_relPath
                        for n, vname in enumerate(vnames):
                            p = p.replace(vname, combo[n])

                        for p2 in p.split('&&'):
                            if p2.strip().lower() in [x.lower() for x in layers]:
                                p2 = layers[[x.lower() for x in layers].index(p2.strip().lower())]
                                folders.append('{0}|layername={1}'.format(d, p2))
            else:
                for d in dirs[:]:
                    new_path = getPathFromRel(d, new_relPath, output_drive=output_drive)

                    for combo in combinations:
                        p = new_path
                        for n, vname in enumerate(vnames):
                            # check if variable name is start of absolute reference
                            # i.e. <<variable>>\results = C:\tuflow\results which means
                            # we don't need anything before the <<variable>>
                            if len(combo[n]) > 2:
                                combo[n] = combo[n].replace('/', os.sep)
                                if combo[n][1] == ':' or combo[n][:2] == '\\\\':
                                    b = p.find("<<")
                                    p = p[b:]
                            p = p.replace(vname, combo[n])

                        if m + 1 == count and '.gpkg' in os.path.splitext(p)[-1].lower():
                            ext = os.path.splitext(relPath)[-1]
                            if '>>' in ext:
                                db_, layer = ext.split('>>', 1)
                                db_ = '{0}{1}'.format(os.path.splitext(p)[0], db_)
                                layer = layer.strip()
                            else:
                                db_ = p
                                layer = os.path.basename(os.path.splitext(db_)[0])

                            if os.path.exists(db_):
                                layers = get_table_names(db_)
                                for combo in combinations:
                                    p2 = layer
                                    for n, vname in enumerate(vnames):
                                        p2 = p2.replace(vname, combo[n])

                                    for p3 in p2.split('&&'):
                                        if p3.strip().lower() in [x.lower() for x in layers]:
                                            p3 = layers[[x.lower() for x in layers].index(p3.strip().lower())]
                                            folders.append('{0}|layername={1}'.format(db_, p3))
                        else:
                            if os.path.exists(p):
                                if m + 1 == count:
                                    path_rest = os.sep.join(path_components[k + 1:])
                                    p = getPathFromRel(p, path_rest, output_drive=output_drive)
                                    if os.path.exists(p):
                                        folders.append(p)
                                else:
                                    dirs.append(p)

                dirs = dirs[1:]

                rpath = os.sep.join(path_components[k + 1:])

    return folders


def getVariableCombinations(vnames, variables, scenarios, events):
    """
    Get all possible combinations from << >> replacement

    :param vnames: list -> str wild card <<~s1~>>
    :param variables: dict { variable name: [ variable value ] }
    :param scenarios: list -> str scenario name
    :param events: list -> str event name
    :return: list -> list -> str
    """

    # collect lists to loop through
    combo_list = []
    for vname in vnames:
        # if defined variable
        if vname[2:-2].lower() in variables:
            combo_list.append(variables[vname[2:-2].lower()])

        # if <<s>>
        elif vname.lower()[2:5] == '~s~':
            combo_list.append(scenarios)

        # if <<~s1~>>
        elif vname.lower()[2:4] == '~s' and vname.lower()[5] == '~':
            combo_list.append(scenarios)

        # if <<~e~>>
        elif vname.lower()[2:5] == '~e~':
            combo_list.append(events)

        # if <<~e1~>>
        elif vname.lower()[2:4] == '~e' and vname.lower()[5] == '~':
            combo_list.append(events)

    no = 1
    for c in combo_list:
        no *= len(c)
    combinations = [['' for y in range(len(combo_list))] for x in range(no)]  # blank combination list
    # populate combinations list with components from each combo_list
    for i, combo in enumerate(combo_list):
        if i == 0:
            proceding_no = 1
            for c in combo_list[i + 1:]:
                proceding_no *= len(c)
            components = combo * proceding_no
        elif i + 1 == len(combo_list):
            preceding_no = 1
            for c in combo_list[:i]:
                preceding_no *= len(c)
            components = []
            for x in combo:
                components += [x] * preceding_no
        else:
            preceding_no = 1
            for c in combo_list[:i]:
                preceding_no *= len(c)
            proceding_no = 1
            for c in combo_list[i + 1:]:
                proceding_no *= len(c)
            components = []
            for x in combo:
                components += [x] * preceding_no
            components *= proceding_no
        for j, comp in enumerate(components):
            combinations[j][i] = comp

    return combinations


def ascToAsc(exe, function, workdir, grids, **kwargs):
    """
    Runs common funtions in the asc_to_asc utility.

    :param exe: str full path to executable
    :param function: str function type e.g. 'diff' or 'max'
    :param workdir: str path to working directory folder
    :param grids: list -> QgsMapLayer or str layer name or str file path to layer
    :param kwargs: dict keyword arguments
    :return: bool error, str message
    """

    inputs = []
    for grid in grids:
        if isinstance(grid, QgsMapLayer):
            layer_helper = LayerHelper(grid)
            inputs.append(layer_helper.tuflow_path)
        elif grid.replace('/', os.sep).count(os.sep) == 0:
            layer = tuflowqgis_find_layer(grid)
            if layer is not None:
                inputs.append(layer.dataProvider().dataSourceUri())
        elif os.path.exists(grid):
            inputs.append(grid)
        elif ' >> ' in grid:
            inputs.append(grid)

    args = [exe, '-b']

    if kwargs.get('format') and kwargs.get('version', 0) >= 20230100:
        args.append('-{0}'.format(kwargs.get('format')))

    if function.lower() == 'diff':
        if len(inputs) == 2:
            args.append('-dif')
            args.append(inputs[0])
            args.append(inputs[1])
        else:
            return True, 'Need exactly 2 input grids'
    elif function.lower() == 'max':
        if len(inputs) >= 2:
            args.append('-max')
            for input in inputs:
                args.append(input)
        else:
            return True, 'Need at least 2 input grids'
    elif function.lower() == 'stat':
        if len(inputs) >= 2:
            args.append('-statALL')
            for input in inputs:
                args.append(input)
        else:
            return True, 'Need at least 2 input grids'
    elif function.lower() == 'conv':
        if len(inputs) >= 1:
            args.append('-conv')
            for input in inputs:
                args.append(input)
        else:
            return True, 'Need at least one input grid'
    elif function.lower() == 'brkline':
        args.append('-brkline')
        args.append(kwargs.get('gis')[0])
        args.append(inputs[0])

    if 'out' in kwargs:
        if kwargs['out']:
            args.append('-out')
            args.append(kwargs['out'])

    if workdir:
        proc = subprocess.Popen(args, cwd=workdir)
    else:
        proc = subprocess.Popen(args)
    proc.wait()

    if 'saveFile' in kwargs:
        if kwargs['saveFile']:
            message = saveBatchFile(args, workdir)
            QMessageBox.information(None, "TUFLOW Utility", message)

    return False, ''


# out = ''
# for line in iter(proc.stdout.readline, ""):
#	if line == b"":
#		break
#	out += line.decode('utf-8')
#	if b'Fortran Pause' in line or b'ERROR' in line or b'Press Enter' in line or b'Please Enter' in line:
#		proc.kill()
#		return True, out
# out, err = proc.communicate()
# if err:
#	return True, out.decode('utf-8')
# else:
#	return False, out.decode('utf-8')


def tuflowToGis(exe, function, workdir, mesh, dataType, timestep, **kwargs):
    """
    Runs common funtions in the tuflow_to_gis utility.

    :param exe: str full path to executable
    :param function: str function type e.g. 'grid' 'points' 'vectors'
    :param workdir: str path to working directory
    :param mesh: str full path to mesh file
    :param dataType: str datatype for xmdf files
    :param timestep: str timestep
    :param kwargs: dict keyword arguments
    :return: bool error, str message
    """

    dataType2flag = {'depth': '-typed', 'water level': '-typeh', 'velocity': '-typev', 'z0': '-typez0'}

    out = None
    if 'out' in kwargs:
        out = ['-out']
        if workdir:
            out.append('{0}'.format(os.path.join(workdir, kwargs['out'])))
        else:
            out.append('{0}'.format(kwargs['out']))

    args = [exe, '-b', mesh]
    _2dm = Path(mesh).with_suffix('.2dm')
    if not _2dm.exists():
        if re.findall('\(.*\){0}$'.format(re.escape(Path(mesh).suffix)), Path(mesh).name):
            new_2dm = re.sub('\(.*\){0}$'.format(re.escape(Path(mesh).suffix)), '.2dm', mesh)
            if Path(new_2dm).exists():
                args.extend(['-2dm', str(new_2dm)])

    if isinstance(timestep, str) and (timestep.lower() == 'max' or timestep.lower() == 'maximum'):
        args.append('-max')
    elif isinstance(timestep, str) and timestep.lower() == 'all':
        args.append('tall')
    else:
        args.append('-t{0}'.format(timestep))
    if os.path.splitext(mesh)[1].upper() == '.XMDF':
        if dataType.lower() in dataType2flag:
            args.append(dataType2flag[dataType.lower()])
        else:
            # args.append('-type{0}'.format(dataType))
            args.append('-{0}'.format(dataType))
    if function.lower() == 'grid':
        args.append('-asc')
    elif function.lower() == 'points':
        args.append('-shp')
    elif function.lower() == 'vectors':
        args.append('-shp')
        args.append('-vector')
    if out:
        args.extend(out)

    if workdir:
        proc = subprocess.Popen(args, cwd=workdir)
    else:
        proc = subprocess.Popen(args)
    proc.wait()

    if 'saveFile' in kwargs:
        if kwargs['saveFile']:
            message = saveBatchFile(args, workdir)
            QMessageBox.information(None, "TUFLOW Utility", message)

    return False, ''


# out = ''
# for line in iter(proc.stdout.readline, ""):
#	if line == b"":
#		break
#	out += line.decode('utf-8')
#	if b'Fortran Pause' in line or b'ERROR' in line or b'Press Enter' in line or b'Please Enter' in line:
#		proc.kill()
#		return True, out
# out, err = proc.communicate()
# if err:
#	return True, out.decode('utf-8')
# else:
#	return False, out.decode('utf-8')


def resToRes(exe, function, workdir, meshes, dataType, **kwargs):
    """
    Runs common functions in the res_to_res utility

    :param exe: str full path to executable
    :param function: str function type e.g. 'info' or 'convert' ..
    :param workdir: str path to working directory
    :param meshes: list -> str full path to mesh
    :param dataType: str dataset type for xmdf files
    :param kwargs: dict keyword arguments
    :return: bool error, str message
    """

    dataType2flag = {'depth': '-typed', 'water level': '-typeh', 'velocity': '-typev', 'z0': '-typez0'}

    args = [exe, '-b']
    if meshes:
        if os.path.splitext(meshes[0])[1].upper() == '.XMDF':
            if dataType.lower() in dataType2flag:
                args.append(dataType2flag[dataType.lower()])
            elif dataType:
                args.append('-{0}'.format(dataType))
            else:
                pass
        if function.lower() == 'info':
            args.append('-xnfo')
            args.append(meshes[0])
            args.append('-out')
            tmpdir = tempfile.mkdtemp(suffix='res_to_res')
            file = os.path.join(tmpdir, 'info.txt')
            args.append(file)
        elif function.lower() == 'conv':
            args.append('-conv')
            args.append(meshes[0])
        elif function.lower() == 'max':
            args.append('-max')
            args += meshes
        elif function.lower() == 'conc':
            args.append('-con')
            args += meshes
    else:
        return True, 'No input meshes'

    if 'out' in kwargs:
        if kwargs['out']:
            if function.lower() != 'info':
                args.append('-out')
                args.append(kwargs['out'])

    if 'hide_window' in kwargs and kwargs['hide_window']:
        CREATE_NO_WINDOW = 0x08000000
        proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE,
                                creationflags=CREATE_NO_WINDOW)
    else:
        if workdir:
            proc = subprocess.Popen(args, cwd=workdir)
        else:
            proc = subprocess.Popen(args)
        proc.wait()
    # out = ''
    # for line in iter(proc.stdout.readline, ""):
    #	if line == b"":
    #		break
    #	out += line.decode('utf-8')
    #	if b'Fortran Pause' in line or b'ERROR' in line or b'Press Enter' in line or b'Please Enter' in line:
    #		proc.kill()
    #		return True, out
    # out, err = proc.communicate()
    # if err:
    #	return True, out.decode('utf-8')
    # else:
    if 'hide_window' in kwargs and kwargs['hide_window']:
        try:
            proc.wait(timeout=5)
            out, err = proc.communicate()
        except subprocess.TimeoutExpired:
            out, err = proc.communicate(input=b'\n')
            if err or 'Finished.' not in out.decode('utf-8', errors='ignore'):
                return True, out.decode('utf-8', errors='ignore')

        if not os.path.exists(file) or err:
            return True, out.decode('utf-8', errors='ignore')

    if function.lower() == 'info':
        info = ''
        try:
            with open(file, 'r', errors='ignore') as f:
                for line in f:
                    info += line
            shutil.rmtree(tmpdir)
            return False, info  # return info instead of process log
        except:
            return True, info
    else:
        if 'saveFile' in kwargs:
            if kwargs['saveFile']:
                message = saveBatchFile(args, workdir)
                QMessageBox.information(None, "TUFLOW Utility", message)

        return False, ''


# return False, out.decode('utf-8')

def tuflowUtility(exe, workdir, flags, saveFile):
    """

    :param exe: str full path to executable
    :param workdir: str path to working directory
    :param flags: str flags or list -> str flags
    :return: bool error, str message
    """
    outfile = None
    args = [exe, '-b']
    lines = flags.split('\n')
    i = -1
    for line in lines:
        if not line:
            continue
        i += 1
        args_ = args.copy()
        if type(line) is list:
            args_ += line
        else:
            f = line.strip().split(' ')
            for a in f:
                if a != '':
                    args_.append(a)

        if workdir:
            # proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=workdir)
            proc = subprocess.Popen(args_, cwd=workdir)
        else:
            proc = subprocess.Popen(args_)
        proc.wait()

        if saveFile:
            message = saveBatchFile(args_, workdir, i > 0, outfile)
            outfile = message.split(':', 1)[1].strip()

    if saveFile:
        QMessageBox.information(None, "TUFLOW Utility", message)

    return False, ''


# out = ''
# for line in iter(proc.stdout.readline, ""):
#	if line == b"":
#		break
#	out += line.decode('utf-8')
#	if b'Fortran Pause' in line or b'ERROR' in line or b'Press Enter' in line or b'Please Enter' in line:
#		proc.kill()
#		return True, out
# out, err = proc.communicate()
# if err:
#	return True, out.decode('utf-8')
# else:
#	return False, out.decode('utf-8')


def saveBatchFile(flags, workdir, append = False, outfile = None):
    # choose a directory to save file into
    # use working directory if available
    # otherwise scan batch file for the first applicable file and save in same location
    dir = None
    if workdir:
        dir = workdir
    else:
        for i, arg in enumerate(flags):
            if i > 0:
                if arg:
                    if arg[0] != '-':
                        if os.path.exists(arg):
                            dir = os.path.dirname(arg)
                            break

    if dir is None:
        return 'Error saving batch file'

    fname = os.path.splitext(os.path.basename(flags[0]))[0]
    if not outfile:
        outfile = '{0}.bat'.format(os.path.join(dir, fname))
    i = 0
    while os.path.exists(outfile) and not append:
        i += 1
        outfile = '{0}_[{1}].bat'.format(os.path.join(dir, fname), i)

    mode = 'a' if append else 'w'

    with open(outfile, mode) as fo:
        for i, arg in enumerate(flags):
            argWritten = False
            if i == 0:
                if type(arg) is str:
                    if arg:
                        if arg[0] != '-':
                            if arg[0] != '"' or arg[0] != "'":
                                fo.write('"{0}"'.format(arg))
                                argWritten = True
                if not argWritten:
                    fo.write('{0}'.format(arg))
            else:
                if type(arg) is str:
                    if arg:
                        if arg[0] != '-':
                            if arg[0] != '"' or arg[0] != "'":
                                fo.write(' "{0}"'.format(arg))
                                argWritten = True
                if not argWritten:
                    fo.write(' {0}'.format(arg))
        fo.write('\n')

    return 'Successfully Saved Batch File: {0}'.format(outfile)


def downloadBinPackage(packageUrl, destinationFileName):
    request = QNetworkRequest(QUrl(packageUrl))
    request.setRawHeader(b'Accept-Encoding', b'gzip,deflate')

    cache = QgsNetworkAccessManager.instance().cache().remove(QUrl(packageUrl))
    reply = QgsNetworkAccessManager.instance().get(request)
    evloop = QEventLoop()
    reply.finished.connect(evloop.quit)
    evloop.exec_(QEventLoop.ExcludeUserInputEvents)
    content_type = reply.rawHeader(b'Content-Type')
    # if content_type == QByteArray().append('application/zip'):
    if content_type == b'application/x-zip-compressed':
        if os.path.isfile(destinationFileName):
            os.unlink(destinationFileName)

        destinationFile = open(destinationFileName, 'wb')
        destinationFile.write(bytearray(reply.readAll()))
        destinationFile.close()
    else:
        ret_code = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
        raise IOError("{} {}".format(ret_code, packageUrl))


class Downloader(QObject):
    updated = pyqtSignal(int)
    finished = pyqtSignal(str)

    def __init__(self, packageUrl, destinationFileName):
        QObject.__init__(self, None)
        self.packageUrl = packageUrl
        self.destinationFileName = destinationFileName
        self.f = None
        self.reply = None
        self.timeout = False

    def start(self):
        try:
            from qgis.core import QgsNetworkAccessManager
            from PyQt5.QtNetwork import QNetworkRequest
            return self.start_with_qgis()
        except ImportError:
            return self.start_with_urlib()

    def download_progress(self, cur, total):
        if total > 0:
            done = int(cur / total * 100)
            self.updated.emit(done)

    def timedout(self):
        self.timeout = True

    def start_with_qgis(self):
        from qgis.core import QgsNetworkAccessManager
        from PyQt5.QtNetwork import QNetworkRequest
        from PyQt5.QtCore import QUrl, QEventLoop
        try:
            with open(self.destinationFileName, 'wb') as f:
                netman = QgsNetworkAccessManager.instance()
                _ = netman.cache().remove(QUrl(self.packageUrl))
                req = QNetworkRequest(QUrl(self.packageUrl))
                self.reply = netman.get(req)
                self.reply.setReadBufferSize(4096)
                self.reply.readyRead.connect(lambda: f.write(self.reply.readAll()))
                self.reply.finished.connect(self.reply.deleteLater)
                self.reply.downloadProgress.connect(self.download_progress)
                netman.requestTimedOut.connect(self.timedout)
                evloop = QEventLoop()
                self.reply.finished.connect(evloop.quit)
                evloop.exec_(QEventLoop.ExcludeUserInputEvents)
                ret_code = self.reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
                if self.timeout:
                    raise Exception('Timeout while downloading')
                if ret_code != 200:
                    raise Exception('Error downloading: {}'.format(self.reply.errorString()))
            self.finished.emit(None)
        except Exception as e:
            self.finished.emit(str(e))

    def start_with_urlib(self):
        from urllib.request import urlopen

        try:
            with urlopen(self.packageUrl) as request:
                total_length = request.length
                if os.path.isfile(self.destinationFileName):
                    os.unlink(self.destinationFileName)
                CHUNK = 4096
                prog = 0
                with open(self.destinationFileName, 'wb') as f:
                    for chunk in iter(lambda: request.read(CHUNK), ''):
                        prog += CHUNK
                        if not chunk:
                            break
                        f.write(chunk)
                        done = int(prog / total_length * 100)
                        self.updated.emit(done)
                        if QThread().currentThread().isInterruptionRequested():
                            break
        except Exception as e:
            self.finished.emit(str(e))
        # self.destinationFileName.close()
        # self.r.close()
        self.finished.emit(None)


class DownloadProgressBar(QObject):

    def __init__(self, label):
        QObject.__init__(self, None)
        self.layout = QVBoxLayout()
        self.label = QLabel(label)
        self.layout.addWidget(self.label)
        self.progressBar = QProgressBar()
        self.progressBar.setRange(0, 0)
        self.layout.addWidget(self.progressBar)
        self.widget = QWidget()
        self.widget.setAttribute(Qt.WA_DeleteOnClose)
        self.widget.setMinimumWidth(525)
        self.widget.setLayout(self.layout)
        self.widget.show()
        self.is_finished = False
        self.error = 0

    def start(self):
        self.widget.show()

    def finish(self, error):
        try:
            self.widget.close()
        except:
            pass
        self.error = error
        self.is_finished = True

    def update(self, prog):
        try:
            if prog > -1:
                if self.progressBar.maximum() != 100:
                    self.progressBar.setRange(0, 100)
                self.progressBar.setValue(prog)
        except:
            pass


class DownloadBinPackage(QObject):

    def __init__(self, packageUrl, destinationFileName, label, add_progress_bar=True, parent_widget=None):
        QObject.__init__(self, parent_widget)
        self.parent_widget = parent_widget
        self.packageUrl = packageUrl
        self.destinationFileName = destinationFileName
        self.add_progress_bar = add_progress_bar
        self.label = label
        self.user_cancelled = False

    def wait(self):
        while not self.progress_bar.is_finished:
            QgsApplication.processEvents()

        self.thread.quit()

        if self.progress_bar.error:
            raise IOError("error code {} {}".format(self.progress_bar.error, self.packageUrl))

    def stop(self):
        if not self.progress_bar.is_finished:
            self.user_cancelled = True
            self.thread.requestInterruption()
            self.thread.quit()

    def start(self):
        if self.add_progress_bar:
            self.progress_bar = DownloadProgressBar(self.label)
            self.downloader = Downloader(self.packageUrl, self.destinationFileName)
            self.thread = QThread()
            self.downloader.moveToThread(self.thread)
            self.downloader.updated.connect(self.progress_bar.update)
            self.downloader.finished.connect(self.progress_bar.finish)
            self.thread.started.connect(self.downloader.start)
            self.progress_bar.widget.destroyed.connect(self.stop)
            self.progress_bar.start()
            self.thread.setTerminationEnabled(True)
            self.thread.start()
        else:
            r = requests.get(self.packageUrl)
            if r.status_code == requests.codes.ok and r.headers['Content-Type'] == 'application/zip':
                if os.path.isfile(self.destinationFileName):
                    os.unlink(self.destinationFileName)
                destinationFile = open(self.destinationFileName, 'wb')
                destinationFile.write(bytearray(r.content))
                destinationFile.close()
            else:
                raise IOError("{} {}".format(r.status_code, self.packageUrl))


def getUtilityDownloadPaths(util_dict, util_path_file):
    # util_path_file = os.path.join(os.path.dirname(__file__), "__utilities__.txt")
    if not os.path.exists(util_path_file):
        return ""

    file_contents = numpy.genfromtxt(util_path_file, dtype=str, delimiter="==")
    d = {x[0].lower().strip(): x[1].strip() for x in file_contents}
    for key in util_dict:
        if key.lower() in d:
            util_dict[key] = d[key.lower()]

    if 'base_url' in d:
        return d['base_url']


def downloadUtility(utility, parent_widget=None):
    util_path_file = os.path.join(os.path.dirname(__file__), "__utilities__.txt")
    latestUtilities = {
        'asc_to_asc': '',
        'tuflow_to_gis': '',
        'res_to_res': '',
        '12da_to_from_gis': '',
        'convert_to_ts1': '',
        'tin_to_tin': '',
        'xsGenerator': '',
    }
    downloadBaseUrl = getUtilityDownloadPaths(latestUtilities, util_path_file)
    if not downloadBaseUrl:
        QMessageBox.critical(parent_widget,
                             'Could Not Download Utilities',
                             'Please check the following setting file exists and is correct:\n{0}'.format(
                                 util_path_file))
        return
    exe = os.path.basename(latestUtilities[utility])
    name = os.path.splitext(exe)[0]
    # utilityNames = {
    #     'asc_to_asc': '{0}/asc_to_asc_w64.exe'.format(name),
    #     'tuflow_to_gis': '{0}/TUFLOW_to_GIS_w64.exe'.format(name),
    #     'res_to_res': '{0}/res_to_res_w64.exe'.format(name),
    #     '12da_to_from_gis': '12da_to_from_gis.exe',
    #     'convert_to_ts1': 'convert_to_ts1.exe',
    #     'tin_to_tin': 'tin_to_tin.exe',
    #     'xsGenerator': 'xsGenerator.exe',
    # }

    # downloadBaseUrl = 'https://www.tuflow.com/Download/TUFLOW/Utilities/'
    destFolder = os.path.join(os.path.dirname(__file__), '_utilities')
    if not os.path.exists(destFolder):
        os.makedirs(destFolder)
    exePath = os.path.join(destFolder, exe)
    # url = downloadBaseUrl + exe
    url = downloadBaseUrl + "/" + latestUtilities[utility]

    qApp.setOverrideCursor(QCursor(Qt.WaitCursor))
    try:
        downloadBinPackage(url, exePath)
        # downloader = DownloadBinPackage(url, exePath, 'Downloading {0}. . .'.format(utility))
        # downloader.start()
        # downloader.wait()
        z = zipfile.ZipFile(exePath)
        z.extractall(destFolder)
        z.close()
        os.unlink(exePath)
        qApp.restoreOverrideCursor()

        extracted_name = [x.filename for x in z.filelist if os.path.splitext(x.filename)[1].upper() == ".EXE"]
        if extracted_name:
            extracted_name = extracted_name[0]
        else:
            extracted_name = ""

        # return os.path.join(destFolder, utilityNames[utility])
        return os.path.join(destFolder, extracted_name)
    except IOError as err:
        qApp.restoreOverrideCursor()
        raise Exception('Download of {0} failed. Please try again or contact support@tuflow.com for '
                        'further assistance.\n\n(Error: {1})'.format(utility, err))
    # QMessageBox.critical(parent_widget,
    # 					 'Could Not Download {0}'.format(utility),
    # 					 "Download of {0} failed. Please try again or contact support@tuflow.com for "
    # 					 "further assistance.\n\n(Error: {1})".format(utility, err))


def convertTimeToFormattedTime(time, hour_padding=2, unit='h'):
    """
    Converts time (hours or seconds) to formatted time hh:mm:ss.ms

    :param time: float
    :return: str
    """

    if unit == 's':
        d = timedelta(seconds=time)
    else:
        d = timedelta(hours=time)
    h = int(d.total_seconds() / 3600)
    m = int((d.total_seconds() % 3600) / 60)
    s = float(d.total_seconds() % 60)
    if '{0:05.02f}'.format(s) == '60.00':
        m += 1
        s = 0.
        if m == 60:
            h += 1
            m = 0

    if hour_padding == 2:
        format = '{0:%H}:{0:%M}:{0:%S.%f}'
        t = '{0:02d}:{1:02d}:{2:05.02f}'.format(h, m, s)
    elif hour_padding == 3:
        t = '{0:03d}:{1:02d}:{2:05.02f}'.format(h, m, s)
    elif hour_padding == 4:
        t = '{0:04d}:{1:02d}:{2:05.02f}'.format(h, m, s)
    else:
        t = '{0:05d}:{1:02d}:{2:05.02f}'.format(h, m, s)

    return t


def convertFormattedTimeToTime(formatted_time, hour_padding=2, unit='h'):
    """
    Converts formatted time hh:mm:ss.ms to time (hours or seconds)

    :param formatted_time: str
    :return: float
    """

    t = formatted_time.split(':')
    if len(t) < 3:
        return 0
    h = int(t[0]) if t[0] != '' else 0
    m = int(t[1]) if t[1] != '' else 0
    s = float(t[2]) if t[2] != '' else 0

    d = timedelta(hours=h, minutes=m, seconds=s)

    if unit == 's':
        return d.total_seconds()
    else:
        return d.total_seconds() / 3600


def convertFormattedDateToTime(formatted_date, format, date2time):
    """
    Converts formatted date (dd/mm/yyyy hh:mm:ss) to time
    """

    dt = datetime.strptime(formatted_date, format)
    if dt in date2time:
        return date2time[dt]
    else:
        return 0


def reSpecPlot(fig, ax, ax2, cax, bqv):
    """

    """

    if cax is None and not bqv:
        gs = gridspec.GridSpec(1, 1)
        rsi, rei, csi, cei = 0, 1, 0, 1
    else:
        gs = gridspec.GridSpec(1000, 1000)
        fig.subplotpars.bottom = 0  # 0.206
        fig.subplotpars.top = 1  # 0.9424
        fig.subplotpars.left = 0  # 0.085
        fig.subplotpars.right = 1  # 0.98
        padding = 3
        wpad = int((padding / fig.bbox.width) * 1000) + 1
        hpad = int((padding / fig.bbox.height) * 1000) + 1
        caxwidth = int((30 / fig.bbox.width) * 1000)
        xlabelsize = 70 if not ax.get_xlabel() else ax.xaxis.get_label().get_size() + ax.xaxis.get_ticklabels()[
            0].get_size() + \
                                                    ax.xaxis.get_tick_padding()
        ylabelsize = 70 if not ax.get_ylabel() else ax.yaxis.get_label().get_size() + ax.yaxis.get_ticklabels()[
            0].get_size() + \
                                                    ax.yaxis.get_tick_padding()
        rei = int(1000 - ((ax.xaxis.get_tightbbox(fig.canvas.get_renderer()).height +
                           xlabelsize) / fig.bbox.height * 1000 + hpad))

        csi = int((ax.yaxis.get_tightbbox(fig.canvas.get_renderer()).width +
                   ylabelsize) / fig.bbox.width * 1000 + wpad)
        rsi = hpad
        if cax is not None:
            width = int((40 / fig.bbox.width) * 1000)
            if ax2 is not None:
                width = int((90 / fig.bbox.width) * 1000)
            if cax != 1:
                # width = int((cax.xaxis.get_tightbbox(fig.canvas.get_renderer()).width + cax.yaxis.get_tightbbox(
                # 	fig.canvas.get_renderer()).width) / fig.bbox.width * 1000)
                cax_bbox_yaxis = cax.yaxis.get_tightbbox(fig.canvas.get_renderer())
                cax_bbox_xaxis = cax.xaxis.get_tightbbox(fig.canvas.get_renderer())
                if cax_bbox_xaxis is None:
                    cax_bbox_xaxis = cax.bbox
                # width = int((max(cax.yaxis.get_tightbbox(fig.canvas.get_renderer()).x1, cax.xaxis.get_tightbbox(fig.canvas.get_renderer()).x1)
                # 				 - cax.xaxis.get_tightbbox(fig.canvas.get_renderer()).x0) / fig.bbox.width * 1000)
                # width += max(0, int(cax.yaxis.get_tightbbox(fig.canvas.get_renderer()).x1 - fig.bbox.x1))
                width = int((max(cax_bbox_yaxis.x1, cax_bbox_xaxis.x1) - cax_bbox_xaxis.x0) / fig.bbox.width * 1000)
                width += max(0, int(cax_bbox_yaxis.x1 - fig.bbox.x1))

            cei = 1000 - width
        else:
            if ax2 is not None:
                y2labelsize = 70 if not ax2.get_ylabel() else ax2.yaxis.get_label().get_size() + \
                                                              ax2.yaxis.get_ticklabels()[0].get_size() + \
                                                              ax2.yaxis.get_tick_padding()
                cei = int(1000 - ax2.yaxis.get_tightbbox(fig.canvas.get_renderer()).width +
                          y2labelsize / fig.bbox.width * 1000 + wpad)
            else:
                cei = 1000 - wpad

    if bqv:
        rsi = rsi + int(30 / fig.bbox.height * 1000)

    gs_pos = gs[rsi:rei, csi:cei]
    pos = gs_pos.get_position(fig)
    ax.set_position(pos)
    ax.set_subplotspec(gs_pos)

    if cax is not None:
        if cax != 1:
            # cax_cei = int(max(0, cax.yaxis.get_tightbbox(fig.canvas.get_renderer()).x1 - fig.bbox.width) + 1)
            cax_cei = int(1000 - ((width + wpad) / 2) + (caxwidth / 2) - wpad)
            cax_csi = int(1000 - ((width + wpad) / 2) - (caxwidth / 2) - wpad)
            if bqv:
                gs_pos = gs[rsi:rei, cax_csi:cax_cei]
            else:
                gs_pos = gs[rsi:rei, cax_csi:cax_cei]
            pos = gs_pos.get_position(fig)
            cax.set_position(pos)
            cax.set_subplotspec(gs_pos)

    if ax2 is not None:
        ax2.set_position(pos)
        ax2.set_subplotspec(gs_pos)

    return gs, rsi, rei, csi, cei


def addColourBarAxes(fig, ax, ax2, bqv, **kwargs):
    """

    """

    padding = 3
    wpad = int((padding / fig.bbox.width) * 1000)
    hpad = int((padding / fig.bbox.height) * 1000)

    if 'respec' in kwargs:
        gs, rsi, rei, csi, cei = kwargs['respec']
        width = 1000 - cei
        caxwidth = int((30 / fig.bbox.width) * 1000)
        cax_cei = int(1000 - (width / 2) + (caxwidth / 2))
        cax_csi = int(1000 - (width / 2) - (caxwidth / 2))
        gs_pos = gs[rsi:rei, cax_csi:cax_cei]
        pos = gs_pos.get_position(fig)
        cax = kwargs['cax']
        cax.set_position(pos)
        cax.set_subplotspec(gs_pos)
    else:
        cax = 1  # dummy value
        gs, rsi, rei, csi, cei = reSpecPlot(fig, ax, ax2, cax, bqv)
        width = 1000 - cei
        caxwidth = int((30 / fig.bbox.width) * 1000)
        cax_cei = int(1000 - ((width + wpad) / 2) + (caxwidth / 2) - wpad)
        cax_csi = int(1000 - ((width + wpad) / 2) - (caxwidth / 2) - wpad)
        cax = fig.add_subplot(gs[rsi:rei, cax_csi:cax_cei])

    return cax


def addQuiverKey(fig, ax, ax2, bqv, qv, label, max_u, **kwargs):
    """

    """

    qk = 1
    if bqv:
        if len(fig.axes) == 2:
            cax = fig.axes[1]
        else:
            cax = None
    else:
        cax = None
    gs, rsi, rei, csi, cei = reSpecPlot(fig, ax, ax2, cax, bqv)

    if cax is not None:
        X = cei / 1000
        Y = 1 - ((rsi / 1000 + (4 / fig.bbox.height)) / 100 + (20 / fig.bbox.height))
    else:
        X = 0.95
        Y = 0.05
    u = max_u / 4
    qk = ax.quiverkey(qv, X=X, Y=Y, U=u, label=label, labelpos='W', coordinates='figure')
    if cax is not None:
        addColourBarAxes(fig, ax, ax2, bqv, respec=(gs, rsi, rei, csi, cei), cax=cax, qk=qk)


def removeDuplicateLegendItems(labels, lines):
    """

    """

    labels_copy, lines_copy = [], []
    for i, l in enumerate(labels):
        if l not in labels_copy:
            labels_copy.append(l)
            lines_copy.append(lines[i])

    return labels_copy, lines_copy


def removeCurtainItems(labels, lines):
    """

    """

    labels_copy, lines_copy = [], []
    for i, l in enumerate(lines[:]):
        if type(l) is not PolyCollection and type(l) is not Quiver:
            lines_copy.append(l)
            labels_copy.append(labels[i])

    return labels_copy, lines_copy


def addLegend(fig, ax, ax2, pos):
    """

    """

    line, lab = ax.get_legend_handles_labels()
    if ax2 is not None:
        line2, lab2 = ax2.get_legend_handles_labels()
    else:
        line2, lab2 = [], []

    lines = line + line2
    labels = lab + lab2
    labels, lines = removeCurtainItems(labels, lines)
    labels, lines = removeDuplicateLegendItems(labels, lines)

    ax.legend(lines, labels, loc=pos)


def convertFormattedTimeToFormattedTime(formatted_time: str, return_format: str = '{0:02d}:{1:02d}:{2:02.0f}') -> str:
    """
    Converts formatted time hh:mm:ss.ms to another formatted time string. Benefit is that it can
    take non digit characters e.g. '_'

    :param formatted_time: str
    :param return_format: str format of the return time string
    :return: str
    """

    t = formatted_time.split(':')
    h = int(t[0]) if t[0] != '' else 0
    m = int(t[1]) if t[1] != '' else 0
    s = float(t[2]) if t[2] != '' else 0

    return return_format.format(h, m, s)


def findToolTip(text, engine="classic"):
    """
    Finds relevant tool tips if file exists

    :param text: empty type
    :return: dict -> { command: value, description: value, wiki link: value, manual link: value, manual page: value }
    """

    if engine.lower() == 'flexible mesh':
        dir = os.path.join(os.path.dirname(__file__), 'empty_tooltips', 'fv')
    else:
        dir = os.path.join(os.path.dirname(__file__), 'empty_tooltips')
    properties = {'location': None,
                  'command': None,
                  'description': None,
                  'wiki link': None,
                  'manual link': None,
                  'manual page': None
                  }

    glob_search = ('{0}{1}*.txt'.format(dir, os.sep))
    files = glob.glob(glob_search)
    for file in files:
        name = os.path.splitext(os.path.basename(file))[0]
        if name.lower() == text.lower():
            with open(os.path.join(dir, file), 'r') as f:
                for line in f:
                    if '==' in line:
                        command, value = line.split('==')
                        command = command.strip()
                        value = value.strip()
                        value = value.replace('\\n', '\n')
                        value = value.replace('\\t', '\t')
                        properties[command.lower()] = value
            break

    return properties


def calculateLength(p1, p2, mapUnits, desiredUnits='m'):
    """
    Calculate cartesian length between 2 points

    :param p1: QgsPoint point 1
    :param p2: QgsPoint point 2 - this is previous point
    :param mapUnits: Enumerator QgsUnitTypes::DistanceUnit
    :param desiredUnits: str 'm' or 'ft'
    :return: float distance
    """

    if mapUnits != QgsUnitTypes.DistanceDegrees:
        return ((p1.y() - p2.y()) ** 2. + (p1.x() - p2.x()) ** 2.) ** 0.5  # simple trig
    else:
        # do some spherical conversions
        try:
            p1Converted = from_latlon(p1.y(), p1.x())
            p2Converted = from_latlon(p2.y(), p2.x())
        except:
            return None
        metres = ((p1Converted[1] - p2Converted[1]) ** 2. + (p1Converted[0] - p2Converted[0]) ** 2.) ** 0.5
        if desiredUnits == 'm':
            return metres
        elif desiredUnits == 'ft':
            return metres * 3.28084


def createNewPoint(p1, p2, length, new_length, mapUnits):
    """
    Create new QgsPoint at a desired length between 2 points

    :param p1: QgsPoint point 1
    :param p2: QgsPoint point 2 - this is previous point
    :param length: float existing length between 2 input points
    :param new_length: float length to insert new point
    :param mapUnits: Enumerator QgsUnitTypes::DistanceUnit
    :return: QgsPoint new point
    """

    if mapUnits != QgsUnitTypes.DistanceDegrees:
        # simple trig
        angle = asin((p1.y() - p2.y()) / length)
        x = p2.x() + (new_length * cos(angle)) if p1.x() - p2.x() >= 0 else p2.x() - (new_length * cos(angle))
        y = p2.y() + (new_length * sin(angle))
        return QgsPoint(x, y)
    else:
        # do some spherical conversions
        p1Converted = from_latlon(p1.y(), p1.x())
        p2Converted = from_latlon(p2.y(), p2.x())
        angle = asin((p1Converted[1] - p2Converted[1]) / length)
        x = p2Converted[0] + (new_length * cos(angle)) if p1Converted[0] - p2Converted[0] >= 0 else p2Converted[0] - (
                new_length * cos(angle))
        y = p2Converted[1] + (new_length * sin(angle))
        pointBackConveted = to_latlon(x, y, p1Converted[2], p1Converted[3])
        return QgsPoint(pointBackConveted[1], pointBackConveted[0])


def getParabolicCoord(x, x1, x2, x3, y1, y2, y3):
    """
    Return y coordinate from x coordinate based on a parabolic
    curve fitted to 3 points (x1, y1) | (x2, y2) | (x3, y3)

    :param x: float
    :param x1: float
    :param x2: float
    :param x3: float
    :param y1: float
    :param y2: float
    :param y3: float
    :return: float
    """

    # make sure all inputs are floats
    x = float(x)
    x1 = float(x1)
    x2 = float(x2)
    x3 = float(x3)
    y1 = float(y1)
    y2 = float(y2)
    y3 = float(y3)

    # eqn ax^2 + bx + c
    # work out a, b, c values
    aNom = x3 * (y2 - y1) + x2 * (y1 - y3) + x1 * (y3 - y2)
    aDen = (x1 - x2) * (x1 - x3) * (x2 - x3)
    a = aNom / aDen

    bNom = x1 ** 2 * (y2 - y3) + x3 ** 2 * (y1 - y2) + x2 ** 2 * (y3 - y1)
    bDen = (x1 - x2) * (x1 - x3) * (x2 - x3)
    b = bNom / bDen

    cNom = x2 ** 2 * (x3 * y1 - x1 * y3) + x2 * (x1 ** 2 * y3 - x3 ** 2 * y1) + x1 * x3 * y2 * (x3 - x1)
    cDen = (x1 - x2) * (x1 - x3) * (x2 - x3)
    c = cNom / cDen

    return a * x ** 2 + b * x + c


def getRasterValue(point, raster):
    """
    Gets the elevation value from a raster at a given location. Assumes raster has only one band or that the first
    band is elevation.

    :param point: QgsPoint
    :param raster: QgsRasterLayer
    :return: float elevation value
    """
    point = QgsPointXY(point)
    return raster.dataProvider().identify(point, QgsRaster.IdentifyFormatValue).results()[1]


class ReallyBasicFieldType:
    Other = -1
    String = 0
    Number = 1
    Any = 2

    @staticmethod
    def fromQVariantType(qvariant_type):
        if qvariant_type == QVariant.String:
            return ReallyBasicFieldType.String
        elif qvariant_type == QVariant.Double or qvariant_type == QVariant.LongLong or qvariant_type == QVariant.Int:
            return ReallyBasicFieldType.Number
        else:
            return ReallyBasicFieldType.Other

    @staticmethod
    def toString(field_type):
        if field_type == ReallyBasicFieldType.String:
            return 'String'
        elif field_type == ReallyBasicFieldType.Number:
            return 'Number  (int or float)'
        else:
            return 'Other'


def is1dNetwork(layer, report_where=False):
    """
    Checks if a layer is a 1d_nwk

    :param layer: QgsMapLayer
    :return: bool
    """

    from .gui.logging import Logging
    correct1dNetworkType = [ReallyBasicFieldType.String, ReallyBasicFieldType.String, ReallyBasicFieldType.Any,
                            ReallyBasicFieldType.String, ReallyBasicFieldType.Number,
                            ReallyBasicFieldType.Number, ReallyBasicFieldType.Number, ReallyBasicFieldType.Number,
                            ReallyBasicFieldType.Number, ReallyBasicFieldType.Any,
                            ReallyBasicFieldType.String, ReallyBasicFieldType.String, ReallyBasicFieldType.Number,
                            ReallyBasicFieldType.Number, ReallyBasicFieldType.Number,
                            ReallyBasicFieldType.Number, ReallyBasicFieldType.Number, ReallyBasicFieldType.Number,
                            ReallyBasicFieldType.Number, ReallyBasicFieldType.Number]

    if not isinstance(layer, QgsVectorLayer):
        return False

    isgpkg = layer.storageType() == 'GPKG'

    if isgpkg:
        correct1dNetworkType.insert(0, ReallyBasicFieldType.Number)
        count = 21
        i = 0
    else:
        count = 20
        i = 0

    fieldTypes = []
    # for i, f in enumerate(layer.getFeatures()):
    # 	if i > 0:
    # 		break
    # 	fields = f.fields()
    fields = layer.fields()
    for j in range(fields.count()):
        if j > count - 1:
            break
        field = fields.field(j)
        fieldType = field.type()
        fieldTypes.append(ReallyBasicFieldType.fromQVariantType(fieldType))

    if len(fieldTypes) < count:
        if report_where:
            Logging.warning('Field count does not match the expected minimum for 1d_nwk: Expected {0}, Received {1}'.format(count, len(fieldTypes)))
        return False

    is_1d_nwk = True
    for i in range(count):
        field_expected = correct1dNetworkType[i]
        field_received = fieldTypes[i]
        if field_expected == ReallyBasicFieldType.Any:
            continue
        if field_expected != field_received:
            is_1d_nwk = False
            field = fields.field(i)
            if report_where:
                Logging.warning(
                    'Field does not match 1d_nwk type: ({0}) {1}: Expected {2}, Received {3}'.format(i+1, field.name(), ReallyBasicFieldType.toString(field_expected), ReallyBasicFieldType.toString(field_received))
                )
    return is_1d_nwk



def is1dTable(layer):
    """
    Checks if a layer is a 1d_ta type

    :param layer: QgsVectorLayer
    :return: bool
    """

    if not isinstance(layer, QgsVectorLayer):
        return False

    isgpkg = False
    is_memory = False
    if re.findall(re.escape(r'.gpkg|layername='), layer.dataProvider().dataSourceUri(), re.IGNORECASE):
        isgpkg = True
    elif re.findall(re.escape('memory?geometry'), layer.dataProvider().dataSourceUri()):
        is_memory = True

    try:
        if isgpkg:
            lyrname = re.split(r'\.gpkg\|layername=', layer.dataProvider().dataSourceUri(), flags=re.IGNORECASE)[1]
        elif is_memory:
            lyrname = layer.name()
        else:
            lyrname = Path(layer.dataProvider().dataSourceUri()).stem
        if '|' in lyrname:
            lyrname = lyrname.split('|')[0]
        if not re.findall(r'^1d_', lyrname, flags=re.IGNORECASE):
            return False
    except RuntimeError:
        return False

    if isgpkg:
        correct1dTableType = [QVariant.LongLong, QVariant.String, QVariant.String, QVariant.String, QVariant.String,
                              QVariant.String,
                              QVariant.String, QVariant.String, QVariant.String, QVariant.String]
        count = 10
    else:
        correct1dTableType = [QVariant.String, QVariant.String, QVariant.String, QVariant.String, QVariant.String,
                              QVariant.String, QVariant.String, QVariant.String, QVariant.String]
        count = 9

    fieldTypes = []
    # for i, f in enumerate(layer.getFeatures()):
    # 	if i > 0:
    # 		break
    # 	fields = f.fields()
    fields = layer.fields()
    if fields.count() < count:
        return False
    for j in range(0, count):
        field = fields.field(j)
        fieldType = field.type()
        fieldTypes.append(fieldType)

    if fieldTypes == correct1dTableType:
        i_source = 1 if isgpkg else 0
        if fields.field(i_source).length() < 5:
            return False
        return True
    else:
        return False


def isPlotLayer(layer, geom=''):
    """

    """
    from .utils.map_layer import file_from_data_source
    from .tuflow_results_gpkg import ResData_GPKG

    if not isinstance(layer, QgsVectorLayer):
        return False

    if layer.customProperty('isTUFLOWPlotLayer'):
        return True

    isgpkg = layer.storageType() == 'GPKG'

    if not geom:
        geom = 'PLR'
    s = r'(?:[_\s]PLOT[_\s][{0}])|(?:_ts_([12]d_)?[PLR])'.format(geom)
    if not re.findall(s, layer.name(), flags=re.IGNORECASE):
        return False

    if isgpkg:
        res = ResData_GPKG()
        err, _ = res.Load(file_from_data_source(layer.dataProvider().dataSourceUri()))
        if not err:
            return True
        correctPlotType = [QVariant.LongLong, QVariant.String, QVariant.String, QVariant.String]
        count = 4
    else:
        correctPlotType = [QVariant.String, QVariant.String, QVariant.String]
        count = 3

    fieldTypes = []
    for i, f in enumerate(layer.getFeatures()):
        if i > 0:
            break
        fields = f.fields()
        if fields.count() < count:
            return False
        for j in range(0, count):
            field = fields.field(j)
            fieldType = field.type()
            fieldTypes.append(fieldType)

    if fieldTypes == correctPlotType:
        return True
    else:
        return False


def is2dBCLayer(layer):
    """

    """

    if not isinstance(layer, QgsVectorLayer):
        return False

    isgpkg = False
    if re.findall(re.escape(r'.gpkg|layername='), layer.dataProvider().dataSourceUri(), re.IGNORECASE):
        isgpkg = True

    count = 8
    correct_attr = [QVariant.String, QVariant.String, QVariant.String, QVariant.Double, QVariant.Double, QVariant.Double, QVariant.Double, QVariant.Double]
    if isgpkg:
        correct_attr.insert(0, QVariant.LongLong)
        count += 1

    fieldTypes = []
    for i, f in enumerate(layer.getFeatures()):
        if i > 0:
            break
        fields = f.fields()
        if fields.count() < count:
            return False
        for j in range(0, count):
            field = fields.field(j)
            fieldType = field.type()
            fieldTypes.append(fieldType)

    return fieldTypes == correct_attr


def isTSLayer(layer, results=None):
    if layer is None:
        return False
    if isinstance(layer, str):
        name = layer
    else:
        name = layer.dataProvider().dataSourceUri()
    if re.findall(re.escape(r'.gpkg|layername='), name, flags=re.IGNORECASE):
        name = re.split(re.escape(r'.gpkg|layername='), name, flags=re.IGNORECASE)[-1]
        name = name.split('|')[0]
    elif re.findall(r'^memory', name):
        name = layer.name()
    else:
        name = Path(name).stem

    return re.findall(r'_TS(MB|MB1d2d)?(_[PLR])?$', name, flags=re.IGNORECASE) and (results is None or name in results)


def clean_data_source_(data_source: str) -> str:
    if '|layername=' in data_source:
        return '|'.join(data_source.split('|')[:2])
    else:
        return '|'.join(data_source.split('|')[:1])


def layer_name_from_data_source_(data_source: str) -> str:
    if '|layername=' in data_source:
        return data_source.split('|')[1].split('=')[1]
    else:
        return Path(clean_data_source_(data_source)).stem


def isBcLayer(layer: QgsVectorLayer):
    if not layer or layer.type() != QgsMapLayer.VectorLayer:
        return False
    name = layer_name_from_data_source_(layer.dataProvider().dataSourceUri())
    return bool(re.findall(r'(^[12]d_(?:bc|sa|rf))', name, flags=re.IGNORECASE))


def getRasterValue(point, raster):
    """
    Gets the elevation value from a raster at a given location. Assumes raster has only one band or that the first
    band is elevation.

    :param point: QgsPoint
    :param raster: QgsRasterLayer
    :return: float elevation value
    """
    try:
        return raster.dataProvider().identify(QgsPointXY(point), QgsRaster.IdentifyFormatValue).results()[1]
    except KeyError:
        return numpy.nan


def readInvFromCsv(source, typ):
    """
    Reads Table CSV file and returns the invert

    :param source: string - csv source file
    :param typ: string - table type
    :return: float - invert
    """

    header = False
    firstCol = []
    secondCol = []
    with open(source, 'r') as fo:
        for f in fo:
            line = f.split(',')
            if not header:
                try:
                    float(line[0].strip('\n').strip())
                    header = True
                except:
                    pass
            if header:
                firstCol.append(float(line[0].strip('\n').strip()))
                secondCol.append(float(line[1].strip('\n').strip()))
    if typ.lower() == 'xz' or typ.lower()[0] == 'w':
        if secondCol:
            return min(secondCol)
        else:
            return None
    else:
        if firstCol:
            return min(firstCol)
        else:
            return None


def getNetworkMidLocation(feature):
    """
    Returns the location of the mid point along a polyline

    :param usVertex: QgsPoint
    :param dsVetex: QgsPoint
    :return: QgsPoint
    """

    from math import sin, cos, asin

    length = feature.geometry().length()
    desiredLength = length / 2.
    points, chainages, directions = lineToPoints(feature, 99999, QgsUnitTypes.DistanceMeters)
    chPrev = 0
    for i, ch in enumerate(chainages):
        if ch > desiredLength and chPrev < desiredLength:
            break
        else:
            chPrev = ch
    usVertex = points[i - 1]
    dsVertex = points[i]
    length = ((dsVertex[1] - usVertex[1]) ** 2. + (dsVertex[0] - usVertex[0]) ** 2.) ** 0.5
    newLength = desiredLength - chPrev
    angle = asin((dsVertex[1] - usVertex[1]) / length)
    x = usVertex[0] + (newLength * cos(angle)) if dsVertex[0] - usVertex[0] >= 0 else usVertex[0] - (newLength * cos(
        angle))
    y = usVertex[1] + (newLength * sin(angle))
    return QgsPoint(x, y)


def interpolateObvert(usInv, dsInv, size, xValues):
    """
    Creates a list of obvert elevations for chainages along a pipe

    :param usInv: float - upstream invert
    :param dsInv: float - downstream invert
    :param xValues: list - chainage values to map obvert elevations to
    :param size: float - pipe height
    :return: list - obvert elevations
    """

    usObv = usInv + size
    dsObv = dsInv + size
    xStart = xValues[0]
    xEnd = xValues[-1]
    obvert = []
    for i, x in enumerate(xValues):
        if i == 0:
            obvert.append(usObv)
        elif i == len(xValues) - 1:
            obvert.append(dsObv)
        else:
            interpolate = (dsObv - usObv) / (xEnd - xStart) * (x - xStart) + usObv
            obvert.append(interpolate)
    return obvert


def browse(parent: QWidget = None, browseType: str = '', key: str = "TUFLOW",
           dialogName: str = "TUFLOW", fileType: str = "ALL (*)",
           lineEdit=None, icon: QIcon = None, action=None, allowDuplicates=True, default_filename=None) -> None:
    """
    Browse folder directory

    :param parent: QWidget Parent widget
    :param type: str browse type 'folder' or 'file'
    :param key: str settings key
    :param dialogName: str dialog box label
    :param fileType: str file extension e.g. "AVI files (*.avi)"
    :param lineEdit: QLineEdit to be updated by browsing
    :param icon: QIcon dialog window icon
    :param action: lambda function
    :param bool: noDuplicates - if adding to list widget, don't allow duplicate entries
    :return: str
    """

    settings = QSettings()
    lastFolder = settings.value(key)

    startDir = os.getcwd()
    if lineEdit is not None:
        if type(lineEdit) is QLineEdit:
            if not re.findall(r'^<.*>$', lineEdit.text()) and lineEdit.text():
                startDir = lineEdit.text()
        elif type(lineEdit) is QComboBox:
            if not re.findall(r'^<.*>$', lineEdit.currentText()) and lineEdit.currentText():
                startDir = lineEdit.currentText()

    if lastFolder and startDir == os.getcwd():  # if outFolder no longer exists, work backwards in directory until find one that does
        if Path(Path(lastFolder).drive).exists():
            pattern = r'[a-z]\:\\$'  # windows root drive directory
            loop_limit = 100
            loop_count = 0
            while lastFolder:
                if os.path.exists(lastFolder):
                    startDir = lastFolder
                    break
                elif not lastFolder:
                    startDir = lastFolder
                    break
                elif re.findall(pattern, lastFolder, re.IGNORECASE):
                    startDir = ''
                    break
                elif loop_count > loop_limit:
                    startDir = ''
                    break
                else:
                    lastFolder = os.path.dirname(lastFolder)
                    loop_count += 1
    if default_filename:
        startDir = os.path.join(startDir, default_filename)
    dialog = QFileDialog(parent, dialogName, startDir, fileType)
    f = []
    if icon is not None:
        dialog.setWindowIcon(icon)
    if browseType == 'existing folder':
        dialog.setAcceptMode(QFileDialog.AcceptOpen)
        dialog.setFileMode(QFileDialog.Directory)
        dialog.setOption(QFileDialog.ShowDirsOnly)
        dialog.setViewMode(QFileDialog.Detail)
    # f = QFileDialog.getExistingDirectory(parent, dialogName, startDir)
    elif browseType == 'existing file':
        dialog.setAcceptMode(QFileDialog.AcceptOpen)
        dialog.setFileMode(QFileDialog.ExistingFile)
        dialog.setViewMode(QFileDialog.Detail)
    # f = QFileDialog.getOpenFileName(parent, dialogName, startDir, fileType)[0]
    elif browseType == 'existing files':
        dialog.setAcceptMode(QFileDialog.AcceptOpen)
        dialog.setFileMode(QFileDialog.ExistingFiles)
        dialog.setViewMode(QFileDialog.Detail)
    # f = QFileDialog.getOpenFileNames(parent, dialogName, startDir, fileType)[0]
    elif browseType == 'output file':
        dialog.setAcceptMode(QFileDialog.AcceptSave)
        dialog.setFileMode(QFileDialog.AnyFile)
        dialog.setViewMode(QFileDialog.Detail)
    elif browseType == 'output database':
        dialog.setAcceptMode(QFileDialog.AcceptSave)
        dialog.setFileMode(QFileDialog.AnyFile)
        dialog.setViewMode(QFileDialog.Detail)
        dialog.setOptions(QFileDialog.DontConfirmOverwrite)
    # f = QFileDialog.getSaveFileName(parent, dialogName, startDir, fileType)[0]
    else:
        return
    if dialog.exec():
        f = dialog.selectedFiles()
    if f:
        if type(f) is list:
            fs = ''
            for i, a in enumerate(f):
                if i == 0:
                    value = a.replace('/', os.sep).replace('\\', os.sep)
                    fs += a.replace('/', os.sep).replace('\\', os.sep)
                else:
                    fs += ';;' + a.replace('/', os.sep).replace('\\', os.sep)
            f = fs
        else:
            f = f.replace('/', os.sep).replace('\\', os.sep)
            value = f
        f = re.sub(r'[\\/]', re.escape(os.sep), f)  # os slashes
        settings.setValue(key, value)
        if lineEdit is not None:
            if type(lineEdit) is QLineEdit:
                lineEdit.setText(f)
            elif type(lineEdit) is QComboBox:
                lineEdit.setCurrentText(f)
            elif type(lineEdit) is QTableWidgetItem:
                lineEdit.setText(f)
            elif type(lineEdit) is QModelIndex:
                lineEdit.model().setData(lineEdit, f, Qt.EditRole)
            elif type(lineEdit) is QListWidget:
                items = [lineEdit.item(x).text() for x in range(lineEdit.count())]
                for f2 in f.split(';;'):
                    if not allowDuplicates:
                        if f2 not in items:
                            lineEdit.addItem(f2)
                    else:
                        lineEdit.addItem(f2)
                for i in range(lineEdit.count()):
                    item = lineEdit.item(i)
                    if item.text() in f.split(';;'):
                        item.setSelected(True)
        else:
            if browseType == 'existing files':
                return f.split(';;')
            else:
                return f

        if action is not None:
            action()


def getResultPathsFromTLF(fpath: str, read_method: int = 0) -> (list, list, list):
    """
    Gets result paths from TLF file

    :param fpath: str full path to .tlf
    :return: list res1D, list res2D, list messages
    """

    if not os.path.exists(fpath):
        return [], [], ['File Does Not Exist: {0}'.format(fpath)]

    secondaryExt = os.path.splitext(os.path.splitext(fpath)[0])[1]
    # if secondaryExt != '':
    if secondaryExt.upper() == '.HPC':
        return [], [], ['Please Make Sure Selecting .tlf Not {0}.tlf'.format(secondaryExt)]

    li = 0
    res1D = []
    res2D = []
    try:
        # if read_method == 0:
        #     # with open(fpath, 'r') as fo:
        #     fo = open(fpath, 'r')
        # else:
        #     fo = codecs.open(fpath, 'r', locale.getpreferredencoding())
        # while True:
        #     try:
        #         line = fo.readline()  # changed to this so i can use try/except
        #         x = fo.tell()
        #         li += 1
        #     except:
        #         if read_method == 0:
        #             fo.close()
        #             return getResultPathsFromTLF(fpath,)
        #         else:
        #             raise Exception(f"Error reading file - encoding error - line {li + 1}\n"
        #                             "Try converting file to UTF-8 (e.g. in Notepad++)\n"
        #                             "https://wiki.tuflow.com/index.php?title=TUFLOW_Message_0060")
        with open(fpath, 'r', errors='ignore') as fo:
            for line in fo:
                if line == "":
                    break
                # for line in fo:
                if '.xmdf' in line.lower():
                    if line.count('"') >= 2:
                        res = line.split('"')[1]
                        if res not in res2D:
                            if os.path.exists(res):
                                res2D.append(res)
                elif 'opening gis layer:' in line.lower() and '_PLOT' in line:
                    if len(line) > 20:
                        path = line[19:].strip()
                        basename = os.path.splitext(os.path.basename(path))[0][:-5]
                        if re.findall(r"_[PLR]$", basename, flags=re.IGNORECASE):
                            basename = basename[:-2]
                        dir = os.path.dirname(os.path.dirname(path))
                        res = '{0}.tpc'.format(os.path.join(dir, basename))
                        if res not in res1D:
                            if os.path.exists(res):
                                res1D.append(res)
                elif 'swmm geopackage time series file:' in line.strip().lower():
                    if len(line.strip()) > 33:
                        path = line.strip()[33:].strip()
                        res1D.append(path)

    except IOError:
        if not fo.closed:
            fo.close()
        return [], [], ['Unexpected Error Opening File: {0}'.format(fpath)]
    except Exception as e:
        if not fo.closed:
            fo.close()
        return [], [], [f'Unexpected Error: {e}']

    # if not fo.closed:
    #     fo.close()

    return res1D, res2D, []


def isBlockStart(text: str) -> bool:
    """
    Only call if it is a start or end block header (not an ordinary line)

    :param text: str
    :return: bool
    """

    line = text.strip()
    if len(line) > 1:
        if line[1] == '/':
            return False

    return True


def blockName(text: str) -> str:
    """

    :param text: str
    :return: str
    """

    line = text.strip()
    if line:
        if line[0] == '<' and line[-1] == '>':
            return line.strip('</>')

    return ''


def removeGlobalSetting(text: str) -> None:
    """


    :param text: str
    :return: None
    """

    line = text.strip()
    if line:
        QSettings().remove(line)


def removeProjectSetting(text: str, enum: bool = False) -> None:
    """


    :param text: str
    :param enum: bool True to enumerate until False
    :return: None
    """

    line = text.strip()
    if line:
        try:
            scope, key = line.split(',')
        except ValueError:
            return
        if not enum:
            QgsProject.instance().removeEntry(scope, key)
        else:
            i = 0
            newKey = key.replace('{0}', i)
            while QgsProject.instance().removeEntry(scope, newKey):
                i += 1
                newKey = key.replace('{0}', i)


def resetQgisSettings(e: QEvent = False, scope: str = 'Global', **kwargs) -> None:
    """
    Can choose to skip certain parameters as specified. Or you can
    choose to only reset one

    :param scope: str 'global' or 'project'
    :param kwargs: dict of specifics to either leave out (=False) or only (=True) e.g. tuviewer=True will only delete tuviewer related settings, tuviewer=False skips deleting tuviewer settings
    :return: None
    """

    varFile = os.path.join(os.path.dirname(__file__), "__settings_variables__.txt")
    if not os.path.exists(varFile):
        return

    # deal with kwargs
    deleteAll = False
    varToDelete = []
    varToSkip = []
    for kw, arg in kwargs.items():
        if type(arg) is bool:
            if arg:
                if kw not in varToDelete:
                    varToDelete.append(kw)
            else:
                if kw not in varToSkip:
                    varToSkip.append(kw)
    if not varToDelete:
        deleteAll = True
    if len(varToDelete) > 1:
        # can only do one of these at the moment
        varToDelete = varToDelete[0:1]
    # varToDelete.append(scope.lower())

    enumerate = False
    toEnumerate = []

    # main loop
    with open(varFile, 'r') as fo:
        inScope = False
        read = False if varToDelete else True
        toFalse = 'start'  # should just be a dummy value because variable read starts as True
        toTrue = 'start'
        for line in fo:
            bname = blockName(line)
            if bname:
                if isBlockStart(line):
                    if bname == scope.lower():
                        inScope = True
                    elif bname == 'enumerate_until_false':
                        enumerate = True
                    else:
                        if inScope:
                            if varToDelete:
                                if bname in varToDelete:
                                    read = True
                                    toTrue = bname
                            else:
                                if read:
                                    if bname in varToSkip:
                                        read = False
                                        toFalse = bname

                else:
                    if bname == scope.lower():
                        inScope = False
                    elif bname == 'enumerate_until_false':
                        for enumLine in toEnumerate:
                            removeProjectSetting(line, enum=True)
                        enumerate = False
                        toEnumerate.clear()
                    else:
                        if inScope:
                            if varToDelete:
                                if bname == toTrue:
                                    read = False
                            else:
                                if not read:
                                    if bname == toFalse:
                                        read = True
            else:
                if read:
                    if enumerate:
                        toEnumerate.append(line)
                    else:
                        if scope == 'Global':
                            removeGlobalSetting(line)
                        else:
                            removeProjectSetting(line)

    if 'feedback' in kwargs:
        if not kwargs['feedback']:
            return
    QMessageBox.information(None, "TUFLOW Clear Settings", "Successfully Cleared {0} Settings".format(scope))


def makeDir(path: str) -> bool:
    """
    Makes directory - will brute force make a directory

    :param path: str full path to dir
    :return: bool
    """

    # make sure separators are in
    # operating system format
    ospath = path.replace("/", os.sep)
    path_comp = ospath.split(os.sep)

    # work out where directories
    # need to be made
    i = 0
    j = len(path_comp) + 1
    testpath = os.sep.join(path_comp)
    while not os.path.exists(testpath):
        i += 1
        testpath = os.sep.join(path_comp[:j - i])
        if not testpath:
            return False

    # now work in reverse and create all
    # required directories
    for k in range(i - 1):
        i -= 1
        try:
            os.mkdir(os.sep.join(path_comp[:j - i]))
        except FileNotFoundError:
            return False
        except OSError:
            return False

    return True


def convert_datetime_to_float(dt_time):
    """
    !!! deprecated !!!! (and wrong now it seems) - use matplotlib.dates num2date and date2num
    How Matplotlib interprets dates: days since 0001-01-01 00:00:00 UTC + 1 day
    https://matplotlib.org/gallery/text_labels_and_annotations/date.html

    :param dt_time: datetime.datetime
    :return: float
    """

    t0 = datetime(1, 1, 1, 0, 0, 0)
    dt = dt_time - t0
    return (dt.total_seconds() / 60 / 60 / 24) + 1


def convert_float_to_datetime(time):
    """
    How Matplotlib interprets dates: days since 0001-01-01 00:00:00 UTC + 1 day
    https://matplotlib.org/gallery/text_labels_and_annotations/date.html

    :param dt_time: datetime.datetime
    :return: float
    """

    t0 = datetime(1, 1, 1, 0, 0, 0)
    return t0 + timedelta(days=time) - timedelta(days=1)


def getNetCDFLibrary():
    try:
        from netCDF4 import Dataset
        return "python", None
    except ImportError:
        try:
            from .netCDF4_ import Dataset_ as Dataset
            return 'python', None
        except ImportError:
            pass

    try:
        from qgis.core import QgsApplication
        netcdf_dll_path = os.path.dirname(os.path.join(os.path.dirname(os.path.dirname(QgsApplication.pkgDataPath()))))
        netcdf_dll_path = os.path.join(netcdf_dll_path, "bin", "netcdf.dll")
        if os.path.exists(netcdf_dll_path):
            return "c_netcdf.dll", netcdf_dll_path
    except ImportError:
        pass

    return None, None


DimReturn = Tuple[str, List[NcDim]]


def ncReadDimCDLL(ncdll: ctypes.cdll, ncid: ctypes.c_long, n: int) -> DimReturn:
    """
    Read all dimensions from netcdf file.

    ncdll - loaded netcdf dll
    ncid - open netcdf file
    n - number of dimensions
    """

    dims = []
    cstr_array = (ctypes.c_char * 256)()
    cint_p = ctypes.pointer(ctypes.c_int())
    for i in range(n):
        dim = NcDim()
        dims.append(dim)

        # gets dimension name and length
        err = ncdll.nc_inq_dim(ncid, ctypes.c_int(i), ctypes.byref(cstr_array), cint_p)
        if err:
            if ncid.value > 0:
                ncdll.nc_close(ncid)
            return "ERROR: error getting netcdf dimensions. Error: {0}".format(NC_Error.message(err)), dims

        dim.id = i
        dim.name = cstr_array.value.decode('utf-8')
        dim.len = cint_p.contents.value

    return "", dims


VarReturn = Tuple[str, List[NcVar]]
ncDimArg = List[NcDim]


def ncReadVarCDLL(ncdll: ctypes.cdll, ncid: ctypes.c_long, n: int, ncDims: ncDimArg) -> VarReturn:
    """
    Read all dimensions from netcdf file.

    ncdll - loaded netcdf dll
    ncid - open netcdf file
    n - number of variables
    ncDims - list of NcDim class
    """

    # get info on variables
    cstr_array = (ctypes.c_char * 256)()
    cint_p = ctypes.pointer(ctypes.c_int())
    ncVars = []
    for i in range(n):
        var = NcVar()
        ncVars.append(var)

        # id
        var.id = i

        # variable name
        err = ncdll.nc_inq_varname(ncid, ctypes.c_int(i), ctypes.byref(cstr_array))
        if err:
            if ncid.value > 0:
                ncdll.nc_close(ncid)
            return "ERROR: error getting netcdf variable names. Error: {0}".format(NC_Error.message(err)), ncVars
        var.name = cstr_array.value.decode('utf-8')

        # variable data type
        err = ncdll.nc_inq_vartype(ncid, ctypes.c_int(i), cint_p)
        if err:
            if ncid.value > 0:
                ncdll.nc_close(ncid)
            return "ERROR: error getting netcdf variable types. Error: {0}".format(NC_Error.message(err)), ncVars
        var.type = cint_p.contents.value

        # number of dimensions
        err = ncdll.nc_inq_varndims(ncid, ctypes.c_int(i), cint_p)
        if err:
            if ncid.value > 0:
                ncdll.nc_close(ncid)
            return "ERROR: error getting netcdf variable dimensions. Error: {0}".format(NC_Error.message(err)), ncVars
        var.nDims = cint_p.contents.value

        # dimension information
        cint_array = (ctypes.c_int * var.nDims)()
        err = ncdll.nc_inq_vardimid(ncid, ctypes.c_int(i), ctypes.byref(cint_array))
        if err:
            if ncid.value > 0:
                ncdll.nc_close(ncid)
            return "ERROR: error getting netcdf variable dimensions. Error: {0}".format(NC_Error.message(err)), ncVars
        var.dimIds = tuple(cint_array[x] for x in range(var.nDims))
        var.dimNames = tuple(ncDims[x].name for x in var.dimIds)
        var.dimLens = tuple(ncDims[x].len for x in var.dimIds)

    return "", ncVars


def lineIntersectsPoly(p1, p2, poly):
    """

    """

    pLine = QgsGeometry.fromPolyline([QgsPoint(p1.x(), p1.y()), QgsPoint(p2.x(), p2.y())])
    return pLine.intersects(poly.geometry())


def doLinesIntersect(a1, a2, b1, b2):
    """
    Does line a intersect line b

    """

    pLine1 = QgsGeometry.fromPolyline([QgsPoint(a1.x(), a1.y()), QgsPoint(a2.x(), a2.y())])
    pLine2 = QgsGeometry.fromPolyline([QgsPoint(b1.x(), b1.y()), QgsPoint(b2.x(), b2.y())])

    return pLine1.intersects(pLine2)


def intersectionPoint(a1, a2, b1, b2):
    """

    """

    pLine1 = QgsGeometry.fromPolyline([QgsPoint(a1.x(), a1.y()), QgsPoint(a2.x(), a2.y())])
    pLine2 = QgsGeometry.fromPolyline([QgsPoint(b1.x(), b1.y()), QgsPoint(b2.x(), b2.y())])

    return pLine1.intersection(pLine2).asPoint()


def generateRandomMatplotColours(n):
    import random
    colours = []
    while len(colours) < n:
        colour = [random.randint(0, 100) / 100 for x in range(3)]
        if colour != [1.0, 1.0, 1.0]:  # don't include white
            colours.append(colour)

    return colours


def colour_distance(rgb1, rgb2):
    """
    Distance between 2 colours
    """

    rm = 0.5 * (rgb1[0] + rgb2[0])
    d = sum((2 + rm, 4, 3 - rm) * (rgb1 - rgb2) ** 2) ** 0.5
    return d


def generateRandomMatplotColours2(nColours, type_='bright', tol=2, tol_reduction=0.1, count_reduction=50,
                                  neighbour_tol=10):
    """
    Creates a random colormap to be used together with matplotlib. Useful for segmentation tasks
    :param nlabels: Number of labels (size of colormap)
    :param type: 'bright' for strong colors, 'soft' for pastel colors
    """

    if type_ not in ('bright', 'soft'):
        print('Please choose "bright" or "soft" for type')
        return

    tol_og = tol
    # Generate color map for bright colors, based on hsv
    randRGBcolors = []
    n = 1
    if type_ == 'bright':
        count = 0
        while n <= nColours:
            randHSVcolor = [numpy.random.uniform(low=0.0, high=1),
                            numpy.random.uniform(low=0.2, high=1),
                            numpy.random.uniform(low=0.9, high=1)]

            # Convert HSV list to RGB
            rgb = numpy.array(colorsys.hsv_to_rgb(randHSVcolor[0], randHSVcolor[1], randHSVcolor[2]))
            if n > 1:
                add_colour = True
                for rgb2 in randRGBcolors[max(n - neighbour_tol, 0):]:
                    if colour_distance(rgb, rgb2) <= tol:
                        add_colour = False
                        break
                if add_colour:
                    randRGBcolors.append(rgb)
                    n += 1
                    tol = tol_og
                else:  # don't want infinite loop or for this to take too long, reduce tolerance at a certain point
                    count += 1
                    if count > count_reduction:
                        tol -= tol_reduction
                        count = 0
            else:
                randRGBcolors.append(rgb)
                n += 1

    # Generate soft pastel colors, by limiting the RGB spectrum
    if type_ == 'soft':
        low = 0.6
        high = 0.95
        rgb = [numpy.random.uniform(low=low, high=high),
               numpy.random.uniform(low=low, high=high),
               numpy.random.uniform(low=low, high=high)]
        if n > 1:
            for rgb2 in randRGBcolors[max(n - 10, 0):]:
                if colour_distance(rgb, rgb2) > tol:
                    randRGBcolors.append(rgb)
                    n += 1
        else:
            randRGBcolors.append(rgb)
            n += 1

    return randRGBcolors


def meshToPolygon(mesh: QgsMesh, face: int) -> QgsFeature:
    """
    converts a mesh to QgsFeature polygon

    """

    # convert mesh face into polygon
    w = 'POLYGON (('
    for i, v in enumerate(face):
        if i == 0:
            w = '{0}{1} {2}'.format(w, mesh.vertex(v).x(), mesh.vertex(v).y())
        else:
            w = '{0}, {1} {2}'.format(w, mesh.vertex(v).x(), mesh.vertex(v).y())
    w += '))'
    f = QgsFeature()
    f.setGeometry(QgsGeometry.fromWkt(w))

    return f


PointList = List[QgsPointXY]
FaceIndexList = List[int]


def getFaceIndexes3(si: QgsMeshSpatialIndex, dp: QgsMeshDataProvider, points: PointList,
                    mesh: QgsMesh) -> FaceIndexList:
    """

    """

    if not points:
        return []
    points = [QgsPointXY(x) for x in points]

    faceIndexes = []
    for p in points:
        indexes = si.nearestNeighbor(p, 1)
        if indexes:
            if len(indexes) == 1:
                if indexes[0] not in faceIndexes:
                    faceIndexes.append(indexes[0])
            else:
                for ind in indexes:
                    f = meshToPolygon(mesh, mesh.face(ind))
                    if f.geometry().contains(p):
                        if ind not in faceIndexes:
                            faceIndexes.append(ind)
                        break

    return faceIndexes


def getFaceIndex(p, si, mesh, p2=None, crs=None, iface=None):
    """

    """

    indexes = si.nearestNeighbor(p, 2)
    if indexes:
        if len(indexes) == 1:
            return indexes[0]
        else:
            for ind in indexes:
                f = meshToPolygon(mesh, mesh.face(ind))
                if p2 is None:
                    if f.geometry().contains(p):
                        return ind
                else:
                    p3 = calcMidPoint2(p, p2, iface)
                    if f.geometry().contains(p3):
                        return ind

    return None


def findMeshFaceIntersects(p1: QgsPointXY, p2: QgsPointXY, si: QgsMeshSpatialIndex, dp: QgsMeshDataProvider,
                           mesh: QgsMesh):
    """

    """

    rect = QgsRectangle(p1, p2)
    return si.intersects(rect)


def sameFace(v, v2, v_used, mesh):
    """Checks v -> v2 direction against v_used pairs. v is common vertex"""

    for vu in v_used:
        if v in vu:
            i = vu.index(v)
            v3 = vu[1 - i]  # the other vertex of the pair
            p = mesh.vertex(v)
            p2 = mesh.vertex(v2)
            p3 = mesh.vertex(v3)
            if abs(atan2(p2.y() - p.y(), p2.x() - p.x()) - atan2(p3.y() - p.y(), p3.x() - p.x())) <= 0.1:
                return True


def intersectAlreadyFound(v1, v2, v_used, v2_used, mesh):
    """
    v1 and v2 are vertexes with intersect,
    v_used are already used vertex pairs,
    v2_used are used vetexes

    If v1 and v2 are already a vertex pair, then intercept already found.
    Quadtree can have 2 faces connected to a single adjacent face
    """

    if sorted([v1, v2]) in v_used:
        return True

    if v1 not in v2_used and v2 not in v2_used:
        return False

    if v1 in v2_used:
        if sameFace(v1, v2, v_used, mesh):
            return True

    if v2 in v2_used:
        return sameFace(v2, v1, v_used, mesh)


FaceList = List[int]


def findMeshSideIntersects(p1: QgsPointXY, p2: QgsPointXY, faces: FaceList, mesh: QgsMesh, allFaces) -> PointList:
    """

    """

    v_used = []  # vertex pairs
    v2_used = []  # individual vertex
    m_used = []
    p_intersects = [p1]
    for f in faces:
        vs = mesh.face(f)
        for i, v in enumerate(vs):
            if i == 0:
                f1 = v
            else:
                p3 = mesh.vertex(vs[i - 1])
                p4 = mesh.vertex(v)
                b = doLinesIntersect(p1, p2, p3, p4)
                if b:
                    # if sorted([vs[i-1], v]) not in v_used:
                    if not intersectAlreadyFound(vs[i - 1], v, v_used, v2_used, mesh):
                        newPoint = intersectionPoint(p1, p2, p3, p4)
                        p_intersects.append(newPoint)
                        v_used.append(sorted([vs[i - 1], v]))
                        if vs[i - 1] not in v2_used:
                            v2_used.append(vs[i - 1])
                        if v not in v2_used:
                            v2_used.append(v)
                    if f not in m_used and f not in allFaces:
                        m_used.append(f)
                if i + 1 == len(vs):
                    p3 = mesh.vertex(v)
                    p4 = mesh.vertex(f1)
                    b = doLinesIntersect(p1, p2, p3, p4)
                    if b:
                        # if sorted([f1, v]) not in v_used:
                        if not intersectAlreadyFound(f1, v, v_used, v2_used, mesh):
                            newPoint = intersectionPoint(p1, p2, p3, p4)
                            p_intersects.append(newPoint)
                            v_used.append(sorted([f1, v]))
                            if f1 not in v2_used:
                                v2_used.append(f1)
                            if v not in v2_used:
                                v2_used.append(v)
                        if f not in m_used and f not in allFaces:
                            m_used.append(f)

    return p_intersects, m_used


def findMeshIntersects(si: QgsMeshSpatialIndex, dp: QgsMeshDataProvider, mesh: QgsMesh,
                       feat: QgsFeature, crs, project: QgsProject = None, iface=None, debug=False):
    """

    """

    # geometry
    if feat.geometry().wkbType() == QgsWkbTypes.LineString:
        geom = feat.geometry().asPolyline()
    elif feat.geometry().wkbType() == QgsWkbTypes.MultiLineString:
        mGeom = feat.geometry().asMultiPolyline()
        geom = []
        for g in mGeom:
            for p in g:
                geom.append(p)
    else:
        return

    # get mesh intersects and face (side) intersects
    points = []
    chainages = []
    allFaces = []
    for i, p in enumerate(geom):
        if i > 0:
            faces = findMeshFaceIntersects(geom[i - 1], p, si, dp, mesh)
            inters, minter = findMeshSideIntersects(geom[i - 1], p, faces, mesh, [])
            if inters:
                inters.append(geom[i])
                pOrdered, mOrdered = orderPointsByDistanceFromFirst(inters, minter, si, mesh, i, crs)
                points += pOrdered
                allFaces += mOrdered
        if i + 1 == len(geom):
            if p not in points:
                points.append(p)

    # calculate chainage
    chainage = 0
    chainages.append(chainage)
    for i, p in enumerate(points):
        if i > 0:
            if iface is not None:
                chainage += calculateLength2(p, points[i - 1], crs, iface.mapCanvas().mapUnits())
            else:
                chainage += calculateLength2(p, points[i - 1], crs, QgsUnitTypes.DistanceMeters)
            chainages.append(chainage)

    # switch on/off to get check mesh faces and intercepts
    if debug:
        # debug - write a temporary polygon layer and import into QGIS to check
        crs = project.crs()
        uri = "polygon?crs={0}".format(crs.authid().lower())
        lyr = QgsVectorLayer(uri, "check_mesh_intercepts", "memory")
        dp = lyr.dataProvider()
        dp.addAttributes([QgsField('Id', QVariant.Int)])
        lyr.updateFields()
        feats = []
        for i, f in enumerate(allFaces):
            feat = meshToPolygon(mesh, mesh.face(f))
            feat.setAttributes([i])
            feats.append(feat)
        dp.addFeatures(feats)
        lyr.updateExtents()
        project.addMapLayer(lyr)

        # debug - write a temporary point layer and import into QGIS to check
        crs = project.crs()
        uri = "point?crs={0}".format(crs.authid().lower())
        lyr = QgsVectorLayer(uri, "check_face_intercepts", "memory")
        dp = lyr.dataProvider()
        dp.addAttributes([QgsField('Ch', QVariant.Double)])
        lyr.updateFields()
        feats = []
        for i, point in enumerate(points):
            feat = QgsFeature()
            feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(point)))
            feat.setAttributes([chainages[i]])
            feats.append(feat)
        dp.addFeatures(feats)
        lyr.updateExtents()
        project.addMapLayer(lyr)

    return points, chainages, allFaces


def calculateLength2(p1, p2, crs=None, units=None):
    """

    """

    if crs is None:
        crs = QgsProject.instance().crs()

    da = QgsDistanceArea()
    da.setSourceCrs(crs, QgsCoordinateTransformContext())
    return da.convertLengthMeasurement(da.measureLine(p1, p2), units)


def calcMidPoint(p1, p2, crs, iface):
    """
    Calculates a point halfway between p1 and p2
    """

    if iface is not None:
        h = calculateLength2(p1, p2, crs, iface.mapCanvas().mapUnits()) / 2.
    else:
        h = calculateLength2(p1, p2, crs, QgsUnitTypes.DistanceMeters) / 2.
    a = atan2((p2.x() - p1.x()), (p2.y() - p1.y()))
    x = p1.x() + sin(a) * h
    y = p1.y() + cos(a) * h
    return QgsPointXY(x, y)


def calcMidPoint2(p1, p2, crs=None):
    """
    Calculates a point halfway between p1 and p2
    """

    return QgsGeometryUtils.interpolatePointOnLine(p1.x(), p1.y(), p2.x(), p2.y(), 0.5)


def orderPointsByDistanceFromFirst(points, faces, si, mesh, ind, crs):
    """

    """

    pointsOrdered = []
    facesOrdered = []
    pointsCopied = [QgsPoint(x.x(), x.y()) for x in points]
    p = QgsPoint(points[0].x(), points[0].y())
    # f = si.nearestNeighbor(QgsPointXY(p), 1)[0]
    f = getFaceIndex(QgsPointXY(p), si, mesh)
    if f is not None:
        facesOrdered.append(f)
    counter = 0
    while len(pointsOrdered) < len(points):
        pointsOrdered.append(QgsPointXY(p))
        pointsCopied.remove(p)
        geom = QgsLineString(pointsCopied)
        p, i = QgsGeometryUtils.closestVertex(geom, p)
        # fs = si.nearestNeighbor(QgsPointXY(p), 2)
        f = getFaceIndex(QgsPointXY(p), si, mesh, pointsOrdered[counter], crs)
        # for f in fs:
        if f is not None:
            if f not in facesOrdered and len(facesOrdered) < len(faces):
                facesOrdered.append(f)
        counter += 1

    if ind > 1:
        pointsOrdered = pointsOrdered[1:]
    # facesOrdered = facesOrdered[1:]

    return pointsOrdered, facesOrdered


def writeTempPoints(points, project, crs=None, label=(), field_id='', field_type=None):
    """

    """

    if crs is None:
        crs = project.crs()
    uri = "point?crs={0}".format(crs.authid().lower())
    lyr = QgsVectorLayer(uri, "check_face_intercepts", "memory")
    dp = lyr.dataProvider()
    if label:
        dp.addAttributes([QgsField(field_id, field_type)])
    else:
        dp.addAttributes([QgsField('ID', QVariant.Int)])

    lyr.updateFields()
    feats = []
    for i, point in enumerate(points):
        feat = QgsFeature()
        feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(point)))
        if label:
            feat.setAttributes([label[i]])
        else:
            feat.setAttributes([i])
        feats.append(feat)
    dp.addFeatures(feats)
    lyr.updateExtents()
    project.addMapLayer(lyr)


def writeTempPolys(polys, project, crs=None, label=(), field_id='', field_type=None):
    """

    """

    if crs is None:
        crs = project.crs()
    uri = "polygon?crs={0}".format(crs.authid().lower())
    lyr = QgsVectorLayer(uri, "check_mesh_intercepts", "memory")
    dp = lyr.dataProvider()
    if label:
        dp.addAttributes([QgsField(field_id, field_type)])
    else:
        dp.addAttributes([QgsField('ID', QVariant.Int)])

    lyr.updateFields()
    feats = []
    for i, poly in enumerate(polys):
        if label:
            poly.setAttributes([label[i]])
        else:
            poly.setAttributes([i])
        feats.append(poly)
    dp.addFeatures(feats)
    lyr.updateExtents()
    project.addMapLayer(lyr)


def getPolyCollectionData(pc, axis):
    """
    Return data for matplotlib PolyCollection:

    axis options: 'x', 'y', 'scalar'
    """

    assert axis.lower() in ['x', 'y', 'scalar'], "'axis' variable not one of 'x', 'y', or 'scalar'"

    if axis.lower() == 'x':
        a = numpy.array([x.vertices[:, 0] for x in pc.get_paths()])
    elif axis.lower() == 'y':
        a = numpy.array([x.vertices[:, 1] for x in pc.get_paths()])
    else:
        a = pc.get_array()

    return a


def getQuiverData(qv, axis):
    """
    Return data for matplotlib Quiver

    axis options: 'x', 'y', 'scalar'
    """

    assert axis.lower() in ['x', 'y', 'scalar'], "'axis' variable not one of 'x', 'y', or 'scalar'"

    if axis.lower() == 'x':
        a = qv.X
    elif axis.lower() == 'y':
        a = qv.Y
    else:
        a = qv.U  # V component is always zero

    return a


def getPolyCollectionExtents(pc, axis, empty_return=(999999, -999999)):
    """
    Return min / max extents for matplotlib PolyCollection:

    axis options: 'x', 'y', 'scalar'
    empty_return: dictates what is returned if array is empty
    """

    assert axis.lower() in ['x', 'y', 'scalar'], "'axis' variable not one of 'x', 'y', or 'scalar'"

    if axis.lower() == 'x':
        a = numpy.array([x.vertices[:, 0] for x in pc.get_paths()])
    elif axis.lower() == 'y':
        a = numpy.array([x.vertices[:, 1] for x in pc.get_paths()])
    else:
        a = pc.get_array()

    if a.size == 0:
        return empty_return
    else:
        return numpy.nanmin(a), numpy.nanmax(a)


def polyCollectionPathIndexFromXY(pc, x, y):
    """
    Return path index from x, y values
    """

    path = [p for p in pc.get_paths()
            if numpy.amin(p.vertices[:, 1]) < y <= numpy.amax(p.vertices[:, 1])
            and numpy.amin(p.vertices[:, 0]) < x <= numpy.amax(p.vertices[:, 0])]

    if len(path) != 1:
        return None
    else:
        return pc.get_paths().index(path[0])


def getQuiverExtents(qv, axis, empty_return=(999999, -999999)):
    """
    Return min/max extents for matplotlib Quiver

    axis options: 'x', 'y', 'scalar'
    empty_return: dictates what is returned if Quiver is empty
    """

    assert axis.lower() in ['x', 'y', 'scalar'], "'axis' variable not one of 'x', 'y', or 'scalar'"

    if axis.lower() == 'x':
        a = qv.X
    elif axis.lower() == 'y':
        a = qv.Y
    else:
        a = qv.U  # V component is always zero

    if a.size == 0:
        return empty_return
    else:
        return numpy.nanmin(a), numpy.nanmax(a)


def convertTimeToDate(refTime, t, unit):
    """
    Convert time to date
    """

    assert unit in ['s', 'h'], "'unit' variable not one of 's', or 'h'"

    if unit == 's':
        date = refTime + timedelta(seconds=t)
    else:
        try:
            date = refTime + timedelta(hours=t)
        except OverflowError:
            date = refTime + timedelta(seconds=t)

    return roundSeconds(date, 2)


def findPlotLayers(geom=''):
    """

    """

    lyrs = []
    if not geom:
        geom = 'PLR'
    s = r'[_\s]PLOT[_\s][{0}]'.format(geom)
    for id, lyr in QgsProject.instance().mapLayers().items():
        if re.findall(s, lyr.name(), flags=re.IGNORECASE):
            lyrs.append(lyr)

    return lyrs


def findTableLayers():
    """

    """

    lyrs = []
    for id, lyr in QgsProject.instance().mapLayers().items():
        if is1dTable(lyr):
            lyrs.append(lyr)

    return lyrs


def findIntersectFeat(feat, lyr):
    """

    """

    for f in lyr.getFeatures():
        if feat.geometry().intersects(f.geometry()):
            return f

    return None


def isSame_float(a, b, prec=None):
    """

    """

    if prec is None:
        prec = abs(sys.float_info.epsilon * max(a, b) * 2.)

    return abs(a - b) <= prec


def isSame_time(a, b, prec=None):
    """

    """

    if prec is None:
        prec = abs(sys.float_info.epsilon * max(a, b) * 2.)

    return abs((a - b).total_seconds()) <= prec


def qdt2dt(dt):
    """
    Converts QDateTime to datetime
    """

    return datetime(dt.date().year(), dt.date().month(), dt.date().day(), dt.time().hour(),
                    dt.time().minute(), dt.time().second(), int(dt.time().msec() * 1000))


def dt2qdt(dt, timeSpec):
    """Converts datetime to QDateTime: assumes timespec = 1"""

    return QDateTime(QDate(dt.year, dt.month, dt.day),
                     QTime(dt.hour, dt.minute, dt.second, int(dt.microsecond / 1000)),
                     Qt.TimeSpec(timeSpec))


def datetime2timespec(dt, timespec1, timespec2):
    """converts datetime object from timespec1 to timespec2"""

    return qdt2dt(dt2qdt(dt, timespec1).toTimeSpec(timespec2))


def regex_dict_val(d: dict, key):
    """return dictionary value when dict keys use re"""

    a = {key: val for k, val in d.items() if re.findall(k, key, flags=re.IGNORECASE)}
    return a[key] if key in a else None


def qgsxml_colorramp_prop(node, key):
    try:
        return [x for x in node.findall('prop') if x.attrib['k'] == key][0].attrib['v']
    except IndexError:
        return None


def read_colour_ramp_qgsxml(xml_node, break_points, reds, greens, blues, alphas):
    """parse breakpoints and colours out of qgis xml file"""

    c1 = qgsxml_colorramp_prop(xml_node, 'color1')
    if c1 is None: return False
    try:
        r, g, b, a = c1.split(',')
        break_points.append(0.)
        reds.append(float(r))
        greens.append(float(g))
        blues.append(float(b))
        alphas.append(float(a))
    except ValueError:
        return False

    cm = qgsxml_colorramp_prop(xml_node, 'stops')
    if cm is None: return False
    stops = cm.split(':')
    for s in stops:
        try:
            br, rgba = s.split(';')
            break_points.append(float(br))
            r, g, b, a = rgba.split(',')
            reds.append(float(r))
            greens.append(float(g))
            blues.append(float(b))
            alphas.append(float(a))
        except ValueError:
            return False

    c2 = qgsxml_colorramp_prop(xml_node, 'color2')
    if c2 is None: return False
    try:
        r, g, b, a = c2.split(',')
        break_points.append(1.)
        reds.append(float(r))
        greens.append(float(g))
        blues.append(float(b))
        alphas.append(float(a))
    except ValueError:
        return False

    return True


def generate_mpl_colourramp(break_points, reds, greens, blues, alphas):
    """Convert data into matplotlib linear colour ramp"""

    cdict = {'red': [], 'green': [], 'blue': []}
    for i, br in enumerate(break_points):
        r = reds[i] / 255.
        cdict['red'].append((br, r, r))
        g = greens[i] / 255.
        cdict['green'].append((br, g, g))
        b = blues[i] / 255.
        cdict['blue'].append((br, b, b))

    return cdict


def qgsxml_as_mpl_cdict(fpath):
    """Read QGIS colour ramp style xml and convert to matplotlib colour ramp dict"""

    mpl_cdicts = {}
    tree = ET.parse(fpath)
    root = tree.getroot()
    if root.findall("colorramps"):
        for cr in root.findall("colorramps")[0].findall("colorramp"):
            name = cr.attrib['name']
            break_points, reds, greens, blues, alphas = [], [], [], [], []
            success = read_colour_ramp_qgsxml(cr, break_points, reds, greens, blues, alphas)
            if not success: continue

            mpl_cr = generate_mpl_colourramp(break_points, reds, greens, blues, alphas)
            mpl_cdicts[name] = mpl_cr

    return mpl_cdicts


def layoutHeight(layout):
    total_h = 0
    for i in range(layout.count()):
        item = layout.itemAt(i)
        if isinstance(item, QBoxLayout):
            h = layoutHeight(item)
        elif isinstance(item, QSpacerItem):
            h = item.sizeHint().height()
        else:
            h = item.widget().sizeHint().height()
        if isinstance(layout, QHBoxLayout):
            total_h = max(total_h, h)
        else:
            total_h += h
    return total_h


def reload_data(layer):
    lyr_type = None
    if layer is not None:
        if isinstance(layer, QgsVectorLayer):
            layer.reload()
            layer.triggerRepaint()
        elif (isinstance(layer, QgsMeshLayer) and Qgis.QGIS_VERSION_INT >= 32800) or isinstance(layer, QgsRasterLayer):

            # check if the result has been temporarily copied - recopy if needed
            if plugins['tuflow'].resultsPlottingDockOpened:
                tuview = plugins['tuflow'].resultsPlottingDock
                if layer in tuview.tuResults.tuResults2D.copied_results:
                    lyr_type = 'mesh'
                    tmp_res = tuview.tuResults.tuResults2D.copied_results[layer]
                elif layer in tuview.tuResults.tuResultsNcGrid.copied_results:
                    lyr_type = 'nc_grid'
                    tmp_res = tuview.tuResults.tuResultsNcGrid.copied_results[layer]
                if lyr_type:
                    if hasattr(tuview, 'timer') and tuview.timer is not None:
                        tuview.timer = None
                        tmp_res.clean()
                        if tmp_res.update_method() == 'RETARGET':
                            layer.reload()
                            if lyr_type == 'nc_grid':
                                for layer_ in QgsProject.instance().mapLayers().values():
                                    if layer_ in tuview.tuResults.tuResultsNcGrid.copied_results:
                                        tmp_res_ = tuview.tuResults.tuResultsNcGrid.copied_results[layer_]
                                    else:
                                        continue
                                    if tmp_res_ == tmp_res:
                                        if layer_ != layer:
                                            layer_.reload()
                                        tuview.tuResults.tuResultsNcGrid.layerReloaded(layer_)
                            return
                    else:
                        tuview.timer = QTimer()
                        tuview.timer.setSingleShot(True)
                        tuview.timer.timeout.connect(lambda: reload_data(layer))
                    tmp_res.update(tuview)
                    if tmp_res.update_method() == 'RETARGET' and Qgis.QGIS_VERSION_INT >= 32000:
                        if lyr_type == 'mesh':
                            layer.setDataSource(str(tmp_res.tmp_file), layer.name(), 'mdal')
                        elif lyr_type == 'nc_grid':
                            for layer_ in QgsProject.instance().mapLayers().values():
                                if layer_ in tuview.tuResults.tuResultsNcGrid.copied_results:
                                    tmp_res_ = tuview.tuResults.tuResultsNcGrid.copied_results[layer_]
                                else:
                                    continue
                                if tmp_res_ == tmp_res:
                                    layer_.setDataSource(str(tmp_res.tmp_file), layer_.name(), 'gdal')

            layer.reload()
            if lyr_type == 'nc_grid':
                for layer_ in QgsProject.instance().mapLayers().values():
                    if layer_ in tuview.tuResults.tuResultsNcGrid.copied_results:
                        tmp_res_ = tuview.tuResults.tuResultsNcGrid.copied_results[layer_]
                    else:
                        continue
                    if tmp_res_ == tmp_res:
                        if layer_ != layer:
                            layer_.reload()
                        tuview.tuResults.tuResultsNcGrid.layerReloaded(layer_)
                tuview.tuResults.tuResultsNcGrid.layerReloaded(None)  # this triggers the timer to start

def tuflowqgis_apply_gpkg_layername(iface):
    for layer_name, layer in QgsProject.instance().mapLayers().items():
        if layer.type() == QgsMapLayer.VectorLayer:
            layername = layer.name()
            dp = layer.dataProvider()
            ds = dp.dataSourceUri()
            pattern = re.escape(r'.gpkg|layername=')
            if re.findall(pattern, ds, re.IGNORECASE):
                tablename = re.split(pattern, ds, flags=re.IGNORECASE)[1].split('|')[0]

                # rename layer in layers panel
                legint = QgsProject.instance().layerTreeRoot()
                # grab all nodes that are QgsMapLayers - get to node bed rock i.e. not a group
                nodes = []
                for child in legint.children():
                    children = [child]
                    while children:
                        nd = children[0]
                        if nd.children():
                            children += nd.children()
                        else:
                            nodes.append(nd)
                        children = children[1:]
                for nd in nodes:
                    if nd.name() == layername:
                        nd.setName(tablename)
                        break
        elif layer.type() == QgsMapLayer.RasterLayer:
            lyrname = None
            ds = layer.dataProvider().dataSourceUri()
            if 'GPKG:' in ds:
                _, lyrname = ds.rsplit(':', 1)
            elif os.path.splitext(ds)[1].lower() == '.gpkg':
                from .compatibility_routines import GPKG
                gpkg = GPKG(ds)
                lyrs = gpkg.raster_layers()
                if lyrs:
                    lyrname = lyrs[0]
            if lyrname:
                nd = QgsProject.instance().layerTreeRoot().findLayer(layer.id())
                nd.setName(lyrname)



def qcolor_to_mplcolor(color):
    """
    qcolor name with alpha is in form: #AARRGGBB
    mplcolor expects #RRGGBBAA
    """

    if len(color) == 9:
        return color[0] + color[3:] + color[1:3]
    else:
        return color


def mplcolor_to_qcolor(color):
    """
    qcolor name with alpha is in form: #AARRGGBB
    mplcolor expects #RRGGBBAA
    """

    if len(color) == 9:
        return color[0] + color[-2:] + color[1:-2]
    else:
        return color


def is_database(layer):
    ds = layer.dataProvider().dataSourceUri()
    if re.findall(re.escape(r'.gpkg|layername='), ds, flags=re.IGNORECASE):
        return True

    return False


def get_table_names(db):
    if Path(db).exists():
        conn = sqlite3.connect(db)
        cur = conn.cursor()
        try:
            cur.execute('SELECT table_name FROM gpkg_contents;')
            tables = [x[0] for x in cur.fetchall()]
            cur.close()
            return tables
        except:
            cur.close()
            return []

    return []


def get_x(origin, angle, dist):
    """Calculates x coordinate location given an origin, angle, and distance."""

    cosang = cos(angle)
    dx = dist * cosang

    return origin + dx


def get_y(origin, angle, dist):
    """ Calculates y coordinate location given an origin, angle, and distance."""

    sinang = sin(angle)
    dy = dist * sinang

    return origin + dy


def calculate_angle(geom):
    """calculate angle of line at centroid"""

    if geom.wkbType() in [QgsWkbTypes.LineString, QgsWkbTypes.LineStringZ, QgsWkbTypes.LineStringM,
                          QgsWkbTypes.LineStringZM, QgsWkbTypes.LineString25D]:
        line = geom.asPolyline()
    elif geom.wkbType() in [QgsWkbTypes.MultiLineString, QgsWkbTypes.MultiLineStringZ, QgsWkbTypes.MultiLineStringM,
                            QgsWkbTypes.MultiLineStringZM, QgsWkbTypes.MultiLineString25D]:
        line = sum(geom.asMultiPolyline(), [])
    else:
        return None

    total_length = geom.length()
    mid_length = total_length / 2.
    p1, p2 = None, None
    for i, p in enumerate(line):
        if i == 0:
            continue
        if geom.distanceToVertex(i) > mid_length:
            p1 = line[i - 1]
            p2 = line[i]
            break

    if p1 is None or p2 is None:
        return None

    return atan2((p2.y() - p1.y()), (p2.x() - p1.x()))


def getRightAngleLine(geom, length):
    """
    Creates a line perpendicular to a given input line. The input line is only used to define
    the new line's angle. The centroid is used to define the new line's location. The new line will contain
    three points - start, end, centroid.
    """

    ang = calculate_angle(geom)
    if ang is None:
        return None
    p1 = QgsPointXY(get_x(geom.centroid().asPoint().x(), ang + pi / 2., length / 2.),
                    get_y(geom.centroid().asPoint().y(), ang + pi / 2., length / 2.))
    p2 = QgsPointXY(get_x(geom.centroid().asPoint().x(), ang - pi / 2., length / 2.),
                    get_y(geom.centroid().asPoint().y(), ang - pi / 2., length / 2.))

    return QgsGeometry.fromPolylineXY([p1, p2])


def copyStyle(lyr1, lyr2):
    doc = QDomDocument("qgis")
    errmsg = lyr1.exportNamedStyle(doc)
    if errmsg:
        return errmsg

    err, errmsg = lyr2.importNamedStyle(doc)
    if err:
        return errmsg

    return ''


def mpl_version_int():
    import matplotlib as mpl
    v_ = [int(x) for x in mpl.__version__.split('.')]
    f = 10000
    version = 0
    for v in v_:
        version += int(v * f)
        f /= 10

    return version


def labels_about_to_break(ax, labels_original):
    artists, labels = ax.get_legend_handles_labels()
    return sorted(artists, key=lambda x: x.get_label()) != artists


def labels_already_broken(labels_original):
    return sorted(labels_original) != labels_original


class XMDF_Header_Info:

    def __init__(self, header_text_dump):
        self._header_text_dump = header_text_dump
        self._vector_dataset_count = 0
        self._scalar_dataset_count = 0
        self._res_types = []
        self._loaded = False

        si, vi = 0, 0
        scalar, vector = False, False
        res_type = None
        line_count = 0
        line_index = 0
        times = []
        for line in header_text_dump.split('\n'):
            if vector and self._vector_dataset_count > 0 and vi == self._vector_dataset_count:
                vector = False
            if scalar and self._scalar_dataset_count > 0 and si == self._scalar_dataset_count:
                scalar = False

            if 'Vector Datasets' in line:
                vector = True
                scalar = False
            elif 'Scalar Datasets' in line:
                scalar = True
                vector = False

            elif 'Number Datasets:' in line:
                n = re.findall(r'\d+', line)
                if n:
                    if vector:
                        self._vector_dataset_count = int(n[0])
                    elif scalar:
                        self._scalar_dataset_count = int(n[0])
            elif re.findall(r'\w+/\w+/\w+(\s\w+)?', line):
                if scalar:
                    si += 1
                elif vector:
                    vi += 1
                else:
                    continue
                folder, name = line.split('/')[-2:]
                if 'Vector' in name:
                    name = re.sub(r'\s*vector\s+', '', name, flags=re.IGNORECASE)
                res_type = XMDF_Res_Type(folder, name, vector, si, vi)
                self._res_types.append(res_type)

            elif 'Num Times' in line:
                line_count = int(re.findall(r'\d+', line)[0])

            elif line_count != 0 and res_type is not None and line_index != line_count:
                line_index += 1
                try:
                    time = float(line)
                except ValueError:
                    return
                times.append(time)
                if line_index == line_count:
                    res_type.add_times(times)
                    res_type = None
                    line_count = 0
                    line_index = 0
                    times = []

        self._loaded = (bool(self._vector_dataset_count) or bool(self._scalar_dataset_count)) and bool(self._res_types)

    def __contains__(self, item):
        if isinstance(item, str):
            return item.lower() in [x.name().lower() for x in self._res_types]
        elif isinstance(item, XMDF_Res_Type):
            return item.name().lower() in [x.name().lower() for x in self._res_types]
        else:
            return False

    def __getitem__(self, item):
        if isinstance(item, tuple) and len(item) == 2:
            item1, item2 = item
            if isinstance(item1, str) and isinstance(item2, str):
                if item2 == 'Max':
                    a = [x for x in self._res_types if
                         x.name() == item1 and x.folder() in ['Maximums', 'Final', 'Times']]
                    if a:
                        return a[0].key(), str(a[0].times()[0])
                elif item2 == 'Min':
                    a = [x for x in self._res_types if x.name() == item1 and x.folder() == 'Minimums']
                    if a:
                        return a[0].key(), str(a[0].times()[0])
                else:
                    a = [x for x in self._res_types if x.name() == item1]
                    if a:
                        for t in a[0].times():
                            if abs(t - float(item2)) < 0.001:
                                return a[0].key(), t
                            else:
                                return a[0].key(), None

        return None, None

    def result_types(self):
        return list(set([x.name() for x in self._res_types[:]]))

    def loaded(self):
        return self._loaded

    def times(self, res_type=None):
        if not res_type:
            return sorted(list(set(sum([x.times() for x in self._res_types], []))))
        else:
            return sorted(list(set(sum([x.times() for x in self._res_types if x.name() == res_type], []))))

    def has_max(self, res_type=None):
        if not res_type:
            return bool([x for x in self._res_types if
                         x.folder() == 'Maximums' or x.folder() == 'Final' or x.folder() == 'Times'])
        else:
            return bool([x for x in self._res_types if x.name() == res_type and (
                    x.folder() == 'Maximums' or x.folder() == 'Final' or x.folder() == 'Times')])

    def has_min(self, res_type=None):
        if not res_type:
            return bool([x for x in self._res_types if x.folder() == 'Minimums'])
        else:
            return bool([x for x in self._res_types if x.name() == res_type and x.folder() == 'Minimums'])


class XMDF_Res_Type:

    def __init__(self, folder, name, is_vector, scalar_count, vector_count):
        self._is_vector = is_vector
        self._key = 'v{0}'.format(vector_count) if is_vector else 's{0}'.format(scalar_count)
        self._folder = folder
        self._name = name
        self._times = []

    def add_times(self, times):
        for time in times:
            if time not in self._times:
                self._times.append(time)
        self._times = sorted(self._times)

    def times(self):
        return self._times[:]

    def name(self):
        return self._name

    def folder(self):
        return self._folder

    def key(self):
        return self._key


def re_ify(text, wildcards):
    # text = re.escape(text)
    for wc in wildcards:
        text = re.sub(wc, '*', text, flags=re.IGNORECASE)
    if re.findall(r'\*\*(?![\\/])', text):
        text = re.sub(re.escape(r'**'), '*', text)

    text = text.replace('*', '.*')

    return text


def getOutputDirs_old(path):
    try:
        from .convert_tuflow_model_gis_format.conv_tf_gis_format.helpers.file import globify
    except ImportError:
        from compatibility_routines import globify

    output_paths = []

    outputFolder1D, outputFolder2D = getOutputFolderFromTCF(path)

    if not outputFolder2D:
        return []

    search_globs = [
        '{0}{1}**{1}{2}.xmdf'.format(outputFolder2D[0], os.sep, os.path.splitext(os.path.basename(path))[0]),
        '{0}{1}**{1}{2}.tpc'.format(outputFolder2D[0], os.sep, os.path.splitext(os.path.basename(path))[0])]

    wildcards = [r'(~[es]\d?~)']
    re_name = re_ify(os.path.splitext(os.path.basename(path))[0], wildcards)
    re_name = r'{0}((_[A-^`-z0-9%&]+)(\+[A-^`-z0-9%&]+)*)?'.format(re_name)

    for f in search_globs:
        pattern = globify(f, wildcards)
        pattern = '{0}*{1}'.format(*os.path.splitext(pattern))
        for file in glob.glob(pattern, recursive=True):
            re_name_ = r'{0}\{1}'.format(re_name, os.path.splitext(file)[1])
            if re.findall(re_name_, os.path.basename(file)):
                output_paths.append(file)

    return output_paths


def getOutputDirs(path, settings=None):
    from .convert_tuflow_model_gis_format.conv_tf_gis_format.helpers.control_file import get_commands
    from .convert_tuflow_model_gis_format.conv_tf_gis_format.helpers.settings import ConvertSettings
    from .convert_tuflow_model_gis_format.conv_tf_gis_format.helpers.file import globify, TuflowPath

    output_paths = []
    if settings is None:
        path = TuflowPath(path)
        settings = ConvertSettings(*['-tcf', path, '-rf', path.parent])
        settings.read_tcf()
    else:
        settings = settings.copy_settings(path, settings.output_folder)

    if isinstance(path, str):
        path = TuflowPath(path)

    for command in get_commands(path, settings):
        if command.is_control_file():
            if (command.is_value_a_file() and command.value.suffix.lower() == '.ecf') or str(
                    command.value).lower() == 'AUTO':
                continue

            pattern = globify(command.value, settings.wildcards)
            for cf in settings.control_file.parent.glob(pattern):
                cf = cf.resolve()
                output_paths.extend(getOutputDirs(cf, settings))
                if len(output_paths) != len(set(output_paths)):
                    length = len(output_paths)
                    for i, op in enumerate(output_paths[::-1]):
                        j = length - i - 1
                        if op in output_paths[:j]:
                            output_paths.pop(j)

        if command.command == 'OUTPUT FOLDER':
            if command.in_1d_domain_block():
                continue

            wildcards = [r'(~[es]\d?~)']
            re_name = re_ify(settings.tcf.with_suffix('').name, wildcards)
            re_name = r'{0}((_[A-^`-z0-9%&\-]+)(\+[A-^`-z0-9%&\-]+)*)?'.format(re_name)

            parent = settings.control_file.parent
            search_globs = [TuflowPath(command.value) / '**' / settings.tcf.with_suffix('.xmdf').name,
                            TuflowPath(command.value) / '**' / settings.tcf.with_suffix('.tpc').name,
                            TuflowPath(command.value) / '**' / settings.tcf.with_suffix('.gpkg').name]
            for i, sg in enumerate(search_globs[:]):
                if sg.root:
                    if sg.drive != settings.control_file.drive:
                        parent = sg.parent.parent
                        search_globs[i] = os.path.relpath(sg, parent)
                    else:
                        search_globs[i] = os.path.relpath(sg, settings.control_file.parent)
            for glob in search_globs:
                pattern = globify(glob, wildcards)
                if str(Path(pattern).with_suffix(''))[-1] != '*':
                    if Path(pattern).suffix == '.gpkg':
                        pattern = '{0}*_swmm_ts{1}'.format(Path(pattern).with_suffix(''), Path(pattern).suffix)
                        re_name_ = r'{0}_swmm_ts\{1}'.format(re_name, Path(pattern).suffix)
                    else:
                        pattern = '{0}*{1}'.format(Path(pattern).with_suffix(''), Path(pattern).suffix)
                        re_name_ = r'{0}\{1}'.format(re_name, Path(pattern).suffix)
                else:
                    re_name_ = re_name
                for file in parent.glob(pattern):
                    # re_name_ = r'{0}\{1}'.format(re_name, file.suffix)
                    if re.findall(re_name_, file.name) and file not in output_paths:
                        output_paths.append(file)

            for oz in settings.output_zones:
                tcf = TuflowPath('{0}_{{{1}}}'.format(settings.tcf.stem, oz))
                parent = settings.control_file.parent
                search_globs = [TuflowPath(command.value) / '**' / tcf.with_suffix('.xmdf').name,
                                TuflowPath(command.value) / '**' / tcf.with_suffix('.tpc').name]
                for i, sg in enumerate(search_globs[:]):
                    if sg.root:
                        if sg.root != settings.control_file.root:
                            parent = sg.parent.parent
                            search_globs[i] = os.path.relpath(sg, parent)
                        else:
                            search_globs[i] = os.path.relpath(sg, settings.control_file.parent)
                for glob in search_globs:
                    pattern = globify(glob, wildcards)
                    pattern = '{0}*{1}'.format(Path(pattern).with_suffix(''), Path(pattern).suffix)
                    for file in parent.glob(pattern):
                        re_name_ = r'{0}_{{{1}}}\{2}'.format(re_name, oz, file.suffix)
                        if re.findall(re_name_, file.name) and file not in output_paths:
                            output_paths.append(file)

        # wildcards = [r'(~[es]\d?~)']
        # re_name = re_ify(settings.tcf.with_suffix('').name, wildcards)
        # re_name = r'{0}((_[A-^`-z0-9%&]+)(\+[A-^`-z0-9%&]+)*)?'.format(re_name)

        # for glob in search_globs:
        # 	pattern = globify(glob, wildcards)
        # 	pattern = '{0}*{1}'.format(Path(pattern).with_suffix(''), Path(pattern).suffix)
        # 	for file in settings.control_file.parent.glob(pattern):
        # 		re_name_ = r'{0}\{1}'.format(re_name, file.suffix)
        # 		if re.findall(re_name_, file.name):
        # 			output_paths.append(file)

    return output_paths


def getResultPathsFromTCF_v2(tcf_path, old_method=False):
    if old_method:
        output_paths = getOutputDirs_old(tcf_path)
    else:
        output_paths = getOutputDirs(tcf_path)
    output_names = []
    for op in output_paths[:]:
        if old_method:
            suffix = os.path.splitext(op)[1]
            stem = os.path.splitext(os.path.basename(op))[0]
        else:
            suffix = op.suffix
            stem = op.stem
            if '_swmm_ts' in stem:
                stem = stem.split('_swmm_ts')[0]
        if suffix.lower() == '.tpc' or suffix.lower() == '.gpkg':
            if check1DResultsForData(op):
                if stem not in output_names:
                    output_names.append(stem)
            else:
                output_paths.remove(op)
        else:
            if stem not in output_names:
                output_names.append(stem)

    return output_paths, output_names, ''


global LoadRasterMessageBox_result
LoadRasterMessageBox_result = None


def LoadRasterMessageBox_signal(dialog, result):
    global LoadRasterMessageBox_result
    LoadRasterMessageBox_result = result
    dialog.accept()


def LoadRasterMessageBox(parent, title, text):
    global LoadRasterMessageBox_result
    dialog = QDialog(parent)
    dialog.setWindowTitle(title)
    image = QLabel()
    image.setPixmap(QPixmap(":/icons/icons/question.svg"))
    label = QLabel()
    label.setText(text)
    pb_yes = QPushButton()
    pb_yes.setText('Yes')
    pb_no = QPushButton()
    pb_no.setText('No')
    pb_invisible = QPushButton()
    pb_invisible.setText('Yes, but not checked on')
    layout_hori_1 = QHBoxLayout()
    layout_hori_1.addWidget(image)
    layout_hori_1.addWidget(label)
    layout_hori_2 = QHBoxLayout()
    layout_hori_2.addWidget(pb_yes)
    layout_hori_2.addWidget(pb_no)
    layout_hori_2.addWidget(pb_invisible)
    layout_vert = QVBoxLayout()
    layout_vert.addLayout(layout_hori_1)
    layout_vert.addLayout(layout_hori_2)
    layout_vert.setSizeConstraint(QLayout.SetFixedSize)
    dialog.setLayout(layout_vert)

    d = {pb_yes: 'yes', pb_no: 'no', pb_invisible: 'invisible'}
    pb_yes.clicked.connect(lambda: LoadRasterMessageBox_signal(dialog, d[pb_yes]))
    pb_no.clicked.connect(lambda: LoadRasterMessageBox_signal(dialog, d[pb_no]))
    pb_invisible.clicked.connect(lambda: LoadRasterMessageBox_signal(dialog, d[pb_invisible]))

    dialog.exec_()
    return LoadRasterMessageBox_result


class LoadTcfOptions:

    def __init__(self):
        self.grouped = QSettings().value('tuflow/load_tcf_options/grouped', 'true')
        if isinstance(self.grouped, str):
            self.grouped = True if self.grouped.lower() == 'true' else False

        self.load_raster_method = QSettings().value('tuflow/load_tcf_options/load_raster_method', 'yes')
        self.order_method = QSettings().value('tuflow/load_tcf_options/order_method', 'alphabetical')


global loadTCFOptionsMessageBox_result
loadTCFOptionsMessageBox_result = 'cancel'


def loadTCFOptionsMessageBox_signal(dlg, text):
    global loadTCFOptionsMessageBox_result
    loadTCFOptionsMessageBox_result = text
    dlg.accept()


def loadTCFOptionsMessageBox_signal_rbgroup1(rb_group):
    checked_button = rb_group.checkedButton()
    QSettings().setValue('tuflow/load_tcf_options/grouped', checked_button.text() == 'Group by control file')


def loadTCFOptionsMessageBox_signal_rbgroup2(rb_group):
    checked_button = rb_group.checkedButton()
    if checked_button.text() == 'Load Normally':
        QSettings().setValue('tuflow/load_tcf_options/load_raster_method', 'yes')
    elif checked_button.text() == 'Do Not Load':
        QSettings().setValue('tuflow/load_tcf_options/load_raster_method', 'no')
    else:
        QSettings().setValue('tuflow/load_tcf_options/load_raster_method', 'invisible')


def loadTCFOptionsMessageBox_signal_rbgroup3(rb_group):
    checked_button = rb_group.checkedButton()
    if checked_button.text() == 'Control File':
        QSettings().setValue('tuflow/load_tcf_options/order_method', 'control_file')
    elif checked_button.text() == 'Control File (Group Rasters)':
        QSettings().setValue('tuflow/load_tcf_options/order_method', 'control_file_group_rasters')
    else:
        QSettings().setValue('tuflow/load_tcf_options/order_method', 'alphabetical')


def LoadTCFOptionsMessageBox(parent, title):
    global loadTCFOptionsMessageBox_result
    loadTCFOptionsMessageBox_result = 'cancel'

    options = LoadTcfOptions()

    dialog = QDialog(parent)
    dialog.setWindowTitle(title)
    image = QLabel()
    image.setPixmap(QPixmap(":/icons/icons/question.svg").scaled(35, 35, Qt.KeepAspectRatio))
    label = QLabel()
    label.setText('<b>Load from Control File import options</b>')
    hlayout1 = QHBoxLayout()
    hlayout1.addWidget(image)
    hlayout1.addWidget(label)
    hlayout1.addStretch()

    group_options_text = QLabel()
    group_options_text.setText('Grouping Options')
    rb1 = QRadioButton()
    rb1.setText('Group by control file')
    rb2 = QRadioButton()
    rb2.setText('Ungrouped')
    rb1.setChecked(True) if options.grouped else rb2.setChecked(True)
    rb_group1 = QButtonGroup()
    rb_group1.addButton(rb1)
    rb_group1.addButton(rb2)
    hlayout2 = QHBoxLayout()
    hlayout2.addWidget(rb1)
    hlayout2.addWidget(rb2)
    hlayout2.addStretch()

    raster_option_text = QLabel()
    raster_option_text.setText('Raster Load Options')
    rb3 = QRadioButton()
    rb3.setText('Load Normally')
    rb4 = QRadioButton()
    rb4.setText('Do Not Load')
    rb5 = QRadioButton()
    rb5.setText('Load, but not checked on')
    rb_group2 = QButtonGroup()
    rb_group2.addButton(rb3)
    rb_group2.addButton(rb4)
    rb_group2.addButton(rb5)
    if options.load_raster_method == 'yes':
        rb3.setChecked(True)
    elif options.load_raster_method == 'no':
        rb4.setChecked(True)
    elif options.load_raster_method == 'invisible':
        rb5.setChecked(True)
    else:
        rb3.setChecked(True)
    hlayout3 = QHBoxLayout()
    hlayout3.addWidget(rb3)
    hlayout3.addWidget(rb4)
    hlayout3.addWidget(rb5)

    order_option_text = QLabel()
    order_option_text.setText('Ordering Options')
    rb6 = QRadioButton()
    rb6.setText('Alphabetical')
    rb7 = QRadioButton()
    rb7.setText('Control File')
    rb8 = QRadioButton()
    rb8.setText('Control File (Group Rasters)')
    rb_group3 = QButtonGroup()
    rb_group3.addButton(rb6)
    rb_group3.addButton(rb7)
    rb_group3.addButton(rb8)
    if options.order_method == 'control_file':
        rb7.setChecked(True)
    elif options.order_method == 'control_file_group_rasters':
        rb8.setChecked(True)
    else:
        rb6.setChecked(True)
    hlayout5 = QHBoxLayout()
    hlayout5.addWidget(rb6)
    hlayout5.addWidget(rb7)
    hlayout5.addWidget(rb8)
    hlayout5.addStretch()

    pbOk = QPushButton()
    pbOk.setText('OK')
    pbCancel = QPushButton()
    pbCancel.setText('Cancel')
    hlayout4 = QHBoxLayout()
    hlayout4.addStretch()
    hlayout4.addWidget(pbOk)
    hlayout4.addWidget(pbCancel)

    vlayout = QVBoxLayout()
    vlayout.addLayout(hlayout1)
    vlayout.addSpacing(10)
    vlayout.addWidget(order_option_text)
    vlayout.addLayout(hlayout5)
    vlayout.addWidget(group_options_text)
    vlayout.addLayout(hlayout2)
    vlayout.addWidget(raster_option_text)
    vlayout.addLayout(hlayout3)
    vlayout.addLayout(hlayout4)
    dialog.setLayout(vlayout)

    vlayout.setSizeConstraint(QLayout.SetFixedSize)

    pbOk.clicked.connect(lambda: loadTCFOptionsMessageBox_signal(dialog, 'ok'))
    pbCancel.clicked.connect(lambda: loadTCFOptionsMessageBox_signal(dialog, 'cancel'))
    rb1.clicked.connect(lambda: loadTCFOptionsMessageBox_signal_rbgroup1(rb_group1))
    rb2.clicked.connect(lambda: loadTCFOptionsMessageBox_signal_rbgroup1(rb_group1))
    rb3.clicked.connect(lambda: loadTCFOptionsMessageBox_signal_rbgroup2(rb_group2))
    rb4.clicked.connect(lambda: loadTCFOptionsMessageBox_signal_rbgroup2(rb_group2))
    rb5.clicked.connect(lambda: loadTCFOptionsMessageBox_signal_rbgroup2(rb_group2))
    rb6.clicked.connect(lambda: loadTCFOptionsMessageBox_signal_rbgroup3(rb_group3))
    rb7.clicked.connect(lambda: loadTCFOptionsMessageBox_signal_rbgroup3(rb_group3))
    rb8.clicked.connect(lambda: loadTCFOptionsMessageBox_signal_rbgroup3(rb_group3))

    dialog.exec_()
    return loadTCFOptionsMessageBox_result


@dataclass
class NetcdfDim:
    name: str
    size: int


@dataclass
class NetcdfVar:
    name: str
    dimensions: list[NetcdfDim]
    fill_value: float = field(default=None)
    attrs: dict[str, str] = field(default_factory=dict)
    data_type: int = field(default=0)
    shape: tuple[int] = field(init=False, default_factory=tuple)
    dim_names: tuple[str] = field(init=False, default_factory=tuple)
    dim_sizes_dict: dict[str, int] = field(init=False, default_factory=dict)

    def __post_init__(self):
        self.shape = tuple([dim.size for dim in self.dimensions])
        self.dim_names = tuple([dim.name for dim in self.dimensions])
        self.dim_sizes_dict = {dim.name: dim.size for dim in self.dimensions}
        for key, value in self.attrs.items():
            self.__dict__[key] = value


class Netcdf:

    def __init__(self, path):
        self.path = path
        self._dim = OrderedDict({})
        self._var = OrderedDict({})
        self.netcdf_lib = getNetCDFLibrary()
        if self.netcdf_lib[0] == 'python':
            self.netcdf_lib = 'pylib'
        else:
            self.nc_lib_path = self.netcdf_lib[1]
            self.netcdf_lib = 'clib'
            if not Path(self.nc_lib_path).exists():
                raise ImportError('NetCDF library not found')
            self.ncdll = ctypes.cdll.LoadLibrary(self.nc_lib_path)

    def __enter__(self, mode='r'):
        return self.open(mode)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def open(self, mode):
        if self.netcdf_lib == 'pylib':
            from netCDF4 import Dataset
            self.ncid = Dataset(self.path, mode)
        else:
            file = ctypes.c_char_p(str.encode(self.path))
            NC_NOWRITE = ctypes.c_int(0)
            ncidp = ctypes.pointer(ctypes.c_int())
            err = self.ncdll.nc_open(file, NC_NOWRITE, ncidp)
            self.ncid = ncidp.contents

        return self

    def close(self):
        if self.netcdf_lib == 'pylib':
            self.ncid.close()
        else:
            self.ncdll.nc_close(self.ncid)

    @property
    def dimensions(self):
        if self.netcdf_lib == 'pylib':
            for dim in self.ncid.dimensions.values():
                self._dim[dim.name] = NetcdfDim(dim.name, dim.size)
        else:
            ndims_p = ctypes.pointer(ctypes.c_int())
            nvars_p = ctypes.pointer(ctypes.c_int())
            natts_p = ctypes.pointer(ctypes.c_int())
            unlimdimid_p = ctypes.pointer(ctypes.c_int())
            err = self.ncdll.nc_inq(self.ncid, ndims_p, nvars_p, natts_p, unlimdimid_p)
            if err:
                raise IOError('Error reading NetCDF file dimensions')
            for i in range(ndims_p.contents.value):
                cstr_array = (ctypes.c_char * 256)()
                cint_p = ctypes.pointer(ctypes.c_int())
                err = self.ncdll.nc_inq_dim(self.ncid, ctypes.c_int(i), ctypes.byref(cstr_array), cint_p)
                if err:
                    raise IOError('Error reading NetCDF file: dimension id {0}'.format(i))
                name = cstr_array.value.decode('utf-8')
                size = cint_p.contents.value
                self._dim[name] = NetcdfDim(name, size)

        return self._dim

    @property
    def variables(self):
        if self.netcdf_lib == 'pylib':
            for var in self.ncid.variables.values():
                if hasattr(var, '_FillValue'):
                    fill_value = var._FillValue
                else:
                    fill_value = None
                self._var[var.name] = NetcdfVar(
                    var.name,
                    [self._dim[dim] for dim in var.dimensions],
                    fill_value,
                    var.__dict__
                )
        else:
            ndims_p = ctypes.pointer(ctypes.c_int())
            nvars_p = ctypes.pointer(ctypes.c_int())
            natts_p = ctypes.pointer(ctypes.c_int())
            unlimdimid_p = ctypes.pointer(ctypes.c_int())
            err = self.ncdll.nc_inq(self.ncid, ndims_p, nvars_p, natts_p, unlimdimid_p)
            if err:
                raise IOError('Error reading NetCDF file: variable')

            for i in range(nvars_p.contents.value):
                cstr_array = (ctypes.c_char * 256)()
                err = self.ncdll.nc_inq_varname(self.ncid, ctypes.c_int(i), ctypes.byref(cstr_array))

                type_p = ctypes.pointer(ctypes.c_int())
                ndims_p = ctypes.pointer(ctypes.c_int())
                err = self.ncdll.nc_inq_var(self.ncid, ctypes.c_int(i), ctypes.c_int(0), type_p, ndims_p,
                                            ctypes.c_int(0), natts_p)
                if err:
                    raise IOError('Error reading NetCDF file: variable id {0}'.format(i))
                dimids_p = ctypes.pointer((ctypes.c_int * ndims_p.contents.value)())
                natts_p = ctypes.pointer(ctypes.c_int())
                err = self.ncdll.nc_inq_var(self.ncid, ctypes.c_int(i), cstr_array, type_p, ndims_p, dimids_p, natts_p)
                if err:
                    raise IOError('Error reading NetCDF file: variable id {0}'.format(i))

                name = cstr_array.value.decode('utf-8')

                atts = OrderedDict({})
                for j in range(natts_p.contents.value):
                    err = self.ncdll.nc_inq_attname(self.ncid, ctypes.c_int(i), ctypes.c_int(j), cstr_array)
                    att_name = cstr_array.value.decode('utf-8')
                    att_type_p = ctypes.pointer(ctypes.c_int())
                    len_p = ctypes.pointer(ctypes.c_int())
                    err = self.ncdll.nc_inq_att(self.ncid, ctypes.c_int(i), cstr_array, att_type_p, len_p)

                    if att_type_p.contents.value == 1:
                        att_val = ctypes.pointer((ctypes.c_byte * len_p.contents.value)())
                    elif att_type_p.contents.value == 2:
                        att_val = ctypes.pointer((ctypes.c_char * len_p.contents.value)())
                    elif att_type_p.contents.value == 3:
                        att_val = ctypes.pointer((ctypes.c_short * len_p.contents.value)())
                    elif att_type_p.contents.value == 4:
                        att_val = ctypes.pointer((ctypes.c_int * len_p.contents.value)())
                    elif att_type_p.contents.value == 5:
                        att_val = ctypes.pointer((ctypes.c_float * len_p.contents.value)())
                    elif att_type_p.contents.value == 6:
                        att_val = ctypes.pointer((ctypes.c_double * len_p.contents.value)())
                    elif att_type_p.contents.value == 7:
                        att_val = ctypes.pointer((ctypes.c_ubyte * len_p.contents.value)())
                    elif att_type_p.contents.value == 8:
                        att_val = ctypes.pointer((ctypes.c_ushort * len_p.contents.value)())
                    elif att_type_p.contents.value == 9:
                        att_val = ctypes.pointer((ctypes.c_uint * len_p.contents.value)())
                    elif att_type_p.contents.value == 10:
                        att_val = ctypes.pointer((ctypes.c_longlong * len_p.contents.value)())
                    elif att_type_p.contents.value == 11:
                        att_val = ctypes.pointer((ctypes.c_ulonglong * len_p.contents.value)())

                    err = self.ncdll.nc_get_att(self.ncid, ctypes.c_int(i), cstr_array, att_val)

                    if att_type_p.contents.value == 2:
                        att_val = att_val.contents.value.decode('utf-8')
                    elif att_type_p.contents.value == 5 or att_type_p.contents.value == 6:
                        att_val = float(att_val.contents[0])
                    else:
                        att_val = int(att_val.contents[0])

                    atts[att_name] = att_val

                no_fill_p = ctypes.pointer(ctypes.c_int())
                if type_p.contents.value == 1:
                    fill_val = ctypes.pointer(ctypes.c_byte())
                elif type_p.contents.value == 2:
                    fill_val = ctypes.pointer(ctypes.c_char())
                elif type_p.contents.value == 3:
                    fill_val = ctypes.pointer(ctypes.c_short())
                elif type_p.contents.value == 4:
                    fill_val = ctypes.pointer(ctypes.c_int())
                elif type_p.contents.value == 5:
                    fill_val = ctypes.pointer(ctypes.c_float())
                elif type_p.contents.value == 6:
                    fill_val = ctypes.pointer(ctypes.c_double())
                elif type_p.contents.value == 7:
                    fill_val = ctypes.pointer(ctypes.c_ubyte())
                elif type_p.contents.value == 8:
                    fill_val = ctypes.pointer(ctypes.c_ushort())
                elif type_p.contents.value == 9:
                    fill_val = ctypes.pointer(ctypes.c_uint())
                elif type_p.contents.value == 10:
                    fill_val = ctypes.pointer(ctypes.c_longlong())
                elif type_p.contents.value == 11:
                    fill_val = ctypes.pointer(ctypes.c_ulonglong())

                err = self.ncdll.nc_inq_var_fill(self.ncid, ctypes.c_int(i), no_fill_p, ctypes.c_int(0))
                if no_fill_p.contents.value != 1:
                    err = self.ncdll.nc_inq_var_fill(self.ncid, ctypes.c_int(i), no_fill_p, fill_val)
                    fill_val = fill_val.contents.value
                else:
                    fill_val = None

                dims = []
                for j in range(ndims_p.contents.value):
                    dimid = dimids_p.contents[j]
                    for k, dim in enumerate(self.dimensions.values()):
                        if k == dimid:
                            dims.append(dim)

                self._var[name] = NetcdfVar(name, dims, fill_val, atts, type_p.contents.value)

        return self._var


class LayerHelper:
    __slots__ = ('_layer', '_datasource')

    def __new__(cls, *args, **kwargs):
        if isinstance(args[0], QgsVectorLayer):
            cls = VectorLayerHelper
        elif isinstance(args[0], QgsRasterLayer):
            cls = RasterLayerHelper
        else:
            raise TypeError('LayerHelper must be initialised with a QgsVectorLayer or QgsRasterLayer')

        self = object.__new__(cls)
        self._layer = args[0]
        self._datasource = self._layer.dataProvider().dataSourceUri()
        return self

    @property
    def is_database(self):
        return False

    @property
    def datasource(self):
        return self._datasource

    @property
    def layer_name(self):
        return self.layer.name()

    @property
    def tuflow_path(self):
        if self.is_database:
            return '{0} >> {1}'.format(self.datasource, self.layer_name)
        else:
            return self.datasource

    def is_tuflow_type(self, version):
        return False


class VectorLayerHelper(LayerHelper):

    @property
    def is_database(self):
        return bool(re.findall(r'\|layername=', self._datasource))

    @property
    def datasource(self):
        ds = re.split('\|layername=', self._datasource)[0]
        return ds.split('|')[0]

    @property
    def layer_name(self):
        if self.is_database:
            _, layer_name = self._datasource.split('|layername=')
        else:
            layer_name = Path(self._datasource).stem
        return layer_name.split('|')[0]

    def is_tuflow_type(self, version):
        if version >= 20230100:
            return Path(self.datasource).suffix.lower() in ['.mif', '.shp', '.gpkg']
        else:
            return Path(self.datasource).suffix.lower() in ['.mif', '.shp']


class RasterLayerHelper(LayerHelper):

    @property
    def is_database(self):
        return Path(self.datasource).suffix.lower() == '.gpkg' or Path(self.datasource).suffix.lower() == '.nc'

    @property
    def datasource(self):
        if 'GPKG:' in self._datasource or 'NetCDF:' in self._datasource:
            _, ds = self._datasource.split(':', 1)
            ds, _ = ds.rsplit(':', 1)
            return ds
        return self._datasource

    @property
    def layer_name(self):
        if self.is_database:
            _, lyrname = self._datasource.rsplit(':', 1)
            return lyrname
        else:
            layer_name = Path(self._datasource).stem

        return layer_name

    def is_tuflow_type(self, version):
        if version >= 20230100:
            return Path(self.datasource).suffix.lower() in ['.asc', '.dem', '.txt', '.flt', '.gpkg', '.nc', '.tif',
                                                            '.tiff', '.gtif', '.gtiff', '.btif', '.btiff', '.tif8',
                                                            '.tiff8']
        else:
            return Path(self.datasource).suffix.lower() in ['.asc', '.dem', '.txt', '.flt']


def plugin_version_to_int(version_string):
    p = version_string.split('.')
    maj = int(p[0]) * 10000
    if len(p) > 1:
        min = int(p[1]) * 1000
    else:
        min = 0
    if len(p) > 2:
        patch = int(p[2]) * 100
    else:
        patch = 0
    if len(p) > 3:
        dev = int(p[3])
    else:
        dev = 0
    return maj + min + patch + dev


def download_latest_dev_plugin(iface=None):
    parent = iface.mainWindow() if iface else None
    _, build_vers = version()
    # latest_dev_version = get_latest_dev_plugin_version()
    # if plugin_version_to_int(latest_dev_version) <= plugin_version_to_int(build_vers):
    # QMessageBox.information(parent, 'Install Latest Dev Plugin',
    #'Installed version is the same or newer than the latest dev version.')
    # 	return

    download_path = browse(parent, 'output file', "TUFLOW/download_location", 'Enter name of the file to save to...',

    'ZIP (*.zip *.ZIP)', default_filename = 'tuflow_plugin.zip')
    if not download_path:
        return

    url = 'https://downloads.tuflow.com/Private_Download/QGIS_TUFLOW_Plugin/tuflow_plugin.zip'
    try:
        downloader = DownloadBinPackage(url, download_path, 'Downloading tuflow_plugin.zip. . . ')
        downloader.start()
        downloader.wait()
    except Exception as e:
        QMessageBox.critical(parent, 'Download Error', 'Error downloading latest dev plugin: {0}'.format(e))
        return

    if downloader.user_cancelled:
        QMessageBox.critical(parent, 'Download Error', 'User cancelled download')
        return

    completed_text = 'Download complete:<p>{0}' \
                     '<p><p>Please see the following wiki page for instructions on how to install:' \
                     '<p><a href=\"https://wiki.tuflow.com/index.php?title=Installing_the_Latest_Development_Version_of_the_TUFLOW_Plugin#How_to_install_the_Development_Plugin_Version\">' \
                     'How to manually install the TUFLOW Plugin</a>'.format(download_path)
    message_box = QMessageBox(parent)
    message_box.setText(completed_text)
    message_box.setIcon(QMessageBox.Information)
    message_box.addButton(QMessageBox.Close)
    btn = QPushButton()
    btn.setText('Copy Path to Clipboard')
    message_box.addButton(btn, QMessageBox.ActionRole)
    btn.disconnect()
    btn.clicked.connect(lambda: QApplication.clipboard().setText(download_path))
    message_box.open()
    # QMessageBox.information(parent, 'Install Latest Dev Plugin', completed_text)


def get_driver_by_extension(driver_type, ext):
    if not ext:
        return

    ext = ext.lower()
    if ext[0] == '.':
        ext = ext[1:]

    for i in range(gdal.GetDriverCount()):
        drv = gdal.GetDriver(i)
        md = drv.GetMetadata_Dict()
        if ('DCAP_RASTER' in md and driver_type == 'raster') or ('DCAP_VECTOR' in md and driver_type == 'vector'):
            if not drv.GetMetadataItem(gdal.DMD_EXTENSIONS):
                continue
            driver_extensions = drv.GetMetadataItem(gdal.DMD_EXTENSIONS).split(' ')
            for drv_ext in driver_extensions:
                if drv_ext.lower() == ext:
                    return drv.ShortName


global has_kart, kart_version_
has_kart = False
kart_version_ = None


def kart_executable():
    if os.name == "nt":
        defaultFolder = os.path.join(os.environ["PROGRAMFILES"], "Kart")
    elif sys.platform == "darwin":
        defaultFolder = "/Applications/Kart.app/Contents/MacOS/"
    else:
        defaultFolder = "/opt/kart"
    folder = defaultFolder
    for exe_name in ("kart.exe", "kart_cli_helper", "kart_cli", "kart"):
        path = os.path.join(folder, exe_name)
        if os.path.isfile(path):
            return path
    return path


def get_kart_version():
    global has_kart, kart_version_
    if has_kart:
        return kart_version_
    elif kart_version_ == -1:
        return kart_version_
    else:
        try:
            proc = subprocess.run([kart_executable(), '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  creationflags=subprocess.CREATE_NO_WINDOW)
            v = proc.stdout.decode('utf-8', errors='ignore').split(',')[0]
            v = re.findall('\d+', v)
            i = 1000
            v_ = 0
            for n in v:
                v_ += int(n) * i
                i /= 10
            kart_version_ = int(v_)
            has_kart = True
        except Exception as e:
            kart_version_ = -1
    return kart_version_


def kart_gpkg(kart_repo):
    kart_folder = actual_kart_folder(kart_repo)
    if not kart_folder:
        return
    config = Path(kart_folder) / 'config'
    if not config.exists():
        return
    with config.open() as f:
        contents = f.read()
    if '[kart "workingcopy"]' not in contents:
        return
    try:
        working_copy = re.split(r'\[kart "workingcopy"\]', contents)[1].split('[')[0]
        working_copy_settings = zip(working_copy.split('=')[::2], working_copy.split('=')[1::2])
        for param, value in working_copy_settings:
            if param.strip() == 'location':
                gpkg = Path(kart_repo) / value.strip()
                return str(os.path.abspath(gpkg))
    except Exception as e:
        return


def actual_kart_folder(repo_path):
    git = Path(repo_path) / '.git'
    if git.exists():
        try:
            kart_dir = None
            with git.open() as f:
                for line in f:
                    if 'gitdir' in line:
                        kart_dir = git.parent / line.split(':')[1].strip()
            if kart_dir and kart_dir.exists():
                config = kart_dir / 'config'
                with config.open() as f:
                    contents = f.read()
                if re.findall(r'\[kart', contents):
                    return str(kart_dir)
        except Exception as e:
            return ''
    else:
        return ''


def kart_repo_from_empty_folder(empty_path):
    git = Path(empty_path).parent
    if actual_kart_folder(git):
        return os.path.abspath(git)
    return ''


class EmptyFileData:

    def __init__(self, out_name, out_file, empty_file, geom):
        self.out_name = out_name
        self.out_file = out_file
        self.empty_file = empty_file
        self.geom = geom


class ImportEmpty:
    """Currently only used for kart."""

    def __init__(self, empty_dir, run_id, database_option, database, convert_to_gpkg):
        self.empty_dir = empty_dir
        self.gis_dir = str(Path(empty_dir).parent / 'gis')
        self.run_id = run_id
        self.database_option = database_option
        self.database = database
        self.convert_to_gpkg = convert_to_gpkg
        self.empty_files = []

    def _empty_file(self, empty_type, geom_ext):
        for file in Path(self.empty_dir).glob('{0}_empty*'.format(empty_type, geom_ext)):
            if re.findall(r'_[PLR]$', file.name):
                if re.findall(r'_[PLR]$', file.name)[0] == geom_ext:
                    return str(file)
            else:
                return str(file)

    def _out_file(self, empty_type, geom_ext, ext, database_option, database):
        out_name = '{0}_{1}'.format(empty_type, self.run_id)
        if ext.lower != '.gpkg' or database_option == 'separate':
            file = '{0}{1}{2} >> {0}{1}'.format(out_name, geom_ext, ext)
        elif database_option == 'grouped':
            file = '{0}{2} >> {0}{1}'.format(out_name, geom_ext, ext)
        else:
            file = '{0} >> {1}{2}'.format(database, out_name, geom_ext)
        return file

    def add(self, empty_type, geom_ext):
        from .compatibility_routines import suffix_2_geom_type
        empty_file = self._empty_file(empty_type, geom_ext)
        if not empty_file:
            return
        out_file = self._out_file(empty_type, geom_ext, Path(empty_file).suffix, self.database_option, self.database)
        db, lyr_name = out_file.split(' >> ')
        empty_file_data = EmptyFileData(lyr_name, db, empty_file, suffix_2_geom_type(geom_ext))
        self.empty_files.append(empty_file_data)

    def validate_layers(self, layers, gpkg):
        from .compatibility_routines import GPKG
        gpkg_layers = [x.lower() for x in GPKG(gpkg).layers()]
        return [x for x in layers if x.lower() in gpkg_layers]

    def validate_kart_layers(self, kart_repo):
        try:
            gpkg = kart_gpkg(kart_repo)
            layers = [x.out_name for x in self.empty_files]
            return self.validate_layers(layers, gpkg)
        except Exception as e:
            pass

        return 'Could not find kart GPKG'

    def import_to_kart(self, kart_exe, kart_repo):
        from .compatibility_routines import copy_field_defn, sanitise_field_defn, GIS_GPKG
        wkdir = actual_kart_folder(kart_repo)
        temp_dir = tempfile.mkdtemp(prefix='import_empty')
        for empty_file in self.empty_files:
            tmp_out = str(Path(temp_dir) / Path(empty_file.out_file).name)
            driver_name = get_driver_by_extension('vector', Path(empty_file.empty_file).suffix)
            if not driver_name:
                return 'Error getting driver for {0}'.format(empty_file.empty_file.stem)
            ds_in = ogr.GetDriverByName(driver_name).Open(empty_file.empty_file)
            lyr_in = ds_in.GetLayer()
            sr = lyr_in.GetSpatialRef()
            ds_out = ogr.GetDriverByName('GPKG').CreateDataSource(tmp_out)
            lyr_out = ds_out.CreateLayer(empty_file.out_name, sr, empty_file.geom)
            layer_defn = lyr_in.GetLayerDefn()
            for i in range(0, layer_defn.GetFieldCount()):
                fieldDefn = copy_field_defn(layer_defn.GetFieldDefn(i))
                fieldDefn = sanitise_field_defn(fieldDefn, GIS_GPKG)
                lyr_out.CreateField(fieldDefn)
            sr = None
            ds_out, lyr_out = None, None
            ds_in, lyr_in = None, None
            proc = subprocess.run([kart_exe, 'import', '{0}'.format(tmp_out), empty_file.out_name], cwd=wkdir,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            Path(tmp_out).unlink()
            shutil.rmtree(temp_dir)
            if proc.returncode != 0:
                return proc.stderr.decode('utf-8', errors='ignore')


def goto_plugin_help():
    url = 'https://wiki.tuflow.com/TUFLOW_QGIS_Plugin'
    webbrowser.open(url)


def goto_plugin_changelog():
    url = 'https://docs.tuflow.com/qgis-tuflow-plugin/changelog/'
    webbrowser.open(url)


def goto_tuflow_downloads():
    url = 'https://tuflow.com/downloads/'
    webbrowser.open(url)


if __name__ == '__main__':
    a = float('{0:.6f}'.format(2. / 60. / 60.))
    print(roundSeconds2(a, 2))
