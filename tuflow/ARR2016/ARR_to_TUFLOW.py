# import required modules
import os
import sys
from datetime import datetime
import ARR_WebRes
import BOM_WebRes
import logging
from ARR_TUFLOW_func_lib import get_args, tpRegion_coords
pythonV = sys.version_info[0]
if pythonV == 3:
    from urllib import request as urllib2
elif pythonV == 2:
    import urllib2
import requests, zipfile, io, json
import traceback

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from __version__ import version

# remote debugging
sys.path.append(r'C:\Program Files\JetBrains\PyCharm 2019.2\debug-eggs')
sys.path.append(r'C:\Program Files\JetBrains\PyCharm 2019.2\plugins\python\helpers\pydev')

build_type, version = version()
now = datetime.now()
disclaimer = 'This plugin is provided free of charge as a tool to automate the process of obtaining hydrologic data\n' \
             'from the ARR datahub and BOM IFD. In no event will BMT Pty Ltd (the developer) be liable for the\n' \
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
urban_initial_loss = None
urban_continuing_loss = None
probability_neutral_losses = True
bComplete_storm = False
preburst_pattern_method = None
preburst_pattern_dur = None
preburst_pattern_tp = None
bPreburst_dur_proportional = False
add_tp = []  # additional temporal patterns to include in the extract
ARF_frequent = False  # Set to true if you want to ignore ARF limits and apply to frequent events (>50% AEP)
min_ARF = 0.2  # minimum ARF factor
export_path = r'C:\Users\Ellis.Symons\Desktop\arr_debugging'  # Export path
access_web = True  # once the .html files have been read, they are saved and you can set this to false for debugging
bom_raw_fname = None  # str or None
arr_raw_fname = None  # str or None
catchment_no = 0  # used in batch mode if specifying more than one catchment. Iterate in cmd to append catchments.

# batch inputs (system/cmd arguments). If not running from GIS, will use above inputs as defaults so be careful.
try:
    arg_error, arg_message, args = get_args(sys.argv)
except Exception as e:
    if '-out' in sys.argv:
        i = sys.argv.index('-out')
        export_path = sys.argv[i+1]
    else:
        export_path = __file__
    logger = r'{0}{1}err_log.txt'.format(export_path, os.sep)
    with open(logger, 'w') as fo:
        fo.write("ERROR: Unable to read arguments...")
        raise SystemExit("Error: Unable to read arguments...")

# export path - get earlier so we can start logging
if 'out' in args.keys():
    export_path = args['out'][0].strip("'").strip('"')  # remove input quotes from path
# site name - get earlier so we can start logging
if 'name' in args.keys():
    site_name = args['name'][0]

# logger - new in 3.0.4 - move away from using stdout and stderr
logger = logging.getLogger('ARR2019')
logger.setLevel(logging.INFO)
fh = logging.FileHandler(r'{0}{1}{2}_log.txt'.format(export_path, os.sep, site_name), mode='w')
fh.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.ERROR)
fmt = logging.Formatter('%(message)s')
fh.setFormatter(fmt)
ch.setFormatter(fmt)
logger.addHandler(fh)
logger.addHandler(ch)

#print('STARTING ARR2019 to TUFLOW SCRIPT\nVersion: {0}\nScript run date: {1:02d}-{2:02d}-{3} at ' \
#      '{4:02d}:{5:02d}:{6:02d}\n\nFound the following system arguments:'\
#      .format(version, now.day, now.month, now.year, now.hour, now.minute, now.second))
logger.info('STARTING ARR2019 to TUFLOW SCRIPT\nVersion: {0}\nScript run date: {1:02d}-{2:02d}-{3} at ' \
            '{4:02d}:{5:02d}:{6:02d}\n\nFound the following system arguments:'\
            .format(version, now.day, now.month, now.year, now.hour, now.minute, now.second))
# create argument order map so arguments are always printed in the same order
arg_map = {'name': 0, 'coords': 1, 'area': 2, 'mag': 3, 'dur': 4, 'nonstnd': 5, 'format': 6, 'output_notation': 7,
           'frequent': 8, 'rare': 9, 'cc': 10, 'year': 11, 'rcp': 12, 'preburst': 13, 'lossmethod': 14, 'mar': 15,
           'lossvalue': 16, 'tuflow_loss_method': 17, 'probability_neutral_losses': 18,
           'complete_storm': 18.1, 'preburst_pattern_method': 18.2, 'preburst_pattern_dur': 18.3,
           'preburst_pattern_tp': 18.4, 'preburst_dur_proportional': 18.5,
           'user_initial_loss': 19,
           'user_continuing_loss': 20,
           'urban_initial_loss': 21, 'urban_continuing_loss': 22, 'addtp': 23,
           'point_tp': 24, 'areal_tp': 25, 'arffreq': 26, 'minarf': 27, 'out': 28, 'offline_mode': 29, 'arr_file': 30,
           'bom_file': 31, 'catchment_no': 32}
for key in sorted(args, key=lambda k: arg_map[k]):
    value = args[key]
    #print('{0}={1};'.format(key, ",".join(map(str,value))))
    logger.info('{0}={1};'.format(key, ",".join(map(str,value))))
#print('\n')
logger.info('\n')
if arg_error:
    #print(arg_message)
    logger.error(arg_message)
    logging.shutdown()
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
            #print('Coordinates not recognised. Must be in decimal degrees. Latitude must be negative. ' \
            #      'Or input coordinates may be out of available range for ARR2016')
            logger.error('Coordinates not recognised. Must be in decimal degrees. Latitude must be negative. ' \
                  'Or input coordinates may be out of available range for ARR2016')
            logging.shutdown()
            raise SystemExit('Coordinates not recognised. Must be in decimal degrees. Latitude must be negative. ' \
                             'Or input coordinates may be out of available range for ARR2016')

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
        #print('Could not process event magnitude arguments. Make sure it is in the form [X]AEP or [X]ARI or [X]EY')
        logger.error('Could not process event magnitude arguments. Make sure it is in the form [X]AEP or [X]ARI or [X]EY')
        logging.shutdown()
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
            #print('Could not process duration arguments. Make sure unit is specified (s, m, h, d)')
            logger.error('Could not process duration arguments. Make sure unit is specified (s, m, h, d)')
            logging.shutdown()
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
            #print('Could not process non-standard event duration arguments. Make sure unit is specified (s, m, h, d)')
            logger.error('Could not process non-standard event duration arguments. Make sure unit is specified (s, m, h, d)')
            logging.shutdown()
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
            #print('Could not process climate change forecast year arguments')
            logger.error('Could not process climate change forecast year arguments')
            logging.shutdown()
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
            #print('Could not process climate change RCP arguments')
            logger.error('Could not process climate change RCP arguments')
            logging.shutdown()
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
    if args['arffreq'][0].lower() == 'true':
        ARF_frequent = True
    elif args['arffreq'][0].lower() == '':
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
        #print('MAR value not recognised. Must be greater than 0mm. Using default value of 800mm.')
        logger.warning('MAR value not recognised. Must be greater than 0mm. Using default value of 800mm.')
        mar = 800
# Static Loss Value
if 'lossvalue' in args.keys():
    try:
        staticLoss = float(args['lossvalue'][0])
    except:
        #print('Static Loss Value not recognised. Must be greater than 0. Using default of 0')
        logger.warning('Static Loss Value not recognised. Must be greater than 0. Using default of 0')
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
# urban initial loss
if 'urban_initial_loss' in args.keys():
    if args['urban_initial_loss'][0] == 'none':
        urban_initial_loss = None
    else:
        urban_initial_loss = args['urban_initial_loss'][0]
# urban continuing loss
if 'urban_continuing_loss' in args.keys():
    if args['urban_continuing_loss'][0] == 'none':
        urban_continuing_loss = None
    else:
        urban_continuing_loss = args['urban_continuing_loss'][0]
# probability neutral losses
if 'probability_neutral_losses' in args.keys():
    if args['probability_neutral_losses'][0] == 'false':
        probability_neutral_losses = False
    else:
        probability_neutral_losses = True
# complete storm stuff
if 'complete_storm' in args.keys():
    if args['complete_storm'][0] == 'true':
        bComplete_storm = True
    else:
        bComplete_storm = False
if 'preburst_pattern_method' in args.keys():
    preburst_pattern_method = args['preburst_pattern_method'][0]
if 'preburst_pattern_dur' in args.keys():
    preburst_pattern_dur = args['preburst_pattern_dur'][0]
if 'preburst_pattern_tp' in args.keys():
    preburst_pattern_tp = args['preburst_pattern_tp'][0]
if 'preburst_dur_proportional' in args.keys():
    if args['preburst_dur_proportional'][0] == 'true':
        bPreburst_dur_proportional = True
    else:
        bPreburst_dur_proportional = False
        
warnings = []

# BOM Depth Data
# Open and save raw BOM depth information
if not os.path.exists(export_path):  # check output directory exists
    os.mkdir(export_path)
if bom_raw_fname is None:
    bom_raw_fname = os.path.join(export_path, 'data', 'BOM_raw_web_{0}.html'.format(site_name))
else:
    #print("Using user specified BOM IFD file: {0}".format(bom_raw_fname))
    logger.info("Using user specified BOM IFD file: {0}".format(bom_raw_fname))
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
        #print('Attempting to access BOM: {0}'.format(url))
        logger.info('Attempting to access BOM: {0}'.format(url))
        f = opener.open(urlRequest)
        page = f.read()
        if frequent_events:
            #print('Attempting to access BOM frequent events: {0}'.format(url_frequent))
            logger.info('Attempting to access BOM frequent events: {0}'.format(url_frequent))
            f_frequent = opener.open(urlRequest_frequent)
            page_frequent = f_frequent.read()
        if rare_events:
            #print('Attempting to access BOM rare events: {0}'.format(url_rare))
            logger.info('Attempting to access BOM rare events: {0}'.format(url_rare))
            f_rare = opener.open(urlRequest_rare)
            page_rare = f_rare.read()
    except:
        #print('Failed to get data from BOM website')
        logger.error('Failed to get data from BOM website')
        logging.shutdown()
        raise SystemExit('Failed to get data from BOM website')

    #print('Saving: {0}'.format(bom_raw_fname))
    logger.info('Saving: {0}'.format(bom_raw_fname))
    try:
        fo = open(bom_raw_fname, 'wb')
    except PermissionError:
        #print("File is locked for editing: {0}".format(bom_raw_fname))
        logger.error("File is locked for editing: {0}".format(bom_raw_fname))
        logging.shutdown()
        raise SystemExit("ERROR: File is locked for editing: {0}".format(bom_raw_fname))
    except IOError:
        #print("Unexpected error opening file: {0}".format(bom_raw_fname))
        logger.error("Unexpected error opening file: {0}".format(bom_raw_fname))
        logging.shutdown()
        raise SystemExit("ERROR: Unexpected error opening file: {0}".format(bom_raw_fname))
    fo.write(page)
    if frequent_events:
        fo.write(page_frequent)
    if rare_events:
        fo.write(page_rare)
    fo.flush()
    fo.close()
    #print('Done saving file.')
    logger.info('Done saving file.')

# Load BOM file
Bom = BOM_WebRes.Bom()
Bom.load(bom_raw_fname, frequent_events, rare_events)
if Bom.error:
    #print('ERROR: {0}'.format(Bom.message))
    logger.error('ERROR: {0}'.format(Bom.message))
    logging.shutdown()
    raise SystemExit(Bom.message)

#print ('Found {0} AEPs and {1} durations in .html file'.format(Bom.naep, Bom.ndur))
logger.info ('Found {0} AEPs and {1} durations in .html file'.format(Bom.naep, Bom.ndur))

# save out depth table
if catchment_area <= 1.0:  # no catchment area, so no ARF. otherwise write out rainfall after ARF applied
    bom_table_fname = os.path.join(export_path, 'data', 'BOM_Rainfall_Depths_{0}.csv'.format(site_name))
    #print('Saving: {0}'.format(bom_table_fname))
    logger.info('Saving: {0}'.format(bom_table_fname))
    Bom.save(bom_table_fname, site_name)
    #print('Done saving file.')
    logger.info('Done saving file.')


# ARR data
# Open and save raw ARR information
areal_tp_download = None
if arr_raw_fname is None:
    arr_raw_fname = os.path.join(export_path, 'data', 'ARR_Web_data_{0}.txt'.format(site_name))
else:
    #print("Using user specified ARR datahub file: {0}".format(arr_raw_fname))
    logger.info("Using user specified ARR datahub file: {0}".format(arr_raw_fname))
if access_web:
    # longitude changed if greater than 153.2999 - set to 153.2999
    # this seems to be a limit for ARR datahub as of June 2019
    # only affects south-eastern most point of qld and north-eatern most point of NSW
    if longitude > 153.2999:
        long_changed = 153.2999
        #print('\nWARNING: Longitude changed from {0} to {1}:\n'
        #      '   ARR datahub does not support longitudes greater than {1}.\n'
        #      '   If this is no longer the case and you would like have this switch removed please contact support@tuflow.com.\n'
        #      '   Longitude for BOM IFD extraction has not been altered.\n'.format(longitude, long_changed))
        logger.warning('\nWARNING: Longitude changed from {0} to {1}:\n'
                       '   ARR datahub does not support longitudes greater than {1}.\n'
                       '   If this is no longer the case and you would like have this switch removed please contact support@tuflow.com.\n'
                       '   Longitude for BOM IFD extraction has not been altered.\n'.format(longitude, long_changed))
    else:
        long_changed = longitude
    url = 'http://data.arr-software.org/?lon_coord={0}5&lat_coord={1}&type=text&All=1'.format(long_changed, -abs(latitude))

    # seems to require a dummy browser, or ARR rejects the connection
    user_agent = 'Mozilla/5.0 (Windows NT 6.1; Win64; x64)'
    headers = {'User-Agent': user_agent}

    # request the URL
    try:
        #print('Attempting to access ARR: {0}'.format(url))
        logger.info('Attempting to access ARR: {0}'.format(url))
        req = urllib2.Request(url, None, headers)
        response = urllib2.urlopen(req)
        the_page = response.read()
        # save the page to file
        #print('Saving: {0}'.format(arr_raw_fname))
        logger.info('Saving: {0}'.format(arr_raw_fname))
        try:
            fo = open(arr_raw_fname, 'wb')
        except PermissionError:
            #print("File is locked for editing: {0}".format(arr_raw_fname))
            logger.error("File is locked for editing: {0}".format(arr_raw_fname))
            logging.shutdown()
            raise SystemExit("ERROR: File is locked for editing: {0}".format(arr_raw_fname))
        except IOError:
            #print("Unexpected error opening file: {0}".format(arr_raw_fname))
            logger.error("Unexpected error opening file: {0}".format(arr_raw_fname))
            logging.shutdown()
            raise SystemExit("ERROR: Unexpected error opening file: {0}".format(arr_raw_fname))
        fo.write(the_page)
        fo.flush()
        fo.close()
        #print('Done saving file.')
        logger.info('Done saving file.')
    except urllib2.URLError:
        if os.path.exists(arr_raw_fname):
            foundTP = False
            with open(arr_raw_fname) as fo:
                for line in fo:
                    if '[STARTPATTERNS]' in line.upper():
                        foundTP = True
                        break
            if foundTP:
                #print('WARNING: Could not access ARR website... found and using existing ARR web data {0}'.format(
                #    arr_raw_fname))
                logger.warning('WARNING: Could not access ARR website... found and using existing ARR web data {0}'.format(
                               arr_raw_fname))
            else:
                #print('Failed to get data from ARR website')
                logger.error('Failed to get data from ARR website')
                logging.shutdown()
                raise SystemExit('Failed to get data from ARR website')
        else:
            #print('Failed to get data from ARR website')
            logger.error('Failed to get data from ARR website')
            logging.shutdown()
            raise SystemExit('Failed to get data from ARR website')

    if areal_tp_csv is None:
        logger.info('Downloading Areal Temporal Pattern csv...')
        atpRegion = ARR_WebRes.Arr()
        atpRegionCode = atpRegion.arealTemporalPatternCode(arr_raw_fname)
        if atpRegionCode:
            try:
                url_atp = f'http://data.arr-software.org//static/temporal_patterns/Areal/Areal_{atpRegionCode}.zip'
                logger.info(f'URL: {url_atp}')
                r = requests.get(url_atp)
                z = zipfile.ZipFile(io.BytesIO(r.content))
                z.extractall(os.path.join(export_path, "data"))
                atpIncFiles = [x.filename for x in z.filelist]
                atpInc = ""
                for f in atpIncFiles:
                    if 'INCREMENTS' in f.upper():
                        atpInc = f
                areal_tp_download = os.path.join(export_path, "data", atpInc)
                if os.path.exists(areal_tp_download):
                    logger.info(f'Areal temporal pattern csv: {areal_tp_download}')
                else:
                    logger.info(f'ERROR finding areal temporal pattern csv: {areal_tp_download}')
                    logger.info('skipping step...')
            except Exception as e:
                logger.warning(f"ERROR: failed to download areal temporal pattern.. skipping step. Contact support@tuflow.com\n{e}")
        else:
            logger.warning("WARNING: unable to determine areal temporal pattern region... skipping step")
    else:
        logger.warning("WARNING: User specified areal temporal pattern found... skipping areal pattern download")

    if point_tp_csv is None:  # only check if user has not specified temporal patterns manually
        #print('Checking Temporal Pattern Region...')
        logger.info('Checking Temporal Pattern Region...')
        tpRegionCheck = ARR_WebRes.Arr()
        tpRegion = tpRegionCheck.temporalPatternRegion(arr_raw_fname)
        #print(tpRegion)
        logger.info(tpRegion)
        if tpRegion.upper() == 'RANGELANDS WEST AND RANGELANDS':
            #print("Splitting {0} into separate regions: Rangelands West, Rangelands".format(tpRegion))
            logger.info("Splitting {0} into separate regions: Rangelands West, Rangelands".format(tpRegion))
            if not add_tp or'rangelands west' not in add_tp:
                #print('Adding Rangelands West to additional temporal patterns')
                logger.info('Adding Rangelands West to additional temporal patterns')
                if type(add_tp) is bool:
                    add_tp = []
                add_tp.append("rangelands west")
            else:
                #print("Rangelands West already selected in additional temporal patterns... skipping")
                logger.info("Rangelands West already selected in additional temporal patterns... skipping")
            if not add_tp or 'rangelands' not in add_tp:
                #print('Adding Rangelands to additional temporal patterns')
                logger.info('Adding Rangelands to additional temporal patterns')
                if type(add_tp) is bool:
                    add_tp = []
                add_tp.append("rangelands")
            else:
                #print("Rangelands already selected in additional temporal patterns... skipping")
                logger.info("Rangelands already selected in additional temporal patterns... skipping")

    
    if add_tp != False:
        if len(add_tp) > 0:
            for tp in add_tp:
                add_tpFilename = os.path.join(export_path, 'data', 'ARR_Web_data_{0}_TP_{1}.txt'.format(site_name, tp))
                tpCoord = tpRegion_coords(tp)
                url2 = 'http://data.arr-software.org/?lon_coord={0}5&lat_coord={1}&type=text&All=1' \
                       .format(tpCoord[1], tpCoord[0])

                try:
                    #print('Attempting to access ARR for additional Temporal Pattern: {0}'.format(tp))
                    logger.info('Attempting to access ARR for additional Temporal Pattern: {0}'.format(tp))
                    req = urllib2.Request(url2, None, headers)
                    response = urllib2.urlopen(req)
                    the_page = response.read()
                except urllib2.URLError:
                    #print('Failed to get data from ARR website')
                    logger.error('Failed to get data from ARR website')
                    logging.shutdown()
                    raise SystemExit('Failed to get data from ARR website')

                #print('Saving: {0}'.format(add_tpFilename))
                logger.info('Saving: {0}'.format(add_tpFilename))
                try:
                    fo = open(add_tpFilename, 'wb')
                except PermissionError:
                    #print("File is locked for editing: {0}".format(add_tpFilename))
                    logger.error("File is locked for editing: {0}".format(add_tpFilename))
                    raise SystemExit("ERROR: File is locked for editing: {0}".format(add_tpFilename))
                except IOError:
                    #print("Unexpected error opening file: {0}".format(add_tpFilename))
                    logger.error("Unexpected error opening file: {0}".format(add_tpFilename))
                    raise SystemExit("ERROR: Unexpected error opening file: {0}".format(add_tpFilename))
                fo.write(the_page)
                fo.flush()
                fo.close()
                #print('Done saving file.')
                logger.info('Done saving file.')

# load from file
ARR = ARR_WebRes.Arr()
try:
    ARR.load(arr_raw_fname, catchment_area, add_tp=add_tp, point_tp=point_tp_csv, areal_tp=areal_tp_csv,
             user_initial_loss=user_initial_loss, user_continuing_loss=user_continuing_loss,
             areal_tp_download=areal_tp_download)
except Exception as e:
    logger.error("ERROR: Unable to load ARR data: {0}".format(e))
    logging.shutdown()
    raise SystemExit("ERROR: Unable to load ARR data: {0}".format(e))
if ARR.error:
    #print('ERROR: {0}'.format(ARR.message))
    logger.error('ERROR: {0}'.format(ARR.message))
    #print("ERROR: if problem persists please email input files and log.txt to support@tuflow.com.")
    logger.error("ERROR: if problem persists please email input files and log.txt to support@tuflow.com.")
    logging.shutdown()
    raise SystemExit(ARR.message)

# loop through each AEP and export
#print ('Exporting data...\n')
logger.info('Exporting data...\n')
# noinspection PyBroadException
try:
    # Combine standard and non standard durations
    if len(non_stnd_dur) > 0:
        for len, unit in non_stnd_dur.items():
            duration[len] = unit

    ARR.export(export_path, aep=AEP, dur=duration, name=site_name, format=out_form, bom_data=Bom, climate_change=cc,
               climate_change_years=cc_years, cc_rcp=cc_RCP, area=catchment_area, frequent=frequent_events,
               rare=rare_events, catch_no=catchment_no, out_notation=output_notation, arf_frequent=ARF_frequent,
               min_arf=min_ARF, preburst=preBurst, lossmethod=lossMethod, mar=mar, staticloss=staticLoss,
               add_tp=add_tp, tuflow_loss_method=tuflow_loss_method, urban_initial_loss=urban_initial_loss,
               urban_continuing_loss=urban_continuing_loss, probability_neutral_losses=probability_neutral_losses,
               use_complete_storm=bComplete_storm, preburst_pattern_method=preburst_pattern_method,
               preburst_pattern_dur=preburst_pattern_dur, preburst_pattern_tp=preburst_pattern_tp,
               preburst_dur_proportional=bPreburst_dur_proportional)
except Exception as e:
    #print('ERROR: Unable to export data: {0}'.format(e))
    try:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        logger.error('ERROR: Unable to export data: {0}'.format(e))
        logger.error(f"{traceback.print_exception(exc_type, exc_value, exc_traceback)}")
    finally:
        del exc_type, exc_value, exc_traceback
    #print("ERROR: if problem persists please email input files and log.txt to support@tuflow.com.")
    logger.error("ERROR: if problem persists please email input files and log.txt to support@tuflow.com.")
    logging.shutdown()
    raise SystemExit("Unable to export data")

if ARR.error:
    #print('ERROR: {0}'.format(ARR.message))
    logger.error('ERROR: {0}'.format(ARR.message))
    #print("ERROR: if problem persists please email input files and log.txt to support@tuflow.com.")
    logger.error("ERROR: if problem persists please email input files and log.txt to support@tuflow.com.")
    logging.shutdown()
    raise SystemExit(ARR.message)
else:
    #print('\nDisclaimer: {0}'.format(disclaimer))
    logger.info('\nDisclaimer: {0}'.format(disclaimer))
    #print('\nSCRIPT FINISHED\n')
    logger.info('\nSCRIPT FINISHED\n')
    logging.shutdown()