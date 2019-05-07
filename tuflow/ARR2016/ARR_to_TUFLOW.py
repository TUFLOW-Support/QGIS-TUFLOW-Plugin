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

version = '2018-01-AB Beta'  # added output figures
now = datetime.now()
disclaimer = 'This plugin is provided free of charge as a tool to automate the process of obtaining hydrologic data\n' \
             'from the ARR datahub and BOM IFD. In no event will BMT WBM Pty Ltd (the developer) be liable for the\n' \
             'results of this plugin. The accuracy of this data, and any pre-processing done by this plugin is the\n' \
             'responsibility of the user. Please cross check all results with the raw ARR datahub text files.'
# inputs
latitude = -21.729  # note negative sign
longitude = 119.328  # non negative :)
site_name = 'test'  # site id, used in outputs
AEP = {'1%': 'AEP', '2%': 'AEP', '5%': 'AEP'} # dict object {magnitude(str): unit(str)} e.g. {'100y': 'ARI', '2%': 'AEP', '0.5': 'EY'} or 'all'
duration = {10: 'm', 15: 'min', 30: 'min', 60: 'min'}  # dict object {mag(float/int): unit(str)} e.g. {30: 'm', 60: 'm', 1.5: 'h'} or 'all'
access_web = True  # once the .html files have been read, they are saved and you can set this to false for debugging
out_form = 'csv'   # csv or ts1
export_path = r'C:\TUFLOW\ARR2016\DualVersion\Output'  # Export path
non_stnd_dur = {270: 'm'}  # non-standard durations. dict object similar to duraiton e.g. {4.5: 'hr'}
frequent_events = False  # set to true to include frequent events (12EY - 0.2EY)
rare_events = False  # set to true to include rare events (1 in 200 - 1 in 2000)
cc = False  # Set to True to output climate change
cc_years = []  # climate change years. List object [year(int)] e.g. [2090]
cc_RCP = []  # Representative Concentration Pathways. List object [RCP(str)] e.g. ['RCP8.5']
preBurst = '50%'  # preburst percentile
lossMethod = '60min'  # chosen loss method e.g. 60min, interpolate, rahman, hill, static
mar = 1500  # mean annual rainfall - for the rahman loss method
staticLoss = 10  # for the static loss method
catchment_area = 100  # catchment area (km2)
add_tp = []  # additional temporal patterns to include in the extract
ARF_frequent = True  # Set to true if you want to ignore ARF limits and apply to frequent events (>50% AEP)
min_ARF = 0.2  # minimum ARF factor
catchment_no = 0  # used in batch mode if specifying more than one catchment. Iterate in cmd to append catchments.
output_notation = 'aep'  # controls output notation e.g. output as 1p_60m or 100y_60m

# batch inputs (system/cmd arguments). If not running from GIS, will use above inputs as defaults so be careful.
arg_error, arg_message, args = get_args(sys.argv)
print('STARTING ARR2016 to TUFLOW SCRIPT\nVersion: {0}\nScript run date: {1:02d}-{2:02d}-{3} at ' \
      '{4:02d}:{5:02d}:{6:02d}\n\nFound the following system arguments:'\
      .format(version, now.day, now.month, now.year, now.hour, now.minute, now.second))
for key, value in args.items():
    print('{0}={1};'.format(key, ",".join(map(str,value))))
print('\n')
if arg_error == True:
    print(arg_message)
    sys.exit('ERROR in input arguemnts')
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
            sys.exit('ERROR in coordinate input')
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
        sys.exit('ERROR: processing event magnitudes')
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
            sys.exit('ERROR: processing event durations')

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
            sys.exit('ERROR: processing non-standard event durations')

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
            sys.exit('ERROR: processing climate change forecast years')
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
            sys.exit('ERROR: processing climate change RCP')
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


# BOM Depth Data
# Open and save raw BOM depth information
if not os.path.exists(export_path):  # check output directory exists
    os.mkdir(export_path)
bom_raw_fname = os.path.join(export_path, 'data', 'BOM_raw_web_{0}.html'.format(site_name))
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
    url_rare = 'http://www.bom.gov.au/water/designRainfalls/revised-ifd/?design=rare&sdday=true&coordinate_type' \
               '=dd&latitude={0}&longitude={1}&user_label=brisbane&values=depths&update=&year=2016'\
               .format(abs(latitude), longitude)
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
        sys.exit()

    print('Saving: {0}'.format(bom_raw_fname))
    fo = open(bom_raw_fname, 'wb')
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
    print ('ERROR: {0}'.format(Bom.message))
    sys.exit("ERROR: {0}".format(Bom.message))
print ('Found {0} AEPs and {1} durations in .html file'.format(Bom.naep, Bom.ndur))

# save out depth table
if catchment_area <= 1.0:  # no catchment area, so no ARF. otherwise write out rainfall after ARF applied
    bom_table_fname = os.path.join(export_path, 'data', 'BOM_Rainfall_Depths_{0}.csv'.format(site_name))
    print('Saving: {0}'.format(bom_table_fname))
    Bom.save(bom_table_fname, site_name)
    print('Done saving file.')


# ARR data
# Open and save raw ARR information
arr_raw_fname = os.path.join(export_path, 'data', 'ARR_Web_data_{0}.txt'.format(site_name))
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
    except urllib2.URLError:
        print('Failed to get data from ARR website')
        sys.exit()
    # save the page to file
    print('Saving: {0}'.format(arr_raw_fname))
    fo = open(arr_raw_fname, 'wb')
    fo.write(the_page)
    fo.flush()
    fo.close()
    print('Done saving file.')

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
                    sys.exit()

                print('Saving: {0}'.format(add_tpFilename))
                fo = open(add_tpFilename, 'wb')
                fo.write(the_page)
                fo.flush()
                fo.close()
                print('Done saving file.')

# load from file
ARR = ARR_WebRes.Arr()
ARR.load(arr_raw_fname, add_tp=add_tp)
if ARR.error:
    print ('ERROR: {0}'.format(ARR.message))
    sys.exit("ERROR: if problem persists please email input files and log.txt to support@tuflow.com.")

# loop through each AEP and export
print ('Exporting data...\n')
# noinspection PyBroadException
try:
    # Combine standard and non standard durations
    if len(non_stnd_dur) > 0:
        for len, unit in non_stnd_dur.items():
            duration[len] = unit

    ARR.export(export_path, aep=AEP, dur=duration, name=site_name, format=out_form, BOM_data=Bom, climate_change=cc,
               climate_change_years=cc_years, cc_rcp=cc_RCP, area=catchment_area, frequent=frequent_events,
               rare=rare_events, catch_no=catchment_no, out_notation=output_notation, ARF_frequent=ARF_frequent,
               min_ARF=min_ARF, preBurst=preBurst, lossMethod=lossMethod, mar=mar, staticLoss=staticLoss,
               add_tp=add_tp)
except:
    print ('ERROR: Unable to export data ')
    sys.exit("ERROR: if problem persists please email input files and log.txt to support@tuflow.com.")

if ARR.error:
    print ('ERROR: {0}'.format(ARR.message))
    sys.exit("ERROR: if problem persists please email input files and log.txt to support@tuflow.com.")
else:
    print('\nDisclaimer: {0}'.format(disclaimer))
    print('\nSCRIPT FINISHED\n')
