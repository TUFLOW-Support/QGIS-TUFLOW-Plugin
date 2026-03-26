from datetime import datetime

from qgis.core import QgsRasterLayer, QgsContrastEnhancement

from ..temporal_controller_widget import temporal_controller

try:
    from netCDF4 import Dataset
    has_nc = True
except ImportError:
    Dataset = 'Dataset'
    has_nc = False


class NetCDFGridLayer(QgsRasterLayer):

    def __init__(self, uri: str, name: str, provider: str, times: list[float], reference_time: datetime):
        super().__init__(uri, name, provider)
        self.times = times
        self.reference_time = reference_time
        self._nc_file = ':'.join(uri.split(':')[1:-1]).strip('"')
        self._lyr_name = uri.split(':')[-1]
        self.static = len(self.times) == 0
        self._block_renderer_changed_sig = False
        self.min = None
        self.max = None
        self.rendererChanged.connect(self.renderer_changed)

    def close(self):
        try:
            self.rendererChanged.disconnect(self.renderer_changed)
        except RuntimeError:
            pass

    def update_band_from_time(self, time: datetime):
        band = self.get_band_from_time(time)
        self.update_band(band)

    def get_band_from_time(self, time):
        if self.static:
            return 1
        i = 1
        for i, time_ in enumerate(self.times):
            if abs((time_ - time).total_seconds()) < 1:
                return i + 1
            elif time_ > time:
                if abs((time_ - time).total_seconds()) > 1:
                    return i
                return i + 1
        return i

    def update_band(self, band_number: int | None):
        if band_number is None:
            return
        self.set_raster_renderer_to_band(band_number)

    def set_raster_renderer_to_band(self, band_number: int):
        if self.static:
            band_number = 1
        if self._curr_band == band_number:
            return
        self._curr_band = band_number
        self.update_renderer(band_number, self.min, self.max)
        self._block_renderer_changed_sig = False

    def renderer_changed(self):
        if self._block_renderer_changed_sig:
            return
        if self.min is None:
            self.min, self.max = self.get_min_max_values(self.renderer())
            return
        time = temporal_controller.currentTime()
        self.update_renderer(self.get_band_from_time(time) if time is not None else 1, self.min, self.max)

    def get_min_max_values(self, renderer):
        min_, max_ = None, None
        if renderer.type() == 'singlebandpseudocolor':
            min_ = renderer.classificationMin()
            max_ = renderer.classificationMax()
        elif renderer.type() == 'singlebandgray':
            min_ = renderer.contrastEnhancement().minimumValue()
            max_ = renderer.contrastEnhancement().maximumValue()
        return min_, max_

    def update_renderer(self, band_number: int, min_: float, max_: float):
        self._block_renderer_changed_sig = True
        renderer = self.renderer().clone()
        if renderer.type() == 'singlebandpseudocolor':
            renderer.setInputBand(band_number)
            renderer.setClassificationMin(min_)
            renderer.setClassificationMax(max_)
            self.setRenderer(renderer)
            self.triggerRepaint()
        elif renderer.type() == 'singlebandgray':
            dtype = self.renderer().dataType(band_number)
            renderer.setInputBand(band_number)
            enhancement = QgsContrastEnhancement(dtype)
            enhancement.setContrastEnhancementAlgorithm(QgsContrastEnhancement.StretchToMinimumMaximum, True)
            enhancement.setMinimumValue(min_)
            enhancement.setMaximumValue(max_)
            renderer.setContrastEnhancement(enhancement)
            self.setRenderer(renderer)
            self.triggerRepaint()
        elif renderer.type() in ['paletted', 'contour', 'singlecolor', 'hillshade']:
            renderer.setInputBand(band_number)
            self.setRenderer(renderer)
            self.triggerRepaint()
        self._block_renderer_changed_sig = False
