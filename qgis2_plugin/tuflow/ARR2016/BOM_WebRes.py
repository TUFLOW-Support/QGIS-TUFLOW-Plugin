import numpy
import os
import math
from ARR_TUFLOW_func_lib import *


class Bom:
    def __init__(self):  # initialise the ARR class
        self.loaded = False
        self.error = False
        self.message = None
        self.ndur = []
        self.naep = 0
        self.duration = []
        self.aep = None
        self.aep_names = []
        self.depths = None

    # noinspection PyBroadException
    def load(self, fname, frequent_events, rare_events):
        # print('Loading BOM website output .html file')
        if not os.path.isfile(fname):
            self.error = True
            self.message = 'File does not exist {0}'.format(fname)
            return
        try:
            fi = open(fname, 'r')
        except IOError:
            self.error = True
            self.message = 'Unexpected error opening file {0}'.format(fname)
            return

        # Load standard IFD
        found = False
        for ln, line in enumerate(fi):
            if line.find('class="ifdTextTableTitle">IFD Design Rainfall') >= 0:
                # print 'start of depth table found on line {0}'.format(ln+1)
                found = True
                finished = False
                header = True
                aep = []
                aep_name = []
                duration = []
                vals = []
                naep = 0
                while not finished:
                    l2 = next(fi)
                    if l2.find('</table>') >= 0:
                        finished = True
                    elif l2.find('ifdDur') >= 0:
                        if not header:
                            hour = l2.find('hour') >= 0
                            tmps = l2[l2.find('>') + 1:]
                            tmps = tmps[:tmps.find('<')]
                            try:
                                if hour:
                                    idur = float(tmps.replace(' hour', ''))
                                    duration.append(int(idur * 60))
                                else:
                                    idur = int(tmps)
                                    duration.append(idur)
                            except:
                                self.error = True
                                self.message = 'Unable to convert to duration {0}'.format(l2)
                                return

                    elif l2.find('ifdAepTableColumn') >= 0:
                        if header:  # read AEP
                            header = False
                            cols = l2.split('</th>')
                            cols.pop(-1)  # remove last
                            for col in cols:
                                col = col.strip()
                                try:
                                    aeps = col[col.rfind('>')+1:col.rfind('%')]
                                    aep.append(float(aeps))
                                    aep_name.append('{0}%'.format(aeps))
                                except TypeError:
                                    self.error = True
                                    self.message = 'Unable to convert to AEP {0}'.format(col)
                                    return
                            naep = len(aep)
                        else:  # normal row of data
                            cols = l2.split('</td>')
                            cols.pop(-1)
                            row = []
                            for col in cols:
                                col = col.strip()
                                try:
                                    tmps = col[col.rfind('>') + 1:]
                                    row.append(float(tmps))
                                except TypeError:
                                    self.error = True
                                    self.message = 'Unable to convert to depths {0}'.format(col)
                                    return
                            if len(row) == naep:
                                vals.append(row)
                            else:
                                self.error = True
                                self.message = \
                                    'Number of columns extracted does not match number of AEPs\n Line: '.format(l2)
                                return
        if not found:
            self.error = True
            self.message = 'No data read - check .html file is complete'
            return

        # checks on consistency
        ndur = len(duration)
        # print('Read {0} duration rows.'.format(nDur))
        if len(vals) != ndur:
            self.error = True
            self.message = 'Number of duration volues does not macth number of rows of data read.'
            return

        # Load Very Frequent AEP IFD
        if frequent_events:
            found = False
            fi.seek(0)
            for ln2, line2 in enumerate(fi):
                if line2.find('class="ifdTextTableTitle">Very Frequent Design Rainfall') >= 0:
                    # print 'start of depth table found on line {0}'.format(ln+1)
                    found = True
                    finished = False
                    aep_frequent = []
                    aep_name_frequent = []
                    vals_frequent = []
                    header = True
                    duration_frequent = []
                    naep_frequent = 0
                    while not finished:
                        l2 = next(fi)
                        if l2.find('</table>') >= 0:
                            finished = True
                        elif l2.find('ifdDur') >= 0:
                            if not header:
                                hour = l2.find('hour') >= 0
                                tmps = l2[l2.find('>') + 1:]
                                tmps = tmps[:tmps.find('<')]
                                try:
                                    if hour:
                                        idur = float(tmps.replace(' hour', ''))
                                        duration_frequent.append(int(idur * 60))
                                    else:
                                        idur = int(tmps)
                                        duration_frequent.append(idur)
                                except:
                                    self.error = True
                                    self.message = 'Unable to convert to duration {0}'.format(l2)
                                    return

                        elif l2.find('ifdAepTableColumn') >= 0:
                            if header:  # read AEP
                                header = False
                                cols = l2.split('</th>')
                                cols.pop(-1)  # remove last
                                for col in cols:
                                    col = col.strip()
                                    try:
                                        aeps = col[col.rfind('>') + 1:col.rfind('E')]
                                        if aeps != '1':
                                            aep_frequent.append(float(aeps))
                                            aep_name_frequent.append('{0}EY'.format(aeps))
                                    except TypeError:
                                        self.error = True
                                        self.message = 'Unable to convert to AEP {0}'.format(col)
                                        return
                                naep_frequent = len(aep_frequent)
                            else:  # normal row of data
                                cols = l2.split('</td>')
                                cols.pop(-1)
                                row = []
                                for col in cols:
                                    col = col.strip()
                                    try:
                                        tmps = col[col.rfind('>') + 1:]
                                        row.append(float(tmps))
                                    except TypeError:
                                        self.error = True
                                        self.message = 'Unable to convert to depths {0}'.format(col)
                                        return
                                if len(row) == naep_frequent + 1:
                                    vals_frequent.append(row[:5] + row[6:])
                                else:
                                    self.error = True
                                    self.message = \
                                        'Number of columns extracted does not match number of AEPs\n Line: '.format(l2)
                                    return
            if not found:
                self.error = True
                self.message = 'No data read - check .html file is complete'
                return

            # checks on consistency
            ndur_frequent = len(duration_frequent)
            # print('Read {0} duration rows.'.format(nDur))
            if len(vals) != ndur:
                self.error = True
                self.message = 'Number of duration volues does not macth number of rows of data read.'
                return
        else:
            aep_frequent = []
            naep_frequent = 0
            aep_name_frequent = []
            duration_frequent = []
            ndur_frequent = 0

        # Load Rare AEP IFD
        if rare_events:
            found = False
            fi.seek(0)
            for ln2, line2 in enumerate(fi):
                if line2.find('class="ifdTextTableTitle">Rare Design Rainfall') >= 0:
                    # print 'start of depth table found on line {0}'.format(ln+1)
                    found = True
                    finished = False
                    aep_rare = []
                    aep_name_rare = []
                    vals_rare = []
                    header = True
                    duration_rare = []
                    naep_rare = 0
                    while not finished:
                        l2 = next(fi)
                        if l2.find('</table>') >= 0:
                            finished = True
                        elif l2.find('ifdDur') >= 0:
                            if not header:
                                hour = l2.find('hour') >= 0
                                tmps = l2[l2.find('>') + 1:]
                                tmps = tmps[:tmps.find('<')]
                                try:
                                    if hour:
                                        idur = float(tmps.replace(' hour', ''))
                                        duration_rare.append(int(idur * 60))
                                    else:
                                        idur = int(tmps)
                                        duration_rare.append(idur)
                                except:
                                    self.error = True
                                    self.message = 'Unable to convert to duration {0}'.format(l2)
                                    return

                        elif l2.find('ifdAepTableColumn') >= 0:
                            if header:  # read AEP
                                header = False
                                cols = l2.split('</th>')
                                cols.pop(-1)  # remove last
                                for col in cols:
                                    col = col.strip()
                                    try:
                                        aeps = col[col.rfind('>') + 6:]
                                        if aeps != '100':
                                            aep_rare.append(float(aeps))
                                            aep_name_rare.append('1 in {0}'.format(aeps))
                                    except TypeError:
                                        self.error = True
                                        self.message = 'Unable to convert to AEP {0}'.format(col)
                                        return
                                naep_rare = len(aep_rare)
                            else:  # normal row of data
                                cols = l2.split('</td>')
                                cols.pop(-1)
                                row = []
                                for col in cols:
                                    col = col.strip()
                                    try:
                                        tmps = col[col.rfind('>') + 1:]
                                        row.append(float(tmps))
                                    except TypeError:
                                        self.error = True
                                        self.message = 'Unable to convert to depths {0}'.format(col)
                                        return
                                if len(row) == naep_rare + 1:
                                    vals_rare.append(row[1:])
                                else:
                                    self.error = True
                                    self.message = \
                                        'Number of columns extracted does not match number of AEPs\n Line: '.format(l2)
                                    return
            if not found:
                self.error = True
                self.message = 'No data read - check .html file is complete'
                return

            # checks on consistency
            ndur_rare = len(duration_rare)
            # print('Read {0} duration rows.'.format(nDur))
            if len(vals) != ndur:
                self.error = True
                self.message = 'Number of duration volues does not macth number of rows of data read.'
                return
        else:
            aep_rare = []
            naep_rare = 0
            aep_name_rare = []
            duration_rare = []
            ndur_rare = 0

        # move it into a numpy array
        try:
            depths_normal = numpy.ones((ndur, naep)) * - 99
            for i in range(ndur):
                val = vals[i]
                for j in range(naep):
                    depths_normal[i, j] = val[j]
#
            if frequent_events:
                depths_frequent = numpy.ones((ndur_frequent, naep_frequent)) * -99
                for i in range(ndur_frequent):
                    val = vals_frequent[i]
                    for j in range(naep_frequent):
                        depths_frequent[i, j] = val[j]
#
            if rare_events:
                depths_rare = numpy.ones((ndur_rare, naep_rare)) * -99
                for i in range(ndur_rare):
                    val = vals_rare[i]
                    for j in range(naep_rare):
                        depths_rare[i, j] = val[j]
                com_aep, com_dur, dep_com, com_dur_index = common_data(aep_rare, duration, aep_rare,
                                                                       duration_rare, depths_normal)
                depths_rare = extend_array(com_dur_index, com_aep, depths_rare, duration)
#
            depths = depths_normal
            if frequent_events:
                depths = numpy.append(depths_frequent, depths, axis=1)
            if rare_events:
                depths = numpy.append(depths, depths_rare, axis=1)
        except:
            self.error = True
            self.message = 'Error converting to numpy array.'
            return

        # checks
        if numpy.nanmin(depths) <= 0:
            self.error = True
            self.message = 'Error  - Negative rainfall depth encountered!'
            return

        # store relevant  info in class
        self.ndur = ndur + ndur_frequent + ndur_rare
        self.naep = naep + naep_frequent + naep_rare
        self.duration = duration
        self.aep = aep_frequent + aep + aep_rare
        self.aep_names = aep_name_frequent + aep_name + aep_name_rare
        self.depths = depths

    def save(self, fname, name):
        if not os.path.exists(os.path.dirname(fname)):  # check output directory exists
            os.mkdir(os.path.dirname(fname))
        try:
            fo = open(fname, 'w')
        except IOError:
            self.error = True
            self.message = 'Unexpected error opening file {0}'.format(fname)
            return

        # write header
        line = 'Duration'
        for AEP in self.aep_names:
            line = line + ',{0}'.format(AEP)
        line = line + '\n'
        fo.write(line)

        # Loop through each duration
        for i, dur in enumerate(self.duration):
            line = '{0}'.format(dur)
            for j in range(self.naep):
                if numpy.isnan(self.depths[i, j]):
                    line = line + ',-'
                else:
                    line = line + ',{0}'.format(self.depths[i, j])
            line = line+'\n'
            fo.write(line)

        # close up
        fo.flush()
        fo.close()

        # Save figure
        fig_name = '{0}.png'.format(os.path.splitext(fname)[0])
        ymax = 10 ** math.ceil(math.log10(numpy.nanmax(self.depths)))
        ymin = 10 ** math.floor(math.log10(numpy.nanmin(self.depths))) if numpy.nanmin(self.depths) > 0. else 0.001
        make_figure(fig_name, self.duration, self.depths, 1, 10000, ymin, ymax, 'Duration (mins)', 'Depth (mm)',
                    'Design Rainfall Depths: {0}'.format(name), self.aep_names, loglog=True)
