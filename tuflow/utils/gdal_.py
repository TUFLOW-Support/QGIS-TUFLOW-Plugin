import re
from pathlib import Path

from osgeo import gdal, osr, ogr


def get_driver_name_from_extension(driver_type: str, ext: str) -> str:
    if not ext:
        return

    ext = ext.lower()
    if ext[0] == '.':
        ext = ext[1:]

    for i in range(gdal.GetDriverCount()):
        drv = gdal.GetDriver(i)
        md = drv.GetMetadata_Dict()
        if ('DCAP_RASTER' in md and driver_type == 'raster') or ('DCAP_VECTOR' in md and driver_type == 'vector'):
            if not drv.GetMetadataItem(gdal.DMD_EXTENSIONS):
                continue
            driver_extensions = drv.GetMetadataItem(gdal.DMD_EXTENSIONS).split(' ')
            for drv_ext in driver_extensions:
                if drv_ext.lower() == ext:
                    if ext.lower() == 'mif':
                        return 'Mapinfo File'  # not sure if bug but it seems like you have to use "Mapinfo File" for MIF instead of "MapInfo File"
                    return drv.ShortName


def get_driver_by_extension(driver_type, ext):
    if not ext:
        return

    ext = ext.lower()
    if ext[0] == '.':
        ext = ext[1:]

    for i in range(gdal.GetDriverCount()):
        drv = gdal.GetDriver(i)
        md = drv.GetMetadata_Dict()
        if ('DCAP_RASTER' in md and driver_type == 'raster') or ('DCAP_VECTOR' in md and driver_type == 'vector'):
            if not drv.GetMetadataItem(gdal.DMD_EXTENSIONS):
                continue
            driver_extensions = drv.GetMetadataItem(gdal.DMD_EXTENSIONS).split(' ')
            for drv_ext in driver_extensions:
                if drv_ext.lower() == ext:
                    return drv.ShortName


def ogr_create(uri, geom_type, schema, projection_wkt, settings=None):
    db, lyrname = uri.split(' >> ')
    sr = osr.SpatialReference(projection_wkt)

    fmt = get_driver_by_extension('vector', Path(db).suffix)
    driver = ogr.GetDriverByName(fmt)
    if Path(db).exists() and fmt == 'GPKG':
        datasource = driver.Open(db, 1)
    elif Path(db).exists():
        datasource = driver.Open(db, 1)
        if datasource is not None:
            datasource.DeleteLayer(0)
        elif fmt == 'Mapinfo File':
            try:
                err = driver.DeleteDataSource(db)
                if err != ogr.OGRERR_NONE:
                    gis_manual_delete(db, fmt)
            except Exception as e:
                print(f'Error: {e}')
            datasource = driver.CreateDataSource(db)
    else:
        Path(db).parent.mkdir(parents=True, exist_ok=True)
        datasource = driver.CreateDataSource(db)

    options = ['OVERWRITE=YES'] if fmt == 'GPKG' else []

    lyr = datasource.CreateLayer(lyrname, sr, geom_type, options)

    for field in schema:
        f = ogr.FieldDefn(field.name, field.type)
        if field.width is not None:
            f.SetWidth(field.width)
        if field.prec is not None:
            f.SetPrecision(field.prec)
        lyr.CreateField(f)

    datasource, lyr = None, None


def gis_manual_delete(file, fmt):
    """Manually delete a GIS file - can be required if GIS file is corrupt -> OGR won't delete it then."""
    file = Path(file)
    if fmt == 'Mapinfo File':
        for file_ in file.parent.glob(f'{file.stem}.*'):
            if file_.suffix.lower() in ['.mif', '.mid']:
                file.unlink()
    elif fmt == 'ESRI Shapefile':
        for file_ in file.parent.glob(f'{file.stem}.*'):
            if file_.suffix.lower() in ['.shp', '.prj', '.dbf', '.shx', '.sbn', '.sbx']:
                file.unlink()

