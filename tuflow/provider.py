import importlib
import os
import sys
import re
from qgis.PyQt.QtGui import QIcon
from qgis._core import Qgis, QgsMessageLog
from qgis.core import QgsProcessingProvider
from pathlib import Path
import traceback

from .alg_loader_mixin import AlgorithmLoaderMixin


class TuflowAlgorithmProvider(QgsProcessingProvider, AlgorithmLoaderMixin):
    """
    Processing provider for executing R scripts
    """

    def __init__(self):
        QgsProcessingProvider.__init__(self)
        self.algs = []
        self.actions = []
        self.script_folder = os.path.join(os.path.dirname(__file__), 'alg', 'hpc')

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

        self.algs = self.load_scripts_from_folder(self.script_folder)
        for a in self.algs:
            self.addAlgorithm(a)

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
