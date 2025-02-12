### Description

[Documentation on TUFLOW Wiki](https://wiki.tuflow.com/QGIS_TIN_Polygons_Assign_Elevations)
This tool acts as an alternative method to using the native "MERGE" functionality in TUFLOW for 2d\_zsh polygons by explicitly assigning elevation points (in a 2d\_zsh template) along the polygon perimeter.
It is recommended to use this tool for Quadtree models, rather than the "MERGE" functionality, where the 2d_zsh input crosses Quadtree nesting levels.
It is recommended to prefix the output layer names with '2d\_zsh'.

### Parameters

1. **Polygon Layer:** The polygon layer that will have elevation points created for it.
2. **Raster Layer:** The raster (DEM) layer that will be used to determine the elevations of the output points.
3. **Vertex Distribution Option:** Determines how the vertices will be distributed along the polygon perimeter.
    - **Densify:** Additional vertices will be inserted along the perimeter of the polygon layer at regular intervals (defined by "Vertex Interval"). This option is recommended unless the polygon layer has a negative 'Shape\_Width' value, and a sufficient number of vertices.
    - **Use Existing:** Elevations will be assigned to the existing vertices of the polygon layer. This option should only be used if the polygon layer has a negative 'Shape\_Width' value, and a sufficient number of vertices.
4. **Vertex Interval (only used for Densify):** The length of the interval between the vertices to be created (in map units). This value should be set to the smaller of the following:
    - Half the model cell size
    - The finest Quadtree level