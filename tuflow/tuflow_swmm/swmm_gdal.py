from osgeo import gdal, ogr

def delete_layer_features(filename, layername):
    ogr.UseExceptions()

    ogr_file = ogr.Open(filename, 1)
    ogr_layer = ogr_file.GetLayerByName(layername)

    for feature in ogr_layer:
        ogr_layer.DeleteFeature(feature.GetFID())

    ogr_file.SyncToDisk()

if __name__ == "__main__":
    filename = r"D:\models\TUFLOW\test_models\SWMM\OneStreet\TUFLOW\model\swmm\hec22_ex4-7_curved_vane.gpkg"
    layername = 'Links--Conduits'

    delete_layer_features(filename, layername)