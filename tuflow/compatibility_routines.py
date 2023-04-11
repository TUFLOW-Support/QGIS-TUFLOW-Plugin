"""
Module to fill the gap for QGIS versions that don't yet have Python 3.9+

Copies routines largely from the convert_tuflow_model_gis_format suite and modifies where required to
make compatible. These routines are just too useful sometimes to re-write in the plugin (so only do this as
required).

Hopefully this will not grow too big and can be deprecated (and removed) sometime in the near future (fingers crossed).
"""

import os
import re
import shutil
import sqlite3
try:
    from pathlib import Path
except ImportError:
    from pathlib_ import Path_ as Path

from osgeo import ogr, gdal, osr


GIS_SHP = 'Esri Shapefile'
GIS_MIF = 'Mapinfo File'
GIS_GPKG = 'GPKG'
GRID_ASC = 'AAIGrid'
GRID_FLT = 'EHdr'
GRID_GPKG = 'GPKG'
GRID_TIF = 'GTiff'
GRID_NC = 'netCDF'


class GPKG:
    """A class that helps with GPKGs."""

    def __init__(self, gpkg_path):
        self.gpkg_path = str(gpkg_path)

    def glob(self, pattern):
        """Do a glob search of the database for tables matching the pattern."""

        p = pattern.replace('*', '.*')
        for lyr in self.layers():
            if re.findall(p, lyr, flags=re.IGNORECASE):
                yield lyr

    def layers(self):
        """Return the GPKG layers in the database."""

        res = []

        if not os.path.exists(self.gpkg_path):
            return res

        conn = sqlite3.connect(self.gpkg_path)
        cur = conn.cursor()

        try:
            cur.execute(f"SELECT table_name FROM gpkg_contents;")
            res = [x[0] for x in cur.fetchall()]
        except Exception:
            pass
        finally:
            cur.close()

        return res

    def geometry_type(self, layer_name):
        conn = sqlite3.connect(self.gpkg_path)
        cur = conn.cursor()
        try:
            cur.execute(f"SELECT geometry_type_name FROM gpkg_geometry_columns where table_name = '{layer_name}';")
            res = [x[0] for x in cur.fetchall()][0]
        except Exception:
            pass
        finally:
            res = ''
            cur.close()

        return res

    def __contains__(self, item):
        """Returns a bool on whether a certain layer is in the database."""

        if not os.path.exists(self.gpkg_path):
            return False

        conn = sqlite3.connect(self.gpkg_path)
        cur = conn.cursor()
        res = None
        try:
            cur.execute(f"SELECT table_name FROM gpkg_contents WHERE table_name='{item}';")
            res = [x[0] for x in cur.fetchall()]
        except:
            pass
        finally:
            cur.close()

        return bool(res)


def gdal_error_handler(err_class: int, err_num: int, err_msg: str) -> None:
    """Custom python gdal error handler - if there is a failure, need to let GDAL finish first."""

    errtype = {
            gdal.CE_None:'None',
            gdal.CE_Debug:'Debug',
            gdal.CE_Warning:'Warning',
            gdal.CE_Failure:'Failure',
            gdal.CE_Fatal:'Fatal'
    }
    err_msg = err_msg.replace('\n',' ')
    err_class = errtype.get(err_class, 'None')
    if err_class.lower() == 'failure':
        global b_gdal_error
        b_gdal_error = True

    # skip these warning msgs
    if 'Normalized/laundered field name:' in err_msg:
        return
    if 'width 256 truncated to 254' in err_msg:
        return

    print('GDAL {0}'.format(err_class.upper()))
    print('{1} Number: {0}'.format(err_num, err_class))
    print('{1} Message: {0}'.format(err_msg, err_class))


def init_gdal_error_handler() -> None:
    """Initialise GDAL error handler"""

    global b_gdal_error
    b_gdal_error = False
    gdal.PushErrorHandler(gdal_error_handler)


def gdal_error() -> bool:
    """Returns a bool if there was a GDAL error or not"""

    global b_gdal_error
    try:
        return b_gdal_error
    except NameError:  # uninitialised
        init_gdal_error_handler()
        return gdal_error()


def get_database_name(file):
    """Strip the file reference into database name >> layer name."""

    if re.findall(r'\s+>>\s+', str(file)):
        return re.split(r'\s+>>\s+', str(file), 1)
    else:
        if Path(file).suffix.upper() == '.PRJ':
            file = Path(file).with_suffix('.shp')
        return [str(file), Path(file).stem]


def is_multi_part(feat=None, lyr=None):
    MULTIPART = [ogr.wkbMultiPoint, ogr.wkbMultiLineString, ogr.wkbMultiPolygon]
    if feat is not None and feat.geometry() is not None:
        return ogr_basic_geom_type(feat.geometry().GetGeometryType(), False) in MULTIPART

    if lyr is not None:
        return bool([f for f in lyr if ogr_basic_geom_type(f.geometry().GetGeometryType(), False) in MULTIPART])

    return False


def ogr_format(file, no_ext_is_mif=False, no_ext_is_gpkg=False):
    """Returns the OGR driver name based on the extension of the file reference."""

    db, layer = get_database_name(file)
    if Path(db).suffix.upper() in ['.SHP', '.PRJ']:
        return GIS_SHP
    if Path(db).suffix.upper() in ['.MIF', '.MID']:
        return GIS_MIF
    if Path(db).suffix.upper() == '.GPKG':
        return GIS_GPKG
    if Path(db).suffix.upper() == '' and no_ext_is_mif:
        return GIS_MIF
    if Path(db).suffix.upper() == '' and no_ext_is_gpkg:
        return GIS_GPKG

    if not Path(db).suffix.upper():
        raise Exception(f'Error: Unable to determine Vector format from blank file extension: {db}')

    raise Exception(f'Error: Vector format not supported by TUFLOW: {Path(db).suffix}')


def ogr_format_2_ext(ogr_format):
    """Convert OGR driver name to a file extension."""

    if ogr_format == GIS_SHP:
        return '.shp'
    if ogr_format == GIS_MIF:
        return '.mif'
    if ogr_format == GIS_GPKG:
        return '.gpkg'


def ogr_basic_geom_type(geom_type, force_single_part=True):
    """Convert OGR geometry type to a basic type e.g. PointM -> Point"""

    while geom_type - 1000 > 0:
        geom_type -= 1000

    if force_single_part:
        if geom_type == ogr.wkbMultiPoint:
            geom_type = ogr.wkbPoint
        elif geom_type == ogr.wkbMultiLineString:
            geom_type = ogr.wkbLineString
        elif geom_type == ogr.wkbMultiPolygon:
            geom_type = ogr.wkbPolygon

    return geom_type


def gis_manual_delete(file, fmt):
    """Manually delete a GIS file - can be required if GIS file is corrupt -> OGR won't delete it then."""

    file = Path(file)
    if fmt == GIS_MIF:
        for file in file.parent.re(rf'{re.escape(file.stem)}\.(mif|mid)', flags=re.IGNORECASE):
            file.unlink()
    elif fmt == GIS_SHP:
        for file in file.parent.re(rf'{re.escape(file.stem)}\.(shp|prj|dbf|shx|sbn|sbx)', flags=re.IGNORECASE):
            file.unlink()


def copy_field_defn(field_defn):
    """Copy field defn to new object."""

    new_field_defn = ogr.FieldDefn()
    new_field_defn.SetName(field_defn.GetName())
    new_field_defn.SetType(field_defn.GetType())
    new_field_defn.SetSubType(field_defn.GetSubType())
    new_field_defn.SetJustify(field_defn.GetJustify())
    new_field_defn.SetWidth(field_defn.GetWidth())
    new_field_defn.SetPrecision(field_defn.GetPrecision())
    new_field_defn.SetNullable(field_defn.IsNullable())
    new_field_defn.SetUnique(field_defn.IsUnique())
    new_field_defn.SetDefault(field_defn.GetDefault())
    new_field_defn.SetDomainName(field_defn.GetDomainName())

    return new_field_defn


def sanitise_field_defn(field_defn, fmt):
    """
    For MIF output only.
    MIF doesn't support all OGR field types, so convert fields to a simpler format that is compatible in MIF.
    """

    SHP_MAX_FIELD_NAME_LEN = 10

    if fmt == GIS_MIF:
        if field_defn.type in [ogr.OFTInteger64, ogr.OFTIntegerList, ogr.OFTInteger64List]:
            field_defn.type = ogr.OFTInteger
        elif field_defn.type in [ogr.OFTRealList]:
            field_defn.type = ogr.OFTReal
        elif field_defn.type in [ogr.OFTStringList, ogr.OFTWideString, ogr.OFTWideStringList]:
            field_defn.type = ogr.OFTString

    if fmt == GIS_SHP:
        if len(field_defn.name) > SHP_MAX_FIELD_NAME_LEN:
            field_defn.name = field_defn.name[:SHP_MAX_FIELD_NAME_LEN]

    return field_defn


def tuflow_type_requires_feature_iter(layername):
    """
    Returns the indexes of fields that could require a file copy e.g. for 1d_xs.

    This will require manual feature iteration and copy in the OGR copy routine.
    """

    req_iter_types = {
        r'^1d_nwk[eb]?_': [10],
        r'^1d_pit_': [3],
        r'^1d_(xs|tab|xz|bg|lc|cs|hw)_': [0],
        r'^1d_na_': [0]
    }

    for pattern, indexes in req_iter_types.items():
        if re.findall(pattern, layername, flags=re.IGNORECASE):
            return indexes

    return []


def globify(infile, wildcards):
    """Converts TUFLOW wildcards (variable names, scenario/event names) to '*' for glob pattern."""

    infile = str(infile)
    if wildcards is None:
        return infile

    for wc in wildcards:
        infile = re.sub(wc, '*', infile, flags=re.IGNORECASE)
    if re.findall(r'\*\*(?![\\/])', infile):
        infile = re.sub(re.escape(r'**'), '*', infile)

    return infile


def copy_file(parent_file, rel_path, output_parent, wildcards):
    """Copy file routine that will also expand glob patterns."""

    file_dest = None
    rel_path_ = globify(rel_path, wildcards)
    copy_count = None
    try:
        if output_parent is not None:
            for copy_count, file_src in enumerate(parent_file.parent.glob(rel_path_)):
                file_src = file_src.resolve()
                rp = os.path.relpath(file_src, parent_file.parent)
                file_dest = (output_parent.parent / rp).resolve()
                file_dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(file_src, file_dest)
    except Exception as e:
        raise Exception(f'Error: {e}')

    if copy_count is not None:
        return file_dest
    else:
        return None


def copy_file2(file_src, file_dest):
    """More basic copy file routine with a different signature. Does not expand glob."""

    try:
        file_dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(file_src, file_dest)
    except Exception as e:
        raise Exception(f'Error: {e}')


def ogr_copy(src_file, dest_file, geom=None, settings=None, **kwargs):
    """
    Copy vector file from one format to another (or the same format).

    If converting from a MIF file, geom should be specified to indicate which geometry type to copy across.

    Some TUFLOW layers (1d_nwk, 1d_tab) contain references to files, these will also be copied and references
    updated if required (output layer can be in a different folder if it's going to a centralised database).
    """

    db_in, lyrname_in = get_database_name(src_file)
    db_out, lyrname_out = get_database_name(dest_file)

    prj_only = False
    sr = None
    if Path(db_in).suffix.upper() == '.PRJ' and not Path(db_in).with_suffix('.shp').exists() and Path(db_out).suffix.upper() == '.SHP':
        if settings and settings.force_projection:
            sr = osr.SpatialReference()
            sr.ImportFromWkt(settings.projection_wkt)
            if not Path(db_out).parent.exists():
                Path(db_out).parent.mkdir(parents=True)
            ds = ogr.GetDriverByName('ESRI Shapefile').CreateDataSource(str(Path(db_out).with_suffix('.shp')))
            if ds is None or gdal_error():
                raise Exception(f'Error: Failed to open: {db_out}')
            lyr = ds.CreateLayer(Path(db_in).stem, sr, ogr.wkbPoint)
            if lyr is None or gdal_error():
                raise Exception(f'Error: Failed to create layer: {Path(db_in).stem}')
            ds, lyr = None, None
        else:
            copy_file2(Path(db_in), Path(db_out).with_suffix('.prj'))
        return
    elif Path(db_in).suffix.upper() == '.PRJ' and not Path(db_in).with_suffix('.shp').exists():
        if settings and settings.force_projection:
            sr = osr.SpatialReference()
            sr.ImportFromWkt(settings.projection_wkt)
        else:
            with open(db_in, 'r') as f:
                try:
                    sr = osr.SpatialReference(f.readline())
                except Exception as e:
                    raise Exception(f'Error reading spatial reference.\n{e}')
        prj_only = True
    elif Path(db_in).suffix.upper() == '.PRJ':
        db_in = str(Path(db_in).with_suffix('.shp'))
    elif Path(db_in).suffix.upper() == '.MID':
        db_in = str(Path(db_in).with_suffix('.mif'))

    lyr_in = None
    fmt_in = ogr_format(db_in)
    if not prj_only:
        driver_in = ogr.GetDriverByName(fmt_in)
        datasource_in = driver_in.Open(db_in)
        if gdal_error():
            if settings is not None:
                settings.errors = True
            raise Exception(f'Error: Failed to open {db_in}')
        lyr_in = datasource_in.GetLayer(lyrname_in)
        if gdal_error():
            if settings is not None:
                settings.errors = True
            raise Exception(f'Error: Failed to open layer {lyrname_in}')

    fmt_out = ogr_format(db_out)
    driver_out = ogr.GetDriverByName(fmt_out)
    if Path(db_out).exists() and fmt_out == GIS_GPKG:
        datasource_out = driver_out.Open(db_out, 1)
    elif Path(db_out).exists():
        datasource_out = driver_out.Open(db_out, 1)
        if datasource_out is not None:
            datasource_out.DeleteLayer(0)
        elif fmt_out == GIS_MIF:
            try:
                err = driver_out.DeleteDataSource(db_out)
                if err != ogr.OGRERR_NONE:
                    gis_manual_delete(db_out, fmt_out)
            except Exception as e:
                if settings is not None:
                    settings.errors = True
                raise Exception(f'Error: Could not overwrite existing file: {db_out}')
            datasource_out = driver_out.CreateDataSource(db_out)
    else:
        Path(db_out).parent.mkdir(parents=True, exist_ok=True)
        datasource_out = driver_out.CreateDataSource(db_out)
    if gdal_error():
        if settings is not None:
            settings.errors = True
        raise Exception(f'Error: Failed to open: {db_out}')

    options = ['OVERWRITE=YES'] if fmt_out == GIS_GPKG else []
    geom_type = 0
    if lyr_in is not None:
        geom_type = geom if geom is not None else lyr_in.GetGeomType()
    elif prj_only:
        geom_type = ogr.wkbPoint

    file_indexes = tuflow_type_requires_feature_iter(lyrname_in)  # is there a file reference in the features
    wildcards = settings.wildcards if settings else []

    # if fmt_out == GIS_MIF or fmt_in == GIS_MIF or prj_only or file_indexes or is_multi_part(lyr=lyr_in):
    if settings is not None and settings.force_projection:
        sr = osr.SpatialReference()
        sr.ImportFromWkt(settings.projection_wkt)
    elif sr is None and lyr_in is not None:
        sr = lyr_in.GetSpatialRef()
    lyr_out = datasource_out.CreateLayer(lyrname_out, sr, geom_type, options)
    if gdal_error():
        if settings is not None:
            settings.errors = True
        raise Exception(f'Error: Failed to create layer {lyrname_out}')
    if prj_only:
        fielDefn = ogr.FieldDefn('ID', ogr.OFTString)
        lyr_out.CreateField(fielDefn)
    else:
        layer_defn = lyr_in.GetLayerDefn()
        for i in range(0, layer_defn.GetFieldCount()):
            fieldDefn = copy_field_defn(layer_defn.GetFieldDefn(i))
            fieldDefn = sanitise_field_defn(fieldDefn, fmt_out)
            lyr_out.CreateField(fieldDefn)
        if fmt_out == GIS_GPKG:
            datasource_out.StartTransaction()
        for feat in lyr_in:
            if geom and ogr_basic_geom_type(feat.geometry().GetGeometryType()) != geom_type:
                continue

            if is_multi_part(feat) and not kwargs.get('explode_multipart') == False:  # double negative, but the default is to explode
                geom_parts = [x for x in feat.GetGeometryRef()]
            else:
                geom_parts = [feat.GetGeometryRef()]

            for gp in geom_parts:
                new_feat = ogr.Feature(lyr_out.GetLayerDefn())
                panMap = list(range(feat.GetFieldCount()))
                new_feat.SetFromWithMap(feat, True, panMap)
                new_feat.SetGeometry(gp)

                if not kwargs.get('copy_associated_files') == False:  # double negative, but default should be to copy
                    for i in file_indexes:  # check if there's a file that needs to be copied e.g. 1d_xs.csv
                        if feat[i]:
                            if '|' in feat[i]:
                                op, file = [x.strip() for x in feat[i].split('|', 1)]
                            else:
                                op, file = None, feat[i]
                            dest_file = (Path(db_out).parent / file).resolve()
                            dest_file2 = Path(dest_file)
                            if settings:
                                rel_path = os.path.relpath((Path(db_in).parent / file).resolve(), settings.root_folder)
                                dest_file2 = (settings.output_folder / rel_path).resolve()
                            if dest_file == dest_file2:
                                copy_file(Path(db_in), file, Path(db_out), wildcards)
                            else:  # this means that we are using a grouped database that will screw up copy - req correction
                                rel_path = os.path.relpath(db_in, settings.root_folder)
                                fake_db_out = (Path(settings.output_folder) / rel_path).resolve()
                                copy_file(Path(db_in), file, fake_db_out, wildcards)
                                if op is None:
                                    new_feat[i] = os.path.relpath(dest_file2, Path(db_out).parent)
                                else:
                                    new_feat[i] = f'{op} | {os.path.relpath(dest_file2, Path(db_out).parent)}'

                lyr_out.CreateFeature(new_feat)

        if fmt_out == GIS_GPKG:
            datasource_out.CommitTransaction()

    datasource_out, lyr_out = None, None
    datasource_in, lyr_in = None, None