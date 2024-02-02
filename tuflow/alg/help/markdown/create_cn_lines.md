### Description

Utility to automatically create TUFLOW CN Lines.

### Parameters

1. **1D Network Channel Layer**: The layer that will have CN lines created for it. CN lines will be created perpendicular to the lines in this layer at the channel ends (two per end). This layer does not need to be a 1d_nwk layer, however if it is, only 'S' and 'G' types will have cross-sections created (blank types are assumed to be 'G' types).
2. **1D Domain Polygon**: Polygon to clip the CN lines to. If both a **1D Domain Polygon** and **HX Lines** input are specified, this input will be ignored. If used, an additional temporary output layer will be created which will be a copy of this input however with additional vertices inserted where the CN lines intersect.
3. **HX Lines**: HX lines to clip the CN lines to. If both a **1D Domain Polygon** and **HX Lines** input are specified, **1D Domain Polygon** will be ignored. If used, an additional temporary output layer will be created which will be a copy of this input however with additional vertices inserted where the CN lines intersect. This layer does not need to be a 2d_bc type, however if it is, only 'HX' types will  be used for trimming the CN lines.
4. **Max CN Line Length**: The length of the CN lines to be created (in map units).
