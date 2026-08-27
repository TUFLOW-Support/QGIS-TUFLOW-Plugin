This tool extracts scenarios from multiple SWMM GeoPackage files. A GeoPackage file will be created for common features and one for each scenario. The GeoPackage for each scenario will include objects not contained in the common GeoPackage file or that has different attributes. This tool is especially useful when converting an XPSWMM model that contains scenarios.

## Preparation
The tool requires that a series of GeoPackage files that represent independent scenarios are loaded into QGIS. When converting an XPSWMM model with scenarios, an XPX file must be exported for each scenario. It is recommended that each GeoPackage file have the same base name related to the project followed by the scenario information. For example, if the base name was "slow_creek" you could have GeoPackages: slow_creek_OptA, slow_creek_OptB, and slow_creek_OptC where the scenarios are "OptA", "OptB", and "OptC."

## Usage
Running the tool will extract scenario names using the approach identified in the preparation section and output a series of GeoPackage files and the commands to include them into the TUFLOW-SWMM control file (tscf).

The input parameters are:
1. Source GeoPackages: This will be a selection list based on loaded SWMM GeoPackages. Identify the scenarios to process.
2. Prefix for Output GeoPackage Files: This prefix will be used with extracted scenario names
3. Folder to Place Generated GPKGs: This folder will be where the output files are placed.

## Outputs
A GeoPackage for the common features for all scenarios and a GeoPackage for each scenario that includes non-common features (a scenario only using common will not have an independent GeoPackage) and a file using the prefix plus "tscf_lines.txt" will contain the commands for reading the scenarios into the TUFLOW-SWMM model.

## Limitations
Currently the tool only works for SWMM input files and looks for changes to node and link tables. Other tables such as options or curves are assumed to be the same and are placed in the common file.