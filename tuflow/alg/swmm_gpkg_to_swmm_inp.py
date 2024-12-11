from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingParameterFile,
)

import os
import sys
import traceback

from tuflow.tuflow_swmm.gis_to_swmm import gis_to_swmm

try:
    from pathlib import Path
except ImportError:
    from pathlib_ import Path_ as Path


# import pydevd_pycharm
# pydevd_pycharm.settrace('localhost', port=53110, stdoutToServer=True, stderrToServer=True)


# Following pattern from https://docs.qgis.org/3.28/en/docs/user_manual/processing/scripts.html#:~:text=Within%20QGIS%2C%20you%20can%20use%20Create%20new%20script,menu.%20This%20opens%20a%20template%20that%20extends%20QgsProcessingAlgorithm.
class ConvertGpkgToSWMMInp(QgsProcessingAlgorithm):
    """
    This processing tool finds the nodes connected to conduits and reassigns the conduit
    'To Node' and 'From Node' appropriately.
    """

    def __init__(self):
        super().__init__()
        self.feedback = None

    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        # Must return a new copy of your algorithm.
        return ConvertGpkgToSWMMInp()

    def name(self):
        """
        Returns the unique algorithm name.
        """
        return 'ConvertGpkgToSWMMInp'

    def displayName(self):
        """
        Returns the translated algorithm name.
        """
        return self.tr('GeoPackage - Write to SWMM Inp')

    def flags(self):
        return QgsProcessingAlgorithm.Flag.FlagNoThreading

    def group(self):
        """
        Returns the name of the group this algorithm belongs to.
        """
        return self.tr('SWMM')

    def groupId(self):
        """
        Returns the unique ID of the group this algorithm belongs
        to.
        """
        return 'TuflowSWMM_Tools'

    def shortHelpString(self):
        """
        Returns a localised short help string for the algorithm.
        """
        folder = Path(os.path.realpath(__file__)).parent
        help_filename = folder / 'help/html/alg_gpkg_to_swmm_inp.html'
        return help_filename.read_text()

    def initAlgorithm(self, config=None):
        """
        Here we define the inputs and outputs of the algorithm.
        """

        # 'INPUT' is the recommended name for the main input
        # parameter.
        self.addParameter(
            QgsProcessingParameterFile(
                'INPUT',
                self.tr('GeoPackage Input File'),
                extension='gpkg',
            )
        )

        # 'OUTPUT' is the recommended name for the main output
        # parameter.
        # self.addOutput(
        #    QgsProcessingOutputFile(
        #        'OUTPUT_filename',
        #        self.tr('SWMM inp filename')
        #    )
        # )

    def processAlgorithm(self, parameters, context, feedback):
        """
        This is where the magic happens
        """
        self.feedback = feedback

        gpkg_file = self.parameterAsFile(parameters,
                                         'INPUT',
                                         context)

        if not Path(gpkg_file).exists():
            self.feedback.reportError(self.tr(f'Geopackage input file does not exist: {gpkg_file}'),
                                      fatalError=True)

        swmm_filename = Path(gpkg_file).with_suffix('.inp')

        # log_feedback = LogProcessingFeedback('C:\\temp\\debug_log.txt')
        try:
            gis_to_swmm(
                gpkg_file,
                swmm_filename,
                feedback=self.feedback,
            )
        except Exception as e:
            message = f'Exception thrown converting GeoPackage to SWMM: {str(e)}\n'
            try:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                message += '\n'.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
            finally:
                del exc_type, exc_value, exc_traceback

            self.feedback.reportError(message)


        # log_feedback.pushInfo('Finished processing')
        # log_feedback.close()

        # feedback.pushInfo(f'Finished writing: {output_filename}')

        result_dict = {
            # 'OUTPUT_filename': swmm_filename,
        }

        # Return the results
        return result_dict
