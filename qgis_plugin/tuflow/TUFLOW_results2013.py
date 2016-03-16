import os
import numpy
import csv
import sys
version = '2015-05-AA'

class LP():
    def __init__(self): #initialise the LP data
        self.chan_list = [] #list of channel IDs
        self.chan_index = []  # list of index values in the ChanInfo class
        self.node_list = []
        self.node_index = []
        self.node_bed = []
        self.node_top = []
        self.H_nd_index = []
        self.dist_nodes = []
        self.dist_chan_inverts = []
        self.dist_inverts= []
        self.Hmax = []
        self.Hdata = []
        self.chan_inv = []
        self.chan_LB = []
        self.chan_RB = []
        self.pit_dist = []
        self.pit_z = []
        self.npits = int(0)
        self.connected = False
        self.static = False

class Data_1D():
    def __init__(self): #initialise the 1D data
        self.nNode = 0
        self.nChan = 0
        self.H = None
        self.V = None
        self.Q = None

    def find_data(self,ID, domain, geom, dat_type):
        # see if the data exists in the file
        try:
            indA = []
            indB = []
            indC = []
            indD = []
            for i, id in enumerate(self.ID): # have to enumerate rather than index as index only returns a single entry there could be the same ID in 1D and 2D
                if id == ID:
                    indA.append(i)
            if len(indA)>0: #ID found - check that 1D/2D is correct
                for ind in indA:
                    if self.domain[ind]==domain:
                        indB.append(ind)
            if len(indB)>0: #id and domain match
                for ind in indB:
                    if self.geom[ind]==geom:
                        indC.append(ind)
            if len(indC)>0: #id, domain and geom match
                for ind in indC:
                    if (self.dat_type[ind].find(dat_type)>=0):
                        indD.append(ind)
            if len(indD)==1:
                #data found
                return True, indD
            elif len(indD)>1:
                print 'WARNING - More than 1 matching dataset - using 1st occurence.'
                return True, indD[0]
            else:
                return False, 0
        except:
            print 'WARNING - Unknown exception finding data in res.find_data().'
            return False, -99 #error shouldn't really be here

class Timeseries():
    """
    Timeseries - used for both 1D and 2D data
    """
    def __init__(self,fullpath,prefix, simID):
        try:
            with open(fullpath, 'rb') as csvfile:
                reader = csv.reader(csvfile, delimiter=',', quotechar='"')
                header = reader.next()
            csvfile.close()
        except:
            print "ERROR - Error reading header from: "+fullpath
        header[0]='Timestep'
        header[1]='Time'
        self.ID = []
        i=1
        for col in header[2:]:
            i= i+1
            a = col[len(prefix)+1:]
            indA = a.find(simID)
            indB = a.rfind('[') #find last occurrence of [
            if (indA >= 0) and (indB >= 0): # strip simulation ID from header
                a = a[0:indB-1]
            self.ID.append(a)
            header [i] = a
        self.Header = header
        try:
            self.Values = numpy.genfromtxt(fullpath, delimiter=",", skip_header=1)
        except:
            print "ERROR - Error reading data from: "+fullpath

        self.nVals = len(self.Values[:,2])
        self.nLocs = len(self.Header)-2
class NodeInfo():
    """
    Node Info data class
    """
    def __init__(self,fullpath):
        self.node_num = []
        self.node_name = []
        self.node_bed = []
        self.node_top = []
        self.node_nChan = []
        self.node_channels = []
        with open(fullpath, 'rb') as csvfile:
            reader = csv.reader(csvfile, delimiter=',', quotechar='"')
            header = reader.next()
            for (counter, row) in enumerate(reader):
                self.node_num.append(int(row[0]))
                self.node_name.append(row[1])
                self.node_bed.append(float(row[2]))
                self.node_top.append(float(row[3]))
                self.node_nChan.append(int(row[4]))
                chan_list = row[5:]
                if len(chan_list) != int(row[4]):
                    if int(row[4]) != 0:
                        print "ERROR - Number of channels connected to ID doesn't match. ID: " + str(row[1])
                else:
                    self.node_channels.append(chan_list)
        csvfile.close()

class ChanInfo():
    """
    Channel Info data class
    """
    def __init__(self,fullpath):
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

        with open(fullpath, 'rb') as csvfile:
            reader = csv.reader(csvfile, delimiter=',', quotechar='"')
            header = reader.next()
            for (counter, row) in enumerate(reader):
                self.chan_num.append(int(row[0]))
                self.chan_name.append(row[1])
                self.chan_US_Node.append(row[2])
                self.chan_DS_Node.append(row[3])
                self.chan_US_Chan.append(row[4])
                self.chan_DS_Chan.append(row[5])
                self.chan_Flags.append(row[6])
                self.chan_Length.append(float(row[7]))
                self.chan_FormLoss.append(float(row[8]))
                self.chan_n.append(float(row[9]))
                self.chan_slope.append(float(row[10]))
                self.chan_US_Inv.append(float(row[11]))
                self.chan_DS_Inv.append(float(row[12]))
                self.chan_LBUS_Obv.append(float(row[13]))
                self.chan_RBUS_Obv.append(float(row[14]))
                self.chan_LBDS_Obv.append(float(row[15]))
                self.chan_RBDS_Obv.append(float(row[16]))
                self.chan_Blockage.append(float(row[17]))
        self.nChan = counter+1
        csvfile.close()

# results class
class ResData():
    """
    ResData class for reading and processing results
    """

    def getTSData(self, id,res):
        message = None
        if(res.upper() in ("H", "H_", "LEVEL","LEVELS")):
            try:
                ind = self.Data_1D.H.Header.index(id)
                data = self.Data_1D.H.Values[:,ind]
                return True, data, message
            except:
                message = 'Data not found for 1D H with ID: '+id
                return False, [0.0], message
        elif(res.upper() in ("Q","Q_","FLOW","FLOWS")):
            try:
                ind = self.Data_1D.Q.Header.index(id)
                data = self.Data_1D.Q.Values[:,ind]
                return True, data, message
            except:
                message = 'Data not found for 1D Q with ID: '+id
                return False, [0.0], message
        elif(res.upper() in ("V","V_","VELOCITY","VELOCITIES")):
            try:
                ind = self.Data_1D.V.Header.index(id)
                data = self.Data_1D.V.Values[:,ind]
                return True, data, message
            except:
                message = 'Data not found for 1D V with ID: '+id
                return False, [0.0], message
        elif(res.upper() in ("US_H", "US LEVELS")):
            chan_list = tuple(self.Channels.chan_name)
            ind = chan_list.index(str(id))
            a = str(self.Channels.chan_US_Node[ind])
            try:
                ind = self.Data_1D.H.Header.index(a)
            except:
                message = 'Unable to find US node: ',+a+' for channel '+ id
                return False, [0.0], message
            try:
                data = self.Data_1D.H.Values[:,ind]
                return True, data, message
            except:
                message = 'Data not found for 1D H with ID: '+a
                return False, [0.0], message
        elif(res.upper() in ("DS_H","DS LEVELS")):
            chan_list = tuple(self.Channels.chan_name)
            ind = chan_list.index(str(id))
            a = str(self.Channels.chan_DS_Node[ind])
            try:
                ind = self.Data_1D.H.Header.index(a)
            except:
                message = 'Unable to find DS node: ',+a+' for channel '+ id
                return False, [0.0], message
            try:
                data = self.Data_1D.H.Values[:,ind]
                return True, data, message
            except:
                message = 'Data not found for 1D H with ID: '+a
                return False, [0.0], message
        else:
            message = 'Warning - Expecting unexpected data type for 1D: '+res
            return False, [0.0], message

    def LP_getConnectivity(self,id1,id2):
        print 'determining LP connectivity'
        message = None
        error = False
        self.LP.chan_list = []
        if (id2 == None): # only one channel selected
            finished = False
            i = 0
            chan_list = tuple(self.Channels.chan_name)
            try:
                ind1 = chan_list.index(str(id1))
            except:
                #QMessageBox.information(iface.mainWindow(),"ERROR", ("ID not found: " + str(id1)))
                print 'ERROR - ID not found: ' + str(id1)
                message = 'ERROR - ID not found: ' + str(id1)
                error = True
                return error, message
            self.LP.chan_list = [id1]
            self.LP.chan_index = [ind1]
            self.LP.node_list = [(self.Channels.chan_US_Node[ind1])]
            self.LP.node_list.append(self.Channels.chan_DS_Node[ind1])
            id = ind1
            while not finished:
                i = i + 1
                chan = self.Channels.chan_DS_Chan[id]
                if(chan=='------'):
                    finished = True
                else:
                    self.LP.chan_list.append(chan)
                    try:
                        id = self.Channels.chan_name.index(chan)
                        self.LP.chan_index.append(id)
                        self.LP.node_list.append(self.Channels.chan_DS_Node[id])
                    except:
                        error = True
                        message = 'ERROR - Unable to process channel: '+chan
                        return error, message
            if not error:
                self.LP.connected = True
            return error, message

        else: # two channels selected (check for more than two in main routine)
            finished = False
            found = False
            i = 0
            chan_list = tuple(self.Channels.chan_name)
            # check 1st ID exists
            try:
                ind1 = chan_list.index(str(id1))
            except:
                error = True
                message = 'ERROR - ID not found: '+str(id1)
                return error, message
            # check 2nd ID exists
            try:
                ind2 = chan_list.index(str(id2))
            except:
                #QMessageBox.information(iface.mainWindow(),"ERROR", ("ID not found: " + str(id2)))
                error = True
                message = 'ERROR - ID not found: '+str(id2)
                return error, message
            # assume ID2 is downstream of ID1
            endchan = id2
            self.LP.chan_list = [id1]
            self.LP.chan_index = [ind1]
            self.LP.node_list = [(self.Channels.chan_US_Node[ind1])]
            self.LP.node_list.append(self.Channels.chan_DS_Node[ind1])
            id = ind1
            while not finished:
                i = i + 1
                chan = self.Channels.chan_DS_Chan[id]
                if(chan=='------'):
                    finished = True
                elif(chan==endchan):
                    found = True
                    finished = True
                    self.LP.chan_list.append(chan)
                    try:
                        id = self.Channels.chan_name.index(chan)
                        self.LP.chan_index.append(id)
                        self.LP.node_list.append(self.Channels.chan_DS_Node[id])
                    except:
                        error = True
                        message = 'ERROR - Unable to process channel: '+chan
                        return error, message
                else:
                    self.LP.chan_list.append(chan)
                    try:
                        id = self.Channels.chan_name.index(chan)
                        self.LP.chan_index.append(id)
                        self.LP.node_list.append(self.Channels.chan_DS_Node[id])
                    except:
                        error = True
                        message = 'ERROR - ID not found: '+str(id)
                        return error, message

            if not (found): # id2 is not downstream of 1d1, reverse direction and try again...
                #QMessageBox.information(iface.mainWindow(), "DEBUG", "reverse direction and try again")
                finished = False
                found = False
                i = 0
                endchan = id1
                self.LP.chan_list = [id2]
                self.LP.chan_index = [ind2]
                self.LP.node_list = [(self.Channels.chan_US_Node[ind2])]
                self.LP.node_list.append(self.Channels.chan_DS_Node[ind2])
                id = ind2
                while not finished:
                    i = i + 1
                    chan = self.Channels.chan_DS_Chan[id]
                    if(chan=='------'):
                        finished = True
                    elif(chan==endchan):
                        found = True
                        finished = True
                        self.LP.chan_list.append(chan)
                        try:
                            id = self.Channels.chan_name.index(chan)
                            self.LP.chan_index.append(id)
                            self.LP.node_list.append(self.Channels.chan_DS_Node[id])
                        except:
                            error = True
                            message = 'ERROR - Unable to process channel: '+chan
                            return error, message
                    else:
                        self.LP.chan_list.append(chan)
                        try:
                            id = self.Channels.chan_name.index(chan)
                            self.LP.chan_index.append(id)
                            self.LP.node_list.append(self.Channels.chan_DS_Node[id])
                        except:
                            error = True
                            message = 'ERROR - Unable to process channel: '+chan
                            return error, message
            if not (found): # id1 and 1d2 are not connected
                error = True
                message = 'Channels ' +id1 + ' and '+id2+' are not connected'
                return error, message
            else:
                if not error:
                    self.LP.connected = True
            return error, message

    def LP_getStaticData(self):
        # get the channel and node properties lenghts, elevations etc doesn't change with results
        print 'Getting static data for LP'
        error = False
        message = None
        if (len(self.LP.chan_index)<1):
            error = True
            message = 'No LP channel data exists - Use .getLP_Connectivity to generate'
            return error, message

        # node info
        self.LP.node_bed = []
        self.LP.node_top = []
        self.LP.H_nd_index = []
        self.LP.node_index = []
        self.LP.Hmax = []
        for nd in self.LP.node_list:
            try: #get node index and elevations
                ind = self.nodes.node_name.index(nd)
                self.LP.node_index.append(ind)
                self.LP.node_bed.append(self.nodes.node_bed[ind])
                self.LP.node_top.append(self.nodes.node_top[ind])
            except:
                error = True
                message = 'Unable to find node in _Nodes.csv file. Node: '+nd
                return error, message
            try: #get index to data in 1d_H.csv used when getting temporal data
                ind = self.Data_1D.H.Header.index(nd)
                self.LP.H_nd_index.append(ind)
                self.LP.Hmax.append(max(self.Data_1D.H.Values[:,ind]))
            except:
                error = True
                message = 'Unable to find node in _1d_H.csv file. Node: '+nd
                return error, message


        # channel info
        self.LP.dist_nodes = [0.0] # nodes only
        self.LP.dist_chan_inverts = [0.0] # at each channel end (no nodes)
        self.LP.dist_inverts = [0.0] # nodes and channel ends
        self.LP.chan_inv = [0.0]
        self.LP.chan_LB = [0.0]
        self.LP.chan_RB = [0.0]

        for i, chan_index in enumerate(self.LP.chan_index):
            #length of current channel
            chan_len = self.Channels.chan_Length[chan_index] # length of current channel

            # distance at nodes
            cur_len = self.LP.dist_nodes[len(self.LP.dist_nodes)-1] #current length at node
            self.LP.dist_nodes.append(cur_len+chan_len)

            #distance at inverts
            cur_len = self.LP.dist_chan_inverts[len(self.LP.dist_chan_inverts)-1] #current length at invert locations
            self.LP.dist_chan_inverts.append(cur_len+0.0001) # dist for upstream invert
            new_len = cur_len + chan_len
            self.LP.dist_chan_inverts.append(new_len-0.0001) #dist for downstream invert

            #distance at both inverts and nodes
            cur_len = self.LP.dist_inverts[len(self.LP.dist_inverts)-1] #current length at invert locations
            self.LP.dist_inverts.append(cur_len+0.0001) # dist for upstream invert
            new_len = cur_len + self.Channels.chan_Length[chan_index]
            self.LP.dist_inverts.append(new_len-0.0001) #dist for downstream invert
            self.LP.dist_inverts.append(new_len) #dist at next node

            #elevations at channel inverts, left and right obverts
            self.LP.chan_inv.append(self.Channels.chan_US_Inv[chan_index])
            self.LP.chan_LB.append(self.Channels.chan_LBUS_Obv[chan_index])
            self.LP.chan_RB.append(self.Channels.chan_RBUS_Obv[chan_index])
            self.LP.chan_inv.append(self.Channels.chan_DS_Inv[chan_index])
            self.LP.chan_LB.append(self.Channels.chan_LBDS_Obv[chan_index])
            self.LP.chan_RB.append(self.Channels.chan_RBDS_Obv[chan_index])

        #get infor about pits
        self.LP.npits = int(0)
        self.LP.pit_dist = []
        self.LP.pit_z = []
        for i, nd_ind in enumerate(self.LP.node_index):
            nchan = self.nodes.node_nChan[nd_ind]
            chan_list = self.nodes.node_channels[nd_ind]
            for j in range(nchan):
                chan = chan_list[j]
                indC = self.Channels.chan_name.index(chan)
                usC = self.Channels.chan_US_Chan[indC]
                dsC = self.Channels.chan_DS_Chan[indC]
                if usC == "------" and dsC == "------": #channel is pit channel
                    self.LP.npits = self.LP.npits + 1
                    self.LP.pit_dist.append(self.LP.dist_nodes[i])
                    self.LP.pit_z.append(self.Channels.chan_US_Inv[indC])


        #normal return
        self.LP.static = True
        return error, message

    def LP_getData(self,dat_type,time,dt_tol):
        self.LP.Hdata = []
        error = False
        message = None
        dt_abs = abs(self.times - time)
        t_ind = dt_abs.argmin()
        if (self.times[t_ind] - time)>dt_tol:
            error = True
            message = 'ERROR - Closest time: '+str(self.times[t_ind])+' outside time search tolerance: '+str(dt_tol)
            return  error, message
        if dat_type == 'Head':
            for h_ind in self.LP.H_nd_index:
                self.LP.Hdata.append(self.Data_1D.H.Values[t_ind,h_ind])
        else:
            error = True
            message = 'ERROR - Only head supported for LP temporal data'
            return  error, message

        return error, message

    def __init__(self, fname):
        self.script_version = version
        self.filename = fname
        self.fpath = os.path.dirname(fname)
        self.nTypes = 0
        self.Types = []
        self.LP = LP()
        self.Data_1D = Data_1D()

        try:
            data = numpy.genfromtxt(fname, dtype=None, delimiter="==")
        except:
            print 'ERROR - Unable to load data, check file exists.'
            print 'File: '+fname
            sys.exit()
        for i in range (0,len(data)):
            tmp = data[i,0]
            dat_type = tmp.strip()
            tmp = data[i,1]
            rdata = tmp.strip()
            if (dat_type=='Format Version'):
                self.formatVersion = int(rdata)
            elif (dat_type=='Units'):
                self.units = rdata
            elif (dat_type=='Simulation ID'):
                self.displayname = rdata
            elif (dat_type=='Number Channels'):
                #self.nChannels = int(rdata)
                self.Data_1D.nChan = int(rdata)
            elif (dat_type=='Number Nodes'):
                self.Data_1D.nNode = int(rdata)
            elif (dat_type=='Channel Info'):
                if rdata != 'NONE':
                    fullpath = os.path.join(self.fpath,rdata)
                    if not os.path.isfile(fullpath):
                        print fullpath+' does not exist'
                        fname = rdata.replace('_1d_','_1d_1d_')
                        fullpath = os.path.join(self.fpath,fname)
                    self.Channels = ChanInfo(fullpath)
                    if (self.Data_1D.nChan != self.Channels.nChan):
                        raise RuntimeError("Number of Channels does not match value in .info")
            elif (dat_type=='Node Info'):
                if rdata != 'NONE':
                    fullpath = os.path.join(self.fpath,rdata)
                    if not os.path.isfile(fullpath):
                        print fullpath+' does not exist'
                        fname = rdata.replace('_1d_','_1d_1d_')
                        fullpath = os.path.join(self.fpath,fname)
                    self.nodes = NodeInfo(fullpath)
            elif (dat_type=='Water Levels'):
                if rdata != 'NONE':
                    fullpath = os.path.join(self.fpath,rdata)
                    self.Data_1D.H = Timeseries(fullpath,'H',self.displayname)
                    self.nTypes = self.nTypes + 1
                    self.Types.append('1D Water Levels')
                    if self.nTypes == 1:
                        self.times = self.Data_1D.H.Values[:,1]
            elif (dat_type=='Flows'):
                if rdata != 'NONE':
                    fullpath = os.path.join(self.fpath,rdata)
                    self.Data_1D.Q = Timeseries(fullpath,'Q',self.displayname)
                    self.nTypes = self.nTypes + 1
                    self.Types.append('1D Flows')
                    if self.nTypes == 1:
                        self.times = self.Data_1D.Q.Values[:,1]
            elif (dat_type=='Velocities'):
                if rdata != 'NONE':
                    fullpath = os.path.join(self.fpath,rdata)
                    self.Data_1D.V = Timeseries(fullpath,'V',self.displayname)
                    self.nTypes = self.nTypes + 1
                    self.Types.append('1D Velocities')
                    if self.nTypes == 1:
                        self.times = self.Data_1D.V.Values[:,1]
            else:
                print "Warning - Unknown Data Type "+dat_type