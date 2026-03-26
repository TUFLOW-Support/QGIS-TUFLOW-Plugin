from qgis.PyQt.QtWidgets import QLabel, QWidget, QGraphicsDropShadowEffect
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtCore import QSettings

from qgis.utils import iface

if not QSettings().value('TUFLOW/TestCase', False, type=bool):
    from ...compatibility_routines import QT_RICH_TEXT, QT_ALIGN_TOP, QT_ALIGN_LEFT
else:
    from tuflow.compatibility_routines import QT_RICH_TEXT, QT_ALIGN_TOP, QT_ALIGN_LEFT


class HelpText(QLabel):

    def __init__(self):
        if iface is not None:
            super().__init__(parent=iface.mapCanvas())
        else:
            super().__init__()
        self.setTextFormat(QT_RICH_TEXT)
        self.colour = QColor('#005581')  # tuflow dark blue
        self.setStyleSheet('QLabel { background-color : rgba(255,255,255,150); padding: 6px; border-radius: 4px; }')
        self.shadow = QGraphicsDropShadowEffect()
        self.shadow.setBlurRadius(6)
        self.shadow.setColor(QColor(0, 0, 0, 100))
        self.shadow.setOffset(3, 3)
        self.setGraphicsEffect(self.shadow)
        self.setAlignment(QT_ALIGN_LEFT | QT_ALIGN_TOP)
        self.move(10, 10)
        self.hide()
        self.owner = None

    def setText(self, text: str):
        super().setText(self.add_formatting(text))
        self.adjustSize()

    def add_formatting(self, text: str) -> str:
        default_div_style = (
            f'<div style="margin-top:3px; margin-bottom:3px; margin-left:0px; font-size:14px; '
            f'font-weight:bold; color:{self.colour.name()}">'
        )
        list_div_style = (
            f'<div style="margin-top:3px; margin-bottom:3px; margin-left:14px; '
            f'font-size: 14px; color: {self.colour.name()};">'
        )
        text = text.replace('<li>', f'{list_div_style}• ')
        text = text.replace('</li>', '<br></div>')
        text = text.replace('<ul>', '</div>')
        text = text.replace('</ul>', f'<br>{default_div_style}')
        return (f'{default_div_style}{text}</div>')

    def show(self):
        super().show()
        self.adjustSize()
