### Description

This tool imports TUFLOW empty files.
The empty types available are populated based on the project directory input and requires empty file to have been created prior and sitting in the appropriate folder structure:
* `model/gis/empty`

The imported files will be saved into the relevant location in the project directory.

### Parameters

1. **Project Folder**: The location of the project folder. This is the parent TUFLOW folder. This will be automatically populated if the create project tool has been run.
2. **Empty Type**: The available empty types available for import.
3. **Geometry Type**: The geometry type of the input file. This will determine what geometry is assigned to the empty files on import.
4. **Run ID**: Custom name that will be given to the imported files. The file name will have the following convention `<empty_type>_<run_id>_<geometry_type>`. E.g. `2d_code_CatchA_R`.
5. **Overwrite Output if Exists**: If checked, will overwrite any existing layers if they already exist. If unchecked, will skip those layers and not import them.
6. **GPKG Export Options**: only applicable if the empty files are GPKG format. This option dictates how the tool will import GPKG layers:
   * **Separate**: All imported layers will be in separate files GPKG databases.
   * **Group Geometry Types**: Geometries will be grouped by their empty type e.g. `2d_zsh_L` and `2d_zsh_P` will be grouped in `2d_zsh.gpkg`
   * **All to One**: All imported layers will be imported into a single GPKG (must be specified by the user, see below)
7. **Export to GPKG**: Only applicable if 'All to One' GPKG option is selected. Specifies the location of the GPKG database to import new layers into. Can be new or existing.
