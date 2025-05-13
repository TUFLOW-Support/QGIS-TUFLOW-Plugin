import sys
from datetime import datetime

from qgis.PyQt.QtCore import QObject, pyqtSignal, QTimer, QThread, QSettings
from qgis.core import QgsUnitTypes, NULL
import numpy as np


class Branch:

    def __init__(self, id_):
        self.id = id_
        self.branches = []
        self.count = 0

    def __len__(self):
        return len(self.branches)

    def add(self, branch):
        self.branches.append(branch)
        self.count += 1


class Branches:

    def __init__(self, max_count):
        self.branches = []
        self.max_count = max_count

    def __getitem__(self, item):
        return self.branches[item]

    def __len__(self):
        return sum([len(x) for x in self.branches])

    def add(self, branch):
        self.branches.append(branch)
        return branch.count == self.max_count

    def isValid(self):
        return len([x for x in self.branches if x.count > 0]) > 0

    def max(self):
        return max(self.branches, key=lambda x: x.count).branches


class ContinuityLimits:

    def __init__(self, units, flowTraceTool):
        self._units = units
        self._area_flag = flowTraceTool.bCheckArea
        self._invert_flag = flowTraceTool.bCheckInvert
        self._gradient_flag = flowTraceTool.bCheckInvert
        self._angle_flag = flowTraceTool.bCheckAngle
        self._cover_flag = flowTraceTool.bCheckCover
        self._area_flag_list = {x: 1 for x in flowTraceTool.flaggedAreaIds}
        self._invert_flag_list = {x: 1 for x in flowTraceTool.flaggedInvertIds}
        self._gradient_flag_list = {x: 1 for x in flowTraceTool.flaggedGradientIds}
        self._angle_flag_list = {x: 1 for x in flowTraceTool.flaggedAngleIds}
        self._cover_flag_list = {x: 1 for x in flowTraceTool.flaggedCoverIds_}

        self._area_flag_labels = {x: flowTraceTool.flaggedAreaLabel[i] for i, x in enumerate(flowTraceTool.flaggedAreaIds)}
        self._invert_flag_labels = {x: flowTraceTool.flaggedInvertLabel[i] for i, x in enumerate(flowTraceTool.flaggedInvertIds)}
        self._gradient_flag_labels = {x: flowTraceTool.flaggedGradientLabel[i] for i, x in enumerate(flowTraceTool.flaggedGradientIds)}
        self._angle_flag_labels = {x: flowTraceTool.flaggedAngleLabel[i] for i, x in enumerate(flowTraceTool.flaggedAngleIds)}
        self._cover_flag_labels = {x: flowTraceTool.flaggedCoverLabel[i] for i, x in enumerate(flowTraceTool.flaggedCoverIds_)}

        self._cover_flag_chainage = {x: flowTraceTool.flaggedCoverChainage[i] for i, x in enumerate(flowTraceTool.flaggedCoverIds_)}

    def areaFlag(self, id_):
        if self._area_flag:
            return bool(self._area_flag_list.get(id_))

        return False

    def areaLabel(self, id_):
        return self._area_flag_labels[id_] if id_ in self._area_flag_labels else ''

    def invertFlag(self, id_):
        if self._invert_flag:
            return bool(self._invert_flag_list.get(id_))

        return False

    def invertLabel(self, id_):
        return self._invert_flag_labels[id_] if id_ in self._invert_flag_labels else ''

    def gradientFlag(self, id_):
        if self._gradient_flag:
            return bool(self._gradient_flag_list.get(id_))

        return False

    def gradientLabel(self, id_):
        return self._gradient_flag_labels[id_] if id_ in self._gradient_flag_labels else ''

    def angleFlag(self, id_):
        if self._angle_flag:
            return bool(self._angle_flag_list.get(id_))

        return False

    def angleLabel(self, id_):
        return self._angle_flag_labels[id_] if id_ in self._angle_flag_labels else ''

    def coverFlag(self, id_):
        if self._cover_flag:
            return bool(self._cover_flag_list.get(id_))

        return False

    def coverLabel(self, id_):
        return self._cover_flag_labels[id_] if id_ in self._cover_flag_labels else ''

    def coverChainage(self, id_):
        return self._cover_flag_chainage[id_] if id_ in self._cover_flag_chainage else 0.


class Connectivity(QObject):

    branchesCollected = pyqtSignal()
    populatedInfo = pyqtSignal()
    error = pyqtSignal()
    updated = pyqtSignal()
    started = pyqtSignal()

    def __init__(self, start_lines, data_collector):
        QObject.__init__(self)
        self.start_lines = start_lines[:]
        self.data_collector = data_collector
        self.valid = False
        self.known_error = False
        self.errmsg = None
        self.stack_trace = False
        self.timer = None
        self.thread = None

        # upstream trace
        self.branches = []

        # plot stuff - mostly legacy naming so the plotting routines don't need updating
        self.pathsName = []
        self.pathsChan = []
        self.pathsGround = []
        self.pathsPipe = []
        self.pathsPlotDecA = []
        self.pathsPlotAdvI = []
        self.pathsPlotAdvG = []
        self.pathsPlotSharpA = []
        self.pathsPlotInCover = []

        self.pathsPlotDecALabel = []
        self.pathsPlotAdvILabel = []
        self.pathsPlotAdvGLabel = []
        self.pathsPlotSharpALabel = []
        self.pathsPlotInCoverLabel = []

        self.ids = [data_collector.feature2id[x[0]][x[1]] for x in start_lines]

    def getBranches(self):
        print('getBranches')
        try:
            branch_max = -1
            if len(self.ids) > 1:
                branch_max = len(self.ids) - 1

            if branch_max == -1:
                self.valid = self._trace_upstream(self.ids[0], None)
            else:
                branches = Branches(branch_max)
                for id1 in self.ids:
                    branch = Branch(id1)
                    for id2 in self.ids:
                        if id1 == id2:
                            continue
                        if self._trace_upstream(id1, id2) and self.branches and self.branches[0]:
                            branch.add(self.branches[0])

                    if branches.add(branch):
                        break

                if branches.isValid():
                    self.branches = branches.max()
                    self.valid = True

            print('finished getBranches')

            self.branchesCollected.emit()
        except:
            import sys
            import traceback
            if not self.known_error:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                self.stack_trace = True
                self.errmsg = ''.join(traceback.extract_tb(exc_traceback).format()) + '{0}{1}'.format(exc_type, exc_value)
            self.error.emit()

    def populateInfo(self, continuity_limits):
        feats = self.data_collector.features
        drapes = self.data_collector.drapes

        try:
            # work out max path length - this is so left -> right = upstream -> downstream and the selected outlet is
            # at the same chainage for all paths in the plot window
            ch_max = 0.
            ch_gr_max = 0.
            for i, branch in enumerate(self.branches):
                ch = sum([feats[x].length for x in branch if x in feats])
                ch_max = max(ch, ch_max)

                ch_gr = sum([drapes[x].chainages[-1] for x in branch if x in drapes and drapes[x].chainages])
                ch_gr_max = max(ch_gr, ch_gr_max)

            self.started.emit()
            for i, branch in enumerate(self.branches):
                chan, ground, pipes, decA, advI, advG, sharpA, inCover = [[] for _ in range(8)]
                decALabel, advILabel, advGLabel, sharpALabel, inCoverLabel = [[] for _ in range(5)]
                self.pathsName.append('Path {0}'.format(i+1))

                ch = ch_max
                ch_gr = ch_gr_max
                for id_ in branch:
                    if id_ not in feats:
                        continue

                    f = feats[id_]
                    ch_ = ch  # store start chainage

                    # channel invert
                    chan.append((ch, f.invertDs))
                    ch -= f.length
                    chan.append((ch, f.invertUs))

                    # ground level
                    if id_ in drapes and [x for x in drapes[id_].elevations if x is not None]:
                        ch_gr -= drapes[id_].chainages[-1]
                        j = len(drapes[id_].chainages) - 1
                        ground.extend([(ch_gr + x, drapes[id_].elevations[j-i]) for i, x in enumerate(reversed(drapes[id_].chainages))])
                    else:
                        ch_gr -= f.length

                    # pipe data
                    height = f.height_
                    if not isinstance(height, float):
                        height = 0.
                    pipes.append(np.array([[ch, f.invertUs], [ch_, f.invertDs], [ch_, f.invertDs + height],
                                          [ch, f.invertUs + height]]))

                    if continuity_limits.areaFlag(id_):
                        decA.append(self._flag_xy(ch_, None, f.invertDs, None, f.invertDs + f.height_, None, 'end'))
                        decALabel.append(continuity_limits.areaLabel(id_))

                    if continuity_limits.invertFlag(id_):
                        advI.append(self._flag_xy(ch_, None, f.invertDs, None, f.invertDs + f.height_, None, 'end'))
                        advILabel.append(continuity_limits.invertLabel(id_))

                    if continuity_limits.gradientFlag(id_):
                        advG.append(self._flag_xy(ch, ch_, f.invertDs, f.invertDs, f.invertDs + f.height_, f.invertUs + f.height_, 'halfway'))
                        advGLabel.append(continuity_limits.gradientLabel(id_))

                    if continuity_limits.angleFlag(id_):
                        sharpA.append(self._flag_xy(ch_, None, f.invertDs, None, f.invertDs + f.height_, None, 'end'))
                        sharpALabel.append(continuity_limits.angleLabel(id_))

                    if continuity_limits.coverFlag(id_):
                        chainage = continuity_limits.coverChainage(id_) + ch
                        inCover.append(self._flag_xy(ch, ch_, f.invertDs, f.invertDs, f.invertDs + f.height_, f.invertUs + f.height_, 'chainage', chainage))
                        inCoverLabel.append(continuity_limits.coverLabel(id_))

                    self.updated.emit()

                self.pathsChan.append(np.array(chan))
                self.pathsGround.append(np.array(ground))
                self.pathsPipe.append(pipes)
                self.pathsPlotDecA.append(np.array(decA))
                self.pathsPlotAdvI.append(np.array(advI))
                self.pathsPlotAdvG.append(np.array(advG))
                self.pathsPlotSharpA.append(np.array(sharpA))
                self.pathsPlotInCover.append(np.array(inCover))

                self.pathsPlotDecALabel.append(decALabel[:])
                self.pathsPlotAdvILabel.append(advILabel[:])
                self.pathsPlotAdvGLabel.append(advGLabel[:])
                self.pathsPlotSharpALabel.append(sharpALabel[:])
                self.pathsPlotInCoverLabel.append(inCoverLabel[:])
        except:
            import sys
            import traceback
            exc_type, exc_value, exc_traceback = sys.exc_info()
            self.errmsg = ''.join(traceback.extract_tb(exc_traceback).format()) + '{0}{1}'.format(exc_type, exc_value)
            self.error.emit()
            return

        self.populatedInfo.emit()

    def getChanInvert(self, i, axis):
        j = 0 if axis.lower() == 'x' else 1
        if self.pathsChan[i].any():
            return self.pathsChan[i][:,j]
        else:
            np.array([])

    def getGround(self, i, axis):
        j = 0 if axis.lower() == 'x' else 1
        if self.pathsGround[i].any():
            return self.pathsGround[i][:,j]
        else:
            return np.array([])

    def getWarning(self, i, axis, type_):
        j = 0 if axis.lower() == 'x' else 1
        if type_ == 'area':
            a = self.pathsPlotDecA
        elif type_ == 'invert':
            a = self.pathsPlotAdvI
        elif type_ == 'gradient':
            a = self.pathsPlotAdvG
        elif type_ == 'angle':
            a = self.pathsPlotSharpA
        elif type_ == 'cover':
            a = self.pathsPlotInCover
        else:
            a = np.array([])

        if a[i].any():
            return a[i][:,j]
        else:
            return np.array([])

    def hasWarning(self, i, type_):
        if type_ == 'area':
            return self.pathsPlotDecA[i].any()
        elif type_ == 'invert':
            return self.pathsPlotAdvI[i].any()
        elif type_ == 'gradient':
            return self.pathsPlotAdvG[i].any()
        elif type_ == 'angle':
            return self.pathsPlotSharpA[i].any()
        elif type_ == 'cover':
            return self.pathsPlotInCover[i].any()
        else:
            return False

    def _flag_xy(self, ch1, ch2, inv1, inv2, obv1, obv2, method, ch_=None):
        if method == 'halfway':
            x_ = (ch1 + ch2) / 2.
            y1 = np.interp(x_, [ch1, ch2], [inv1, inv2])
            y2 = np.interp(x_, [ch1, ch2], [obv1, obv2])
        elif method == 'chainage':
            x_ = ch_
            y1 = np.interp(x_, [ch1, ch2], [inv1, inv2])
            y2 = np.interp(x_, [ch1, ch2], [obv1, obv2])
        else:
            x_ = ch1
            y1 = inv1
            y2 = obv1

        if y2 == y1:
            y2 = y1 + 1

        return x_, y2 + (y2 - y1) * 1.1

    def _timeout(self):
        print('timeout')
        self.known_error = True
        self.errmsg = ('Timeout error: Long plot find branches took too long to complete. ')
        sys.setrecursionlimit(self.rd)
        raise Exception

    def _trace_upstream(self, start_chan, end_chan):
        # assume checking channels exist has already been done
        print('_trace_upstream')
        self.timeout_limit = float(QSettings().value('tuflow/flow_trace_timeout', 30))
        self.rd = sys.getrecursionlimit()
        sys.setrecursionlimit(int(QSettings().value('tuflow/flow_trace_recursion_limit', 25)))
        self.timer = datetime.now()
        found = self._find_branches(start_chan, end_chan, [], self.branches)
        if self.branches and self.branches[-1]:
            if found:
                self.branches = self.branches[-1:]
            elif end_chan is None:
                found = True
        else:
            found = False
        print('finished _trace_upstream')
        sys.setrecursionlimit(self.rd)
        return found

    def _find_branches(self, start_chan, end_chan, chan_ids, branches):
        found = False
        if start_chan:
            chan_ids.append(start_chan)
            i = 0
            for chan in self._iterate_upstream_channels(start_chan):
                if (datetime.now() - self.timer).total_seconds() > self.timeout_limit:
                    self._timeout()
                if chan in chan_ids:
                    branches.append(chan_ids)
                    return found
                if end_chan is not None and chan == end_chan:
                    chan_ids.append(chan)
                    branches.append(chan_ids)
                    return True

                i += 1
                try:
                    found = self._find_branches(chan, end_chan, chan_ids[:], branches)
                    if found:
                        return found
                except RecursionError:
                    branches.append(chan_ids)
                    return found

            if not i:
                branches.append(chan_ids)

        return found

    def _iterate_upstream_channels(self, channel_id):
        if channel_id in self.data_collector.connections:
            for upstream_channel in self.data_collector.connections[channel_id].linesUs:
                yield upstream_channel
