import io
import re
import typing
import numpy as np

from .TUFLOW_results import ResData
from .compatibility_routines import Path
from .utils import CaseInsStrDict


class BC_Tables(ResData):

    def __init__(self):
        self.bndry_parser = None
        super().__init__()
        self.formatVersion = 2

    @property
    def displayname(self) -> str:
        if self.bndry_parser:
            return self.bndry_parser.name
        return ''

    @displayname.setter
    def displayname(self, value: str) -> None:
        pass

    def Load(self, fname: str) -> typing.Tuple[bool, str]:
        err, msg = False, ''
        fname = Path(fname)
        if not fname.exists():
            err, msg = True, 'File {0} does not exist'.format(fname.name)
            return err, msg
        if not re.findall(r'_[12]d_bc_tables_check\.csv$', fname.name):
            err, msg = True, 'File "{0}" is not a BC Tables Check file'.format(fname.name)
            return err, msg
        self.bndry_parser = BC_Tables_Parser(fname)
        self.Types = []
        for bndry in self.bndry_parser:
            if bndry.type not in self.Types:
                self.Types.append(bndry.type)
        return err, msg

    def getTSData(self, id, dom, res, geom) -> typing.Tuple[bool, list[float], str]:
        if self.bndry_parser.empty:
            return False, [0.], 'No data'
        if id in self.bndry_parser and self.bndry_parser[id].type == res:
            bndry = self.bndry_parser[id]
            self.times = bndry.values[:, 0]
            data = bndry.values[:, 1]
            return True, data, ''
        return False, [0.], 'No data'

    def timeSteps(self, zero_time=None):
        for bndry in self.bndry_parser:
            return bndry.values[:, 0]
        return []

    def lineResultTypesLP(self) -> typing.List[str]:
        return []

    def pointResultTypesTS(self) -> typing.List[str]:
        return []

    def lineResultTypesTS(self) -> typing.List[str]:
        return []

    def regionResultTypesTS(self) -> typing.List[str]:
        return []


class BC_Tables_1D(BC_Tables):

    @property
    def displayname(self) -> str:
        return '{0}_1d_bc'.format(self.bndry_parser.name)

    @displayname.setter
    def displayname(self, value: str) -> None:
        pass

    def pointResultTypesTS(self) -> typing.List[str]:
        types = []
        for bndry in self.bndry_parser:
            if bndry.type in types:
                continue
            types.append(bndry.type)
        return types

    def regionResultTypesTS(self) -> typing.List[str]:
        types = []
        for bndry in self.bndry_parser:
            if bndry.type in types:
                continue
            if bndry.type == 'Flow':
                types.append(bndry.type)
        return types


class BC_Tables_2D(BC_Tables):

    @property
    def displayname(self) -> str:
        return '{0}_2d_bc'.format(self.bndry_parser.name)

    @displayname.setter
    def displayname(self, value: str) -> None:
        pass

    def lineResultTypesTS(self) -> typing.List[str]:
        types = []
        for bndry in self.bndry_parser:
            if bndry.type in types:
                continue
            if bndry.type == 'Flow' and isinstance(bndry, Boundary_QT):
                types.append('Flow')
            elif isinstance(bndry, Boundary_SA) or isinstance(bndry, Boundary_RF):
                continue
            else:
                types.append(bndry.type)
        return types

    def regionResultTypesTS(self) -> typing.List[str]:
        types = []
        for bndry in self.bndry_parser:
            if bndry.type in types:
                continue
            if isinstance(bndry, Boundary_SA) or isinstance(bndry, Boundary_RF):
                types.append(bndry.type)
        return types


class Boundary:

    def __new__(cls, line: str):
        line = line.strip('\n\t "')
        if re.findall(r'^BC\d{6}:', line):
            line_ = re.sub(r'^BC\d{6}:\s*', '', line)
            if line_.startswith('QT'):
                cls = Boundary_QT
            elif line_.startswith('HT'):
                cls = Boundary_HT
            elif line_.startswith('HQ'):
                cls = Boundary_HQ
            elif line_.startswith('ST') and 'based on SA region' in line_:
                cls = Boundary_SA
            elif line_.startswith('RF') and 'based on SA region' in line_:
                cls = Boundary_RF

        self = super().__new__(cls)
        self._init(line)
        return self

    def _init(self, line: str) -> None:
        self.id = ''
        self.name = ''
        self.gis_file = ''
        self.bc_dbase = ''
        self.bc_file = ''
        self.type = ''
        self.col1_header = None
        self.col2_header = None
        self.header_line_count = 2
        self.values = np.array([])
        self.valid = False

    def __repr__(self):
        if self.valid:
            return '<{0} {1}>'.format(self.__class__.__name__, self.name)
        return '<{0} Invalid>'.format(self.__class__.__name__)


class Boundary_BC(Boundary):

    def _init(self, line: str) -> None:
        super()._init(line)
        self.id = re.findall(r'^BC\d{6}', line)[0]
        line_ = re.sub(r'^BC\d{6}:\s*', '', line)
        if re.findall(r'[A-Za-z]{2} BC in ', line_):
            line_ = re.sub(r'[A-Za-z]{2} BC in ', '', line_)
            if 'Tabular data' in line_:
                i = line_.index('Tabular data')
                self.gis_file = Path(line_[:i].strip(' .'))
                line_ = line_[i:]
        if 'Tabular data' in line_:
            line_ = line_.replace('Tabular Data from file ', '')
            if ' and name ' in line_:
                i = line_.index(' and name ')
                self.bc_file = Path(line_[:i].strip(' ."'))
                line_ = line_[i:]
        if 'and name ' in line_:
            line_ = line_.replace('and name ', '')
            if re.findall(r'( (?:and|in) database )', line_):
                text = re.findall(r'(?: (?:and|in) database )', line_)[0]
                i = line_.index(text)
                self.name = line_[:i].strip(' "')
                line_ = line_[i:]
        if re.findall(r'( (?:and|in) database )', line_):
            line_ = re.sub(r'( (?:and|in) database )', '', line_)
            self.bc_dbase = Path(line_.strip(' ."'))
        if self.name:
            self.valid = True

    def read(self, fo: io.TextIOWrapper) -> None:
        _, self.col1_header, self.col2_header = [x.strip('\n\t "') for x in fo.readline().split(',')]
        for _ in range(self.header_line_count - 1):
            next(fo)
        data = []
        for line in fo:
            if not line.strip():
                break
            data.append(line.strip().split(',')[1:])
        self.values = np.array(data, dtype=float)


class Boundary_QT(Boundary_BC):

    def _init(self, line: str) -> None:
        super()._init(line)
        self.type = 'Flow'


class Boundary_HT(Boundary_BC):

    def _init(self, line: str) -> None:
        super()._init(line)
        self.type = 'Level'


class Boundary_HQ(Boundary_BC):

    def _init(self, line: str) -> None:
        super()._init(line)
        self.header_line_count = 1
        self.type = 'HQ'


class Boundary_SA(Boundary_BC):

    def _init(self, line: str) -> None:
        super()._init(line)
        self.type = 'Flow'


class Boundary_RF(Boundary_BC):

    def _init(self, line: str) -> None:
        super()._init(line)
        self.type = 'Rainfall Depth'

    def read(self, fo: io.TextIOWrapper) -> None:
        super().read(fo)
        a1 = sum([[x, x] for x in self.values[:, 0]], [])
        a1 = a1[1:-1]
        a2 = sum([[x, x] for x in self.values[:, 1]], [])
        a2 = a2[2:]
        self.values = np.array([a1, a2]).T


class BC_Tables_Parser:

    def __init__(self, file: typing.Union[str, Path]):
        self.file = Path(file)
        self.name = re.sub(r'(_[12]d_bc_tables_check)', '', self.file.stem)
        self.boundaries = CaseInsStrDict()
        with self.file.open() as f:
            for line in f:
                bndry = Boundary(line)
                if bndry.valid:
                    try:
                        bndry.read(f)
                        self.boundaries[bndry.name] = bndry
                    except:
                        pass

    @property
    def empty(self) -> bool:
        return len(self.boundaries) == 0

    def __repr__(self):
        return f'<{self.__class__.__name__} {self.name}>'

    def __contains__(self, item):
        return item in self.boundaries

    def __getitem__(self, item):
        return self.boundaries[item]

    def __next__(self):
        for bndry in self.boundaries.values():
            yield bndry

    def __iter__(self):
        return next(self)


if __name__ == '__main__':
    file = r"C:\Users\esymons\Downloads\TGD-477\example_models\check\EG00\EG00_001_2d_bc_tables_check.csv"
    bc_tables = BC_Tables_Parser(file)
    print('here')
