def get_gis_layers(gis_path):
    has_pyogrio = False
    has_fiona = False
    fiona = None
    try:
        import pyogrio

        has_pyogrio = True
    except ImportError:
        pyogrio = None

        # only need fiona if we can't import pyogrio
        try:
            import fiona

            has_fiona = True
        except:
            fiona = None

    if has_pyogrio:
        return pyogrio.list_layers(gis_path)[:, 0]
    elif has_fiona and fiona is not None:
        return fiona.listlayers(gis_path)
    else:
        raise ValueError('The pyogrio or fiona libraries are required for this operation. See '
                         'https://wiki.tuflow.com/QGIS_Intallation_with_OSGeo4W for install instructions.')
