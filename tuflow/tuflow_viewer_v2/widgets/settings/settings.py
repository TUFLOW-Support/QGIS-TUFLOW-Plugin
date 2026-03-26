import json

from qgis.PyQt.QtCore import QSettings


class CustomDict(dict):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.callback = None

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        if self.callback:
            self.callback()


class TuflowViewerSettings:

    KEY = 'TUFLOW/ViewerSettings'

    def __init__(self):
        self._block_save = True
        self.enabled_fmts = CustomDict([
            ('XMDF', True),
            ('SMS DAT', True),
            ('NetCDF Mesh', True),
            ('NetCDF Grid', True),
            ('TUFLOW CATCH Json', True),
            ('TPC', True),
            ('GPKG Time Series', True),
            ('TUFLOW Cross Sections', True),
            ('BC Tables Check', True),
            ('Hydraulic Tables Check', True),
            ('Flood Modeller', True),
            ('Flood Modeller DAT', True),
            ('FV BC Tide', True),
        ])
        self.enabled_fmts.callback = self.save
        self.theme_name = 'Light'
        self.copy_results_on_load = False

        self._block_save = False
        self.load()

    def __setattr__(self, key, value):
        super().__setattr__(key, value)
        if not self._block_save and not key.startswith('_'):
            self.save()

    def clear(self):
        QSettings().remove(self.KEY)

    def save(self):
        QSettings().setValue(self.KEY, self.serialize())

    def load(self):
        s = QSettings().value(self.KEY, '', type=str)
        if s:
            self._block_save = True
            self.deserialize(s)
            self._block_save = False

    def serialize(self) -> str:
        d = {}
        for attr in dir(self):
            if not attr.startswith('_') and not callable(getattr(self, attr)):
                d[attr] = getattr(self, attr)
        return json.dumps(d)

    def deserialize(self, string: str):
        d = json.loads(string)
        for k, v in d.items():
            if isinstance(v, dict) and hasattr(self, k) and isinstance(getattr(self, k), dict):
                getattr(self, k).update(v)
            else:
                setattr(self, k, v)
