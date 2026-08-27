! TUFLOW CATCH CONTROL FILE (.TCC) defines the TUFLOW CATCH model simulation parameters

!________________________________________________________
! GLOBAL SETTINGS
GIS Format == SHP                 ! Specify the global output format for all GIS files
${catch_gis_projection_command}     ! Sets the default GIS projection
Hardware == GPU                   ! Options - GPU | CPU

! SIMULATION SETTINGS
Time Format == ISODATE                  ! Specified the simulation time format
! Start Time == <dd/mm/yyyy HH:MM:SS>   ! Specifies the simulation start time
! End Time == <dd/mm/yyyy HH:MM:SS>     ! Specifies the simulation end time

! OUTPUT FOLDERS
Output Directory == ..\results\     ! Location of the results files and prefixes them with the .tcc filename
Write Check Files == ..\check\      ! Location of the check files and prefixes them with the .tcc filename
Log Folder == log                   ! Location of the log output files

! BOUNDARY CONDITION CONFIGURATION
Catch BC Output Folder == ..\bc_dbase       ! Location of the BC output files
Catch BC Output Interval Nodestring == 300  ! Interval to output BC nodestring data (seconds)
Catch BC Output Interval Lateral == 900     ! Interval to output BC lateral data (seconds)
CSV Write Frequency Day == 1                ! Interval to write CSV output (days)

!_________________________________________________________________
! CATCHMENT HYDRAULICS
Catchment Hydraulic Model == None  ! Options - None | HPC

    Demo Model == ON        ! Required to run TUFLOW CATCH without a license. Remove if license available

    ! Times
    ! Zero Date == <dd/mm/yyyy HH:MM>       ! Specifies the simulation start time in TUFLOW FV ISODATE format

    ! Base runs directory and TUFLOW HPC executable
    Runs Directory == ..\..\TUFLOW\runs
    EXE == ${hpcexe}

    ! GIS
    GIS Format == ${gis_format}
    ${spatial_database_command}
    ${gis_projection_command}       ! Comment out if equal to the global settings projection
    ! TIF Projection == <path/to.tif>

    ! Solver
    Solution Scheme == HPC
    Timestep == 1                       ! Specifies the first 2D computational timestep (seconds)
    ! Timestep Maximum == <timestep>    ! Specifies a maximum timestep (seconds)
    Time Format == TUFLOWFV             ! Specifies the time format of output results

    ! SGS Settings
    SGS == ON
    ! SGS Sample Target Distance == <distance>  ! Sets SGS Sample Target Distance (meters)

    ! Event(s) and Scenario(s)
    ! Model Event == <event_name>
    ! Model Scenario == <scenario_name>
    ! Event File == ..\..\TUFLOW\model\${model_name}_events.tef     ! Reference the TUFLOW Event File

    ! Control Files
    Geometry Control File == ..\..\TUFLOW\model\${model_name}_001.tgc            ! Reference the TUFLOW Geometry Control File
    BC Control File == ..\..\TUFLOW\model\${model_name}_001.tbc                  ! Reference the TUFLOW Boundary Conditions Control File
    BC Database == ..\..\TUFLOW\bc_dbase\bc_dbase_${model_name}_001.csv          ! Reference the Boundary Conditions Database
    Read Materials File == ..\..\TUFLOW\model\${model_name}_001.csv              ! Reference the Materials Definition File
    ! Rainfall Control File == ..\..\TUFLOW\bc_dbase\${model_name}_rainfall.trfc ! Reference the TUFLOW Rainfall Control File
    ! ESTRY Control File == ..\..\TUFLOW\model\${model_name}_001.ecf             ! Reference the ESTRY (1D) Control File

    ! Soils
    ! Read Soils File == ..\..\TUFLOW\model\${model_name}_soils.tsoilf  ! Reference the Soils File
    ! Soil Negative Rainfall Approach == FACTOR

    ! Initial Water Level
    ! Set IWL == <value>

    ! Pollutant Configuration
    ! Receiving Polygon == <path/to/2d_rp>      ! GIS layer defining the receiving polygon
    ! Pollutant == <name1, name2, name3, ...>   ! Specify the pollutant names

    ! Output Map Configuration
    Map Output Format == XMDF               ! Result file types
    Map Output Data Types == catch h v d    ! Output data types
    Map Output Interval == 900              ! Interval of output map data (seconds)
    ! Map Cutoff Depth == 0.01              ! Sets map cutoff depth (meters)

    ! Plot Output Configuration
    Time Series Output Interval == 60       ! Interval of output time series data (seconds)
    ! Read GIS PO == <path/to/2d_po>        ! Reads in plot output

End Catchment Hydraulic Model

! _________________________________________________________________
! POLLUTANT EXPORT
Catchment Pollutant Export Model == None  ! Options - None | Mass Accumulation Release
    ! Examples below show various options for setting up a constituent. 
    ! <name> should be replaced with a pollutant name from the names specified by 'Pollutant ==' above.
    ! <bc_name> should be replaced with the name declared in the TUFLOW HPC bc_dbase.csv.
    ! <device_name> should be replaced with a device name defined in the 2d_im GIS layer.
    ! Values (if specified) should be updated as the below values are examples only
    
    ! Constant Concentrations
    ! Constant <name> == <value>
    ! e.g. Constant Salinity == 0.0
    
    ! Prohibited Infiltrations
    ! Infiltration <name> == OFF
    ! e.g. Infiltration SED_FINES == OFF
    
    ! Time Series
    ! Time-Series <name> == <bc_name>
    ! e.g. Time-Series Temperature == Temperature
    
    ! Pollutant Export Properties
    ! 'Rate' is in kg/(ha.yr), 'Limit' is in kg/ha. Set Limit to same as yearly rate.
    ! 'Time Constant' is in seconds, 'Depth Threshold' is in meters, 'Deposition Velocity' is in meters/day.
    ! Material == ALL ! Default parameters for all materials
		! <name>, Method == Shear1, Limit == L_shr, Depth Threshold == d, Deposition Stress == tau_cd, Erosion Stress == tau_ce, Deposition Velocity == w_s, Erosion Rate == E_r
		! <name>, Method == Washoff1, Rate == R_a, Limit == L_acc, Time Constant == T_c, Rain Threshold == R_r, Depth Threshold == d, Deposition Velocity == w_s
    ! End Material

    ! Material == 1, 7, 8  ! Material specific definitions e.g. urban areas
		! <name>, Method == Shear1, Limit == L_shr, Depth Threshold == d, Deposition Stress == tau_cd, Erosion Stress == tau_ce, Deposition Velocity == w_s, Erosion Rate == E_r
		! <name>, Method == Washoff1, Rate == R_a, Limit == L_acc, Time Constant == T_c, Rain Threshold == R_r, Depth Threshold == d, Deposition Velocity == w_s
    ! End Material

    ! Interventions
    ! Read GIS Intervention == <path/to/2d_im>  ! GIS layer defining interventions (multiple instances supported)

    ! Mass Removal Properties
    ! Device == ALL   ! Default definitions for all devices
		! <name>, Method == Eqn, Eqn == <equation_type>, Coefficients == <coeff1, coeff2, ...>
		! <name>, Method == Table, Path == <path/to/table.csv>
    ! End Device

    ! Device == <device_name>  ! Device specific definitions
		! <name>, Method == Eqn, Eqn == <equation_type>, Coefficients == <coeff1, coeff2, ...>
		! <name>, Method == Table, Path == <path/to/table.csv>
    ! End Device

End Catchment Pollutant Export Model

! _________________________________________________________________
! RECEIVING HYDRODYNAMICS AND WQ
Receiving Model == None  ! Options - None | TUFLOWFV

    Demo Model == ON        ! Required to run TUFLOW CATCH without a license. Remove if license available

    ! Base runs directory and TUFLOW FV executable
    Runs Directory == ..\..\TUFLOWFV\runs
    EXE == ${fvexe}

    ! Hardware
    ! Hardware == CPU       ! Options - GPU | CPU

    ! GIS
    GIS Format == ${fv_gis_format}          ! Specify the output format for GIS files

    ! General Parameters
    Bottom Drag Model == Manning
    Include Salinity == 0,0
    Include Temperature == 0,0
    Include Sediment == 0,0
    Include Heat == 0
    Spatial Order == 1,1

    ! Timestep Commands
    ! CFL == <value_less_than_1>        ! Specify the Courant–Friedrichs–Lewy (CFL) number (default is 1)
    ! Timestep Limits == <min, max>     ! Specify the minimum and maximum timesteps (seconds)
    Display dt == 900                   ! Interval of displaying timestep information to the log (seconds)

    ! Model Parameters
    ! Stability Limits == <max_WL, max_v>               ! Specify maximum water level (meters) and velocity (m/s) which indicate an unstable model
    ! Momentum Mixing Model == None                     ! Options - None | Constant | Smagorinsky
    ! Global Horizontal Eddy Viscosity ==               ! Parameter(s) for momentum mixing model
    ! Global Horizontal Eddy Viscosity Limits ==        ! Parameter(s) for momentum mixing model
    ! Scalar Mixing Model == None                       ! Options - None | Constant | Smagorinsky | Elder | Warmup
    ! Global Horizontal Scalar Diffusivity ==           ! Parameter(s) for scalar mixing model
    ! Global Horizontal Scalar Diffusivity Limits ==    ! Parameter(s) for scalar mixing model
    ! Vertical Mixing Model == Constant                 ! Options - Constant | Parametric | External
    ! Global Vertical Eddy Viscosity Limits ==          ! Parameter(s) for vertical mixing model
    ! Global Vertical Scalar Diffusivity Limits ==      ! Parameter(s) for vertical mixing model
    ! Turbulence Update dt ==                           ! Specify the timestep for updating the above two terms (seconds)

    ! Water Quality
    ! Water Quality Model == TUFLOW
    ! Water Quality Control File == ..\..\TUFLOWFV\wqm\${model_name}_001.fvwq   ! Reference the Water Quality Control File
    ! Water Quality Model Directory == ..\..\TUFLOWFV\wqm\                  ! Location of the Water Quality Directory
    ! Cell Water Quality Depth == 0.01      ! Minimum depth to execute water quality calculations (meters)

    ! Sediment Transport
    ! Sediment Control File == ..\..\TUFLOWFV\stm\${model_name}_001.fvsed       ! Reference the Sediment Control File

    ! 2D Geometry
    ! Geometry 2D == <path/to/mesh.2dm>     ! 2D geometry input file (mesh file)
    ! Read Grid Zpts == <path/to/DEM>       ! Assigns the elevation of Zpts from the grid (.asc or .flt format)

    ! 3D Geometry
    ! Vertical Mesh Type == Sigma           ! Options - Sigma | Z
    ! Layer Face File == <path/to/csv>      ! Parameter(s) for vertical mesh type
    ! Sigma Layers ==                       ! Parameter(s) for vertical mesh type
    ! Min Bottom Layer Thickness ==         ! Minimum thickness of lowest layer (meters)
    ! Cell 3D Depth ==                      ! Threshold water depth for 3D calculations (meters)

    ! Materials
    ! Example material block
    ! Read GIS Mat == <path_to_2d_mat>      ! Sets the TUFLOW FV material values according to attributes in the GIS layer
    Set Mat == 1                            ! Sets the default material ID for all cells in the TUFLOW FV model domain
    Material == 1
        Bottom Roughness == 0.012
    End Material
    
    ! Initial Conditions
    ! Initial Temperature == 0.0            ! Specify initial temperature (degrees Celsius)
    ! Initial Water Level == 0.0            ! Specify initial water level (meters)
    ! Initial Salinity == 0.0               ! Specify initial salinity (psu)
    ! Initial Sediment Concentration == <sed_1, ..., sed_N> ! Specify initial suspended sediment concentration for each sediment (mg/L)
    ! Initial WQ Concentration == <wq_1, ..., wq_N>       ! Specify initial water quality concentration for each wq constituents

    ! Non-Catchment Boundaries
    ! Read GIS Nodestring == <path/to/2d_ns_L>              ! GIS nodestring layer defining non-catchment boundary(ies)
    ! BC == <boundary_type>, <boundary_name>, <path/to/csv> ! Third parameter is 'friction slope' for 'QN' boundaries
    !     BC Header == <time_header>, <value_header>
    ! End BC

    ! Catchment Boundaries (to be used for linkage)
    ! Catchment BC Nodestring == <path/to/hpc/linking/node_strings> ! GIS nodestring layer defining catchment boundary(ies)

    ! Fluxes
    ! Read GIS Nodestring == <path/to/2d_ns_L>      ! GIS nodestring layer defining internal flux lines

    ! Meteorology
    ! Can be defined by either time series, or grid. Do not use both.
    ! Both of the following examples could be defined via Include == <path/to/fvc> (see TUFLOW FV manual)
    ! BC keyword options: AIR_TEMP, CLOUD, CYC_HOLLAND, LW_NET, LW_RAD, PRECIP, REL_HUM, SURF_TEMP, SW_RAD, W10
    ! Time series example
    ! BC == <bc_keyword>, <path/to/ts.csv>                  ! Specify BC keyword and path to time series file
        ! BC Header == <bc_header1, bc_header2, ...>        ! Column headers to read from time series file
        ! BC Update dt ==                                   ! Specify update timestep for BC (seconds)
        ! BC Time Units == Hours                            ! Options - Hours, Days, Minutes, Seconds, Isotime
        ! BC Reference Time == <dd/mm/yyyy hh:mm>           ! Specify boundary condition reference time
    ! End BC
    ! Gridded data example
    ! Grid Definition File == <path/to/nc>                  ! Specify path to NetCDF file
        ! Grid Definition Variables == <X, Y>               ! Specify the x,y coordinate variable names
        ! Grid Definition Label == <grid_label>             ! Specify the grid label
    ! End Grid
    ! BC == <grid_keyword>, <grid_label>, <path/to/nc>      ! Specify grid BC keyword, grid label and path to NetCDF file
        ! BC Header == <bc_header1, bc_header2, ...>        ! Column headers to read from NetCDF file
        ! BC Update dt == 900                               ! Specify update timestep for BC (seconds)
    ! End BC

    ! Outputs
    ! Example output blocks below
    ! Output == NetCDF
    !     Output Parameters == <output_parameters>
    !     Output Interval == 3600.
    !     Suffix == <suffix>
    ! End Output
    
    Output == Flux
        Output Interval == 3600.
    End Output
    
    Output == Mass
        Output Interval == 3600.
    End Output
    
    Write Restart dt == 24          ! Time interval to write a restart file (hours)
    Restart Overwrite == 1          ! Overwrite the .rst (1) or create new .rst (0) at time interval specified above

End Receiving Model
