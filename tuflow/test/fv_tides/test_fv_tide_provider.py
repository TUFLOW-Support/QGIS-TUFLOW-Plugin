from pathlib import Path
from unittest import TestCase

from tuflow.fvbc_tide_provider import FVBCTideProvider


class TestFVTideProvider(TestCase):

    def test_load(self):
        gis_fpath = Path(__file__).parent / 'data' / '2d_ns_Cudgen_004_OceanBoundary_L.shp'
        nc_fpath = Path(__file__).parent / 'data' / 'Cudgen_Tide.nc'
        prov = FVBCTideProvider(nc_fpath, gis_fpath)
        self.assertTrue(prov.is_fv_tide_bc())
        prov.close()

    def test_get_timesteps(self):
        gis_fpath = Path(__file__).parent / 'data' / '2d_ns_Cudgen_004_OceanBoundary_L.shp'
        nc_fpath = Path(__file__).parent / 'data' / 'Cudgen_Tide.nc'
        prov = FVBCTideProvider(nc_fpath, gis_fpath)
        timesteps = prov.get_timesteps()
        self.assertEqual(3073, len(timesteps))
        timesteps = prov.get_timesteps('datetime')
        self.assertEqual(3073, len(timesteps))
        prov.close()

    def test_get_ch_points(self):
        gis_fpath = Path(__file__).parent / 'data' / '2d_ns_Cudgen_004_OceanBoundary_L.shp'
        nc_fpath = Path(__file__).parent / 'data' / 'Cudgen_Tide.nc'
        prov = FVBCTideProvider(nc_fpath, gis_fpath)
        points = prov.get_ch_points('Ocean')
        self.assertEqual(12, len(points))
        prov.close()

    def test_get_section(self):
        gis_fpath = Path(__file__).parent / 'data' / '2d_ns_Cudgen_004_OceanBoundary_L.shp'
        nc_fpath = Path(__file__).parent / 'data' / 'Cudgen_Tide.nc'
        prov = FVBCTideProvider(nc_fpath, gis_fpath)
        time = prov.get_timesteps()[5]
        section = prov.get_section('Ocean', time, data_at_ends=True)
        self.assertEqual(13, section.shape[0])
        time = prov.get_timesteps('datetime')[20]
        section = prov.get_section('Ocean', time)
        self.assertEqual(12, section.shape[0])
        prov.close()

    def test_get_time_series(self):
        gis_fpath = Path(__file__).parent / 'data' / '2d_ns_Cudgen_004_OceanBoundary_L.shp'
        nc_fpath = Path(__file__).parent / 'data' / 'Cudgen_Tide.nc'
        prov = FVBCTideProvider(nc_fpath, gis_fpath)
        time_series = prov.get_time_series('Ocean', 0)
        self.assertTrue(time_series.any())
        prov.close()

    def test_multiple_boundaries(self):
        gis_fpath = Path(__file__).parent / 'data' / '2d_ns_Open_Boundary_001_L.shp'
        nc_fpath = Path(__file__).parent / 'data' / 'GoC_Tide_20100301_20100501_AEST.nc'
        prov = FVBCTideProvider(nc_fpath, gis_fpath)
        self.assertEqual(['Eastern_Boundary', 'Western_Boundary'], prov.get_labels())
        prov.close()

    def test_get_chainages_multi(self):
        gis_fpath = Path(__file__).parent / 'data' / '2d_ns_Open_Boundary_001_L.shp'
        nc_fpath = Path(__file__).parent / 'data' / 'GoC_Tide_20100301_20100501_AEST.nc'
        prov = FVBCTideProvider(nc_fpath, gis_fpath)
        points = prov.get_ch_points('Eastern_Boundary')
        self.assertEqual(60, points.shape[0])
        points = prov.get_ch_points('Western_Boundary')
        self.assertEqual(121, points.shape[0])
        prov.close()
