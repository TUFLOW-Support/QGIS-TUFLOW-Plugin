# import required modules
import os
import sys
from datetime import datetime
import ARR_WebRes
import BOM_WebRes
from ARR_TUFLOW_func_lib import get_args, tpRegion_coords
pythonV = sys.version_info[0]
if pythonV == 3:
    from urllib import request as urllib2
elif pythonV == 2:
    import urllib2

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from __version__ import version

build_type, version = version()
now = datetime.now()
disclaimer = 'This plugin is provided free of charge as a tool to automate the process of obtaining hydrologic data\n' \
             'from the ARR datahub and BOM IFD. In no event will BMT WBM Pty Ltd (the developer) be liable for the\n' \
             'results of this plugin. The accuracy of this data, and any pre-processing done by this plugin is the\n' \
             'responsibility of the user. Please cross check all results with the raw ARR datahub text files.'
# inputs
site_name = '205'  # site id, used in outputs
latitude = -37.6243  # note negative sign
longitude = 145.0491  # non negative :)
catchment_area = 3.785276443449942  # catchment area (km2)
AEP = {'1%': 'AEP'} # dict object {magnitude(str): unit(str)} e.g. {'100y': 'ARI', '2%': 'AEP', '0.5': 'EY'} or 'all'
duration = {60: 'm'}  # dict object {mag(float/int): unit(str)} e.g. {30: 'm', 60: 'm', 1.5: 'h'} or 'all'
non_stnd_dur = {}  # non-standard durations. dict object similar to duraton e.g. {4.5: 'hr'}
point_tp_csv = None  #r"C:\_Advanced_Training\Module_Data\ARR\WT_Increments.csv"  # file path or None
areal_tp_csv = None  #"C:\_Advanced_Training\Module_Data\ARR\Areal_Rwest_Increments.csv"  # file path or None
out_form = 'csv'   # csv or ts1
output_notation = 'ari'  # controls output notation e.g. output as 1p_60m or 100y_60m
frequent_events = False  # set to true to include frequent events (12EY - 0.2EY)
rare_events = False  # set to true to include rare events (1 in 200 - 1 in 2000)
cc = True  # Set to True to output climate change
cc_years = [2090]  # climate change years. List object [year(int)] e.g. [2090]
cc_RCP = ['RCP8.5']  # Representative Concentration Pathways. List object [RCP(str)] e.g. ['RCP8.5']
preBurst = '50%'  # preburst percentile
lossMethod = 'interpolate'  # chosen loss method e.g. 60min, interpolate, rahman, hill, static
mar = 0  # mean annual rainfall - for the rahman loss method
staticLoss = 0  # for the static loss method
tuflow_loss_method = 'infiltration'  # options: infiltration, excess
user_initial_loss = None  # float or str or None  e.g. 10, '10', None
user_continuing_loss = None  # float or str or None e.g. 2.5, '2.5', None
add_tp = []  # additional temporal patterns to include in the extract
ARF_frequent = False  # Set to true if you want to ignore ARF limits and apply to frequent events (>50% AEP)
min_ARF = 0.2  # minimum ARF factor
export_path = r'C:\Users\Ellis.Symons\Desktop\arr_debugging'  # Export path
access_web = True  # once the .html files have been read, they are saved and you can set this to false for debugging
bom_raw_fname = None  # str or None
arr_raw_fname = None  # str or None
catchment_no = 0  # used in batch mode if specifying more than one catchment. Iterate in cmd to append catchments.

# batch inputs (system/cmd arguments). If not running from GIS, will use above inputs as defaults so be careful.
arg_error, arg_message, args = get_args(sys.argv)
print('STARTING ARR2016 to TUFLOW SCRIPT\nVersion: {0}\nScript run date: {1:02d}-{2:02d}-{3} at ' \
      '{4:02d}:{5:02d}:{6:02d}\n\nFound the following system arguments:'\
      .format(version, now.day, now.month, now.year, now.hour, now.minute, now.second))
# create argument order map so arguments are always printed in the same order
arg_map = {'name': 0, 'coords': 1, 'area': 2, 'mag': 3, 'dur': 4, 'nonstnd': 5, 'format': 6, 'output_notation': 7,
           'frequent': 8, 'rare': 9, 'cc': 10, 'year': 11, 'rcp': 12, 'preburst': 13, 'lossmethod': 14, 'mar': 15,
           'lossvalue': 16, 'tuflow_loss_method': 17, 'user_initial_loss': 18, 'user_continuing_loss': 19, 'addtp': 20,
           'point_tp': 21, 'areal_tp': 22, 'arffreq': 23, 'minarf': 24, 'out': 25, 'offline_mode': 26, 'arr_file': 27,
           'bom_file': 28, 'catchment_no': 29}
for key in sorted(args, key=lambda k: arg_map[k]):
    value = args[key]
    print('{0}={1};'.format(key, ",".join(map(str,value))))
print('\n')
if arg_error == True:
    print(arg_message)
    raise SystemExit(arg_message)

# longitude and latitude (must be input as argument)
if 'coords' in args.keys():
    coords = args['coords']
    for x in coords:
        if float(x) < -9.0 and float(x) > -45.0:
            latitude = float(x)
        elif float(x) > 110.0 and float(x) < 155.0:
            longitude = float(x)
        else:
            print('Coordinates not recognised. Must be in decimal degrees. Latitude must be negative. ' \
                  'Or input coordinates may be out of available range for ARR2016')
            raise SystemExit('Coordinates not recognised. Must be in decimal degrees. Latitude must be negative. ' \
                             'Or input coordinates may be out of available range for ARR2016')

# site name
if 'name' in args.keys():
    site_name = args['name'][0]
# AEP
if 'mag' in args.keys():
    event_mags = args['mag']
    AEP = {}
    try:
        if event_mags[0].lower() == 'all':
            AEP = 'all'
        else:
            event_mags = str(event_mags).strip('[').strip(']').strip("'").strip()
            event_mags = event_mags.split(' ')
            for event_mag in event_mags:
                if event_mag[-2:] == 'EY':
                    AEP[event_mag[:-2]] = event_mag[-2:]
                elif event_mag[-3:] == 'ARI':
                    AEP[event_mag[:-3] + 'y'] = event_mag[-3:]
                else:
                    AEP[event_mag[:-3] + '%'] = event_mag[-3:]
    except:
        print('Could not process event magnitude arguments. Make sure it is in the form [X]AEP or [X]ARI or [X]EY')
        raise SystemExit('Could not process event magnitude arguments. Make sure it is in the form [X]AEP or [X]ARI or [X]EY')

# duration
if 'dur' in args.keys():
    duration = {}
    if args['dur'][0] == 'none':
        duration = {}
    elif len(args['dur']) > 0:
        event_durs = args['dur']
        try:
            if event_durs[0].lower() == 'all':
                duration = 'all'
            else:
                event_durs = str(event_durs).strip('[').strip(']').strip("'").strip()
                event_durs = event_durs.split(' ')
                for event_dur in event_durs:
                    try:
                        duration[float(event_dur[:-1])] = event_dur[-1]
                    except:
                        if event_dur[-2:].lower() == 'hr':
                            duration[float(event_dur[:-2])] = event_dur[-2:]
                        else:
                            duration[float(event_dur[:-3])] = event_dur[-3:]

        except:
            print('Could not process duration arguments. Make sure unit is specified (s, m, h, d)')
            raise SystemExit('Could not process duration arguments. Make sure unit is specified (s, m, h, d)')

# non standard durations
if 'nonstnd' in args.keys():
    non_stnd_dur = {}
    if args['nonstnd'][0] == 'none':
        non_stnd_dur = {}
    elif len(args['nonstnd']) > 0:
        event_nonstnd_durs = args['nonstnd']
        try:
            event_nonstnd_durs = str(event_nonstnd_durs).strip('[').strip(']').strip("'").strip()
            event_nonstnd_durs = event_nonstnd_durs.split(' ')
            for event_nonstnd_dur in event_nonstnd_durs:
                try:
                    non_stnd_dur[float(event_nonstnd_dur[:-1])] = event_nonstnd_dur[-1]
                except:
                    if event_nonstnd_dur[-2:].lower() == 'hr':
                        non_stnd_dur[float(event_nonstnd_dur[:-2])] = event_nonstnd_dur[-2:]
                    else:
                        non_stnd_dur[float(event_nonstnd_dur[:-3])] = event_nonstnd_dur[-3:]
        except:
            print('Could not process non-standard event duration arguments. Make sure unit is specified (s, m, h, d)')
            raise SystemExit('Could not process non-standard event duration arguments. Make sure unit is specified (s, m, h, d)')

# frequent event switch
if 'frequent' in args.keys():
    if args['frequent'][0].lower() == 'true':
        frequent_events = True
    elif args['frequent'][0].lower() == '':
        frequent_events = True
    else:
        frequent_events = False
# rare event switch
if 'rare' in args.keys():
    if args['rare'][0].lower() == 'true':
        rare_events = True
    elif args['rare'][0].lower() == '':
        rare_events = True
    else:
        rare_events = False
# output format
if 'format' in args.keys():
    out_form = args['format'][0]
# export path
if 'out' in args.keys():
    export_path = args['out'][0].strip("'").strip('"')  # remove input quotes from path
# climate change
if 'cc' in args.keys():
    if args['cc'][0].lower() == 'true':
        cc = True
    elif args['cc'][0].lower() == '':
        cc = True
    else:
        cc = False
# climate change year
if 'year' in args.keys():
    cc_years = []
    if args['year'][0] == 'none':
        cc_years = []
    elif len(args['year']) > 0:
        try:
            cc_years_str = args['year']
            cc_years_str = str(cc_years_str).strip('[').strip(']').strip("'").strip()
            cc_years_str = cc_years_str.split(' ')
            for item in cc_years_str:
                cc_years.append(float(item))
        except:
            print('Could not process climate change forecast year arguments')
            raise SystemExit('Could not process climate change forecast year arguments')

# RCP
if 'rcp' in args.keys():
    cc_RCP = []
    if args['rcp'][0] == 'none':
        cc_RCP = []
    elif len(args['rcp']) > 0:
        try:
            cc_RCP_str = args['rcp']
            cc_RCP_str = str(cc_RCP_str).strip('[').strip(']').strip("'").strip()
            cc_RCP_str = cc_RCP_str.split(' ')
            for item in cc_RCP_str:
                cc_RCP.append('RCP{0}'.format(item))
        except:
            print('Could not process climate change RCP arguments')
            raise SystemExit('Could not process climate change RCP arguments')

# catchment area
if 'area' in args.keys():
    catchment_area = float(args['area'][0])
# catchment number
if 'catchment_no' in args.keys():
    catchment_no = float(args['catchment_no'][0])
# Output notation
if 'output_notation' in args.keys():
    if 'ari' in args['output_notation'][0].lower():
        output_notation = 'ari'
    else:
        output_notation = 'aep'
# Preburst percentile
if 'preburst' in args.keys():
    if args['preburst'][0] in ['10%', '25%', '50%', '75%', '90%']:
        preBurst = args['preburst'][0]
    else:
        preBurst = '50%'
# use ARF for frequent events
if 'arffreq' in args.keys():
    if args['ARFfrequent'][0].lower() == 'true':
        ARF_frequent = True
    elif args['ARFfrequent'][0].lower() == '':
        ARF_frequent = True
    else:
        ARF_frequent = False
# Minimum ARF
if 'minarf' in args.keys():
    min_ARF = float(args['minarf'][0])
# Loss method
if 'lossmethod' in args.keys():
    if args['lossmethod'][0] in ['interpolate', 'rahman', 'hill', 'static', '60min']:
        lossMethod = args['lossmethod'][0]
    else:
        lossMethod = 'interpolate'
# Mean Annual Rainfall
if 'mar' in args.keys():
    try:
        mar = float(args['mar'][0])
    except:
        print('MAR value not recognised. Must be greater than 0mm. Using default value of 800mm.')
        mar = 800
# Static Loss Value
if 'lossvalue' in args.keys():
    try:
        staticLoss = float(args['lossvalue'][0])
    except:
        print('Static Loss Value not recognised. Must be greater than 0. Using default of 0')
        staticLoss = 0
# Additional temporal pattern regions
if 'addtp' in args.keys():
    if args['addtp'][0] == 'false':
        add_tp = False
    else:
        add_tp = []
        for tp in args['addtp'][0].split(','):
            add_tp.append(tp.strip())
# tuflow loss method
if 'tuflow_loss_method' in args.keys():
    if args['tuflow_loss_method'][0] in ['infiltration', 'excess']:
        tuflow_loss_method = args['tuflow_loss_method'][0]
    else:
        tuflow_loss_method = 'infiltration'
# point temporal pattern
if 'point_tp' in args.keys():
    if args['point_tp'][0] == 'none':
        point_tp_csv = None
    else:
        point_tp_csv = args['point_tp'][0]
# areal temporal pattern
if 'areal_tp' in args.keys():
    if args['areal_tp'][0] == 'none':
        areal_tp_csv = None
    else:
        areal_tp_csv = args['areal_tp'][0]
# access web / offline mode
if 'offline_mode' in args.keys():
    if args['offline_mode'][0] == 'true':
        access_web = False
    else:
        access_web = True
# arr file
if 'arr_file' in args.keys():
    if args['arr_file'][0] == 'none':
        arr_raw_fname = None
    else:
        arr_raw_fname = args['arr_file'][0]
# bom file
if 'bom_file' in args.keys():
    if args['bom_file'][0] == 'none':
        bom_raw_fname = None
    else:
        bom_raw_fname = args['bom_file'][0]
# user initial loss
if 'user_initial_loss' in args.keys():
    if args['user_initial_loss'][0] == 'none':
        user_initial_loss = None
    else:
        user_initial_loss = args['user_initial_loss'][0]
# user continuing loss
if 'user_continuing_loss' in args.keys():
    if args['user_continuing_loss'][0] == 'none':
        user_continuing_loss = None
    else:
        user_continuing_loss = args['user_continuing_loss'][0]

# BOM Depth Data
# Open and save raw BOM depth information
if not os.path.exists(export_path):  # check output directory exists
    os.mkdir(export_path)
if bom_raw_fname is None:
    bom_raw_fname = os.path.join(export_path, 'data', 'BOM_raw_web_{0}.html'.format(site_name))
else:
    print("Using user specified BOM IFD file: {0}".format(bom_raw_fname))
if not os.path.exists(os.path.dirname(bom_raw_fname)):  # check output directory exists
    os.mkdir(os.path.dirname(bom_raw_fname))
if access_web:
    opener = urllib2.build_opener()
    opener.addheaders.append(('Cookie',
                              'acknowledgedConditions=true;acknowledgedCoordinateCaveat=true;ifdCookieTest=true'))
    if len(non_stnd_dur) > 0:  # if any non-standard durations, make sure included in web address
        nsd = ''
        for dur, unit in non_stnd_dur.items():
            nsd += 'nsd%5B%5D={0}&nsdunit%5B%5D={1}&'.format(dur, unit[0])

    else:
        nsd = 'nsd[]=&nsdunit[]=m&'
    url = 'http://www.bom.gov.au/water/designRainfalls/revised-ifd/?design=ifds&sdmin=true&sdhr=true&sdday' \
          '=true&{0}coordinate_type=dd&latitude={1}&longitude={2}&user_label=&values=depths&update' \
          '=&year=2016'.format(nsd, abs(latitude), longitude)
    url_frequent = 'http://www.bom.gov.au/water/designRainfalls/revised-ifd/?design=very_frequent&sdmin=true&sdhr' \
                   '=true&sdday=true&{0}coordinate_type=dd&latitude={1}&longitude={2}&user_label=&values=depths&update'\
                   '=&year=2016'.format(nsd, abs(latitude), longitude)
    url_rare = 'http://www.bom.gov.au/water/designRainfalls/revised-ifd/?design=rare&sdmin=true&sdhr=true&sdday=true' \
               '&{0}&coordinate_type=dd&latitude={1}&longitude={2}&user_label=brisbane&values=depths&update=&year=2016'\
               .format(nsd, abs(latitude), longitude)
    urlRequest = urllib2.Request(url, headers={'User-Agent': 'Magic Browser'})
    urlRequest_frequent = urllib2.Request(url_frequent, headers={'User-Agent': 'Magic Browser'})
    urlRequest_rare = urllib2.Request(url_rare, headers={'User-Agent': 'Magic Browser'})
    try:
        print('Attempting to access BOM: {0}'.format(url))
        f = opener.open(urlRequest)
        page = f.read()
        if frequent_events:
            print('Attempting to access BOM frequent events: {0}'.format(url_frequent))
            f_frequent = opener.open(urlRequest_frequent)
            page_frequent = f_frequent.read()
        if rare_events:
            print('Attempting to access BOM rare events: {0}'.format(url_rare))
            f_rare = opener.open(urlRequest_rare)
            page_rare = f_rare.read()
    except:
        print('Failed to get data from BOM website')
        raise SystemExit('Failed to get data from BOM website')

    print('Saving: {0}'.format(bom_raw_fname))
    try:
        fo = open(bom_raw_fname, 'wb')
    except PermissionError:
        print("File is locked for editing: {0}".format(bom_raw_fname))
        raise SystemExit("ERROR: File is locked for editing: {0}".format(bom_raw_fname))
    except IOError:
        print("Unexpected error opening file: {0}".format(bom_raw_fname))
        raise SystemExit("ERROR: Unexpected error opening file: {0}".format(bom_raw_fname))
    fo.write(page)
    if frequent_events:
        fo.write(page_frequent)
    if rare_events:
        fo.write(page_rare)
    fo.flush()
    fo.close()
    print('Done saving file.')

# Load BOM file
Bom = BOM_WebRes.Bom()
Bom.load(bom_raw_fname, frequent_events, rare_events)
if Bom.error:
    print('ERROR: {0}'.format(Bom.message))
    raise SystemExit(Bom.message)

print ('Found {0} AEPs and {1} durations in .html file'.format(Bom.naep, Bom.ndur))

# save out depth table
if catchment_area <= 1.0:  # no catchment area, so no ARF. otherwise write out rainfall after ARF applied
    bom_table_fname = os.path.join(export_path, 'data', 'BOM_Rainfall_Depths_{0}.csv'.format(site_name))
    print('Saving: {0}'.format(bom_table_fname))
    Bom.save(bom_table_fname, site_name)
    print('Done saving file.')


# ARR data
# Open and save raw ARR information
if arr_raw_fname is None:
    arr_raw_fname = os.path.join(export_path, 'data', 'ARR_Web_data_{0}.txt'.format(site_name))
else:
    print("Using user specified ARR datahub file: {0}".format(arr_raw_fname))
if access_web:
    url = 'http://data.arr-software.org/?lon_coord={0}5&lat_coord={1}&All=on'.format(longitude, -abs(latitude))

    # seems to require a dummy browser, or ARR rejects the connection
    user_agent = 'Mozilla/5.0 (Windows NT 6.1; Win64; x64)'
    headers = {'User-Agent': user_agent}

    # request the URL
    try:
        print('Attempting to access ARR: {0}'.format(url))
        req = urllib2.Request(url, None, headers)
        response = urllib2.urlopen(req)
        the_page = response.read()
        # save the page to file
        print('Saving: {0}'.format(arr_raw_fname))
        try:
            fo = open(arr_raw_fname, 'wb')
        except PermissionError:
            print("File is locked for editing: {0}".format(arr_raw_fname))
            raise SystemExit("ERROR: File is locked for editing: {0}".format(arr_raw_fname))
        except IOError:
            print("Unexpected error opening file: {0}".format(arr_raw_fname))
            raise SystemExit("ERROR: Unexpected error opening file: {0}".format(arr_raw_fname))
        fo.write(the_page)
        fo.flush()
        fo.close()
        print('Done saving file.')
    except urllib2.URLError:
        if os.path.exists(arr_raw_fname):
            foundTP = False
            with open(arr_raw_fname) as fo:
                for line in fo:
                    if '[STARTPATTERNS]' in line.upper():
                        foundTP = True
                        break
            if foundTP:
                print('WARNING: Could not access ARR website... found and using existing ARR web data {0}'.format(
                    arr_raw_fname))
            else:
                print('Failed to get data from ARR website')
                raise SystemExit('Failed to get data from ARR website')
        else:
            print('Failed to get data from ARR website')
            raise SystemExit('Failed to get data from ARR website')
    
    if point_tp_csv is None:  # only check if user has not specified temporal patterns manually
        print('Checking Temporal Pattern Region...')
        tpRegionCheck = ARR_WebRes.Arr()
        tpRegion = tpRegionCheck.temporalPatternRegion(arr_raw_fname)
        print(tpRegion)
        if tpRegion.upper() == 'RANGELANDS WEST AND RANGELANDS':
            print("Splitting {0} into separate regions: Rangelands West, Rangelands".format(tpRegion))
            if 'rangelands west' not in add_tp:
                print('Adding Rangelands West to additional temporal patterns')
                add_tp.append("rangelands west")
            else:
                print("Rangelands West already selected in additional temporal patterns... skipping")
            if 'rangelands' not in add_tp:
                print('Adding Rangelands to additional temporal patterns')
                add_tp.append("rangelands")
            else:
                print("Rangelands already selected in additional temporal patterns... skipping")
    
    
    if add_tp != False:
        if len(add_tp) > 0:
            for tp in add_tp:
                add_tpFilename = os.path.join(export_path, 'data', 'ARR_Web_data_{0}_TP_{1}.txt'.format(site_name, tp))
                tpCoord = tpRegion_coords(tp)
                url2 = 'http://data.arr-software.org/?lon_coord={0}5&lat_coord={1}&TemporalPatterns=on' \
                       .format(tpCoord[1], tpCoord[0])

                try:
                    print('Attempting to access ARR for additional Temporal Pattern: {0}'.format(tp))
                    req = urllib2.Request(url2, None, headers)
                    response = urllib2.urlopen(req)
                    the_page = response.read()
                except urllib2.URLError:
                    print('Failed to get data from ARR website')
                    raise SystemExit('Failed to get data from ARR website')

                print('Saving: {0}'.format(add_tpFilename))
                try:
                    fo = open(add_tpFilename, 'wb')
                except PermissionError:
                    print("File is locked for editing: {0}".format(add_tpFilename))
                    raise SystemExit("ERROR: File is locked for editing: {0}".format(add_tpFilename))
                except IOError:
                    print("Unexpected error opening file: {0}".format(add_tpFilename))
                    raise SystemExit("ERROR: Unexpected error opening file: {0}".format(add_tpFilename))
                fo.write(the_page)
                fo.flush()
                fo.close()
                print('Done saving file.')

# load from file
ARR = ARR_WebRes.Arr()
ARR.load(arr_raw_fname, catchment_area, add_tp=add_tp, point_tp=point_tp_csv, areal_tp=areal_tp_csv,
         user_initial_loss=user_initial_loss, user_continuing_loss=user_continuing_loss)
if ARR.error:
    print('ERROR: {0}'.format(ARR.message))
    print("ERROR: if problem persists please email input files and log.txt to support@tuflow.com.")
    raise SystemExit(ARR.message)

# loop through each AEP and export
print ('Exporting data...\n')
# noinspection PyBroadException
#try:
# Combine standard and non standard durations
if len(non_stnd_dur) > 0:
    for len, unit in non_stnd_dur.items():
        duration[len] = unit

ARR.export(export_path, aep=AEP, dur=duration, name=site_name, format=out_form, bom_data=Bom, climate_change=cc,
           climate_change_years=cc_years, cc_rcp=cc_RCP, area=catchment_area, frequent=frequent_events,
           rare=rare_events, catch_no=catchment_no, out_notation=output_notation, arf_frequent=ARF_frequent,
           min_arf=min_ARF, preburst=preBurst, lossmethod=lossMethod, mar=mar, staticloss=staticLoss,
           add_tp=add_tp, tuflow_loss_method=tuflow_loss_method)
#except:
#    print('ERROR: Unable to export data')
#    print("ERROR: if problem persists please email input files and log.txt to support@tuflow.com.")
#    raise SystemExit("Unable to export data")

if ARR.error:
    print('ERROR: {0}'.format(ARR.message))
    print("ERROR: if problem persists please email input files and log.txt to support@tuflow.com.")
    raise SystemExit(ARR.message)
else:
    print('\nDisclaimer: {0}'.format(disclaimer))
    print('\nSCRIPT FINISHED\n')
