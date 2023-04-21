import struct
from os.path import basename, dirname, splitext, join, exists, isdir
import numpy as np


class TMO:
    """
    Class for handling .tmo outputs from TUFLOW.

    Only header information is read in when the class is initialised.
    Values can be obtained using "data_at_time" method.
    """

    def __init__(self, file_path):
        self.wd = None
        self.header = TMO_Header(file_path)
        if not self.header.is_wd:
            self.wd_file = join(dirname(file_path), '{0}_wd.tmo'.format('_'.join(self.header.name.split('_')[:-1])))
            if exists(self.wd_file):
                self.wd = TMO(self.wd_file)

    def __str__(self):
        return self.header.name

    def translate_time(self, time):
        """
        Method to return actual time in dataset given an input time.

        Checks for 'min' and 'max' time and converts to float value (-99999. and 99999.).

        Check time exists in dataset and consider rounding errors
           e.g. input 0.083 returns the time 0.08333333

        Returns time from dataset if found.
        """
        if isinstance(time, str):
            if time.lower() == 'max':
                time = 99999.0
            elif time.lower() == 'min':
                time = -99999.0
            else:
                try:
                    time = float(time)
                except ValueError:
                    time = None
        elif isinstance(time, int):
            time = float(time)
        elif isinstance(time, float):
            pass
        else:
            return None

        times = np.array(self.header.times)
        time = times[np.isclose(times, time, atol=0.001)]
        if time.tolist():
            return time[0]

        return None

    def point_count(self):
        return sum([x.row_count * x.col_count for x in self.header.domains])

    def get_pos(self, time_index, domain_index):
        """Get the offset in file for the start of the time and domain values."""
        pos = 0
        domain_size = 64
        for i, domain in enumerate(self.header.domains):
            pos = self.header.header_length + domain_size + self.header.data_block_size * time_index
            domain_size += domain.data_block_size_buffer
            if domain_index == i:
                break

        return pos

    def data_at_time(self, time, call_back_log = None, call_back_progress = None):
        """
        Returns values at a given time for all domains.
        The values returned is a list of tuples of real world co-ordinates (x, y, value).
        """
        time = self.translate_time(time)
        if time is None or time not in self.header.times:
            raise Exception('Invalid input time: {0}\nAvailable times: {1}'.format(time, self.header.times))

        time_index = self.header.times.index(time)

        xrw = lambda x, y, ox, ang: ox + x * np.cos(ang) - y * np.sin(ang)
        yrw = lambda x, y, oy, ang: oy + x * np.sin(ang) + y * np.cos(ang)
        for i, domain in enumerate(self.header.domains):
            if call_back_log is not None:
                call_back_log('Reading file data for domain: {0}\n{1}\n'.format(i, domain))
            a = self.row_col_data_at_time(time_index, i)
            if self.wd is not None:
                wd = self.wd.row_col_data_at_time(time_index, i)
                if wd is not None:
                    mask = wd < 1
                    a = np.ma.masked_where(mask, a, True)
            for n in range(domain.row_count):
                for m in range(domain.col_count):
                    if self.wd is not None and wd is not None and mask[n,m]:
                        if call_back_progress is not None:
                            call_back_progress()
                        continue
                    if self.header.version >= 3:
                        x = xrw(m * domain.dx, n * domain.dy, domain.origin_x, domain.geo_angle)
                        y = yrw(m * domain.dx, n * domain.dy, domain.origin_y, domain.geo_angle)
                    else:
                        x = xrw(m * domain.dx + domain.dx / 2., n * domain.dy + domain.dy / 2., domain.origin_x,
                                domain.geo_angle)
                        y = yrw(m * domain.dx + domain.dx / 2., n * domain.dy + domain.dy / 2., domain.origin_y,
                                domain.geo_angle)

                    if call_back_progress is not None:
                        call_back_progress()

                    yield x, y, a[n,m]


    def row_col_data_at_time(self, time_index, domain_index):
        """Returns the 2D array of values at the requested time and domain index."""
        try:
            domain = self.header.domains[domain_index]
        except IndexError:
            return

        pos = self.get_pos(time_index, domain_index)
        return domain[pos]


class TMO_Header:
    """
    Class for handling TMO header information.

    TMO files are stored in 64-bit blocks.
    """

    def __init__(self, file_path):
        if not exists(file_path):
            raise FileExistsError(file_path)
        if isdir(file_path):
            raise Exception('file path must be a file not a directory')
        self.domains = []
        self.times = []
        self.name, self.ext = splitext(basename(file_path))
        try:
            with open(file_path, 'rb') as fo:
                self._read_block_1(*struct.unpack('i' * 16, fo.read(64)))
                self._read_block_2(*struct.unpack('q' * 8, fo.read(64)))
                self._read_block_3(*struct.unpack('f' * 16, fo.read(64)))
                if self.data_size == 1:
                    self._read_block_4(*struct.unpack('b' * 64, fo.read(64)))
                else:
                    self._read_block_4(*struct.unpack('f' * 16, fo.read(64)))
        except struct.error as e:
            raise Exception('Error reading TMO header, possibly incomplete file: {0}'.format(e))
        except Exception as e:
            raise Exception('Reading TMO Header: {0}'.format(e))

        self.header_length = 256 + self.domain_count * 128
        for i in range(self.domain_count):
            self.domains.append(TMO_Domain(file_path, i, self.data_size))

        self.is_wd = self.data_size == 1
        self._get_times(file_path)

    def __str__(self):
        return self.name

    def _read_block_1(self, version, result_type, pad_size, data_size, data_type, is_regular_time_interval,
                        domain_count, time_count, min_max_flag, minor_version, tuflow_version, *args):
        self.version = version
        self.result_type = result_type
        self.pad_size = pad_size
        self.data_size = data_size
        self.data_type = data_type
        self.is_regular_time_interval = is_regular_time_interval
        self.domain_count = domain_count
        self.time_count = time_count
        self.min_max_flag = min_max_flag
        if self.version >= 3:
            self.minor_version = minor_version
            self.tuflow_version = tuflow_version
        else:
            self.minor_version = 0
            self.tuflow_version = -1

    def _read_block_2(self, max_data_block_size, *args):
        self.data_block_size = max_data_block_size * self.data_size + 128  # size of each data block (for all domains) considering 64-bit block size

    def _read_block_3(self, time_start, time_end, time_interval, *args):
        self.time_start = time_start
        self.time_end = time_end
        self.time_interval = time_interval

    def _read_block_4(self, null_value, ignore_value, *args):
        self.null_value = null_value
        self.ignore_value = ignore_value

    def _get_times(self, file_path):
        try:
            with open(file_path, 'rb') as fo:
                start_pos = self.header_length
                for i in range(self.time_count + self.min_max_flag):
                    fo.seek(start_pos + i * self.data_block_size)
                    self.times.extend(struct.unpack('f', fo.read(4)))
        except struct.error as e:
            return
        except Exception as e:
            self.valid = False


class TMO_Domain:
    """
    Class for handing 2D domain information.

    TMO can store multi-domain results (e.g. quadtree results) as multiple regular grids.
    This class stores header information for a given domain.

    It can also be called to get values for a given domain if
    the starting position is passed in through square brackets domain[offset].
    """

    def __init__(self, file_path, domain_index, data_size):
        self.domain_index = domain_index
        self.file_path = file_path
        self.data_size = data_size
        try:
            with open(file_path, 'rb') as fo:
                fo.seek(256 + domain_index * 128)
                self._read_block_1(*struct.unpack('i' * 8, fo.readline(32)))  # this block is split in 2
                self._read_block_2(*struct.unpack('q' * 4, fo.readline(32)))
                self._read_block_3(*struct.unpack('d' * 8, fo.readline(64)))
        except struct.error as e:
            raise Exception('Error reading TMO domain {0}, possibly incomplete file: {1}'.format(domain_index + 1, e))
        except Exception as e:
            raise Exception('Error reading TMO domain {0}: {1}'.format(domain_index + 1, e))

    def __str__(self):
        return 'Domain {0}: ox {1} oy {2} dx {3} dy {4} ncol {5} nrow {6}'.format(self.domain_index, self.origin_x,
                                                                                  self.origin_y, self.dx, self.dy,
                                                                                  self.col_count, self.row_count)

    def __getitem__(self, item):
        if not isinstance(item, int):
            raise IndexError('Index must be of type integer')
        try:
            dtype_ = np.float32 if self.data_size == 4 else np.int8
            a = np.fromfile(self.file_path, offset=item, dtype=dtype_, count=self.col_count * self.row_count)
            return np.reshape(a, (self.row_count, self.col_count))
        except struct.error as e:
            raise Exception('Error reading TMO domain {0} data at time index {1}, possibly incomplete file: {2}'.format(
                self.domain_index + 1, item, e))
        except Exception as e:
            raise Exception('Error reading TMO domain {0} data at time index {1}: {2}'.format(self.domain_index + 1,
                                                                                              item, e))


    def _read_block_1(self, col_count, row_count, *args):
        self.col_count = col_count
        self.row_count = row_count

    def _read_block_2(self, data_block_size, data_block_size_buffer, *args):
        self.data_block_size = data_block_size * self.data_size  # size of domain data in bytes
        self.data_block_size_buffer = data_block_size_buffer * self.data_size  # size of domain data in bytes but considering the 64-bit block size

    def _read_block_3(self, origin_x, origin_y, dx, dy, geo_angle, *args):
        self.origin_x = origin_x
        self.origin_y = origin_y
        self.dx = dx
        self.dy = dy
        self.geo_angle = geo_angle
