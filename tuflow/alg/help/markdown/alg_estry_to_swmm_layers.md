This tool converts one or more ESTRY layers into a SWMM project (inp) file.

Supported ESTRY layers includes
* 1D network layers (polylines or points)
* 1D node layers (points)
* Pit layers (points)
* ESTRY table link layers (cross-sections and irregular culvert shapes)

The tool also creates a Geo-Package representation of the SWMM input data.

## Usage
ESTRY channels and links should be converted at the same time.  The tool will create nodes as needed if ESTRY uses automatic nodes.

Parameters used in the conversion process include:
* Pit/inlet database - This is required to convert the pit (inlet) curves for use with SWMM.
* Reference cell size - The 1D/2D linking for SWMM is always based upon a width while ESTRY can specify (using a negative number) an exact number of cells to use when linking. The reference cell size is used to convert fixed number of linked cells from ESTRY to SWMM.
* Snap tolerance - This is the distance to search for nodes snapped to the endpoint of channels.
* Output CRS - The CRS used in the Geo-Package representation of the inp file
* Create options, and report tables - Whether or not the options and report tables should be generated. This should be yes for stand alone models. No can be used to generate files used for scenarios where these tables are provided in a separate file.
* Options table report step - The SWMM report step to use if writing the options table.
* Options table minimum surface area - This parameter can help stabilize a model.

## Outputs
The outputs of the tool are the SWMM output file (inp) format, a Geo-Package with the same name but "gpkg" extention, and an inlet usage filename that can be used with TUFLOW-SWMM models.

## Limitations
This tool is intended to make it easier to convert ESTRY models for use with SWMM. Some of the conversions may not be the optimal representation for SWMM. It is the responsibility of the modeller to check the final model and ensure that it is correct.

Hydraulic structures in particular should be reviewed. Pump operations are not converted and must be setup manually. Weirs have a variety of options in both platforms and the automatic conversion may not be the most appropriate SWMM representation.

No effort is made to convert TUFLOW operational structures to SWMM controls which must be done manually.

Inlets are always specified as using the "Sag" option because this is how inlets are used with ESTRY. It may be appropriate to modify SWMM inlets to use the "Grade" option. This requires the user to provide additional information such as street cross-section and longitudinal slopes.

Some model parameters are defaulted during the process. For example, default street information is created. SWMM pits (inlets) require street information even though this information is not used with the inlets as converted because they are set to use the "Sag" method. Pits (inlets) use the external "inlet usage" approach where inlet usage is written to a separate layer that is included in TUFLOW using the command "Read GIS SWMM INLET USAGE."

The SWMM model parameters may need to be modified after the conversion process for the model to run stably with low mass errors.