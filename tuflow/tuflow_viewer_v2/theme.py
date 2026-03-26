import re
from pathlib import Path

from qgis.core import QgsApplication, Qgis
from qgis.PyQt.QtGui import QPalette, QColor
from qgis.PyQt.QtWidgets import QApplication


class TuflowViewerTheme:

    def __init__(self, theme_name: str, style_sheet: str, palette: QPalette):
        self.theme_name = theme_name
        self.style_sheet = style_sheet
        self.palette = palette
        self.valid = palette is not None or theme_name == 'default'


def theme_folder(theme_name: str) -> tuple[Path, str]:
    """Returns the folder path and theme name for a given theme.
    Note, the theme can be 'qgis' to use the current QGIS theme.
    """
    if theme_name.lower() == 'qgis':
        theme_name = QgsApplication.instance().themeName()
        if theme_name.lower() == 'default':
            theme_name = 'Light'
    return Path(__file__).parent / 'theme' / theme_name, theme_name


def load_theme(theme_name: str) -> TuflowViewerTheme:
    follow_qgis = False
    if theme_name.lower() == 'default':
        follow_qgis = True
        theme_name = QgsApplication.instance().themeName() if QgsApplication.instance().themeName() else 'default'
        if theme_name.lower() == 'default':
            theme_name = 'Light'
    theme_path, theme_name = theme_folder(theme_name)
    style_sheet = theme_path / 'style.qss'
    variables_file = theme_path / 'variables.qss'
    palette_file = theme_path / 'palette.txt'

    qgis_theme_path = QgsApplication.uiThemes().get(theme_name, 'default')
    if not qgis_theme_path:
        qgis_theme_path = QgsApplication.defaultThemePath()

    if not style_sheet.exists() or not variables_file.exists() or not palette_file.exists():
        return TuflowViewerTheme(theme_name, '', None)

    with style_sheet.open() as f:
        style_data = f.read()

    style_data = style_data.replace('@theme_path', qgis_theme_path)
    with variables_file.open() as f:
        for line in f:
            if line.startswith('@'):
                name, value = [x.strip() for x in line.split(':', 1)]
                # style_data = style_data.replace(name, value)
                style_data = re.sub(r'(?<=[:;\s])' + re.escape(name) + r'(?=[:;\s])', value, style_data)

    # if Qgis.UI_SCALE_FACTOR != 1.0:
    #     for match in re.finditer(r'(?<=[\\s:])([0-9\\.]+)(?=em)', style_data):
    #         number = float(match.group(0)) * Qgis.UI_SCALE_FACTOR
    #         style_data = style_data[:match.start(0)] + f'{number:.2f}' + style_data[match.end(0):]

    palette = QgsApplication.instance().palette()
    with palette_file.open() as f:
        for line in f:
            role, colour = [x.strip() for x in line.split(':', 1)]
            palette.setColor(QPalette.ColorRole(int(role)), QColor(colour))

    theme = TuflowViewerTheme(theme_name, style_data, palette)
    theme.theme_name = 'Default' if follow_qgis else theme_name
    return theme
