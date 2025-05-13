## Increment Layer

### Description

Increment the current layer.

### Parameters

1. **Increment Layer Name**: Updates the name of the current layer.
   * **Rename Layer**: If checked, the source layer will be renamed. If unchecked, a copy of the source layer will be created.
2. **Remove/Keep old layer**: Determines if the old layer will be removed from the QGIS workspace. If the layer is renamed (as per the option above), this will have no effect as the old layer is the same as the new layer.
3. **Supersede source layer**: If checked, the tool will supersede a copy of the source layer into a new location. This is useful if you are not incrementing the source layer name, or renaming the source layer rather than copying it, as it allows a backup to be created.
   * **Database to Supersede Into**: The database that will contain the superseded layer.
   * **Superseded Layer Name**: The name of the superseded layer.
