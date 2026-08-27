### Description

Utility to automatically create TUFLOW cross-sections.

### Parameters

1. **1D Network Channel Layer**: The layer that will have cross-sections created for it. Cross-sections will be created perpendicular to the lines in this layer. This layer does not need to be a 1d_nwk layer, however if it is, only 'S' and 'G' types will have cross-sections created (blank types are assumed to be 'G' types).
2. **Cross-Section Position**:
   1. **At Ends**: Cross-sections will be created at the ends of each channel.
   2. **At Midpoints**: Cross-sections will be created at the midpoints of each channel.
3. **Cross-Section Line Length**: The length of the cross-section lines to be created (in map units).
4. **Clip Cross-Sections to Layer**: If checked, cross-sections will be clipped to the boundary of the polygon layer specified in **Clip Layer**.
5. **Clip Layer**: The polygon layer to clip cross-sections to. Only applicable if **Clip Cross-Sections to Layer** is checked.
6. **Export Cross-Sections to CSV**: If checked, cross-sections will be exported to a CSV file. The CSV files will be created in the same directory as the output file (in a folder called 'csv') if a location is not specified in **CSV Output Directory**. If checked, the user must either specify a **CSV Output Directory** or a location for the output layer (cannot be a temporary layer).
7. **CSV Output Directory**: The directory to export CSV files to. If left blank, CSV files will be created in the same directory as the output file (in a folder called 'csv').
8. **Elevation Raster**: Raster to extract elevations from for CSV output. Must be specified if **Export Cross-Sections to CSV** is checked.