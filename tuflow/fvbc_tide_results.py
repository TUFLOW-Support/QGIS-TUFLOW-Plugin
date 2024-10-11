from tuflow.TUFLOW_results import ResData
from tuflow.fvbc_tide_provider import FVBCTideProvider


class FVBC_TideResults(ResData):

    def __init__(self):
        super().__init__()
        self.provider = None
        self.has_reference_time = True
        self.gis_line_fpath = ''
        self.gis_point_fpath = ''
        self.formatVersion = 2
        self.uri = ''
        self.lp_ids = []
        self.supports_new_profile_plot = True

    def Load(self, nc_fpath, gis_fpath, use_local_time):
        try:
            self.provider = FVBCTideProvider(nc_fpath, gis_fpath, use_local_time)
        except Exception as e:
            return True, str(e)
        if not self.provider.is_fv_tide_bc():
            return True, 'The input file(s) do not look like a recognised FV tide boundary condition.'
        if self.provider.is_empty():
            return True, 'The input file(s) do not contain any data.'
        self.displayname = self.provider.display_name
        self.reference_time = self.provider.reference_time
        self.gis_line_fpath = gis_fpath
        self.gis_point_fpath = f'point?crs={self.provider.get_crs()}&field=ID:string&field=Ch:real&field=Type:string&field=Source:string'
        self.times = self.provider.get_timesteps()
        self.uri = f'FVBC_TideResults://{nc_fpath}::{gis_fpath}::{use_local_time}'
        return False, ''

    @property
    def gis_line_layer_name(self):
        return self.provider.gis_name

    @gis_line_layer_name.setter
    def gis_line_layer_name(self, value):
        pass

    @property
    def gis_point_layer_name(self):
        return f'{self.provider.gis_name}_pts'

    @gis_point_layer_name.setter
    def gis_point_layer_name(self, value):
        pass

    @property
    def gis_region_layer_name(self):
        return ''

    @gis_region_layer_name.setter
    def gis_region_layer_name(self, value):
        pass

    def ids(self):
        return self.provider.get_labels()

    def pointResultTypesTS(self):
        return ['Water Level']

    def lineResultTypesTS(self):
        return []

    def regionResultTypesTS(self):
        return []

    def lineResultTypesLP(self):
        return ['Water Level']

    def timeSteps(self, zero_time=None):
        return self.provider.get_timesteps()

    def LP_getStaticData(self):
        return False, ''

    def LP_getData(self, dat_type, time, dt_tol):
        return False, ''

    def LP_getConnectivity(self, *args, **kwargs):
        self.lp_ids = args[:]

    def getLongPlotXY(self, type, time):
        return None, None

    def getTimeSeriesProfile(self, id_, type_, time):
        if type_.lower() != 'water level':
            return None, None
        if time is None:
            return None, None
        section = self.provider.get_section(id_, time, data_at_ends=True)
        return section[:, 0], section[:, 1]

    def getTSData(self, id, dom, res, geom):
        if res.lower() != 'water level':
            return False, [], ''
        try:
            id, ind = id.rsplit('_', 1)
            int(ind)
        except (ValueError, TypeError):
            return False, [], 'Invalid ID'
        data = self.provider.get_time_series(id, ind)
        return True, data[:,1], ''

    def getGeometry(self, label):
        return self.provider.get_geometry(label)
