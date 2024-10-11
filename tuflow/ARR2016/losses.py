import typing
import logging
import numpy

from tuflow.ARR2016.meta import ArrMeta
from tuflow.ARR2016.parser import DataBlock


class ArrLosses:
    """Class for loading and storing ARR losses"""

    def __init__(self):
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
        self.data = {}
        self.meta = ArrMeta()
        self.id = None
        self.init_loss = 0
        self.cont_loss = 0

        # NSW probability neutral losses
        self.existsPNLosses = False
        self.AEP = []
        self.AEP_names = []
        self.Duration = []
        self.ilpn = None

    def load(self, fi: typing.TextIO) -> None:
        """Load the losses from the file.

        Parameters
        ----------
        fi : typing.TextIO
            File object to read
        """
        self.data = DataBlock(fi, 'LOSSES', False)
        self.meta.time_accessed = self.data.time_accessed
        self.meta.version = self.data.version
        self.id = int(self.data.get('ID'))
        self.init_loss = float(self.data.get('Storm Initial Losses (mm)'))
        self.cont_loss = float(self.data.get('Storm Continuing Losses (mm/h)'))
        self._load_probability_neutral_losses(fi)
        self.load_(fi)

    def _load_probability_neutral_losses(self, fi: typing.TextIO) -> None:
        self.neutral_losses_data = DataBlock(fi, 'BURSTIL', True)
        self.neutral_losses = self.neutral_losses_data.df
        self.has_neutral_losses = not self.neutral_losses.empty
        if self.has_neutral_losses:
            self.neutral_losses.index = [x.split('(')[0] for x in self.neutral_losses.index]

    def load_(self, fi):
        for line in fi:
            if line.find('[LOSSES]') >= 0:
                finished = False
                for block_line in fi:
                    data = block_line.split(',')
                    finished = (data[0] == '\n' or block_line.find('[LOSSES_META]') >= 0)
                    if finished:
                        break
                    if data[0].lower() == 'storm initial losses (mm)':
                        self.ils_datahub = data[1].strip()
                        try:
                            self.ils = float(self.ils_datahub)
                            if numpy.isnan(self.ils):
                                raise ValueError
                        except ValueError:
                            msg = 'ERROR: Processing "Initial Storm Loss". Value found: {0}. Assuming value of zero instead'.format(
                                self.ils_datahub)
                            self.logger.info(msg)
                            self.ils = 0.
                    if data[0].lower() == 'storm continuing losses (mm/h)':
                        self.cls_datahub = data[1].strip()
                        try:
                            self.cls = float(self.cls_datahub)
                            if numpy.isnan(self.cls):
                                raise ValueError
                        except ValueError:
                            msg = 'ERROR: Processing "Continuing Storm Loss". Value found: {0}. Assuming value of zero instead.'.format(
                                data[1].strip())
                            self.logger.info(msg)
                            self.cls = 0.
                if finished:
                    break
        if self.ils is None or self.cls is None:
            self.error = True
            self.message = 'Error processing Storm Losses. This may be because you have selected an urban area.'
            self.ils = 0
            self.cls = 0
        fi.seek(0)  # rewind file

        self.loadProbabilityNeutralLosses(fi)
        if self.existsPNLosses:
            self.logger.info("Catchment is in NSW, multiplying Datahub continuing loss by 0.4")
            self.cls *= 0.4
            self.cls = float('{0:.2f}'.format(self.cls))

        self.loaded = True
        # print('Finished reading file.')
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
                                self.logger.warning(
                                    "ERROR: Reading Probability Neutral Initial Losses AEP... skipping\n{0}".format(e))
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
                            self.logger.warning(
                                "ERROR: Reading Probability Neutral Initial Losses... skipping\n{0}".format(e))
                            return
                if finished:
                    self.ilpn = numpy.array(losses_all)
                    self.existsPNLosses = True
                    self.logger.info("Finished reading Probability Neutral Initial Losses.")
                    break

        fi.seek(0)

    def applyUserInitialLoss(self, loss):
        """apply user specified (storm) initial loss to calculations instead of datahub loss"""

        # self.ils = loss
        self.ils_user = loss
        # print("Using user specified intial loss: {0}".format(loss))
        self.logger.info("Using user specified initial loss: {0}".format(loss))

    def applyUserContinuingLoss(self, loss):
        """apply user specified continuing loss to calculations instead of datahub loss"""

        self.cls = loss
        self.cls_user = loss
        # print("Using user specified continuing loss: {0}".format(loss))
        self.logger.info("Using user specified continuing loss: {0}".format(loss))
