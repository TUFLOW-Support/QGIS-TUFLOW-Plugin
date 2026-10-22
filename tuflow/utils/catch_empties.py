from osgeo import ogr

from .gdal_ import ogr_create


class TuflowCatchEmptyFiles:

    def __init__(self, gis_format, projection_wkt):
        self.empty_types = [
            TuflowEmptyType('2d_rp', 'R', gis_format, projection_wkt),
            TuflowEmptyType('2d_im', 'L', gis_format, projection_wkt)
        ]

    def write(self, dir_path):
        for et in self.empty_types:
            et.write_empty(dir_path)


class TuflowEmptyType:

    def __init__(self, name, geom, gis_format, projection_wkt):
        self.name = name
        self.geom = geom
        self.gis_format = gis_format
        self.projection_wkt = projection_wkt

    def count(self):
        return len(self.geom)

    def get_schema(self):
        return EmptySchemas.get_schema(self.name)

    def write_empty(self, dir_path):
        schema = self.get_schema()

        if 'pts' in self.name:
            table_name = f'{self.name[:-4]}_empty_pts'
        else:
            table_name = f'{self.name}_empty'

        if self.gis_format == 'mif':
            uris = [(f'{dir_path / table_name}.{self.gis_format} >> {table_name}', self.geom[0])]
        elif self.gis_format == 'gpkg':
            uris = []
            for g in self.geom:
                uris.append((f'{dir_path / table_name}.{self.gis_format} >> {table_name}_{g}', g))
        else:
            uris = []
            for g in self.geom:
                uris.append((f'{dir_path / table_name}_{g}.{self.gis_format} >> {table_name}_{g}', g))

        for uri, geom in uris:
            geom_type = ogr.wkbPoint
            if geom == 'P':
                geom_type = ogr.wkbPoint
            elif geom == 'L':
                geom_type = ogr.wkbLineString
            elif geom == 'R':
                geom_type = ogr.wkbPolygon
            ogr_create(uri, geom_type, schema, self.projection_wkt)


class Schema:

    def __init__(self, name, type_, width=None, prec=None):
        self.name = name
        self.type = type_
        self.width = width
        self.prec = prec


class EmptySchemas:

    @staticmethod
    def get_schema(name):
        if hasattr(EmptySchemas, f'_{name}'):
            return getattr(EmptySchemas, f'_{name}')()

    @staticmethod
    def _2d_rp():
        return [
            Schema('NOT USED', ogr.OFTString, 36),
        ]

    @staticmethod
    def _2d_im():
        return [
            Schema('ID', ogr.OFTString, 254),
            Schema('Length', ogr.OFTReal, 11, 3),
            Schema('res_char1', ogr.OFTString, 100),
            Schema('res_char2', ogr.OFTString, 100),
            Schema('res_int1', ogr.OFTInteger64, 10),
            Schema('res_int2', ogr.OFTInteger64, 10),
            Schema('res_float1', ogr.OFTReal, 11, 3),
            Schema('res_float2', ogr.OFTReal, 11, 3),
            Schema('res_float3', ogr.OFTReal, 11, 3),
            Schema('res_float4', ogr.OFTReal, 11, 3),
        ]
