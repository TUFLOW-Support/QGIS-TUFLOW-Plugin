# Run SWMM - GPKG or INP

Run a SWMM inp file using a SWMM executable.

## Inputs
- SWMM Input File (Inp or GPKG): If a GPKG is provided, the inp is generated first, then SWMM runs.
- SWMM Executable (optional): Path to `runswmm.exe`. Leave blank if `runswmm.exe` is in a standard location. 
- Save with new name (optional): If set, it is used for the `.inp`, `.rpt`, and `.out` files. If not set, outputs use the input name.
- Start Date (optional)
- Start Time (optional)
- End Date (optional)
- End Time (optional)

## Outputs
- Report File (RPT)
- Output File (OUT)

## Notes
- If any start/end date or time is provided, the `[OPTIONS]` section of the inp is updated before running using `MM/DD/YYYY` and `HH:MM:SS`.
- After the run completes, the report is scanned and up to 10 lines containing
  `ERROR` or `WARNING` are sent to the QGIS log. If more exist, the log is truncated.
- You can click "Run in background" in the Processing dialog to keep QGIS responsive
  while SWMM is simulating.
- Typically the default path search for the SWMM Excecutable should be enough. If multiple SWMM installations are present the latest version is picked by default.
