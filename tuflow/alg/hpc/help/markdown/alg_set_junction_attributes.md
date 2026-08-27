## Overview
This tool sets SWMM junction attributes Ymax (Maximum depth), Ysur (maximum surge depth), and Apond (area of ponding). This tool supports edit-in-place so you can modify an existing layer.

The recommended settings for junctions within the 2D domain depends on whether the node receives flow from a subcatchment and whether and how the node is connected to the 2D domain.

## Input layers
Input Layer - The features to set the attributes for. Defaults to the selected layer when entering the dialog (not shown for edit-in-place).
Input subcatchments layers - These layers are used to identify nodes that receive subcatchments flows. They must be named Hydrology--Subcatchments following TUFLOW-SWMM GeoPackage conventions.
Input BC Connections - These layers are used to identify nodes that are connected to 2D domains but do not have an inlet connection.

## General options

### Maximum Depth Option (Ymax)
Recommend using 0.0 for all nodes

### Nodes receiving subcatchment flows
Recommend "based on options selected below"
For models using catchments routed to pipe networks, recommend adding command "Maximum Inlet Ponded Depth" with a value between 0.0-0.1 to the TUFLOW-SWMM Control File (tscf).

Turning off ponding forces the water level in the node to never exceed YMax underrepresenting the head at the node if set to 0.0 and can cause instabilities if YMax is based on the ground elevation. Therefore, it is recommend for all nodes to use ponding even if they are connected to subcatchments. The "Maximum Inlet Ponded Depth" helps prevent excessive energy heads in 1D nodes receiving subcatchment flows. 

## Nodes connected to 2D without inlets (through embankment culvert)
Recommend converting to storage nodes with size approximate to the area of connected HX cells.

If junction nodes are used, recommend using a ponding value approximately the area of the connected HX cells but storage nodes more accurately reflect storage in the system and improve stability.

### Junction nodes connected to 2D with inlets (underground pipe network)
Recommend:
"Use global option" for option"
Ysur = 0.0
Apond = Typical area of manholes

If converting from an XPSWMM model, the "Set to inlet elevation - node elevation", may more closely align with previous results which may necessitate using this option if changes in results are to be avoided. However, this configuration is generally less stable as SWMM does not account for storage in the manhole or shaft between the top of connected conduits and the inlet (ground) elevation.

### Nodes without a 2D connection (underground pipe network)
Recommend either of the options below:

1. Ysur = higher than expected node depths (say 100.0) and Apond = 0.0
2. Ysur = 0.0 (ignored if Apond > 0.0) and Apond = (Typical area of manholes)

Flood losses would be lost from the model resulting in mass losses and inaccurate results. Prevent by allowing ponding or making surge elevation high.

## Limitations
This tool will set junction attributes based on generic rules and individual nodes may need to be modified.