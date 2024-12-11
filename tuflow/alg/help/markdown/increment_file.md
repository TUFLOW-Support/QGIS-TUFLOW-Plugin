## Increment File

### Description

Increments a given layer by saving the old layer as a new layer with a new name (usually by incrementing the run number in the layer name). In this case the layer is either a SHP or MIF file so the entire file will be incremented. The open layer in QGIS will have its datasource replaced by the new layer.

### Parameters

1. **Output Folder**: The location of the output folder. This is where the new layer will be saved to (usually the same directory as the old layer).
2. **Output Name**: The name of the new layer. This name will automatically be incremented by 1 (e.g. `2d_zsh_001` will become `2d_zsh_002`).
3. **Remove Old Layer**: If checked, will not retain the old layer in the QGIS workspace.
4. **Keep Old Layer**: If checked, will retain the old layer in the QGIS workspace.
