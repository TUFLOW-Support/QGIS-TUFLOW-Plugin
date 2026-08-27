### Description

This tool imports TUFLOW Classic/HPC, TUFLOW CATCH and TUFLOW FV empty files. It has been designed for use with **TUFLOW CATCH** projects.

The empty types available are populated based on the project directory input and requires empty file to have been created prior and sitting in the appropriate folder structure:
* `TUFLOW/model/gis/empty`
* `TUFLOWFV/model/gis/empty`

The imported files will be saved into the relevant location in the project directory.

### Parameters

1. **Project Directory**: The location of the project folder (i.e. `Modelling`) This is the parent of the `TUFLOW`, `TUFLOWCATCH` and `TUFLOWFV` folders. This will be automatically populated if the create project tool has been run.
1. **Empty Type**: The available empty types available for import. The list will include TUFLOW, TUFLOW CATCH and TUFLOW FV empty types. If an empty type exists in both HPC and FV, it is distinguished by a label. For example: `2d_mat (HPC)` and `2d_mat (FV)`.
1. **Run ID**: Custom name that will be given to the imported files. The file name will have the following convention `<empty_type>_<run_id>_<geometry_type>`. E.g. `2d_code_CatchA_R`.
1. **Overwrite Output if Exists**: If checked, will overwrite any existing layers if they already exist. If unchecked, will skip those layers and not import them.
1. **GPKG Export Options**: only applicable if the empty files are GPKG format. This option dictates how the tool will import GPKG layers:
   * **Separate**: All imported layers will be in separate files GPKG databases.
   * **Group Geometry Types**: Geometries will be grouped by their empty type e.g. `2d_zsh_L` and `2d_zsh_P` will be grouped in `2d_zsh.gpkg`
   * **All to One**: All imported layers will be imported into a single GPKG (must be specified by the user, see below)
1. **Export to GPKG**: Only applicable if 'All to One' GPKG option is selected. Specifies the location of the GPKG database to import new layers into. Can be new or existing.
