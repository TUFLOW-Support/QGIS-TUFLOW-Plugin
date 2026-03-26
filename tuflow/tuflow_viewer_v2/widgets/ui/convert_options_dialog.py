import subprocess
from collections import OrderedDict
from pathlib import Path

OSGEO = r"C:\TUFLOW\dev\OSGeo4W\OSGeo4W.bat"

DIR = Path(__file__).parent
INPUT = DIR / 'options_dialog.ui'
OUT = DIR / '..' / 'settings' / 'ui_options_dialog.py'

COMP_MAP = OrderedDict([
    ('QtCore.Qt.Horizontal', 'QT_HORIZONTAL'),
    ('QtWidgets.QDialogButtonBox.Close', 'QT_BUTTON_BOX_CLOSE'),
    ('QtCore.Qt.ScrollBarAlwaysOff', 'QT_SCROLL_BAR_ALWAYS_OFF'),
    ('QtWidgets.QAbstractItemView.NoEditTriggers', 'QT_ABSTRACT_ITEM_VIEW_NO_EDIT_TRIGGERS'),
    ('QtCore.Qt.ElideNone', 'QT_ELIDE_NONE'),
])

imports = ', '.join(COMP_MAP.values()).split('\n')
while len(imports[-1]) > 80:
    last = imports.pop()
    split_at = last.rfind(',', 0, 80)
    imports.append(last[:split_at + 1])
    imports.append(last[split_at + 1:])
IMPORTS = '\n    '.join(imports)


def main():
    proc = subprocess.run([OSGEO, 'pyuic5', str(INPUT), '-o', str(OUT)])

    with OUT.open() as f:
        lines = f.readlines()

    with OUT.open('w') as f:
        for line in lines:
            if line.startswith('from PyQt5'):
                f.write('from qgis.PyQt import QtCore, QtGui, QtWidgets\n')
                f.write('\n')
                f.write('if not QtCore.QSettings().value(\'TUFLOW/TestCase\', False, type=bool):\n')
                f.write(f'   from ....compatibility_routines import ({IMPORTS})\n')
                f.write('else:\n')
                f.write(f'   from tuflow.compatibility_routines import ({IMPORTS})\n')
                continue

            while any(k in line for k in COMP_MAP.keys()):
                for k, v in COMP_MAP.items():
                    line = line.replace(k, v)

            f.write(line)


if __name__ == '__main__':
    main()
