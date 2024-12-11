from osgeo import gdal


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
