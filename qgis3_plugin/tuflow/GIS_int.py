# TuPLOT External Load interface python file.
# Build: 2017-11-AA Development
# Author: PR

# ArcGIS and QGIS use identical versions

import os
import sys

class INT:
    def __init__(self): #initialise the .int
        self.error = False
        self.message = None
        self.GeomNone = 0
        self.GeomPoint = 1
        self.GeomLine = 2
        self.GeomRegion = 3
        self.GeomMulti = 4
        self.GeomUnknown = 5
        self.ID_att = [] #GIS ID attribute
        self.Type_Att = [] #GIS Type attribute
        self.Source_Att =[] #GIS Source
        self.Doms = [] #domain, 1D, 2D, RL
        self.Geom = self.GeomNone

    def load(self, fname):
        #reset lists
        self.ID_att = []
        self.Type_Att = []
        self.Source_Att =[]
        self.Geom = self.GeomNone

        #open file
        fi = open(fname, 'rt')

        #get geometry
        for line in fi:
            if(line.find('[GEOMETRY]') >= 0):
                line = next(fi)
                if line.upper().find('POINT') >= 0:
                    self.Geom = self.GeomPoint
                elif line.upper().find('LINE') >= 0:
                    self.Geom = self.GeomLine
                elif line.upper().find('REGION') >= 0:
                    self.Geom = self.GeomRegion
                elif line.upper().find('MULTI') >= 0:
                    self.Geom = self.GeomMulti
                else:
                    self.Geom = self.GeomUnknown
                    self.error = True
                    self.message = 'ERROR - Unexpected geometry type in interface file {0}'.format(fname)
                    return #bail out
                break #found break this for loop

        #get info on selected GIS objects
        fi.seek(0) #rewind file
        for line in fi:
            if(line.upper().find('[SELECTION]') >= 0):
                data_block = True
                while (data_block):
                    line = next(fi)
                    if not line: break
                    if (line.upper().find('[/SELECTION]') >= 0):
                        data_block = False
                    else:
                        data = line.strip('\n').split(',')
                        if len(data)  <3:
                            self.error = True
                            self.message = 'ERROR - Data missing from selection line: '.format(line)
                            return
                        self.ID_att.append(data[0].strip('"').strip()) #1st strip removes double quotes, 2nd strip removes whitespace at start or end
                        type_att = data[1].strip('"')
                        self.Type_Att.append(type_att)
                        #work out domain
                        if (type_att.upper().find('NODE') >= 0) or (type_att.upper().find('CHAN') >= 0):
                            dom = '1D'
                        else:
                            dom = type_att
                        self.Doms.append(dom)
                        self.Source_Att.append(data[2].strip('"'))

        #close file
        fi.close()

        #some checks
        if len(self.ID_att) == 0:
            self.error = True
            self.message = 'ERROR - No GIS objects selected.'
            return

        if len(self.ID_att) != len(self.Type_Att) or len(self.ID_att) != len(self.Source_Att) or len(self.ID_att) != len(self.Doms):
            self.error = True
            self.message = 'ERROR - Number of selection attributes do not match.'
            return