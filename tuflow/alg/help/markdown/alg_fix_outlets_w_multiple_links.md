This tool creates a conduit extension to eliminate the SWMM error with multiple links connected to the same outfall node. This is a common issue when converting ESTRY models for use in TUFLOW-SWMM.

## Usage
This tool starts with a GeoPackage file and create a new GeoPackage file that contains the channel extensions. The newly created extension channel is always an open rectangular channel with the provided attributes.

## Limitations
This tool is intended to make it easier to correct the issue with multiple channels at the same outfall nodes. The generated channels may need to be modified to match the real world geometry at the location.