"""A module for downloading ERA5 data from the Climate Data Store (CDS) using the CDSAPI."""

# import packages, objects & function

import glob
import os
import re

from netCDF4 import Dataset
import cdsapi

if __name__ == 'tuflow.swangis.swangis.downloads':  # called from tuflow plugin
    from tuflow.swangis.swangis.mdatetime import *
else:
    from swangis.mdatetime import *


# metadata for ERA5 requests
metadata = \
    {
        'wind':
            {
                'model_name': 'reanalysis-era5-single-levels',
                'product_type': 'reanalysis',
                'variable': ['10m_u_component_of_wind', '10m_v_component_of_wind'],
                'format': 'netcdf',
            },

        'temperature':
            {
                'model_name': 'reanalysis-era5-single-levels',
                'product_type': 'reanalysis',
                'variable': ['2m_temperature'],
                'format': 'netcdf',
            },

        'radiation':
            {
                'model_name': 'reanalysis-era5-single-levels',
                'product_type': 'reanalysis',
                'variable': ['mean_surface_downward_long_wave_radiation_flux',
                             'mean_surface_downward_short_wave_radiation_flux'],
                'format': 'netcdf',
            },

        'pressure':
            {
                'model_name': 'reanalysis-era5-single-levels',
                'product_type': 'reanalysis',
                'variable': ['mean_sea_level_pressure'],
                'format': 'netcdf',
            },

        'humidity':
            {
                'model_name': 'reanalysis-era5-pressure-levels',
                'product_type': 'reanalysis',
                'variable': ['relative_humidity'],
                'pressure_level': '1000',
                'format': 'netcdf',
            },

        'waves':
            {
                'model_name': 'reanalysis-era5-single-levels',
                'product_type': 'reanalysis',
                'variable': ['mean_wave_direction', 'mean_wave_period', 'peak_wave_period',
                             'significant_height_of_combined_wind_waves_and_swell'],
                'format': 'netcdf',
            },

        'cloud_cover':
            {
                'model_name': 'reanalysis-era5-pressure-levels',
                'product_type': 'reanalysis',
                'variable': ['fraction_of_cloud_cover'],
                'pressure_level': '1000',
                'format': 'netcdf',
            },

        'precipitation':
            {
                'model_name': 'reanalysis-era5-single-levels',
                'product_type': 'reanalysis',
                'variable': ['mean_total_precipitation_rate'],
                'format': 'netcdf',
            },
    }


class ProgressBar:
    """Iterator class for tracking progress of for loops. Inspired by 'progress' package on PyPi."""

    def __init__(self, count=100, width=40, fill='█', format='[{barString}] {percentComplete}%'):
        # set basic attributes
        self.count = count
        self.width = width
        self.fill = fill
        self.format = format

        # set counter to zero
        self.counter = 0

        # log the start time
        self.startTime = dt.datetime.now().timestamp()

        # print
        self.print()

    @property
    def currentTime(self):
        """Returns the current time as python timestamp rounded to the nearest second"""

        return round(dt.datetime.now().timestamp())

    @property
    def elapsedTime(self):
        """Returns elapsed time rounded to the nearest second"""

        return round(self.currentTime - self.startTime)

    @property
    def remainingTime(self):
        """Returns estimate of remaining time rounded to nearest second"""

        if self.percentComplete != 0:
            return round((1 / (self.percentComplete / 100) - 1) * self.elapsedTime)
        else:
            return 'NaN'

    @property
    def percentComplete(self):
        """Returns percent complete as an integer"""

        if self.count != 0:
            return round(self.counter/self.count*100)
        else:
            return 100

    @property
    def barString(self):
        """Returns progress bar as string"""

        # get counter relative to bar width
        counter = round(self.percentComplete/100*self.width)

        # return the progress bar string
        return counter*self.fill + (self.width - counter)*'-'

    def __iter__(self):
        """Returns the iterator (self)"""
        return self

    def __next__(self):
        """Updates the counter and prints progress to sys.stdout"""
        self.counter += 1
        self.print()

    def print(self):
        """Returns carriage on current line and print the progress bar to sys.stdout"""

        # get iterator properties as dictionary
        properties = {key: getattr(self, key) for key in dir(self) if '__' not in key}

        # get message with using format string
        message = self.format.format(**properties)

        # add carriage return on current line
        message = '\r' + message

        # print message to sys.stdout
        print(message, end='', flush=True)

    def next(self):
        """Calls next() on self"""
        next(self)


def upToDate(file):
    """
    Checks if file is up to date.

    Parameters
    ----------
    file : string
        File path of monthly ERA5 file to check

    Returns
    -------
    upToDate : boolean
        True if file is up to date.
    """

    # check if file exists
    if not os.path.isfile(file):
        return False

    # get year and month of existing data file using regular expression
    pattern = re.compile('ERA5_(.*)_(\d{4})(\d{2})')  # create pattern object
    content = pattern.findall(file)[0]  # find content of first and only match
    variable, year, month = content  # unpack the content into variables
    year, month = int(year), int(month)  # convert strings to integers

    # find what the last time value should be
    t1 = datenum((year, month, 1, 0, 0, 0))
    t2 = datenum((year, month, daysInMonth(t1), 23, 0, 0))

    # convert to ERA5 time convention
    t2 = (t2 + (datenum((1970, 1, 1)) - datenum((1900, 1, 1))))/3600

    # check time values match those in the file
    nc = Dataset(file, 'r')
    if nc['time'][:].data[-1] == t2:
        return True
    else:
        return False


def download(variable, xLimit, yLimit, tLimit, outFolder='.',  nameTag=None):
    """
    A wrapper around the csdapi Client() object. Downloads ERA5 data in monthly intervals.

    Parameters
    ----------
    variable : string
        Name of variable to download. See metadata.keys() for list of variables.
    xLimit : tuple
        Longitudinal bounds of data as (x1, x2)
    yLimit : tuple
        Latitudinal bounds of data as (y1, y2)
    tLimit : tuple
        Temporal bounds of data as (t1, t2)

    Other Parameters
    ----------------
    outFolder : string, '.'
        Optional output destination for monthly files. Default is current working directory.
    nameTag : string, None
        Optional file name prefix used to describe the data. Default is None.
    """

    # check if cdsapi key is accessible
    home = os.path.expanduser("~")
    if not os.path.isfile(home + '\\.cdsapirc'):
        raise Exception('Cannot find csdapi key')

    # get monthly download intervals
    intervals = drange(tLimit[0], tLimit[1], unit='month', step=1)

    # count number of intervals
    count = len(intervals) - 1

    # specify the area as [N, W, S, E]. Default: Global.
    area = [yLimit[1], xLimit[0], yLimit[0], xLimit[1]]

    # print basic message about variable and interval
    ts_str = datestr(intervals[0], '%d/%m/%Y')
    te_str = datestr(intervals[-1], '%d/%m/%Y')
    print('\nDownloading {} data from {} to {}'.format(variable, ts_str, te_str))

    # create progress bar
    bar = ProgressBar(count=count, format='[{barString}] {percentComplete}% | Elapsed time: {elapsedTime}s | ' +
                                          'Time remaining: {remainingTime}s')

    # iterate over intervals
    for aa in range(count):
        # get download times
        year = intervals[aa].year
        month = intervals[aa].month

        days = ['{:02d}'.format(dd) for dd in range(1, 32)]
        times = ['{:02d}:00'.format(tt) for tt in range(0, 24)]

        # get request attributes for given variable
        payload = metadata[variable]

        # add area and time information to the request payload
        payload = {**payload, 'area': area, 'year': year, 'month': month, 'day': days, 'time': times}

        # get output file name using standard format
        outName = 'ERA5_{}_{:04d}{:02d}.nc'.format(variable.upper(), year, month)

        # append name tag to front of file
        if nameTag is not None:
            outName = nameTag + '_' + outName

        # get absolute output file path
        outFile = os.path.abspath(outFolder + '\\' + outName)

        if not upToDate(outFile):
            # download data using cdsapi Client() with payload if valid file does not exist
            cdsapi.Client(quiet=True).retrieve(payload.get('model_name'), payload, outFile)

            # iterate progress bar
            bar.next()
        else:
            # hack bar to discount skipped file
            bar.count -= 1
            bar.print()


def merge(variable, inFolder='.', outFolder='.', nameTag=None, tLimit=None):
    """

    Merges monthly ERA5 files.

    Parameters
    ----------
    variable : string
        Name of variable to merge. See metadata.keys() for list of variables.

    Other Parameters
    ----------------
    inFolder : string, '.'
        Optional input location of monthly files. Default is current working directory.
    outFolder : string, '.'
        Optional output destination for merged file. Default is current working directory.
    nameTag : string, None
        Optional file name prefix used to describe the data. Default is None.
    tLimit : tuple
        Optional temporal bounds for merging data as (t1, t2)
    """

    # get all netCDf4 file paths in input folder
    if nameTag is None:
        search = inFolder + '\\ERA5_*.nc'
    else:
        search = inFolder + '\\' + nameTag + '_ERA5_*.nc'

    files = sorted([file for file in glob.glob(search)])

    # filter raw data files using regular expression
    pattern, aa = re.compile('ERA5_(.*)_(\d{4})(\d{2})'), 0
    while aa < len(files):
        content = pattern.findall(files[aa])
        if len(content) == 0:
            files.pop(aa)
        else:
            if content[0][0] != variable.upper():
                files.pop(aa)
            else:
                aa += 1

    # return None if no files to merge
    if len(files) == 0:
        return None

    # get unique time steps
    time = np.empty((0,), dtype=np.float64)
    for file in files:
        nc_in = Dataset(file, 'r')
        time = np.hstack((time, nc_in['time'][:]))
        nc_in.close()
    time = np.unique(time)

    # if time limit applied, trim time array
    if tLimit is not None:
        time = time[((tLimit[0] - datenum((1900, 1, 1)))/3600 <= time) &
                     (time <= (tLimit[1] - datenum((1900, 1, 1)))/3600)]

    # get start and end times
    epoch = dt.datetime(1900, 1, 1)
    ts = epoch + dt.timedelta(hours=time[0])
    ts_str = ts.strftime('%Y%m%d')

    tf = epoch + dt.timedelta(hours=time[-1])
    tf_str = tf.strftime('%Y%m%d')

    # get output file path
    outName = 'ERA5_{}_{}_{}'.format(variable.upper(), ts_str, tf_str)

    if nameTag is not None:
        outName = nameTag + '_' + outName

    outFile = os.path.abspath(outFolder + '\\' + outName)

    # create output netCDF4 file
    ncOut = Dataset(outFile, 'w', format='NETCDF4')

    # get handle on template file
    ncIn = Dataset(files[0], 'r')

    # create dimensions
    for dim in ncIn.dimensions.values():
        if dim.name == 'time':
            ncOut.createDimension(dim.name, 0)
        else:
            ncOut.createDimension(dim.name, dim.size)

    # create variables
    variables = []
    for var in list(ncIn.variables.values()):
        # specify dimensions of variable
        dims = list(var.dimensions)

        # create variable
        ncOut.createVariable(var.name, var.dtype.str, dims, fill_value=var[:].fill_value)

        # set attributes
        attributes = var.ncattrs()
        for att in attributes:
            if att == '_FillValue':
                continue
            ncOut[var.name].setncattr(att, var.getncattr(att))

        # if time varying, store variable name
        if 'time' in dims:
            variables.append(var.name)
        # else, store static data
        else:
            ncOut[var.name][:] = var[:]

    # clear handle on template file
    ncIn.close()

    # print basic message about variable and interval
    print('\nMerging {} data from {} to {}'.format(variable, ts.strftime('%d/%m/%Y'), tf.strftime('%d/%m/%Y')))

    # create progress bar
    bar = ProgressBar(count=len(files), format='[{barString}] {percentComplete}% | Elapsed time: {elapsedTime}s | ' +
                                          'Time remaining: {remainingTime}s')

    # compile time varying data
    for file in files:
        ncIn = Dataset(file, 'r')
        nt = ncOut['time'].size

        for aa in range(len(variables)):
            # get time logical index
            if tLimit is not None:
                lgi = (tLimit[0] <= ncIn['time'][:]) & (ncIn['time'][:] <= tLimit[1])
            else:
                lgi = np.ones(ncIn['time'].shape, dtype=np.bool)

            # index data along time dimension
            data = ncIn[variables[aa]][lgi]

            # append data along infinite time dimension
            ncOut[variables[aa]][nt:] = data

            # note: it would be good if this function could be made general. i.e. a mechanism
            #        to detect the time dimension and index it rather then hard coding.

        # iterate on progress bar
        bar.next()

    # close output file handle
    ncOut.close()
