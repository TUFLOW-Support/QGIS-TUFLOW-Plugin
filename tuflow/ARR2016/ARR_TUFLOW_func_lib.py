import io
import re
from datetime import datetime

import numpy as np
from math import log10
import matplotlib as mpl
import pandas as pd

mpl.use('qt5agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter
import matplotlib.ticker as ticker
import warnings
import logging
warnings.filterwarnings("ignore", category =RuntimeWarning)


def get_args(argv):
    """Get command arguments for input. Flags will begin with '-' and can be followed by values."""

    error = False
    message = ''
    arguments = {}
    loop_limit = 100
    loop_count = 0
    while argv:
        loop_count += 1
        assert loop_count < loop_limit, "Get Argument Loop Limit Reached: {0}".format(loop_limit)
        try:
            if argv[0][0] == '-':  # argument is flag
                try:
                    float(argv[0])  # if this works, then most likely latitude value and not a flag
                except:
                    try:
                        for i, arg in enumerate(argv[1:]):  # find index of next argument flag.
                            if arg[0] == '-':
                                try:
                                    float(arg)  # if this works, then most likely latitude value and not a flag
                                except:
                                    end_index = i + 1
                                    break
                            else:
                                end_index = i + 2
                        arguments[argv[0][1:].lower()] = argv[1:end_index]
                    except:
                        error = True
                        message = '{0}Unable to Read Arg: "{1}" Value: "{2}"\n'.format(message, argv[0], arg)
                        return error, message, arguments
        except:
            pass
        argv = argv[1:]  # remove processed argument
    return error, message, arguments


def common_index(input_list, compare_list):
    """Compares lists. Outputs the value and index from input list that are found in the compare list."""

    common_values = []
    common_values_index = []
    for i, value in enumerate(input_list):
        if value in compare_list:
            common_values.append(value)
            common_values_index.append(i)
    return common_values, common_values_index


def common_data(input_aep, input_dur, compare_aep, compare_dur, input_array):
    """Takes a numpy data array and returns an array of common data using the comparison AEPs and Durations."""

    common_aep, common_aep_index = common_index(input_aep, compare_aep)
    common_dur, common_dur_index = common_index(input_dur, compare_dur)
    common_data_values = []
    for i, dur in enumerate(input_array):
        if i in common_dur_index:
            common_data_value = dur[np.array(common_aep_index)]
            common_data_values.append(common_data_value)
    common_data_values = np.array(common_data_values)
    return common_aep, common_dur, common_data_values, common_dur_index


def rahman(dur, aep, ils):
    """Returns numpy array of calculated losses using Rahman et al 2002 and converts to numpy array

    dur: list of durations
    aep: np array single row
    ils: float of storm loss"""

    ils = float(ils)
    shape = np.shape(aep)

    ilr = []
    for d in dur:
        d = float(d)
        if d < 60:
            row = []
            loss = ils * (0.5 + 0.25 * log10(d / 60.0))
            row.append(loss)
            row = row * shape[0]
            ilr.append(row)
    ilr_array = np.array(ilr)

    return ilr_array


def hill(dur, aep, ils, mar):
    """Returns numpy array of calculated losses using Hill et al 1996:1998

    list dur: durations
    np array single row aep: Annual Exceedance probability
    float ils: storm initial loss
    float mar: Mean Annual Rainfall"""

    ils = float(ils)
    mar = float(mar)
    shape = np.shape(aep)

    ilh = []
    for d in dur:
        if d < 60.0:
            row = []
            loss = ils * (1.0 - (1.0 / (1.0 + 142.0 * (d / 60.0)**0.5 / mar)))
            row.append(loss)
            row = row * shape[0]
            ilh.append(row)
    ilh_array = np.array(ilh)

    return ilh_array


def static(dur, aep, staticLoss):
    """Return numpy array of static values

    list dur: event durations
    np array single row: Annual Exceedence Probability
    float staticLoss: user input loss to be adopted < 60min"""

    staticLoss = float(staticLoss)
    shape = np.shape(aep)

    ilStatic = []
    for d in dur:
        if d < 60.0:
            row = [staticLoss] * shape[0]
            ilStatic.append(row)
    ilStatic_array = np.array(ilStatic)

    return ilStatic_array


def use_60min(dur, aep60m):
    """Return numpy array of values adopting 60min loss

    list dur: event durations
    np array aep60m: single row of 60min losses"""

    aep60m = np.reshape(aep60m, [1, len(aep60m)])
    shape = np.shape(aep60m)

    il60m = np.zeros(shape)
    for d in dur:
        if d < 60.0:
            row = aep60m
            il60m = np.append(il60m, row, axis=0)
    il60m = np.delete(il60m, 0, axis=0)

    return il60m


def extend_array_dur(common_dur_index, common_aep, input_array, dur):
    """Takes an array and extends the durations (rows) with nan values.

    common_dur_index: list of index positions in the extended array
    common_aep: list of the common aep values
    input_array: numpy array to be extended
    dur: list of durations that the array will be extended to"""

    shape = [len(dur), len(common_aep)]  # shape of the new extended array

    # Create new array and insert values from input array into correct positions based on duration
    extended_array = np.multiply(np.zeros(shape), np.nan)
    array_index = 0
    for i, values in enumerate(extended_array):
        if i in common_dur_index:
            extended_array[i] = input_array[array_index]
            array_index += 1

    return extended_array


def extend_array_aep(common_aep, complete_aep, input_array, interpolate_missing=True, extrapolate_missing=False):
    """
    Takes an array and extends the aep (columns) with nan values.
    
    :param common_aep: list -> str common aep names
    :param complete_aep: list -> str all aep names
    :param input_array: ndarray -> current complete initial loss array
    :param interpolate_missing: bool interpolate unknown values
    :param extrapolate_missing: bool extrapolate unknown values
    :return: ndarray
    """

    old_shape = input_array.shape
    new_shape = (old_shape[0], len(complete_aep))  # shape of the new extended array
    
    # get common aep indexes
    common_aep_indexes = []  # index of common aeps in complete aep list
    for aep in common_aep:
        index = complete_aep.index(aep)
        common_aep_indexes.append(index)
        
    # Create new array and insert values from input array into correct positions based on common aep
    extended_array = np.multiply(np.zeros(new_shape), np.nan)
    for i in range(new_shape[1]):  # iterate through columns
        if i in common_aep_indexes:
            j = common_aep_indexes.index(i)  # index of column in original input array
            values = input_array[:,j]
            extended_array[:,i] = values

    # interpolate 0.2EY and 0.5EY if needed and settings in turned on
    if interpolate_missing:
        if '0.2EY' in complete_aep:
            print('Interpolating initial loss values for 0.2EY...')
            i = complete_aep.index('0.2EY')
            lower_i = complete_aep.index('20%')
            upper_i = complete_aep.index('10%')
            lower_array = np.reshape(extended_array[:,lower_i], (1, extended_array.shape[0]))
            upper_array = np.reshape(extended_array[:,upper_i], (1, extended_array.shape[0]))
            inter_array = interpolate(5, 4.48, 10, lower_array, upper_array)
            extended_array = np.delete(extended_array, i, axis=1)
            extended_array = np.insert(extended_array, i, inter_array, axis=1)
        if '0.5EY' in complete_aep:
            print('Interrpolating initial loss values for 0.5EY...')
            i = complete_aep.index('0.5EY')
            lower_i = complete_aep.index('50%')
            upper_i = complete_aep.index('20%')
            lower_array = np.reshape(extended_array[:,lower_i], (1, extended_array.shape[0]))
            upper_array = np.reshape(extended_array[:,upper_i], (1, extended_array.shape[0]))
            inter_array = interpolate(2, 1.44, 4.48, lower_array, upper_array)
            extended_array = np.delete(extended_array, i, axis=1)
            extended_array = np.insert(extended_array, i, inter_array, axis=1)

    return extended_array
            

def interpolate(ref, lower_ref, upper_ref, lower_values, upper_values):
    """Interpolates between single row numpy arrrays.

    ref: float of reference number getting interpolated value for
    lower_ref: float of lower reference value
    upper_ref: float of upper reference value
    lower_values: single row numpy array interpolating between
    upper_values: single row numpy array interpolating between"""

    a = np.add(upper_values, -lower_values)
    b = upper_ref - lower_ref
    c = ref - lower_ref

    int_values = np.add(lower_values, (a / b * c))
    return int_values


def interpolate_nan(input_array, dur, ils ,**kwargs):
    """Removes nan values in numpy array using linear interpolation. Will not extrapolate beyond data range.

    input_array: numpy array containing nan values
    dur: duration list that will be used as reference for interpolation"""
    lossMethod = ''
    staticLoss = 0.
    mar = 0.
    for kw in kwargs:
        if kw.lower() == 'lossmethod':
            lossMethod = kwargs[kw]
        if kw.lower() == 'mar':
            mar = kwargs[kw]
        if kw.lower() == 'staticloss':
            staticLoss = kwargs[kw]

    # setup interpolated array with values less than 60min based on user defined loss method
    int_array = np.insert(input_array, 0, np.nan, axis=1)  # add column at front for duration values
    if lossMethod == 'interpolate':
        int_array = np.insert(int_array, 0, 0, axis=0)  # add row at front with zero values
    elif lossMethod == 'interpolate_log':
        xp = [0, np.log10(60.)]
        ind = dur.index(60)
        for i, dur_ in enumerate(dur):
            if dur_ >= 60.:
                break
            for j in range(input_array.shape[1]):
                fp = [0, input_array[ind][j]]
                int_array[i][j+1] = np.interp(np.log10(dur_), xp, fp)
        int_array = np.insert(int_array, 0, 0, axis=0)
    elif lossMethod == 'rahman':
        il_array = rahman(dur, input_array[0], ils)
        il_array_shape = np.shape(il_array)
        for i in range(il_array_shape[0]):
            for j in range(il_array_shape[1]):
                int_array[i][j+1] = il_array[i][j]
        int_array = np.insert(int_array, 0, 0, axis=0)
    elif lossMethod == 'hill':
        il_array = hill(dur, input_array[0], ils, mar)
        il_array_shape = np.shape(il_array)
        for i in range(il_array_shape[0]):
            for j in range(il_array_shape[1]):
                int_array[i][j + 1] = il_array[i][j]
        int_array = np.insert(int_array, 0, 0, axis=0)
    elif lossMethod == 'static':
        il_array = static(dur, input_array[0], staticLoss)
        il_array_shape = np.shape(il_array)
        for i in range(il_array_shape[0]):
            for j in range(il_array_shape[1]):
                int_array[i][j + 1] = il_array[i][j]
        int_array = np.insert(int_array, 0, 0, axis=0)
    elif lossMethod == '60min':
        for i, d in enumerate(dur):
            if d == 60:
                ind60m = i
        il_array = use_60min(dur, input_array[ind60m])
        il_array_shape = np.shape(il_array)
        for i in range(il_array_shape[0]):
            for j in range(il_array_shape[1]):
                int_array[i][j + 1] = il_array[i][j]
        int_array = np.insert(int_array, 0, 0, axis=0)
    else:
        int_array = np.insert(int_array, 0, 0, axis=0)

    # Populate first column with duration values (skipping first row)
    k = None
    for i, duration in enumerate(dur):
        int_array[i + 1][0] = dur[i]

        # extend array for dur > 72hrs
        if duration == 4320:
            k = i + 1
        if duration > 4320 and k is not None:
            for j in range(int_array.shape[1] - 1):
                int_array[i+1,j+1] = int_array[k,j+1]

    # fill in nan values by interpolating
    for i, row in enumerate(int_array):
        if np.isnan(row[1]):
            for j, sub_row in enumerate(int_array[i:]):
                if not np.isnan(sub_row[1]):
                    upper = sub_row
                    break
            try:
                lower = int_array[i - 1]
                int_array[i][1:] = interpolate(row[0], lower[0], upper[0], lower[1:], upper[1:])
                upper = None
            except:
                break  # cannot find upper value for interpolation

    # Tidy up array - delete first row and first column
    int_array = np.delete(int_array, 0, axis=0)
    int_array = np.delete(int_array, 0, axis=1)

    return int_array


def arf_eqn241(area, duration, aep):
    """Short duration ARF equation 2.4.1

    area: km2
    duration: mins
    AEP: fraction (between 0.5 and 0.0005)"""

    area = float(area)
    duration = float(duration)
    aep = float(aep)

    arf = 1.0 - 0.287 * (area ** 0.265 - 0.439 * log10(duration)) * duration ** (-0.36) + \
          2.26 * 10.0 ** (-3.0) * area ** 0.226 * duration ** 0.125 * (0.3 + log10(aep)) + \
          0.0141 * area ** 0.213 * 10.0 ** ((-0.021 * (duration - 180) ** 2.0) / 1440) * (0.3 + log10(aep))

    return min(1.0, arf)


def arf_eqn242(area, duration, aep, a, b, c, d, e, f, g, h, i):
    """Long duration ARF equation ARR2016

     - Formally eqn244 in the plugin prior to 3.1.4.33

    area: km2
    duration: mins
    AEP: fraction (between 0.5 and 0.0005)"""

    area = float(area)
    duration = float(duration)
    aep = float(aep)
    a = float(a)
    b = float(b)
    c = float(c)
    d = float(d)
    e = float(e)
    f = float(f)
    g = float(g)
    h = float(h)
    i = float(i)

    arf = 1.0 - a * (area ** b - c * log10(duration)) * duration ** (-d) + \
          e * area ** f * duration ** g * (0.3 + log10(aep)) + \
          h * 10.0 ** (i * area * (duration / 1440.0)) * (0.3 + log10(aep))

    return min(1.0, arf)


def arf_eqn243(duration, arf12h, arf24h):
    """Short duration ARF equation 2.4.2

    - Formally eqn242 in the plugin prior to 3.1.4.33

    duration: min
    arf12h (ARF 10km2 12h): fraction
    arf24h (ARF 10km2 24h): fraction"""

    duration = float(duration)
    arf12h = float(arf12h)
    arf24h = float(arf24h)

    arf = arf12h + (arf24h - arf12h) * ((duration - 720.0) / 720.0)
    return arf


def arf_eqn244(area, arf10k):
    """Short duration ARF equation 2.4.3

    - Formally eqn243 in the plugin prior to 3.1.4.33

    area: km2
    arf10k (ARF 10km2): fraction"""

    area = float(area)
    arf10k = float(arf10k)

    arf = 1.0 - 0.6614 * (1.0 - arf10k) * (area ** 0.4 - 1.0)
    return arf


def short_arf(area, duration_list, aep_list, ARF_frequent, min_ARF):
    """Short duration ARF equation ARR2016

    area: km2
    duration: mins
    AEP(%): 50 and 0.05)"""

    logger = logging.getLogger('ARR2019')

    AEP_max = 100 if ARF_frequent == True else 50

    if area <= 1:
        arf_array = np.ones(len(duration_list), len(aep_list))

    elif area <= 10:
        arf_list = []  # ARF list that will be converted to numpy array
        for duration in duration_list:
            arf_row = []  # ARF row (create a list of lists so can be converted to numpy array)
            for aep in aep_list:
                if 0.05 <= aep <= AEP_max:
                    # arf10km2 = arf_eqn242(duration, arf_eqn241(10, 720, (aep / 100)), arf_eqn241(10, 1440, (aep / 100)))
                    # arf = arf_eqn243(area, arf10km2)
                    # 3.1.4.33 - changed above 2 lines to the below
                    arf10km2 = arf_eqn241(10, duration, (aep / 100))
                    arf = arf_eqn244(area, arf10km2)
                    if arf >= min_ARF:
                        arf_row.append(arf)
                    else:
                        arf_row.append(min_ARF)
                else:
                    arf_row.append(1)
            arf_list.append(arf_row)

        arf_array = np.array(arf_list)

    elif area <= 1000:
        arf_list = []  # ARF list that will be converted to numpy array
        for duration in duration_list:
            arf_row = []  # ARF row (create a list of lists so can be converted to numpy array)
            for aep in aep_list:
                if 0.05 <= aep <= AEP_max:
                    arf = arf_eqn241(area, duration, (aep / 100))
                    if arf >= min_ARF:
                        arf_row.append(arf)
                    else:
                        arf_row.append(min_ARF)
                else:
                    arf_row.append(1)
            arf_list.append(arf_row)

        arf_array = np.array(arf_list)

    else:
        # print('WARNING: {0:.0f}km2 out of range of generalised equations for short duration ARF factors. '
        #       'Applying method for 1000km2, however this may not be applicable for catchment. '
        #       'Please consult ARR2016'.format(area))
        logger.warning('WARNING: {0:,.0f}km2 out of range of generalised equations for short duration ARF factors. '
                       'Applying method for 1000km2, however this may not be applicable for catchment. '
                       'Please consult ARR'.format(area))
        arf_list = []  # ARF list that will be converted to numpy array
        for duration in duration_list:
            arf_row = []  # ARF row (create a list of lists so can be converted to numpy array)
            for aep in aep_list:
                if 0.05 <= aep <= AEP_max:
                    arf = arf_eqn241(area, duration, (aep / 100))
                    if arf >= min_ARF:
                        arf_row.append(arf)
                    else:
                        arf_row.append(min_ARF)
                else:
                    arf_row.append(1)
            arf_list.append(arf_row)

        arf_array = np.array(arf_list)

    return arf_array


def medium_arf(area, duration_list, aep_list, a, b, c, d, e, f, g, h, i, ARF_frequent, min_ARF):
    """Long duration ARF equation ARR2016

    area: km2
    duration: mins
    AEP(%): between 50 and 0.05"""

    logger = logging.getLogger('ARR2019')

    AEP_max = 100 if ARF_frequent == True else 50

    if area <= 1:
        arf_array = np.ones(len(duration_list), len(aep_list))

    elif area <= 10:
        arf_list = []  # ARF list that will be converted to numpy array
        for duration in duration_list:
            arf_row = []  # ARF row (create a list of lists so can be converted to numpy array)
            for aep in aep_list:
                if 0.05 <= aep <= AEP_max:
                    # arf10km2 = arf_eqn242(duration,
                    #                       arf_eqn241(10, 720, (aep / 100)),
                    #                       arf_eqn244(10, 1440, (aep / 100), a, b, c, d, e, f, g, h, i))
                    # arf = arf_eqn243(area, arf10km2)

                    # 3.1.4.33 - same process as above but with new eqn names.
                    # ARR still seems to ref incorrect equations - no doubt will be fixing this again in the future
                    arf10km24h = arf_eqn242(10, 1440, (aep / 100), a, b, c, d, e, f, g, h, i)
                    arf10km12h = arf_eqn241(10, 720, (aep / 100))
                    arf10km = arf_eqn243(duration, arf10km12h, arf10km24h)  # in ARR they say use eqn 2.4.4
                    arf = arf_eqn244(area, arf10km)  # in ARR they say use eqn 2.4.3
                    if arf >= min_ARF:
                        arf_row.append(arf)
                    else:
                        arf_row.append(min_ARF)
                else:
                    arf_row.append(1)
            arf_list.append(arf_row)

        arf_array = np.array(arf_list)

    elif area <= 30000:
        arf_list = []  # ARF list that will be converted to numpy array
        for duration in duration_list:
            arf_row = []  # ARF row (create a list of lists so can be converted to numpy array)
            for aep in aep_list:
                if 0.05 <= aep <= AEP_max:
                    # arf = arf_eqn242(duration,
                    #                  arf_eqn241(area, 720, (aep / 100)),
                    #                  arf_eqn244(area, 1440, (aep / 100), a, b, c, d, e, f, g, h, i))

                    # 3.1.4.33 - same process as above but with new eqn names.
                    arf24h = arf_eqn242(area, 1440, (aep / 100), a, b, c, d, e, f, g, h, i)
                    arf12h = arf_eqn241(area, 720, (aep / 100))
                    arf = arf_eqn243(duration, arf12h, arf24h)

                    if arf >= min_ARF:
                        arf_row.append(arf)
                    else:
                        arf_row.append(min_ARF)
                else:
                    arf_row.append(1)
            arf_list.append(arf_row)

        arf_array = np.array(arf_list)

    else:
        # print('WARNING: {0:.0f}km2 out of range of generalised equations for medium duration ARF factors. ' \
        #       'Applying method for 30,000km2, however this may not be applicable for cathcment. ' \
        #       'Please consult ARR2016.'.format(area))
        logger.warning('WARNING: {0:,.0f}km2 out of range of generalised equations for medium duration ARF factors. ' \
                       'Applying method for 30,000km2, however this may not be applicable for catchment. ' \
                       'Please consult ARR.'.format(area))
        arf_list = []  # ARF list that will be converted to numpy array
        for duration in duration_list:
            arf_row = []  # ARF row (create a list of lists so can be converted to numpy array)
            for aep in aep_list:
                if 0.05 <= aep <= AEP_max:
                    # arf = arf_eqn242(duration,
                    #                  arf_eqn241(area, 720, (aep / 100)),
                    #                  arf_eqn244(area, 1440, (aep / 100), a, b, c, d, e, f, g, h, i))

                    # 3.1.4.33 - same process as above but with new eqn names.
                    arf24h = arf_eqn242(area, 1440, (aep / 100), a, b, c, d, e, f, g, h, i)
                    arf12h = arf_eqn241(area, 720, (aep / 100))
                    arf = arf_eqn243(duration, arf12h, arf24h)

                    if arf >= min_ARF:
                        arf_row.append(arf)
                    else:
                        arf_row.append(min_ARF)
                else:
                    arf_row.append(1)
            arf_list.append(arf_row)

        arf_array = np.array(arf_list)
        # if arf_array.shape != [len(duration_list), len(aep_list)]:
        #    arf_array = np.zeros(len(duration_list), len(aep_list)) + 1

    return arf_array


def long_arf(area, duration_list, aep_list, a, b, c, d, e, f, g, h, i, ARF_frequent, min_ARF):
    """Long duration ARF equation ARR2016

    area: km2
    duration: mins
    AEP(%): between 50 and 0.05"""

    logger = logging.getLogger('ARR2019')

    AEP_max = 100 if ARF_frequent == True else 50

    if area <= 1:
        arf_array = np.ones(len(duration_list), len(aep_list))

    elif area <= 10:
        arf_list = []  # ARF list that will be converted to numpy array
        for duration in duration_list:
            arf_row = []  # ARF row (create a list of lists so can be converted to numpy array)
            for aep in aep_list:
                if 0.05 <= aep <= AEP_max:
                    # arf10km2 = arf_eqn244(10, duration, (aep / 100), a, b, c, d, e, f, g, h, i)
                    # arf = arf_eqn243(area, arf10km2)

                    # 3.1.4.33 - same process as above but with new eqn names.
                    arf10km2 = arf_eqn242(10, duration, (aep / 100), a, b, c, d, e, f, g, h, i)
                    arf = arf_eqn244(area, arf10km2)

                    if arf >= min_ARF:
                        arf_row.append(arf)
                    else:
                        arf_row.append(min_ARF)
                else:
                    arf_row.append(1)
            arf_list.append(arf_row)

        arf_array = np.array(arf_list)

    elif area <= 30000:
        arf_list = []  # ARF list that will be converted to numpy array
        for duration in duration_list:
            arf_row = []  # ARF row (create a list of lists so can be converted to numpy array)
            for aep in aep_list:
                if 0.05 <= aep <= AEP_max:
                    # arf = arf_eqn244(area, duration, (aep / 100), a, b, c, d, e, f, g, h, i)

                    # 3.1.4.33 - same process as above but with new eqn names.
                    arf = arf_eqn242(area, duration, (aep / 100), a, b, c, d, e, f, g, h, i)

                    if arf >= min_ARF:
                        arf_row.append(arf)
                    else:
                        arf_row.append(min_ARF)
                else:
                    arf_row.append(1)
            arf_list.append(arf_row)

        arf_array = np.array(arf_list)

    else:
        # print('WARNING: {0:.0f}km2 out of range of generalised equations for long duration ARF factors. '
        #       'Applying method for 30,000km2, however this may not be applicable for cathcment. '
        #       'Please consult ARR2016.'.format(area))
        logger.warning('WARNING: {0:,.0f}km2 out of range of generalised equations for long duration ARF factors. '
                       'Applying method for 30,000km2, however this may not be applicable for catchment. '
                       'Please consult ARR.'.format(area))
        arf_list = []  # ARF list that will be converted to numpy array
        for duration in duration_list:
            arf_row = []  # ARF row (create a list of lists so can be converted to numpy array)
            for aep in aep_list:
                if aep <= AEP_max and aep >= 0.05:
                    # arf = arf_eqn244(area, duration, (aep / 100), a, b, c, d, e, f, g, h, i)

                    # 3.1.4.33 - same process as above but with new eqn names.
                    arf = arf_eqn242(area, duration, (aep / 100), a, b, c, d, e, f, g, h, i)

                    if arf >= min_ARF:
                        arf_row.append(arf)
                    else:
                        arf_row.append(min_ARF)
                else:
                    arf_row.append(1)
            arf_list.append(arf_row)

        arf_array = np.array(arf_list)

    return arf_array


def arf_factors(area, duration_list, aep_name_list, a, b, c, d, e, f, g, h, i, ARF_frequent, min_ARF):
    """returns numpy array of ARF factors"""

    # housekeeping, convert aep name list to proper aeps (EY to AEP etc)
    aep_list = []
    for aep in aep_name_list:
        # EY
        if aep[-2:] == 'EY':
            ey = float(aep.strip('EY'))
            aep_conv = {12: 99.85, 6: 99.75, 4: 98.17, 3: 95.02, 2: 86.47, 1: 63.21, 0.5: 39.35, 0.2: 18.13}
            aep = aep_conv[ey]
            aep_list.append(aep)
        # AEP
        elif aep[-1] == '%':
            aep = float(aep[:-1])
            aep_list.append(aep)
        # 1 in X
        elif aep.find('1 in') >= 0:
            ari = float(aep[5:])
            aep = 1 / ari * 100
            aep_list.append(aep)
        else:
            print('Unrecognised storm event magnitude')
            return

    short_dur_list = []
    medium_dur_list = []
    long_dur_list = []

    for duration in duration_list:
        if duration <= 720:
            short_dur_list.append(duration)
        elif duration < 1440:
            medium_dur_list.append(duration)
        else:
            long_dur_list.append(duration)

    short_dur_arf = short_arf(area, short_dur_list, aep_list, ARF_frequent, min_ARF)
    medium_dur_arf = medium_arf(area, medium_dur_list, aep_list, a, b, c, d, e, f, g, h, i, ARF_frequent, min_ARF)
    long_dur_arf = long_arf(area, long_dur_list, aep_list, a, b, c, d, e, f, g, h, i, ARF_frequent, min_ARF)

    if len(short_dur_list) < 1 and len(medium_dur_list) < 1:
        all_arf = long_dur_arf
    elif len(short_dur_list) < 1:
        all_arf = np.append(medium_dur_arf, long_dur_arf, axis=0)
    elif len(medium_dur_list) < 1 and len(long_dur_list) < 1:
        all_arf = short_dur_arf
    elif len(long_dur_list) < 1:
        all_arf = np.append(short_dur_arf, medium_dur_arf, axis=0)
    elif len(medium_dur_list) < 1:
        all_arf = np.append(short_dur_arf, long_dur_arf, axis=0)
    else:
        all_arf = np.append(np.append(short_dur_arf, medium_dur_arf, axis=0), long_dur_arf, axis=0)

    return all_arf

def myLogFormat(y, pos):
    """Function to format log axis to correct decimal points"""

    a = -np.log10(y)
    b = np.maximum(a, 0)
    decimalPlaces = int(b)
    formatstring = '{{:.{:1d}f}}'.format(decimalPlaces)

    return formatstring.format(y)

def make_figure(fig_name, xdata, ydata, xmin, xmax, ymin, ymax, xaxis_name, yaxis_name, chart_title, legend, **kws):
    use_formatter = False
    fig, ax = plt.subplots()
    ax.axis([xmin, xmax, ymin, ymax])
    for kw in kws:
        if kw.lower() == 'loglog':
            if kws[kw] == True:
                ax.loglog()
                use_formatter = True
        if kw.lower() == 'ylog':
            if kws[kw] == True:
                plt.yscale('log')
                use_formatter = True
        if kw.lower() == 'xlog':
            if kws[kw] == True:
                plt.xscale('log')
    plt.grid(True)
    for axis in [ax.xaxis, ax.yaxis]:
        axis.set_major_formatter(ScalarFormatter())
    if use_formatter:
        ax.yaxis.set_major_formatter(ticker.FuncFormatter(myLogFormat))
    plt.xlabel(xaxis_name)
    plt.ylabel(yaxis_name)
    plt.title(chart_title)
    plt.plot(xdata, ydata)
    lgd = plt.legend(legend, bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
    plt.savefig(fig_name, bbox_extra_artists=(lgd,), bbox_inches='tight')

    return


def tpRegion_coords(region):
    """returns a list of coordinates for additional temporal pattern regions

    list regions: a list of region names"""

    region_dict = {
                   'rangelands west': [-23.3026, 118.1178],
                   'wet tropics': [-16.9202, 145.7727],
                   'rangelands': [-23.70173, 133.8766],
                   'central slopes': [-26.5715, 148.7845],
                   'monsoonal north': [-12.4538, 130.8412],
                   'murray basin': [-35.3086, 149.1244],
                   'east coast north': [-27.6541, 152.6674],
                   'east coast south': [-33.8701, 151.2063],
                   'southern slopes mainland': [-37.8171, 144.9552],
                   'southern slopes tasmania': [-42.8798, 147.3217],
                   'east flatlands': [-34.9237, 138.6000],
                   'west flatlands': [-31.9509, 115.8578]
                  }

    return region_dict[region.lower()]


def convertMagToAEP(mag, unit, frequent_events):
    """
    Convert incoming magnitude to an AEP
    
    :param mag: str event magnitude
    :param unit: str magnitude unit... 'ARI' 'AEP' 'EY'
    :param frequent_events: bool frequent events are included
    """

    if frequent_events:
        aep_conv = {5: '0.2EY', 2: '0.5EY', 1: '63.2%'}
    else:
        aep_conv = {5: '20%', 2: '50%', 1: '63.2%'}  # closest conversion for small ARI events

    message = ''
    # convert magnitude to float
    if unit.lower() == 'ey':
        mag = float(mag)
    else:
        mag = float(mag[:-1])
    # convert ari to aep
    if unit.lower() == 'ari':
        if mag <= 5:
            try:
                if mag == 1:
                    print('MESSAGE: ARI {0:.0f} year being converted to available AEP'.format(mag))
                    print('MESSAGE: using {0}'.format(aep_conv[mag]))
                elif frequent_events:
                    print('MESSAGE: ARI {0:.0f} year being converted to available EY'.format(mag))
                    print('MESSAGE: using {0}'.format(aep_conv[mag]))
                else:
                    print('WARNING: ARI {0} year does not correspond to available AEP'.format(mag))
                    print('MESSAGE: using closest available AEP: {0}.. or turn on "frequent events" ' \
                          'to obtain exact storm magnitude'.format(aep_conv[mag]))
                if mag in aep_conv:
                    return aep_conv[mag]
                else:
                    return None
            except:
                message = 'Unable to convert ARI {0}year to AEP'.format(mag)
        elif mag <= 100:
            return '{0:.0f}%'.format((1 / float(mag)) * 100)
        else:
            return '{0}%'.format((1 / float(mag)) * 100)
    elif unit.lower() == 'ey':
        if mag >= 1:
            return '{0:.0f}EY'.format(mag)
        else:
            return '{0}EY'.format(mag)
    elif unit.lower() == 'aep':
        if mag > 50:
            return '{0:.1f}%'.format(mag)
        elif mag >= 1:
            return '{0:.0f}%'.format(mag)
        else:
            return '{0}%'.format(mag)
    
    return None


def linear_interp_pb_dep(pb_depths, durations, dur_inds):
    pbdur = np.array(durations)[dur_inds]  # pre-burst durations (mins)

    a = []
    x = durations[:dur_inds[0]]
    xp = [0, pbdur[0]]
    for i in range(pb_depths.shape[1]):
        fp = [0, pb_depths[0,i]]
        a_ = np.interp(x, xp, fp)
        a.append(a_)
    a = np.transpose(np.array(a))

    pb_depths = np.insert(pb_depths, 0, a, axis=0)

    return pb_depths


def log_interp_pb_dep(pb_depths, durations, dur_inds):
    durations_ = np.log10(durations)
    return linear_interp_pb_dep(pb_depths, durations_, dur_inds)


class DataBlock:

    def __init__(self, fi, start_text: str):
        self.fi = fi
        self.start_text = start_text
        self.finished = False
        self.data = {}
        self.time_accessed = None
        self.version = ''
        self.version_int = -1
        self._collect()

    def _find_start(self):
        for line in self.fi:
            if self.start_text in line:
                return True
        self.fi.seek(0)
        return False

    def _collect(self):
        if not self._find_start():
            return
        while not self.finished:
            self._block()
        self.fi.seek(0)

    def _block(self):
        line = None
        for line in self.fi:
            if f'END_{self.start_text}' in line:
                self.finished = True
                return
            if '[' in line and 'END' not in line:
                break
        if not line:
            self.finished = True
            return
        name = line.strip('[]\n')
        if 'META' in name:
            self._meta_block()
            return
        buf = io.StringIO()
        for line in self.fi:
            if 'END' in line:
                break
            buf.write(line)
        buf.seek(0)
        df = pd.read_csv(buf, index_col=0)
        self.data[name] = df

    def _meta_block(self):
        self.time_accessed = self.fi.readline().split(',')[1].strip()
        try:
            self.time_accessed = datetime.strptime(self.time_accessed, '%d %B %Y %I:%M%p')
        except:
            pass
        self.version = self.fi.readline().split(',')[1].strip()
        try:
            major, minor = self.version.split('_', 1)
            self.version_int = int(major) * 1000 + int(minor.strip('v')) * 100
        except:
            pass

