import re
import struct
import numpy as np


def unpack_fixed_field(input_string, col_widths):
    """
    Unpacks input string based on fixed field lengths described in col_widths.
    The function will return a list of the split columns.

    The function will handle most situations where the input string length
    is shorter than the input fixed fields.

    :param input_string: str
    :param col_widths: tuple[int] - list of column widths
    :return:  list[str]
    """

    sum_ = 0
    new_widths = []
    for len_ in col_widths:
        if len(input_string) <= sum_ + len_:
            if len(input_string) - sum_ < 1:
                break
            else:
                new_widths.append(len(input_string) - sum_)
                break
        else:
            new_widths.append(len_)
            sum_ += len_

    fmtstring = ' '.join('{0}{1}'.format(abs(len_), 'x' if len_ < 0 else 's') for len_ in new_widths)
    return [x.decode('utf-8') for x in struct.unpack_from(fmtstring, input_string.encode())]


class FmUnit:

    def __init__(self, name_):
        self.name = name_
        self.xs = None
        self.arches = None
        self.cc = 1.
        self.skew = 0.
        self.orifice_flag = False
        self.lower_transition_depth = 0.
        self.upper_transition_depth = 0.
        self.discharge_coefficient = 1.


class FmDat:

    def __init__(self, unit_types, sub_types):
        self.unit_types = unit_types[:]
        self.sub_types = sub_types[:]
        self.count = 0
        self.fm_unit_names = []
        self.fm_units = []

        self._start = False

    def read_dat(self, dat_io):
        for line in dat_io:
            if re.findall(r'^(END GENERAL)', line):
                self._start = True
            elif re.findall(r'^(GISINFO|INITIAL CONDITIONS)', line):
                self._start = False
                return self._start

            if self._start:
                for unit_type in self.unit_types:
                    pattern = r'^({0})'.format(unit_type)
                    if re.findall(pattern, line):
                        subline = dat_io.readline()
                        for sub_type in self.sub_types:
                            pattern = r'^({0})'.format(sub_type)
                            if re.findall(pattern, subline):
                                return self._start

        return self._start

    def find_all(self, datfile):
        with open(datfile, 'r') as f:
            while self.read_dat(f):
                self.count += 1
                self.fm_unit_names.append(unpack_fixed_field(f.readline(), [12])[0].strip())

        return self.fm_unit_names

    def get_data(self, datfile, unit_name):
        with open(datfile, 'r') as f:
            while self.read_dat(f):
                if unpack_fixed_field(f.readline(), [12])[0].strip().lower() == unit_name.lower():
                    fm_unit = FmUnit(unit_name)
                    next(f)
                    attr = unpack_fixed_field(f.readline(), [10] * 9)
                    try:
                        fm_unit.cc = float(attr[0])
                    except (ValueError, IndexError):
                        pass
                    try:
                        fm_unit.skew = float(attr[1])
                    except (ValueError, IndexError):
                        pass
                    try:
                        fm_unit.orifice_flag = bool(attr[5])
                    except (ValueError, IndexError):
                        pass
                    try:
                        fm_unit.lower_transition_depth = float(attr[6])
                    except (ValueError, IndexError):
                        pass
                    try:
                        fm_unit.upper_transition_depth = float(attr[7])
                    except (ValueError, IndexError):
                        pass
                    try:
                        fm_unit.discharge_coefficient = float(attr[8])
                    except (ValueError, IndexError):
                        pass
                    try:
                        nval = int(unpack_fixed_field(f.readline(), [10])[0])
                    except ValueError:
                        nval = 0
                    xy = []
                    for _ in range(nval):
                        attr = unpack_fixed_field(f.readline(), [10] * 3)
                        try:
                            xy.append((float(attr[0]), float(attr[1])))
                        except (ValueError, IndexError):
                            pass
                    fm_unit.xs = np.array(xy)
                    try:
                        nval = int(unpack_fixed_field(f.readline(), [10])[0])
                    except ValueError:
                        nval = 0
                    arches = []
                    for _ in range(nval):
                        attr = unpack_fixed_field(f.readline(), [10] * 4)
                        try:
                            arches.append((float(attr[0]), float(attr[1]), float(attr[2]), float(attr[3])))
                        except (ValueError, IndexError):
                            pass
                    fm_unit.arches = np.array(arches)

                    self.fm_units.append(fm_unit)

        return self.fm_units


def fm_dat_parser(datfile, unit_types, sub_types, unit_name):
    """
    Read Flood Modeller dat file.

    If unit_name is None, will return all unit names of unit_type - sub_type.
    If unit_name is not None, will return complete parsed unit properties of that given unit.
    """

    dat = FmDat(unit_types, sub_types)
    if unit_name is None:
        return dat.find_all(datfile)
    else:
        return dat.get_data(datfile, unit_name)