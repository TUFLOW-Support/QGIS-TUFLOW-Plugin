# -------------------------------------------------------------------------------
#  Name:        module1
#  Purpose:
#
#  Author:      par, es
#
#  Created:     03/03/2017
#  Copyright:   (c) par 2017
#  Licence:     <your licence>
# -------------------------------------------------------------------------------
import os
import sys
import re
import zipfile
from pathlib import Path

import numpy
import math
import logging
import io

import pandas as pd

from tuflow.ARR2016.ARR_TUFLOW_func_lib import *
from tuflow.ARR2016.BOM_WebRes import Bom
from tuflow.ARR2016.meta import ArrMeta
from tuflow.ARR2016.climate_change import ArrCCF
from tuflow.ARR2016.losses import ArrLosses
from tuflow.ARR2016.preburst import ArrPreburst
from tuflow.ARR2016.arr_settings import ArrSettings
from tuflow.ARR2016.parser import DataBlock
from tuflow.ARR2016.downloader import Downloader


class ArrRivReg:
    def __init__(self):
        self.loaded = False
        self.error = False
        self.message = None
        self.Division = None
        self.RivRegNum = None
        self.River_Region = None
        self.Meta = ArrMeta()
        self.logger = logging.getLogger('ARR2019')

    def load(self, fi):
        for line in fi:
            if line.find('[RIVREG]') >= 0:
                finished = False
                for block_line in fi:
                    data = block_line.split(',')
                    if data[0].lower() == 'division':
                        self.Division = data[1]
                    elif data[0].lower() == 'rivregnum':
                        self.RivRegNum = float(data[1])
                    elif data[0].lower() == 'river region':
                        self.River_Region = data[1]
                    elif data[0].find('[RIVREG_META]') >= 0:
                        self.Meta.read(fi)
                    elif data[0].find('[END_RIVREG]') >= 0:
                        finished = True
                        break
                if finished:
                    break
        fi.seek(0)  # rewind file
        self.loaded = True
        #print('Finished reading file.')
        self.logger.info('Finished reading file')


# noinspection PyBroadException
class ArrInput:
    def __init__(self):  # initialise the ARR input data class
        self.loaded = False
        self.error = False
        self.message = None
        self.Latitude = None
        self.Longitude = None
        self.logger = logging.getLogger('ARR2019')

    def load(self, fi):
        for line in fi:
            if line.find('[INPUTDATA]') >= 0:
                finished = False
                for block_line in fi:
                    data = block_line.split(',')
                    if data[0].lower() == 'latitude':
                        try:
                            self.Latitude = float(data[1])
                        except TypeError:
                            self.error = True
                            self.message = 'Unexpected error opening file {0}'.format(fi)
                            return
                    elif data[0].lower() == 'longitude':
                        try:
                            self.Longitude = float(data[1])
                        except:
                            self.error = True
                            self.message = 'Unexpected error opening file {0}'.format(fi)
                            return
                    elif data[0].find('[END_INPUTDATA]') >= 0:
                        finished = True
                        break
                if finished:
                    break
        fi.seek(0)  # rewind file
        self.loaded = True
        #print('Finished reading file.')
        self.logger.info('Finished reading file.')


class ArrArf:
    def __init__(self):  # initilise the ARR Areal Reduction Factors
        self.loaded = False
        self.error = False
        self.message = None
        self.param = {}
        self.logger = logging.getLogger('ARR2019')

    def load(self, fi):
        found = False
        for line in fi:
            if line.find('[LONGARF]') >= 0:
                found = True
                finished = False
                for block_line in fi:
                    data = block_line.split(',')
                    finished = (data[0] == '\n' or block_line.find('[LONGARF_META]') >= 0)
                    if finished:
                        break
                    if not data[0].lower() == 'zone':
                        self.param[data[0]] = data[1]
                if finished:
                    break
        if not found:
            self.logger.info('WARNING: No Areal Reduction Factors (ARF) found.')
            fi.seek(0)
            return
        if len(self.param) < 1:
            self.error = True
            self.message = 'Error processing ARF.'
        fi.seek(0)
        self.loaded = True
        #print('Finished reading file.')
        self.logger.info('Finished reading file.')


class ArrTemporal:
    def __init__(self):  # initialise the ARR temoral pattern class
        self.loaded = False
        self.error = False
        self.message = None
        self.tpCount = 0
        self.meta = ArrMeta()
        # point temporal pattern data
        self.pointID = []
        self.pointDuration = []
        self.pointTPNumnber = []
        self.pointTimeStep = []
        self.pointRegion = []
        self.pointAEP_Band = []
        self.pointincrements = []
        # areal temporal pattern data
        self.arealID = {}  # dict {tp catchment area: [id]} e.g. { 100: [ 9802, 9803, 9804, .. ], 200: [ .. ], ..  }
        self.arealDuration = {}  # dict {tp cathcment area: [duration]} e.g. { 100: [ 10, 10, 10, .. ] }
        self.arealTPNumber = {}
        self.arealTimeStep = {}  # dict {tp catchment area: [timestep]} e.g. { 100: [ 5, 5, 5, .. ] }
        self.arealRegion = {}  # dict {tp catchment area: [region]} e.g. { 100: [ 'Wet Tropics', .. ] }
        self.arealAEP_Band = {}  # dict {tp catchment area: [aep band]} e.g. { 100: [ 'frequent', .. ] }
        self.arealincrements = {}  # dict {tp catchment area: [increments]} e.g. { 100: [ [ 53.95, 46.05 ], .. ] }
        # adopted temporal pattern data
        self.ID = []
        self.Duration = []
        self.TPNumber = []
        self.TimeStep = []
        self.Region = []
        self.AEP_Band = []
        self.increments = []  # list of rainfall increments, length varies depending on duration
        self.tpRegion = ''  # extracted before patterns start
        self.dur2tptype = {}  # duration to temporal pattern type ('point' or 'areal')
        self.add_areal_tp = 0
        self.add_areal_messages = []

        self.tp_data = {}

        self.logger = logging.getLogger('ARR2019')
    
    def load(self, fname, fi, tpRegion, point_tp_csv, areal_tp_csv, areal_tp_download=None):
        """Load ARR data"""
        self.tp_data = DataBlock(fi, 'TP', False)
        self.meta.version = self.tp_data.version_int
        self.meta.time_accessed = self.tp_data.time_accessed
        self.tp_region = self.tp_data.get('Label')

        if point_tp_csv is None:
            #print("Loading point temporal patterns from download: {0}".format(fname))
            self.logger.info("Loading point temporal patterns from download: {0}".format(fname))
            self.loadPointTpFromDownload(fi, tpRegion)
        else:
            #print("Loading point temporal patterns from user input: {0}".format(point_tp_csv))
            self.logger.info("Loading point temporal patterns from user input: {0}".format(point_tp_csv))
            self.loadPointTpFromCSV(point_tp_csv)
        if self.error:
            #print("ERROR loading point temporal patterns: {0}".format(self.message))
            self.logger.error("ERROR loading point temporal patterns: {0}".format(self.message))
            raise Exception("Error loading point temporal patterns")
            
        if areal_tp_csv is not None:
            #print("Loading areal temporal patterns from user input: {0}".format(areal_tp_csv))
            self.logger.info("Loading areal temporal patterns from user input: {0}".format(areal_tp_csv))
            self.loadArealTpFromCSV(areal_tp_csv)
            if self.error:
                #print("ERROR loading areal temporal patterns: {0}".format(self.message))
                self.logger.error("ERROR loading areal temporal patterns: {0}".format(self.message))
                raise Exception("Error loading areal temporal patterns")

        if areal_tp_download is not None:
            #print("Loading areal temporal patterns from user input: {0}".format(areal_tp_csv))
            self.logger.info("Loading areal temporal patterns from download: {0}".format(areal_tp_download))
            self.loadArealTpFromCSV(areal_tp_download)
            if self.error:
                #print("ERROR loading areal temporal patterns: {0}".format(self.message))
                self.logger.error("ERROR loading areal temporal patterns: {0}".format(self.message))
                raise Exception("Error loading areal temporal patterns")
    
    def loadPointTpFromDownload(self, fi, tpRegion):
        self.tpRegion = tpRegion
        code = None
        tpno = 0
        for line in fi:
            if line.find('[TP]') >= 0:
                for block_line in fi:
                    if 'code' in block_line:
                        _, code = [x.strip() for x in block_line.split(',', 1)]
                        break
                    if '[END_TP]' in block_line:
                        break
            if line.find('[STARTPATTERNS]') >= 0:
                finished = False
                # fi.next() # skip 1st line
                for block_line in fi:
                    data = block_line.split(',')
                    finished = '[ENDPATTERNS]' in block_line
                    if finished:
                        break
                    if block_line == '\n':
                        continue
                    if 'eventid' in block_line.lower():
                        continue
                    elif block_line == '\n':
                        continue
                    try:
                        tpno += 1
                        if tpno > 10:
                            tpno = 1
                        self.pointTPNumnber.append(tpno)
                        self.pointID.append(int(data[0]))
                        dur = int(data[1])
                        self.pointDuration.append(dur)
                        inc = int(data[2])
                        self.pointTimeStep.append(inc)
                        self.pointRegion.append(data[3])
                        self.pointAEP_Band.append(data[4].lower())
                    except:
                        self.error = True
                        self.message = 'Error processing line {0}'.format(block_line)
                        break
                    try:
                        incs = []
                        for i in range(int(dur / inc)):
                            incs.append(float(data[5 + i]))
                        self.pointincrements.append(incs)
                    except:
                        self.error = True
                        self.message = 'Error processing from line {0}'.format(block_line)
                        break
                if finished:
                    break
        fi.seek(0)  # rewind file
        if not self.pointincrements and self.tpRegion.upper() != 'RANGELANDS WEST AND RANGELANDS':
            if code is None:
                self.error = True
                self.message = 'No temporal patterns found. Please check "ARR_web_data" to see if temporal patterns are present.'
            else:
                self.logger.info('Temporal patterns not found in {0}. Trying to manually download....'.format(os.path.basename(fi.name)))
                csv = self.download_point_tp(code, os.path.dirname(fi.name))
                if csv is not None and not self.error:
                    self.loadPointTpFromCSV(csv)
                else:
                    return
        self.loaded = True
        #print('Finished reading file.')
        self.logger.info('Finished reading file.')

    def append(self, fi):
        code = None
        found_something = False
        tpno = 0
        for line in fi:
            if line.find('[TP]') >= 0:
                for block_line in fi:
                    if 'code' in block_line:
                        _, code = [x.strip() for x in block_line.split(',', 1)]
                        break
                    if '[END_TP]' in block_line:
                        break
            if line.find('[STARTPATTERNS]') >= 0:
                finished = False
                # fi.next() # skip 1st line
                for block_line in fi:
                    data = block_line.split(',')
                    finished = (data[0] == '\n' or block_line.find('[ENDPATTERNS]') >= 0)
                    if finished:
                        break
                    if not finished:
                        if 'eventid' in block_line.lower():
                            continue
                        elif block_line == '\n':
                            continue
                        try:
                            found_something = True
                            tpno += 1
                            if tpno > 10:
                                tpno = 1
                            self.pointTPNumnber.append(tpno)
                            self.pointID.append(int(data[0]))
                            dur = int(data[1])
                            self.pointDuration.append(dur)
                            inc = int(data[2])
                            self.pointTimeStep.append(inc)
                            self.pointRegion.append(data[3])
                            self.pointAEP_Band.append(data[4].lower())
                        except:
                            self.error = True
                            self.message = 'Error processing line {0}'.format(block_line)
                            break
                        try:
                            incs = []
                            for i in range(int(dur / inc)):
                                incs.append(float(data[5 + i]))
                            self.pointincrements.append(incs)
                        except:
                            self.error = True
                            self.message = 'Error processing from line {0}'.format(block_line)
                            break
                if finished:
                    break
        fi.seek(0)  # rewind file
        if not found_something:
            if code is None:
                self.logger.warning('No temporal patterns found.')
            else:
                self.logger.info('Temporal patterns not found in {0}. Trying to manually download....'.format(os.path.basename(fi.name)))
                csv = self.download_point_tp(code, os.path.dirname(fi.name))
                if csv is not None and not self.error:
                    self.loadPointTpFromCSV(csv)
                else:
                    return
        self.loaded = True
        #print('Finished reading file.')
        self.logger.info('Finished reading file.')

    def download_point_tp(self, code, out_path):
        url = 'http://data.arr-software.org//static/temporal_patterns/TP/{0}.zip'.format(code)
        self.logger.info('URL: {0}'.format(url))
        try:
            downloader = Downloader(url)
            downloader.download()
            if not downloader.ok():
                raise Exception(f'Failed to download point temporal pattern: {downloader.error_string}')
            z = zipfile.ZipFile(io.BytesIO(downloader.data))
            z.extractall(out_path)
            csv = [os.path.join(out_path, x.filename) for x in z.filelist if x.filename and 'INCREMENTS' in x.filename.upper()]
            if csv:
                return csv[0]
            else:
                raise Exception('Temporal pattern Increments file not found')
        except Exception as e:
            self.error = True
            self.message = "ERROR: failed to download/extract point temporal pattern.\n{0}".format(e)

    def loadPointTpFromCSV(self, tp):
        """
        Load point temporal patterns from csv (i.e. "_Increments.csv")
        
        :param tp: str full file path to csv
        :return: void
        """
        tpno = 0
        if os.path.exists(tp):
            try:
                with open(tp, 'r') as tp_open:
                    for i, line in enumerate(tp_open):
                        if i > 0:
                            data = line.split(',')
                            finished = data[0] == '\n'
                            if finished:
                                break
                            if not finished:
                                try:
                                    tpno += 1
                                    if tpno > 10:
                                        tpno = 1
                                    self.pointTPNumnber.append(tpno)
                                    self.pointID.append(int(data[0]))
                                    dur = int(data[1])
                                    self.pointDuration.append(dur)
                                    inc = int(data[2])
                                    self.pointTimeStep.append(inc)
                                    self.pointRegion.append(data[3])
                                    self.pointAEP_Band.append(data[4].lower())
                                except:
                                    self.error = True
                                    self.message = 'Error processing line {0}'.format(line)
                                    break
                                try:
                                    incs = []
                                    for i in range(int(dur / inc)):
                                        incs.append(float(data[5 + i]))
                                    self.pointincrements.append(incs)
                                except:
                                    self.error = True
                                    self.message = 'Error processing from line {0}'.format(line)
                                    break
            except IOError:
                #print("Could not open {0}".format(tp))
                self.logger.error("Could not open {0}".format(tp))
                raise ("Could not open point temporal pattern csv")
        else:
            #print("Could not find {0}".format(tp))
            self.logger.error("Could not find {0}".format(tp))
            raise ("Could not find point temporal pattern csv")

    def loadArealTpFromCSV(self, tp):
        """
        Load areal temporal patterns from csv (i.e. "Areal_Increments.csv")

        :param tp: str full file path to csv
        :return: void
        """

        self.logger.info('Loading Areal Temporal Pattern from CSV: {0}'.format(tp))

        tpno = 0
        if os.path.exists(tp):
            try:
                with open(tp, 'r') as tp_open:
                    for i, line in enumerate(tp_open):
                        if i > 0:
                            data = line.split(',')
                            finished = data[0] == '\n'
                            if finished:
                                break
                            if not finished:
                                try:
                                    area = int(data[4])
                                    tpno += 1
                                    if tpno > 10:
                                        tpno = 1
                                    if area not in self.arealTPNumber:
                                        self.arealTPNumber[area] = []
                                    self.arealTPNumber[area].append(tpno)
                                    if area not in self.arealID:
                                        self.arealID[area] = []
                                    self.arealID[area].append(int(data[0]))
                                    dur = int(data[1])
                                    if area not in self.arealDuration:
                                        self.arealDuration[area] = []
                                    self.arealDuration[area].append(dur)
                                    inc = int(data[2])
                                    if area not in self.arealTimeStep:
                                        self.arealTimeStep[area] = []
                                    self.arealTimeStep[area].append(inc)
                                    if area not in self.arealRegion:
                                        self.arealRegion[area] = []
                                    self.arealRegion[area].append(data[3])
                                    if area not in self.arealAEP_Band:
                                        self.arealAEP_Band[area] = []
                                    self.arealAEP_Band[area].append('all')
                                except:
                                    self.error = True
                                    self.message = 'Error processing line {0}'.format(line)
                                    break
                                try:
                                    incs = []
                                    for i in range(int(dur / inc)):
                                        incs.append(float(data[5 + i]))
                                    if area not in self.arealincrements:
                                        self.arealincrements[area] = []
                                    self.arealincrements[area].append(incs)
                                except:
                                    self.error = True
                                    self.message = 'Error processing from line {0}'.format(line)
                                    break
            except IOError:
                #print("Could not open {0}".format(tp))
                self.logger.error("Could not open {0}".format(tp))
                raise ("Could not open areal temporal pattern csv")
        else:
            #print("Could not find {0}".format(tp))
            self.logger.error("Could not find {0}".format(tp))
            raise ("Could not find areal temporal pattern csv")

    def findNextClosest(self, area, index):
        if not index:
            return area
        area_list = [100, 200, 500, 1000, 2500, 5000, 10000, 20000, 40000]
        actual = self.arealTpArea(area, 0)
        if not actual:
            return
        area_list.remove(actual)
        diffs = [abs(x - area) for x in area_list]
        sorted_list = [x[1] for x in sorted(zip(diffs, area_list))]
        if index > len(sorted_list):
            return None
        return sorted_list[index - 1]

    def arealTpArea(self, area, closest):
        area = self.findNextClosest(area, closest)
        if not area:
            return

        if area < 75:
            tp_area = None
        elif area <= 140:
            tp_area = 100
        elif area <= 300:
            tp_area = 200
        elif area <= 700:
            tp_area = 500
        elif area <= 1600:
            tp_area = 1000
        elif area <= 3500:
            tp_area = 2500
        elif area <= 7000:
            tp_area = 5000
        elif area <= 14000:
            tp_area = 10000
        elif area <= 28000:
            tp_area = 20000
        else:
            tp_area = 40000

        return tp_area
        
    def combineArealTp(self, area):
        """
        Combines point temporal pattern with areal temporal patterns
        
        :param area: float catchment area
        :return: void
        """
        
        # determine if areal pattern is needed
        # if yes, which one
        tp_area = self.arealTpArea(area, 0)

        self.ID = self.pointID[:]
        self.TPNumber = self.pointTPNumnber[:]
        self.Duration = self.pointDuration[:]
        self.TimeStep = self.pointTimeStep[:]
        self.Region = self.pointRegion[:]
        self.AEP_Band = self.pointAEP_Band[:]
        self.increments = self.pointincrements[:]

        self.dur2tptype = {x: 'point' for x in self.Duration}
        
        # check if there are any areal temporal patterns available
        if self.arealDuration:
           # check if areal patterns are required for catchment size
            if tp_area is not None:
                self.logger.info('Using areal temporal pattern area: {0:,}km2'.format(tp_area))
                point_durations = self.getTemporalPatternDurations(self.pointDuration)
                areal_durations = self.getTemporalPatternDurations(self.arealDuration[tp_area])
                inclusions, exclusions = self.getExclusions(point_durations, areal_durations)
                printed_messages = []
                k = 0
                n = 1  # nth closest areal tp
                for i, dur in enumerate(self.Duration):
                    if dur >= inclusions[0]:
                        if dur not in exclusions:
                            if self.dur2tptype[dur] == 'point':
                                n = 1  # reset this as we are in a new duration
                            self.dur2tptype[dur] = 'areal'
                            m = self.arealRegion[tp_area].index(self.Region[i])
                            j = self.arealDuration[tp_area][m:].index(dur) + m
                            if self.Region[i] == self.arealRegion[tp_area][j]:
                                if len(self.arealID[tp_area]) > j + k:  # 40,000km2 areal tp 168hr dur only has one tp
                                    self.ID[i] = self.arealID[tp_area][j + k]
                                    self.TPNumber[i] = self.arealTPNumber[tp_area][j + k]
                                    self.TimeStep[i] = self.arealTimeStep[tp_area][j + k]
                                    self.increments[i] = self.arealincrements[tp_area][j + k]
                                    if k == 9:
                                        k = 0
                                    else:
                                        k += 1
                                else:
                                    while True:
                                        tp_area2 = self.arealTpArea(area, n)
                                        message = "WARNING: {0} min duration has run out of areal temporal patterns... switching to using next closest areal temporal pattern area: {1:,}km2".format(dur, tp_area2)
                                        if message not in printed_messages:
                                            self.logger.warning(message)
                                            printed_messages.append(message)
                                        m = self.arealRegion[tp_area2].index(self.Region[i])
                                        j = self.arealDuration[tp_area2][m:].index(dur) + m
                                        if self.Region[i] == self.arealRegion[tp_area2][j]:
                                            if len(self.arealID[tp_area2]) > j + k:  # 40,000km2 areal tp 168hr dur only has one tp
                                                self.ID[i] = self.arealID[tp_area2][j + k]
                                                self.TPNumber[i] = self.arealTPNumber[tp_area2][j + k]
                                                self.TimeStep[i] = self.arealTimeStep[tp_area2][j + k]
                                                self.increments[i] = self.arealincrements[tp_area2][j + k]
                                                if k == 9:
                                                    k = 0
                                                else:
                                                    k += 1
                                                break
                                        else:
                                            n = n + 1  # shouldn't really get here
                                            if n == 8:
                                                message = "ERROR: {0} min duration has run out of areal temporal patterns... bailing out".format(dur)
                                                self.logger.error(message)
                                                return

                        else:
                            message = "WARNING: {0} min duration does not have an areal temporal pattern... using point temporal pattern".format(dur)
                            if message not in printed_messages:
                                #print(message)
                                self.logger.warning(message)
                                printed_messages.append(message)
        
        self.getTPCount()

    def addArealTP(self, area, ind):
        tp_area = self.arealTpArea(area, ind + 1)
        if not tp_area:
            return False

        self.logger.info('Adding additional areal temporal pattern {0}: {1:,}km2'.format(ind+1, tp_area))

        dur_prev = None
        counter = 0
        for i, dur in enumerate(self.Duration.copy()):
            if self.dur2tptype[dur] == 'point' or dur == dur_prev:
                continue
            if self.AEP_Band[i].startswith('add_areal_tp'):
                break
            dur_prev = dur

            region = self.Region[i]
            m = self.arealRegion[tp_area].index(region)
            j = self.arealDuration[tp_area][m:].index(dur) + m
            if region == self.arealRegion[tp_area][j]:
                count = self.arealDuration[tp_area][m:].count(dur)
                if count < 10 and (tp_area, dur) not in self.add_areal_messages:
                    self.logger.warning('WARNING: Areal TP [{0:,}km2 - {1} min] only contains {2} temporal patterns'.format(tp_area, dur, count))
                    self.add_areal_messages.append((tp_area, dur))
                for k in range(count):
                    counter += 1
                    self.ID.append(self.arealID[tp_area][j+k])
                    self.TPNumber.append(self.arealTPNumber[tp_area][j+k])
                    self.Duration.append(dur)
                    self.TimeStep.append(self.arealTimeStep[tp_area][j+k])
                    self.Region.append(region)
                    self.AEP_Band.append('add_areal_tp_{0}'.format(ind))
                    self.increments.append(self.arealincrements[tp_area][j+k])

        return True

    def get_dur_aep(self, duration, aep_bands):
        # print ('Getting all events with duration {0} min and AEP band {1}'.format(duration,AEP))
        id_ = []
        increments = []
        timestep = []
        for aep_band in aep_bands:
            for i in range(len(self.ID)):
                if self.Duration[i] == duration and self.AEP_Band[i].lower() == aep_band.lower():
                    id_.append(self.ID[i])
                    increments.append(self.increments[i])
                    timestep.append(self.TimeStep[i])
        return id_, increments, timestep

    def figure_out_pb_dur(self, duration, preburst_pattern_dur, bpreburst_dur_proportional):
        if bpreburst_dur_proportional:
            dur = duration * float(preburst_pattern_dur)
        else:
            if re.findall(r"hr", preburst_pattern_dur, re.IGNORECASE):
                dur = float(preburst_pattern_dur.strip(' hr')) * 60.
            elif re.findall(r"min", preburst_pattern_dur, re.IGNORECASE):
                dur = float(preburst_pattern_dur.strip(' min'))
        return self.findClosestTP(dur)

    def get_dur_aep_pb(self, duration, aep_bands, preburst_pattern_method, preburst_pattern_dur,
                       preburst_pattern_tp, bpreburst_dur_proportional, aep_name):
        increments = []
        timestep = 0
        if preburst_pattern_method.lower() == "constant":
            if bpreburst_dur_proportional:
                dur = duration * float(preburst_pattern_dur)
            else:
                dur = float(preburst_pattern_dur) * 60.
            increments.append(100)
            timestep = dur
            self.logger.info("For complete storm {0} {1} min using constant preburst rate of {2} mins".format(aep_name, duration, dur))
        else:
            dur = self.figure_out_pb_dur(duration, preburst_pattern_dur, bpreburst_dur_proportional)
            self.logger.info("For complete storm {0} {1} min "
                             "using ARR Temporal pattern for preburst: {2} mins, {3}".format(aep_name, duration, dur,
                                                                                             preburst_pattern_tp))
            if preburst_pattern_tp == 'design_burst':
                preburst_pattern_tp = 'TP01'  # placeholder

            id, increments, timestep = self.get_dur_aep(dur, aep_bands)

            tp = int(re.findall(r"\d{2}", preburst_pattern_tp)[0])
            increments = increments[tp-1]
            timestep = timestep[tp-1]

        return increments, timestep

    def findClosestTP(self, dur):
        diff = 99999
        diff_prev = 99999
        d_prev = 0
        for d in self.Duration:
            diff = abs(dur - d)
            if diff > diff_prev:
                return d_prev
            else:
                diff_prev = diff
                d_prev = d

        return d_prev

    def get_durations(self, aep):
        # print ('Getting a list of durations with AEP band {0}'.format(AEP))
        duration_all = []
        for i in range(len(self.ID)):
            if self.AEP_Band[i] == aep.lower():
                duration_all.append(self.Duration[i])
        durations = sorted(set(duration_all))  # sorted, unique list
        return durations
    
    def getTemporalPatternDurations(self, all_durations):
        """Get unique list of durations"""
        
        durations = []
        for dur in all_durations:
            if dur not in durations:
                durations.append(dur)
        durations = sorted(set(durations))
        
        return durations
    
    def getExclusions(self, firstTP, secondTP):
        """Creates an exclusion list of temporal patterns based on the second list of TP i.e. anything not in
        secondTP greater than the minimum duration is counted as an exclusion.
        
        The reason is to find all temporal patterns that are missing from the areal temporal list not counting the
        short durations.
        
        Also returns list of all temporal patterns not counting short durations"""
        
        minDur = secondTP[0]
        i = firstTP.index(minDur)
        exclusion_list = []
        inclusion_list = []
        for dur in firstTP[i:]:
            inclusion_list.append(dur)
            if dur not in secondTP:
                exclusion_list.append(dur)

        return inclusion_list, exclusion_list
    
    def getTPCount(self):
        """Get temporal pattern count"""
        
        if self.Duration:
            dur = self.Duration[0]
            count = self.Duration.count(dur)
            self.tpCount = int(count / 3)

    def get_tp_number(self, tpid):
        i = self.ID.index(tpid)
        return self.TPNumber[i]

    def get_tp_increments(self, tp_number, duration, aep_bands, preburst_pattern_dur, bpreburst_dur_proportional):
        dur = self.figure_out_pb_dur(duration, preburst_pattern_dur, bpreburst_dur_proportional)
        id, increments, timestep = self.get_dur_aep(dur, aep_bands)
        return increments[tp_number - 1]


class Limb:

    def __init__(self):
        self.logger = logging.getLogger('ARR2019')
        self.has_limb = False
        self.ifd = Bom()

    def load(self, fi, limb_data):
        if limb_data == 'enveloped':
            source = 'LIMBifdenv'
        elif limb_data == 'high res':
            source = 'LIMBifdhr'
        elif limb_data == 'bom res':
            source = 'LIMBifdbom'
        else:
            self.logger.info('WARNING LIMB IFD type not recognised, defaulting to Enveloped')
            source = 'LIMBifdenv'

        durs = []
        aeps = []
        aep_names = []
        vals = []
        i = 0
        for line in fi:
            i += 1
            if '[{0}]'.format(source) in line:
                self.has_limb = True
                # collect AEP header info
                header = fi.readline().split(',')
                i += 1
                for x in header:
                    try:
                        aep = float(x)
                        aep_name = '{0}%'.format(x.strip())
                        aeps.append(aep)
                        aep_names.append(aep_name)
                    except ValueError:
                        continue
                continue
            elif '[{0}_META]'.format(source) in line or '[END_{0}]'.format(source) in line:
                self.ifd.loaded = True
                break
            if not self.has_limb:
                continue
            data = line.split(',')
            try:
                dur = data[0].split('(')[0].strip()
            except IndexError:
                self.ifd.error = True
                self.ifd.message = 'Error splitting LIMB IFD row: {0}, line: {1}'.format(i, line)
                break
            try:
                durs.append(int(dur))
            except ValueError:
                self.ifd.error = True
                self.ifd.message = 'Error converting LIMB IFD duration to integer: {0}, line: {1}'.format(i, line)
                break
            try:
                row = [float(x) for x in data[1:]]
            except (ValueError, IndexError):
                self.ifd.error = True
                self.ifd.message = 'Error converting LIMB IFD row to float: {0}, line: {1}'.format(i, line)
                break
            vals.append(row)

        self.ifd.aep = aeps
        self.ifd.aep_names = aep_names
        self.ifd.naep = len(aep_names)
        self.ifd.duration = durs
        self.ifd.ndur = len(durs)
        self.ifd.depths = numpy.array(vals)

        fi.seek(0)


# noinspection PyBroadException,PyBroadException,PyBroadException,PyBroadException,PyBroadException,PyBroadException
class Arr:
    def __init__(self):  # initialise the ARR class
        self.loaded = False
        self.error = False
        self.message = None
        self.Temporal = ArrTemporal()
        self.Input = ArrInput()
        self.RivReg = ArrRivReg()
        self.CCF = ArrCCF()
        self.PreBurst = ArrPreburst()
        self.Losses = ArrLosses()
        self.Arf = ArrArf()
        self.Limb = Limb()
        self.logger = logging.getLogger('ARR2019')
        self.settings = ArrSettings.get_instance()

    def load(self, fname, area, **kwargs):
        
        # deal with kwargs
        add_tp = kwargs['add_tp'] if 'add_tp' in kwargs else None
        point_tp_csv = kwargs['point_tp'] if 'point_tp' in kwargs else None
        areal_tp_csv = kwargs['areal_tp'] if 'areal_tp' in kwargs else None
        user_initial_loss = kwargs['user_initial_loss'] if 'user_initial_loss' in kwargs else None
        user_continuing_loss = kwargs['user_continuing_loss'] if 'user_continuing_loss' in kwargs else None
        areal_tp_download = kwargs['areal_tp_download'] if 'areal_tp_download' in kwargs else None
        limb_data = kwargs['limb_data'] if 'limb_data' in kwargs else None
        add_areal_tp = kwargs.get('add_areal_tp', 0)

        #print('Loading ARR website output .txt file')
        self.logger.info('Loading ARR website output .txt file')
        if not os.path.isfile(fname):
            self.error = True
            self.message = 'File does not exist {0}'.format(fname)
            return
        try:
            fi = open(fname, 'r')
        except IOError:
            #print('Unexpected error opening file {0}'.format(fname))
            self.logger.error('Unexpected error opening file {0}'.format(fname))
            raise Exception('Unexpected error opening file {0}'.format(fname))

        # INPUT DATA
        #print('Loading Input Data Block')
        self.logger.info('Loading Input Data Block')
        self.Input.load(fi)
        if self.Input.error:
            #print('An error was encountered, when reading Input Data Information.')
            self.logger.error('An error was encountered, when reading Input Data Information.')
            #print('Return message = {0}'.format(self.Input.message))
            self.logger.error('Return message = {0}'.format(self.Input.message))
            raise Exception("ERROR: {0}".format(self.Input.message))

        # RIVER REGION
        #print('Loading River Region Block')
        self.logger.info('Loading River Region Block')
        self.RivReg.load(fi)
        if self.RivReg.error:
            #print('An error was encountered, when reading River Region Information.')
            self.logger.error('An error was encountered, when reading River Region Information.')
            #print('Return message = {0}'.format(self.RivReg.message))
            self.logger.error('Return message = {0}'.format(self.RivReg.message))
            raise Exception("ERROR: {0}".format(self.RivReg.message))

        # ARF
        #print('Loading ARF block')
        self.logger.info('Loading ARF block')
        self.Arf.load(fi)
        if self.Arf.error:
            #print('An error was encountered, when reading ARF information.')
            self.logger.error('An error was encountered, when reading ARF information.')
            #print('Return message = {0}'.format(self.Arf.message))
            self.logger.error('Return message = {0}'.format(self.Arf.message))
            raise Exception("ERROR: {0}".format(self.Arf.message))

        # STORM LOSSES
        #print('Loading Storm Losses Block')
        self.logger.info('Loading Storm Losses Block')
        self.Losses.load(fi)
        if self.Losses.error:
            #print('An error was encountered, when reading Storm Losses Information.')
            self.logger.error('An error was encountered, when reading Storm Losses Information.')
            #print('Return message = {0}'.format(self.Losses.message))
            self.logger.error('Return message = {0}'.format(self.Losses.message))
        if user_initial_loss is not None:
            self.Losses.applyUserInitialLoss(user_initial_loss)
        if user_continuing_loss is not None:
            self.Losses.applyUserContinuingLoss(user_continuing_loss)
            

        # INTERIM CLIMATE CHANGE FACTOR
        #print('Loading Interim Climate Change Factors Block')
        self.logger.info('Loading Interim Climate Change Factors Block')
        self.CCF.load(fi)
        if self.CCF.error:
            #print('An error was encountered, when reading Interim Climate Change Factors Information.')
            self.logger.error('An error was encountered, when reading Interim Climate Change Factors Information.')
            #print('Return message = {0}'.format(self.CCF.message))
            self.logger.error('Return message = {0}'.format(self.CCF.message))
            raise Exception("ERROR: {0}".format(self.CCF.message))

        # TEMPORAL PATTERNS
        #print('Loading Temporal Patterns')
        self.logger.info('Loading Temporal Patterns')
        tpRegion = self.temporalPatternRegion(fi)
        if tpRegion == 'Rangelands West And Rangelands':
            areal_tp_download = None
        self.Temporal.load(fname, fi, tpRegion, point_tp_csv, areal_tp_csv, areal_tp_download)
        if self.Temporal.error:
            #print('An error was encountered, when reading temporal patterns.')
            self.logger.error('An error was encountered, when reading temporal patterns.')
            #print('Return message = {0}'.format(self.Temporal.message))
            self.logger.error('Return message = {0}'.format(self.Temporal.message))
            raise Exception("ERROR: {0}".format(self.Temporal.message))
        if add_tp:
            for tp in add_tp:
                f = "{0}_TP_{1}.txt".format(os.path.splitext(fname)[0], tp)
                fadd_tp = open(f, 'r')
                self.Temporal.append(fadd_tp)
                fadd_tp.close()
                tpCode = self.arealTemporalPatternCode(f)
                f = os.path.join(os.path.dirname(f), "Areal_{0}_Increments.csv".format(tpCode))
                if os.path.exists(f):
                    self.Temporal.loadArealTpFromCSV(f)
                if self.Temporal.error:
                    #print('An error was encountered, when reading temporal pattern: {0}'.format(tp))
                    self.logger.error('An error was encountered, when reading temporal pattern: {0}'.format(tp))
                    #print('Return message = {0}'.format(self.Temporal.message))
                    self.logger.error('Return message = {0}'.format(self.Temporal.message))
                    raise Exception("ERROR: {0}".format(self.Temporal.message))

        self.Temporal.combineArealTp(area)
        for i in range(add_areal_tp):
            added = self.Temporal.addArealTP(area, i)
            if added:
                self.Temporal.add_areal_tp += 1
        if add_areal_tp > self.Temporal.add_areal_tp:
            self.logger.warning('WARNING: Limiting number of additional areal temporal patterns to {0}'.format(self.Temporal.add_areal_tp))

        # PREBURST DEPTH
        #print('Loading median preburst data')
        self.logger.info('Loading median preburst data')
        self.PreBurst.load(fi, self.settings.preburst_percentile)
        if self.PreBurst.error:
            #print('An error was encountered, when reading median preburst data.')
            self.logger.error('An error was encountered, when reading median preburst data.')
            #print('Return message = {0}'.format(self.PreBurst.message))
            self.logger.error('Return message = {0}'.format(self.PreBurst.message))

        # LIMB data
        if limb_data is not None:
            self.logger.info('Loading LIMB data: {0}'.format(limb_data))
            self.Limb.load(fi, limb_data)
            if not self.Limb.has_limb:
                self.logger.info('No LIMB data found')
            if self.Limb.has_limb and self.Limb.ifd.error:
                self.logger.error(self.Limb.ifd.message)
            if self.Limb.has_limb and not self.Limb.ifd.error:
                self.logger.info('Finished loading LIMB data')

        #print('Data Loaded')
        self.logger.info('Data Loaded')

    def export(self, fpath, aep, dur, **kwargs):
        """Process and export ARR2016 data"""

        # deal with kwargs
        out_form = kwargs['format'] if 'format' in kwargs else 'csv'
        site_name = kwargs['name'] if 'name' in kwargs else 'name'
        cc = kwargs['climate_change'] if 'climate_change' in kwargs else False
        cc_years = kwargs['climate_change_years'] if 'climate_change_years' in kwargs else [2090]
        cc_RCP = kwargs['cc_rcp'] if 'cc_rcp' in kwargs else ['RCP8.5']
        cc_param = kwargs.get('cc_param', {})
        bom = kwargs['bom_data'] if 'bom_data' in kwargs else None
        catchment_area = kwargs['area'] if 'area' in kwargs else 0
        frequent_events = kwargs['frequent'] if 'frequent' in kwargs else False
        rare_events = kwargs['rare'] if 'rare' in kwargs else False
        catch_no = kwargs['catch_no'] if 'catch_no' in kwargs else 0
        out_notation = kwargs['out_notation'] if 'out_notation' in kwargs else 'aep'
        ARF_frequent = kwargs['arf_frequent'] if 'arf_frequent' in kwargs else True
        min_ARF = kwargs['min_arf'] if 'min_arf' in kwargs else 0
        preBurst = kwargs['preburst'] if 'preburst' in kwargs else '50%'
        lossMethod = kwargs['lossmethod'] if 'lossmethod' in kwargs else 'interpolate'
        mar = kwargs['mar'] if 'mar' in kwargs else 1500
        staticLoss = kwargs['staticloss'] if 'staticloss' in kwargs else 0
        add_tp = kwargs['add_tp'] if 'add_tp' else []
        tuflow_loss_method = kwargs['tuflow_loss_method'] if 'tuflow_loss_method' in kwargs else 'infiltration'
        urban_initial_loss = kwargs['urban_initial_loss'] if 'urban_initial_loss' in kwargs else None
        urban_continuing_loss = kwargs['urban_continuing_loss'] if 'urban_continuing_loss' in kwargs else None
        probability_neutral_losses = kwargs['probability_neutral_losses'] if 'probability_neutral_losses' in kwargs else True
        bComplete_storm = kwargs['use_complete_storm'] if 'use_complete_storm' in kwargs else False
        preburst_pattern_method = kwargs['preburst_pattern_method'] if 'preburst_pattern_method' else 'Constant Rate'
        preburst_pattern_dur = kwargs['preburst_pattern_dur'] if 'preburst_pattern_dur' else None
        preburst_pattern_tp = kwargs['preburst_pattern_tp'] if 'preburst_pattern_tp' else None
        bpreburst_dur_proportional = kwargs['preburst_dur_proportional'] if 'preburst_dur_proportional' else False
        use_global_continuing_loss = kwargs['use_global_continuing_loss'] if 'use_global_continuing_loss' else False
        all_point_tp = kwargs.get('all_point_tp', False)

        # convert input RCP if 'all' is specified
        if str(cc_RCP).lower() == 'all':
            cc_RCP = ['RCP4.5', 'RCP6', 'RCP8.5']
        # convert cc years if 'all' is specified
        if str(cc_years).lower() == 'all':
            cc_years = self.CCF.Year

        # overwrite BOM rainfall data with LIMB data
        if self.Limb.has_limb and not self.Limb.ifd.error:
            min_dur, max_dur = min(self.Limb.ifd.duration), max(self.Limb.ifd.duration)
            min_aep_, max_aep_ = max(self.Limb.ifd.aep), min(self.Limb.ifd.aep)
            min_aep = self.Limb.ifd.aep_names[self.Limb.ifd.aep.index(min_aep_)]
            max_aep = self.Limb.ifd.aep_names[self.Limb.ifd.aep.index(max_aep_)]
            self.logger.info('CHECK: Overwriting BOM data with LIMB data where available.\n'
                             'Data outside of LIMB range (min dur = {0} min, max dur = {1} min, min aep = {2}, max aep = {3})\n'
                             'will adopt BOM values. Values not listed in LIMB data but within the data range '
                             'will be interpolated from the LIMB data.'.format(min_dur, max_dur, min_aep, max_aep))
            bom_ = bom
            bom = self.Limb.ifd

            # note 12EY does not equal 99.9% AEP, but this need a value and needs to have the highest value so 99.9 used as dummy value
            conv2aep = {'12EY': 99.9, '6EY': 99.75, '4EY': 98.17, '3EY': 95.02, '2EY': 86.47, '1EY': 63.23,
                        '0.5EY': 39.35, '0.2EY': 18.13, '1 in 200': 0.5, '1 in 500': 0.2, '1 in 1000': 0.1,
                        '1 in 2000': 0.05, '63.2%': 63.23}

            # order bom aeps correctly from frequent to extreme
            bom_aeps = []
            bom_aep2aep_name = {}
            bom_aep2aep = {}
            for i, aep_name in enumerate(bom_.aep_names):
                if aep_name in conv2aep:
                    bom_aeps.append(conv2aep[aep_name])
                else:
                    bom_aeps.append(bom_.aep[i])
                bom_aep2aep_name[bom_aeps[-1]] = aep_name
                bom_aep2aep[bom_aeps[-1]] = bom_.aep[i]
            ind = list(reversed(numpy.argsort(bom_aeps)))
            bom_aeps = numpy.array(bom_aeps)[ind].tolist()
            bom_.aep = numpy.array(bom_.aep)[ind].tolist()
            bom_.aep_names = numpy.array(bom_.aep_names)[ind].tolist()
            bom_.depths = bom_.depths[:,ind]

            # keep copy of original data
            self.Limb.ifd.depths_ = self.Limb.ifd.depths
            self.Limb.ifd.duration_ = self.Limb.ifd.duration
            self.Limb.ifd.aep_ = self.Limb.ifd.aep
            self.Limb.ifd.aep_names_ = self.Limb.ifd.aep_names

            depths = []
            durs = []
            aeps = []
            aep_names = []
            aep_ids = []
            for i, dur_ in enumerate(bom_.duration):
                row = []
                for j, aep_ in enumerate(bom_aeps):
                    if aep_ < max_aep_ or aep_ > min_aep_:
                        if dur_ not in self.Limb.ifd.duration:
                            continue
                        row.append(bom_.depths[i,j])
                        if dur_ not in durs:
                            durs.append(dur_)
                        aep__ = bom_.aep[j]
                        if aep_ not in aep_ids:
                            aeps.append(aep__)
                            aep_ids.append(aep_)
                            aep_name = bom_.aep_names[j]
                            aep_names.append(aep_name)
                    elif dur_ in self.Limb.ifd.duration and aep_ in self.Limb.ifd.aep:
                        i_ = self.Limb.ifd.duration.index(dur_)
                        j_ = self.Limb.ifd.aep.index(aep_)
                        row.append(self.Limb.ifd.depths[i_,j_])
                        if dur_ not in durs:
                            durs.append(dur_)
                        if aep_ not in aep_ids:
                            aeps.append(bom_aep2aep[aep_])
                            aep_ids.append(aep_)
                            aep_name = bom_aep2aep_name[aep_]
                            aep_names.append(aep_name)
                if row:
                    depths.append(row)

            # set new values but keep old values for record
            self.Limb.ifd.depths = numpy.array(depths)
            self.Limb.ifd.duration = durs
            self.Limb.ifd.aep = aeps
            self.Limb.ifd.aep_names = aep_names

            depths = []
            durs = []
            aeps = []
            aep_names = []
            aep_aep = []
            aep_ids = []
            for i, aep_name in enumerate(self.Limb.ifd.aep_names):
                if aep_name in conv2aep:
                    aep_aep.append(conv2aep[aep_name])
                else:
                    aep_aep.append(self.Limb.ifd.aep[i])
            for i, dur_ in enumerate(bom_.duration):
                row = []
                for j, aep_ in enumerate(bom_aeps):
                    if dur_ < min_dur or dur_ > max_dur:
                        if aep_ not in aep_aep:
                            continue
                        row.append(bom_.depths[i, j])
                        if dur_ not in durs:
                            durs.append(dur_)
                        aep__ = bom_.aep[j]
                        if aep_ not in aep_ids:
                            aeps.append(aep__)
                            aep_ids.append(aep_)
                            aep_name = bom_.aep_names[j]
                            aep_names.append(aep_name)
                    elif dur_ in self.Limb.ifd.duration and aep_ in aep_aep:
                        i_ = self.Limb.ifd.duration.index(dur_)
                        j_ = aep_aep.index(aep_)
                        row.append(self.Limb.ifd.depths[i_, j_])
                        if dur_ not in durs:
                            durs.append(dur_)
                        try:
                            aep__ = self.Limb.ifd.aep[j_]
                        except IndexError:
                            print('here')
                        if aep_ not in aep_ids:
                            aeps.append(aep__)
                            aep_ids.append(aep_)
                            aep_name = self.Limb.ifd.aep_names[j_]
                            aep_names.append(aep_name)
                depths.append(row)

            # set new values but keep old values for record
            self.Limb.ifd.depths = numpy.array(depths)
            self.Limb.ifd.duration = durs
            self.Limb.ifd.aep = aeps
            self.Limb.ifd.aep_names = aep_names
            self.Limb.ifd.ndur = len(durs)
            self.Limb.ifd.naep = len(aeps)

        # new stuff that can be used for future development
        depths = pd.DataFrame(bom.depths, columns=bom.aep_names, index=bom.duration)
        depths_adj = depths.copy()  # ARF applied (not yet though)
        if self.Losses.existsPNLosses and probability_neutral_losses:
            self.Losses.cont_loss = self.Losses.cls
        if self.Losses.ils_user is not None:
            self.Losses.init_loss = float(self.Losses.ils_user)
        if self.Losses.cls_user is not None:
            self.Losses.cont_loss = float(self.Losses.cls_user)

        # create year dictionary with index as the value so the appropriate multiplier can be called from self.CCF
        # later on
        tpCount = self.Temporal.tpCount
        #if add_tp != False:
        #    tpCount = 10 + 10 * len(add_tp)
        #else:
        #    tpCount = 10
        cc_years_dict = {}
        for i, year in enumerate(self.CCF.Year):
            if year in cc_years:
                cc_years_dict[year] = i

        # create list of climate change events multiply by 10 for each temporal pattern
        cc_events = []
        if self.CCF.meta.version > 2024000:
            for key in cc_param:
                for i in range(tpCount):
                    cc_events.append(key)
        else:
            for year in cc_years:
                for rcp in cc_RCP:
                    for i in range(tpCount):
                        cc_events.append('{0:.0f}_{1}'.format(year, rcp[3:]))

        # convert input AEP to list
        aep_list = []
        if str(aep).lower() == 'all':
            conversion = {'1 in 2000': '0.05%', '1 in 1000': '0.1%', '1 in 500': '0.2%', '1 in 200': '0.5%'}
            aep_list = []
            for aep in bom.aep_names:
                if aep in conversion.keys():
                    aep_list.append(conversion[aep])
                else:
                    aep_list.append(aep)
        else:
            for mag, unit in aep.items():
                aep_list.append(convertMagToAEP(mag, unit, frequent_events))

        # House Keeping: Order list based on high AEP to low AEP
        aep_map = {'0.05%': 1, '0.1%': 2, '0.2%': 3, '0.5%': 4, '1%': 5, '2%': 6, '5%': 7, '10%': 8,
                   '20%': 9, '50%': 10, '63.2%': 11, '0.2EY': 12, '0.5EY': 13, '2EY': 14, '3EY': 15, '4EY': 16,
                   '6EY': 17, '12EY': 18}
        ari_map = {'0.05%': 1, '0.1%': 2, '0.2%': 3, '0.5%': 4, '1%': 5, '2%': 6, '5%': 7, '10%': 8, '0.2EY': 9,
                   '20%': 10, '0.5EY': 11, '50%': 12, '63.2%': 13, '2EY': 14, '3EY': 15, '4EY': 16,
                   '6EY': 17, '12EY': 18}
        if out_notation == 'ari':
            aep_list = sorted(aep_list, key=lambda k: ari_map[k])
        else:
            aep_list = sorted(aep_list, key=lambda k: aep_map[k])

        # convert input duration
        all_duration = False
        if str(dur).lower() == 'all':
            all_duration = True
        else:
            dur_list = []
            for mag, unit in dur.items():
                if unit[0].lower() == 's':
                    dur_list.append(int(mag / 60))
                elif unit[0].lower() == 'm':
                    dur_list.append(int(mag))
                elif unit[0].lower() == 'h':
                    dur_list.append(int(mag * 60))
                elif unit[0].lower() == 'd':
                    dur_list.append(int(mag * 60 * 24))
                else:
                    self.error = True
                    self.message = 'Not a valid duration unit: {0}'.format(unit.lower())
        dur_list.sort()

        # write out Areal Reduction Factors and rainfall depths with ARF applied
        if self.Arf.loaded and catchment_area > 1.0 or self.Limb.has_limb and not self.Limb.ifd.error:
            if catchment_area > 1.0:
                arf_array = arf_factors(catchment_area, bom.duration, bom.aep_names,
                                        self.Arf.param['a'],
                                        self.Arf.param['b'],
                                        self.Arf.param['c'],
                                        self.Arf.param['d'],
                                        self.Arf.param['e'],
                                        self.Arf.param['f'],
                                        self.Arf.param['g'],
                                        self.Arf.param['h'],
                                        self.Arf.param['i'], ARF_frequent, min_ARF)
                arf_file = os.path.join(fpath, 'data', '{0}_ARF_Factors.csv'.format(site_name))
                if not os.path.exists(os.path.dirname(arf_file)):  # check output directory exists
                    os.mkdir(os.path.dirname(arf_file))
                try:
                    arf_file_open = open(arf_file, 'w')
                except IOError:
                    self.error = True
                    self.message = 'Unexpected error opening file {0}'.format(arf_file)
                    return
                arf_file_open.write(
                    'This file has been generated using ARR_to_TUFLOW. Areal Reducation Factors have been calculated '
                    'based on equations from ARR2016 using parameters extracted from the ARR datahub.\n')
                arf_file_open.write('Duration (mins), {0}\n'.format(",".join(map(str, bom.aep_names))))
                for i in range(len(bom.duration)):
                    arf_file_open.write(
                        '{0}, {1}\n'.format(bom.duration[i], ",".join(map(str, arf_array[i].tolist()))))
                arf_file_open.write('\n\n**WARNING: Minimum ARF value has been set at {0}'.format(min_ARF))
                arf_file_open.flush()
                arf_file_open.close()
                neg_arf = float((arf_array < 0).sum())  # total number of negative entries
                if ARF_frequent:
                    if '63.2%' in aep_list or frequent_events:
                        #print('WARNING: ARF being applied to frequent events is outside recommended '
                        #      'bounds (50% - 0.05%)')
                        self.logger.warning('WARNING: ARF being applied to frequent events is outside recommended '
                                            'bounds (50% - 0.05%)')
                if neg_arf > 0:
                    #print('WARNING: {0:.0f} ARF entries have a negative value. ' \
                    #      'Check "Rainfall_ARF_Factors.csv" output.'.format(neg_arf))
                    self.logger.warning('WARNING: {0:.0f} ARF entries have a negative value. ' \
                                        'Check "Rainfall_ARF_Factors.csv" output.'.format(neg_arf))
                # Save Figure
                fig_name = os.path.join(fpath, 'data', '{0}_ARF_Factors.png'.format(site_name))
                make_figure(fig_name, bom.duration, arf_array, 1, 10000, 0, 1.2, 'Duration (mins)', 'ARF',
                            'ARF Factors: {0}'.format(site_name), bom.aep_names, xlog=True)

                # multiply rainfall by ARF
                bom.depths = numpy.multiply(bom.depths, arf_array)

                depths_adj = depths_adj * arf_array

                # write out rainfall depths
            f_arf_depths = os.path.join(fpath, 'data', 'BOM_Rainfall_Depths_{0}.csv'.format(site_name))
            try:
                fo_arf_depths = open(f_arf_depths, 'w')
            except IOError:
                self.error = True
                self.message = 'Unexpected error opening file {0}'.format(f_arf_depths)
                return
            fo_arf_depths.write(
                'This file has been generated using ARR_to_TUFLOW. Areal Reduction Factors have been applied to '
                'the rainfall depths using ARR2016. For applied ARF values please view "Rainfall_ARF_Factors.csv"\n')
            # if neg_depths > 0:
            #    fo_arf_depths.write('WARNING: negative depths have been set to zero.\n')
            neg_depths = 0
            fo_arf_depths.write('Duration (mins), {0}\n'.format(",".join(map(str, bom.aep_names))))
            for i, dur in enumerate(bom.duration):
                line = '{0}'.format(dur)
                for j in range(bom.naep):
                    if numpy.isnan(bom.depths[i, j]):
                        line = line + ',-'
                    elif bom.depths[i, j] < 0:
                        line = line + ',0'
                        neg_depths += 1
                    else:
                        line = line + ',{0:.1f}'.format(bom.depths[i, j])
                line = line + '\n'
                fo_arf_depths.write(line)
            if neg_depths > 0:
                fo_arf_depths.write('\n**WARNING: negative depths have been set to zero.')
                #print('WARNING: {0} negative rainfall depths have occured, caused by negative ARF values. ' \
                #      'Negative depth values have been set to zero.'.format(neg_depths))
                self.logger.warning('WARNING: {0} negative rainfall depths have occured, caused by negative ARF values. ' \
                                    'Negative depth values have been set to zero.'.format(neg_depths))
            fo_arf_depths.flush()
            fo_arf_depths.close()

            # Save figure
            fig_name = os.path.join(fpath, 'data', 'BOM_Rainfall_Depths_{0}.png'.format(site_name))
            ymax = 10 ** math.ceil(math.log10(numpy.nanmax(bom.depths)))
            ymin = 10 ** math.floor(math.log10(numpy.nanmin(bom.depths))) if numpy.nanmin(bom.depths) > 0. else 0.001
            make_figure(fig_name, bom.duration, bom.depths, 1, 10000, ymin, ymax, 'Duration (mins)', 'Depth (mm)',
                        'Design Rainfall Depths: {0}'.format(site_name), bom.aep_names, loglog=True)
        else:
            #print('Catchment area less than 1 km2, ignoring ARF factors.')
            self.logger.info('Catchment area less than 1 km2, ignoring ARF factors.')

        # write out climate change data
        if cc:
            if (self.CCF.meta.version < 2024000 and len(cc_param) > 0) or (self.CCF.meta.version > 2024000 and len(cc_RCP) > 0):
                self.logger.error('Requested climate change scenarios do not match ARR datahub version.')
                raise Exception('Requested climate change scenarios do not match ARR datahub version.')

            if self.CCF.meta.version > 2024000:
                out_dir = Path(fpath) / 'data'
                for name, param in cc_param.items():
                    self.CCF.add_scenario(name, param)
                    self.CCF.calc_rainfall_depths(name, depths_adj)
                    self.CCF.write_rainfall_to_file(name, out_dir)

            else:  # old version
                if len(cc_years) < 1:
                    #print('No year(s) specified when considering climate change.')
                    self.logger.error('No year(s) specified when considering climate change.')
                    raise Exception('ERROR: no year(s) specified in Climate Change consideration')
                if len(cc_RCP) < 1:
                    #print('No RCP(s) specified when considering climate change.')
                    self.logger.error('No RCP(s) specified when considering climate change.')
                    raise Exception('ERROR: no RCP(s) specified in Climate Change consideration.')
                for year, k in cc_years_dict.items():
                    # j is year index of year in self.CCF.Year so multiplier can be extracted
                    if year not in self.CCF.Year:
                        #print('Climate change year ({0}) not recognised, or not a valid year.'.format(year))
                        self.logger.error('Climate change year ({0}) not recognised, or not a valid year.'.format(year))
                        raise Exception('ERROR: Climate change year ({0}) not recognised, or not a valid year.'.format(year))
                    for rcp in cc_RCP:
                        if rcp == 'RCP4.5':
                            cc_multip = (self.CCF.RCP4p5[k] / 100) + 1
                        elif rcp == 'RCP6':
                            cc_multip = (self.CCF.RCP6[k] / 100) + 1
                        elif rcp == 'RCP8.5':
                            cc_multip = (self.CCF.RCP8p5[k] / 100) + 1
                        else:
                            #print('Climate change RCP ({0}) not recognised, or valid.'.format(rcp))
                            self.logger.error('Climate change RCP ({0}) not recognised, or valid.'.format(rcp))
                            raise Exception("ERROR: Climate change RCP ({0}) not recognised, or valid".format(rcp))

                        # start by writing out climate change rainfall depths
                        cc_depths = bom.depths * cc_multip
                        cc_file = 'BOM_Rainfall_Depths_{0}_{1}_{2}.csv'.format(site_name, year, rcp)
                        cc_file_out = os.path.join(fpath, 'data', cc_file)
                        cc_file_open = open(cc_file_out, 'w')
                        cc_file_open.write(
                            'This file has been generated using ARR_to_TUFLOW. Climate Change rainfall '
                            'depths have been calculated based on Climate Change Factors '
                            'extracted from the ARR datahub for {0} and {1}.\n'.format(year, rcp))
                        cc_file_open.write('Duration (mins),{0}\n'.format(",".join(map(str, bom.aep_names))))
                        for i, dur in enumerate(bom.duration):
                            line = '{0}'.format(dur)
                            for j in range(bom.naep):
                                if numpy.isnan(bom.depths[i, j]):
                                    line = line + ',-'
                                else:
                                    line = line + ',{0:.1f}'.format(cc_depths[i, j])
                            line = line + '\n'
                            cc_file_open.write(line)
                        cc_file_open.flush()
                        cc_file_open.close()

                        # Save Figure
                        fig_name = os.path.join(fpath, 'data',
                                                'BOM_Rainfall_Depths_{0}_{1}_{2}.png'.format(site_name, year, rcp))
                        ymax = 10 ** math.ceil(math.log10(numpy.nanmax(cc_depths)))
                        ymin = 10 ** math.floor(math.log10(numpy.nanmin(cc_depths))) if numpy.nanmin(cc_depths) > 0. else 0.001
                        make_figure(fig_name, bom.duration, cc_depths, 1, 10000, ymin, ymax, 'Duration (mins)', 'Depth (mm)',
                                    'Design Rainfall Depths: {0}_{1}_{2}.csv'.format(site_name, year, rcp), bom.aep_names,
                                    loglog=True)

        # initialise unique durations and AEPs to export to control files
        exported_aep = []
        exported_dur = []
        ari_conv = {'63.2%': '1y', '50%': '1.4y', '20%': '4.5y', '10%': '10y', '5%': '20y', '2%': '50y', '1%': '100y',
                    '0.5EY': '2y', '0.2EY': '5y', '0.5%': '200y', '0.2%': '500y', '0.1%': '1000y', '0.05%': '2000y'}

        # format dur list
        max_dur = max(dur_list)
        dur_list_formatted = []
        if max_dur == 10080:
            for dur in dur_list:
                dur_list_formatted.append('{0:05d}'.format(dur))
        elif max_dur in [1080, 1440, 1800, 2160, 2880, 4320, 5760, 7200, 8640]:
            for dur in dur_list:
                dur_list_formatted.append('{0:04d}'.format(dur))
        elif max_dur in [120, 180, 270, 360, 720]:
            for dur in dur_list:
                dur_list_formatted.append('{0:03d}'.format(dur))
        else:
            for dur in dur_list:
                dur_list_formatted.append('{0:02d}'.format(dur))

        # format aep list
        aep_list_formatted = []
        if out_notation == 'aep':
            if '0.05%' in aep_list:
                decimal_places = 2
            elif '0.5EY' in aep_list or '0.2EY' in aep_list or '0.1%' in aep_list or '0.2%' in aep_list \
                    or '0.5%' in aep_list or '63.2%' in aep_list:
                decimal_places = 1
            else:
                decimal_places = 0
            if '12EY' in aep_list or '63.2%' in aep_list or '50%' in aep_list or '20%' in aep_list or '10%' in aep_list:
                padding = 2
            else:
                padding = 1
            for aep in aep_list:
                if padding == 2 and decimal_places == 2:
                    if aep[-1] == '%':
                        aep_list_formatted.append('{0:05.2f}p'.format(float(aep[:-1])))
                    else:
                        aep_list_formatted.append('{0:05.2f}e'.format(float(aep[:-2])))
                elif padding == 2 and decimal_places == 1:
                    if aep[-1] == '%':
                        aep_list_formatted.append('{0:04.1f}p'.format(float(aep[:-1])))
                    else:
                        aep_list_formatted.append('{0:04.1f}e'.format(float(aep[:-2])))
                elif padding == 2 and decimal_places == 0:
                    if aep[-1] == '%':
                        aep_list_formatted.append('{0:02.0f}p'.format(float(aep[:-1])))
                    else:
                        aep_list_formatted.append('{0:02.0f}e'.format(float(aep[:-2])))
                elif padding == 1 and decimal_places == 2:
                    if aep[-1] == '%':
                        aep_list_formatted.append('{0:.2f}p'.format(float(aep[:-1])))
                    else:
                        aep_list_formatted.append('{0:.2f}e'.format(float(aep[:-2])))
                elif padding == 1 and decimal_places == 1:
                    if aep[-1] == '%':
                        aep_list_formatted.append('{0:.1f}p'.format(float(aep[:-1])))
                    else:
                        aep_list_formatted.append('{0:.1f}e'.format(float(aep[:-2])))
                else:
                    if aep[-1] == '%':
                        aep_list_formatted.append('{0:.0f}p'.format(float(aep[:-1])))
                    else:
                        aep_list_formatted.append('{0:.0f}e'.format(float(aep[:-2])))
        else:
            if '0.5EY' in aep_list or '0.2EY' in aep_list or '50%' in aep_list or '20%' in aep_list:
                decimal_places = 1
            else:
                decimal_places = 0
            if '0.05%' in aep_list or '0.1%' in aep_list:
                padding = 4
            elif '0.2%' in aep_list or '0.5%' in aep_list or '1%' in aep_list:
                padding = 3
            elif '2%' in aep_list or '5%' in aep_list or '10%' in aep_list:
                padding = 2
            else:
                padding = 1
            for aep in aep_list:
                if padding == 4 and decimal_places == 1:
                    if aep[-1] == '%':
                        aep_list_formatted.append('{0:06.1f}y'.format(float(ari_conv[aep][:-1])))
                    else:
                        aep_list_formatted.append('{0:06.1f}e'.format(float(aep[:-2])))
                elif padding == 4 and decimal_places == 0:
                    if aep[-1] == '%':
                        aep_list_formatted.append('{0:04.0f}y'.format(float(ari_conv[aep][:-1])))
                    else:
                        aep_list_formatted.append('{0:04.0f}e'.format(float(aep[:-2])))
                elif padding == 3 and decimal_places == 1:
                    if aep[-1] == '%':
                        aep_list_formatted.append('{0:05.1f}y'.format(float(ari_conv[aep][:-1])))
                    else:
                        aep_list_formatted.append('{0:05.1f}e'.format(float(aep[:-2])))
                elif padding == 3 and decimal_places == 0:
                    if aep[-1] == '%':
                        aep_list_formatted.append('{0:03.0f}y'.format(float(ari_conv[aep][:-1])))
                    else:
                        aep_list_formatted.append('{0:03.0f}e'.format(float(aep[:-2])))
                elif padding == 2 and decimal_places == 1:
                    if aep[-1] == '%':
                        aep_list_formatted.append('{0:04.1f}y'.format(float(ari_conv[aep][:-1])))
                    else:
                        aep_list_formatted.append('{0:04.1f}e'.format(float(aep[:-2])))
                elif padding == 2 and decimal_places == 0:
                    if aep[-1] == '%':
                        aep_list_formatted.append('{0:02.0f}y'.format(float(ari_conv[aep][:-1])))
                    else:
                        aep_list_formatted.append('{0:02.0f}e'.format(float(aep[:-2])))
                elif padding == 1 and decimal_places == 1:
                    if aep[-1] == '%':
                        aep_list_formatted.append('{0:.1f}y'.format(float(ari_conv[aep][:-1])))
                    else:
                        aep_list_formatted.append('{0:.1f}e'.format(float(aep[:-2])))
                else:
                    if aep[-1] == '%':
                        aep_list_formatted.append('{0:.0f}y'.format(float(ari_conv[aep][:-1])))
                    else:
                        aep_list_formatted.append('{0:.0f}e'.format(float(aep[:-2])))

        # Initial Losses
        if self.Losses.existsPNLosses and probability_neutral_losses:  # use probability neutral initial losses if they exist
            # generate same size array between rainfall depths and initial losses
            b_com_aep, b_com_dur, b_dep_com, b_com_dur_index = common_data(bom.aep_names, bom.duration,
                                                                           self.Losses.AEP_names,
                                                                           self.Losses.Duration,
                                                                           bom.depths)
            ilb_complete = extend_array_dur(b_com_dur_index, b_com_aep, self.Losses.ilpn,
                                            bom.duration)  # add all durations to array
            ilb_complete = interpolate_nan(ilb_complete, bom.duration, self.Losses.ils, lossMethod=lossMethod,
                                           mar=mar,
                                           staticLoss=staticLoss)
            # complete loss array to include all aeps (with nans)
            ilb_complete = extend_array_aep(b_com_aep, bom.aep_names, ilb_complete)

            # apply user IL
            if self.Losses.ils_user is not None:
                # if float(self.Losses.ils) < 0:
                if float(self.Losses.ils) > 0:
                    ilb_complete = ilb_complete * (float(self.Losses.ils_user) / float(self.Losses.ils))
                else:
                    self.logger.warning(
                        "WARNING: Cannot calculate initial losses from user input because Storm Initial loss is zero")

        else:  # original method of using preburst and storm loss
            # write out burst initial loss
            preBurst_depths = self.PreBurst.get_depths(self.Losses)
            # if preBurst == '10%':
            #     preBurst_depths = self.PreBurst.Depths10
            #     preBurst_ratios = self.PreBurst.Ratios10
            # elif preBurst == '25%':
            #     preBurst_depths = self.PreBurst.Depths25
            #     preBurst_ratios = self.PreBurst.Ratios25
            # elif preBurst == '50%':
            #     preBurst_depths = self.PreBurst.Depths50
            #     preBurst_ratios = self.PreBurst.Ratios50
            # elif preBurst == '75%':
            #     preBurst_depths = self.PreBurst.Depths75
            #     preBurst_ratios = self.PreBurst.Ratios75
            # elif preBurst == '90%':
            #     preBurst_depths = self.PreBurst.Depths90
            #     preBurst_ratios = self.PreBurst.Ratios90
            # else:
            #     preBurst_depths = self.PreBurst.Depths50
            #     preBurst_ratios = self.PreBurst.Ratios50


            # generate same size numpy arrays for burst and preburst data based on common AEPs and Durations
            b_com_aep, b_com_dur, b_dep_com, b_com_dur_index = common_data(bom.aep_names, bom.duration,
                                                                           self.PreBurst.AEP_names,
                                                                           self.PreBurst.Duration,
                                                                           bom.depths)
            pb_com_aep, pb_com_dur, pb_dep_com, pb_com_dur_index = common_data(self.PreBurst.AEP_names,
                                                                               self.PreBurst.Duration,
                                                                               bom.aep_names,
                                                                               bom.duration, preBurst_depths)
            # pb_com_aep, pb_com_dur, pb_rto_com, pb_com_dur_index = common_data(self.PreBurst.AEP_names,
            #                                                                    self.PreBurst.Duration,
            #                                                                    bom.aep_names,
            #                                                                    bom.duration, preBurst_ratios)

            # calculate the maximum preburst depths
            # pb_rto_d_com = numpy.multiply(b_dep_com, pb_rto_com)  # convert preburst ratios to depths
            # pb_dep_final = numpy.maximum(pb_dep_com, pb_rto_d_com)  # take the max of preburst ratios and depths
            pb_dep_final = pb_dep_com

            if lossMethod in ['interpolate_linear_preburst', 'interpolate_log_preburst']:
                if lossMethod == 'interpolate_linear_preburst':
                    self.logger.info('Using linear interpolation to extend pre-burst depths < 60 min')
                    pb_dep_final = linear_interp_pb_dep(pb_dep_final, bom.duration, b_com_dur_index)
                else:
                    self.logger.info('Using log-linear interpolation to extend pre-burst depths < 60 min')
                    pb_dep_final = log_interp_pb_dep(pb_dep_final, bom.duration, b_com_dur_index)
                b_com_dur_index = list(range(b_com_dur_index[0])) + b_com_dur_index  # update common duration index

            # calculate burst intial loss (storm il minus preburst depth)
            if type(self.Losses.ils) is str and 'nan' in self.Losses.ils.lower():
                self.logger.warning('WARNING: Initial loss value from Datahub is NaN')
                self.Losses.ils = 0
            if type(self.Losses.cls) is str and 'nan' in self.Losses.cls.lower():
                self.logger.warning('WARNING: Continuing loss value from Datahub is NaN')
                self.Losses.cls = 0
            if float(self.Losses.ils) == 0 and float(self.Losses.cls) == 0:
                # print('WARNING: No rainfall losses found.')
                self.logger.warning('WARNING: No rainfall losses found.')
            if float(self.Losses.ils) < 0:
                # print('WARNING: initial loss value is {0}'.format(self.Losses.ils))
                self.logger.warning('WARNING: initial loss value is {0}'.format(self.Losses.ils))
            if float(self.Losses.cls) < 0:
                # print('WARNING: continuing loss value is {0}'.format(self.Losses.cls))
                self.logger.warning('WARNING: continuing loss value is {0}'.format(self.Losses.cls))
            shape_com = pb_dep_final.shape  # array dimensions of preburst depths
            if self.Losses.ils_user is not None:
                ils = numpy.zeros(shape_com) + float(self.Losses.ils_user)  # storm initial loss array
            else:
                ils = numpy.zeros(shape_com) + float(self.Losses.ils)  # storm initial loss array

            ilb = numpy.add(ils, -pb_dep_final)  # burst initial loss (storm initial loss subtract preburst)

            # extend loss array to all durations using interpolation
            ilb_complete = extend_array_dur(b_com_dur_index, b_com_aep, ilb,
                                            bom.duration)  # add all durations to array
            ilb_complete = interpolate_nan(ilb_complete, bom.duration, self.Losses.ils, lossMethod=lossMethod,
                                           mar=mar,
                                           staticLoss=staticLoss)
            # complete loss array to include all aeps (with nans)
            ilb_complete = extend_array_aep(b_com_aep, bom.aep_names, ilb_complete)

        # extend pb array to all durations/AEP by reversing the calculation
        pb_dep_final_complete = numpy.add(float(self.Losses.ils), -ilb_complete)

        # save pre-burst values to csv and png
        fname_pb = '{0}_PreBurst_Depths.csv'.format(site_name)
        fname_pb_out = os.path.join(fpath, 'data', fname_pb)
        try:
            fpb = open(fname_pb_out, 'w')
        except PermissionError:
            self.logger.error("File is locked for editing {0}".format(fname_pb_out))
            raise Exception("ERROR: File is locked for editing {0}".format(fname_pb_out))
        except IOError:
            self.logger.error('Unexpected error opening file {0}'.format(fname_pb_out))
            raise Exception('ERROR: Unexpected error opening file {0}'.format(fname_pb_out))
        if lossMethod == 'interpolate_linear_preburst':
            loss_method_txt = 'linear interpolation of pre-burst depths assuming that the depth at 0 min is 0 mm'
        elif lossMethod == 'interpolate_log_preburst':
            loss_method_txt = 'log-linear interpolation of pre-burst depths assuming that the depth at 0 min is 0 mm'
        elif lossMethod == 'interpolate':
            loss_method_txt = 'linear interpolation of initial loss values assuming that the IL at 0 min is 0 mm'
        elif lossMethod == 'interpolate_log':
            loss_method_txt = 'log-linear interpolation of initial loss values assuming that the IL at 0 min is 0 mm'
        elif lossMethod == 'rahman':
            loss_method_txt = 'Rahman et al. 2002 method'
        elif lossMethod == 'hill':
            loss_method_txt = 'Hill et al. 1996: 1998 method with a Mean Annual Rainfall of {0} mm'.format(mar)
        elif lossMethod == 'static':
            loss_method_txt = 'a static initial loss of {0} mm'.format(staticLoss)
        elif lossMethod == '60min':
            loss_method_txt = 'the 60 min initial loss value'
        else:
            loss_method_txt = ''

        fpb.write('This file has been generated using ARR_to_TUFLOW. The PreBurst depths have been generated from '
                  'using the ARR datahub {0} pre-burst depths and using {1} to calculate pre-burst depths for durations'
                  ' less than 60 mins.\n'.format(preBurst, loss_method_txt))
        fpb.write('Duration (mins),{0}\n'.format(",".join(map(str, bom.aep_names))))
        for i, dur in enumerate(bom.duration):
            line = '{0}'.format(dur)
            for j in range(pb_dep_final_complete.shape[1]):
                if numpy.isnan(pb_dep_final_complete[i, j]):
                    line = line + ',-'
                else:
                    line = line + ',{0:.2f}'.format(pb_dep_final_complete[i, j])
            line = line + '\n'
            fpb.write(line)
        fpb.close()

        # Save Figure
        fig_name = os.path.join(fpath, 'data', '{0}_PreBurst_Depths.png'.format(site_name))
        ymax = math.ceil(numpy.nanmax(pb_dep_final_complete)) * 1.1
        xmax = 10 ** math.ceil(math.log10(max(b_com_dur)))
        ymin = math.floor(numpy.nanmin(pb_dep_final_complete) / 10.0) * 10

        make_figure(fig_name, bom.duration, pb_dep_final_complete, 1, xmax, ymin, ymax, 'Duration (mins)', 'Depth (mm)',
                    'Pre-burst Depths: {0}'.format(site_name), bom.aep_names, xlog=True)

        # add initial losses to climate change scenarios
        if cc:
            out_dir = Path(fpath) / 'data'
            for name in cc_param:
                self.CCF.calc_rainfall_losses(name, self.Losses.init_loss, self.Losses.cont_loss, ilb_complete, self.Temporal.tp_region)
                self.CCF.write_losses_to_file(name, out_dir)

        # copy ilb_complete incase complete storm is used later on - change values in routine further down as required
        il_complete = numpy.copy(ilb_complete)

        # set up negative entry and perc neg entry calculations
        shape_ilb_complete = ilb_complete.shape  # array dimensions of preburst depths
        total_entries = float(shape_ilb_complete[0] * shape_ilb_complete[1])  # total number of entries
        neg_entries = 0

        # write burst initial losses to csv
        fname_losses = '{0}_Burst_Initial_Losses.csv'.format(site_name)
        fname_losses_out = os.path.join(fpath, 'data', fname_losses)
        try:
            flosses = open(fname_losses_out, 'w')
        except PermissionError:
            # print("File is locked for editing {0}".format(fname_losses_out))
            self.logger.error("File is locked for editing {0}".format(fname_losses_out))
            raise Exception("ERROR: File is locked for editing {0}".format(fname_losses_out))
        except IOError:
            # print('Unexpected error opening file {0}'.format(fname_losses_out))
            self.logger.error('Unexpected error opening file {0}'.format(fname_losses_out))
            raise Exception('ERROR: Unexpected error opening file {0}'.format(fname_losses_out))
        if self.Losses.existsPNLosses and probability_neutral_losses:
            if self.Losses.ils_user is not None:
                flosses.write(
                    'This File has been generated using ARR_to_TUFLOW. The Burst losses have been calculated by '
                    'using Probability Neutral Burst Initial Losses provided by the Datahub and the user '
                    'provided initial loss value of {0} mm. '
                    'Eqn: IL Burst = User IL x IL Burst ARR / IL Storm ARR\n'.format(self.Losses.ils_user))
            else:
                flosses.write(
                    'This File has been generated using ARR_to_TUFLOW. The Burst losses have been calculated by '
                    'using Probability Neutral Burst Initial Losses provided by the Datahub.\n')
        else:
            if self.Losses.ils_user is not None:
                flosses.write(
                    'This File has been generated using ARR_to_TUFLOW. The Burst losses have been calculated by '
                    'subtracting the maximum preburst (Depth or Ratios) from the user defined initial loss '
                    'value of {0} mm.\n'.format(self.Losses.ils_user))
            else:
                flosses.write(
                    'This File has been generated using ARR_to_TUFLOW. The Burst losses have been calculated by '
                    'subtracting the maximum preburst (Depth or Ratios) from the storm initial loss.\n')
        flosses.write('Duration (mins),{0}\n'.format(",".join(map(str, bom.aep_names))))

        for i, dur in enumerate(bom.duration):
            line = '{0}'.format(dur)
            for j in range(shape_ilb_complete[1]):
                if numpy.isnan(ilb_complete[i, j]):
                    line = line + ',-'
                else:
                    line = line + ',{0:.1f}'.format(ilb_complete[i, j])
                    neg_entries += (1 if ilb_complete[i, j] < 0 else 0)
            line = line + '\n'
            flosses.write(line)

        flosses.flush()
        flosses.close()

        # Save Figure
        fig_name = os.path.join(fpath, 'data', '{0}_Burst_Initial_Losses.png'.format(site_name))
        ymax = math.ceil(float(self.Losses.ils) / 10.0) * 10
        xmax = 10 ** math.ceil(math.log10(max(b_com_dur)))
        ymin = math.floor(numpy.nanmin(ilb_complete) / 10.0) * 10

        make_figure(fig_name, bom.duration, ilb_complete, 1, xmax, ymin, ymax, 'Duration (mins)', 'Depth (mm)',
                    'Design Initial Losses: {0}'.format(site_name), bom.aep_names, xlog=True)

        # complete neg entry calculation and write out warning
        perc_neg = (neg_entries / total_entries) * 100  # percentage of negative entries
        if neg_entries > 0:
            # print('WARNING: {0} preburst rainfall depths exceeded storm initial loss ({1:.1f}% of entries)'.
            #      format(neg_entries, perc_neg))
            self.logger.warning(
                'WARNING: {0} preburst rainfall depths exceeded storm initial loss ({1:.1f}% of entries)'.
                    format(neg_entries, perc_neg))

        for a, aep in enumerate(aep_list):
            # get AEP band as per Figure 2.5.12. Temporal Pattern Ranges
            if aep not in exported_aep:
                exported_aep.append(aep)
                if out_notation == 'ari':
                    if aep == '50%':
                        #print('WARNING: 50% AEP does not correspond to 2y ARI. Rather it is equivalent to'
                        #      ' the 1.44y ARI. For 2y ARI please use 0.5EY.')
                        self.logger.warning('WARNING: 50% AEP does not correspond to 2y ARI. Rather it is equivalent to'
                                            ' the 1.44y ARI. For 2y ARI please use 0.5EY.')
                    if aep == '20%':
                        #print('WARNING: 20% AEP does not correspond to 5y ARI. Rather it is equivalent to'
                        #      ' the 4.48y ARI. For 5y ARI please use 0.2EY.')
                        self.logger.warning('WARNING: 20% AEP does not correspond to 5y ARI. Rather it is equivalent to'
                                            ' the 4.48y ARI. For 5y ARI please use 0.2EY.')
            if aep[-2:] != 'EY' and aep[:4] != '1 in':
                if float(aep[:-1]) < 1:
                    #print("WARNING: {0}% AEP event is considered 'Very Rare'. Temporal patterns for 'Very Rare' "
                    #      "events are not yet provided... using 'Rare' temporal patterns.".format(aep[:-1]))
                    self.logger.warning("WARNING: {0}% AEP event is considered 'Very Rare'. Temporal patterns for 'Very Rare' "
                                        "events are not yet provided... using 'Rare' temporal patterns.".format(aep[:-1]))
                    aep_band = 'rare'
                elif float(aep[:-1]) <= 3.2:
                    aep_band = 'rare'
                elif float(aep[:-1]) <= 14.4:
                    aep_band = 'intermediate'
                else:
                    aep_band = 'frequent'
            elif aep[-2:] == 'EY':
                aep_band = 'frequent'
            else:
                #print("WARNING: 1 in {0} yr event is considered 'Very Rare'. Temporal patterns for 'Very Rare' "
                #      "events are not yet provided... using 'Rare' temporal patterns.".format(aep[4:]))
                self.logger.warning("WARNING: 1 in {0} yr event is considered 'Very Rare'. Temporal patterns for 'Very Rare' "
                                    "events are not yet provided... using 'Rare' temporal patterns.".format(aep[4:]))
                aep_band = 'rare'
            process_aep = True
            try:
                if aep[-2:] != 'EY' and float(aep[:-1]) < 1:  # need to convert back to '1 in X' format for indexing
                    ari = 1 / (float(aep[:-1]) / 100)
                    ari_name = '1 in {0:.0f}'.format(ari)
                    aep_ind = bom.aep_names.index(ari_name)
                else:
                    aep_ind = bom.aep_names.index(aep)
            except:
                #print('WARNING: Unable to find BOM data for AEP: {0} - skipping'.format(aep))
                self.logger.warning('WARNING: Unable to find BOM data for AEP: {0} - skipping'.format(aep))
                continue

            # rf inflow
            tp_count_max = tpCount
            if process_aep:  # AEP data exists
                if all_duration:
                    # need to specify AEP_band based on AEP specified
                    arr_durations = self.Temporal.get_durations(aep_band)
                    dur_list = sorted(list(set(arr_durations).intersection(bom.duration)))
                # loop through all durations
                for d, duration in enumerate(dur_list):
                    aep_bands = [aep_band]  # aep bands for temporal patterns
                    aep_bands_4_pb = aep_bands.copy()  # aep bands used for preburst stuff
                    cc_events_ = cc_events.copy()
                    if self.Temporal.dur2tptype[duration] == 'point':
                        tp_count = tpCount * 3 if all_point_tp else tpCount
                        if all_point_tp:
                            aep_bands.extend([x for x in ('frequent', 'intermediate', 'rare') if x != aep_band])
                            cc_events_ = sum([[x for _ in range(3)] for x in cc_events], [])
                    else:
                        tp_count = tpCount + self.Temporal.add_areal_tp * tpCount
                        if self.Temporal.add_areal_tp:
                            aep_bands.extend(['add_areal_tp_{0}'.format(i) for i in range(self.Temporal.add_areal_tp)])
                            cc_events_ = sum([[x for _ in range(self.Temporal.add_areal_tp + 1)] for x in cc_events], [])
                            assert len(cc_events_) == tp_count * len(cc_years) * len(cc_RCP), "Should not be here - List of climate change event names is not the correct length - Actual Length: {0}, Expected Length: {1}".format(len(cc_events_), tp_count * len(cc_years) * len(cc_RCP))

                    tp_count_max = max(tp_count, tp_count_max)

                    # print ('Duration = {0} minutes'.format(duration))
                    process_dur = True
                    try:
                        dur_ind = bom.duration.index(duration)
                    except:
                        #print('WARNING: Unable to find BOM data for duration: {0:.0f}min - skipping'.format(duration))
                        self.logger.warning('WARNING: Unable to find BOM data for duration: {0:.0f}min - skipping'.format(duration))
                        continue
                    if process_dur:
                        if duration not in exported_dur:
                            exported_dur.append(duration)
                        depth = bom.depths[dur_ind, aep_ind]
                        depth_available = True
                        if numpy.isnan(depth):
                            if float(aep[:-1]) < 1:
                                #print("WARNING: Depths for very rare events (< 1% AEP) are not yet provided.")
                                self.logger.warning("WARNING: Depths for very rare events (< 1% AEP) are not yet provided.")
                                depth_available = False
                        ids, increments, dts = self.Temporal.get_dur_aep(duration, aep_bands)
                        increments_pb = []
                        dts_pb = 0
                        pb_depth = 0
                        if bComplete_storm:
                            if self.Losses.existsPNLosses and probability_neutral_losses:
                                self.logger.warning("WARNING: Cannot use complete storm and Probability Neutral Burst"
                                                    "Initial Losses... using design storm")
                                bComplete_storm = False
                            else:
                                i = aep_ind
                                j = dur_ind
                                try:
                                    pb_depth = pb_dep_final_complete[j,i]
                                    if numpy.isnan(pb_depth):
                                        self.logger.warning(
                                            "WARNING: No preburst depths exist for aep/duration [{0}/{1} min]"
                                            "... using design storm".format(aep, duration))
                                    else:
                                        increments_pb, dts_pb = self.Temporal.get_dur_aep_pb(duration, aep_bands,
                                                                                             preburst_pattern_method,
                                                                                             preburst_pattern_dur,
                                                                                             preburst_pattern_tp,
                                                                                             bpreburst_dur_proportional,
                                                                                             aep)
                                        il_complete[j,i] = float(self.Losses.ils)  # change burst loss to storm loss
                                except IndexError:
                                    self.logger.warning(
                                        "WARNING: Error occurred obtaining preburst depth... using design storm")

                        nid = len(ids)
                        ntimes = len(increments[0]) + len(increments_pb) + 2  # add zero to start and end
                        rf_array = numpy.zeros([nid, ntimes])
                        times = [0]
                        if out_form == 'ts1':
                            dt = dts[0]
                        else:
                            dt = dts[0] / 60.  # output in hours
                            dts_pb = dts_pb / 60.
                        for i in range(len(increments_pb)):
                            times.append(times[-1] + dts_pb)
                        for i in range(len(increments[0])):
                            times.append(times[-1] + dt)
                        times.append(times[-1] + dt)
                        # sort data into nice array
                        for i, tpid in enumerate(ids):
                            if bComplete_storm and preburst_pattern_tp == 'design_burst':
                                tp_number = self.Temporal.get_tp_number(tpid)
                                increments_pb = self.Temporal.get_tp_increments(tp_number, duration, aep_bands, preburst_pattern_dur, bpreburst_dur_proportional)
                            i2 = 1
                            for j in range(len(increments_pb)):
                                rf_array[i, i2] = increments_pb[j] * pb_depth / 100.
                                i2 += 1
                            for j in range(len(increments[i])):
                                #rf_array[i, j + 1] = increments[i][j] * depth / 100.
                                rf_array[i, i2] = increments[i][j] * depth / 100.
                                i2 += 1
                        if cc:
                            cc_rf_array = numpy.zeros([nid, ntimes])
                            # add climate change temporal patter to array so it can be written to same file
                            if self.CCF.meta.version > 2024000:
                                for name in cc_param:
                                    cc_multip = self.CCF.get_scenario(name).rf_f.iloc[dur_ind,aep_ind]
                                    for i in range(nid):
                                        i2 = 1
                                        for j in range(len(increments_pb)):
                                            cc_rf_array[i, i2] = increments_pb[j] * pb_depth / 100.
                                            i2 += 1
                                        for j in range(len(increments[i])):
                                            cc_rf_array[i, i2] = increments[i][j] * depth * cc_multip / 100
                                            i2 += 1
                                    rf_array = numpy.append(rf_array, cc_rf_array, axis=0)
                            else:
                                for year, k in cc_years_dict.items():
                                    # k is year correct index of year in self.CCF.Year so multiplier can be extracted
                                    for rcp in cc_RCP:
                                        if rcp == 'RCP4.5':
                                            cc_multip = (self.CCF.RCP4p5[k] / 100) + 1
                                        elif rcp == 'RCP6':
                                            cc_multip = (self.CCF.RCP6[k] / 100) + 1
                                        elif rcp == 'RCP8.5':
                                            cc_multip = (self.CCF.RCP8p5[k] / 100) + 1
                                        # cc_rf_array = np.zeros([nid, ntimes])
                                        for i in range(nid):
                                            i2 = 1
                                            for j in range(len(increments_pb)):
                                                cc_rf_array[i, i2] = increments_pb[j] * pb_depth / 100.
                                                i2 += 1
                                            for j in range(len(increments[i])):
                                                #cc_rf_array[i, j + 1] = increments[i][j] * depth * cc_multip / 100
                                                cc_rf_array[i, i2] = increments[i][j] * depth * cc_multip / 100
                                                i2 += 1
                                        rf_array = numpy.append(rf_array, cc_rf_array, axis=0)
                        # open output file
                        if aep[-1] == '%':
                            if out_notation == 'ari':
                                # if aep == '50%':
                                #    print('WARNING: 50% AEP does not correspond to 2y ARI. Rather it is equivalent to'
                                #          ' the 1.44y ARI. For 2y ARI please use 0.5EY.')
                                # if aep == '20%':
                                #    print('WARNING: 20% AEP does not correspond to 5y ARI. Rather it is equivalent to'
                                #          ' the 4.48y ARI. For 5y ARI please use 0.2EY.')
                                fname = '{0}_RF_{1}{2}m.{3}'.format(site_name, aep_list_formatted[a],
                                                                    dur_list_formatted[d], out_form)
                            else:
                                fname = '{0}_RF_{1}{2}m.{3}'.format(site_name, aep_list_formatted[a],
                                                                    dur_list_formatted[d], out_form)
                        elif aep[-2:] == 'EY':
                            if out_notation == 'ari' and (aep == '0.5EY' or aep == '0.2EY'):
                                fname = '{0}_RF_{1}{2}m.{3}'.format(site_name, aep_list_formatted[a],
                                                                    dur_list_formatted[d], out_form)
                            else:
                                fname = '{0}_RF_{1}{2}m.{3}'.format(site_name, aep_list_formatted[a],
                                                                    dur_list_formatted[d], out_form)
                        else:
                            if out_notation == 'ari':
                                fname = '{0}_RF_{1}{2}m.{3}'.format(site_name, aep_list_formatted[a],
                                                                    dur_list_formatted[d], out_form)
                            else:
                                fname = '{0}_RF_{1}{2}m.{3}'.format(site_name, aep_list_formatted[a],
                                                                    dur_list_formatted[d], out_form)
                        outfname = os.path.join(fpath, 'rf_inflow', fname)
                        if not os.path.exists(os.path.dirname(outfname)):  # check output directory exists
                            os.mkdir(os.path.dirname(outfname))
                        try:
                            fo = open(outfname, 'w')
                        except IOError:
                            #print('Unexpected error opening file {0}'.format(outfname))
                            self.logger.error('Unexpected error opening file {0}'.format(outfname))
                            raise Exception('Unexpected error opening file {0}'.format(outfname))
                        except PermissionError:
                            #print("File is locked for editing {0}".format(outfname))
                            self.logger.error("File is locked for editing {0}".format(outfname))
                            raise Exception("File is locked for editing {0}".format(outfname))
                        # ts1
                        fo.write('! Written by TUFLOW ARR Python Script based on {0} temporal pattern\n'.format
                                 (aep_band))
                        if out_form == 'ts1':
                            line3 = 'Time (min)'
                        else:
                            line3 = 'Time (hour)'

                        line1 = "Start_Index"
                        line2 = "End_Index"
                        line2b = 'Event ID'

                        tp_cc = False
                        cc_event_index = 0  # index to call correct name from cc_events
                        k = -1
                        cc_count = self.CCF.scenario_count() if self.CCF.meta.version > 2024000 else len(cc_years) * len(cc_RCP)
                        # create a list 1 - 10 repeated for all temporal pattern sets
                        for i in [k for k in range(1, tp_count+1)] * (cc_count + 1):
                            if i > len(ids):
                                break
                            line1 = line1 + ', 1'
                            line2 = line2 + ', {0}'.format(ntimes)
                            if k + 1 >= tp_count:
                                k = -1
                            k += 1
                            line2b = line2b + ',{0}'.format(ids[k])
                            if i < tp_count and not tp_cc:  # standard temporal pattern
                                line3 = line3 + ',TP{0:02d}'.format(i)
                            elif i == tp_count and not tp_cc:  # last standard temporal pattern, make cc true so cc next iter
                                tp_cc = True
                                line3 = line3 + ',TP{0:02d}'.format(i)
                            else:  # add climate change name to temporal pattern
                                if cc:
                                    line3 = line3 + ',TP{0:02d}_{1}'.format(i, cc_events_[cc_event_index])
                                    cc_event_index += 1
                                else:
                                    break
                        if out_form == 'ts1':
                            fo.write('{0}, {1}\n'.format(nid, ntimes))
                            fo.write(line1 + '\n')
                            fo.write(line2 + '\n')
                        if out_form == 'CSV':
                            fo.write(line2b + '\n')
                        fo.write(line3 + '\n')
                        for i in range(ntimes):
                            line = '{0}'.format(times[i])
                            for j in range(rf_array.shape[0]):
                                if numpy.isnan(rf_array[j, i]):
                                    line += ',0'
                                else:
                                    line += ',{0}'.format(rf_array[j, i])
                            fo.write(line + '\n')
                        if not depth_available:
                            fo.write("**Depth data not available for very rare events (< 1% AEP)")
                        fo.flush()
                        fo.close()

    #    # Initial Losses
    #    if self.Losses.existsPNLosses and probability_neutral_losses:  # use probability neutral initial losses if they exist
    #        # generate same size array between rainfall depths and initial losses
    #        b_com_aep, b_com_dur, b_dep_com, b_com_dur_index = common_data(bom.aep_names, bom.duration,
    #                                                                       self.Losses.AEP_names,
    #                                                                       self.Losses.Duration,
    #                                                                       bom.depths)
    #        ilb_complete = extend_array_dur(b_com_dur_index, b_com_aep, self.Losses.ilpn, bom.duration)  # add all durations to array
    #        ilb_complete = interpolate_nan(ilb_complete, bom.duration, self.Losses.ils, lossMethod=lossMethod, mar=mar,
    #                                       staticLoss=staticLoss)
    #        # complete loss array to include all aeps (with nans)
    #        ilb_complete = extend_array_aep(b_com_aep, bom.aep_names, ilb_complete)
#
    #        # apply user IL
    #        if self.Losses.ils_user is not None:
    #            if float(self.Losses.ils) < 0:
    #                ilb_complete = ilb_complete * (self.Losses.ils_user / self.Losses.ils)
    #            else:
    #                self.logger.warning(
    #                    "WARNING: Cannot calculate initial losses from user input because Storm Initial is zero")
#
    #    else:  # original method of using preburst and storm loss
    #        # write out burst initial loss
    #        if preBurst == '10%':
    #            preBurst_depths = self.PreBurst.Depths10
    #            preBurst_ratios = self.PreBurst.Ratios10
    #        elif preBurst == '25%':
    #            preBurst_depths = self.PreBurst.Depths25
    #            preBurst_ratios = self.PreBurst.Ratios25
    #        elif preBurst == '50%':
    #            preBurst_depths = self.PreBurst.Depths50
    #            preBurst_ratios = self.PreBurst.Ratios50
    #        elif preBurst == '75%':
    #            preBurst_depths = self.PreBurst.Depths75
    #            preBurst_ratios = self.PreBurst.Ratios75
    #        elif preBurst == '90%':
    #            preBurst_depths = self.PreBurst.Depths90
    #            preBurst_ratios = self.PreBurst.Ratios90
    #        else:
    #            preBurst_depths = self.PreBurst.Depths50
    #            preBurst_ratios = self.PreBurst.Ratios50
#
    #        # generate same size numpy arrays for burst and preburst data based on common AEPs and Durations
    #        b_com_aep, b_com_dur, b_dep_com, b_com_dur_index = common_data(bom.aep_names, bom.duration,
    #                                                                       self.PreBurst.AEP_names, self.PreBurst.Duration,
    #                                                                       bom.depths)
    #        pb_com_aep, pb_com_dur, pb_dep_com, pb_com_dur_index = common_data(self.PreBurst.AEP_names,
    #                                                                           self.PreBurst.Duration, bom.aep_names,
    #                                                                           bom.duration, preBurst_depths)
    #        pb_com_aep, pb_com_dur, pb_rto_com, pb_com_dur_index = common_data(self.PreBurst.AEP_names,
    #                                                                           self.PreBurst.Duration, bom.aep_names,
    #                                                                           bom.duration, preBurst_ratios)
#
    #        # calculate the maximum preburst depths
    #        pb_rto_d_com = numpy.multiply(b_dep_com, pb_rto_com)  # convert preburst ratios to depths
    #        #pb_dep_final = numpy.maximum(pb_dep_com, pb_rto_d_com)  # take the max of preburst ratios and depths
    #        pb_dep_final = pb_dep_com
#
    #        # calculate burst intial loss (storm il minus preburst depth)
    #        if float(self.Losses.ils) == 0 and float(self.Losses.cls) == 0:
    #            #print('WARNING: No rainfall losses found.')
    #            self.logger.warning('WARNING: No rainfall losses found.')
    #        if float(self.Losses.ils) < 0:
    #            #print('WARNING: initial loss value is {0}'.format(self.Losses.ils))
    #            self.logger.warning('WARNING: initial loss value is {0}'.format(self.Losses.ils))
    #        if float(self.Losses.cls) < 0:
    #            #print('WARNING: continuing loss value is {0}'.format(self.Losses.cls))
    #            self.logger.warning('WARNING: continuing loss value is {0}'.format(self.Losses.cls))
    #        shape_com = pb_dep_final.shape  # array dimensions of preburst depths
    #        if self.Losses.ils_user is not None:
    #            ils = numpy.zeros(shape_com) + float(self.Losses.ils_user)  # storm initial loss array
    #        else:
    #            ils = numpy.zeros(shape_com) + float(self.Losses.ils)  # storm initial loss array
    #        ilb = numpy.add(ils, -pb_dep_final)  # burst initial loss (storm initial loss subtract preburst)
#
    #        # extend loss array to all durations using interpolation
    #        ilb_complete = extend_array_dur(b_com_dur_index, b_com_aep, ilb, bom.duration)  # add all durations to array
    #        ilb_complete = interpolate_nan(ilb_complete, bom.duration, self.Losses.ils, lossMethod=lossMethod, mar=mar,
    #                                       staticLoss=staticLoss)
    #        # complete loss array to include all aeps (with nans)
    #        ilb_complete = extend_array_aep(b_com_aep, bom.aep_names, ilb_complete)
#
    #    # set up negative entry and perc neg entry calculations
    #    shape_ilb_complete = ilb_complete.shape  # array dimensions of preburst depths
    #    total_entries = float(shape_ilb_complete[0] * shape_ilb_complete[1])  # total number of entries
    #    neg_entries = 0
#
    #    # write burst initial losses to csv
    #    fname_losses = '{0}_Burst_Initial_Losses.csv'.format(site_name)
    #    fname_losses_out = os.path.join(fpath, 'data', fname_losses)
    #    try:
    #        flosses = open(fname_losses_out, 'w')
    #    except PermissionError:
    #        #print("File is locked for editing {0}".format(fname_losses_out))
    #        self.logger.error("File is locked for editing {0}".format(fname_losses_out))
    #        raise Exception("ERROR: File is locked for editing {0}".format(fname_losses_out))
    #    except IOError:
    #        #print('Unexpected error opening file {0}'.format(fname_losses_out))
    #        self.logger.error('Unexpected error opening file {0}'.format(fname_losses_out))
    #        raise Exception('ERROR: Unexpected error opening file {0}'.format(fname_losses_out))
    #    if self.Losses.existsPNLosses and probability_neutral_losses:
    #        if self.Losses.ils_user is not None:
    #            flosses.write(
    #                'This File has been generated using ARR_to_TUFLOW. The Burst losses have been calculated by '
    #                'using Probability Neutral Burst Initial Losses provided by the Datahub and the user '
    #                f'provided initial loss value of {self.Losses.ils_user} mm. '
    #                'Eqn: IL Burst = User IL x IL Burst ARR / IL Storm ARR\n')
    #        else:
    #            flosses.write('This File has been generated using ARR_to_TUFLOW. The Burst losses have been calculated by '
    #                          'using Probability Neutral Burst Initial Losses provided by the Datahub.\n')
    #    else:
    #        if self.Losses.ils_user is not None:
    #            flosses.write(
    #                'This File has been generated using ARR_to_TUFLOW. The Burst losses have been calculated by '
    #                'subtracting the maximum preburst (Depth or Ratios) from the user defined initial loss '
    #                f'value of {self.Losses.ils_user} mm.\n')
    #        else:
    #            flosses.write('This File has been generated using ARR_to_TUFLOW. The Burst losses have been calculated by '
    #                          'subtracting the maximum preburst (Depth or Ratios) from the storm initial loss.\n')
    #    flosses.write('Duration (mins),{0}\n'.format(",".join(map(str, bom.aep_names))))
#
    #    for i, dur in enumerate(bom.duration):
    #        line = '{0}'.format(dur)
    #        for j in range(shape_ilb_complete[1]):
    #            if numpy.isnan(ilb_complete[i, j]):
    #                line = line + ',-'
    #            else:
    #                line = line + ',{0:.1f}'.format(ilb_complete[i, j])
    #                neg_entries += (1 if ilb_complete[i, j] < 0 else 0)
    #        line = line + '\n'
    #        flosses.write(line)
#
    #    flosses.flush()
    #    flosses.close()
#
    #    # Save Figure
    #    fig_name = os.path.join(fpath, 'data', '{0}_Burst_Initial_Losses.png'.format(site_name))
    #    ymax = math.ceil(float(self.Losses.ils) / 10.0) * 10
    #    xmax = 10 ** math.ceil(math.log10(max(b_com_dur)))
    #    ymin = math.floor(numpy.nanmin(ilb_complete) / 10.0) * 10
#
    #    make_figure(fig_name, bom.duration, ilb_complete, 1, xmax, ymin, ymax, 'Duration (mins)', 'Depth (mm)',
    #                'Design Initial Losses: {0}'.format(site_name), bom.aep_names, xlog=True)
#
    #    # complete neg entry calculation and write out warning
    #    perc_neg = (neg_entries / total_entries) * 100  # percentage of negative entries
    #    if neg_entries > 0:
    #        #print('WARNING: {0} preburst rainfall depths exceeded storm initial loss ({1:.1f}% of entries)'.
    #        #      format(neg_entries, perc_neg))
    #        self.logger.warning('WARNING: {0} preburst rainfall depths exceeded storm initial loss ({1:.1f}% of entries)'.
    #                            format(neg_entries, perc_neg))

        # write common bc_dbase
        bc_fname = os.path.join(fpath, 'bc_dbase.csv')
        if catch_no == 0:
            try:
                bcdb = open(bc_fname, 'w')
            except PermissionError:
                #print("File is locked for editing: {0}".format(bc_fname))
                self.logger.error("File is locked for editing: {0}".format(bc_fname))
                raise Exception("ERROR: File is locked for editing: {0}".format(bc_fname))
            except IOError:
                #print('Unexpected error opening file {0}'.format(bc_fname))
                self.logger.error('Unexpected error opening file {0}'.format(bc_fname))
                raise Exception('ERROR: Unexpected error opening file {0}'.format(bc_fname))
            bcdb.write('Name,Source,Column 1,Column 2,Add Col 1,Mult Col 2,Add Col 2,Column 3,Column 4\n')
            if out_form == 'ts1':
                bcdb.write('{0},rf_inflow\\{0}_RF_~{1}~~DUR~.{2},Time (min), ~TP~\n'.format(site_name,
                                                                                           out_notation.upper(),
                                                                                           out_form))
            else:
                bcdb.write('{0},rf_inflow\\{0}_RF_~{1}~~DUR~.{2},Time (hour), ~TP~\n'.format(site_name,
                                                                                            out_notation.upper(),
                                                                                            out_form))
            bcdb.flush()
            bcdb.close()
        else:
            try:
                bcdb = open(bc_fname, 'a')
            except PermissionError:
                #print("File is locked for editing: {0}".format(bc_fname))
                self.logger.error("File is locked for editing: {0}".format(bc_fname))
                raise Exception("ERROR: File is locked for editing: {0}".format(bc_fname))
            except IOError:
                #print('Unexpected error opening file {0}'.format(bc_fname))
                self.logger.error('Unexpected error opening file {0}'.format(bc_fname))
                raise Exception('ERROR: Unexpected error opening file {0}'.format(bc_fname))
            if out_form == 'ts1':
                bcdb.write(r'{0},rf_inflow\{0}_RF_~{1}~~DUR~.{2},Time (min), ~TP~\n'.format(site_name,
                                                                                           out_notation.upper(),
                                                                                           out_form))
            else:
                bcdb.write(r'{0},rf_inflow\{0}_RF_~{1}~~DUR~.{2},Time (hour), ~TP~\n'.format(site_name,
                                                                                            out_notation.upper(),
                                                                                            out_form))
            bcdb.flush()
            bcdb.close()

        # write climate change bc_dbase
        if cc:
            if catch_no == 0:
                bc_fname_cc = os.path.join(fpath, 'bc_dbase_CC.csv')
                try:
                    bcdb_cc = open(bc_fname_cc, 'w')
                except PermissionError:
                    #print("File is locked for editing: {0}".format(bc_fname_cc))
                    self.logger.error("File is locked for editing: {0}".format(bc_fname_cc))
                    raise Exception("ERROR: File is locked for editing: {0}".format(bc_fname_cc))
                except IOError:
                    #print('Unexpected error opening file {0}'.format(bc_fname_cc))
                    self.logger.error('Unexpected error opening file {0}'.format(bc_fname_cc))
                    raise Exception('ERROR: Unexpected error opening file {0}'.format(bc_fname_cc))
                bcdb_cc.write('Name,Source,Column 1, Column 2\n')
                if out_form == 'ts1':
                    bcdb_cc.write('{0},rf_inflow\\{0}_RF_~{1}~~DUR~.{2},Time (min), ~TP~_~CC~\n'.
                                  format(site_name, out_notation.upper(), out_form))
                else:
                    bcdb_cc.write('{0},rf_inflow\\{0}_RF_~{1}~~DUR~.{2},Time (hour), ~TP~_~CC~\n'.
                                  format(site_name, out_notation.upper(), out_form))
                bcdb_cc.flush()
                bcdb_cc.close()
            else:
                bc_fname_cc = os.path.join(fpath, 'bc_dbase_CC.csv')
                try:
                    bcdb_cc = open(bc_fname_cc, 'a')
                except PermissionError:
                    #print("File is locked for editing: {0}".format(bc_fname_cc))
                    self.logger.error("File is locked for editing: {0}".format(bc_fname_cc))
                    raise Exception("ERROR: File is locked for editing: {0}".format(bc_fname_cc))
                except IOError:
                    #print('Unexpected error opening file {0}'.format(bc_fname_cc))
                    self.logger.error('Unexpected error opening file {0}'.format(bc_fname_cc))
                    raise Exception('ERROR: Unexpected error opening file {0}'.format(bc_fname_cc))
                if out_form == 'ts1':
                    bcdb_cc.write(r'{0},rf_inflow\{0}_RF_~{1}~~DUR~.{2},Time (min), ~TP~_~CC~\n'.
                                  format(site_name, out_notation.upper(), out_form))
                else:
                    bcdb_cc.write(r'{0},rf_inflow\{0}_RF_~{1}~~DUR~.{2},Time (hour), ~TP~_~CC~\n'.
                                  format(site_name, out_notation.upper(), out_form))
                bcdb_cc.flush()
                bcdb_cc.close()

        # open common .tef
        tef_fname = os.path.join(fpath, 'Event_File.tef')
        try:
            tef = open(tef_fname, 'w')
        except PermissionError:
            #print("File is locked for editing: {0}".format(tef_fname))
            self.logger.error("File is locked for editing: {0}".format(tef_fname))
            raise Exception("ERROR: File is locked for editing: {0}".format(tef_fname))
        except IOError:
            #print('Unexpected error opening file {0}'.format(tef_fname))
            self.logger.error('Unexpected error opening file {0}'.format(tef_fname))
            raise Exception('ERROR: Unexpected error opening file {0}'.format(tef_fname))
        tef.write('!EVENT MAGNITUDES\n')
        for a, aep in enumerate(exported_aep):
            if aep[-2:] == 'EY':
                if out_notation == 'ari' and (aep == '0.5EY' or aep == '0.2EY'):
                    tef.write('Define Event == {0}\n'.format(aep_list_formatted[a]))
                    tef.write('    BC Event Source == ~ARI~ | {0}\n'.format(aep_list_formatted[a]))
                    tef.write('End Define\n\n')
                elif out_notation == 'ari':
                    tef.write('Define Event == {0}\n'.format(aep_list_formatted[a]))
                    tef.write('    BC Event Source == ~ARI~ | {0}\n'.format(aep_list_formatted[a]))
                    tef.write('End Define\n\n')
                else:
                    tef.write('Define Event == {0}\n'.format(aep_list_formatted[a]))
                    tef.write('    BC Event Source == ~AEP~ | {0}\n'.format(aep_list_formatted[a]))
                    tef.write('End Define\n\n')
            elif out_notation == 'ari':
                tef.write('Define Event == {0}\n'.format(aep_list_formatted[a]))
                tef.write('    BC Event Source == ~ARI~ | {0}\n'.format(aep_list_formatted[a]))
                tef.write('End Define\n\n')
            else:
                tef.write('Define Event == {0}\n'.format(aep_list_formatted[a]))
                tef.write('    BC Event Source == ~AEP~ | {0}\n'.format(aep_list_formatted[a]))
                tef.write('End Define\n\n')

        # now to loop through events and output
        tef.write('!EVENT DURATIONS\n')
        for d, duration in enumerate(exported_dur):
            tef.write('Define Event == {0:}m\n'.format(dur_list_formatted[d]))
            tef.write('    BC Event Source == ~DUR~ | {0:}m\n'.format(dur_list_formatted[d]))
            tef.write('End Define\n\n')

        tef.write('!EVENT TEMPORAL PATTERNS\n')
        for i in range(tp_count_max):
            tef.write('Define Event == tp{0:02d}\n'.format(i + 1))
            tef.write('    BC Event Source == ~TP~ | TP{0:02d}\n'.format(i + 1))
            tef.write('End Define\n\n')

        if cc:
            tef.write('!CLIMATE CHANGE YEAR\n')
            scenario_prev = ''
            i = 1
            for scenario in cc_events:
                if scenario != scenario_prev:
                    tef.write(f'!{self.CCF.get_scenario(scenario).param_to_string()}\n')
                    tef.write(f'Define Event == {scenario}\n')
                    tef.write('    BC Event Source == ~CC~ | {0}\n'.format(scenario))
                    tef.write('End Define\n\n')
                    scenario_prev = scenario
                    i += 1

                # tef.write('!CLIMATE CHANGE RCP\n')
                # for rcp in cc_RCP:
                #    tef.write('Define Event == rcp{0}\n'.format(rcp[3:]))
                #    tef.write('    BC Event Source == ~RCP~ | {0}\n'.format(rcp[3:]))
                #    tef.write('End Define\n\n')

        # close up
        tef.flush()
        tef.close()
        
        # write losses control file
        if tuflow_loss_method == 'infiltration':
            tsoilf = os.path.join(fpath, 'soils.tsoilf')
            try:
                if catch_no == 0:
                    tsoilf_open = open(tsoilf, 'w')
                else:
                    tsoilf_open = open(tsoilf, 'a')
            except PermissionError:
                #print("File is locked for editing: {0}".format(tsoilf))
                self.logger.error("File is locked for editing: {0}".format(tsoilf))
                raise Exception("ERROR: File is locked for editing: {0}".format(tsoilf))
            except IOError:
                #print('Unexpected error opening file {0}'.format(tsoilf))
                self.logger.error('Unexpected error opening file {0}'.format(tsoilf))
                raise Exception('ERROR: Unexpected error opening file {0}'.format(tsoilf))
            if catch_no == 0:
                tsoilf_open.write('! Soil ID, Method, IL, CL\n')
            increment = 1
            if urban_initial_loss is not None and urban_continuing_loss is not None:
                increment = 2
                if catch_no == 0:
                    tsoilf_open.write('1, ILCL, {0}, {1},  ! Impervious Area Rainfall Losses\n'.format(urban_initial_loss, urban_continuing_loss))
            if use_global_continuing_loss and not cc:
                tsoilf_open.write('{1:.0f}, ILCL, <<IL_{0}>>, {2}  ! Design ARR2016 Losses For Catchment {0}\n'.format(site_name, catch_no + increment, self.Losses.cls))
            else:
                tsoilf_open.write('{1:.0f}, ILCL, <<IL_{0}>>, <<CL_{0}>>  ! Design ARR2016 Losses For Catchment {0}\n'.format(site_name, catch_no + increment))
            
            tsoilf_open.close()
        else:
            materials = os.path.join(fpath, 'materials.csv')
            try:
                if catch_no == 0:
                    materials_open = open(materials, 'w')
                else:
                    materials_open = open(materials, 'a')
            except IOError:
                #print('Unexpected error opening file {0}'.format(materials))
                self.logger.error('Unexpected error opening file {0}'.format(materials))
                raise ('Unexpected error opening file')
            if catch_no == 0:
                materials_open.write("Material ID,Manning's n,Rainfall Loss Parameters,Land Use Hazard ID,Storage Reduction Factor,Fraction Impervious,! Description\n")
            increment = 1
            if urban_initial_loss is not None and urban_continuing_loss is not None:
                increment = 2
                if catch_no == 0:
                    materials_open.write('1,,"{0}, {1}",,,,! Impervious Area Rainfall Losses\n'.format(urban_initial_loss, urban_continuing_loss))
            if use_global_continuing_loss and not cc:
                materials_open.write('{1:.0f},,"<<IL_{0}>>, {2}",,,,! Design ARR2016 Losses for catchment {0}\n'.format(site_name, catch_no + increment, self.Losses.cls))
            else:
                materials_open.write('{1:.0f},,"<<IL_{0}>>, <<CL_{0}>>",,,,! Design ARR2016 Losses for catchment {0}\n'.format(site_name, catch_no + increment))
            materials_open.close()

        rareMag2Name = {'0.5%': '1 in 200', '0.2%': '1 in 500', '0.1%': '1 in 1000',
                        '0.05%': '1 in 2000'}

        # dump loss data to file - when processing multiple catchments losses have to be merged into as single IF statement
        # so cache the data so the IF statement can be re-written each time
        persistent_data_folder = os.path.join(fpath, 'data')
        if catch_no == 0:
            self.settings.persistent_data.clear(persistent_data_folder)
        for i, aep in enumerate(aep_list_formatted):
            for j, dur in enumerate(dur_list_formatted):
                if aep_list[i] in rareMag2Name:
                    mag_index = bom.aep_names.index(rareMag2Name[aep_list[i]])
                else:
                    mag_index = bom.aep_names.index(aep_list[i])
                dur_index = bom.duration.index(dur_list[j])
                il = il_complete[dur_index, mag_index]
                if numpy.isnan(il):
                    il = 0
                cl = float(self.Losses.cls)
                self.settings.persistent_data.add_initial_loss(persistent_data_folder, aep, dur, 'NOCC', site_name, (il, cl))
                if cc:
                    for name in cc_param:
                        scen = self.CCF.get_scenario(name)
                        if bComplete_storm:
                            ilcc = scen.init_loss
                        else:
                            ilcc = scen.init_losses_a.iloc[dur_index, mag_index]
                            if numpy.isnan(ilcc):
                                ilcc = 0
                        clcc = scen.cont_loss
                        self.settings.persistent_data.add_initial_loss(persistent_data_folder, aep, dur, name, site_name, (ilcc, clcc))

        # write trd losses file
        if tuflow_loss_method == 'infiltration':
            trd = os.path.join(fpath, 'soil_infiltration.trd')
        else:
            trd = os.path.join(fpath, 'rainfall_losses.trd')
        losses = self.settings.persistent_data.load(persistent_data_folder)
        try:
            with open(trd, 'w') as trd_open:
                trd_open.write("! TUFLOW READ FILE - SET RAINFALL LOSS VARIABLES\n")
                for i, (aep, aep_dict) in enumerate(losses.items()):
                    if1 = 'If' if i == 0 else 'Else If'
                    trd_open.write(f"{if1} Event == {aep}\n")
                    for j, (dur, dur_dict) in enumerate(aep_dict.items()):
                        if2 = 'If' if j == 0 else 'Else If'
                        trd_open.write(f"    {if2} Event == {dur}m\n")
                        k = -1
                        if cc:
                            for cc_name, cc_dict in dur_dict.items():
                                if cc_name == 'NOCC':
                                    continue  # add at end
                                k += 1
                                if3 = 'If' if k == 0 else 'Else If'
                                trd_open.write(f"        {if3} Event == {cc_name}\n")
                                for catch_name, (il, cl) in cc_dict.items():
                                    trd_open.write(f'            Set Variable IL_{catch_name} == {il:.1f}\n')
                                    trd_open.write(f'            Set Variable CL_{catch_name} == {cl:.1f}\n')
                            trd_open.write('        Else  ! no climate change\n')
                            for catch_name, (il, cl) in dur_dict['NOCC'].items():
                                trd_open.write(f'            Set Variable IL_{catch_name} == {il:.1f}\n')
                                trd_open.write(f'            Set Variable CL_{catch_name} == {cl:.1f}\n')
                            trd_open.write('        End If\n')
                        else:
                            for catch_name, (il, cl) in dur_dict['NOCC'].items():
                                trd_open.write(f'        Set Variable IL_{catch_name} == {il:.1f}\n')
                                if not use_global_continuing_loss:
                                    trd_open.write(f'        Set Variable CL_{catch_name} == {cl:.1f}\n')
                    trd_open.write('    Else\n')
                    trd_open.write('        Pause == Event Not Recognised\n')
                    trd_open.write('    End If\n')
                trd_open.write('Else\n')
                trd_open.write('    Pause == Event Not Recognised\n')
                trd_open.write('End If')
        except (IOError, PermissionError):
            self.logger.error("File is locked for editing: {0}".format(trd))
            raise Exception("ERROR: File is locked for editing: {0}".format(trd))

    def temporalPatternRegion(self, fi):
        """
        Collects the temporal pattern region
        
        :param fi: str full file path to input file
        :return: str temporal pattern region
        """
        
        label = ''
        
        # if fi is a string then open
        if type(fi) is str:
            with open(fi, 'r') as fo:
                for line in fo:
                    if "[TP]" in line.upper():
                        for subline in fo:
                            if '[END_TP]' in subline.upper():
                                return label
                            if 'LABEL' in subline.upper():
                                property_name, property_value = subline.split(',')
                                label = property_value.strip()
        
        # else file may already be an open object
        else:
            for line in fi:
                if "[TP]" in line.upper():
                    for subline in fi:
                        if '[END_TP]' in subline.upper():
                            fi.seek(0)
                            return label
                        if 'LABEL' in subline.upper():
                            property_name, property_value = subline.split(',')
                            label = property_value.strip()
            fi.seek(0)
            
        return label

    def arealTemporalPatternCode(self, fi):
        """
        Collects the areal temporal pattern region code

        :param fi: str full file path to input file
        :return: str temporal pattern region
        """

        label = ''

        # if fi is a string then open
        if type(fi) is str:
            with open(fi, 'r') as fo:
                for line in fo:
                    if "[ATP]" in line.upper():
                        for subline in fo:
                            if '[END_ATP]' in subline.upper():
                                return label
                            if 'CODE' in subline.upper():
                                property_name, property_value = subline.split(',')
                                label = property_value.strip()

        # else file may already be an open object
        else:
            for line in fi:
                if "[ATP]" in line.upper():
                    for subline in fi:
                        if '[END_ATP]' in subline.upper():
                            fi.seek(0)
                            return label
                        if 'CODE' in subline.upper():
                            property_name, property_value = subline.split(',')
                            label = property_value.strip()
            fi.seek(0)

        return label
    
if __name__ == '__main__':
    file = r"C:\TUFLOW\ARR2016\QGIS\Whole_catchment\data\ARR_Web_data_catch_A.txt"
    areal_tp_csv = r"C:\_Advanced_Training\Module_Data\ARR\Areal_WT_Increments.csv"
    ARR = Arr()
    ARR.load(file, 125, add_tp=[], areal_tp=areal_tp_csv)
    