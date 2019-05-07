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
        print('Finished reading file.')


# noinspection PyBroadException
class ArrInput:
    def __init__(self):  # initialise the ARR input data class
        self.loaded = False
        self.error = False
        self.message = None
        self.Latitude = None
        self.Longitude = None

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
        print('Finished reading file.')


class ArrArf:
    def __init__(self):  # initilise the ARR Areal Reduction Factors
        self.loaded = False
        self.error = False
        self.message = None
        self.param = {}

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
        print('Finished reading file.')


class ArrLosses:
    def __init__(self):  # initialise the ARR storm losses
        self.loaded = False
        self.error = False
        self.message = None
        self.ils = None
        self.cls = None

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
                        self.ils = data[1]
                    if data[0].lower() == 'storm continuing losses (mm/h)':
                        self.cls = data[1]
                if finished:
                    break
        if self.ils is None or self.cls is None:
            self.error = True
            self.message = 'Error processing Storm Losses. This may be because you have selected an urban area.'
            self.ils = 0
            self.cls = 0
        fi.seek(0)  # rewind file
        self.loaded = True
        print('Finished reading file.')


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
        print('Finished reading file.')


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
        print('Finished reading file.')


class ArrTemporal:
    def __init__(self):  # initialise the ARR temoral pattern class
        self.loaded = False
        self.error = False
        self.message = None
        self.ID = []
        self.Duration = []
        self.TimeStep = []
        self.Region = []
        self.AEP_Band = []
        self.increments = []  # list of rainfall increments, length varies depending on duration

    def load(self, fi):
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
                        try:
                            self.ID.append(int(data[0]))
                            dur = int(data[1])
                            self.Duration.append(dur)
                            inc = int(data[2])
                            self.TimeStep.append(inc)
                            self.Region.append(data[3])
                            self.AEP_Band.append(data[4].lower())
                        except:
                            self.error = True
                            self.message = 'Error processing line {0}'.format(block_line)
                            return
                        try:
                            incs = []
                            for i in range(int(dur / inc)):
                                incs.append(float(data[5 + i]))
                            self.increments.append(incs)
                        except:
                            self.error = True
                            self.message = 'Error processing from line {0}'.format(block_line)
                            return
                if finished:
                    break
        fi.seek(0)  # rewind file
        self.loaded = True
        print('Finished reading file.')

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
                        try:
                            self.ID.append(int(data[0]))
                            dur = int(data[1])
                            self.Duration.append(dur)
                            inc = int(data[2])
                            self.TimeStep.append(inc)
                            self.Region.append(data[3])
                            self.AEP_Band.append(data[4].lower())
                        except:
                            self.error = True
                            self.message = 'Error processing line {0}'.format(block_line)
                            return
                        try:
                            incs = []
                            for i in range(int(dur / inc)):
                                incs.append(float(data[5 + i]))
                            self.increments.append(incs)
                        except:
                            self.error = True
                            self.message = 'Error processing from line {0}'.format(block_line)
                            return
                if finished:
                    break
        fi.seek(0)  # rewind file
        self.loaded = True
        print('Finished reading file.')

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

    def get_durations(self, aep):
        # print ('Getting a list of durations with AEP band {0}'.format(AEP))
        duration_all = []
        for i in range(len(self.ID)):
            if self.AEP_Band[i] == aep.lower():
                duration_all.append(self.Duration[i])
        durations = sorted(set(duration_all))  # sorted, unique list
        return durations


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

    def load(self, fname, **kwargs):
        for kw in kwargs:
            if kw.lower() == 'add_tp':
                add_tp = kwargs[kw]
            else:
                self.error = True
                self.message = 'Unrecognised keyword argument: {0}'.format(kw)
                return

        print('Loading ARR website output .txt file')
        if not os.path.isfile(fname):
            self.error = True
            self.message = 'File does not exist {0}'.format(fname)
            return
        try:
            fi = open(fname, 'r')
        except IOError:
            print('Unexpected error opening file {0}'.format(fname))
            sys.exit("ERROR: Opening file.")

        # INPUT DATA
        print('Loading Input Data Block')
        self.Input.load(fi)
        if self.Input.error:
            print('An error was encountered, when reading Input Data Information.')
            print('Return message = {0}'.format(self.Input.message))
            sys.exit("ERROR: Reading Input Data Information.")

        # RIVER REGION
        print('Loading River Region Block')
        self.RivReg.load(fi)
        if self.RivReg.error:
            print('An error was encountered, when reading River Region Information.')
            print('Return message = {0}'.format(self.RivReg.message))
            sys.exit("ERROR: Reading River Region Information.")

        # ARF
        print('Loading ARF block')
        self.Arf.load(fi)
        if self.Arf.error:
            print('An error was encountered, when reading ARF information.')
            print('Return message = {0}'.format(self.Arf.message))
            sys.exit("ERROR: Reading ARF Information.")

        # STORM LOSSES
        print('Loading Storm Losses Block')
        self.Losses.load(fi)
        if self.Losses.error:
            print('An error was encountered, when reading Storm Losses Information.')
            print('Return message = {0}'.format(self.Losses.message))
            # sys.exit("ERROR: Reading Storm Losses Information.")

        # INTERIM CLIMATE CHANGE FACTOR
        print('Loading Interim Climate Change Factors Block')
        self.CCF.load(fi)
        if self.CCF.error:
            print('An error was encountered, when reading Interim Climate Change Factors Information.')
            print('Return message = {0}'.format(self.CCF.message))
            sys.exit("ERROR: Reading Interim Climate Change Factors Information.")

        # TEMPORAL PATTERNS
        print('Loading Temporal Patterns')
        self.Temporal.load(fi)
        if self.Temporal.error:
            print('An error was encountered, when reading temporal patterns.')
            print('Return message = {0}'.format(self.Temporal.message))
            sys.exit("ERROR: Reading temporal data.")
        if add_tp != False:
            if len(add_tp) > 0:
                for tp in add_tp:
                    f = "{0}_TP_{1}.txt".format(os.path.splitext(fname)[0], tp)
                    fadd_tp = open(f, 'r')
                    self.Temporal.append(fadd_tp)
                    fadd_tp.close()
                    if self.Temporal.error:
                        print('An error was encountered, when reading temporal pattern: {0}'.format(tp))
                        print('Return message = {0}'.format(self.Temporal.message))
                        sys.exit("ERROR: Reading temporal data.")


        # PREBURST DEPTH
        print('Loading median preburst data')
        self.PreBurst.load(fi)
        if self.PreBurst.error:
            print('An error was encountered, when reading median preburst data.')
            print('Return message = {0}'.format(self.PreBurst.message))
            # sys.exit("ERROR: Reading temporal data.")

        print('Data Loaded')

    def export(self, fpath, aep, dur, **keywords):
        for kw in keywords:
            if kw.lower() == 'format':
                if (keywords[kw]).lower() == 'csv':
                    out_form = 'csv'
                elif (keywords[kw]).lower() == 'ts1':
                    out_form = 'ts1'
                else:
                    self.error = True
                    self.message = \
                        'Unrecognised ouput format {0} - expecting "csv" or "ts1"'.format(keywords[kw].lower())
                    return
            elif kw.lower() == 'name':
                try:
                    site_name = keywords[kw]
                except:
                    self.error = True
                    self.message = 'Unable to Read Site Name: {0}'.format(keywords[kw])
            elif kw.lower() == 'climate_change':
                try:
                    cc = keywords[kw]
                except:
                    self.error = True
                    self.message = 'Unrecognised Climate Change argument: {0}'.format(keywords[kw].lower())
                    return
            elif kw.lower() == 'climate_change_years':
                try:
                    cc_years = keywords[kw]
                except:
                    self.error = True
                    self.message = 'Unable to process year from climate change years argument: {0}' \
                        .format(keywords[kw].lower())
                    return
            elif kw.lower() == 'cc_rcp':
                try:
                    cc_RCP = keywords[kw]
                except:
                    self.error = True
                    self.message = 'Unable to process RCP from climate change RCP argument: {0}' \
                        .format(keywords[kw].lower())
                    return
            elif kw.lower() == 'bom_data':
                try:
                    bom = keywords[kw]
                except:
                    self.error = True
                    self.message = 'Unable to process year from CCF_PH argument: {0}'.format(keywords[kw].lower())
                    return
            elif kw.lower() == 'area':
                try:
                    catchment_area = keywords[kw]
                except:
                    self.error = True
                    self.message = 'Unable to process catchment area argument: {0}'.format(keywords[kw].lower())
                    return
            elif kw.lower() == 'frequent':
                try:
                    frequent_events = keywords[kw]
                except:
                    self.error = True
                    self.message = 'Problem reading arguement: {0}'.format(keywords[kw].lower())
            elif kw.lower() == 'rare':
                try:
                    rare_events = keywords[kw]
                except:
                    self.error = True
                    self.message = 'Problem reading arguement: {0}'.format(keywords[kw].lower())

            elif kw.lower() == 'catch_no':
                try:
                    catch_no = keywords[kw]
                except:
                    self.error = True
                    self.message = 'Problem reading argument: {0}'.format(keywords[kw].lower())
            elif kw.lower() == 'out_notation':
                try:
                    out_notation = keywords[kw]
                except:
                    self.error = True
                    self.message = 'Problem reading argument: {0}'.format(keywords[kw].lower())
            elif kw.lower() == 'arf_frequent':
                try:
                    ARF_frequent = keywords[kw]
                except:
                    self.error = True
                    self.message = 'Problem reading argument: {0}'.format(keywords[kw].lower())
            elif kw.lower() == 'min_arf':
                try:
                    min_ARF = keywords[kw]
                except:
                    self.error = True
                    self.message = 'Problem reading argument: {0}'.format(keywords[kw].lower())
            elif kw.lower() == 'preburst':
                try:
                    preBurst = keywords[kw]
                except:
                    self.error = True
                    self.message = 'Problem reading argument: {0}'.format(keywords[kw].lower())
            elif kw.lower() == 'lossmethod':
                try:
                    lossMethod = keywords[kw]
                except:
                    self.error = True
                    self.message = 'Problem reading argument: {0}'.format(keywords[kw].lower())
            elif kw.lower() == 'mar':
                try:
                    mar = keywords[kw]
                except:
                    self.error = True
                    self.message = 'Problem reading argument: {0}'.format(keywords[kw].lower())
            elif kw.lower() == 'staticloss':
                try:
                    staticLoss = keywords[kw]
                except:
                    self.error = True
                    self.message = 'Problem reading argument: {0}'.format(keywords[kw].lower())
            elif kw.lower() == 'add_tp':
                try:
                    add_tp = keywords[kw]
                except:
                    self.error = True
                    self.message = 'Problem reading argument: {0}'.format(keywords[kw].lower())
            else:
                self.error = True
                self.message = 'Unrecognised keyword argument: {0}'.format(kw)
                return

        # convert input RCP if 'all' is specified
        if str(cc_RCP).lower() == 'all':
            cc_RCP = ['RCP4.5', 'RCP6', 'RCP8.5']
        # convert cc years if 'all' is specified
        if str(cc_years).lower() == 'all':
            cc_years = self.CCF.Year

        # create year dictionary with index as the value so the appropriate multiplier can be called from self.CCF
        # later on
        if add_tp != False:
            tpCount = 10 + 10 * len(add_tp)
        else:
            tpCount = 10
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
            if frequent_events:
                aep_conv = {5: '0.2EY', 2: '0.5EY', 1: '63.2%'}
            else:
                aep_conv = {5: '20%', 2: '50%', 1: '63.2%'}  # closest conversion for small ARI events
            for mag, unit in aep.items():
                # convert magnitude to float
                if unit.lower() == 'ey':
                    mag = float(mag)
                else:
                    mag = float(mag[:-1])
                # convert ari to aep
                if unit.lower() == 'ari':
                    if mag <= 5:
                        try:
                            aep_list.append(aep_conv[mag])
                            if mag == 1:
                                print('MESSAGE: ARI {0:.0f} year being converted to available AEP'.format(mag))
                                print('MESSAGE: using {0}'.format(aep_conv[mag]))
                            elif frequent_events:
                                print('MESSAGE: ARI {0:.0f} year being converted to available EY'.format(mag))
                                print('MESSAGE: using {0}'.format(aep_conv[mag]))
                            else:
                                print('WARNING: ARI {0} year does not correspond to available AEP'.format(mag))
                                print('MESSAGE: using closest available AEP: {0}.. or turn on "frequent events" ' \
                                      'to obtain exact storm magnitude'.format(aep_conv[mag]))
                        except:
                            self.error = True
                            self.message = 'Unable to convert ARI {0}year to AEP'.format(mag)
                    elif mag <= 100:
                        aep_list.append('{0:.0f}%'.format((1 / float(mag)) * 100))
                    else:
                        aep_list.append('{0}%'.format((1 / float(mag)) * 100))
                elif unit.lower() == 'ey':
                    if mag >= 1:
                        aep_list.append('{0:.0f}EY'.format(mag))
                    else:
                        aep_list.append('{0}EY'.format(mag))
                elif unit.lower() == 'aep':
                    if mag > 50:
                        aep_list.append('{0:.1f}%'.format(mag))
                    elif mag >= 1:
                        aep_list.append('{0:.0f}%'.format(mag))
                    else:
                        aep_list.append('{0}%'.format(mag))
                else:
                    self.error = True
                    self.message = 'Not a valid storm magnitude unit: {0}'.format(unit.upper())
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
            arf_file_open.write('\n\n**WARNING: Minimum ARF value has been set at 0.2')
            arf_file_open.flush()
            arf_file_open.close()
            neg_arf = float((arf_array < 0).sum())  # total number of negative entries
            if neg_arf > 0:
                print('WARNING: {0:.0f} ARF entries have a negative value. ' \
                      'Check "Rainfall_ARF_Factors.csv" output.'.format(neg_arf))
            # Save Figure
            fig_name = os.path.join(os.path.splitext(fpath)[0], 'data', '{0}_ARF_Factors.png'.format(site_name))
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
                print('WARNING: {0} negative rainfall depths have occured, caused by negative ARF values. ' \
                      'Negative depth values have been set to zero.'.format(neg_depths))
            fo_arf_depths.flush()
            fo_arf_depths.close

            # Save figure
            fig_name = os.path.join(os.path.splitext(fpath)[0], 'data', 'BOM_Rainfall_Depths_{0}.png'.format(site_name))
            ymax = 10 ** math.ceil(math.log10(numpy.nanmax(bom.depths)))
            ymin = 10 ** math.floor(math.log10(numpy.nanmin(bom.depths))) if numpy.nanmin(bom.depths) > 0. else 0.001
            make_figure(fig_name, bom.duration, bom.depths, 1, 10000, ymin, ymax, 'Duration (mins)', 'Depth (mm)',
                        'Design Rainfall Depths: {0}'.format(site_name), bom.aep_names, loglog=True)
        else:
            print('Catchment area less than 1 km2, ignoring ARF factors.')

        # write out climate change data
        if cc:
            if len(cc_years) < 1:
                print('No year(s) specified when considering climate change.')
                sys.exit('ERROR: no year(s) specified in Climate Change consideration')
            if len(cc_RCP) < 1:
                print('No RCP(s) specified when considering climate change.')
                sys.exit('ERROR: no RCP(s) specified in Climate Change consideration.')
            for year, k in cc_years_dict.items():
                # j is year index of year in self.CCF.Year so multiplier can be extracted
                if year not in self.CCF.Year:
                    print('Climate change year ({0}) not recognised, or not a valid year.'.format(year))
                    sys.exit('ERROR: Climate change year not valid.')
                for rcp in cc_RCP:
                    if rcp == 'RCP4.5':
                        cc_multip = (self.CCF.RCP4p5[k] / 100) + 1
                    elif rcp == 'RCP6':
                        cc_multip = (self.CCF.RCP6[k] / 100) + 1
                    elif rcp == 'RCP8.5':
                        cc_multip = (self.CCF.RCP8p5[k] / 100) + 1
                    else:
                        print('Climate change RCP ({0}) not recognised, or valid.'.format(rcp))
                        sys.exit('ERROR: Climate change RCP not valid')
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
                    fig_name = os.path.join(os.path.splitext(fpath)[0], 'data',
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
                        aep_list_formatted.append('{0:06.1f}e'.format(float(ari_conv[aep][:-1])))
                elif padding == 4 and decimal_places == 0:
                    if aep[-1] == '%':
                        aep_list_formatted.append('{0:04.0f}y'.format(float(ari_conv[aep][:-1])))
                    else:
                        aep_list_formatted.append('{0:04.0f}e'.format(float(ari_conv[aep][:-1])))
                elif padding == 3 and decimal_places == 1:
                    if aep[-1] == '%':
                        aep_list_formatted.append('{0:05.1f}y'.format(float(ari_conv[aep][:-1])))
                    else:
                        aep_list_formatted.append('{0:05.1f}e'.format(float(ari_conv[aep][:-1])))
                elif padding == 3 and decimal_places == 0:
                    if aep[-1] == '%':
                        aep_list_formatted.append('{0:03.0f}y'.format(float(ari_conv[aep][:-1])))
                    else:
                        aep_list_formatted.append('{0:03.0f}e'.format(float(ari_conv[aep][:-1])))
                elif padding == 2 and decimal_places == 1:
                    if aep[-1] == '%':
                        aep_list_formatted.append('{0:04.1f}y'.format(float(ari_conv[aep][:-1])))
                    else:
                        aep_list_formatted.append('{0:04.1f}e'.format(float(ari_conv[aep][:-1])))
                elif padding == 2 and decimal_places == 0:
                    if aep[-1] == '%':
                        aep_list_formatted.append('{0:02.0f}y'.format(float(ari_conv[aep][:-1])))
                    else:
                        aep_list_formatted.append('{0:02.0f}e'.format(float(ari_conv[aep][:-1])))
                elif padding == 1 and decimal_places == 1:
                    if aep[-1] == '%':
                        aep_list_formatted.append('{0:.1f}y'.format(float(ari_conv[aep][:-1])))
                    else:
                        aep_list_formatted.append('{0:.1f}e'.format(float(ari_conv[aep][:-1])))
                else:
                    if aep[-1] == '%':
                        aep_list_formatted.append('{0:.0f}y'.format(float(ari_conv[aep][:-1])))
                    else:
                        aep_list_formatted.append('{0:.0f}e'.format(float(ari_conv[aep][:-1])))

        for a, aep in enumerate(aep_list):
            # get AEP band as per Figure 2.5.12. Temporal Pattern Ranges
            if aep not in exported_aep:
                exported_aep.append(aep)
                if out_notation == 'ari':
                    if aep == '50%':
                        print('WARNING: 50% AEP does not correspond to 2y ARI. Rather it is equivalent to'
                              ' the 1.44y ARI. For 2y ARI please use 0.5EY.')
                    if aep == '20%':
                        print('WARNING: 20% AEP does not correspond to 5y ARI. Rather it is equivalent to'
                              ' the 4.48y ARI. For 5y ARI please use 0.2EY.')
            if aep[-2:] != 'EY' and aep[:4] != '1 in':
                if float(aep[:-1]) < 1:
                    print("WARNING: {0}% AEP event is considered 'Very Rare'. Temporal patterns for 'Very Rare' "
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
                print("WARNING: 1 in {0} yr event is considered 'Very Rare'. Temporal patterns for 'Very Rare' "
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
                print('WARNING: Unable to find BOM data for AEP: {0} - skipping'.format(aep))
                continue
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
                        print('WARNING: Unable to find BOM data for duration: {0:.0f}min - skipping'.format(duration))
                        continue
                    if process_dur:
                        if duration not in exported_dur:
                            exported_dur.append(duration)
                        depth = bom.depths[dur_ind, aep_ind]
                        ids, increments, dts = self.Temporal.get_dur_aep(duration, aep_band)
                        nid = len(ids)
                        ntimes = len(increments[0]) + 2  # add zero to start and end
                        rf_array = numpy.zeros([nid, ntimes])
                        times = [0]
                        if out_form == 'ts1':
                            dt = dts[0]
                        else:
                            dt = dts[0] / 60.  # output in hours
                        for i in range(ntimes - 1):
                            times.append(times[-1] + dt)
                        # sort data into nice array
                        for i in range(nid):
                            for j in range(len(increments[i])):
                                rf_array[i, j + 1] = increments[i][j] * depth / 100.
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
                                        for j in range(len(increments[i])):
                                            cc_rf_array[i, j + 1] = increments[i][j] * depth * cc_multip / 100
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
                            print('Unexpected error opening file {0}'.format(outfname))
                            sys.exit("ERROR: Opening file.")
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
                                line = line + ', {0}'.format(rf_array[j, i])
                            fo.write(line + '\n')
                        fo.flush()
                        fo.close()

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
                                                                       self.PreBurst.AEP_names, self.PreBurst.Duration,
                                                                       bom.depths)
        pb_com_aep, pb_com_dur, pb_dep_com, pb_com_dur_index = common_data(self.PreBurst.AEP_names,
                                                                           self.PreBurst.Duration, bom.aep_names,
                                                                           bom.duration, preBurst_depths)
        pb_com_aep, pb_com_dur, pb_rto_com, pb_com_dur_index = common_data(self.PreBurst.AEP_names,
                                                                           self.PreBurst.Duration, bom.aep_names,
                                                                           bom.duration, preBurst_ratios)

        # calculate the maximum preburst depths
        pb_rto_d_com = numpy.multiply(b_dep_com, pb_rto_com)  # convert preburst ratios to depths
        pb_dep_final = numpy.maximum(pb_dep_com, pb_rto_d_com)  # take the max of preburst ratios and depths

        # calculate burst intial loss (storm il minus preburst depth)
        if self.Losses.ils == 0 and self.Losses.cls == 0:
            print('WARNING: No rainfall losses found.')
        shape_com = pb_dep_final.shape  # array dimensions of preburst depths
        ils = numpy.zeros(shape_com) + float(self.Losses.ils)  # storm initial loss array
        ilb = numpy.add(ils, -pb_dep_final)  # burst initial loss (storm initial loss subtract preburst)

        # extend loss array to all durations using interpolation
        ilb_complete = extend_array(b_com_dur_index, b_com_aep, ilb, bom.duration)  # add all durations to array
        ilb_complete = interpolate_nan(ilb_complete, bom.duration, self.Losses.ils, lossMethod=lossMethod, mar=mar,
                                       staticLoss=staticLoss)

        # set up negative entry and perc neg entry calculations
        shape_ilb_complete = ilb_complete.shape  # array dimensions of preburst depths
        total_entries = float(shape_ilb_complete[0] * shape_ilb_complete[1])  # total number of entries
        neg_entries = 0

        # write burst initial losses to csv
        fname_losses = '{0}_Burst_Initial_Losses.csv'.format(site_name)
        fname_losses_out = os.path.join(fpath, 'data', fname_losses)
        try:
            flosses = open(fname_losses_out, 'w')
        except IOError:
            print('Unexpected error opening file {0}'.format(fname_losses_out))
            sys.exit('ERROR: Opening File.')
        flosses.write('This File has been generated using ARR_to_TUFLOW. The Burst losses have been calculated by '
                      'subtracting the maximum preburst (Depth or Ratios) from the storm initial loss.\n')
        flosses.write('Duration (mins),{0}\n'.format(",".join(map(str, b_com_aep))))

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
        fig_name = os.path.join(os.path.splitext(fpath)[0], 'data', '{0}_Burst_Initial_Losses.png'.format(site_name))
        ymax = math.ceil(float(self.Losses.ils) / 10.0) * 10
        xmax = 10 ** math.ceil(math.log10(max(b_com_dur)))
        ymin = math.floor(numpy.nanmin(ilb_complete) / 10.0) * 10
        make_figure(fig_name, bom.duration, ilb_complete, 1, xmax, ymin, ymax, 'Duration (mins)', 'Depth (mm)',
                    'Design Initial Losses: {0}'.format(site_name), b_com_aep, xlog=True)

        # complete neg entry calculation and write out warning
        perc_neg = (neg_entries / total_entries) * 100  # percentage of negative entries
        if neg_entries > 0:
            print('WARNING: {0} preburst rainfall depths exceeded storm initial loss ({1:.1f}% of entries)'.
                  format(neg_entries, perc_neg))

        # write common bc_dbase
        bc_fname = os.path.join(fpath, 'bc_dbase.csv')
        if catch_no == 0:
            try:
                bcdb = open(bc_fname, 'w')
            except IOError:
                print('Unexpected error opening file {0}'.format(bc_fname))
                sys.exit("ERROR: Opening file.")
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
            except IOError:
                print('Unexpected error opening file {0}'.format(bc_fname))
                sys.exit("ERROR: Opening file.")
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
                except IOError:
                    print('Unexpected error opening file {0}'.format(bc_fname_cc))
                    sys.exit("ERROR: Opening file.")
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
                except IOError:
                    print('Unexpected error opening file {0}'.format(bc_fname_cc))
                    sys.exit("ERROR: Opening file.")
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
        except IOError:
            print('Unexpected error opening file {0}'.format(tef_fname))
            sys.exit("ERROR: Opening file.")
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
