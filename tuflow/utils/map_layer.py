from PyQt5.QtXml import QDomDocument
from qgis.core import QgsReadWriteContext, Qgis, QgsWkbTypes, QgsUnitTypes

from ..compatibility_routines import Path


def clean_data_source(data_source: str) -> str:
    if '|layername=' in data_source:
        ds = '|'.join(data_source.split('|')[:2])
    else:
        ds = '|'.join(data_source.split('|')[:1])
    split = [x.strip() for x in ds.split('|')]
    if len(split) > 1 and Path(split[0]).suffix.lower() != '.gpkg':
        ds = split[0]
    return ds


def file_from_data_source(data_source: str) -> Path:
    return Path(data_source.split('|')[0])


def layer_name_from_data_source(data_source: str) -> str:
    if '|layername=' in data_source:
        return data_source.split('|')[1].split('=')[1]
    else:
        return Path(clean_data_source(data_source)).stem


def copy_layer_style(iface, src_lyr, dest_lyr):
    """Copies styling from one layer to another."""

    if src_lyr is None or dest_lyr is None:
        return

    # create dom document to store layer style
    doc = QDomDocument("styles")
    element = doc.createElement("maplayer")
    errorCopy = ''
    errorRead = ''
    src_lyr.writeStyle(element, doc, errorCopy, QgsReadWriteContext())

    # set style to new layer
    dest_lyr.readStyle(element, errorRead, QgsReadWriteContext())

    # refresh map and legend
    dest_lyr.triggerRepaint()
    iface.layerTreeView().refreshLayerSymbology(dest_lyr.id())


def set_vector_temporal_properties(lyr, enable: bool = True):
    try:
        fld = lyr.fields()['Datetime']
        lyr.temporalProperties().setIsActive(enable)
        if not enable:
            return
        lyr.temporalProperties().setMode(Qgis.VectorTemporalMode.FeatureDateTimeInstantFromField)
        lyr.temporalProperties().setLimitMode(Qgis.VectorTemporalLimitMode.IncludeBeginIncludeEnd)
        lyr.temporalProperties().setStartField('Datetime')
        lyr.temporalProperties().setEndField('Datetime')
        try:
            from ..tuflow_results_gpkg import ResData_GPKG
        except ImportError:
            return
        db = file_from_data_source(lyr.dataProvider().dataSourceUri())
        dt = -1
        res = ResData_GPKG()
        try:
            err, msg = res.Load(db)
        except Exception as e:
            return
        try:
            if lyr.geometryType() == QgsWkbTypes.PointGeometry:
                res_type = res.pointResultTypesTS()
                if res_type:
                    res_type = res_type[0]
                else:
                    return
            elif lyr.geometryType() == QgsWkbTypes.LineGeometry:
                res_type = res.lineResultTypesTS()
                if res_type:
                    res_type = res_type[0]
                else:
                    return
            elif lyr.geometryType() == QgsWkbTypes.PolygonGeometry:
                res_type = res.regionResultTypesTS()
                if res_type:
                    res_type = res_type[0]
                else:
                    return
            else:
                return
            dt = res.timestep_interval(lyr.name(), res_type)
        except Exception as e:
            pass
        finally:
            res.close()
        if dt > 0:
            sec = dt * 3600.
            lyr.temporalProperties().setFixedDuration(sec)
            lyr.temporalProperties().setDurationUnits(QgsUnitTypes.TemporalUnit.TemporalSeconds)
    except Exception as e:
        pass
