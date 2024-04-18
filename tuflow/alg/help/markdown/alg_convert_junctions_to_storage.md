This tool converts junctions attached to HX connections (embankment culverts) to storage nodes. This is necessary to accurately represent storage in the system as HX cells do not track storage. The use of storage nodes also improves model stability.

## Usage
Specify the junction layer with junctions that you want to convert to storage nodes, the bc layers that have the CN and HX lines to identify the nodes connected to HX boundaries, shape information for the storage node, and output layers.

Pyramidal storage shapes with 0.0 inverse slope (vertical) that are appropxiately the typical area of connected HX condes should be used by default. If there are large differences in areas within the model, these values can be modified to better represent outliers.

## Outputs
The generated junction and storage nodes must be copied into the correct GeoPackage file using the layer names "Nodes--Junctions" and "Nodes--Storage."
