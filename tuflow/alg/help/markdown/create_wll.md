### Description

Utility to automatically create TUFLOW WLLs.

### Parameters

1. **1D Network Channel Layer**: The layer that will have water level lines created for it. WLL will be created perpendicular to the lines in this layer. This layer does not need to be a 1d_nwk layer, however if it is, 'X' type channels will be ignored.
2. **WLL Line Length**: The length of the WLL lines to be created (in map units).
3. **WLL Max Spacing**: The maximum spacing between WLL lines (in map units).
4. **WLL Spacing Calculation Method**: The method used to calculate the spacing between WLL Lines (note, a WLL will always be created at channel ends)
   1. **Fixed Spacing Along Channel Length**: WLLs will be placed at exactly the **WLL Max Spacing** along each channel
   2. **Equal Spacing Along Channel Length**: WLLs will be placed at equal intervals along each channel. The number of WLLs will be calculated based on the **WLL Max Spacing** and the channel length. Note, at least one WLL will be created for each channel.
   3. **Equal Spacing Along Channel Segment**: WLLs will be placed at equal intervals along each channel segment (i.e. between internal vertices). The number of WLLs will be calculated based on the **WLL Max Spacing** and the segment length. Note, at least one WLL will be created for each segment only if **Always Add WLL at Vertices** is not checked.
5. **Always Add WLL at Vertices**: If checked, a WLL will be added at each internal vertex of the channel layer.
6. **Clip WLLs to Layer**: If checked, WLLs will be clipped to the boundary of the polygon layer specified in **Clip Layer**.
7. **Clip Layer**: The polygon layer to clip WLLs to. Only applicable if **Clip WLLs to Layer** is checked.
8. **WLL Thinning Options**: Options to thin/filter resulting WLLs
   1. **No Thinning**: No thinning will be applied to the WLLs
   2. **Remove Overlapping WLLs**: Any WLLs that overlap will be removed (note, removal will be based on processing order, with later WLLs removed if intersecting earlier created WLLs)
   3. **Remove Overlapping WLLs and WLLs close to Vertices**: Remove overlapping WLLs (same as **Remove Overlapping WLLs**) and will also remove WLLs that are within 20% of the **WLL Max Spacing** of an end or mid vertex.