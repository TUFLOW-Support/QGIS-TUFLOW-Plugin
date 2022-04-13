import re
import os
import numpy as np
from TUFLOW_results import ResData, Timeseries, NodeInfo, ChanInfo
from TUFLOW_XS import XS, XS_Data


class FM_Node:
    """Flood Modeller node"""

    def __init__(self, id_, type_, x, y):
        self.x = x
        self.y = y
        self.id = id_
        self.sub_type = type_
        self.type = type_.split(' ')[0]


class FM_Link:
    """Flood Modeller link"""

    def __init__(self, index, us_node, ds_node):
        self.index = index
        self.us_node = us_node
        self.ds_node = ds_node
        self.x = [us_node.x, ds_node.x]
        self.y = [us_node.y, ds_node.y]


class FM_NodeInfo(NodeInfo):
    """Inherits from extry NodeInfo class"""

    def __init__(self, nodes, links):
        self.node_num = []
        self.node_name = []
        self.node_bed = []
        self.node_top = []
        self.node_nChan = []
        self.node_channels = []
        self.message = ''
        self.error = False

        # new
        self.nodes = nodes[:]

        if nodes is None:
            return

        link_ids = [x.index for x in links]
        link_upn = [x.us_node for x in links]
        link_dnn = [x.ds_node for x in links]

        for i, node in enumerate(nodes):
            self.node_num.append(i + 1)
            self.node_name.append(node.id)
            self.node_bed.append(-99999)
            self.node_top.append(-99999)
            self.node_nChan.append(link_upn.count(node.id) + link_dnn.count(node.id))
            m = 0
            for j in range(link_upn.count(node.id)):
                k = link_upn[m:].index(node.id) + m
                self.node_channels.append(links[k])
                m = k + 1
            m = 0
            for j in range(link_dnn.count(node.id)):
                k = link_dnn[m:].index(node.id) + m
                self.node_channels.append(links[k])
                m = k + 1

    def loadBedElevations(self, xs_data):
        """Sets node bed elevation from cross section data"""

        xs_ids = {x.source: x for x in xs_data.fm_xs}
        for i, nn in enumerate(self.node_name):
            if nn in xs_ids:
                self.node_bed[i] = min(xs_ids[nn].z)



class FM_ChanInfo(ChanInfo):

    def __init__(self, links):
        self.chan_num = []
        self.chan_name = []
        self.chan_US_Node = []
        self.chan_DS_Node = []
        self.chan_US_Chan = []
        self.chan_DS_Chan = []
        self.chan_Flags = []
        self.chan_Length = []
        self.chan_FormLoss = []
        self.chan_n = []
        self.chan_slope = []
        self.chan_US_Inv = []
        self.chan_DS_Inv = []
        self.chan_LBUS_Obv = []
        self.chan_RBUS_Obv = []
        self.chan_LBDS_Obv = []
        self.chan_RBDS_Obv = []
        self.chan_Blockage = []

        self.message = ''
        self.error = False

        if links is None:
            return

        link_ids = [x.index for x in links]
        link_upn = [x.us_node for x in links]
        link_dnn = [x.ds_node for x in links]


        for link in links:
            self.chan_num.append(int(link.index))
            self.chan_name.append(link.index)
            self.chan_US_Node.append(link.us_node.id)
            self.chan_DS_Node.append(link.ds_node.id)

            if link.us_node in link_dnn:
                i = link_dnn.index(link.us_node)
                self.chan_US_Chan.append(links[i].index)
            else:
                self.chan_US_Chan.append('------')
            if link.ds_node in link_upn:
                i = link_upn.index(link.ds_node)
                self.chan_DS_Chan.append(links[i].index)
            else:
                self.chan_DS_Chan.append('------')

            self.chan_Flags.append('S')
            if link.us_node.x != 0 and link.us_node.y != 0 and link.ds_node.x != 0 and link.ds_node.y != 0:
                self.chan_Length .append(((link.us_node.x - link.ds_node.x) ** 2 + (link.us_node.y - link.ds_node.y) ** 2) ** 0.5)
            else:
                self.chan_Length.append(0.)

            self.chan_FormLoss.append(0.)
            self.chan_n.append(0.)
            self.chan_slope.append(0.)
            self.chan_US_Inv.append(-99999)
            self.chan_DS_Inv.append(-99999)
            self.chan_LBUS_Obv.append(-99999)
            self.chan_RBUS_Obv.append(-99999)
            self.chan_LBDS_Obv.append(-99999)
            self.chan_RBDS_Obv.append(-99999)
            self.chan_Blockage.append(0.)

    def loadBedElevations(self, xs_data):
        """Sets channel invert elevation from cross section data"""

        xs_ids = {x.source: x for x in xs_data.fm_xs}
        for i, cn in enumerate(self.chan_US_Node):
            if cn in xs_ids:
                self.chan_US_Inv[i] = min(xs_ids[cn].z)
        for i, cn in enumerate(self.chan_DS_Node):
            if cn in xs_ids:
                self.chan_DS_Inv[i] = min(xs_ids[cn].z)


class FM_Timeseries(Timeseries):
    """Inherits from estry timeseries class"""

    def Load(self, fullpath, prefix, simID, fo):
        """
        Overrides Load function so can be tailored
        for Flood Modeller results.
        """

        error = False
        msg = ""

        self.nCol = 1
        self.ID.clear()
        self.uID.clear()
        self.null_data = -9999.99  # different than estry
        self.nVals = 0

        values = []
        for line in fo:
            if line == '\n':
                break
            elif 'time' in line.lower():
                self.Header = line.strip().split(',')
                self.Header.insert(0, 'Timestep')
                self.Header[1] = 'Time'
                self.nLocs = len(self.Header) - 1
                self.ID = self.Header[1:]
            else:
                self.nVals += 1
                values.append(line.strip().split(','))

        try:
            a = np.array(values, dtype=np.float64)
            timesteps = np.array([x+1 for x in range(self.nVals)])
            a = np.insert(a, 0, timesteps, axis=1)
            ma = np.ma.masked_equal(a, self.null_data)
            self.Values = ma
            self.loaded = True
        except Exception as e:
            error = True
            msg = str(e)

        return error, msg


class TuFloodModellerDataProvider(ResData):
    """Inherits from estry data provider class"""

    def __init__(self):
        ResData.__init__(self)

        # private
        self._gxy = None
        self._result_file = None
        self._resValid = False
        self._name2node = {}
        self._crossSectionsLoaded = False

        # public
        self.gxyname = None
        self.displayname = None
        self.nodes = []
        self.links = []
        self.connectionCount = 0
        self.isgxyValid = False
        self.isValid = False

        # override
        self.Data_1D.H = FM_Timeseries()
        self.Data_1D.Q = FM_Timeseries()
        self.Data_1D.V = FM_Timeseries()
        self.times = []

    def load_gxy(self, filepath):
        # courtesy of DK
        # Reads through FM GXY file and splits into Node Unit_ID, X, Y.
        errors = False
        msg = []
        self._gxy = filepath
        self.gxyname = os.path.splitext(os.path.basename(filepath))[0]
        node_list = []
        with open(filepath, 'r') as file:
            links = False
            finished = False
            for line in file:
                if finished:
                    break
                elif links:
                    if line == '\n':  # end of links
                        finished = True
                        continue
                    if 'ConnectionCount' in line:
                        self.connectionCount = int(line.split('=')[1].strip())
                        continue
                    index, nodes = line.strip().split('=')
                    us_node, ds_node = nodes.split(',')
                    if us_node not in self._name2node or ds_node not in self._name2node:
                        errors = True
                        msg.append('Link index: {0}'.format(index))
                        continue
                    us_node = self._name2node[us_node]
                    ds_node = self._name2node[ds_node]
                    link = FM_Link(index, us_node, ds_node)
                    self.links.append(link)
                else:  # node
                    if '[Connections]' in line:
                        links = True
                        continue
                    if re.findall(r'\[.*\]', line):
                        # Clean the various bits of data and split into Node Unit_ID, X, Y.
                        unit = line.strip('[]\n')  # remove the [ and ] from the string
                        try:
                            unit_type = ' '.join(unit.split('_', 2)[:2])
                            unit_id = unit.split('_', 2)[2]
                            # x
                            subline = file.readline()
                            x = float(subline.split('X=')[1].strip())
                            # y
                            subline = file.readline()
                            y = float(subline.split('Y=')[1].strip())

                            node = FM_Node(unit_id, unit_type, x, y)
                            node_list.append(node)
                            self._name2node[unit] = node
                        except:
                            errors = True
                            msg.append('Node: {0}'.format(unit))
                            continue

        self.nodes = FM_NodeInfo(node_list, self.links)
        self.Channels = FM_ChanInfo(self.links)

        if self.nodes and self.links:  # at least some nodes and links have been read in
            self.isgxyValid = True

        return errors, msg

    def Load(self, fname):
        """
        Overrides Load function so can be tailored
        for Flood Modeller results.
        """

        error = False
        message = []
        self.displayname = os.path.splitext(os.path.basename(fname))[0]  # initially set to filename
        valid_restypes = ['stage', 'flow', 'velocity']

        self.formatVersion = 2
        self.units = 'METRIC'  # not sure if this can change or if it's reflected in the output

        with open(fname, 'r') as fo:
            for line in fo:
                if 'output data from file' in line.lower():
                   self.displayname = os.path.splitext(os.path.basename(line.strip()))[0]
                if line.strip().lower() in valid_restypes:
                    if line.strip().lower() == 'stage':
                        err, msg = self.Data_1D.H.Load(fname, None, None, fo)
                        if err:
                            error = True
                            message.append(msg)
                        else:
                            self.Types.append('1D Water Levels')
                            self.times = self.Data_1D.H.Values[:,1]
                    elif line.strip().lower() == 'flow':
                        err, msg = self.Data_1D.Q.Load(fname, None, None, fo)
                        if err:
                            error = True
                            message.append(msg)
                        else:
                            self.Types.append('1D Flows')
                            self.times = self.Data_1D.Q.Values[:, 1]
                    elif line.strip().lower() == 'velocity':
                        err, msg = self.Data_1D.V.Load(fname, None, None, fo)
                        if err:
                            error = True
                            message.append(msg)
                        else:
                            self.Types.append('1D Velocities')
                            self.times = self.Data_1D.V.Values[:, 1]

        return error, message

    def loadBedElevations(self, xs_data):
        self.nodes.loadBedElevations(xs_data)
        self.Channels.loadBedElevations(xs_data)

        # interpolate values
        for i, nn in enumerate(self.nodes.node_name):
            if self.nodes.nodes[i].type.upper() == 'INTERPOLATE' and self.nodes.node_bed[i] == -99999:

                # find upstream elevation
                usz = -99999
                usLen = 0
                nn2 = nn
                while (1):
                    found = False
                    interp = False
                    ii = -1
                    ip = -1
                    m = 0
                    # look for river section
                    for j in range(self.Channels.chan_DS_Node.count(nn2)):
                        k = self.Channels.chan_DS_Node[m:].index(nn2) + m
                        jj = self.nodes.node_name.index(self.Channels.chan_US_Node[k])
                        if self.nodes.nodes[jj].type == 'RIVER':
                            found = True
                            usLen += self.Channels.chan_Length[k]
                            ii = jj
                            break
                        elif self.nodes.nodes[jj].type == 'INTERPOLATE':
                            interp = True
                            ipLen = self.Channels.chan_Length[k]
                            ip = jj
                        m = k + 1
                    if not found and interp:
                        nn2 = self.nodes.nodes[jj].id
                        usLen += ipLen
                        continue
                    break
                if ii == -1:
                    continue
                else:
                    usz = self.nodes.node_bed[ii]

                # find downstream elevation
                dsz = -99999
                dsLen = 0
                nn2 = nn
                while (1):
                    found = False
                    interp = False
                    ii = -1
                    ip = -1
                    m = 0
                    # look for river section
                    for j in range(self.Channels.chan_US_Node.count(nn2)):
                        k = self.Channels.chan_US_Node[m:].index(nn2) + m
                        jj = self.nodes.node_name.index(self.Channels.chan_DS_Node[k])
                        if self.nodes.nodes[jj].type == 'RIVER':
                            found = True
                            dsLen += self.Channels.chan_Length[k]
                            ii = jj
                            break
                        elif self.nodes.nodes[jj].type == 'INTERPOLATE':
                            interp = True
                            ipLen = self.Channels.chan_Length[k]
                            ip = jj
                        m = k + 1
                    if not found and interp:
                        nn2 = self.nodes.nodes[jj].id
                        dsLen += ipLen
                        continue
                    break
                if ii == -1:
                    continue
                else:
                    dsz = self.nodes.node_bed[ii]

                # interpoalate bed_level
                if usz != -99999 and dsz != -99999:
                    zr = float(dsz) - float(usz)
                    lr = float(usLen) + float(dsLen)
                    self.nodes.node_bed[i] = usz + zr / lr * usLen

                    kk = self.Channels.chan_US_Node.index(nn)
                    self.Channels.chan_US_Inv[kk] = self.nodes.node_bed[i]
                    kk = self.Channels.chan_DS_Node.index(nn)
                    self.Channels.chan_DS_Inv[kk] = self.nodes.node_bed[i]

        self._crossSectionsLoaded = True

    def pointResultTypesTS(self):
        """
        Overrides exisitng function -
        Flood Modeller stores all results on node (point)
        """

        types = []

        for type_ in self.Types:
            if 'WATER LEVEL' in type_.upper():
                types.append('level')
            elif 'FLOW' in type_.upper():
                types.append('flow')
            elif 'VELOCITIES' in type_.upper():
                types.append('velocity')

        return types

    def lineResultTypesTS(self):
        """
        Overrides exisitng function -
        Flood Modeller stores all results on node (point) so no results on line
        """

        types = []

        return types

    def regionResultTypesTS(self):
        """
        Overrides exisitng function -
        Flood Modeller doesn't have any region types
        """

        types = []

        return types

    def lineResultTypesLP(self):
        """
        Overrides exisitng function -
        Long profile not yet supported for Flood Modeller results
        """

        types = []

        for type_ in self.Types:
            if 'WATER LEVEL' in type_.upper():
                types.append('Water Level')
        if self._crossSectionsLoaded:
            types.append('Bed Level')

        return types

    @staticmethod
    def getSimulationName(fname):
        """
        Static method that returns the simulation name - either from header information
        whithin the file, or from the file name if there is no header.
        """

        simname = os.path.splitext(os.path.basename(fname))[0]
        valid_restypes = ['stage', 'flow', 'velocity']

        with open(fname, 'r') as fo:
            for line in fo:
                if 'output data from file' in line.lower():
                   simname = os.path.splitext(os.path.basename(line.strip()))[0]
                   break
                elif line.strip().lower() in valid_restypes:
                    break

        return simname

    def LP_getConnectivity(self, id1, id2, *args, **kwargs):
        """Populate list of connected channels"""

        self.LP.chan_ids.clear()
        self.LP.chan_index.clear()
        self.LP.node_list.clear()

        err = False
        msg = ""

        if not args:
            return

        selected_ids = [x for x in args]
        link_ids = [x.index for x in self.links]
        link_upn = [x.us_node for x in self.links]
        link_dnn = [x.ds_node for x in self.links]

        # assume first selection must be plotted and work up and down through selection
        if selected_ids[0] not in link_ids:
            return err, msg
        i = link_ids.index(selected_ids[0])
        self.LP.chan_ids.append(selected_ids[0])
        self.LP.chan_index.append(i)
        self.LP.node_list.append(self.links[i].us_node.id)
        self.LP.node_list.append(self.links[i].ds_node.id)

        # work upstream until no longer in selection
        while (1):
            found = False
            if self.links[i].us_node in link_dnn:
                count = link_dnn.count(self.links[i].us_node)
                m = 0
                for j in range(count):
                    k = link_dnn[m:].index(self.links[i].us_node) + m
                    m = k + 1
                    if self.links[k].index in selected_ids:
                        if self.links[k].index not in self.LP.chan_ids:
                            self.LP.chan_ids.insert(0, self.links[k].index)
                            self.LP.chan_index.insert(0, k)
                            self.LP.node_list.insert(0, self.links[k].us_node.id)
                            found = True
                            i = k
                            break
            if not found:
                if self.links[i].us_node.type.lower() == 'spill':  # can go the other way with spills
                    count = link_dnn.count(self.links[i].ds_node)
                    m = 0
                    for j in range(count):
                        k = link_dnn[m:].index(self.links[i].ds_node) + m
                        m = k + 1
                        if self.links[k].index in selected_ids:
                            if self.links[k].index not in self.LP.chan_ids:
                                self.LP.chan_ids.insert(0, self.links[k].index)
                                self.LP.chan_index.insert(0, k)
                                self.LP.node_list.insert(0, self.links[k].us_node.id)
                                found = True
                                i = k
                                break
                if self.links[i].us_node in link_upn:
                    count = link_upn.count(self.links[i].us_node)
                    m = 0
                    for j in range(count):
                        k = link_upn[m:].index(self.links[i].us_node) + m
                        m = k + 1
                        if self.links[k].us_node.type.lower() == 'spill':
                            if self.links[k].index in selected_ids:
                                if self.links[k].index not in self.LP.chan_ids:
                                    self.LP.chan_ids.insert(0, self.links[k].index)
                                    self.LP.chan_index.insert(0, k)
                                    self.LP.node_list.insert(0, self.links[k].us_node.id)
                                    found = True
                                    i = k
                                    break
                if not found:
                    break

        # work downstream until no longer in selection
        i = link_ids.index(selected_ids[0])
        while (1):
            found = False
            if self.links[i].ds_node in link_upn:
                count = link_upn.count(self.links[i].ds_node)
                m = 0
                for j in range(count):
                    k = link_upn[m:].index(self.links[i].ds_node) + m
                    m = k + 1
                    if self.links[k].index in selected_ids:
                        if self.links[k].index not in self.LP.chan_ids:
                            self.LP.chan_ids.append(self.links[k].index)
                            self.LP.chan_index.append(k)
                            self.LP.node_list.append(self.links[k].ds_node.id)
                            found = True
                            i = k
                            break
            if not found:
                if self.links[i].us_node.type.lower() == 'spill':  # can go the other way with spills
                    count = link_upn.count(self.links[i].us_node)
                    m = 0
                    for j in range(count):
                        k = link_upn[m:].index(self.links[i].us_node) + m
                        m = k + 1
                        if self.links[k].index in selected_ids:
                            if self.links[k].index not in self.LP.chan_ids:
                                self.LP.chan_ids.append(self.links[k].index)
                                self.LP.chan_index.append(k)
                                self.LP.node_list.append(self.links[k].ds_node.id)
                                found = True
                                i = k
                                break
                if self.links[i].ds_node in link_dnn:
                    count = link_dnn.count(self.links[i].ds_node)
                    m = 0
                    for j in range(count):
                        k = link_dnn[m:].index(self.links[i].ds_node) + m
                        m = k + 1
                        if self.links[k].us_node.type.lower() == 'spill':
                            if self.links[k].index in selected_ids:
                                if self.links[k].index not in self.LP.chan_ids:
                                    self.LP.chan_ids.append(self.links[k].index)
                                    self.LP.chan_index.append(k)
                                    self.LP.node_list.append(self.links[k].ds_node.id)
                                    found = True
                                    i = k
                                    break
                if not found:
                    break

        return err, msg

    def LP_getStaticData(self):
        # get the channel and node properties length, elevations etc doesn't change with results

        error = False
        message = None
        if (len(self.LP.chan_index) < 1):
            error = True
            message = 'No LP channel data exists - Use .getLP_Connectivity to generate'
            return error, message

        # node info
        self.LP.node_bed = []
        self.LP.node_top = []
        self.LP.H_nd_index = []
        self.LP.node_index = []
        self.LP.Hmax = []
        self.LP.Emax = []
        self.LP.tHmax = []
        # long profile adverse grades
        self.LP.adverseH.nLocs = 0
        self.LP.adverseH.chainage = []
        self.LP.adverseH.node = []
        self.LP.adverseH.elevation = []
        self.LP.adverseE.nLocs = 0
        self.LP.adverseE.chainage = []
        self.LP.adverseE.node = []
        self.LP.adverseE.elevation = []

        # channel info
        self.LP.dist_nodes = [0.0]  # nodes only
        self.LP.dist_chan_inverts = [0.0]  # at each channel end (no nodes)
        self.LP.dist_chan_inverts = []  # at each channel end (no nodes)
        self.LP.dist_inverts = [0.0]  # nodes and channel ends
        self.LP.chan_inv = []
        self.LP.chan_LB = []
        self.LP.chan_RB = []
        self.LP.culv_verts = []

        for i, chan_index in enumerate(self.LP.chan_index):
            # length of current channel
            chan_len = self.Channels.chan_Length[chan_index]  # length of current channel

            # distance at nodes
            cur_len = self.LP.dist_nodes[len(self.LP.dist_nodes) - 1]  # current length at node
            self.LP.dist_nodes.append(cur_len + chan_len)

            # distance at inverts
            if len(self.LP.dist_chan_inverts) == 0:
                cur_len = 0.
            else:
                cur_len = self.LP.dist_chan_inverts[
                    len(self.LP.dist_chan_inverts) - 1]  # current length at invert locations
            self.LP.dist_chan_inverts.append(cur_len + 0.0001)  # dist for upstream invert
            new_len = cur_len + chan_len
            self.LP.dist_chan_inverts.append(new_len - 0.0001)  # dist for downstream invert

            # distance at both inverts and nodes
            cur_len = self.LP.dist_inverts[len(self.LP.dist_inverts) - 1]  # current length at invert locations
            self.LP.dist_inverts.append(cur_len + 0.0001)  # dist for upstream invert
            new_len = cur_len + self.Channels.chan_Length[chan_index]
            self.LP.dist_inverts.append(new_len - 0.0001)  # dist for downstream invert
            self.LP.dist_inverts.append(new_len)  # dist at next node

            # elevations at channel inverts, left and right obverts
            self.LP.chan_inv.append(self.Channels.chan_US_Inv[chan_index])
            self.LP.chan_LB.append(self.Channels.chan_LBUS_Obv[chan_index])
            self.LP.chan_RB.append(self.Channels.chan_RBUS_Obv[chan_index])
            self.LP.chan_inv.append(self.Channels.chan_DS_Inv[chan_index])
            self.LP.chan_LB.append(self.Channels.chan_LBDS_Obv[chan_index])
            self.LP.chan_RB.append(self.Channels.chan_RBDS_Obv[chan_index])

            # distance polygons for culverts
            x = []
            y = []
            c_type = self.Channels.chan_Flags[chan_index]
            if c_type == "R" or c_type == "C" or c_type == "I":
                x.append(self.LP.dist_chan_inverts[-2])
                x.append(self.LP.dist_chan_inverts[-1])
                x.append(self.LP.dist_chan_inverts[-1])
                x.append(self.LP.dist_chan_inverts[-2])
                y.append(self.LP.chan_inv[-2])
                y.append(self.LP.chan_inv[-1])
                y.append(self.LP.chan_LB[-1])
                y.append(self.LP.chan_LB[-2])
                verts = list(zip(x, y))
                self.LP.culv_verts.append(verts)
            else:
                self.LP.culv_verts.append(None)

        for i, nd in enumerate(self.LP.node_list):
            try:  # get node index and elevations
                ind = self.nodes.node_name.index(nd)
                self.LP.node_index.append(ind)
                self.LP.node_bed.append(self.nodes.node_bed[ind])
                self.LP.node_top.append(self.nodes.node_top[ind])
            except:
                error = True
                message = 'Unable to find node in _Nodes.csv file. Node: ' + nd
                return error, message
            try:  # get index to data in 1d_H.csv used when getting temporal data
                ind = self.Data_1D.H.Header.index(nd)
                self.LP.H_nd_index.append(ind)
            except:
                error = True
                message = 'Unable to find node in _1d_H.csv for node: ' + nd
                return error, message

        self.LP.Hmax = None
        self.LP.Emax = None
        self.LP.tHmax = None

        # adverse gradient stuff
        try:
            if self.LP.Hmax:  # none type if no values
                for i in range(1, len(self.LP.node_list)):
                    dh = self.LP.Hmax[i] - self.LP.Hmax[i - 1]
                    if dh > 0:
                        self.LP.adverseH.nLocs = self.LP.adverseH.nLocs + 1
                        self.LP.adverseH.elevation.append(self.LP.Hmax[i])
                        self.LP.adverseH.node.append(self.LP.node_list[i])
                        self.LP.adverseH.chainage.append(self.LP.dist_nodes[i])
        except:
            error = True
            message = 'ERROR processing adverse gradients from LP'
            return error, message
        try:
            if self.LP.Emax:  # none type if no values
                for i in range(1, len(self.LP.node_list)):
                    dh = self.LP.Emax[i] - self.LP.Emax[i - 1]
                    if dh > 0:
                        self.LP.adverseE.nLocs = self.LP.adverseE.nLocs + 1
                        self.LP.adverseE.elevation.append(self.LP.Emax[i])
                        self.LP.adverseE.node.append(self.LP.node_list[i])
                        self.LP.adverseE.chainage.append(self.LP.dist_nodes[i])
        except:
            error = True
            message = 'ERROR processing adverse gradients from LP'
            return error, message

        self.LP.chan_inv = np.ma.array(self.LP.chan_inv)
        self.LP.chan_inv = np.ma.masked_equal(self.LP.chan_inv, -99999)

        # normal return
        self.LP.static = True
        return error, message

    # def LP_getData(self, dat_type, time, dt_tol):
    #     pass


class FM_XS_Data(XS_Data):

    def __init__(self):
        self.source = None
        self.feature = None
        self.flags = ""
        self.col1 = ""
        self.col2 = ""
        self.col3 = ""
        self.col4 = ""
        self.col5 = ""
        self.col6 = ""
        self.loaded = False
        self.fullpath = None
        self.mat = []
        self.has_mat = False
        self.mat_type = None
        self.area = []
        self.has_area = False
        self.perim = []
        self.has_perim = False

        # error initialisation
        self.error = False
        self.message = None

        self.type = 'XZ'
        self.x = []
        self.z = []
        self.np = []
        self.FM_n = []

        self.FM_section = None
        self.FM_xloc = []  # spatial x-coord
        self.FM_yloc = []  # spatial y=coord

        self.FM_layername = None

        self.FM_filtered_points = []
        self.FM_nFiltered_points = 0

    def load(self, section, label, x, z, n, xcoord, ycoord, filtered_points, layername, error, message):
        self.source = label
        self.FM_section = section
        self.x = x
        self.z = z
        self.FM_n = n
        self.FM_xloc = xcoord
        self.FM_yloc = ycoord
        self.FM_nxypnts = len(xcoord)

        self.np = len(x)

        self.FM_filtered_points = filtered_points
        self.FM_nFiltered_points = len(filtered_points)

        self.FM_layername = layername

        self.error = error
        self.message = message


class FM_XS(XS):

    def __init__(self):
        XS.__init__(self)
        self.fm_dat = None
        self.fm_xs = []
        self.fm_nXs = 0
        self.layer_name = []

    def fmLoadDat(self, fpath):
        """Load cross section data from FM dat file"""

        layername = '1d_xz_{0}'.format(os.path.basename(os.path.splitext(fpath)[0]))
        error = False
        msg = []
        self.fm_dat = fpath
        with open(fpath, 'r') as fo:
            startRiver = False
            i = 1
            for line in fo:
                i += 1
                if re.findall(r'^(END GENERAL)', line):
                    startRiver = True
                elif re.findall(r'^(GISINFO)', line):
                    startRiver = False

                if re.findall(r'^(COMMENT)', line):
                    subline = fo.readline()
                    nCommentLines = int(subline.strip())
                    for j in range(nCommentLines):
                        fo.readline()

                if startRiver:
                    if re.findall(r'^(RIVER)', line):
                        self.fm_nXs += 1
                        data = FM_XS_Data()
                        section = fo.readline().strip()  # SECTION line
                        i += 1
                        label = fo.readline().split(' ')[0].strip()  # label line
                        if len(label) > 12:
                            label = label[:12]  # fixed field format
                        i += 1
                        chainage = fo.readline().strip()  # chainage line
                        i += 1
                        try:
                            subline = fo.readline()
                            i += 1
                            np = int(subline.strip())
                        except Exception as e:
                            error = True
                            msg.append('Error reading number of points for section: {0} on line {1}'.format(label, i))
                            continue
                        xall = []
                        yall = []
                        nall = []
                        xcoordall = []
                        ycoordall = []
                        filtered_points = []
                        error2 = False
                        message = ""
                        for i in range(np):
                            subline = fo.readline().strip()
                            i += 1
                            a = [x for x in subline.split(' ') if x]
                            b = [x.strip('LEFTRIGHTBED*\n') for x in a]
                            try:
                                x, y = b[:2]
                                x = float(x)
                                y = float(y)
                                xall.append(x)
                                yall.append(y)
                            except Exception as e:
                                error = True
                                error2 = True
                                message = 'Error reading in section XZ data: {0} on line {1}'.format(label, i)
                                msg.append(message)
                                break
                            try:
                                n = b[2]
                                nall.append(n)
                            except:
                                pass
                            try:
                                xcoord, ycoord = b[4:6]
                                xcoord = float(xcoord)
                                ycoord = float(ycoord)
                                if xcoord == 0 or ycoord == 0:
                                    filtered_points.append(i)
                                else:
                                    xcoordall.append(xcoord)
                                    ycoordall.append(ycoord)
                            except:
                                error = True
                                error2 = True
                                message = 'Error reading in section coordinate data: {0} on line {1}'.format(label, i)
                                msg.append(message)
                                break

                        if error2:
                            x, y = [], []
                            nall = []
                            xcoordall = []
                            ycoordall = []
                        if len(nall) != len(xall):
                            nall = []
                        # if len(xcoordall) != len(xall) or len(ycoordall) != len(xall):
                        #     xcoordall = []
                        #     ycoordall = []
                        data.load(section, label, xall, yall, nall, xcoordall, ycoordall, filtered_points, layername, error2, message)
                        self.fm_xs.append(data)

        return error, msg

    def add(self, fpath, fname, xs_type, flags, col1, col2, col3, col4, col5, col6):
        pass

    def addFromFeature(self, fpath, fields, feature, lyr):
        error = False
        message = None

        # get field info
        if len(fields) < 9:
            error = True
            message = 'ERROR - Expecting at least 9 fields in 1d_xs layer'
            return error, message
        try:
            f1 = str(fields.field(0).name())  # source
            f2 = str(fields.field(1).name())  # type
            f3 = str(fields.field(2).name())  # flags
            f4 = str(fields.field(3).name())  # column_1
            f5 = str(fields.field(4).name())  # column_2
            f6 = str(fields.field(5).name())  # column_3
            f7 = str(fields.field(6).name())  # column_4
            f8 = str(fields.field(7).name())  # column_5
            f9 = str(fields.field(8).name())  # column_6
        except:
            error = True
            message = 'ERROR - Unable to extract field names'
            return error, message

        source = feature[f1]
        xs_type = feature[f2].upper()
        fm_xs_names = [x.source for x in self.fm_xs]
        if source not in fm_xs_names:
            error = True
            message = 'ERROR - Could not find XS in {0}'.format(self.fm_dat)
            return error, message

        i = fm_xs_names.index(source)
        xs = self.fm_xs[i]
        if xs.error:
            return xs.error, xs.message

        self.nXS += 1
        self.source.append(source)
        self.data.append(xs)

        if self.all_types.count(xs.type) < 1:
            self.all_types.append(xs.type)

        # normal termination
        self.lyr = lyr
        return error, message

    def delByLayername(self, layername):
        for i, xs in enumerate(self.fm_xs[:]):
            if xs.FM_layername == layername:
                self.fm_xs.remove(xs)

