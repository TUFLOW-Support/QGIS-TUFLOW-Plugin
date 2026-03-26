import logging
import typing
from collections import OrderedDict

from qgis.PyQt.QtGui import QColor
import numpy as np

if typing.TYPE_CHECKING:
    # noinspection PyUnusedImports
    from .pyqtgraph_subclass.custom_view_box import CustomViewBox


class ShiftedColour:

    def __init__(self, name: str):
        self.name = name
        self.used_shifts = set()
        self.used_colours = {}
        self._based_used = False
        self._max = 200  # inclusive
        self._min = 0  # exclusive
        self._inc = 25
        self._base = 100
        self._extra_shift = None

    def shift(self) -> str:
        if not self._based_used:
            self._based_used = True
            return self.name
        for shift in range(self._base + self._inc, self._max + self._inc, self._inc):
            if shift not in self.used_shifts:
                return self._shift(shift)
        for shift in range(self._base - self._inc, self._min, -self._inc):
            if shift not in self.used_shifts:
                return self._shift(shift)
        # all used, start cycle again
        if self._extra_shift is None:
            self._extra_shift = ShiftedColour(self.name)
        return self._extra_shift.shift()

    def shift_backward(self, name: str) -> str:
        if self._extra_shift is not None:
            return name  # don't bother shifting backwards if we've started cycling
        if name == self.name:  # nowhere to go back to
            return name
        if name not in self.used_colours:
            return name  # shouldn't get here
        shift = self.used_colours[name]
        if shift > self._base:
            new_shift = shift - self._inc
        elif shift < self._base:
            new_shift = shift + self._inc
            if new_shift >= self._base:
                new_shift = self._base
                while new_shift + self._inc < self._max:
                    new_shift += self._inc
        else:
            return name  # shouldn't get here as equals check done above between name and self.name
        if new_shift == self._base:
            self._based_used = True
            return self.name
        return self._shift(new_shift)

    def release(self, name: str):
        if self._extra_shift is not None and name in self._extra_shift.used_colours:
            self._extra_shift.release(name)
            if len(self._extra_shift.used_colours) == 0:
                self._extra_shift = None
            return
        if name == self.name:
            self._based_used = False
            return
        if name in self.used_colours:
            shift = self.used_colours.pop(name)
            self.used_shifts.remove(shift)

    def reset(self):
        self._based_used = False
        self.used_shifts.clear()
        self.used_colours.clear()
        self._extra_shift = None

    def _shift(self, shift: int):
        self.used_shifts.add(shift)
        c = QColor(self.name).lighter(shift).name()
        self.used_colours[c] = shift
        return c


class ColourAllocator:

    def __init__(self, base_colours: list[str]):
        self._base_colours = base_colours
        self._available = OrderedDict((c, False) for c in base_colours)
        self._shifted_colours = {}
        self._shift_increment = 25
        self._unique_colours = set(base_colours)

    def next_colour(self, unique: bool = False) -> str:
        for c, in_use in self._available.items():
            if not in_use:
                self._available[c] = True
                return c
        # fallback random
        if unique:
            while True:
                c = QColor(*np.random.randint(0, 255, 3)).name()
                if c not in self._unique_colours:
                    self._unique_colours.add(c)
                    return c
        return QColor(*np.random.randint(0, 255, 3)).name()

    def shift_colour(self, name: str, vb: 'CustomViewBox') -> str:
        if vb not in self._shifted_colours:
            self._shifted_colours[vb] = {}
        shifted_colours = self._shifted_colours[vb]
        if name not in shifted_colours:
            shifted_colours[name] = ShiftedColour(name)
        return shifted_colours[name].shift()

    def shift_colour_backward(self, name: str, shifted_name: str, vb: 'CustomViewBox') -> str:
        if vb not in self._shifted_colours:
            return name
        shifted_colours = self._shifted_colours[vb]
        if name not in shifted_colours:
            return name
        return shifted_colours[name].shift_backward(shifted_name)

    def release(self, name: str):
        if name in self._available:
            self._available[name] = False
        for shifted_colours in self._shifted_colours.values():
            if name in shifted_colours:
                del shifted_colours[name]
        if name not in self._base_colours and name in self._unique_colours:
            self._unique_colours.remove(name)

    def release_shifted(self, name: str, shifted_name: str, vb: 'CustomViewBox'):
        if vb not in self._shifted_colours:
            return
        shifted_colours = self._shifted_colours[vb]
        if name in shifted_colours:
            shifted_colours[name].release(shifted_name)

    def reset(self):
        for k in self._available:
            self._available[k] = False
            if k not in self._base_colours and k in self._unique_colours:
                self._unique_colours.remove(k)
        self._shifted_colours.clear()
