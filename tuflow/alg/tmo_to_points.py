import tempfile
from osgeo import ogr, gdal

from qgis.PyQt.QtCore import QCoreApplication, QVariant
from qgis.PyQt.QtWidgets import QComboBox
from qgis.core import (QgsProcessingParameterFile, QgsProject, QgsProcessingParameterDefinition,
                        QgsProcessingParameterEnum, QgsProcessingOutputLayerDefinition, QgsProcessingMultiStepFeedback,
                        QgsProcessingParameterVectorDestination, QgsExpressionContext, QgsProcessingAlgorithm)
from qgis.gui import QgsProcessingHiddenWidgetWrapper, QgsProcessingParametersGenerator
import processing
from processing.tools.dataobjects import createContext
from processing.gui.wrappers import WidgetWrapper
from processing.gui.AlgorithmDialogBase import AlgorithmDialogBase
from processing.gui.AlgorithmDialog import AlgorithmDialog
from processing.gui.ParametersPanel import ParametersPanel

from ..tmo import TMO
try:
    from pathlib import Path
except ImportError:
    from pathlib_ import Path_ as Path


def get_driver_by_extension(driver_type, ext):
    if not ext:
        return

    ext = ext.lower()
    if ext[0] == '.':
        ext = ext[1:]

    for i in range(gdal.GetDriverCount()):
        drv = gdal.GetDriver(i)
        md = drv.GetMetadata_Dict()
        if ('DCAP_RASTER' in md and driver_type == 'raster') or ('DCAP_VECTOR' in md and driver_type == 'vector'):
            if not drv.GetMetadataItem(gdal.DMD_EXTENSIONS):
                continue
            driver_extensions = drv.GetMetadataItem(gdal.DMD_EXTENSIONS).split(' ')
            for drv_ext in driver_extensions:
                if drv_ext.lower() == ext:
                    return drv.ShortName


class TmoToPoints_CustomParametersPanel(ParametersPanel):

    def createProcessingParameters(self, flags=QgsProcessingParametersGenerator.Flags()):
        include_default = not (flags & QgsProcessingParametersGenerator.Flag.SkipDefaultValueParameters)
        parameters = {}
        for p, v in self.extra_parameters.items():
            parameters[p] = v

        for param in self.algorithm().parameterDefinitions():
            if param.flags() & QgsProcessingParameterDefinition.FlagHidden:
                continue
            if not param.isDestination():
                try:
                    wrapper = self.wrappers[param.name()]
                except KeyError:
                    continue

                # For compatibility with 3.x API, we need to check whether the wrapper is
                # the deprecated WidgetWrapper class. If not, it's the newer
                # QgsAbstractProcessingParameterWidgetWrapper class
                # TODO QGIS 4.0 - remove
                if issubclass(wrapper.__class__, WidgetWrapper):
                    widget = wrapper.widget
                else:
                    widget = wrapper.wrappedWidget()

                if not isinstance(wrapper, QgsProcessingHiddenWidgetWrapper) and widget is None:
                    continue

                value = wrapper.parameterValue()
                if isinstance(widget, QComboBox):
                    value = widget.currentText()
                if param.defaultValue() != value or include_default:
                    parameters[param.name()] = value

                # if not param.checkValueIsAcceptable(value):
                #     raise AlgorithmDialogBase.InvalidParameterValue(param, widget)
            else:
                if self.in_place and param.name() == 'OUTPUT':
                    parameters[param.name()] = 'memory:'
                    continue

                try:
                    wrapper = self.wrappers[param.name()]
                except KeyError:
                    continue

                widget = wrapper.wrappedWidget()
                value = wrapper.parameterValue()
                if isinstance(widget, QComboBox):
                    value = widget.currentText()

                dest_project = None
                if wrapper.customProperties().get('OPEN_AFTER_RUNNING'):
                    dest_project = QgsProject.instance()

                if value and isinstance(value, QgsProcessingOutputLayerDefinition):
                    value.destinationProject = dest_project
                if value and (param.defaultValue() != value or include_default):
                    parameters[param.name()] = value

                    context = createContext()
                    ok, error = param.isSupportedOutputValue(value, context)
                    if not ok:
                        raise AlgorithmDialogBase.InvalidOutputExtension(widget, error)

        return self.algorithm().preprocessParameters(parameters)


class TmoToPoints_CustomDialog(AlgorithmDialog):

    def getParametersPanel(self, alg, parent):
        return TmoToPoints_CustomParametersPanel(parent, alg, self.in_place, self.active_layer)

    def changeEvent(self,  *args, **kwargs):
        AlgorithmDialog.changeEvent(self, *args, **kwargs)
        self.event_handler()

    def keyReleaseEvent(self, *args, **kwargs):
        AlgorithmDialog.keyReleaseEvent(self, *args, **kwargs)
        self.event_handler()

    def event_handler(self):
        if self.mainWidget() is None:
            return
        if not hasattr(self.mainWidget(), 'wrappers'):
            return
        if 'tmo_file' not in self.mainWidget().wrappers or 'times' not in self.mainWidget().wrappers:
            return
        tmo_file_value = self.mainWidget().wrappers['tmo_file'].widgetValue()
        times_wrapper = self.mainWidget().wrappers['times']
        times_param = times_wrapper.parameterDefinition()
        times_cbo = times_wrapper.wrappedWidget()
        if isinstance(tmo_file_value, QVariant) and tmo_file_value.isNull():
            self.tmo_file = None
            times_param.setOptions([])
            if times_cbo is not None:
                times_cbo.clear()
            return
        if isinstance(tmo_file_value, str) and not tmo_file_value:
            self.tmo_file = None
            times_param.setOptions([])
            if times_cbo is not None:
                times_cbo.clear()
            return

        if not hasattr(self, 'tmo_file'):
            return

        if tmo_file_value == self.tmo_file:
            return

        self.tmo_file = tmo_file_value
        try:
            tmo = TMO(self.tmo_file)
            options = []
            for time in tmo.header.times:
                if time == 99999.0:
                    options.insert(0, 'max')
                elif time == -99999.0:
                    options.insert(0, 'min')
                else:
                    options.append(str(time))
            times_param.setOptions(options)
            times_cbo.clear()
            times_cbo.addItems(options)
        except FileExistsError:
            self.tmo_file = None
            times_param.setOptions([])
            times_cbo.clear()
        except Exception:
            self.tmo_file = None
            times_param.setOptions([])
            times_cbo.clear()


class TmoToPoints(QgsProcessingAlgorithm):

    def call_back_prog(self, *args, **kwargs):
        self.count += 1
        self.feedback.setCurrentStep(self.count)

    def call_back_log(self, *args, **kwargs):
        self.feedback.pushInfo(args[0])

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFile('tmo_file', 'TMO File', optional=False,
                                                     behavior=QgsProcessingParameterFile.File, fileFilter='TMO (*.tmo)',
                                                     defaultValue=None))
        self.addParameter(QgsProcessingParameterEnum('times', 'Time Selection', options=['max'], allowMultiple=False))
        self.addParameter(
            QgsProcessingParameterVectorDestination(
                'OUTPUT',
                self.tr('Points output')
            )
        )

    def processAlgorithm(self, parameters, context, model_feedback):
        # try and initialise tmo class
        try:
            tmo = TMO(parameters['tmo_file'])
        except Exception as e:
            model_feedback.reportError(str(e))
            return {}

        try:
            # set total points for processing for progress bar
            point_count = tmo.point_count()
            self.feedback = QgsProcessingMultiStepFeedback(point_count, model_feedback)

            # get output file
            if parameters['OUTPUT'].sink.value(QgsExpressionContext())[0] == 'TEMPORARY_OUTPUT':
                name = Path(parameters['tmo_file']).stem + '_{0}'.format(parameters['times'])
                tmpdir = tempfile.mkdtemp(prefix='tuflow_alg_tmo_to_points')
                output_file = Path(tmpdir) / (name + '.gpkg')
            else:
                output_file = Path(parameters['OUTPUT'].sink.value(QgsExpressionContext())[0])
                name = output_file.stem

            # create output file
            driver_name = get_driver_by_extension('vector', output_file.suffix)
            if driver_name is None:
                self.feedback.reportError('Output format not recognised: {0}'.format(output_file))
                return {}

            if output_file.exists():
                dataset = ogr.GetDriverByName(driver_name).Open(str(output_file), 1)
                if dataset is None:
                    self.feedback.reportError('Unable to open {0}'.format(output_file))
                    return {}
                if dataset.GetLayerByName(name):
                    dataset.DeleteLayer(name)
            else:
                dataset = ogr.GetDriverByName(driver_name).CreateDataSource(str(output_file))
                if dataset is None:
                    self.feedback.reportError('could not open {0}'.format(output_file))
                    return {}
            lyr = dataset.CreateLayer(name)
            if lyr is None:
                self.feedback.reportError('could not create layer')
                return {}
            field = ogr.FieldDefn('Value', ogr.OFTReal)
            field.SetWidth(15)
            field.SetPrecision(5)
            lyr.CreateField(field)
            field = ogr.FieldDefn('Domain', ogr.OFTInteger)
            lyr.CreateField(field)

            # iterate through points and create feature
            self.count = 0
            dataset.StartTransaction()
            for point in tmo.data_at_time(parameters['times'], self.call_back_log, self.call_back_prog):
                x, y, val, dom_ind = point
                feat = ogr.Feature(lyr.GetLayerDefn())
                geom = ogr.Geometry(ogr.wkbPoint)
                geom.AddPoint(x, y)
                feat.SetGeometry(geom)
                feat.SetField(0, float(val))
                feat.SetField(1, int(dom_ind))
                lyr.CreateFeature(feat)
                feat = None
            dataset.CommitTransaction()

            dataset, lyr = None, None

        except Exception as e:
            self.feedback.reportError(str(e))
            return {}

        # open output file
        alg_params = {
            'INPUT': str(output_file),
            'NAME': name
        }
        if parameters['OUTPUT'].destinationProject is not None:
            processing.run('native:loadlayer', alg_params, context=context, feedback=self.feedback, is_child_algorithm=True)

        return {'OUTPUT': str(output_file)}

    def createCustomParametersWidget(self, parent=None):
        return TmoToPoints_CustomDialog(self, False, parent)

    def name(self):
        return 'TMO to Points'

    def displayName(self):
        return self.tr(self.name())

    def createInstance(self):
        return TmoToPoints()

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def checkParameterValues(self, parameters, p_str=None, Any=None, *args, **kwargs):
        return True, ''
