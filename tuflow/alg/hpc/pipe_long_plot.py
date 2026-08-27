import os
import typing
from pathlib import Path

from qgis.PyQt import QtCore, QtGui

from qgis.core import Qgis
from qgis.core import (QgsProcessingAlgorithm, QgsProcessingContext, QgsProcessingFeedback, QgsProcessingParameterFile,
                       QgsProcessingParameterRasterLayer, QgsProcessingParameterString, QgsProcessingParameterNumber,
                       QgsProcessingParameterBoolean, QgsProcessingMultiStepFeedback,
                       QgsProcessingParameterFileDestination, QgsProcessingParameterDefinition)

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from matplotlib.patches import Polygon

import tuflow.pt.pytuflow as pt
from tuflow.gui.alg.processing_parameter_font import QgsProcessingParameterFont
from tuflow.gui.alg.processing_parameter_linestyle import QgsProcessingParameterLineStyle


# Support older versions of QGIS - but require at least Python 3.10
FILE = Qgis.ProcessingFileParameterBehavior.File if Qgis.QGIS_VERSION_INT >= 33600 else Qgis.ProcessingFileParameterBehavior.File
DOUBLE = Qgis.ProcessingNumberParameterType.Double if Qgis.QGIS_VERSION_INT >= 33600 else Qgis.ProcessingNumberParameterType.Double
INTEGER = Qgis.ProcessingNumberParameterType.Integer if Qgis.QGIS_VERSION_INT >= 33600 else Qgis.ProcessingNumberParameterType.Integer


_fig = plt.figure()
SUPPORTED_IMAGE_FORMATS = _fig.canvas.get_supported_filetypes()
SUPPORTED_IMAGE_FILTER = ' '.join([f'*.{ext}' for ext in SUPPORTED_IMAGE_FORMATS.keys()])


_QFONTSTYLE_MAP = {
    QtGui.QFont.Style.StyleNormal: 'normal',
    QtGui.QFont.Style.StyleItalic: 'italic',
    QtGui.QFont.Style.StyleOblique: 'oblique',
}

_QPENSTYLE_MAP = {
    QtCore.Qt.PenStyle.SolidLine: '-',
    QtCore.Qt.PenStyle.DashLine: '--',
    QtCore.Qt.PenStyle.DotLine: ':',
    QtCore.Qt.PenStyle.DashDotLine: '-.',
    QtCore.Qt.PenStyle.DashDotDotLine: '-..',
}


class PipePlot(QgsProcessingAlgorithm):

    def initAlgorithm(self, configuration: dict[str | None, typing.Any] = ...) -> None:
        # title
        self.addParameter(
            QgsProcessingParameterString(
                'TITLE',
                self.tr('Enter the plot title'),
                defaultValue=None,
                optional=True
            )
        )
        # tpc
        self.addParameter(
            QgsProcessingParameterFile(
                'TPC',
                self.tr('Select the TPC file'),
                behavior=FILE,
                fileFilter='TPC (*.tpc *.TPC)',
                defaultValue=None
            )
        )
        # dem
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                'DEM',
                self.tr('Select the DEM raster layer'),
                defaultValue=None,
                optional=True
            )
        )
        # start channel
        self.addParameter(
            QgsProcessingParameterString(
                'START_CHANNEL',
                self.tr('Enter the start channel name'),
                defaultValue=None
            )
        )
        # end channel
        self.addParameter(
            QgsProcessingParameterString(
                'END_CHANNEL',
                self.tr('Enter the end channel name'),
                defaultValue=None,
                optional=True
            )
        )
        # time
        self.addParameter(
            QgsProcessingParameterNumber(
                'TIME',
                self.tr('Enter the time (hours) or 99999 for max, -99999 for min'),
                type=DOUBLE,
            )
        )
        # energy
        self.addParameter(
            QgsProcessingParameterBoolean(
                'INCLUDE_ENERGY',
                self.tr('Include energy in the plot?'),
                defaultValue=False
            )
        )
        # DPI
        self.addParameter(
            QgsProcessingParameterNumber(
                'DPI',
                self.tr('Output Image DPI'),
                type=INTEGER,
                defaultValue=150
            )
        )
        # output file
        self.addParameter(
            QgsProcessingParameterFileDestination(
                'OUTPUT',
                self.tr('Select the output file'),
                fileFilter=SUPPORTED_IMAGE_FILTER,
                defaultValue=None
            )
        )

        # Styling
        # Title font parameter (advanced)
        param = QgsProcessingParameterFont('TITLE_FONT', self.tr('Title font'), defaultValue=QtGui.QFont('Arial', 12, QtGui.QFont.Weight.Bold))
        param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(param)
        # Main font parameter (advanced)
        param = QgsProcessingParameterFont('MAIN_FONT', self.tr('Main font (axis labels, major tick labels)'), defaultValue=QtGui.QFont('Arial', 10))
        param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(param)
        # Secondary font parameter (advanced)
        param = QgsProcessingParameterFont('SECONDARY_FONT', self.tr('Secondary font (channel labels, minor tick labels)'), defaultValue=QtGui.QFont('Arial', 8))
        param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(param)
        # Tertiary font parameter (advanced)
        param = QgsProcessingParameterFont('TERTIARY_FONT', self.tr('Tertiary font (diameter and slope labels)'), defaultValue=QtGui.QFont('Arial', 8), defaultColor=QtGui.QColor('blue'))
        param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(param)
        # Legend font parameter (advanced)
        param = QgsProcessingParameterFont('LEGEND_FONT', self.tr('Legend font'), defaultValue=QtGui.QFont('Arial', 8))
        param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(param)
        # Main grid line style
        param = QgsProcessingParameterLineStyle(
            'MAIN_LINESTYLE',
            self.tr('Main grid line style (border, axis ticks)'),
            defaultColor=QtGui.QColor('black'),
            defaultWidth=1.2,
            defaultPenStyle=QtCore.Qt.PenStyle.SolidLine
        )
        param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(param)
        # Secondary line style
        param = QgsProcessingParameterLineStyle(
            'SECONDARY_LINESTYLE',
            self.tr('Secondary grid line style (culvert boundaries)'),
            defaultColor=QtGui.QColor('black'),
            defaultWidth=0.9,
            defaultPenStyle=QtCore.Qt.PenStyle.DotLine
        )
        param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(param)
        # Water level line style
        param = QgsProcessingParameterLineStyle(
            'WATER_LINESTYLE',
            self.tr('Water level line style'),
            defaultColor=QtGui.QColor('royalblue'),
            defaultWidth=1.5,
            defaultPenStyle=QtCore.Qt.PenStyle.SolidLine
        )
        param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(param)
        # Energy line style
        param = QgsProcessingParameterLineStyle(
            'ENERGY_LINESTYLE',
            self.tr('Energy line style'),
            defaultColor=QtGui.QColor('#d6008b'),
            defaultWidth=1.2,
            defaultPenStyle=QtCore.Qt.PenStyle.DotLine
        )
        param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(param)
        # Pipe color
        param = QgsProcessingParameterLineStyle(
            'PIPE_COLOUR',
            self.tr('Pipe color (colour only)'),
            defaultColor=QtGui.QColor('#b0b0b0'),
            defaultWidth=1.0,
            defaultPenStyle=QtCore.Qt.PenStyle.SolidLine
        )
        param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(param)
        # Pit color
        param = QgsProcessingParameterLineStyle(
            'PIT_COLOUR',
            self.tr('Pit color (colour only)'),
            defaultColor=QtGui.QColor('#606060'),
            defaultWidth=1.0,
            defaultPenStyle=QtCore.Qt.PenStyle.SolidLine
        )
        param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(param)
        # DEM color
        param = QgsProcessingParameterLineStyle(
            'DEM_COLOUR',
            self.tr('DEM color (colour only)'),
            defaultColor=QtGui.QColor('#c8a96e'),
            defaultWidth=1.0,
            defaultPenStyle=QtCore.Qt.PenStyle.SolidLine
        )
        param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(param)

    def processAlgorithm(
            self,
            parameters: dict[str|None, typing.Any],
            context: QgsProcessingContext,
            feedback: QgsProcessingFeedback | None
    ) -> dict[str, typing.Any]:
        title = self.parameterAsString(parameters, 'TITLE', context)
        tpc_path = self.parameterAsFile(parameters, 'TPC', context)
        dem_layer = self.parameterAsRasterLayer(parameters, 'DEM', context)
        start_channel = self.parameterAsString(parameters, 'START_CHANNEL', context)
        end_channel = self.parameterAsString(parameters, 'END_CHANNEL', context)
        time = self.parameterAsDouble(parameters, 'TIME', context)
        include_energy = self.parameterAsBool(parameters, 'INCLUDE_ENERGY', context)
        dpi = self.parameterAsInt(parameters, 'DPI', context)
        ou = self.parameterAsFileOutput(parameters, 'OUTPUT', context)
        if not Path(ou).suffix or Path(ou).suffix.lower() == '.file':
            ou = str(Path(ou).with_suffix('.png'))

        # styling
        # title font
        raw = self.parameterAsString(parameters, 'TITLE_FONT', context)
        title_font = QgsProcessingParameterFont.valueAsFont(raw)
        title_color = QgsProcessingParameterFont.valueAsColor(raw)
        # main font
        raw = self.parameterAsString(parameters, 'MAIN_FONT', context)
        main_font = QgsProcessingParameterFont.valueAsFont(raw)
        main_color = QgsProcessingParameterFont.valueAsColor(raw)
        # secondary font
        raw = self.parameterAsString(parameters, 'SECONDARY_FONT', context)
        secondary_font = QgsProcessingParameterFont.valueAsFont(raw)
        secondary_color = QgsProcessingParameterFont.valueAsColor(raw)
        # tertiary font
        raw = self.parameterAsString(parameters, 'TERTIARY_FONT', context)
        tertiary_font = QgsProcessingParameterFont.valueAsFont(raw)
        tertiary_color = QgsProcessingParameterFont.valueAsColor(raw)
        # legend font
        raw = self.parameterAsString(parameters, 'LEGEND_FONT', context)
        legend_font = QgsProcessingParameterFont.valueAsFont(raw)
        legend_color = QgsProcessingParameterFont.valueAsColor(raw)
        # main line style
        raw = self.parameterAsString(parameters, 'MAIN_LINESTYLE', context)
        main_line_color = QgsProcessingParameterLineStyle.valueAsColor(raw)
        main_line_width = QgsProcessingParameterLineStyle.valueAsWidth(raw)
        main_line_style = QgsProcessingParameterLineStyle.valueAsPenStyle(raw)
        # Secondary line style
        raw = self.parameterAsString(parameters, 'SECONDARY_LINESTYLE', context)
        secondary_line_color = QgsProcessingParameterLineStyle.valueAsColor(raw)
        secondary_line_width = QgsProcessingParameterLineStyle.valueAsWidth(raw)
        secondary_line_style = QgsProcessingParameterLineStyle.valueAsPenStyle(raw)
        # Water level line style
        raw = self.parameterAsString(parameters, 'WATER_LINESTYLE', context)
        water_line_color = QgsProcessingParameterLineStyle.valueAsColor(raw)
        water_line_width = QgsProcessingParameterLineStyle.valueAsWidth(raw)
        water_line_style = QgsProcessingParameterLineStyle.valueAsPenStyle(raw)
        # Energy line style
        raw = self.parameterAsString(parameters, 'ENERGY_LINESTYLE', context)
        energy_line_color = QgsProcessingParameterLineStyle.valueAsColor(raw)
        energy_line_width = QgsProcessingParameterLineStyle.valueAsWidth(raw)
        energy_line_style = QgsProcessingParameterLineStyle.valueAsPenStyle(raw)
        # Pipe color
        raw = self.parameterAsString(parameters, 'PIPE_COLOUR', context)
        pipe_color = QgsProcessingParameterLineStyle.valueAsColor(raw)
        # Pit color
        raw = self.parameterAsString(parameters, 'PIT_COLOUR', context)
        pit_color = QgsProcessingParameterLineStyle.valueAsColor(raw)
        # DEM color
        raw = self.parameterAsString(parameters, 'DEM_COLOUR', context)
        dem_color = QgsProcessingParameterLineStyle.valueAsColor(raw)

        kwargs = {
            'title_font': title_font,
            'title_color': title_color,
            'main_font': main_font,
            'main_color': main_color,
            'secondary_font': secondary_font,
            'secondary_color': secondary_color,
            'tertiary_font': tertiary_font,
            'tertiary_color': tertiary_color,
            'legend_font': legend_font,
            'legend_color': legend_color,
            'main_line_color': main_line_color,
            'main_line_width': main_line_width,
            'main_line_style': main_line_style,
            'secondary_line_color': secondary_line_color,
            'secondary_line_width': secondary_line_width,
            'secondary_line_style': secondary_line_style,
            'water_line_color': water_line_color,
            'water_line_width': water_line_width,
            'water_line_style': water_line_style,
            'energy_line_color': energy_line_color,
            'energy_line_width': energy_line_width,
            'energy_line_style': energy_line_style,
            'pipe_color': pipe_color,
            'pit_color': pit_color,
            'dem_color': dem_color,
        }

        multi_feedback = QgsProcessingMultiStepFeedback(6, feedback)
        multi_feedback.setCurrentStep(0)

        multi_feedback.pushInfo(f'Output file: {ou}')

        multi_feedback.pushInfo(f'Loading TPC: {tpc_path}')
        res, df, units = load_tpc_section(tpc_path, start_channel, end_channel, time)
        multi_feedback.setCurrentStep(1)
        multi_feedback.pushInfo(f'  Channels in section: {df["channel"].nunique()}, rows: {len(df)}')

        channels = df['channel'].unique().tolist()
        channel_geom = get_channel_geometry(res, channels)
        multi_feedback.setCurrentStep(2)
        multi_feedback.pushInfo(f'  Channel geometries loaded: {len(channel_geom)}/{len(channels)}')

        linestring = build_dem_linestring(df, channel_geom)
        multi_feedback.setCurrentStep(3)
        multi_feedback.pushInfo(f'  DEM linestring points: {len(linestring)}')

        dem_df = None
        if dem_layer:
            multi_feedback.pushInfo(f'Loading DEM: {dem_layer}')
            dem_fpath = dem_layer.dataProvider().dataSourceUri()
            dem_df = load_dem_section(dem_fpath, linestring)
        else:
            multi_feedback.pushInfo(f'No DEM, skipping...')
        multi_feedback.setCurrentStep(3)

        segments = build_segments(df, res._channel_info, units)
        multi_feedback.setCurrentStep(4)
        multi_feedback.pushInfo(f'  Pipe segments: {len(segments)}')

        plot_long_section(title, df, dem_df, segments, res, ou, units, time, include_energy, dpi, **kwargs)
        multi_feedback.setCurrentStep(5)

        return {'OUTPUT': ou}

    def name(self) -> str:
        return 'Pipe Long Plot'

    def displayName(self) -> str:
        return self.tr(self.name())

    def group(self) -> str:
        return self.tr(self.groupId())

    def groupId(self) -> str:
        return 'Plotting'

    def shortHelpString(self) -> str:
        folder = Path(os.path.realpath(__file__)).parent
        help_filename = folder / 'help' / 'html' / 'pipe_long_plot.html'
        if not help_filename.exists():
            return ''
        return self.tr(help_filename.read_text(errors='ignore').replace('\n', '<p>'))

    def shortDescription(self) -> str:
        return self.tr("Generate a long profile plot of a pipe network.")

    def createInstance(self) -> 'PipePlot':
        return PipePlot()

    def tr(self, string):
        return QtCore.QCoreApplication.translate('Processing', string)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_tpc_section(tpc_path: str, start_channel: str, end_channel: str | None, time: float):
    """Load TPC results and return the main-branch long-profile DataFrame."""
    res = pt.TPC(tpc_path)
    if time in [99999, -99999]:
        time = res.times()[0]
    df = res.section([start_channel, end_channel] if end_channel else start_channel, None, time)
    df = df[df['branch_id'] == 0].reset_index(drop=True)
    return res, df, res.units


def get_channel_geometry(res: pt.TPC, channels: list[str]) -> dict:
    """Return a dict of {channel_id: np.ndarray of shape (N, 2)} by reading
    the GIS plot layer lines via TuflowPath.
    """
    gis_path = res._gis_layer_l_fpath
    if gis_path is None:
        raise RuntimeError('No GIS Plot Layer Lines found in TPC.')

    geom_by_id = {}
    with pt.TuflowPath(gis_path).open_gis() as gis:
        for i in range(gis.feature_count()):
            feat = gis.get_feature(i)
            fid = feat.attrs.get('ID', '')
            if fid in channels:
                lines = feat.geom.lines()
                if lines:
                    geom_by_id[fid] = np.vstack(lines)
    return geom_by_id


def build_dem_linestring(df: pd.DataFrame, channel_geom: dict) -> list:
    """Assemble an ordered (x, y) point list spanning all channels in the
    long profile, suitable for passing to Grid.section().
    """
    seen = []
    for ch in df['channel']:
        if ch not in seen:
            seen.append(ch)

    all_coords = []
    for ch in seen:
        if ch not in channel_geom:
            continue
        coords = channel_geom[ch].copy()
        if all_coords:
            prev = np.array(all_coords[-1])
            if np.linalg.norm(coords[-1] - prev) < np.linalg.norm(coords[0] - prev):
                coords = coords[::-1]
        all_coords.extend(coords.tolist())

    return [(float(x), float(y)) for x, y in all_coords]


def load_dem_section(dem_path: str, linestring: list) -> pd.DataFrame:
    """Extract a terrain profile from the DEM along the pipe route."""
    if len(linestring) < 2:
        return None
    grid = pt.Grid(dem_path)
    raw = grid.section(linestring, None, -1)
    # raw has MultiIndex columns (line_name, data_type) where the first
    # sub-column is 'offset'.  Drill into the first line group to get a
    # simple DataFrame with columns ['offset', '<data_type>'].
    line_name = raw.columns.get_level_values(0)[0]
    return raw[line_name].copy()


# ---------------------------------------------------------------------------
# Segment metadata
# ---------------------------------------------------------------------------

def build_segments(df: pd.DataFrame, channel_info: pd.DataFrame, units: str) -> list[dict]:
    """Return a list of per-channel dicts containing offsets, elevations,
    diameter and slope needed for plotting.
    """
    segments = []
    seen = []
    for _, row in df.iterrows():
        ch = row['channel']
        if ch in seen or ch not in channel_info.index:
            continue
        seen.append(ch)

        ch_rows = df[df['channel'] == ch]
        if len(ch_rows) < 2:
            continue
        ci = channel_info.loc[ch]

        segments.append({
            'channel': ch,
            'x_us': float(ch_rows.iloc[0]['offset']),
            'x_ds': float(ch_rows.iloc[-1]['offset']),
            'z_us_inv': float(ci['us_invert']),
            'z_ds_inv': float(ci['ds_invert']),
            'z_us_obv': float(ci['lbus_obvert']),
            'z_ds_obv': float(ci['lbds_obvert']),
            'diameter': (float(ci['lbus_obvert']) - float(ci['us_invert'])) * (1000.0 if units == 'si' else 12.),
            'slope_pct': float(ci['pslope']),  # already in %
        })
    return segments


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

def _add_culvert_lines(ax: plt.Axes, segments: list[dict], font: QtGui.QFont, color: str, **kwargs):
    """Draw dotted vertical culvert boundaries with inline channel labels."""
    secondary_line_color = kwargs.get('secondary_line_color', 'black')
    if isinstance(secondary_line_color, QtGui.QColor):
        secondary_line_color = secondary_line_color.name()
    secondary_line_width = kwargs.get('secondary_line_width', 0.9)
    secondary_line_style = kwargs.get('secondary_line_style', ':')
    if isinstance(secondary_line_style, QtCore.Qt.PenStyle):
        secondary_line_style = _QPENSTYLE_MAP.get(secondary_line_style, ':')

    for seg in segments:
        x = seg['x_us']
        ax.axvline(x, color=secondary_line_color, linestyle=secondary_line_style, linewidth=secondary_line_width, zorder=2)
        # Use axes-fraction y so the label always sits just inside the top edge
        ax.text(
            x + 0.3, 0.97, seg['channel'],
            rotation=90, va='top', ha='left',
            fontsize=font.pointSizeF(), color=color, zorder=8,
            fontfamily=font.family(), fontstyle=_QFONTSTYLE_MAP.get(font.style(), 'normal'),
            clip_on=True,
            transform=ax.get_xaxis_transform(),
        )
    # Draw a closing line at the downstream end of the last culvert (no label)
    if segments:
        ax.axvline(segments[-1]['x_ds'], color=secondary_line_color, linestyle=secondary_line_style, linewidth=secondary_line_width, zorder=2)


def _add_label_axis(ax: plt.Axes, segments: list[dict], labels: list, font: QtGui.QFont, color: str, ylabel: str, **kwargs):
    """
    Configure one of the thin axes below the main plot.
    Tick marks at pipe starts; centred text labels between ticks.
    """
    if isinstance(color, QtGui.QColor):
        color = color.name()
    ticks = [seg['x_us'] for seg in segments]
    if segments:
        ticks.append(segments[-1]['x_ds'])

    ax.set_xticks(ticks)
    ax.set_xticklabels(['' for _ in ticks])
    ax.tick_params(axis='x', direction='inout', length=12)
    ax.set_yticks([])

    for seg, label in zip(segments, labels):
        x_mid = (seg['x_us'] + seg['x_ds']) / 2.0
        ax.text(
            x_mid, 0.5, label,
            ha='center', va='top',
            transform=ax.get_xaxis_transform(),
            fontfamily=font.family(), fontstyle=_QFONTSTYLE_MAP.get(font.style(), 'normal'),
            fontsize=font.pointSizeF(), color=color,
        )

    # ylabel rotated to sit flush on the left
    main_color = kwargs.get('main_color', 'black')
    if isinstance(main_color, QtGui.QColor):
        main_color = main_color.name()
    main_font = kwargs.get('main_font', QtGui.QFont('Arial', 10))
    ax.set_ylabel(ylabel, color=main_color, fontsize=main_font.pointSizeF(), fontfamily=main_font.family(), fontstyle=_QFONTSTYLE_MAP.get(main_font.style(), 'normal'), rotation=0, labelpad=35, va='center', loc='top')


def plot_long_section(
        title: str | None,
        df: pd.DataFrame,
        dem_df: pd.DataFrame | None,
        segments: list[dict], res: pt.TPC,
        output_path: str,
        units: str,
        time: float,
        show_energy: bool = False,
        dpi: int = 150,
        **kwargs
        ):
    title_font = kwargs.get('title_font', QtGui.QFont('Arial', 12))
    title_text_color = kwargs.get('title_color', 'black')
    if isinstance(title_text_color, QtGui.QColor):
        title_text_color = title_text_color.name()
    main_font = kwargs.get('main_font', QtGui.QFont('Arial', 10))
    main_text_color = kwargs.get('main_color', 'black')
    if isinstance(main_text_color, QtGui.QColor):
        main_text_color = main_text_color.name()
    secondary_font = kwargs.get('secondary_font', QtGui.QFont('Arial', 8))
    secondary_text_color = kwargs.get('secondary_color', 'black')
    if isinstance(secondary_text_color, QtGui.QColor):
        secondary_text_color = secondary_text_color.name()
    tertiary_font = kwargs.get('tertiary_font', QtGui.QFont('Arial', 8))
    tertiary_text_color = kwargs.get('tertiary_color', 'blue')
    if isinstance(tertiary_text_color, QtGui.QColor):
        tertiary_text_color = tertiary_text_color.name()
    legend_font = kwargs.get('legend_font', QtGui.QFont('Arial', 8))
    legend_text_color = kwargs.get('legend_color', 'black')
    if isinstance(legend_text_color, QtGui.QColor):
        legend_text_color = legend_text_color.name()
    main_line_color = kwargs.get('main_line_color', 'black')
    if isinstance(main_line_color, QtGui.QColor):
        main_line_color = main_line_color.name()
    main_line_width = kwargs.get('main_line_width', 1.2)
    main_line_style = kwargs.get('main_line_style', '-')
    if isinstance(main_line_style, QtCore.Qt.PenStyle):
        main_line_style = _QPENSTYLE_MAP.get(main_line_style, '-')
    secondary_line_color = kwargs.get('secondary_line_color', 'black')
    if isinstance(secondary_line_color, QtGui.QColor):
        secondary_line_color = secondary_line_color.name()
    secondary_line_width = kwargs.get('secondary_line_width', 0.9)
    secondary_line_style = kwargs.get('secondary_line_style', ':')
    if isinstance(secondary_line_style, QtCore.Qt.PenStyle):
        secondary_line_style = _QPENSTYLE_MAP.get(secondary_line_style, ':')
    wl_line_color = kwargs.get('water_line_color', 'royalblue')
    if isinstance(wl_line_color, QtGui.QColor):
        wl_line_color = wl_line_color.name()
    wl_line_width = kwargs.get('water_line_width', 1.5)
    wl_line_style = kwargs.get('water_line_style', '-')
    if isinstance(wl_line_style, QtCore.Qt.PenStyle):
        wl_line_style = _QPENSTYLE_MAP.get(wl_line_style, '-')
    energy_line_color = kwargs.get('energy_line_color', '#d6008b')
    if isinstance(energy_line_color, QtGui.QColor):
        energy_line_color = energy_line_color.name()
    energy_line_width = kwargs.get('energy_line_width', 1.2)
    energy_line_style = kwargs.get('energy_line_style', ':')
    if isinstance(energy_line_style, QtCore.Qt.PenStyle):
        energy_line_style = _QPENSTYLE_MAP.get(energy_line_style, ':')
    pipe_color = kwargs.get('pipe_color', '#b0b0b0')
    if isinstance(pipe_color, QtGui.QColor):
        pipe_color = pipe_color.name()
    pit_color = kwargs.get('pit_color', '#606060')
    if isinstance(pit_color, QtGui.QColor):
        pit_color = pit_color.name()
    dem_color = kwargs.get('dem_color', '#7a5900')
    if isinstance(dem_color, QtGui.QColor):
        dem_color = dem_color.name()

    """Build and save the full long-section figure."""
    fig = plt.figure(figsize=(20, 10))
    gs = GridSpec(3, 1, height_ratios=[50, 1, 1], hspace=0.4 + max(0, main_font.pointSizeF() - 10) / 20, figure=fig)

    ax_main = fig.add_subplot(gs[0])
    ax_diam = fig.add_subplot(gs[1])
    ax_slope = fig.add_subplot(gs[2])

    # remove border around diam and slope axes
    for ax in (ax_diam, ax_slope):
        for placement in ('bottom', 'left', 'right'):
            ax.spines[placement].set_visible(False)
        ax.spines['top'].set(color=main_line_color, linestyle=main_line_style, linewidth=main_line_width)
        ax.tick_params('x', top=True, bottom=False, labelbottom=False, labeltop=True, color=main_line_color,
                       width=main_line_width)

    # ---- DEM bed elevation ------------------------------------------------
    if dem_df is not None:
        dem_col = next(c for c in dem_df.columns if c != 'offset')
        d_off = dem_df['offset'].values
        d_elev = dem_df[dem_col].values
        # Fill below the DEM surface at low zorder so pipes stay visible
        ax_main.fill_between(
            d_off, d_elev - 100, d_elev,
            color=dem_color, alpha=0.35, label='DEM Bed Elevation', zorder=1,
        )
        darker = QtGui.QColor(dem_color).darker(150).name()
        ax_main.plot(d_off, d_elev, color=darker, lw=1.0, zorder=1)

    # ---- Pipe bed level (invert) ------------------------------------------
    # Bed level: deduplicate consecutive same-offset rows so the line connects
    # us_invert → ds_invert diagonally for each pipe (constant-slope segment).
    # bl = df[['offset', 'bed level']].drop_duplicates(subset='offset')
    # ax_main.plot(
    #     bl['offset'], bl['bed level'],
    #     color='black', lw=1.2, label='Bed Level', zorder=10,
    # )

    # Water level: deduplicate same-offset rows so the line slopes correctly
    if time == 99999:
        wl_dtype = 'max water level'
        e_dtype = 'max energy'
    elif time == -99999:
        wl_dtype = 'min water level'
        e_dtype = 'min energy'
    else:
        wl_dtype = 'water level'
        e_dtype = 'energy'
    wl = df[['offset', wl_dtype]].drop_duplicates(subset='offset')
    ax_main.plot(
        wl['offset'], wl[wl_dtype],
        color=wl_line_color, lw=wl_line_width, linestyle=wl_line_style, label='Water Level', zorder=11,
    )

    # Energy line (optional, only if --energy flag and column present)
    if show_energy and e_dtype in df.columns:
        el = df[['offset', e_dtype]].drop_duplicates(subset='offset')
        ax_main.plot(
            el['offset'], el[e_dtype],
            color=energy_line_color, lw=energy_line_width, linestyle=energy_line_style, label='Energy', zorder=12,
        )
    elif show_energy:
        print('energy data type not in results, skipping...')

    # ---- Culvert Polygons --------------------------------------------------
    pipe_patch = None
    for seg in segments:
        verts = [
            (seg['x_us'], seg['z_us_inv']),
            (seg['x_ds'], seg['z_ds_inv']),
            (seg['x_ds'], seg['z_ds_obv']),
            (seg['x_us'], seg['z_us_obv']),
        ]
        darker = QtGui.QColor(pipe_color).darker(150).name()
        poly = Polygon(
            verts, closed=True,
            facecolor=pipe_color, edgecolor=darker,
            linewidth=1.0, zorder=5,
        )
        ax_main.add_patch(poly)
        pipe_patch = poly  # keep reference for legend

    # ---- Pits --------------------------------------------------------------
    pit_df = df[df['pits'].notna()]
    if not pit_df.empty:
        ax_main.vlines(
            pit_df['offset'], pit_df['bed level'], pit_df['pits'],
            color=pit_color, lw=3.0, label='Pits', zorder=6,
        )

    # ---- Culvert boundary lines + labels ----------------------------------
    # Set focused y-limits before adding labels (culverts use axes transform)
    all_inverts = [seg['z_us_inv'] for seg in segments] + [seg['z_ds_inv'] for seg in segments]
    all_obverts = [seg['z_us_obv'] for seg in segments] + [seg['z_ds_obv'] for seg in segments]
    wl_vals = df['water level'].dropna().values
    dem_vals = dem_df[dem_col].values if dem_df is not None else np.array([])
    y_min = min(all_inverts) - 1.0
    y_max = max(
        max(all_obverts) if all_obverts else y_min,
        wl_vals.max() if len(wl_vals) else y_min,
        dem_vals.max() if len(dem_vals) else y_min,
        pit_df['pits'].max() if len(pit_df) else y_min
    ) + 1.0
    ax_main.set_ylim(y_min, y_max)
    x_lim = (df['offset'].min(), df['offset'].max() * 1.01)
    ax_main.set_xlim(*x_lim)
    _add_culvert_lines(ax_main, segments, font=secondary_font, color=secondary_text_color, **kwargs)

    # ---- Legend / labels ---------------------------------------------------
    legend_handles = ax_main.get_legend_handles_labels()
    if pipe_patch is not None:
        from matplotlib.patches import Patch
        legend_handles[0].insert(2, Patch(facecolor='#b0b0b0',
                                          edgecolor='#606060', label='Pipes'))
        legend_handles[1].insert(2, 'Pipes')
    ax_main.legend(
        legend_handles[0], legend_handles[1],
        loc='upper right', labelcolor=legend_text_color,
        prop={'family': legend_font.family(), 'style': _QFONTSTYLE_MAP.get(legend_font.style(), 'normal'),
              'size': legend_font.pointSizeF()}
    )
    yunits = 'Elevation (m RL)' if units == 'si' else 'Elevation (ft RL)'
    xunits = 'Chainage (m)' if units == 'si' else 'Chainage (ft)'
    ax_main.set_ylabel(yunits, fontsize=main_font.pointSizeF(), color=main_text_color, fontfamily=main_font.family(),
                       fontstyle=_QFONTSTYLE_MAP.get(main_font.style(), 'normal'))
    ax_main.set_xlabel(xunits, fontsize=main_font.pointSizeF(), color=main_text_color, fontfamily=main_font.family(),
                       fontstyle=_QFONTSTYLE_MAP.get(main_font.style(), 'normal'))
    if title:
        ax_main.set_title(title,
                          fontdict={
                                'fontsize': title_font.pointSizeF(),
                                'color': title_text_color,
                                'fontfamily': title_font.family(),
                                'fontstyle': _QFONTSTYLE_MAP.get(title_font.style(), 'normal')
                          }
        )
    ax_main.grid(True, linestyle='--', alpha=0.4)
    plt.setp(ax_main.get_xticklabels(), visible=True)

    # Minor ticks at each pipe start chainage + the closing end chainage
    from matplotlib.ticker import FixedLocator, FuncFormatter
    pipe_starts = [seg['x_us'] for seg in segments]
    if segments:
        pipe_starts.append(segments[-1]['x_ds'])
    tick_to_label = {round(x, 4): f"{x:.1f}" for x in pipe_starts}
    ax_main.xaxis.set_minor_locator(FixedLocator(pipe_starts))
    ax_main.xaxis.set_minor_formatter(
        FuncFormatter(lambda x, pos: tick_to_label.get(round(x, 4), ''))
    )
    ax_main.tick_params(axis='x', which='minor', rotation=90, labelsize=secondary_font.pointSizeF(),
                        length=4, color='grey', labelcolor=secondary_text_color, labelfontfamily=secondary_font.family())
    ax_main.xaxis.set_tick_params(which='minor', pad=2)

    ax_main.tick_params(axis='both', which='major', labelfontfamily=main_font.family(),
                        length=4, color=main_line_color, labelcolor=main_text_color, labelsize=main_font.pointSizeF())
    for spine in ('left', 'right', 'top', 'bottom'):
        ax_main.spines[spine].set(color=main_line_color, linestyle=main_line_style, linewidth=main_line_width)

    # ---- Diameter axis -----------------------------------------------------
    diam_units = 'mm' if units == 'si' else 'in.'
    diam_labels = [f"{seg['diameter']:.0f} {diam_units}" for seg in segments]
    _add_label_axis(ax_diam, segments, diam_labels, font=tertiary_font, color=tertiary_text_color, ylabel='Diameter', **kwargs)
    ax_diam.set_xlim(*x_lim)
    plt.setp(ax_diam.get_xticklabels(), visible=False)

    # ---- Slope axis --------------------------------------------------------
    slope_labels = [f"{seg['slope_pct']:.2f}%" for seg in segments]
    _add_label_axis(ax_slope, segments, slope_labels, font=tertiary_font, color=tertiary_text_color, ylabel='Slope', **kwargs)
    ax_slope.set_xlim(*x_lim)

    fig.savefig(output_path, dpi=dpi, bbox_inches='tight')
    plt.close(fig)
    print(f'Saved: {output_path}')
