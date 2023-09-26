### Description

This tool creates a TUFLOW project with the following features:
* Creates the TUFLOW folder structure
* Generates the empty input files
* Creates a template TUFLOW control files (.tcf, .tgc, etc.)
* Saves the settings to the QGIS project and JSON file which can be used by the other TUFLOW tools. JSON file allows settings to be copied and shared between users and projects more easily.

Note this tool currently only supports TUFLOW Classic / HPC.

### Parameters

1. **Project Name**: The name of the project. This will be used to help name the input files. The name should  avoid spaces and other characters not supported in file paths (e.g. `/\:*?"<>|`).
2. **Project Folder**: The location of the project folder.
3. **Project CRS**: The Co-ordinate Reference System used for the project.
4. **Default GIS Format**: The default GIS format (GPKG, SHP, MIF) to use for the project.
5. **TUFLOW Executable**: The location of the TUFLOW executable.
7. **Create Empty Files**: If checked, will (re)generate empty files.
8. **Create Folder Structure**: If checked, will create the TUFLOW folder structure. Only creates the folder structure if it does not already exist.
9. **Setup Control File Templates**: If checked, will create a series of template control files that can be used as inputs to TUFLOW. Note, the templates are not complete and require further editing by the user before use. The settings and inputs used in the templates are not considered to be final and appropriate for all models, in fact most of them are simply examples and should be treated as such.