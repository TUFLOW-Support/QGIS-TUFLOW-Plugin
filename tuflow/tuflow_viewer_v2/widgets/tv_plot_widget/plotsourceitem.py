from copy import deepcopy

import numpy as np

from ...tvinstance import get_viewer_instance


class PlotSourceItem:

    def __init__(self, id_: str, plot_type: str, output_id: str, data_type: str, loc: str, domain: str, geom: list, is_tv_layer: bool,
                 colour: str, sel_type: str, static: bool, chan_type: str):
        self.id = id_
        self.plot_type = plot_type
        self.output_id = output_id
        self.data_type = data_type
        self.loc = loc
        self.domain = domain
        self.geom = geom
        self.range = None
        self.is_tv_layer = is_tv_layer
        self.colour = colour
        self.sel_type = sel_type
        self.static = static
        self.chan_type = chan_type
        self.output = get_viewer_instance().output(output_id)
        self.label = ''
        self.averaging_method = None
        self._branch = 0
        self.branch_count = 1
        self.xdata = np.array([])
        self.ydata = np.array([])
        self.channel_ids = []
        self.node_ids = []
        self.is_pipes = False
        self.is_pits = False
        self.is_flow_regime = False
        self.level_boundaries = []
        self.qgis_data_min = None
        self.qgis_data_max = None
        self.qgis_data_colour_curve = None
        self.qgis_data_colour_interp_method = 'linear'
        self.feedback_context = ''
        self.xaxis_name = ''
        self.xaxis_units = ''
        self.yaxis_name = ''
        self.units = ''
        self.use_label_in_tooltip = False
        self.ready_for_plotting = False

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}: {self.id}>'

    def __eq__(self, other):
        if not isinstance(other, PlotSourceItem):
            return False
        # ignore branch for equality
        return self.id.split('/', 5)[:5] == other.id.split('/', 5)[:5]

    def __lt__(self, other):
        if not isinstance(other, PlotSourceItem):
            return NotImplemented
        return self.id < other.id

    def __le__(self, other):
        if not isinstance(other, PlotSourceItem):
            return NotImplemented
        return self.id <= other.id

    def __gt__(self, other):
        if not isinstance(other, PlotSourceItem):
            return NotImplemented
        return self.id > other.id

    def __ge__(self, other):
        if not isinstance(other, PlotSourceItem):
            return NotImplemented
        return self.id >= other.id

    def __hash__(self):
        return hash(self.id)

    def __deepcopy__(self, memo):
        # override so we don't deepcopy "output"
        ret = PlotSourceItem(self.id, self.plot_type, self.output_id, self.data_type, self.loc, self.domain, self.geom,
                             self.is_tv_layer, self.colour, self.sel_type, self.static, self.chan_type)
        for attr in dir(self):
            if not attr.startswith('_') and not callable(getattr(self, attr)) and attr != 'output':
                setattr(ret, attr, deepcopy(getattr(self, attr), memo))
        ret.tooltip = self.tooltip
        return ret

    @property
    def branch(self) -> int:
        return self._branch

    @branch.setter
    def branch(self, value: int):
        self._branch = value
        data = self.id.split('/', 5)
        if len(data) >= 5:
            data[4] = str(value)
        else:
            data.append(str(value))
        self.id = '/'.join(data)

    @staticmethod
    def tooltip(src_item: 'PlotSourceItem', location_id: str, position: tuple[float, float], *args, **kwargs) -> str:
        string = ''
        if src_item.output is not None:
            string = src_item.output.name
        if location_id:
            string = f'{string}\n{location_id}' if string else location_id
        elif src_item.use_label_in_tooltip:
            string = f'{string}\n{src_item.label}'
        if not src_item.xaxis_name:
            src_item.xaxis_name = 'X'
        if not src_item.yaxis_name:
            src_item.yaxis_name = 'Y'
        if position:
            pos0 = f'{position[0]:.3g}'
            pos1 = f'{position[1]:.3g}' if isinstance(position[1], float) else position[1]
            string = f'{string}\n{src_item.data_type_pretty(src_item.xaxis_name)}: {pos0}' if string else f'{src_item.data_type_pretty(src_item.xaxis_name)}: {pos0}'
            if src_item.xaxis_units:
                string = f'{string} {src_item.xaxis_units}'
            string = f'{string}\n{src_item.data_type_pretty(src_item.yaxis_name)}: {pos1}' if string else f'{src_item.data_type_pretty(src_item.yaxis_name)}: {pos1}'
            if src_item.units:
                string = f'{string} {src_item.units}'
        else:
            string = f'{string}\n{src_item.data_type_pretty(src_item.yaxis_name)}'
        return string

    def fuzzy_match(self, other: 'PlotSourceItem'):
        parts1 = self.id.split('/', 5)
        if len(parts1) >= 5:
            comp1 = '/'.join(parts1[:4]).lower()
        else:
            comp1 = self.id.lower()
        parts2 = other.id.split('/', 5)
        if len(parts2) >= 5:
            comp2 = '/'.join(parts2[:4]).lower()
        else:
            comp2 = other.id.lower()
        return comp1 == comp2

    def data_type_pretty(self, name: str):
        data_type_pretty = name
        if self.averaging_method and name == self.data_type:
            avg_method_comp = self.averaging_method.split('&')
            avg_method_str = avg_method_comp[0]
            if '?' in avg_method_str:
                name_, dir_ = avg_method_str.split('?')
                dir_ = dir_.split('=')[1]
                avg_method_str = f'{name_} (from {dir_})'
            avg_method_str = '{0} - {1}'.format(avg_method_str, ', '.join(avg_method_comp[1:]))
            data_type_pretty = f'{self.data_type}: {avg_method_str}'
        return data_type_pretty

    def export_label(self) -> str:
        if self.output is None:
            return f'{self.data_type_pretty(self.data_type)}'
        if self.branch_count == 1:
            return f'{self.output.name}/{self.data_type_pretty(self.data_type)}'
        else:
            return f'{self.output.name}/{self.data_type_pretty(self.data_type)}/Branch {self.branch + 1}'
