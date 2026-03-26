import subprocess
import sys, traceback, re, os
from pathlib import Path

OSGEO = r"C:\TUFLOW\dev\OSGeo4W\OSGeo4W.bat"

REMOVE_IMPORTS = [
    'from tab_widget import CustomTabWidget\n',
    'from time_series_plot_widget import TimeSeriesPlotWidget\n',
    'from qgsdockwidget import QgsDockWidget\n'
]

def main():
    inp = Path(sys.argv[1])
    out = Path(sys.argv[2])

    proc = subprocess.run([OSGEO, 'pyuic5', str(inp), '-o', str(out)])

    with out.open() as f:
        lines = f.readlines()

    with out.open('w') as f:
        for line in lines:
            if line.startswith('from PyQt5'):
                f.write('from qgis.PyQt import QtCore, QtGui, QtWidgets\n')
                f.write('\n')
                f.write('from .tab_widget import CustomTabWidget\n')
                f.write('from .tv_plot_widget.time_series_plot_widget import TimeSeriesPlotWidget\n')
                f.write('if not QtCore.QSettings().value(\'TUFLOW/TestCase\', False, type=bool):')
                f.write('   from ...compatibility_routines import (QT_HORIZONTAL, QT_TAB_WIDGET_TRIANGULAR, QT_RICH_TEXT, QT_DOCK_WIDGET_AREA_NONE,\n'
                        '                                          QT_SIZE_POLICY_EXPANDING, QT_SIZE_POLICY_MINIMUM)\n')
                f.write('else:\n')
                f.write('   from tuflow.compatibility_routines import (QT_HORIZONTAL, QT_TAB_WIDGET_TRIANGULAR, QT_RICH_TEXT, QT_DOCK_WIDGET_AREA_NONE,\n'
                    '                                                  QT_SIZE_POLICY_EXPANDING, QT_SIZE_POLICY_MINIMUM)\n')
                continue
            if 'QtCore.Qt.Horizontal' in line:
                line = line.replace('QtCore.Qt.Horizontal', 'QT_HORIZONTAL')
            if 'QtWidgets.QTabWidget.Triangular' in line:
                line = line.replace('QtWidgets.QTabWidget.Triangular', 'QT_TAB_WIDGET_TRIANGULAR')
            if 'QtCore.Qt.RichText' in line:
                line = line.replace('QtCore.Qt.RichText', 'QT_RICH_TEXT')
            if 'QtCore.Qt.NoDockWidgetArea' in line:
                line = line.replace('QtCore.Qt.NoDockWidgetArea', 'QT_DOCK_WIDGET_AREA_NONE')
            if 'QtWidgets.QSizePolicy.Expanding' in line:
                line = line.replace('QtWidgets.QSizePolicy.Expanding', 'QT_SIZE_POLICY_EXPANDING')
            if 'QtWidgets.QSizePolicy.Minimum' in line:
                line = line.replace('QtWidgets.QSizePolicy.Minimum', 'QT_SIZE_POLICY_MINIMUM')
            if line in REMOVE_IMPORTS:
                continue

            f.write(line)



if __name__ == '__main__':
    main()
