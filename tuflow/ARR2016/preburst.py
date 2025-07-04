import typing
import logging

import numpy
import pandas as pd

from tuflow.ARR2016.meta import ArrMeta
from tuflow.ARR2016.parser import DataBlock
from tuflow.ARR2016.arr_settings import ArrSettings
from tuflow.ARR2016.BOM_WebRes import Bom


PREBURST_NAME = {
    'median': '[PREBURST]',
    '10': '[PREBURST10]',
    '25': '[PREBURST25]',
    '50': '[PREBURST]',
    '75': '[PREBURST75]',
    '90': '[PREBURST90]'
}

LIMB_NAME = {
    'enveloped': '[LIMBifdenv]',
    'high res': '[LIMBifdhr]',
    'bom res': '[LIMBifdbom]'
}

# note 12EY does not equal 99.9% AEP, but this needs a value and needs to have the highest value so 99.9 used as dummy value
CONV2AEP = {'12EY': '99.9', '6EY': '99.75', '4EY': '98.17', '3EY': '95.02', '2EY': '86.47', '1EY': '63.23',
            '0.5EY': '39.35', '0.2EY': '18.13', '1 in 200': '0.5', '1 in 500': '0.2', '1 in 1000': '0.1',
            '1 in 2000': '0.05', '63.2%': '63.23', '50%': '50.0', '20%': '20.0', '10%': '10.0', '5%': '5.0',
            '2%': '2.0', '1%': '1.0'}
AEP2NAME = {'99.9': '12EY', '99.75': '6EY', '98.17': '4EY', '95.02': '3EY', '86.47': '2EY',
            '39.35': '0.5EY', '18.13': '0.2EY', '0.5': '1 in 200', '0.2': '1 in 500', '0.1': '1 in 1000',
            '0.05': '1 in 2000', '63.23': '63.2%', '50.0': '50%', '20.0': '20%', '10.0': '10%', '5.0': '5%',
            '2.0': '2%', '1.0': '1%'}


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
        self.ratios = pd.DataFrame()
        self.percentile = 'median'
        self.pbtrans = False
        self.il_storm = -1
        self.nsw_losses = pd.DataFrame()
        self.settings = ArrSettings.get_instance()
        self.bom = pd.DataFrame()
        self.limb = pd.DataFrame()

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
        self.load_depths(fi)
        self.Duration = self.depths.index.astype(int).tolist()
        self.AEP = self.depths.columns.astype(float).tolist()
        self.AEP_names = ['{0:.0f}%'.format(x) for x in self.AEP]

    def load_depths(self, fi: typing.TextIO):
        try:
            keytext = PREBURST_NAME.get(self.percentile, '[PREBURST]')
            self.data = DataBlock(fi, keytext, True)
            if self.data:
                self.data.df.index = [int(str(x).split('(')[0]) for x in self.data.df.index]
                self.data.df.columns = [f'{float(x):.1f}' for x in self.data.df.columns]
                self.depths = self.data.df
                self.meta.time_accessed = self.data.time_accessed
                self.meta.version = self.data.version

            burst_data = DataBlock(fi, 'BURSTIL', True)  # nsw probability neutral losses
            limb_data = DataBlock(fi, LIMB_NAME.get(self.settings.limb_option, 'enveloped'), True)  # limb data
            if self.settings.use_nsw_prob_neutral_losses and burst_data:
                self.pbtrans = True
                self.data = DataBlock(fi, '[PREBURST_TRANS]', True)
                if not self.load_storm_initial_loss(fi):
                    raise Exception('Could not load storm initial loss as part of preburst data extraction - '
                                    'please email log file, catchment file, and ARR_Web_data.txt to support@tuflow.com')
                if not self.load_nsw_prob_neutral_losses(fi):
                    raise Exception('Could not load NSW probability neutral losses as part of preburst data extraction - '
                                    'please email log file, catchment file, and ARR_Web_data.txt to support@tuflow.com')
                self.data.df.index = [int(x.split('(')[0]) for x in self.data.df.index]
                self.depths = self.il_storm - self.data.df
                rf_depths = self.get_rainfall_depths(fi)
                rf_ = rf_depths.reindex_like(self.data.df)
                self.ratios = self.depths / rf_
            elif self.settings.limb_option and limb_data and self.settings.limb_recalc_pb_ratios:
                self.ratios = self.data.df.copy()
                for col in self.ratios.columns:
                    self.ratios[col] = self.ratios[col].str.extract(r'(\d+\.\d+\s+)(\(\d+(?:\.\d*)?\))').iloc[:,
                                       1].str.replace(r'\(|\)', '', regex=True).astype(float)
                rf_depths = self.get_rainfall_depths(fi)
                rf_ = rf_depths.reindex_like(self.data.df)
                self.depths = rf_ * self.ratios
            else:
                self.ratios = self.data.df.copy()
                for col in self.depths.columns:
                    self.depths[col] = self.depths[col].str.replace(r'\(\d+(?:\.\d*)?\)', '', regex=True).astype(float)
                for col in self.ratios.columns:
                    self.ratios[col] = self.ratios[col].str.extract(r'(\d+\.\d+\s+)(\(\d+(?:\.\d*)?\))').iloc[:,
                                       1].str.replace(r'\(|\)', '', regex=True).astype(float)
        except Exception as e:
            raise Exception('Error loading preburst rainfall data: {0}'.format(e)) from e

    def get_depths(self, losses):
        return self.depths.to_numpy()

    def get_ratios(self, losses):
        return self.ratios.to_numpy()

    def load_storm_initial_loss(self, fi: typing.TextIO) -> bool:
        data = DataBlock(fi, 'LOSSES', True)
        if data.empty():
            return False
        self.il_storm = data.df.loc['Storm Initial Losses (mm)'].values[0]
        return True

    def load_nsw_prob_neutral_losses(self, fi: typing.TextIO) -> bool:
        data = DataBlock(fi, 'BURSTIL', True)
        if data.empty():
            return False
        data.df.index = [int(str(x).split('(')[0]) for x in data.df.index]
        self.nsw_losses = data.df
        return True

    def get_rainfall_depths(self, fi: typing.TextIO) -> pd.DataFrame:
        bom = Bom()
        bom.load(self.settings.bom_data_file, self.settings.frequent_events, self.settings.rare_events)
        self.bom = pd.DataFrame(bom.depths, columns=bom.aep_names, index=bom.duration)
        self.bom.columns = [CONV2AEP.get(x, x) for x in self.bom.columns]

        keytext = LIMB_NAME.get(self.settings.limb_option)
        if not keytext:
            return self.bom

        limb_data = DataBlock(fi, keytext, True)
        if not limb_data:
            return self.bom

        limb_data.df.index = [int(str(x).split('(')[0]) for x in limb_data.df.index]
        self.limb = limb_data.df

        # update bom rainfdall depths with limb data where available
        df = self.bom.copy()
        df1 = self.limb.reindex_like(df).combine_first(self.limb)
        df.update(df1)
        return df

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