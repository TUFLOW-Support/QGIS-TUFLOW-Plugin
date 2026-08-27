This tool classifies SWMM inlet placements (on-grade vs on-sag) based on extracted DEM elevations in the direction of the nearest road segment. Inlets that are determined to be in or next to a low spot based on a user defined tolerance are identified as on-grade. Otherwise, they are on-sag. A bc layer for connectivity is created for on-grade inlets. A check points file and a cross-section file which can be viewed in the TUFLOW Viewer V2 are output for quality control.

## Usage

The following parameters are required inputs for the algorithm:
- Input inlets layer - This must be in the SWMM input usage layer format that can be created from the "swmm_iu" empty file. The parameters should be filled in. The placement and slope will get overwritten.
- Number of elevation values to extract (each side of the inlet) - The algorithm extracts a line of values to determine on-sag vs on-grade. This controls how many values are extracted.
- DEM - The source for extracted elevations.
- Input roads layer - The roads are required to identify the direction to extract elevations at the inlets.
- Sample distance - The distance to extend both directions of the inlet in the direction of the roadway to extract elevations from.
- Maximum distance to nearest road - If an inlet does not have a roadway within this distance, it is unable to be classified.
- Minimum rise from low-point to each side for on-sag inlets - This distance determines whether a rise in elevation is enough to classify an inlet as on-sag. Increasing this number will lead to more on-grade inlets. Decreasing it will lead to fewer on-grade inlets.
- Offset distance for BC line - For BC lines created for on-grade inlets, this will be the offset used. The offset is useful because it prevents the CN and SX lines from overlapping.
- Distance for BC line behind inlet - The HEC-22 approach that is used to determine on-grade inlet discharges is based on the approach flow extracted across half the roadway from the crown to the edge of the roadway area. This value identifies how far to extend opposite from the centerline for BC lines to connect the 2D and 1D domains.

## Outputs

Several output layers are output from this tool.

### Modified TUFLOW-SWMM Inlet Usage Layer

The input inlet usage layer data is used for the output with the following changes:
- Placement - Modified with on-sag and on-grade as determined by the algorithm. If the algorithm is unable to determine, the original value will remain.
- Conn1D\_2D - The tool assumes that on-grade inlets will use the derived BC connections and therefore remove any automatic SX or SXZ values.
- Slopepct\_Longitudinal - The calculated slope from the extracted elevation values.

### A 2D BC layer:

This layer contains SX and CN lines for boundary connections between the TUFLOW 2D and the SWMM 1D domains that capture the flow from half the street as required by the HEC-22 methodology.

## Check Layer Points

This layer contains information useful for understanding how the algorithm determined the inlet placement. The fields contained include:
- grade\_sag - whether the inlet is ON SAG, ON GRADE, or UNKNOWN
- elev\_inlet - the extracted DEM elevation at the inlet
- elev\_up - the maximum extracted elevation on the upstream side (based on the DEM) of the local minimum
- elev\_down - the maximum extracted elevation on the downstream side of the local minimum
- avg\_slope - the estimated slope from the extracted elevations
- dist\_to\_road - the determined distance to the nearest roadway line in the roadway inputs

### Check Layer Cross-sections

The extracted DEM elevations in 1d_xs format and includes files written to a "csv" folder created within the directory the cross-section layer is written to. The cross-sections can be viewed with the TUFLOW viewer to understand why inlets may be classified as on-sag or on-grade.

## Algorithm

The algorithm proceeds as follows to determine if an inlet is on-grade or on-sag:
1. Elevations are extracted at points along a line offset from the nearest roadway based on the user defined distance and number of elevation values to extract.
2. The local minimum location at the inlet is determined by following each direction until there is a rise in slope.
3. The maximum elevations on either side of the local minimum are determined which will be referred to as max1 and max2.
4. The local minimum is compared with max1 and max2. If both max1 and max2 are more than the user defined minimum rise for sag inlets, then the inlet is identified as an on-sag inlet. Otherwise, the inlet is identified as an on-grade inlet.

Note: If the algorithm is unable to determine if the inlet should be on-sag or on-grade largely due to not finding an adjacent roadway, the check file will identify the placement as unknown and the input placement will be used for the SWMM inlet usage output.

The slope at the inlet is calculated based on a linear fit for all of the extracted points.

For on-grade inlets, a SX boundary condition connection is created by drawing a line from the nearest roadway to the inlet location and then extended the user defined distance behind the inlet. A CN line connects the inlet to the SX line. The user defined offset is applied to the SX line which avoids having the SX and CN lines overlapping.

## Limitations
This algorithm used by this tool may misclassify inlets and the results should be reviewed by the modeller.