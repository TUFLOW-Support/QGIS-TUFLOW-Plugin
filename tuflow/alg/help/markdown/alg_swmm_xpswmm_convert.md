This tool converts XPSWMM models for use in TUFLOW-SWMM using an xpx file exported from XPSWMM. Common XPSWMM parameters are converted. Some attributes will need to be specified manually.

The tool uses the "Convert TUFLOW Model GIS Format" processing tool to convert the 2D portion of the model, extracts the 1D portion from the xpx file, and modifies the converted model to incorporate SWMM into the TUFLOW model. 

## Usage
The xpx file required for this tool can be exported from XPSWMM or the free XPSWMM Viewer by clicking on the file menu and selecting "Import/Export Data" and then "Export XPX Data" from the secondary menu.

## Parameters
Here is a brief description of the parameters. The parameters used in the "Convert TUFLOW Model GIS Format" may have a more detailed description with that tool.

1. XPSWMM Exported XPX File: The xpx file exported from the XPSWMM application or viewer.
2. TUFLOW TCF Filename: The TUFLOW tcf filename from within the XPSWMM folder. This is usually in the "2D\Data" folder within the project directory. If this file does not exist, you may need to run the Analyze tool from within XPSWMM.
3. Output Solution Scheme: This is added to the tcf file to select either HPC for the High Performance Compute solver or CLA for the Classic solver.
4. Output Vector Format: The GIS format to use for the converted TUFLOW files.
5. Output Raster Format: The raster format used for DEMs for the converted TUFLOW files.
6. Output Profile: Indicates whether GIS files should be separate files, grouped by control file, or all in one GIS file (requires GeoPackage).
7. Output Folder: The folder to write the converted TUFLOW files to.
8. Output CRS: The crs to use for the converted files. The files are not converted but assumed to be in the provided crs.

## Outputs
A TUFLOW model with SWMM connectivity will be added to the output folder.

## Supported Features
The following functionalities and attributes are supported in the conversion process:
* Nodes - junction, outfalls, and storage
* Conduits - including the various shape types including natural channels with transects and custom H-W curves.
* Inlets and inlet placement with connections to the 2D.
* Weirs and orifices
* Pump - The locations currently converted but not pump curves.
* Nodal inflows
* Inactive geometries are ignored
* Subcatchments - Attributes other than area are only brought across currently if using SWMM hydrology. Because the functionalities differ in this area, it is an area where manual conversion may be required.

## Limitations
TUFLOW-SWMM required or recommended conventions such as HX connections to non-outfall nodes (required), storage nodes at HX connections, and recommended junction attributes (ymax=0, area of ponding=positive value) are not currently incorporated. It is recommended to modify the input files to enforce these conventions. The processing toolbox has many tools to help enforce these settings.  