This tool converts an ESTRY model to create a SWMM (5.2 version) inp project file. This project file can be read into EPA SWMM or used 

## Usage
Currently, this functionality requires check files written from a TUFLOW model (using ESTRY) setup to write GeoPackage check files. The GeoPackage check file and the "ta_check_file" (csv format) are required. These files are used instead of the input files to allow TUFLOW to do the input processing such as snapping nodes and channels, interpolating pit (inlet) elevations from the 2D, and interpolating inverts between adjacent pipes.

This tool will generate a SWMM (inp) file that can be used with TUFLOW-SWMM.

## Limitations
This tool is intended to make it easier to convert ESTRY models for use with SWMM. Some of the conversions may not be the optimal representation for SWMM. It is the responsibility of the modeller to check the final model and ensure that it is correct.

Hydraulic structures should be reviewed. Pump operations are not converted and must be setup manually. Weirs have a variety of options in both platforms and the automatic conversion may not be the most appropriate SWMM representation.

No effort is made to convert TUFLOW operational structures to SWMM controls which must be done separately.

Some model parameters are defaulted during the process. For example, default street information is created. SWMM pits (inlets) require street information even though this information is not used with the inlets as converted because they are set to use the OnSAG method. Pits (inlets) use the external "inlet usage" approach where inlet usage is written to a separate layer that is included in TUFLOW using the command "Read GIS SWMM INLET USAGE."

The SWMM model parameters may need to be modified after the conversion process for the model to run stably with low mass errors.