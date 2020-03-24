try:
    import winreg
except:
    pass
import os, subprocess, re, sys, traceback
import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal, QVariant
from PyQt5.QtWidgets import QMessageBox
from qgis.core import QgsVectorFileWriter, QgsFields, QgsField, QgsWkbTypes, QgsFeature, NULL
from tuflow.tuflowqgis_library import convertFormattedTimeToTime

try:
    from .checksum import checkSum
except ImportError:
    pass


class Refh2(QObject):
    """Class for obtaining ReFH2 data and
    processing into TUFLOW
    
    Inherits from QObject so signals and QThread can be used.
    """
    
    England = 'ENGWANI'
    Scotland = 'SCOTLAND'
    Winter = 'WINTER'
    Summer = 'SUMMER'
    Urban = 'URBANISED'
    Rural = 'RURAL'
    GrossRainfall = 1
    UrbanRainfall = 2
    RuralRainfall = 3
    NetRainfall = 5
    DirectRunoff = 6
    BaseFlow = 7
    TotalRunoff = 8
    UserArea = 10
    QgisArea = 11
    RF = 12
    SA = 13
    SA_RF = 14
    BC_2d = 15
    BC_1d = 16
    AutoPad = 20
    NoPad = 21
    UserPad = 22
    
    # signals
    locatingExe = pyqtSignal()
    refh2Start = pyqtSignal()
    tuflowProcessingStart = pyqtSignal()
    finished = pyqtSignal(str)
    
    def __init__(self, inputs: dict=None) -> None:
        QObject.__init__(self)
        self.inputs = inputs
        self.data = None
        self.headers = []
        self.bcdbaseContent = []

    def run(self) -> None:
        """
        Run the tool using ReFH2 cmd API
        
        :return: None
        """
        
        if 'exe' not in self.inputs:
            exeLoc = self.findExe()
            if 'error' in exeLoc:
                self.finished.emit(exeLoc)
                return
            else:
                self.inputs['exe'] = exeLoc
        
        # arguments
        exe = self.inputs['exe']
        infile = '--infile={0}'.format(self.inputs['descriptor'])
        #outfile = '--outfile={0}'.format(self.inputs['output file'])
        checksum = '--checksum={0}'.format(checkSum(self.inputs['descriptor']))
        vendor = '--vendor=bmt'
        mode = '--mode=HYDROGRAPH'
        returnperiods = '--returnperiods={0}'.format(','.join([str(x) for x in self.inputs['return periods']]))
        country = '--country={0}'.format(self.inputs['location'])
        #model = '--model={0}'.format(self.inputs['output hydrograph type'])
        seasonality = '--seasonality={0}'.format(self.inputs['season'])
        plotscale = '--plotscale=NO'
        area = '--area={0}'.format(self.inputs['area'])
        reportoutputfolder = '--reportoutputfolder={0}'.format(os.path.dirname(self.inputs['output file']))
        rainModel = '--rainmodel={0}'.format(self.inputs['rain model'])

        durations = self.inputs['durations']
        timesteps = self.inputs['timesteps']
        if not durations:
            self.inputs['durations'] = [None]
            durations = [None]  # dummy entry

        index = -1
        for j, dur in enumerate(durations):
            for i, (k, m) in enumerate(self.inputs['output hydrograph type'].items()):
                index += 1
                model = f'--model={m}'
                outfile = '--outfile={0}_{1}.csv'.format(self.inputs['output file'], m)
                self.inputs['output file final'] = outfile[10:]
                args = [exe, infile, outfile, checksum, vendor, mode, returnperiods,
                        country, model, seasonality, plotscale, area, reportoutputfolder,
                        rainModel]

                if dur is not None:
                    outfile = '--outfile={0}_{1}_{2}.csv'.format(self.inputs['output file'], m, dur.replace(':', '-'))
                    self.inputs['output file final'] = outfile[10:]
                    args[2] = outfile
                    duration = '--duration={0}'.format(dur)
                    timestep = '--timestep={0}'.format(timesteps[j])
                    args.append(duration)
                    args.append(timestep)

                self.refh2Start.emit()
                CREATE_NO_WINDOW = 0x08000000
                proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                        creationflags=CREATE_NO_WINDOW)
                proc.wait()
                out, err = proc.communicate()
                if out:
                    msg = out.decode('utf-8')
                    if re.findall(r"^\d*:", msg):
                        try:
                            code = int(re.findall(r"^\d*:", msg)[0][:-1])
                            if code == 6040:
                                self.processIntoTuflow(msg=f"WARNING {msg}", model=k, model_type=m, index=index, iter=i, iDur=j)
                                continue
                        except ValueError:
                            self.finished.emit(msg)
                    self.finished.emit(msg)
                    return
                else:
                    self.processIntoTuflow(model=k, model_type=m, index=index, iter=i, iDur=j)
        
    def processIntoTuflow(self, msg='', model=None, index=0, model_type=None, iter=0, iDur=0) -> None:
        """
        Processing the output data from ReFH2
        into TUFLOW format.
        
        :return: None
        """
        
        self.tuflowProcessingStart.emit()

        mIter = len(set([x for k, x in self.inputs['output hydrograph type'].items()]))
        mDur = len(self.inputs['durations'])

        if self.inputs['do output rainfall'] or self.inputs['do output hydrograph']:
            # manipulate output data
            self.convertFormatToTuflow(model, iter, mIter, model_type, index, mIter * mDur, iDur)
            
            # create TEF
            if index == 0:
                self.createTEF()
            
            # create bc_dbase
            if index < mIter:
                self.createBcDbase(model, iter, mIter, model_type)
            
            # create GIS
            if index == 0:
                self.createGis()
            
        if index + 1 == mIter * mDur:
            self.finished.emit(msg)

    def getTimestep(self, model=None) -> float:
        """
        Works out what the timestep is from the REFH2 output file

        :return: float
        """

        timeFirst = None
        timeSecond = None
        timestep = 0
        f = self.inputs['output file final']
        #f = "{0}_{1}.csv".format(self.inputs['output file'], self.inputs['output hydrograph type'][model])
        try:
            with open(f, 'r') as fo:
                for i, line in enumerate(fo):
                    comp = line.split(',')
                    if i > 0:
                        if timeFirst is not None and timeSecond is None:
                            timeSecond = convertFormattedTimeToTime(comp[0])
                            timestep = timeSecond - timeFirst
                            break
                        if timeFirst is None:
                            timeFirst = convertFormattedTimeToTime(comp[0])
        except IOError:
            self.finished.emit('Error Opening {0}'.format(f))
            return 0
        except Exception:
            self.finished.emit('Unexpected error calculating timestep from {0}'.format(self.inputs['output file']))
            return 0

        return timestep
        
    def convertFormatToTuflow(self, model=None, iter=0, mIter=1, model_type=None, index=0, mIndex=1, iDur=0) -> None:
        """
        Converts the native output from
        ReFH2 to TUFLOW compatible - change time column and remove unwanted columns
        
        :return: None
        """

        # name = '{0}_TUFLOW.csv'.format(os.path.basename(os.path.splitext(self.inputs['output file'])[0]))
        if self.inputs['durations'][0] is not None:
            #iDur = int((index - iter) / len(self.inputs['durations']))
            name = '{0}_{1}.csv'.format(os.path.basename(self.inputs['output file']), self.inputs['durations'][iDur].replace(":", "-"))
            self.inputs['source file'] = '{0}_~DUR~.csv'.format(os.path.basename(self.inputs['output file']))
        else:
            name = '{0}.csv'.format(os.path.basename(self.inputs['output file']))
            self.inputs['source file'] = name
        outfile = os.path.join(os.path.dirname(self.inputs['output file']), name)
        timehr = None
        contents = []
        timestep = self.getTimestep(model)
        if not timestep:
            return
        try:
            f = self.inputs['output file final']
            #f = "{0}_{1}.csv".format(self.inputs['output file'], self.inputs['output hydrograph type'][model])
            with open(f, 'r') as fo:
                for i, line in enumerate(fo):
                    lineComp = line.split(',')
                    if i == 0:
                        contents.append('Time (hr)')
                    else:
                        if i == 1:  # insert zero values
                            # first time
                            zeros = ['0'] * len(self.inputs['return periods']) * len(self.inputs['output data'])
                            contents[-1] = ('{0}0'.format(contents[-1]))
                            contents.append(','.join(zeros) + '\n')
                        timehr = convertFormattedTimeToTime(lineComp[0]) + timestep
                        contents[-1] = ('{0}{1:.2f}'.format(contents[-1], timehr))
                    for k in range(len(self.inputs['return periods'])):
                        for j, outdata in enumerate(self.inputs['output data']):
                            contents.append(lineComp[outdata + 8*k].strip())  # 8 columns in source file
                            if j + 1 == len(self.inputs['output data']) and k + 1 == len(self.inputs['return periods']):
                                contents[-1] = contents[-1] + '\n'
                            if i == 0 and k == 0:
                                sourceHeader = lineComp[outdata].strip()
                                sourceHeaderWoARI = re.split(r'[0-9]+ year', sourceHeader)
                                if len(sourceHeaderWoARI) == 2:
                                    sourceHeaderWildcard = '{0}~ARI~{1}'.format(sourceHeaderWoARI[0], sourceHeaderWoARI[1])
                                else:
                                    sourceHeaderWildcard = '!! ERROR occured getting header name !!'
                                if 'net rain' in sourceHeaderWildcard.lower():
                                    if model_type == self.inputs['output hydrograph type']["rainfall"]:
                                        self.inputs['net rainfall source column'] = sourceHeaderWildcard
                                elif 'design rain' in sourceHeaderWildcard.lower():
                                    if model_type == self.inputs['output hydrograph type']["rainfall"]:
                                        self.inputs['design rainfall source column'] = sourceHeaderWildcard
                                elif 'direct runoff' in sourceHeaderWildcard.lower():
                                    if model_type == self.inputs['output hydrograph type']["hydrograph"]:
                                        self.inputs['direct runoff inflow source column'] = sourceHeaderWildcard
                                elif 'baseflow' in sourceHeaderWildcard.lower():
                                    if model_type == self.inputs['output hydrograph type']["hydrograph"]:
                                        self.inputs['baseflow inflow source column'] = sourceHeaderWildcard
                                elif 'total flow' in sourceHeaderWildcard.lower():
                                    if model_type == self.inputs['output hydrograph type']["hydrograph"]:
                                        self.inputs['total inflow source column'] = sourceHeaderWildcard
                # write a zero entry at the end
                if timehr:
                    contents[-1] = ('{0}{1}'.format(contents[-1], timehr + timestep))
                    contents.append(','.join(zeros))
        except IOError:
            self.finished.emit('Error Opening {0}'.format(f))
            return
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            self.finished.emit(f"{traceback.print_exception(exc_type, exc_value, exc_traceback)}")
        try:
            #with open(outfile, 'w') as fo:
            #    fo.write('! {0} Processed into TUFLOW Format by ReFH2 to TUFLOW QGIS Plugin Tool\n'.format(self.inputs['output file']))
            #    fo.write('! Zero values have been inserted at the start and end of event\n'.format(self.inputs['output file']))
            #    fo.write(','.join(contents))
            # change to array
            d = [x.split(",") for x in ",".join(contents).split("\n")]
            h = d[0]
            a = np.array([[float(x) for x in y] for y in d[1:]])
            if iter == 0:
                self.data = np.copy(a)
                self.headers = h[:]
            else:
                self.data, a = self.makeEqualLength(self.data, a, fill=0)
                indexes = self.getModelIndexes(model, h)
                for i in indexes:
                    self.headers[i] = h[i]
                    self.data[:,i] = a[:,i]

            if iter + 1 == mIter:
                header = '! {0} Processed into TUFLOW Format by ReFH2 to TUFLOW QGIS Plugin Tool\n' \
                         '! Zero values have been inserted at the start and end of event\n' \
                         '{1}'.format(self.inputs['output file'], ','.join(self.headers))
                np.savetxt(outfile, self.data, fmt="%.3f", delimiter=",", newline="\n", header=header, comments="")

        except PermissionError:
            self.finished.emit('{0} Locked'.format(outfile))
            return
        except IOError:
            self.finished.emit('Error Opening {0}'.format(outfile))
            return
        except Exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            self.finished.emit(f"{traceback.print_exception(exc_type, exc_value, exc_traceback)}")
    
    def createBcDbase(self, model=None, index=0, mIndex=1, model_type=None) -> None:
        """
        Create TUFLOW bc_dbase.csv
        based on user inputs i.e. catchment name
        
        :return: None
        """
        
        bc_dbase = os.path.join(os.path.dirname(self.inputs['output file']), 'bc_dbase.csv')

        #if index == 0:
            #self.bcdbaseContent.append('Name,Source,Column 1,Column 2')
        if self.inputs['do output rainfall'] and model_type == self.inputs['output hydrograph type']['rainfall']:
            if Refh2.GrossRainfall in self.inputs['output data']:
                self.bcdbaseContent.append('{0}_Gross,{1},Time (hr),{2}'.format(self.inputs['rainfall name'],
                                                                  self.inputs['source file'],
                                                                  self.inputs['design rainfall source column']))
            if Refh2.NetRainfall in self.inputs['output data']:
                self.bcdbaseContent.append('{0}_Net,{1},Time (hr),{2}'.format(self.inputs['rainfall name'],
                                                                  self.inputs['source file'],
                                                                  self.inputs['net rainfall source column']))
        if self.inputs['do output hydrograph'] and model_type == self.inputs['output hydrograph type']['hydrograph']:
            if Refh2.DirectRunoff in self.inputs['output data']:
                self.bcdbaseContent.append('{0}_Direct,{1},Time (hr),{2}'.format(self.inputs['inflow name'],
                                                                     self.inputs['source file'],
                                                                     self.inputs['direct runoff inflow source column']))
            if Refh2.BaseFlow in self.inputs['output data']:
                self.bcdbaseContent.append('{0}_Baseflow,{1},Time (hr),{2}'.format(self.inputs['inflow name'],
                                                                       self.inputs['source file'],
                                                                       self.inputs['baseflow inflow source column']))
            if Refh2.TotalRunoff in self.inputs['output data']:
                self.bcdbaseContent.append('{0}_Total,{1},Time (hr),{2}'.format(self.inputs['inflow name'],
                                                                    self.inputs['source file'],
                                                                    self.inputs['total inflow source column']))
        if index + 1 == mIndex:
            try:
                with open(bc_dbase, 'w') as fo:
                    fo.write('Name,Source,Column 1,Column 2\n')
                    fo.write('\n'.join(self.bcdbaseContent))
            except PermissionError:
                self.finished.emit('{0} Locked'.format(bc_dbase))
                return
            except IOError:
                self.finished.emit('Error Opening {0}'.format(bc_dbase))
                return
    
    def createTEF(self) -> None:
        """
        Create TUFLOW Event File (TEF)
        based on the user's selected
        return period(s).
        
        :return: None
        """
        
        # TEF file path
        tef = os.path.join(os.path.dirname(self.inputs['output file']), 'event_file.tef')
        
        # work out padding e.g. if 100y in return periods
        # all other return periods will be padded accordingly
        # e.g. 010y
        if self.inputs['zero padding'] == Refh2.AutoPad:
            pad = len(str(max(self.inputs['return periods'])))
        elif self.inputs['zero padding'] == Refh2.NoPad:
            pad = 0
        else:
            pad = self.inputs['number zero padding']
        rps = ['{0:0{1}d}'.format(x, pad) for x in sorted(self.inputs['return periods'])]  # sorted list with padding
        
        try:
            with open(tef, 'w') as fo:
                fo.write('! TEF Written by ReFH2 to TUFLOW QGIS Plugin Tool\n\n')
                fo.write('!! RAINFALL EVENTS !!\n')
                for rp in rps:
                    fo.write('Define Event == {0}yr\n'.format(rp))
                    fo.write('    BC Event Source == ~ARI~ | {0} year\n'.format(int(rp)))
                    fo.write('End Define\n')
                    fo.write('!-------------------------------------\n')
                if self.inputs['durations'][0] is not None:
                    fo.write('\n!! DURATIONS !!\n')
                    for dur in self.inputs['durations']:
                        fo.write(f'Define Event == {dur.replace(":","-")}\n')
                        fo.write(f'    BC Event Source == ~DUR~ | {dur.replace(":","-")}\n')
                        fo.write('End Define\n')
                        fo.write('!-------------------------------------\n')
        except PermissionError:
            self.finished.emit('{0} Locked'.format(tef))
            return
        except IOError:
            self.finished.emit('Error Opening {0}'.format(tef))
            return
        
    def createGis(self) -> None:
        """
        Create TUFLOW GIS Layer(s)
        Use input GIS feature for data
        
        :return: None
        """
        
        if self.inputs['gis feature'] is not None:
            if self.inputs['output gis'] is not None:
                for gisOutput in self.inputs['output gis']:
                    fields = QgsFields()
                    feat = QgsFeature()
                    feat.setGeometry(self.inputs['gis feature'].geometry())
                    name = os.path.splitext(os.path.basename(self.inputs['output file']))[0]
                    if gisOutput == Refh2.RF:
                        outfile = os.path.join(os.path.dirname(self.inputs['output file']),
                                               '2d_rf_{0}_R.shp'.format(name))
                        fields.append(QgsField("Name", QVariant.String, len=100))
                        fields.append(QgsField("f1", QVariant.Double, len=15, prec=5))
                        fields.append(QgsField("f2", QVariant.Double, len=15, prec=5))
                        feat.setAttributes([self.inputs['rainfall name'], 1, 1])
                    elif gisOutput == Refh2.SA_RF:
                        outfile = os.path.join(os.path.dirname(self.inputs['output file']),
                                               '2d_sa_rf_{0}_R.shp'.format(name))
                        fields.append(QgsField("Name", QVariant.String, len=100))
                        fields.append(QgsField("Catchment_", QVariant.Double, len=15, prec=5))
                        fields.append(QgsField("Rain_Gauge", QVariant.Double, len=15, prec=5))
                        fields.append(QgsField("IL", QVariant.Double, len=15, prec=5))
                        fields.append(QgsField("CL", QVariant.Double, len=15, prec=5))
                        feat.setAttributes([self.inputs['rainfall name'], self.inputs['area'], NULL, NULL, NULL])
                    elif gisOutput == Refh2.SA:
                        outfile = os.path.join(os.path.dirname(self.inputs['output file']),
                                               '2d_sa_{0}_R.shp'.format(name))
                        fields.append(QgsField("Name", QVariant.String, len=100))
                        feat.setAttributes([self.inputs['inflow name']])
                    elif gisOutput == Refh2.BC_2d:
                        outfile = os.path.join(os.path.dirname(self.inputs['output file']),
                                               '2d_rf_{0}_L.shp'.format(name))
                        fields.append(QgsField("Type", QVariant.String, len=2))
                        fields.append(QgsField("Flags", QVariant.String, len=3))
                        fields.append(QgsField("Name", QVariant.String, len=100))
                        fields.append(QgsField("f", QVariant.Double, len=15, prec=5))
                        fields.append(QgsField("d", QVariant.Double, len=15, prec=5))
                        fields.append(QgsField("td", QVariant.Double, len=15, prec=5))
                        fields.append(QgsField("a", QVariant.Double, len=15, prec=5))
                        fields.append(QgsField("b", QVariant.Double, len=15, prec=5))
                        feat.setAttributes(['QT', NULL, self.inputs['inflow name'], NULL, NULL, NULL, NULL, NULL])
                    elif gisOutput == Refh2.BC_1d:
                        if self.inputs['gis geometry'] == QgsWkbTypes.PointGeometry:
                            outfile = os.path.join(os.path.dirname(self.inputs['output file']),
                                                   '1d_bc_{0}_P.shp'.format(name))
                        else:
                            outfile = os.path.join(os.path.dirname(self.inputs['output file']),
                                                   '1d_bc_{0}_R.shp'.format(name))
                        fields.append(QgsField("Type", QVariant.String, len=2))
                        fields.append(QgsField("Flags", QVariant.String, len=6))
                        fields.append(QgsField("Name", QVariant.String, len=50))
                        fields.append(QgsField("Descriptio", QVariant.String, len=250))
                        feat.setAttributes(['QT', NULL, self.inputs['inflow name'], NULL])
                    writer = QgsVectorFileWriter(outfile, "UTF-8", fields, self.inputs['gis geometry'], self.inputs['crs'], driverName="ESRI Shapefile")
                    if writer.hasError() != QgsVectorFileWriter.NoError:
                        self.finished.emit(writer.errorMessage())
                        return
                    writer.addFeature(feat)
                    del writer
    
    def findExe(self) -> str:
        """
        Find ReFH2.exe using the registry.
        
        :return: str exe path
        """
        
        self.locatingExe.emit()
        
        # does the user have a license - does not check if current
        key = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Installer\UserData\S-1-5-18\Components"
        hKey = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key)
        for i in range(winreg.QueryInfoKey(hKey)[0]):
            hKey2 = winreg.OpenKey(hKey, winreg.EnumKey(hKey, i))
            if winreg.QueryInfoKey(hKey2)[1] == 1:  # only one value
                if 'refh2.exe' == os.path.basename(winreg.EnumValue(hKey2, 0)[1].lower()):
                    return '{0}{1}RefH2CLI.exe'.format(os.path.dirname(winreg.EnumValue(hKey2, 0)[1]), os.path.sep)
        
        return "Error: Cannot Find ReFH2.exe"

    def getModelIndexes(self, model, header):
        """
        Returns index of relevant headers for model type.

        Example:
            model = "rainfall"
            return indexes for headers - "net rain" and "design rain"

        """

        indexes = []
        for i, h in enumerate(header):
            if model == "rainfall":
                if 'net rain' in h.lower():
                    indexes.append(i)
                elif 'design rain' in h.lower():
                    indexes.append(i)
            elif model == "hydrograph":
                if 'direct runoff' in h.lower():
                    indexes.append(i)
                elif 'baseflow' in h.lower():
                    indexes.append(i)
                elif 'total flow' in h.lower():
                    indexes.append(i)

        return indexes

    def makeEqualLength(self, a, b, fill=0):
        """
        Makes numpy qrrays equal length (based on largest).

        """

        shapeA = a.shape
        shapeB = b.shape

        if shapeA[0] > shapeB[0]:
            b = self.lengthenArrayAndFill(b, shapeA[0], fill)
        elif shapeA[0] < shapeB[0]:
            a = self.lengthenArrayAndFill(a, shapeB[0], fill)

        return a, b

    def lengthenArrayAndFill(self, a, length, fill):
        """
        lengthen array a to length and fill.

        """

        diff = length - a.shape[0]
        f = np.array([[fill for x in range(a.shape[1])] for y in range(diff)])
        b = np.append(a, f, axis=0)

        return b

