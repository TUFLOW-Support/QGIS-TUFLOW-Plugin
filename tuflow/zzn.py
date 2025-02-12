import os
import re
import struct
from datetime import datetime
import numpy as np
try:
    from pathlib import Path
except ImportError:
    from pathlib_ import Path_ as Path


pNNODES = 129
pDT = 256
pTIMESTEP_FIRST = 260
pTIMESTEP_LAST = 384
pOUT_INTERVAL = 388
pLABEL_LEN = 396
pDATE = 400
pFIRST_LABEL = 640


def byte2str(b):
    return re.sub(rf'[{chr(0)}-{chr(31)}]', '', b''.join(b).decode('utf-8', errors='ignore')).strip()


class ZZL:

    def __init__(self, zzl_path):
        self.labels = []
        self.nvars = 6
        with zzl_path.open('rb') as f:
            self._model_title = byte2str(struct.unpack('c'*128, f.read(128)))
            self.model_title = self._model_title.split('FILE=')[0].strip()
            self.dat = self._model_title.split('FILE=')[1].split('.dat')[0].strip() + '.dat'
            self.fm_version = self._model_title.split('VER=')[1].strip()
            self.nnodes = struct.unpack('I', f.read(4))[0]
            f.seek(pDT)
            self.dt = struct.unpack('f', f.read(4))[0]
            f.seek(pTIMESTEP_FIRST)
            self.timestep_first = struct.unpack('I', f.read(4))[0]
            f.seek(pTIMESTEP_LAST)
            self.timestep_last = struct.unpack('I', f.read(4))[0]
            f.seek(pOUT_INTERVAL)
            self.save_multiple = struct.unpack('I', f.read(4))[0]
            self.output_interval = self.save_multiple * self.dt
            f.seek(pLABEL_LEN)
            self.label_len = struct.unpack('I', f.read(4))[0]
            f.seek(pDATE)
            hr = struct.unpack('I', f.read(4))[0]
            min = struct.unpack('I', f.read(4))[0]
            day = struct.unpack('I', f.read(4))[0]
            mon = struct.unpack('I', f.read(4))[0]
            yr = struct.unpack('I', f.read(4))[0]
            self.reference_time = datetime(yr, mon, day, hr, min)
            f.seek(pFIRST_LABEL)
            for i in range(self.nnodes):
                if i != 0 and i % 10 == 0:
                    f.read(8)
                self.labels.append(byte2str(struct.unpack('c'*self.label_len, f.read(self.label_len))))


class ZZN:

    def __init__(self, file_path):
        self._zzn_path = Path(file_path)
        self._zzl_path = self._zzn_path.with_suffix('.zzl')
        if not self._zzl_path.exists() or not self._zzn_path.exists():
            raise FileNotFoundError
        self._zzl = ZZL(self._zzl_path)
        self._a = np.fromfile(str(self._zzn_path), dtype=np.float32, count=self.timestep_count()*self.node_count()*self.result_type_count())
        self._a = np.reshape(self._a, (self.timestep_count(), self.node_count()*self.result_type_count()))
        self._h = np.array(sum([['q', 'h', 'f', 'v', 's', 'm'] for _ in range(self.node_count())], []))

    def get_time_series_data(self, type_):
        return self._a[:,self._h == type_.lower()]

    def labels(self):
        return self._zzl.labels[:]

    def output_interval(self):
        return self._zzl.output_interval

    def node_count(self):
        return self._zzl.nnodes

    def floodmodeller_version(self):
        return self._zzl.fm_version

    def result_name(self):
        return self._zzl.model_title

    def first_timestep(self):
        return self._zzl.timestep_first

    def last_timestep(self):
        return self._zzl.timestep_last

    def timestep_count(self) -> int:
        model_duration = (self._zzl.timestep_last - self._zzl.timestep_first + 1) * self._zzl.dt  # in seconds
        return int(np.round(model_duration / self._zzl.output_interval)) + 1

    def timesteps(self):
        start_time = (self._zzl.timestep_first - 1) * self._zzl.dt / 3600
        end_time = self._zzl.timestep_last * self._zzl.dt / 3600
        a = np.arange(start_time, end_time, self._zzl.output_interval / 3600)
        if not np.isclose(a[-1], end_time, rtol=0., atol=0.001):
            a = np.append(a, np.reshape(end_time, (1,)), axis=0)
        return np.reshape(a, (a.size,1))

    def result_type_count(self):
        return self._zzl.nvars

    def reference_time(self):
        return self._zzl.reference_time
