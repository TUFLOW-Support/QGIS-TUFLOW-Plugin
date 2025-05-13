from qgis.PyQt.QtWidgets import QApplication, QComboBox, QDialog, QWidget


shape_geom_types = {
    'CIRCULAR':
        {'Geom1': 'Diameter'},
    'FORCE_MAIN':
        {'Geom1': 'Diameter',
         'Geom2': 'Roughness', },
    'FILLED_CIRCULAR':
        {'Geom1': 'Diameter',
         'Geom2': 'Sediment Depth', },
    'RECT_CLOSED':
        {'Geom1': 'Full Height',
         'Geom2': 'Top Width', },
    'RECT_OPEN':
        {'Geom1': 'Full Height',
         'Geom2': 'Top Width', },
    'TRAPEZOIDAL':
        {'Geom1': 'Full Height',
         'Geom2': 'Base Width',
         'Geom3': 'Left Slope',
         'Geom4': 'Right Slope', },
}
geometry_controls = {
    'Geom1': [
        'txt_geom1',
        'edt_geom1'
    ],
    'Geom2': [
        'txt_geom2',
        'edt_geom2'
    ],
    'Geom3': [
        'txt_geom3',
        'edt_geom3'
    ],
    'Geom4': [
        'txt_geom4',
        'edt_geom4'
    ],
    'Size Code': [
        'txt_size_code',
        'edt_size_code',
    ]
}


def setup_qgis():
    pass


def cbx_shape_changed(dialog, cbx_shape, index):
    shape = cbx_shape.currentText()
    if shape not in shape_geom_types:
        raise ValueError('Unrecognized shape')

    geom_options = shape_geom_types[shape]

    for geom_variable, geom_controls in geometry_controls.items():
        if geom_variable in geom_options:
            # First control has text
            control1 = dialog.findChild(QWidget, geom_controls[0])
            control1.setText(geom_options[geom_variable])
            for control in geom_controls:
                window = dialog.findChild(QWidget, control)
                window.show()
        else:
            for control in geom_controls:
                window = dialog.findChild(QWidget, control)
                window.hide()


def swmm_links_conduits_editor(dialog, layer, feature):
    geom = feature.geometry()

    shape = feature['xsec_XsecType']
    cbx_shape = dialog.findChild(QComboBox, 'cbx_shape')
    for shape_type in shape_geom_types.keys():
        cbx_shape.addItem(shape_type)

    cbx_shape.setCurrentIndex(cbx_shape.findText(shape.upper()))
    cbx_shape_changed(dialog, cbx_shape, cbx_shape.currentIndex())

    cbx_shape.currentIndexChanged.connect(lambda x: cbx_shape_changed(dialog, cbx_shape, x))

    if not layer.isEditable():
        cbx_shape.setEnabled(False)
