from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import qgsfunction, QgsProcessingAlgorithm, QgsProcessingParameterFile
import numpy as np
import re


FORWARD_LOOK_COUNT = 3  # integer value
PERC_DIFF_BETWEEN_MAX_AND_TS = 5.  # percent value
LIKELY_UNSTABLE_COUNT_LIMIT = 4  # integer value
LIKELY_UNSTABLE_PERC_LIMIT = 5.  # percent value
POSSIBLY_UNSTABLE_COUNT_LIMIT = 1  # integer value
POSSIBLY_UNSTABLE_PERC_LIMIT = 1.  # percent value


def attname_to_float(name):
    '''Converts GIS field name to a float.'''
    return float(name.replace('_', '.').strip('t'))


def field_names(feature, start=0):
    '''Field name iterator given an input feature. Can specify a field start index.'''
    for i in range(start, feature.fields().count()):
        yield feature.fields()[i].name()


def field_names_to_float(feature, start):
    '''Converts field names of a given feature to floats. Can specify a field start index.'''
    for field_name in field_names(feature, start):
        yield attname_to_float(field_name)


def diff(a):
    '''
    Calculates the difference between sequential rows in a 1D array.
    Will maintain the array length by inserting a zero at the start.
    '''
    if a.shape[0] < 2:
        return np.array([])
    return np.insert(a[1:] - a[:-1], 0, 0.)  # keeps array size the same as input size


class TS_GIS_Feature:

    def __init__(self, feature):
        self.feature = feature
        self.ts_data = np.array([])
        self.ts_max = np.array([])
        self.ts_min = np.array([])
        self.max = np.array([])
        self.min = np.array([])
        self.output_interval = None
        self.minmax_loaded = False
        self.gradient = np.array([])
        self.gradient = np.array([])
        self.sign = np.array([])
        self.sign_diff = np.array([])

        self._load()

    def _load(self):
        start = -1
        for j, field_name in enumerate(field_names(self.feature)):
            if re.findall(r'^t\d_\d+', field_name):
                start = j
                break

        xdata = [x for x in field_names_to_float(self.feature, start)]
        if len(xdata) > 1:
            self.output_interval = xdata[1] - xdata[0]
        ydata = self.feature.attributes()[start:]
        self.ts_data = np.array(list(zip(xdata, ydata)))
        ts_max = np.nanmax(self.ts_data[:,1])
        self.ts_max = np.array([self.ts_data[self.ts_data[:,1] == ts_max][0][0], ts_max])
        ts_min = np.nanmin(self.ts_data[:,1])
        self.ts_min = np.array([self.ts_data[self.ts_data[:, 1] == ts_min][0][0], ts_min])

        try:
            max_ = [self.feature.attribute(i) for i, x in enumerate(field_names(self.feature)) if x == 'Max'][0]
            time_max_ = [self.feature.attribute(i) for i, x in enumerate(field_names(self.feature)) if x == 'Time_Max'][0]
            self.max = np.array([time_max_, max_])
            min_ = [self.feature.attribute(i) for i, x in enumerate(field_names(self.feature)) if x == 'Min'][0]
            time_min_ = [self.feature.attribute(i) for i, x in enumerate(field_names(self.feature)) if x == 'Time_Min'][0]
            self.min = np.array([time_min_, min_])
            self.minmax_loaded = True
        except IndexError:
            pass

        self.gradient = diff(self.ts_data[:, 0]) / diff(self.ts_data[:, 1])
        self.gradient = np.nan_to_num(self.gradient, True, 0., 0., 0.)
        self.sign = np.sign(self.gradient)
        self.sign_diff = diff(self.sign)

    def is_unstable(self, climit, plimit, flag_neg_values):
        # check for negative values
        if flag_neg_values:
            if self.minmax_loaded and self.min[1] < 0.:
                return True
            elif not self.minmax_loaded and self.ts_min[1] < 0.:
                return True

        # check timing difference between min/max
        if self.minmax_loaded:
            if abs(self.max[0] - self.min[0]) <= self.output_interval * FORWARD_LOOK_COUNT and not np.isclose(self.min[0], self.ts_data[0,0], atol=self.output_interval):
                return True
        if abs(self.ts_max[0] - self.ts_min[0]) <= self.output_interval * FORWARD_LOOK_COUNT and not np.isclose(self.ts_min[0], self.ts_data[0,0], atol=self.output_interval):
            return True

        # check how different max and ts_max / min and ts_min are
        if self.minmax_loaded:
            atol_y = abs(self.ts_max[1] - self.ts_min[1]) * (PERC_DIFF_BETWEEN_MAX_AND_TS / 100.)
            if not np.isclose(self.ts_max[1], self.max[1], atol=atol_y) \
                    or not np.isclose(self.ts_min[1], self.min[1], atol=atol_y):
                return True
            # check timing of max as well
            atol_x = abs(self.ts_data[-1,0] - self.ts_data[0,0]) * (PERC_DIFF_BETWEEN_MAX_AND_TS / 100.)
            if not np.isclose(self.ts_max[0], self.max[0], atol=atol_x):
                interpolated_value = np.interp(self.max[0], self.ts_data[:,0], self.ts_data[:,1])
                if not np.isclose(interpolated_value, self.max[1], atol=atol_y):
                    return True

        # check bouncing
        count = 0
        sdiffprev = 0.
        bounce = 0
        indexes = []
        for i, sdiff in enumerate(self.sign_diff):
            count += 1
            if count > FORWARD_LOOK_COUNT:
                sdiffprev = 0.
                count = 0

            if abs(sdiff) + abs(sdiffprev) == 4:
                bounce += 1
                count = 0
                sdiffprev = sdiff
                indexes.append(i)
                continue

            if abs(sdiff) > abs(sdiffprev):
                sdiffprev = sdiff
                count = 0

        if bounce <= climit:
            return False

        mags = []
        for i in indexes:
            mag = 0.
            for k1 in range(FORWARD_LOOK_COUNT, -1, -1):
                si = max(0, i - k1)
                for k2 in range(1, FORWARD_LOOK_COUNT + 1):
                    ei = si + k2
                    mag_diff = abs(self.ts_data[ei, 1] - self.ts_data[si, 1])
                    mag = max(mag, mag_diff)

            mags.append(mag)

        mags = np.array(mags)
        total_range = np.nanmax(self.ts_data[:, 1]) - np.nanmin(self.ts_data[:, 1])
        value_diff_bounce_perc = mags / total_range * 100

        return np.where(value_diff_bounce_perc > plimit)[0].shape[0] > climit


@qgsfunction(args="auto", group='Custom')
def tuflow_ts_likely_unstable(feature, parent, context):
    time_series = TS_GIS_Feature(feature)
    return time_series.is_unstable(LIKELY_UNSTABLE_COUNT_LIMIT, LIKELY_UNSTABLE_PERC_LIMIT, False)


@qgsfunction(args="auto", group='Custom')
def tuflow_ts_possibly_unstable(feature, parent, context):
    time_series = TS_GIS_Feature(feature)
    return not time_series.is_unstable(LIKELY_UNSTABLE_COUNT_LIMIT, LIKELY_UNSTABLE_PERC_LIMIT, False) and \
            time_series.is_unstable(POSSIBLY_UNSTABLE_COUNT_LIMIT, POSSIBLY_UNSTABLE_PERC_LIMIT, True)


class CustomStylingFunctions(QgsProcessingAlgorithm):

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFile('dummy', 'Dummy Input', optional=True,
                                                     behavior=QgsProcessingParameterFile.File, fileFilter='ALL (*.)',
                                                     defaultValue=None))

    def processAlgorithm(self, parameters, context, model_feedback):
        return {}

    def name(self):
        return 'Custom TUFLOW Styling Functions'

    def displayName(self):
        return self.tr(self.name())

    def group(self):
        return self.tr(self.groupId())

    def groupId(self):
        return ''

    def shortHelpString(self):
        return self.tr(
            "Ancillary database of custom functions used by the TUFLOW plugin for styling."
            "This toolbox does not run any scripts, it only serves as a helper to the TUFLOW "
            "plugin."
        )

    def shortDescription(self):
        return self.tr("Ancillary database of custom functions used by the TUFLOW plugin for styling."
                       "This toolbox does not run any scripts, it only serves as a helper to the TUFLOW "
                       "plugin.")

    def createInstance(self):
        return CustomStylingFunctions()

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)