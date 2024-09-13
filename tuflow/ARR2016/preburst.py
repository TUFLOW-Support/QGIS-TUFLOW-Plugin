import typing
import logging

import numpy

from ARR2016.meta import ArrMeta
from ARR2016.parser import DataBlock


PREBURST_NAME = {
    'median': 'PREBURST',
    '10': 'PREBURST10',
    '25': 'PREBURST25',
    '50': 'PREBURST',
    '75': 'PREBURST75',
    '90': 'PREBURST90'
}


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
        self.meta = ArrMeta()
        self.data = {}
        self.depths = None
        self.percentile = 'median'

    def load(self, fi: typing.TextIO, percentile: typing.Union[str, int]) -> None:
        """Load the ARR Preburst Rainfall from a file.

        Parameters
        ----------
        fi : typing.TextIO
            File object to read
        percentile : typing.Union[str, int]
            The percentile to load. Can be 'median', 10, 25, 50, 75, 90
        """
        self.percentile = str(percentile).strip('%')
        keytext = PREBURST_NAME.get(percentile, 'PREBURST')
        self.data = DataBlock(fi, keytext, True)
        self.meta.time_accessed = self.data.time_accessed
        self.meta.version = self.data.version
        self.depths = self.data.df

        # remove hours from the index and just use minutes
        self.depths.index = [int(x.split('(')[0]) for x in self.depths.index]

        # remove ratios from depths columns and just keep the depths
        for col in self.depths.columns:
            self.depths[col] = self.depths[col].str.replace(r'\(\d+(?:\.\d*)?\)', '', regex=True).astype(float)

        self.load_(fi)  # hopefully remove this in the future

    def load_(self, fi):

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