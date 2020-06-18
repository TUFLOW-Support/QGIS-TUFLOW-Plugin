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
import numpy
import math
import logging
from ARR_TUFLOW_func_lib import *


class ArrMeta:
    def __init__(self):
        self.Time_Accessed = None
        self.Version = None

    def read(self, fi):
        line = next(fi).strip('\n')
        data = line.split(',')
        self.Time_Accessed = data[1]
        line = next(fi).strip('\n')
        data = line.split(',')
        self.Version = data[1]


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
        for line in fi:
            if line.find('[LONGARF]') >= 0:
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
        if len(self.param) < 1:
            self.error = True
            self.message = 'Error processing ARF.'
        fi.seek(0)
        self.loaded = True
        #print('Finished reading file.')
        self.logger.info('Finished reading file.')


class ArrLosses:
    def __init__(self):  # initialise the ARR storm losses
        self.loaded = False
        self.error = False
        self.message = None
        self.ils = None
        self.cls = None
        self.ils_datahub = None
        self.cls_datahub = None
        self.ils_user = None
        self.cls_user = None
        self.logger = logging.getLogger('ARR2019')

        # NSW probability neutral losses
        self.existsPNLosses = False
        self.AEP = []
        self.AEP_names = []
        self.Duration = []
        self.ilpn = None

    def load(self, fi):
        for line in fi:
            if line.find('[LOSSES]') >= 0:
                finished = False
                for block_line in fi:
                    data = block_line.split(',')
                    finished = (data[0] == '\n' or block_line.find('[LOSSES_META]') >= 0)
                    if finished:
                        break
                    if data[0].lower() == 'storm initial losses (mm)':
                        self.ils_datahub = data[1]
                        self.ils = data[1]
                    if data[0].lower() == 'storm continuing losses (mm/h)':
                        self.cls_datahub = data[1]
                        self.cls = data[1]
                if finished:
                    break
        if self.ils is None or self.cls is None:
            self.error = True
            self.message = 'Error processing Storm Losses. This may be because you have selected an urban area.'
            self.ils = 0
            self.cls = 0
        fi.seek(0)  # rewind file

        self.loadProbabilityNeutralLosses(fi)

        self.loaded = True
        #print('Finished reading file.')
        self.logger.info('Finished reading file.')

    def loadProbabilityNeutralLosses(self, fi):
        """
        Load probability neutral losses

        :param fi: FileIO object
        :return: None
        """

        self.logger.info("Searching for Probability Neutral Initial Losses...")
        for line in fi:
            if line.find("[BURSTIL]") > -1:
                self.logger.info("Found Probability Neutral Initial Losses... loading")
                finished = False
                read_header = True
                losses_all = []
                for block_line in fi:
                    data = block_line.split(',')
                    finished = (data[0] == '\n' or block_line.find('[BURSTIL_META]') >= 0)
                    if finished:
                        break
                    if read_header:
                        data = block_line.strip('\n').split(',')
                        for valstr in data[1:]:
                            try:
                                val = float(valstr)
                                self.AEP.append(val)
                                self.AEP_names.append('{0:.0f}%'.format(val))
                            except Exception as e:
                                self.logger.warning(f"ERROR: Reading Probability Neutral Initial Losses AEP... skipping\n{e}")
                                read_header = False
                                return
                        read_header = False
                    else:
                        try:
                            dur = int(data[0][:data[0].index('(')])
                            self.Duration.append(dur)
                            losses = [float(x) for x in data[1:]]
                            losses_all.append(losses)
                        except Exception as e:
                            self.error = True
                            self.message = 'Error processing from line {0}'.format(block_line)
                            self.logger.warning(f"ERROR: Reading Probability Neutral Initial Losses... skipping\n{e}")
                            return
                if finished:
                    self.ilpn = numpy.array(losses_all)
                    self.existsPNLosses = True
                    self.logger.info("Finished reading Probability Neutral Initial Losses.")
                    break

        fi.seek(0)

    def applyUserInitialLoss(self, loss):
        """apply user specified (storm) initial loss to calculations instead of datahub loss"""
        
        #self.ils = loss
        self.ils_user = loss
        #print("Using user specified intial loss: {0}".format(loss))
        self.logger.info("Using user specified initial loss: {0}".format(loss))

    def applyUserContinuingLoss(self, loss):
        """apply user specified continuing loss to calculations instead of datahub loss"""
    
        self.cls = loss
        self.cls_user = loss
        #print("Using user specified continuing loss: {0}".format(loss))
        self.logger.info("Using user specified continuing loss: {0}".format(loss))


# noinspection PyBroadException,PyBroadException
class ArrPreburst:
    def __init__(self):  # initialise the ARR median preburst
        self.loaded = False
        self.error = False
        self.message = None
        self.AEP = []
        self.AEP_names = []
        self.Duration = []
        self.Depths10 = []
        self.Ratios10 = []
        self.Depths25 = []
        self.Ratios25 = []
        self.Depths50 = []
        self.Ratios50 = []
        self.Depths75 = []
        self.Ratios75 = []
        self.Depths90 = []
        self.Ratios90 = []
        self.logger = logging.getLogger('ARR2019')

    def load(self, fi):

        for line in fi:
            if line.find('[PREBURST]') >= 0:
                finished = False
                read_header = True
                for block_line in fi:
                    data = block_line.split(',')
                    finished = (data[0] == '\n' or block_line.find('[PREBURST_META]') >= 0)
                    if finished:
                        break
                    if read_header:
                        data = block_line.strip('\n').split(',')
                        for valstr in data[1:]:
                            try:
                                val = float(valstr)
                                self.AEP.append(val)
                                self.AEP_names.append('{0:.0f}%'.format(val))
                            except:
                                read_header = False
                        read_header = False
                    else:
                        try:
                            dur = int(data[0][:data[0].index('(')])
                            self.Duration.append(dur)
                            depths = []
                            ratios = []
                            for i in range(len(self.AEP)):
                                # get rid of brackets and split, can be done with regular expression
                                tmp = data[1 + i].replace('(', ',').replace(')', ',').split(',')
                                depths.append(float(tmp[0]))
                                ratios.append(float(tmp[1]))
                            self.Depths50.append(depths)
                            self.Ratios50.append(ratios)
                        except:
                            self.error = True
                            self.message = 'Error processing from line {0}'.format(block_line)
                            return
            if line.find('[PREBURST10]') >= 0:
                finished = False
                read_header = True
                for block_line in fi:
                    data = block_line.split(',')
                    finished = (data[0] == '\n' or block_line.find('[PREBURST10_META]') >= 0)
                    if finished:
                        break
                    if read_header:
                        read_header = False
                    else:
                        try:
                            depths = []
                            ratios = []
                            for i in range(len(self.AEP)):
                                # get rid of brackets and split, can be done with regular expression
                                tmp = data[1 + i].replace('(', ',').replace(')', ',').split(',')
                                depths.append(float(tmp[0]))
                                ratios.append(float(tmp[1]))
                            self.Depths10.append(depths)
                            self.Ratios10.append(ratios)
                        except:
                            self.error = True
                            self.message = 'Error processing from line {0}'.format(block_line)
                            return
            if line.find('[PREBURST25]') >= 0:
                finished = False
                read_header = True
                for block_line in fi:
                    data = block_line.split(',')
                    finished = (data[0] == '\n' or block_line.find('[PREBURST25_META]') >= 0)
                    if finished:
                        break
                    if read_header:
                        read_header = False
                    else:
                        try:
                            depths = []
                            ratios = []
                            for i in range(len(self.AEP)):
                                # get rid of brackets and split, can be done with regular expression
                                tmp = data[1 + i].replace('(', ',').replace(')', ',').split(',')
                                depths.append(float(tmp[0]))
                                ratios.append(float(tmp[1]))
                            self.Depths25.append(depths)
                            self.Ratios25.append(ratios)
                        except:
                            self.error = True
                            self.message = 'Error processing from line {0}'.format(block_line)
                            return
            if line.find('[PREBURST75]') >= 0:
                finished = False
                read_header = True
                for block_line in fi:
                    data = block_line.split(',')
                    finished = (data[0] == '\n' or block_line.find('[PREBURST75_META]') >= 0)
                    if finished:
                        break
                    if read_header:
                        read_header = False
                    else:
                        try:
                            depths = []
                            ratios = []
                            for i in range(len(self.AEP)):
                                # get rid of brackets and split, can be done with regular expression
                                tmp = data[1 + i].replace('(', ',').replace(')', ',').split(',')
                                depths.append(float(tmp[0]))
                                ratios.append(float(tmp[1]))
                            self.Depths75.append(depths)
                            self.Ratios75.append(ratios)
                        except:
                            self.error = True
                            self.message = 'Error processing from line {0}'.format(block_line)
                            return
            if line.find('[PREBURST90]') >= 0:
                finished = False
                read_header = True
                for block_line in fi:
                    data = block_line.split(',')
                    finished = (data[0] == '\n' or block_line.find('[PREBURST90_META]') >= 0)
                    if finished:
                        break
                    if read_header:
                        read_header = False
                    else:
                        try:
                            depths = []
                            ratios = []
                            for i in range(len(self.AEP)):
                                # get rid of brackets and split, can be done with regular expression
                                tmp = data[1 + i].replace('(', ',').replace(')', ',').split(',')
                                depths.append(float(tmp[0]))
                                ratios.append(float(tmp[1]))
                            self.Depths90.append(depths)
                            self.Ratios90.append(ratios)
                        except:
                            self.error = True
                            self.message = 'Error processing from line {0}'.format(block_line)
                            return
                if finished:
                    break
        try:
            if len(self.Depths50) > 0:
                self.Depths50 = numpy.array(self.Depths50)
                self.Ratios50 = numpy.array(self.Ratios50)
                self.Depths10 = numpy.array(self.Depths10)
                self.Ratios10 = numpy.array(self.Ratios10)
                self.Depths25 = numpy.array(self.Depths25)
                self.Ratios25 = numpy.array(self.Ratios25)
                self.Depths75 = numpy.array(self.Depths75)
                self.Ratios75 = numpy.array(self.Ratios75)
                self.Depths90 = numpy.array(self.Depths90)
                self.Ratios90 = numpy.array(self.Ratios90)
            else:
                self.Depths50 = numpy.zeros([11, 6])
                self.Ratios50 = numpy.zeros([11, 6])
                self.Depths10 = numpy.zeros([11, 6])
                self.Ratios10 = numpy.zeros([11, 6])
                self.Depths25 = numpy.zeros([11, 6])
                self.Ratios25 = numpy.zeros([11, 6])
                self.Depths75 = numpy.zeros([11, 6])
                self.Ratios75 = numpy.zeros([11, 6])
                self.Depths90 = numpy.zeros([11, 6])
                self.Ratios90 = numpy.zeros([11, 6])
                self.AEP = [50.0, 20.0, 10.0, 5.0, 1.0]
                self.AEP_names = ['50%', '20%', '10%', '5%', '2%', '1%']
                self.Duration = [60, 90, 120, 180, 360, 720, 1080, 1440, 2160, 2880, 4320]
                self.error = True
                self.message = 'Error processing Preburst Rainfall. Check ARR_Web_data.txt.'
        except:
            self.error = True
            self.message = 'Error in preburst depth data.'
        fi.seek(0)  # rewind file
        self.loaded = True
        #print('Finished reading file.')
        self.logger.info('Finished reading file.')


# noinspection Annotator,PyBroadException
class ArrCCF:
    def __init__(self):  # initialise the ARR interim  Climate Change Factors
        self.loaded = False
        self.error = False
        self.message = None
        self.Year = []
        self.RCP4p5 = []
        self.RCP6 = []
        self.RCP8p5 = []
        self.Meta = ArrMeta()
        self.logger = logging.getLogger('ARR2019')

    def load(self, fi):
        for line in fi:
            if line.find('[CCF]') >= 0:
                finished = False
                for block_line in fi:
                    if block_line.find('[CCF_META]') >= 0:
                        self.Meta.read(fi)
                        finished = True
                        break
                    if not finished:
                        if 'rcp' in block_line.lower():
                            continue
                        elif block_line == '\n':
                            continue
                        try:
                            data = block_line.split(',')
                            self.Year.append(int(data[0]))
                            self.RCP4p5.append(float(re.split(r'[\(\)%+]', data[1])[1]))
                            self.RCP6.append(float(re.split(r'[\(\)%+]', data[2])[1]))
                            self.RCP8p5.append(float(re.split(r'[\(\)%+]', data[3])[1]))
                        except:
                            self.error = True
                            self.message = 'Error processing climate change factor line {0}'.format(block_line)
                            return
                if finished:
                    break
        fi.seek(0)  # rewind file
        self.loaded = True
        #print('Finished reading file.')
        self.logger.info('Finished reading file.')


class ArrTemporal:
    def __init__(self):  # initialise the ARR temoral pattern class
        self.loaded = False
        self.error = False
        self.message = None
        self.tpCount = 0
        # point temporal pattern data
        self.pointID = []
        self.pointDuration = []
        self.pointTimeStep = []
        self.pointRegion = []
        self.pointAEP_Band = []
        self.pointincrements = []
        # areal temporal pattern data
        self.arealID = {}  # dict {tp catchment area: [id]} e.g. { 100: [ 9802, 9803, 9804, .. ], 200: [ .. ], ..  }
        self.arealDuration = {}  # dict {tp cathcment area: [duration]} e.g. { 100: [ 10, 10, 10, .. ] }
        self.arealTimeStep = {}  # dict {tp catchment area: [timestep]} e.g. { 100: [ 5, 5, 5, .. ] }
        self.arealRegion = {}  # dict {tp catchment area: [region]} e.g. { 100: [ 'Wet Tropics', .. ] }
        self.arealAEP_Band = {}  # dict {tp catchment area: [aep band]} e.g. { 100: [ 'frequent', .. ] }
        self.arealincrements = {}  # dict {tp catchment area: [increments]} e.g. { 100: [ [ 53.95, 46.05 ], .. ] }
        # adopted temporal pattern data
        self.ID = []
        self.Duration = []
        self.TimeStep = []
        self.Region = []
        self.AEP_Band = []
        self.increments = []  # list of rainfall increments, length varies depending on duration
        self.tpRegion = ''  # extracted before patterns start

        self.logger = logging.getLogger('ARR2019')
    
    def load(self, fname, fi, tpRegion, point_tp_csv, areal_tp_csv, areal_tp_download=None):
        """Load ARR data"""
        
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
            raise SystemExit("Error loading point temporal patterns")
            
        if areal_tp_csv is not None:
            #print("Loading areal temporal patterns from user input: {0}".format(areal_tp_csv))
            self.logger.info("Loading areal temporal patterns from user input: {0}".format(areal_tp_csv))
            self.loadArealTpFromCSV(areal_tp_csv)
            if self.error:
                #print("ERROR loading areal temporal patterns: {0}".format(self.message))
                self.logger.error("ERROR loading areal temporal patterns: {0}".format(self.message))
                raise SystemExit("Error loading areal temporal patterns")

        if areal_tp_download is not None:
            #print("Loading areal temporal patterns from user input: {0}".format(areal_tp_csv))
            self.logger.info("Loading areal temporal patterns from download: {0}".format(areal_tp_download))
            self.loadArealTpFromCSV(areal_tp_download)
            if self.error:
                #print("ERROR loading areal temporal patterns: {0}".format(self.message))
                self.logger.error("ERROR loading areal temporal patterns: {0}".format(self.message))
                raise SystemExit("Error loading areal temporal patterns")
    
    def loadPointTpFromDownload(self, fi, tpRegion):
        self.tpRegion = tpRegion
        for line in fi:
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
            self.error = True
            self.message = 'No temporal patterns found. Please check "ARR_web_data" to see if temporal patterns are present.'
        self.loaded = True
        #print('Finished reading file.')
        self.logger.info('Finished reading file.')

    def append(self, fi):
        for line in fi:
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
        self.loaded = True
        #print('Finished reading file.')
        self.logger.info('Finished reading file.')

    def loadPointTpFromCSV(self, tp):
        """
        Load point temporal patterns from csv (i.e. "_Increments.csv")
        
        :param tp: str full file path to csv
        :return: void
        """
        
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
        
    def combineArealTp(self, area):
        """
        Combines point temporal pattern with areal temporal patterns
        
        :param area: float catchment area
        :return: void
        """
        
        # determine if areal pattern is needed
        # if yes, which one
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

        self.ID = self.pointID[:]
        self.Duration = self.pointDuration[:]
        self.TimeStep = self.pointTimeStep[:]
        self.Region = self.pointRegion[:]
        self.AEP_Band = self.pointAEP_Band[:]
        self.increments = self.pointincrements[:]
        
        # check if there are any areal temporal patterns available
        if self.arealDuration:
           # check if areal patterns are required for catchment size
            if tp_area is not None:
                point_durations = self.getTemporalPatternDurations(self.pointDuration)
                areal_durations = self.getTemporalPatternDurations(self.arealDuration[tp_area])
                inclusions, exclusions = self.getExclusions(point_durations, areal_durations)
                printed_messages = []
                k = 0
                for i, dur in enumerate(self.Duration):
                    if dur >= inclusions[0]:
                        if dur not in exclusions:
                            m = self.arealRegion[tp_area].index(self.Region[i])
                            j = self.arealDuration[tp_area][m:].index(dur) + m
                            if self.Region[i] == self.arealRegion[tp_area][j]:
                                self.ID[i] = self.arealID[tp_area][j + k]
                                self.TimeStep[i] = self.arealTimeStep[tp_area][j + k]
                                self.increments[i] = self.arealincrements[tp_area][j + k]
                                if k == 9:
                                    k = 0
                                else:
                                    k += 1
                        else:
                            message = "WARNING: {0} min duration does not have an areal temporal pattern... using point temporal pattern".format(dur)
                            if message not in printed_messages:
                                #print(message)
                                self.logger.warning(message)
                                printed_messages.append(message)
        
        self.getTPCount()

    def get_dur_aep(self, duration, aep):
        # print ('Getting all events with duration {0} min and AEP band {1}'.format(duration,AEP))
        id_ = []
        increments = []
        timestep = []
        for i in range(len(self.ID)):
            if self.Duration[i] == duration and self.AEP_Band[i] == aep.lower():
                id_.append(self.ID[i])
                increments.append(self.increments[i])
                timestep.append(self.TimeStep[i])
        return id_, increments, timestep

    def get_dur_aep_pb(self, duration, aep, preburst_pattern_method, preburst_pattern_dur,
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
            self.logger.info(f"For complete storm {aep_name} {duration} min using constant preburst rate of {dur} mins")
        else:
            if bpreburst_dur_proportional:
                dur = duration * float(preburst_pattern_dur)
            else:
                if re.findall(r"hr", preburst_pattern_dur, re.IGNORECASE):
                    dur = float(preburst_pattern_dur.strip(' hr')) * 60.
                elif re.findall(r"min", preburst_pattern_dur, re.IGNORECASE):
                    dur = float(preburst_pattern_dur.strip(' min'))
            dur = self.findClosestTP(dur)
            self.logger.info(f"For complete storm {aep_name} {duration} min "
                             f"using ARR Temporal pattern for preburst: {dur} mins, {preburst_pattern_tp}")
            id, increments, timestep = self.get_dur_aep(dur, aep)

            tp = int(re.findall(r"\d{2}", preburst_pattern_tp)[0])
            increments = increments[tp]
            timestep = timestep[tp]

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
        self.logger = logging.getLogger('ARR2019')

    def load(self, fname, area, **kwargs):
        
        # deal with kwargs
        add_tp = kwargs['add_tp'] if 'add_tp' in kwargs else None
        point_tp_csv = kwargs['point_tp'] if 'point_tp' in kwargs else None
        areal_tp_csv = kwargs['areal_tp'] if 'areal_tp' in kwargs else None
        user_initial_loss = kwargs['user_initial_loss'] if 'user_initial_loss' in kwargs else None
        user_continuing_loss = kwargs['user_continuing_loss'] if 'user_continuing_loss' in kwargs else None
        areal_tp_download = kwargs['areal_tp_download'] if 'areal_tp_download' in kwargs else None

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
            raise SystemExit('Unexpected error opening file {0}'.format(fname))

        # INPUT DATA
        #print('Loading Input Data Block')
        self.logger.info('Loading Input Data Block')
        self.Input.load(fi)
        if self.Input.error:
            #print('An error was encountered, when reading Input Data Information.')
            self.logger.error('An error was encountered, when reading Input Data Information.')
            #print('Return message = {0}'.format(self.Input.message))
            self.logger.error('Return message = {0}'.format(self.Input.message))
            raise SystemExit("ERROR: {0}".format(self.Input.message))

        # RIVER REGION
        #print('Loading River Region Block')
        self.logger.info('Loading River Region Block')
        self.RivReg.load(fi)
        if self.RivReg.error:
            #print('An error was encountered, when reading River Region Information.')
            self.logger.error('An error was encountered, when reading River Region Information.')
            #print('Return message = {0}'.format(self.RivReg.message))
            self.logger.error('Return message = {0}'.format(self.RivReg.message))
            raise SystemExit("ERROR: {0}".format(self.RivReg.message))

        # ARF
        #print('Loading ARF block')
        self.logger.info('Loading ARF block')
        self.Arf.load(fi)
        if self.Arf.error:
            #print('An error was encountered, when reading ARF information.')
            self.logger.error('An error was encountered, when reading ARF information.')
            #print('Return message = {0}'.format(self.Arf.message))
            self.logger.error('Return message = {0}'.format(self.Arf.message))
            raise SystemExit("ERROR: {0}".format(self.Arf.message))

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
            raise SystemExit("ERROR: {0}".format(self.CCF.message))

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
            raise SystemExit("ERROR: {0}".format(self.Temporal.message))
        if add_tp != False:
            if len(add_tp) > 0:
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
                        raise SystemExit("ERROR: {0}".format(self.Temporal.message))

        self.Temporal.combineArealTp(area)


        # PREBURST DEPTH
        #print('Loading median preburst data')
        self.logger.info('Loading median preburst data')
        self.PreBurst.load(fi)
        if self.PreBurst.error:
            #print('An error was encountered, when reading median preburst data.')
            self.logger.error('An error was encountered, when reading median preburst data.')
            #print('Return message = {0}'.format(self.PreBurst.message))
            self.logger.error('Return message = {0}'.format(self.PreBurst.message))

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

        # convert input RCP if 'all' is specified
        if str(cc_RCP).lower() == 'all':
            cc_RCP = ['RCP4.5', 'RCP6', 'RCP8.5']
        # convert cc years if 'all' is specified
        if str(cc_years).lower() == 'all':
            cc_years = self.CCF.Year

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
            fo_arf_depths.close

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
            if len(cc_years) < 1:
                #print('No year(s) specified when considering climate change.')
                self.logger.error('No year(s) specified when considering climate change.')
                raise SystemExit('ERROR: no year(s) specified in Climate Change consideration')
            if len(cc_RCP) < 1:
                #print('No RCP(s) specified when considering climate change.')
                self.logger.error('No RCP(s) specified when considering climate change.')
                raise SystemExit('ERROR: no RCP(s) specified in Climate Change consideration.')
            for year, k in cc_years_dict.items():
                # j is year index of year in self.CCF.Year so multiplier can be extracted
                if year not in self.CCF.Year:
                    #print('Climate change year ({0}) not recognised, or not a valid year.'.format(year))
                    self.logger.error('Climate change year ({0}) not recognised, or not a valid year.'.format(year))
                    raise SystemExit('ERROR: Climate change year ({0}) not recognised, or not a valid year.'.format(year))
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
                        raise SystemExit("ERROR: Climate change RCP ({0}) not recognised, or valid".format(rcp))

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
                if float(self.Losses.ils) < 0:
                    ilb_complete = ilb_complete * (self.Losses.ils_user / self.Losses.ils)
                else:
                    self.logger.warning(
                        "WARNING: Cannot calculate initial losses from user input because Storm Initial is zero")

        else:  # original method of using preburst and storm loss
            # write out burst initial loss
            if preBurst == '10%':
                preBurst_depths = self.PreBurst.Depths10
                preBurst_ratios = self.PreBurst.Ratios10
            elif preBurst == '25%':
                preBurst_depths = self.PreBurst.Depths25
                preBurst_ratios = self.PreBurst.Ratios25
            elif preBurst == '50%':
                preBurst_depths = self.PreBurst.Depths50
                preBurst_ratios = self.PreBurst.Ratios50
            elif preBurst == '75%':
                preBurst_depths = self.PreBurst.Depths75
                preBurst_ratios = self.PreBurst.Ratios75
            elif preBurst == '90%':
                preBurst_depths = self.PreBurst.Depths90
                preBurst_ratios = self.PreBurst.Ratios90
            else:
                preBurst_depths = self.PreBurst.Depths50
                preBurst_ratios = self.PreBurst.Ratios50

            # generate same size numpy arrays for burst and preburst data based on common AEPs and Durations
            b_com_aep, b_com_dur, b_dep_com, b_com_dur_index = common_data(bom.aep_names, bom.duration,
                                                                           self.PreBurst.AEP_names,
                                                                           self.PreBurst.Duration,
                                                                           bom.depths)
            pb_com_aep, pb_com_dur, pb_dep_com, pb_com_dur_index = common_data(self.PreBurst.AEP_names,
                                                                               self.PreBurst.Duration,
                                                                               bom.aep_names,
                                                                               bom.duration, preBurst_depths)
            pb_com_aep, pb_com_dur, pb_rto_com, pb_com_dur_index = common_data(self.PreBurst.AEP_names,
                                                                               self.PreBurst.Duration,
                                                                               bom.aep_names,
                                                                               bom.duration, preBurst_ratios)

            # calculate the maximum preburst depths
            pb_rto_d_com = numpy.multiply(b_dep_com, pb_rto_com)  # convert preburst ratios to depths
            # pb_dep_final = numpy.maximum(pb_dep_com, pb_rto_d_com)  # take the max of preburst ratios and depths
            pb_dep_final = pb_dep_com

            # calculate burst intial loss (storm il minus preburst depth)
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
            raise SystemExit("ERROR: File is locked for editing {0}".format(fname_losses_out))
        except IOError:
            # print('Unexpected error opening file {0}'.format(fname_losses_out))
            self.logger.error('Unexpected error opening file {0}'.format(fname_losses_out))
            raise SystemExit('ERROR: Unexpected error opening file {0}'.format(fname_losses_out))
        if self.Losses.existsPNLosses and probability_neutral_losses:
            if self.Losses.ils_user is not None:
                flosses.write(
                    'This File has been generated using ARR_to_TUFLOW. The Burst losses have been calculated by '
                    'using Probability Neutral Burst Initial Losses provided by the Datahub and the user '
                    f'provided initial loss value of {self.Losses.ils_user} mm. '
                    'Eqn: IL Burst = User IL x IL Burst ARR / IL Storm ARR\n')
            else:
                flosses.write(
                    'This File has been generated using ARR_to_TUFLOW. The Burst losses have been calculated by '
                    'using Probability Neutral Burst Initial Losses provided by the Datahub.\n')
        else:
            if self.Losses.ils_user is not None:
                flosses.write(
                    'This File has been generated using ARR_to_TUFLOW. The Burst losses have been calculated by '
                    'subtracting the maximum preburst (Depth or Ratios) from the user defined initial loss '
                    f'value of {self.Losses.ils_user} mm.\n')
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
            if process_aep:  # AEP data exists
                if all_duration:
                    # need to specify AEP_band based on AEP specified
                    arr_durations = self.Temporal.get_durations(aep_band)
                    dur_list = sorted(list(set(arr_durations).intersection(bom.duration)))
                # loop through all durations
                for d, duration in enumerate(dur_list):
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
                        ids, increments, dts = self.Temporal.get_dur_aep(duration, aep_band)
                        increments_pb = []
                        dts_pb = 0
                        pb_depth = 0
                        if bComplete_storm:
                            if self.Losses.existsPNLosses and probability_neutral_losses:
                                self.logger.warning("WARNING: Cannot use complete storm and Probability Neutral Burst"
                                                    "Initial Losses... using design storm")
                            else:
                                i = aep_ind
                                j = dur_ind
                                try:
                                    pb_depth = pb_dep_final_complete[j,i]
                                    if numpy.isnan(pb_depth):
                                        self.logger.warning(
                                            f"WARNING: No preburst depths exist for aep/duration [{aep}/{duration} min]"
                                            "... using design storm")
                                    else:
                                        increments_pb, dts_pb = self.Temporal.get_dur_aep_pb(duration, aep_band,
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
                        for i in range(nid):
                            i2 = 1
                            for j in range(len(increments_pb)):
                                rf_array[i, i2] = increments_pb[j] * pb_depth / 100.
                                i2 += 1
                            for j in range(len(increments[i])):
                                #rf_array[i, j + 1] = increments[i][j] * depth / 100.
                                rf_array[i, i2] = increments[i][j] * depth / 100.
                                i2 += 1
                        if cc:
                            # add climate change temporal patter to array so it can be written to same file
                            for year, k in cc_years_dict.items():
                                # k is year correct index of year in self.CCF.Year so multiplier can be extracted
                                for rcp in cc_RCP:
                                    if rcp == 'RCP4.5':
                                        cc_multip = (self.CCF.RCP4p5[k] / 100) + 1
                                    elif rcp == 'RCP6':
                                        cc_multip = (self.CCF.RCP6[k] / 100) + 1
                                    elif rcp == 'RCP8.5':
                                        cc_multip = (self.CCF.RCP8p5[k] / 100) + 1
                                    cc_rf_array = np.zeros([nid, ntimes])
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
                            raise SystemExit('Unexpected error opening file {0}'.format(outfname))
                        except PermissionError:
                            #print("File is locked for editing {0}".format(outfname))
                            self.logger.error("File is locked for editing {0}".format(outfname))
                            raise SystemExit("File is locked for editing {0}".format(outfname))
                        # ts1
                        fo.write('! Written by TUFLOW ARR Python Script based on {0} temporal pattern\n'.format
                                 (aep_band))
                        if out_form == 'ts1':
                            line3 = 'Time (min)'
                        else:
                            line3 = 'Time (hour)'

                        line1 = "Start_Index"
                        line2 = "End_Index"

                        tp_cc = False
                        cc_event_index = 0  # index to call correct name from cc_events
                        # create a list 1 - 10 repeated for all temporal pattern sets
                        for i in [k for k in range(1, tpCount+1)] * (len(cc_years) * len(cc_RCP) + 1):
                            line1 = line1 + ', 1'
                            line2 = line2 + ', {0}'.format(ntimes)
                            if i < tpCount and not tp_cc:  # standard temporal pattern
                                line3 = line3 + ', TP{0:02d}'.format(i)
                            elif i == tpCount and not tp_cc:  # last standard temporal pattern, make cc true so cc next iter
                                tp_cc = True
                                line3 = line3 + ', TP{0:02d}'.format(i)
                            else:  # add climate change name to temporal pattern
                                if cc:
                                    line3 = line3 + ', TP{0:02d}_{1}'.format(i, cc_events[cc_event_index])
                                    cc_event_index += 1
                                else:
                                    break
                        if out_form == 'ts1':
                            fo.write('{0}, {1}\n'.format(nid, ntimes))
                            fo.write(line1 + '\n')
                            fo.write(line2 + '\n')
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
    #        raise SystemExit("ERROR: File is locked for editing {0}".format(fname_losses_out))
    #    except IOError:
    #        #print('Unexpected error opening file {0}'.format(fname_losses_out))
    #        self.logger.error('Unexpected error opening file {0}'.format(fname_losses_out))
    #        raise SystemExit('ERROR: Unexpected error opening file {0}'.format(fname_losses_out))
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
                raise SystemExit("ERROR: File is locked for editing: {0}".format(bc_fname))
            except IOError:
                #print('Unexpected error opening file {0}'.format(bc_fname))
                self.logger.error('Unexpected error opening file {0}'.format(bc_fname))
                raise SystemExit('ERROR: Unexpected error opening file {0}'.format(bc_fname))
            bcdb.write('Name,Source,Column 1, Column 2\n')
            if out_form == 'ts1':
                bcdb.write('{0},rf_inflow\{0}_RF_~{1}~~DUR~.{2},Time (min), ~TP~\n'.format(site_name,
                                                                                           out_notation.upper(),
                                                                                           out_form))
            else:
                bcdb.write('{0},rf_inflow\{0}_RF_~{1}~~DUR~.{2},Time (hour), ~TP~\n'.format(site_name,
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
                raise SystemExit("ERROR: File is locked for editing: {0}".format(bc_fname))
            except IOError:
                #print('Unexpected error opening file {0}'.format(bc_fname))
                self.logger.error('Unexpected error opening file {0}'.format(bc_fname))
                raise SystemExit('ERROR: Unexpected error opening file {0}'.format(bc_fname))
            if out_form == 'ts1':
                bcdb.write('{0},rf_inflow\{0}_RF_~{1}~~DUR~.{2},Time (min), ~TP~\n'.format(site_name,
                                                                                           out_notation.upper(),
                                                                                           out_form))
            else:
                bcdb.write('{0},rf_inflow\{0}_RF_~{1}~~DUR~.{2},Time (hour), ~TP~\n'.format(site_name,
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
                    raise SystemExit("ERROR: File is locked for editing: {0}".format(bc_fname_cc))
                except IOError:
                    #print('Unexpected error opening file {0}'.format(bc_fname_cc))
                    self.logger.error('Unexpected error opening file {0}'.format(bc_fname_cc))
                    raise SystemExit('ERROR: Unexpected error opening file {0}'.format(bc_fname_cc))
                bcdb_cc.write('Name,Source,Column 1, Column 2\n')
                if out_form == 'ts1':
                    bcdb_cc.write('{0},rf_inflow\{0}_RF_~{1}~~DUR~.{2},Time (min), ~TP~_~CC~\n'.
                                  format(site_name, out_notation.upper(), out_form))
                else:
                    bcdb_cc.write('{0},rf_inflow\{0}_RF_~{1}~~DUR~.{2},Time (hour), ~TP~_~CC~\n'.
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
                    raise SystemExit("ERROR: File is locked for editing: {0}".format(bc_fname_cc))
                except IOError:
                    #print('Unexpected error opening file {0}'.format(bc_fname_cc))
                    self.logger.error('Unexpected error opening file {0}'.format(bc_fname_cc))
                    raise SystemExit('ERROR: Unexpected error opening file {0}'.format(bc_fname_cc))
                if out_form == 'ts1':
                    bcdb_cc.write('{0},rf_inflow\{0}_RF_~{1}~~DUR~.{2},Time (min), ~TP~_~CC~\n'.
                                  format(site_name, out_notation.upper(), out_form))
                else:
                    bcdb_cc.write('{0},rf_inflow\{0}_RF_~{1}~~DUR~.{2},Time (hour), ~TP~_~CC~\n'.
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
            raise SystemExit("ERROR: File is locked for editing: {0}".format(tef_fname))
        except IOError:
            #print('Unexpected error opening file {0}'.format(tef_fname))
            self.logger.error('Unexpected error opening file {0}'.format(tef_fname))
            raise SystemExit('ERROR: Unexpected error opening file {0}'.format(tef_fname))
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
        for i in range(tpCount):
            tef.write('Define Event == tp{0:02d}\n'.format(i + 1))
            tef.write('    BC Event Source == ~TP~ | TP{0:02d}\n'.format(i + 1))
            tef.write('End Define\n\n')

        if cc:
            tef.write('!CLIMATE CHANGE YEAR\n')
            scenario_prev = ''
            i = 1
            for scenario in cc_events:
                if scenario != scenario_prev:
                    tef.write('Define Event == cc{0:02d}\n'.format(i))
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
                raise SystemExit("ERROR: File is locked for editing: {0}".format(tsoilf))
            except IOError:
                #print('Unexpected error opening file {0}'.format(tsoilf))
                self.logger.error('Unexpected error opening file {0}'.format(tsoilf))
                raise SystemExit('ERROR: Unexpected error opening file {0}'.format(tsoilf))
            if catch_no == 0:
                tsoilf_open.write('! Soil ID, Method, IL, CL\n')
            increment = 1
            if urban_initial_loss is not None and urban_continuing_loss is not None:
                increment = 2
                if catch_no == 0:
                    tsoilf_open.write('1, ILCL, {0}, {1},  ! Impervious Area Rainfall Losses\n'.format(urban_initial_loss, urban_continuing_loss))
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
                materials_open.write("Material ID, Manning's n, Rainfall Loss Parameters, Land Use Hazard ID, ! Description\n")
            increment = 1
            if urban_initial_loss is not None and urban_continuing_loss is not None:
                increment = 2
                if catch_no == 0:
                    materials_open.write('1,,"{0}, {1}",,! Impervious Area Rainfall Losses\n'.format(urban_initial_loss, urban_continuing_loss))
            materials_open.write('{1:.0f},,"<<IL_{0}>>, <<CL_{0}>>",,! Design ARR2016 Losses for catchment {0}\n'.format(site_name, catch_no + increment))
            materials_open.close()
        
        rareMag2Name = {'0.5%': '1 in 200', '0.2%': '1 in 500', '0.1%': '1 in 1000',
                        '0.05%': '1 in 2000'}
        # write trd losses file
        trd = os.path.join(fpath, 'rainfall_losses.trd')
        if catch_no == 0:  # write new file
            try:
                trd_open = open(trd, 'w')
            except PermissionError:
                #print("File is locked for editing: {0}".format(trd))
                self.logger.error("File is locked for editing: {0}".format(trd))
                raise SystemExit("ERROR: File is locked for editing: {0}".format(trd))
            except IOError:
                #print('Unexpected error opening file {0}'.format(trd))
                self.logger.error('Unexpected error opening file {0}'.format(trd))
                raise SystemExit('ERROR: Unexpected error opening file {0}'.format(trd))
            trd_open.write("! TUFLOW READ FILE - SET RAINFALL LOSS VARIABLES\n")
            for i, aep in enumerate(aep_list_formatted):
                if i == 0:
                    trd_open.write("If Event == {0}\n".format(aep))
                else:
                    trd_open.write("Else If Event == {0}\n".format(aep))
                if aep_list[i] in rareMag2Name:
                    mag_index = bom.aep_names.index(rareMag2Name[aep_list[i]])
                else:
                    mag_index = bom.aep_names.index(aep_list[i])
                for j, dur in enumerate(dur_list_formatted):
                    if j == 0:
                        trd_open.write("    If Event == {0}m\n".format(dur))
                    else:
                        trd_open.write("    Else If Event == {0}m\n".format(dur))
                    # get intial loss value
                    dur_index = bom.duration.index(dur_list[j])
                    #il = ilb_complete[dur_index, mag_index]
                    il = il_complete[dur_index, mag_index]
                    if np.isnan(il):
                        il = 0
                    trd_open.write("        Set Variable IL_{1} == {0:.1f}\n".format(il, site_name))
                    trd_open.write("        Set Variable CL_{1} == {0:.1f}\n".format(float(self.Losses.cls), site_name))
                trd_open.write("    Else\n")
                trd_open.write("        Pause == Event Not Recognised\n")
                trd_open.write("    End If\n")
            trd_open.write("Else\n")
            trd_open.write("    Pause == Event Not Recognised\n")
            trd_open.write("End If")
            trd_open.close()
        else:  # insert losses in already defined IF statements rather than straight append
            try:
                trd_text = []
                insert_index = []
                insert_il = []
                k = 0
                with open(trd, 'r') as trd_open:
                    for i, line in enumerate(trd_open):
                        i = k + 1
                        trd_text.append(line)
                        if 'If Event' in line:  # first level would be mag
                            ind = line.find('If Event')
                            if '!' not in line[:ind]:
                                command, mag = line.split('==')
                                mag = mag.split('!')[0]
                                mag = mag.strip()
                                if mag[-1] == 'y':
                                    unit = 'ARI'
                                elif mag[-1] == 'p':
                                    unit = 'AEP'
                                else:
                                    unit = 'EY'
                                    mag = mag[:-1]
                                mag = convertMagToAEP(mag, unit, frequent_events)
                                if mag in rareMag2Name:
                                    mag_index = bom.aep_names.index(rareMag2Name[mag])
                                else:
                                    mag_index = bom.aep_names.index(mag)
                                for j, subline in enumerate(trd_open):
                                    k = i + j + 1
                                    trd_text.append(subline)
                                    if 'If Event' in subline:  # sub level would be dur
                                        ind = line.find('If Event')
                                        if '!' not in line[:ind]:
                                            command, dur = subline.split('==')
                                            dur = dur.split('!')[0]
                                            dur = dur.strip().strip('m')
                                            dur_index = bom.duration.index(int(dur))
                                            #il = ilb_complete[dur_index, mag_index]
                                            il = il_complete[dur_index, mag_index]
                                            if np.isnan(il):
                                                il = 0
                                            insert_index.append(k + catch_no * 2 + 1)
                                            insert_il.append(il)
                                    if 'End If' in subline:
                                        break
            except PermissionError:
                #print("File is locked for editing: {0}".format(trd))
                self.logger.error("File is locked for editing: {0}".format(trd))
                raise SystemExit("ERROR: File is locked for editing: {0}".format(trd))
            except IOError:
                #print('Unexpected error opening file {0}'.format(trd))
                self.logger.error('Unexpected error opening file {0}'.format(trd))
                raise SystemExit('ERROR: Unexpected error opening file {0}'.format(trd))
            
            if trd_text:
                for i, j in enumerate(reversed(insert_index)):
                    j = int(j)
                    k = int(len(insert_index) - 1 - i)
                    trd_text.insert(j, '        Set Variable CL_{0} == {1:.1f}\n'.format(site_name, float(self.Losses.cls)))
                    trd_text.insert(j, '        Set Variable IL_{0} == {1:.1f}\n'.format(site_name, insert_il[k]))
                text = ''
                for t in trd_text:
                    text += t
                try:
                    trd_open = open(trd, 'w')
                    trd_open.write(text)
                    trd_open.close()
                except PermissionError:
                    #print("File is locked for editing: {0}".format(trd))
                    self.logger.error("File is locked for editing: {0}".format(trd))
                    raise SystemExit("ERROR: File is locked for editing: {0}".format(trd))
                except IOError:
                    #print('Unexpected error opening file {0}'.format(trd))
                    self.logger.error('Unexpected error opening file {0}'.format(trd))
                    raise SystemExit('ERROR: Unexpected error opening file {0}'.format(trd))

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
    