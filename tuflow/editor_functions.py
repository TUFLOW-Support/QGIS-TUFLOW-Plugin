"""
This file contains functions to provide custom dialogs for property editors in QGIS aiming to make editing individual
features moe inuitive by providing drop-down boxes or other controls.

This file has to be in the root plugin folder for QGIS to find the function. To keep this file clean, please limit the
file to forward calls to a more appropriate location.

The only way I have been able to get this to work so far has been to us ethe layer options "Provide code in this dialog"
add "from tuflow.editor_functions import editor_swmm_links_conduits"
This will ask them about running macros and works after the first time called.

These functions are specified using the QgsEditFormConfig functions "setInitCodeSource" and "setInitFunction" and
  are applied using the layer function "setEditFormConfig"
https://qgis.org/pyqgis/master/core/QgsEditFormConfig.html#qgis.core.QgsEditFormConfig.setInitCodeSource
https://qgis.org/pyqgis/master/core/Qgis.html#qgis.core.Qgis.AttributeFormPythonInitCodeSource
"""
#import os
#import sys
#sys.path.append(os.path.dirname(__file__))

from tuflow.tuflow_swmm.qgis.editor_forms.swmm_links_conduits_editor import swmm_links_conduits_editor


def editor_swmm_links_conduits(dialog, layer, feature):
    swmm_links_conduits_editor(dialog, layer, feature)


# Didn't help - thought he would help QGIS see the function
# globals()['editor_swmm_links_conduits'] = editor_swmm_links_conduits
