import io
import json
import logging
import re
import typing
from pathlib import Path

import numpy as np
import pandas as pd

from ARR2016.meta import ArrMeta
from ARR2016.parser import DataBlock


RATE_OF_CHANGE = json.load(open(Path(__file__).parent / 'data' / 'cc_rate_of_change.json'))
POST_INDUSTRIAL_ADJ = 0.3


class ArrCCF:
    """Class for storing ARR Climate Change Factors."""

    def __init__(self):
        self.loaded = False
        self.error = False
        self.message = None
        self.Year = []
        self.RCP4p5 = []
        self.RCP6 = []
        self.RCP8p5 = []
        self.meta = ArrMeta()
        self.logger = logging.getLogger('ARR2019')
        self.data = {}
        self.ssp1 = None
        self.ssp2 = None
        self.ssp3 = None
        self.ssp5 = None
        self.il = None
        self.cl = None
        self.temp = None
        self.scenarios = []

    def load(self, fi: typing.TextIO) -> None:
        """Load the ARR Climate Change Factors from a file.

        Parameters
        ----------
        fi : typing.TextIO
            File object to read
        """
        self.data = DataBlock(fi, 'CCF', False)
        self.meta.time_accessed = self.data.time_accessed
        self.meta.version = self.data.version_int
        if self.meta.version > 2024000:
            self._load_ssp()
        else:
            self._load_rcp(fi)

    def scenario_count(self) -> int:
        return len(self.scenarios)

    def get_scenario(self, name: str) -> 'CCScenario':
        for scen in self.scenarios:
            if scen.name == name:
                return scen

    def add_scenario(self, name: str, param: dict) -> None:
        scen = CCScenario(self, name, param['horizon'], param['ssp'], param['base'], param['temp'])
        self.scenarios.append(scen)

    def calc_rainfall_depths(self, name: str, depths: pd.DataFrame) -> None:
        scen = self.get_scenario(name)
        scen.calc_rainfall_adj_factors(depths)

    def calc_rainfall_losses(self, name: str, init_loss: float, cont_loss: float, il_a: np.ndarray, tp_region: str) -> None:
        scen = self.get_scenario(name)
        scen.calc_loss_adj_factors(init_loss, cont_loss, il_a, tp_region)
        self.logger.info(f'Losses calculated for scenario {name}- Initial Loss {scen.init_loss:.2f}, Continuing Loss {scen.cont_loss:.2f}')

    def write_rainfall_to_file(self, name: str, out_dir: Path) -> None:
        scen = self.get_scenario(name)

        # factors
        fpath = out_dir / f'{name}_rainfall_factors.csv'
        try:
            with fpath.open('w') as f:
                f.write(f'This file has been generated using ARR_to_TUFLOW. The rainfall factors have been calculated for '
                        f'the scenario "{name}" which uses the following parameters- {scen.param_to_string()}.\n')
                scen.rf_f.to_csv(f, lineterminator='\r')
        except PermissionError:
            self.logger.error(f'File is locked for editing, skipping writing: {fpath}')

        # depths
        fpath = out_dir / f'{name}_rainfall_depths.csv'
        try:
            with fpath.open('w') as f:
                f.write('This file has been generated using ARR_to_TUFLOW. The rainfall depths have been calculated for '
                        f'the scenario "{name}" which uses the following parameters- {scen.param_to_string()}.\n')
                scen.rf.to_csv(f, lineterminator='\r')
        except PermissionError:
            self.logger.error(f'File is locked for editing, skipping writing: {fpath}')

    def write_losses_to_file(self, name: str, out_dir: Path) -> None:
        scen = self.get_scenario(name)
        fpath = out_dir / f'{name}_losses.csv'

        try:
            with fpath.open('w') as f:
                f.write('This file has been generated using ARR_to_TUFLOW. The losses have been calculated for '
                        f'the scenario "{name}" which uses the following parameters- {scen.param_to_string()}.\n')
                scen.init_losses_a.to_csv(f, lineterminator='\r')
        except PermissionError:
            self.logger.error(f'File is locked for editing, skipping writing: {fpath}')

    def _load_ssp(self):
        self.ssp1 = self.data.get('SSP1-2.6')
        self.ssp2 = self.data.get('SSP2-4.5')
        self.ssp3 = self.data.get('SSP3-7.0')
        self.ssp5 = self.data.get('SSP8-8.5')
        self.il = self.data.get('Climate_Change_INITIAL_LOSS')
        self.cl = self.data.get('Climate_Change_CONTINUING_LOSS')
        self.temp = self.data.get('TEMPERATURE_CHANGES')

    def _load_rcp(self, fi):
        # method is a little ugly, but should be deprecated as ARR doesn't use RCP method anymore
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
        self.logger.info('Finished reading file.')


class CCScenario:

    def __init__(self, ccf: ArrCCF, name: str, horizon: str, ssp: str, baseline: float, temp_change: float) -> None:
        self.ccf = ccf
        self.name = name

        if horizon == 'Near-term':
            self.horizon = 2030
        elif horizon == 'Medium-term':
            self.horizon = 2050
        elif horizon == 'Long-term':
            self.horizon = 2090
        else:
            self.horizon = horizon
        self.ssp = ssp
        self.baseline = baseline
        self.temp_change = temp_change  # user input
        self.dtemp = self._get_delta_temp()
        self.rf = pd.DataFrame()  # should already have ARF applied
        self.rf_f = pd.DataFrame()
        self.init_loss = -1
        self.cont_loss = -1
        self.init_loss_f = 1
        self.cont_loss_f = 1
        self.init_losses_a = pd.DataFrame()  # array

    def param_to_string(self) -> str:
        return (f'Horizon {self.horizon}; SSP {self.ssp}; Baseline change {self.baseline}; '
                f'User temperature change {self.temp_change}; Final temperature change {self.dtemp}')

    def calc_rainfall_adj_factors(self, depths: pd.DataFrame) -> None:
        self.rf_f = depths.copy()
        roc = self.rf_f.index.map(lambda x: self._get_rate_of_change('rainfall', x)).to_frame(index=False)
        roc.set_index(self.rf_f.index, inplace=True)
        for col in depths.columns:
            self.rf_f[col] = (1 + roc / 100) ** self.dtemp
        self.rf = depths * self.rf_f

    def calc_loss_adj_factors(self, init_loss: float, cont_loss: float, il_a: np.ndarray, tp_region: str) -> None:
        self.init_loss_f = (1 + self._get_rate_of_change('initial_loss', tp_region) / 100) ** self.dtemp
        self.cont_loss_f = (1 + self._get_rate_of_change('continuing_loss', tp_region) / 100) ** self.dtemp
        self.init_loss = init_loss * self.init_loss_f
        self.cont_loss = cont_loss * self.cont_loss_f
        self.init_losses_a = pd.DataFrame(il_a * self.init_loss_f, index=self.rf.index, columns=self.rf.columns)

    def _get_delta_temp(self) -> float:
        if self.temp_change == -1:
            dtemp = self.ccf.temp.loc[self.horizon, self.ssp]
        else:
            dtemp = max(float(self.temp_change) - POST_INDUSTRIAL_ADJ, 0)
        return max(dtemp - float(self.baseline), 0)

    def _get_rate_of_change(self, typ, dur) -> float:
        if isinstance(dur, int):
            if dur < 60:
                dur = '1'
            elif dur > 24 * 60:
                dur = '24'
            else:
                dur = str(dur / 60)
                if '.0' in dur:
                    dur = dur.split('.')[0]
        return RATE_OF_CHANGE[typ][dur]
