This tool sets SWMM junction attributes Ymax (Maximum depth), Ysur (maximum surge depth), and Apond (area of ponding). This tool supports edit-in-place so you can modify an existing layer.

The recommended settings for junctions within the 2D domain depends on whether the node receives flow from a subcatchment and whether and how the node is connected to the 2D domain.

## Input layers
Input Layer - The features to set the attributes for. Defaults to the selected layer when entering the dialog (not shown for edit-in-place).
Input subcatchments layers - These layers are used to identify nodes that receive subcatchments flows. They must be named Hydrology--Subcatchments following TUFLOW-SWMM GeoPackage conventions.
Input BC Connections - These layers are used to identify nodes that are connected to 2D domains but do not have an inlet connection.

## General options
Maximum Depth Option (Ymax) can either be set to initialize Ymax to 0.0 or leave as-is when doing edit in place. Note these options may be overriden for nodes connected to inlets.

Nodes receiving subcatchment flows can either use settings normally applied or force subcatchment outlets to use 0.0 for Ysur and Apond (turns off ponding). When ponding is turned off, node surcharging is reported as "flooding" to SWMM and is immediately transferred to the 2D domain regardless of the 2D domain water level. Ponding at these nodes will consider the 2D water level when determining discharge but will use the inlet outflow to control flooding discharge which may throttle subcatchment flows to the 2D domain. If using ponding, consider using the command "Maximum Inlet Ponded Depth" if the WSE in nodes connected to subcatchments becomes unreasonable due to throttling the outflow (should have similiar WSE in node and 2D).

Ysur = 0.0 (forced)

Apond = 0.0 (forced)

## Junction nodes not receiving subcatchment flows connected to a 2D Domain
When nodes do not receive flows from subcatchments, it is recommended to allow ponding (set Apond >0). This will allow the head in the node (including pressure head) as a water level. If the water level in the node exceeds the water level in the 2D domain, there will be a flow from the 1D domain to 2D domain.

### Junction nodes connected to 2D with an inlet
At inlets, users can choose to set the maximum depth (Ymax) based on the global setting or use the inlet elevation minus the node elevation. 

When nodes are connected through an inlet, either Ysur (surcharge dpeth) or Apond (area of ponding) can be used to allow the pressure head to exceed Ymax. Using a positive area of ponding may enhance stability. Generally, Apond would represent the manhole shaft or a small area. A larger area may enhance model stability but may artificially attenuate discharges. If Apond is non-zero, Ysur is ignored.

Ysur = 0.0 if ponding otherwise higher than expected depths to prevent flooding

Apond = Manhole area

### Junction nodes connected with a HX boundary (no inlet)
When nodes are connected through an HX boundary such as culverts through an embankment, it is recommended to set apond (area of ponding) to the approximate area of connected cells. A larger area of ponding may improve stability but may artificially attenuate discharges. This will depend on the model cell size. Generally, a typical value is chosen that is reasonable for most of the connections and any signficantly larger or smaller structures can be modified on an individual basis. 

Ysur = 0.0

Apond = Typical area of connected 2D cells (higher values may aid stability).

### Junctions not connected to 2D domains
Flood losses would be lost from the model resulting in mass losses and inaccurate results. Prevent by allowing ponding or making surge elevation high.
#### Option #1
Ysur = higher than expected node depths

Apond = 0.0
#### or Option #2
Ysur = 0.0 (ignored)

Apond = (positive number)

**Note: It is recommended that Ymax be set to 0.0 for all junctions. SWMM will set Ymax to higest soffit of connected conduits.**

## Limitations
This tool will set junction attributes based on generic rules and individual nodes may need to be modified.