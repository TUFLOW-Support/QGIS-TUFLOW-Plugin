import os
import re
from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsProcessingProvider
from pathlib import Path

from .alg_loader_mixin import AlgorithmLoaderMixin


class TuflowCatchAlgorithmProvider(QgsProcessingProvider, AlgorithmLoaderMixin):
    """
    Processing provider for executing TUFLOW Catch scripts.
    """

    def __init__(self):
        super().__init__()
        self.algs = []
        self.actions = []
        self.script_folder = os.path.join(os.path.dirname(__file__), 'alg', 'catch')

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

        return 'TUFLOWCATCH'

    def name(self):
        """
        Returns the provider name, which is used to describe the provider
        within the GUI.

        This string should be short (e.g. "Lastools") and localised.
        """

        return self.tr('TUFLOW Catch')

    def icon(self):
        """
        Returns the provider's icon
        """

        return QIcon(self.svgIconPath())

    def svgIconPath(self):
        """
        Returns a path to the provider's icon as a SVG file
        """

        return os.path.join(os.path.dirname(__file__), 'icons', 'Fishing-Boy-Silhouette.svg')

    def longName(self):
        """
        Returns the a longer version of the provider name, which can include
        extra details such as version numbers. E.g. "Lastools LIDAR tools
        (version 2.2.1)". This string should be localised. The default
        implementation returns the same string as name().
        """

        return self.name()
