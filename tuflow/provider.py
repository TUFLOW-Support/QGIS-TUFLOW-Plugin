import os
import sys
import re
from qgis.PyQt.QtGui import QIcon
from qgis._core import Qgis, QgsMessageLog
from qgis.core import QgsProcessingProvider
from pathlib import Path
import traceback

# We need this path setup for the SWMM alg functions to find the tuflow_swmm folder. It is here instead of
# in those scripts so it will only happen once
script = os.path.dirname(__file__)
# sys.path.append(script)

class Directive:

    def __new__(cls, line: str):
        if DirectiveQgisVersion.matches(line):
            cls = DirectiveQgisVersion
        self = super().__new__(cls)
        self.valid = False
        self._init(line)
        return self

    def __bool__(self):
        return self.valid

    def _init(self, line: str):
        self.line = line

    def qualifies(self):
        return True


class DirectiveQgisVersion(Directive):

    def _init(self, line: str):
        super()._init(line)
        try:
            self.version = int(re.findall(r'\d{5}', line)[0])
            self.check = re.findall(r'[><=]{1,2}', line)[0]
            self.valid = True
        except Exception:
            pass

    @staticmethod
    def matches(line) -> bool:
        r = r'^# QGIS_VERSION[><=]{1,2}\d{5}'
        return bool(re.findall(r, line))

    def qualifies(self):
        qv = Qgis.QGIS_VERSION_INT
        return eval('{0}{1}{2}'.format(qv, self.check, self.version))


class TuflowAlgorithmProvider(QgsProcessingProvider):
    """
    Processing provider for executing R scripts
    """

    def __init__(self):
        QgsProcessingProvider.__init__(self)
        self.algs = []
        self.actions = []
        self.script_folder = os.path.join(os.path.dirname(__file__), 'alg')

    def unload(self):
        """
        Unloads the provider. Any tear-down steps required by the provider
        should be implemented here.
        """
        pass

    def loadAlgorithms(self):
        """
        Called when provider must populate its available algorithms
        """

        self.load_scripts_from_folder()

        for a in self.algs:
            self.addAlgorithm(a)

    def load_scripts_from_folder(self):
        """
        Loads all scripts found under the specified sub-folder
        """
        if not os.path.exists(self.script_folder):
            return

        self.algs.clear()
        for file in Path(self.script_folder).glob('*.py'):
            alg = self.algorithmName(file)
            if alg is not None:
                try:
                    exec('from .alg.{0} import {1}'.format(file.stem, alg))
                    self.algs.append(eval('{0}()'.format(alg)))
                except SyntaxError as err:
                    QgsMessageLog.logMessage(f"Syntax error loading processing algorithm from file: {file}\n"
                                             f"  {err.__class__.__name__} {err.args[0]} on line {err.lineno}",
                                             'TUFLOW',
                                             level=Qgis.Warning)
                except Exception as err:
                    cl, exc, tb = sys.exc_info()
                    line_number = traceback.extract_tb(tb)[-1][1]
                    QgsMessageLog.logMessage(f"Exception loading processing algorithm from file: {file}\n"
                                             f"  {err.__class__.__name__} {err.args[0]}\n"
                                             f"  {traceback.format_exc()}",
                                             'TUFLOW',
                                             level=Qgis.Warning)
                    continue

    def algorithmName(self, file):
        """Extract the algorithm name from python file - assumes only one exists in file."""
        # TEMP
        #pydevd_pycharm.settrace('localhost', port=53110, stdoutToServer=True, stderrToServer=True)
        with open(file, 'r') as f:
            in_multi_line_comment = False
            for line in f:
                directive = Directive(line)
                if directive and not directive.qualifies():
                    return None
                text = [x.strip() for x in line.split('#', 1)]
                if len(text) == 2:
                    text, comment = text
                else:
                    text = text[0]
                text = [x.strip() for x in text.split('"""', 1)]
                if len(text) == 2:
                    code, comment = text
                else:
                    code = text[0]
                if not code.strip():
                    continue

                if code and not in_multi_line_comment:
                    if re.findall(r'^class [A-z]*\(QgsProcessingAlgorithm\):', code):
                        return code.split('class ')[1].split('(')[0]

                if code and not in_multi_line_comment:
                    if re.findall(r'^class [A-z]*\(QgsProcessingFeatureBasedAlgorithm\):', code):
                        return code.split('class ')[1].split('(')[0]

                if re.findall(r'"{3}', line):
                    multi_line_comment = len(re.findall(r'"{3}', line)) % 2 != 0
                    if multi_line_comment:
                        in_multi_line_comment = not in_multi_line_comment

        return None

    def id(self):
        """
        Returns the unique provider id, used for identifying the provider. This
        string should be a unique, short, character only string, eg "qgis" or
        "gdal". This string should not be localised.
        """

        return 'TUFLOW'

    def name(self):
        """
        Returns the provider name, which is used to describe the provider
        within the GUI.

        This string should be short (e.g. "Lastools") and localised.
        """

        return self.tr('TUFLOW')

    def icon(self):
        """
        Returns the provider's icon
        """

        return QIcon(os.path.join(os.path.dirname(__file__), 'tuflow.png'))

    def svgIconPath(self):
        """
        Returns a path to the provider's icon as a SVG file
        """

        return os.path.join(os.path.dirname(__file__), 'icons', 'results.svg')

    def longName(self):
        """
        Returns the a longer version of the provider name, which can include
        extra details such as version numbers. E.g. "Lastools LIDAR tools
        (version 2.2.1)". This string should be localised. The default
        implementation returns the same string as name().
        """

        return self.name()
