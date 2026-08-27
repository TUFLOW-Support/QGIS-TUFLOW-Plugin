Convert XPSWMM GIS Inlet Layer to SWMM

This tool converts an XPSWMM GIS layer with 2D connectivity information for use with TUFLOW-SWMM.

The tool works on discharges computed from the equation: Q=coefficient*depth<sup>exponent</sup>

## Usage
To export the GIS layer required from XPSWMM or the XPSWMM Viewer:

1. Right click on the nodes layer and choose "Export to GIS."
2. Expand the tree folders "Hydraulics Node\HDR Node Data"
3. Select Node 2D Inflow Capture Flag, Gound Elevation(Spill Crest), 2D Inflow Capture Coefficient, and 2D Inflow Capture Exponent
4. Remove the paranthesis from "Ground Elevation(Spill Crest)." **Required for some versions of QGIS**
4.  Set the GIS filename
5. Click Export

The inlets require a  name for each combination of coefficient and exponent that must be added to the GIS layer.

Once the layer is setup, you can run the tool and select the parameters for the appropriate fields. The Ground elevation should be used for the "Inlet elevation field." The CRS should match your TUFLOW-SWMM project.

## Outputs
This processing tool generates a GIS layer that can be used to with the "Read GIS SWMM Inlet Usage" command to link SWMM inlets to a TUFLOW 2D model.






