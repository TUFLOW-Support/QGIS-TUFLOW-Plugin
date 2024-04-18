Convert XPSWMM Hydrology for use in TUFLOW-SWMM

Unfortunately, XPSWMM does not write out all required hydrology information when doing a simple export to EPA SWMM 5. Some of the parameters especially infiltration parameters such as curve numbers do not get written correctly. This tool can extract information from GIS data exported from XPSWMM for nodes and subcatchments, manipulate it, and add it to the exported EPA SWMM 5 file data. 

## Usage

### Export EPA SWMM5 Hydrology

1. Make sure that, "Rnf" is the selected mode.
2. From the file menu, select "Import/Export data" -> "Export to EPASWMM 5"
3. This will create an "inp" file in the folder with the XPSWMM project file. Suggest copying this file to a new name to prevent it from being overwritten.

### Export the GIS Subcatchment data which is required to align with the hydrology data associated with nodes

1. Right-click on the "Catchments" layer under the Nodes layer in the XPSWMM layer tree.
2. Click the export button and identify a filename to write the information to.

### Export the Hydrology data associated with the nodes

1. Right-click on the nodes layer and choose "Export to GIS."
2. Expand the "Runoff Node" folder.
3. The columns to include vary based on the hydrology and infiltration options being used by XPSWMM and what will be used in the TUFLOW-SWMM model. Find the appropriate data fields and double click to add them to the list.  
4. Set the GIS filename
5. Click Export

Fill-in the inputs with the files identified above and identify an output location.

## Outputs
The output of the tool will be a GIS layer with the required fields for the "Hydrology--Subcatchment" layer of a TUFLOW-SWMM GPKG layer with additional fields copied over from the exported nodal data that can be manually copied to individual fields using the field calculator.


