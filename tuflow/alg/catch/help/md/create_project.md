### Description

This tool creates a TUFLOW CATCH project with the following features:
* Creates the TUFLOW CATCH folder structure
* Generates the empty input files for both the Catchment Hydraulic (HPC) and Receiving (FV) models
* Generates template control files, including a template TUFLOW CATCH Control File (.tcc)
* Saves the settings to the QGIS project and JSON file which can be used by the other TUFLOW CATCH tools

### Parameters

1. **Project Name**: The name of the project. This will be used to name the input files. 
The name should avoid spaces and other characters not supported in file paths (e.g. `/\:*?"<>|`). This name will be automatically suffixed with "`_`001". Example, "MyCATCHProject`_`001".
2. **Project Folder**: The location of the project folder. 
3. **Project CRS**: The Coordinate Reference System (CRS) used for the project.
4. **TUFLOW HPC Executable**: The location of the TUFLOW HPC executable.
5. **TUFLOW FV Executable**: The location of the TUFLOW FV executable.
6. **GIS Format for Catchment Hydraulic Model**: The GIS format (GPKG, SHP) to be used for the Catchment Hydraulic (HPC) model. 
Note: The global GIS format will default to SHP, as the Receiving (FV) model does not support GPKG.
7. **Create Empty Files**: If checked, will (re)generate empty files for both the Catchment Hydraulic (HPC) and Receiving (FV) models.
8. **Create Folder Structure**: If checked, will create the TUFLOW CATCH folder structure. 
Only creates the folder structure if it does not already exist.
9. **Setup Control File Templates**: If checked, the 'Control File Templates' parameter will become available. Template control files will be created for all selected files.
Note, the templates are not complete and require further editing by the user before use. The settings and inputs used in the templates are not considered to be final and appropriate for all models, in fact most of them are simply examples and should be treated as such.
10. **Control File Templates**: List of control files that can be used in a TUFLOW CATCH project. The tool will generate a template for each selected control file.