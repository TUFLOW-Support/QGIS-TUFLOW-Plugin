"""
Tests for alg/hpc/create_project.py and the underlying ProjectConfig logic.

These tests exercise the core business logic of the Create TUFLOW Project tool,
including folder creation, GIS format helpers, projection commands, template
substitution, timestep handling, JSON persistence, and domain setup.
"""
import json
import os
import shutil
import tempfile
import unittest
from collections import OrderedDict
from pathlib import Path
from unittest.mock import patch, MagicMock

from qgis.core import QgsApplication, QgsCoordinateReferenceSystem

# Ensure a minimal QgsApplication exists before importing anything that
# touches QGIS internals.  If one is already running (e.g. inside QGIS)
# this is a no-op.
_app = QgsApplication.instance() or QgsApplication([], False)
if not QgsApplication.instance():
    _app.initQgis()

from tuflow.utils.project import ProjectConfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _default_settings(**overrides) -> OrderedDict:
    """Return a minimal set of TUFLOW settings for testing."""
    base = OrderedDict({
        'Solution Scheme': 'HPC',
        'Hardware': 'GPU',
        'SGS': 'ON',
        'Cell Size': 1.0,
        'Tutorial Model': 'OFF',
        'Projection': 'EPSG:28354',
        'GIS Format': 'GPKG',
        'GRID Format': 'TIF',
        'Start Time': 0.0,
        'End Time': 1.0,
        'Timestep': 1.0,
    })
    base.update(overrides)
    return base


def _make_project(tmpdir: str, name='test_proj', gis_format='gpkg',
                  hpcexe='/path/to/tuflow.exe', settings=None, domain='',
                  output_formats=None, crs_auth='EPSG:28354') -> ProjectConfig:
    """Convenience factory – does NOT call save_settings() so no QGIS project I/O."""
    if settings is None:
        settings = _default_settings()
    crs = QgsCoordinateReferenceSystem(crs_auth)
    return ProjectConfig(name, tmpdir, crs, gis_format, hpcexe, None,
                         domain, settings, output_formats, False)


# ---------------------------------------------------------------------------
# GIS format conversion helpers
# ---------------------------------------------------------------------------

class TestGisFormatHelpers(unittest.TestCase):

    def setUp(self):
        self.proj = _make_project(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(str(self.proj.folder), ignore_errors=True)

    # gis_format_extension -----------------------------------------------

    def test_gis_format_extension_0_returns_gpkg(self):
        self.assertEqual('gpkg', self.proj.gis_format_extension(0))

    def test_gis_format_extension_1_returns_shp(self):
        self.assertEqual('shp', self.proj.gis_format_extension(1))

    def test_gis_format_extension_2_returns_mif(self):
        self.assertEqual('mif', self.proj.gis_format_extension(2))

    # gis_extension_to_enum -----------------------------------------------

    def test_gis_extension_to_enum_gpkg(self):
        self.assertEqual(0, self.proj.gis_extension_to_enum('gpkg'))

    def test_gis_extension_to_enum_shp(self):
        self.assertEqual(1, self.proj.gis_extension_to_enum('shp'))

    def test_gis_extension_to_enum_mif(self):
        self.assertEqual(2, self.proj.gis_extension_to_enum('mif'))

    def test_gis_format_enum_round_trip(self):
        """Extension → enum → extension round-trip should be lossless."""
        for ext in ('gpkg', 'shp', 'mif'):
            enum = self.proj.gis_extension_to_enum(ext)
            self.assertEqual(ext, self.proj.gis_format_extension(enum))

    # gis_template_type ---------------------------------------------------

    def test_gpkg_uses_db_template_type(self):
        self.assertEqual('db', self.proj.gis_template_type)

    def test_shp_uses_sep_template_type(self):
        proj = _make_project(tempfile.mkdtemp(), gis_format='shp')
        self.assertEqual('sep', proj.gis_template_type)
        shutil.rmtree(str(proj.folder), ignore_errors=True)

    def test_mif_uses_sep_template_type(self):
        proj = _make_project(tempfile.mkdtemp(), gis_format='mif')
        self.assertEqual('sep', proj.gis_template_type)
        shutil.rmtree(str(proj.folder), ignore_errors=True)


# ---------------------------------------------------------------------------
# Projection command
# ---------------------------------------------------------------------------

class TestProjectionCommand(unittest.TestCase):

    def _proj(self, gis_format, tmpdir=None):
        d = tmpdir or tempfile.mkdtemp()
        return _make_project(d, gis_format=gis_format)

    def test_gpkg_projection_command_contains_filename(self):
        p = self._proj('gpkg')
        cmd = p.projection_command(False)
        # Should reference the named gpkg file followed by >> projection
        self.assertIn('test_proj_001.gpkg', cmd)
        self.assertIn('>> projection', cmd)
        shutil.rmtree(str(p.folder), ignore_errors=True)

    def test_gpkg_projection_command_uses_gpkg_prefix(self):
        p = self._proj('gpkg')
        cmd = p.projection_command(False)
        self.assertTrue(cmd.startswith('GPKG Projection =='))
        shutil.rmtree(str(p.folder), ignore_errors=True)

    def test_shp_projection_command_uses_shp_prefix(self):
        p = self._proj('shp')
        cmd = p.projection_command(False)
        self.assertTrue(cmd.startswith('SHP Projection =='))
        self.assertIn('projection.shp', cmd)
        shutil.rmtree(str(p.folder), ignore_errors=True)

    def test_mif_projection_command_uses_mi_prefix(self):
        p = self._proj('mif')
        cmd = p.projection_command(False)
        self.assertTrue(cmd.startswith('MI Projection =='))
        self.assertIn('projection.mif', cmd)
        shutil.rmtree(str(p.folder), ignore_errors=True)

    def test_gpkg_fv_projection_falls_back_to_shp(self):
        """GPKG projects should use SHP projection for FV (TUFLOW FV limitation)."""
        p = self._proj('gpkg')
        fv_cmd = p.projection_command(True)
        # FV mode with GPKG should degrade to SHP-style projection command
        self.assertNotIn('GPKG Projection ==', fv_cmd)
        shutil.rmtree(str(p.folder), ignore_errors=True)


# ---------------------------------------------------------------------------
# Command validation
# ---------------------------------------------------------------------------

class TestValidateCommand(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_hardware_valid_when_solution_scheme_is_hpc(self):
        p = _make_project(self.tmpdir, settings=_default_settings(**{'Solution Scheme': 'HPC'}))
        # Hardware validation requires Solution Scheme == HPC
        self.assertTrue(p._validate_command('Hardware', p.command_validation))

    def test_hardware_invalid_when_solution_scheme_is_classic(self):
        p = _make_project(self.tmpdir, settings=_default_settings(**{'Solution Scheme': 'Classic'}))
        self.assertFalse(p._validate_command('Hardware', p.command_validation))

    def test_sgs_valid_when_solution_scheme_is_hpc(self):
        p = _make_project(self.tmpdir, settings=_default_settings(**{'Solution Scheme': 'HPC'}))
        self.assertTrue(p._validate_command('SGS', p.command_validation))

    def test_sgs_invalid_when_solution_scheme_is_classic(self):
        p = _make_project(self.tmpdir, settings=_default_settings(**{'Solution Scheme': 'Classic'}))
        self.assertFalse(p._validate_command('SGS', p.command_validation))

    def test_command_with_no_validation_entry_is_always_valid(self):
        p = _make_project(self.tmpdir)
        # 'Cell Size' has no validation condition – should always be valid
        self.assertTrue(p._validate_command('Cell Size', p.command_validation))

    def test_unknown_command_is_always_valid(self):
        p = _make_project(self.tmpdir)
        self.assertTrue(p._validate_command('NonExistentCommand', p.command_validation))


# ---------------------------------------------------------------------------
# Timestep settings
# ---------------------------------------------------------------------------

class TestTimestepSettings(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_hpc_scheme_sets_timestep_initial_from_timestep(self):
        """When Solution Scheme is HPC, Timestep Initial should be set to Timestep value."""
        p = _make_project(self.tmpdir, settings=_default_settings(**{
            'Solution Scheme': 'HPC', 'Timestep': 2.5
        }))
        self.assertEqual(2.5, p.settings.get('Timestep Initial'))

    def test_hpc_scheme_marks_plain_timestep_as_invalid(self):
        """When HPC, the bare 'Timestep ==' command should be excluded from output."""
        p = _make_project(self.tmpdir, settings=_default_settings(**{'Solution Scheme': 'HPC'}))
        # Validation for 'Timestep' should point to Classic-only condition
        self.assertFalse(p._validate_command('Timestep', p.command_validation))

    def test_classic_scheme_keeps_timestep_valid(self):
        """When Classic, the bare 'Timestep ==' command should be kept."""
        p = _make_project(self.tmpdir, settings=_default_settings(**{'Solution Scheme': 'Classic'}))
        self.assertTrue(p._validate_command('Timestep', p.command_validation))

    def test_classic_scheme_marks_timestep_initial_as_invalid(self):
        """When Classic, 'Timestep Initial ==' should be excluded from output."""
        p = _make_project(self.tmpdir, settings=_default_settings(**{'Solution Scheme': 'Classic'}))
        self.assertFalse(p._validate_command('Timestep Initial', p.command_validation))


# ---------------------------------------------------------------------------
# Domain commands
# ---------------------------------------------------------------------------

class TestDomainCommands(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_domain_commands_contain_origin(self):
        domain = '100.0:200.0--45.0--1000.0:500.0'
        p = _make_project(self.tmpdir, domain=domain)
        result = p._domain_commands(domain)
        self.assertIn('Origin == 100.0 200.0', result)

    def test_domain_commands_contain_orientation_angle(self):
        domain = '100.0:200.0--45.0--1000.0:500.0'
        p = _make_project(self.tmpdir, domain=domain)
        result = p._domain_commands(domain)
        self.assertIn('Orientation Angle == 45.0', result)

    def test_domain_commands_contain_grid_size(self):
        domain = '100.0:200.0--45.0--1000.0:500.0'
        p = _make_project(self.tmpdir, domain=domain)
        result = p._domain_commands(domain)
        self.assertIn('Grid Size (X,Y) == 1000.0, 500.0', result)

    def test_zero_angle_domain(self):
        domain = '0.0:0.0--0.0--500.0:250.0'
        p = _make_project(self.tmpdir, domain=domain)
        result = p._domain_commands(domain)
        self.assertIn('Origin == 0.0 0.0', result)
        self.assertIn('Orientation Angle == 0.0', result)
        self.assertIn('Grid Size (X,Y) == 500.0, 250.0', result)


# ---------------------------------------------------------------------------
# Folder creation
# ---------------------------------------------------------------------------

class TestCreateFolders(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_hpc_folders_are_created(self):
        p = _make_project(self.tmpdir, hpcexe='/path/to/tuflow.exe')
        p.run_hpc = True
        p.create_folders()
        expected = [
            'bc_dbase',
            'check',
            os.path.join('model', 'gis'),
            os.path.join('model', 'grid'),
            'results',
            os.path.join('runs', 'log'),
        ]
        for folder in expected:
            with self.subTest(folder=folder):
                self.assertTrue((Path(self.tmpdir) / folder).is_dir(),
                                 f"Expected folder '{folder}' was not created")

    def test_no_hpc_folders_without_run_hpc(self):
        p = _make_project(self.tmpdir, hpcexe='')
        # run_hpc defaults to False when no exe is given
        p.create_folders()
        self.assertFalse((Path(self.tmpdir) / 'bc_dbase').exists())

    def test_create_folders_idempotent(self):
        """Calling create_folders twice should not raise."""
        p = _make_project(self.tmpdir, hpcexe='/path/to/tuflow.exe')
        p.run_hpc = True
        p.create_folders()
        p.create_folders()  # should not raise


# ---------------------------------------------------------------------------
# JSON persistence
# ---------------------------------------------------------------------------

class TestJsonPersistence(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_write_json_creates_tfsettings_file(self):
        p = _make_project(self.tmpdir)
        p.write_json()
        self.assertTrue((Path(self.tmpdir) / 'tfsettings.json').exists())

    def test_write_json_name_field(self):
        p = _make_project(self.tmpdir, name='my_project')
        p.write_json()
        with (Path(self.tmpdir) / 'tfsettings.json').open() as f:
            d = json.load(f)
        self.assertEqual('my_project', d['name'])

    def test_write_json_crs_field(self):
        p = _make_project(self.tmpdir, crs_auth='EPSG:28354')
        p.write_json()
        with (Path(self.tmpdir) / 'tfsettings.json').open() as f:
            d = json.load(f)
        self.assertEqual('EPSG:28354', d['crs'])

    def test_write_json_gis_format_field(self):
        p = _make_project(self.tmpdir, gis_format='gpkg')
        p.write_json()
        with (Path(self.tmpdir) / 'tfsettings.json').open() as f:
            d = json.load(f)
        self.assertEqual('gpkg', d['gis_format'])

    def test_write_json_hpcexe_field(self):
        p = _make_project(self.tmpdir, hpcexe='/some/tuflow.exe')
        p.write_json()
        with (Path(self.tmpdir) / 'tfsettings.json').open() as f:
            d = json.load(f)
        # Path is stored in posix format; on Linux this is unchanged
        self.assertIn('tuflow.exe', d['hpcexe'])

    def test_write_json_raises_when_folder_does_not_exist(self):
        p = _make_project('/nonexistent/path/that/does/not/exist')
        with self.assertRaises(Exception):
            p.write_json()

    def test_from_json_round_trip_name(self):
        p = _make_project(self.tmpdir, name='round_trip')
        p.write_json()
        with (Path(self.tmpdir) / 'tfsettings.json').open() as f:
            p2 = ProjectConfig.from_json(f)
        self.assertEqual(p.name, p2.name)

    def test_from_json_round_trip_crs(self):
        p = _make_project(self.tmpdir)
        p.write_json()
        with (Path(self.tmpdir) / 'tfsettings.json').open() as f:
            p2 = ProjectConfig.from_json(f)
        self.assertEqual(p.crs.authid(), p2.crs.authid())

    def test_from_json_round_trip_gis_format(self):
        p = _make_project(self.tmpdir, gis_format='gpkg')
        p.write_json()
        with (Path(self.tmpdir) / 'tfsettings.json').open() as f:
            p2 = ProjectConfig.from_json(f)
        self.assertEqual(p.gis_format, p2.gis_format)

    def test_from_json_round_trip_hpcexe(self):
        p = _make_project(self.tmpdir, hpcexe='/some/path/tuflow.exe')
        p.write_json()
        with (Path(self.tmpdir) / 'tfsettings.json').open() as f:
            p2 = ProjectConfig.from_json(f)
        self.assertEqual(str(p.hpcexe), str(p2.hpcexe))


# ---------------------------------------------------------------------------
# Template variable substitution
# ---------------------------------------------------------------------------

class TestReplaceVariables(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_model_name_substituted(self):
        p = _make_project(self.tmpdir, name='my_model')
        result = p._replace_variables('File == ${model_name}_001.gpkg')
        self.assertIn('my_model_001.gpkg', result)

    def test_gis_format_substituted_uppercase(self):
        p = _make_project(self.tmpdir, gis_format='gpkg')
        result = p._replace_variables('GIS Format == ${gis_format}')
        self.assertIn('GIS Format == GPKG', result)

    def test_gis_ext_substituted_lowercase(self):
        p = _make_project(self.tmpdir, gis_format='gpkg')
        result = p._replace_variables('File == data.${gis_ext}')
        self.assertIn('data.gpkg', result)


# ---------------------------------------------------------------------------
# Control file template setup (setup_cf_templates)
# ---------------------------------------------------------------------------

class TestSetupCfTemplates(unittest.TestCase):
    """Tests for the full template-processing pipeline triggered by setup_cf_templates."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _make_hpc_project(self, name='test_proj', gis_format='gpkg', **setting_overrides):
        p = _make_project(self.tmpdir, name=name, gis_format=gis_format,
                          settings=_default_settings(**setting_overrides))
        p.run_hpc = True
        p.run_fv = False
        return p

    def _tcf_content(self, name='test_proj') -> str:
        tcf = Path(self.tmpdir) / 'runs' / f'{name}_001.tcf'
        self.assertTrue(tcf.exists(), f'TCF file not found: {tcf}')
        return tcf.read_text()

    # --- file creation ---

    def test_tcf_file_is_created(self):
        p = self._make_hpc_project()
        p.setup_cf_templates()
        self.assertTrue((Path(self.tmpdir) / 'runs' / 'test_proj_001.tcf').exists())

    def test_tgc_file_is_created(self):
        p = self._make_hpc_project()
        p.setup_cf_templates()
        self.assertTrue((Path(self.tmpdir) / 'model' / 'test_proj_001.tgc').exists())

    def test_tbc_file_is_created(self):
        p = self._make_hpc_project()
        p.setup_cf_templates()
        self.assertTrue((Path(self.tmpdir) / 'model' / 'test_proj_001.tbc').exists())

    def test_ecf_file_is_created(self):
        p = self._make_hpc_project()
        p.setup_cf_templates()
        self.assertTrue((Path(self.tmpdir) / 'model' / 'test_proj_001.ecf').exists())

    def test_bc_dbase_csv_is_created(self):
        p = self._make_hpc_project()
        p.setup_cf_templates()
        self.assertTrue((Path(self.tmpdir) / 'bc_dbase' / 'bc_dbase.csv').exists())

    # --- content: model name substitution ---

    def test_tcf_contains_model_name_in_spatial_database(self):
        p = self._make_hpc_project(name='mymodel')
        p.setup_cf_templates()
        content = (Path(self.tmpdir) / 'runs' / 'mymodel_001.tcf').read_text()
        self.assertIn('mymodel_001.gpkg', content)

    def test_tcf_model_name_appears_in_control_file_references(self):
        p = self._make_hpc_project(name='proj42')
        p.setup_cf_templates()
        content = (Path(self.tmpdir) / 'runs' / 'proj42_001.tcf').read_text()
        # The geometry control file should reference the named TGC
        self.assertIn('proj42_001.tgc', content)

    # --- content: solution scheme (HPC) ---

    def test_tcf_hpc_solution_scheme_written(self):
        p = self._make_hpc_project(**{'Solution Scheme': 'HPC'})
        p.setup_cf_templates()
        content = self._tcf_content()
        self.assertIn('Solution Scheme == HPC', content)

    def test_tcf_hpc_uses_timestep_initial_not_timestep(self):
        p = self._make_hpc_project(**{'Solution Scheme': 'HPC', 'Timestep': 3.0})
        p.setup_cf_templates()
        content = self._tcf_content()
        # Timestep Initial == should be present
        self.assertIn('Timestep Initial ==', content)
        # The bare 'Timestep ==' active line should NOT be present for HPC
        active_timestep_lines = [
            l for l in content.split('\n')
            if l.strip().startswith('Timestep ==')
        ]
        self.assertEqual(0, len(active_timestep_lines),
                         'HPC TCF should not contain an active "Timestep ==" line')

    def test_tcf_hpc_timestep_initial_value_matches_timestep_setting(self):
        p = self._make_hpc_project(**{'Solution Scheme': 'HPC', 'Timestep': 5.0})
        p.setup_cf_templates()
        content = self._tcf_content()
        self.assertIn('Timestep Initial == 5.0', content)

    def test_tcf_hpc_hardware_setting_written(self):
        p = self._make_hpc_project(**{'Solution Scheme': 'HPC', 'Hardware': 'GPU'})
        p.setup_cf_templates()
        content = self._tcf_content()
        self.assertIn('Hardware == GPU', content)

    def test_tcf_hpc_sgs_setting_written(self):
        p = self._make_hpc_project(**{'Solution Scheme': 'HPC', 'SGS': 'ON'})
        p.setup_cf_templates()
        content = self._tcf_content()
        self.assertIn('SGS == ON', content)

    # --- content: solution scheme (Classic) ---

    def test_tcf_classic_solution_scheme_written(self):
        p = self._make_hpc_project(**{'Solution Scheme': 'Classic'})
        p.setup_cf_templates()
        content = self._tcf_content()
        self.assertIn('Solution Scheme == Classic', content)

    def test_tcf_classic_uses_timestep_not_timestep_initial(self):
        p = self._make_hpc_project(**{'Solution Scheme': 'Classic', 'Timestep': 10.0})
        p.setup_cf_templates()
        content = self._tcf_content()
        self.assertIn('Timestep == 10.0', content)
        active_ti_lines = [
            l for l in content.split('\n')
            if l.strip().startswith('Timestep Initial ==')
        ]
        self.assertEqual(0, len(active_ti_lines),
                         'Classic TCF should not contain an active "Timestep Initial ==" line')

    def test_tcf_classic_hardware_line_removed(self):
        """Hardware command is HPC-only; it should not appear in a Classic TCF."""
        p = self._make_hpc_project(**{'Solution Scheme': 'Classic'})
        p.setup_cf_templates()
        content = self._tcf_content()
        active_hw_lines = [
            l for l in content.split('\n')
            if l.strip().startswith('Hardware ==')
        ]
        self.assertEqual(0, len(active_hw_lines),
                         'Classic TCF should not contain an active "Hardware ==" line')

    # --- content: GIS format ---

    def test_tcf_gis_format_written_uppercase(self):
        p = self._make_hpc_project(gis_format='gpkg')
        p.setup_cf_templates()
        content = self._tcf_content()
        self.assertIn('GIS Format == GPKG', content)

    def test_tcf_shp_gis_format_written(self):
        p = _make_project(self.tmpdir, gis_format='shp',
                          settings=_default_settings(**{'GIS Format': 'SHP'}))
        p.run_hpc = True
        p.run_fv = False
        p.setup_cf_templates()
        content = (Path(self.tmpdir) / 'runs' / 'test_proj_001.tcf').read_text()
        self.assertIn('GIS Format == SHP', content)

    # --- setup_cf_templates is idempotent (does not overwrite existing files) ---

    def test_setup_cf_templates_does_not_overwrite_existing_files(self):
        p = self._make_hpc_project()
        p.setup_cf_templates()
        tcf = Path(self.tmpdir) / 'runs' / 'test_proj_001.tcf'
        original_content = tcf.read_text()
        # Manually alter the file, then call again
        tcf.write_text(original_content + '\n! custom line')
        p.setup_cf_templates()
        # The custom line should still be there (not overwritten)
        self.assertIn('! custom line', tcf.read_text())


# ---------------------------------------------------------------------------
# ProjectConfig.valid flag
# ---------------------------------------------------------------------------

class TestProjectConfigValid(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_valid_is_true_when_name_provided(self):
        p = _make_project(self.tmpdir, name='some_name')
        self.assertTrue(p.valid)

    def test_valid_is_false_when_name_is_empty(self):
        p = _make_project(self.tmpdir, name='')
        self.assertFalse(p.valid)


if __name__ == '__main__':
    unittest.main()
