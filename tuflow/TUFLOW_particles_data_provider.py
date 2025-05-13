from datetime import datetime
import re
import netCDF4
from qgis.PyQt.QtWidgets import QMessageBox

class TuParticlesDataProviderError(BaseException):
    pass

class TuParticlesDataProvider:
    def __init__(self):
        self.filename = None
        self.nc = None
        self.times = [] # Python DateTimes (absolute)
        self.reference_time = None # Python DateTime
        self.default_reference_time = None
        self.has_reference_time = False
        self.crs = None

    def load_file(self, filename, defaultRefTime=None):
        """
        Loads a netCDF4 filename

        :param filename: full path to particles result file
        :return: bool -> True for successful, False for unsuccessful
        """

        self.filename = filename
        self.default_reference_time = defaultRefTime
        self.nc = netCDF4.Dataset(self.filename, 'r')
        try:
            self._fill_times_arr()
        except (KeyError, TuParticlesDataProviderError) as e:
            QMessageBox.critical(None, 'Loading Particles', f'{e}')
            self.nc = None

        return self._is_valid_file()

    def getReferenceTime(self):
        """
        Return refencence time as python datetime

        :return: Reference time
        """
        return self.reference_time

    def timeSteps(self, zerotime):
        """
        Return relative times in hours to the zerotime

        :return: array of relative times in hours
        """
        rel_times_in_hour = []
        for t in self.times:
            timediference = t - zerotime
            hours = timediference.total_seconds() / 3600.0
            rel_times_in_hour += [hours]
        return rel_times_in_hour

    def read_data_at_time(self, at_time):
        """
        Return data for attributes for particular time index (at_time is the index in the self.times)
        """
        if self.nc is None:
            return None

        if self.times is None:
            return None

        if at_time < 0 or at_time >= self.times.shape[0]:
            return None

        ignored_vars = ['Time']
        data = {}
        variables = self.nc.variables.keys()
        for var in variables:
            if var in ignored_vars:  # if variable should be ignored, e.g. Time
                continue
            if self.nc.variables[var].ndim == 1:  # 1D variable
                data[var] = self.nc.variables[var][:].data
            elif self.nc.variables[var].ndim == 2:  # 2D variable
                data[var] = self.nc.variables[var][at_time, :].data
            elif self.nc.variables[var].ndim == 3:  # 3D variable
                third_dimension_size = self.nc.variables[var].shape[2]
                if third_dimension_size == 1:
                    # variables with dimension time * trajectory * 1, so _x or _1 is unnecessary
                    data[var] = self.nc.variables[var][at_time, :, 0].data
                elif third_dimension_size == 3 and var != 'mass':  # variables f.e. uvw, uvw_water
                    data[var + '_x'] = self.nc.variables[var][at_time, :, 0].data
                    data[var + '_y'] = self.nc.variables[var][at_time, :, 1].data
                    data[var + '_z'] = self.nc.variables[var][at_time, :, 2].data
                else:  # other variables, f.e. mass
                    for i in range(third_dimension_size):
                        data[var + '_' + str(i)] = self.nc.variables[var][at_time, :, i].data
            else:
                pass  # unknown dimensions

        return data

    def get_all_variable_names(self, debug=False):
        """
            Return the names of the attributes that are in the file
        """
        vars = list(self.nc.variables.keys())
        ignore_vars = ['Time', 'x', 'y', 'z'] if not debug else ['Time']

        ret_vars = []
        for var in vars:
            if var in ignore_vars:
                continue

            var_dim = self.nc.variables[var].ndim
            if var_dim == 1 or var_dim == 2:
                ret_vars.append(var)
            if var_dim == 3:  # 3 dimensional variable, change to _x or _1 ..
                third_dimension_size = self.nc.variables[var].shape[2]
                if third_dimension_size == 1:
                    # variables with dimension time * trajectory * 1, so _x or _1 is unnecessary
                    ret_vars.append(var)
                elif third_dimension_size == 3 and var != 'mass':  # variables f.e. uvw, uvw_water
                    ret_vars.extend([var + '_x', var + '_y', var + '_z'])
                else:  # other variables, f.e. mass
                    for i in range(third_dimension_size):
                        ret_vars.append(var + '_' + str(i))

        return ret_vars

    def _build_time_string(self, override_reference_time=None):
        units = self.nc.variables['Time'].units
        name = self.nc.variables['Time'].long_name

        # string needs to be converted to format '<units> since <datetime>'
        time_tokens = name.split(' ')[-2:]
        if len(time_tokens) != 2:
            raise TuParticlesDataProviderError("Invalid time long_name")

        conditions = [bool(re.match(re.compile('^[0-9]+'), candidate)) for candidate in time_tokens]
        if not (conditions[0] and conditions[1]):
            if override_reference_time is None:
                if self.default_reference_time is None:
                    raise TuParticlesDataProviderError("Invalid time long_name")
                else:
                    date = self.default_reference_time

            else:
                date = override_reference_time
            self.has_reference_time = False
        else:
            if override_reference_time is None:
                # d/m/y needs to be converted to y-m-d
                date = ' '.join(time_tokens)
                date = datetime.strptime(date, '%d/%m/%Y %H:%M:%S')
            else:
                date = override_reference_time
                self.has_reference_time = True

        # needed format example: hours since 1950-01-01T00:00:00Z
        time_string = units + ' since ' + date.strftime('%Y-%m-%dT%H:%M:%SZ')
        return date, time_string

    def _fill_times_arr(self, override_reference_time=None):
        reference_time, time_string = self._build_time_string(override_reference_time)
        time_data = self.nc.variables['Time'][:].data
        self.times = netCDF4.num2date(time_data, units=time_string, only_use_python_datetimes=True)
        self.reference_time = reference_time

    def _is_valid_file(self):
        if self.nc is None:
            return False
        variable_names = self.nc.variables.keys()
        mandatory_variables = ['x', 'y', 'z', 'Time', 'groupID']
        return all(must_var in variable_names for must_var in mandatory_variables)

    def set_reference_time(self, time):
        self._fill_times_arr(override_reference_time=time)
