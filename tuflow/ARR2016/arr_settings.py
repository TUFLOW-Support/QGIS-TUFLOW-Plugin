import json
import threading
from collections import OrderedDict
from pathlib import Path

import pandas as pd

lock = threading.Lock()


class Singleton(type):

    _instance = None

    def __call__(cls, *args, **kwargs):
        with lock:
            if cls._instance is None:
                cls._instance = super(Singleton, cls).__call__(*args, **kwargs)
            return cls._instance


class ArrSettings(metaclass=Singleton):

    def __init__(self):
        self.preburst_percentile = 'median'
        self.persistent_data = ArrPersistent()

    @staticmethod
    def get_instance():
        return ArrSettings()


class ArrPersistent:

    def __init__(self):
        self.losses = {}  # AEP: pd.DataFrame(Dur x CC)
        self.test = ''

    def clear(self, folder: str):
        f = Path(folder) / 'persistent_data.json'
        if f.exists():
            f.unlink()

    def load(self, folder: str):
        f = Path(folder) / 'persistent_data.json'
        if f.exists():
            with f.open() as fo:
                losses = json.loads(fo.read(), object_pairs_hook=OrderedDict)
                return losses
        return OrderedDict()

    def save(self, folder: str):
        f = Path(folder) / 'persistent_data.json'
        with f.open('w') as fo:
            json.dump(self.losses, fo, indent=4)

    def add_initial_loss(self, folder: str, aep: str, dur: str, cc: str, site_name: str, loss: float):
        self.losses = self.load(folder)
        if aep not in self.losses:
            self.losses[aep] = OrderedDict()
        if dur not in self.losses[aep]:
            self.losses[aep][dur] = OrderedDict()
        if cc not in self.losses[aep][dur]:
            self.losses[aep][dur][cc] = OrderedDict()
        self.losses[aep][dur][cc][site_name] = loss
        self.save(folder)
