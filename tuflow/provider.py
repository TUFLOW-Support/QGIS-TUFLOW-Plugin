import os
import sys
import re
from PyQt5.QtGui import QIcon
from qgis.core import QgsProcessingProvider
from pathlib import Path


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

        sys.path.append(self.script_folder)

        self.algs.clear()
        for file in Path(self.script_folder).glob('*.py'):
            alg = self.algorithmName(file)
            if alg is not None:
                try:
                    exec('from {0} import {1}'.format(file.stem, alg))
                    self.algs.append(eval('{0}()'.format(alg)))
                except:
                    continue

    def algorithmName(self, file):
        """Extract the algorithm name from python file - assumes only one exists in file."""

        with open(file, 'r') as f:
            in_multi_line_comment = False
            for line in f:
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
