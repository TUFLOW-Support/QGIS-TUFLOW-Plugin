import geopandas as gpd
import pandas as pd
from pathlib import Path
import re


def increment_last_digits(s):
    # Find the last sequence of digits in the string
    match = re.search(r'\d+$', s)

    if match:
        # Extract the digits
        digits = match.group()

        # Convert to integer and increment
        new_number = int(digits) + 1

        # Format the new number with the same number of digits
        new_digits = f'{new_number:0{len(digits)}d}'

        # Replace the old digits with the new ones
        return re.sub(r'\d+$', new_digits, s)
    else:
        # If no digits found, return the original string
        return s


def increment_layer(filename: str, layername: [str, None]) -> (str, str):
    filename_mod = filename

    layername_mod = None
    if layername is not None and layername != '':
        layername_mod = increment_last_digits(layername)
        if layername_mod == layername:
            layername_mod = layername + '_001'
    else:
        filename_path = Path(filename)
        filename_mod = str(filename_path.with_stem(increment_last_digits(filename_path.stem)))
        if filename_mod == filename:
            filename_mod = str(filename_path.with_stem(filename_path.stem + '_001'))

    return filename_mod, layername_mod


def read_and_concat_layers(filename, layerlist, other_gdfs):
    gdfs = other_gdfs
    for layer in layerlist:
        try:
            gdf = gpd.read_file(filename, layer=layer)
            gdfs.append(gdf)
        except:
            pass  # Was not in the file

    gdf_merged = pd.concat(gdfs)
    return gdf_merged


def read_and_concat_files_layers(file_and_layer_names):
    gdfs = []
    for filename, layername in file_and_layer_names:
        try:
            gdf = gpd.read_file(filename, layer=layername)
            gdfs.append(gdf)
        except:
            pass  # Was not in the file

    gdf_merged = pd.concat(gdfs)
    return gdf_merged
