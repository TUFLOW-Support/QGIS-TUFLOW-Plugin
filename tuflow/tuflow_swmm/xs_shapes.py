import math
import numpy as np
import pandas as pd

import matplotlib.pyplot as plt

width_ratios_list = {
    'BasketHandle':
        np.array([
            0.0, 0.49, 0.667, 0.82, 0.93, 1.00, 1.00, 1.00, 0.997,
            0.994, 0.988, 0.982, 0.967, 0.948, 0.928, 0.904, 0.874,
            0.842, 0.798, 0.75, 0.697, 0.637, 0.567, 0.467, 0.342,
            0.0
        ]),
    'Eggshaped':
        np.array(
            [.0, .3250, .4270, .5080, .5820, .6420, .6960, .7460, .7910,
             .8360, .8660, .8960, .9260, .9560, .9700, .9850, 1.000,
             .9850, .9700, .9400, .8960, .8360, .7640, .6420, .3100,
             .0
             ]),
    'Arch':
        np.array(
            [.0, .6272, .8521, .9243, .9645, .9846, .9964, .9988, .9917, .9811,
             .9680, .9515, .9314, .9101, .8864, .8592, .8284, .7917, .7527, .7065,
             .6544, .5953, .5231, .4355, .3195, .0]
        ),
    'Horiz_Ellipse':
        np.array(
            [.0, .3919, .5426, .6499, .7332, .8000, .8542, .8980, .9330, .9600,
             .9798, .9928, .9992, .9992, .9928, .9798, .9600, .9330, .8980, .8542,
             .8000, .7332, .6499, .5426, .3919, .0]
        ),
    'Vert_Ellipse':
        np.array(
            [.0, .3919, .5426, .6499, .7332, .8000, .8542, .8980, .9330, .9600,
             .9798, .9928, .9992, .9992, .9928, .9798, .9600, .9330, .8980, .8542,
             .8000, .7332, .6499, .5426, .3919, .0]
        ),
}

area_ratios = {
    'CIRCULAR':
        np.array(
            [
                0.0, .00471, .0134, .024446, .0374, .05208, .0680, .08505, .1033, .12236,
                .1423, .16310, .1845, .20665, .2292, .25236, .2759, .29985, .3242, .34874,
                .3736, .39878, .4237, .44907, .4745, .500, .5255, .55093, .5763, .60135,
                .6264, .65126, .6758, .70015, .7241, .74764, .7708, .79335, .8154, .83690,
                .8576, .87764, .8967, .91495, .9320, .94792, .9626, .97555, .9866, .99516,
                1.000
            ]
        ),
}

# required if not here
width_height_ratios = {
    'Circular': 1.0,
    'Force_main': 1.0,
    'Filled_circular': 1.0,
    'Eggshaped': 2.0 / 3.0,
    'Horseshoe': 1.0,
    'Gothic': 0.84,
    'Catenary': 0.9,
    'Semielliptical': 1.0,
    'BasketHandle': 0.944,
    'Semicircular': 1.64,
}

# Standard shapes
standard_area_tables = {
    'Ellipse': [
        1.80, 3.30, 4.10, 5.10, 6.30, 7.40, 8.80, 10.20, 12.90, 16.60, 20.50, 24.80, 29.50, 34.60,
        40.10, 46.10, 52.40, 59.20, 66.40, 74.00, 82.00, 99.20, 118.60
    ],
    'Arch': [
        1.1, 1.65, 2.2, 2.8, 4.4, 6.4, 8.8, 11.4, 14.3, 17.7, 25.6, 34.6,
        44.5, 51.7, 66, 81.8, 99.1, 1.1, 1.6, 2.2, 2.9, 4.5, 6.5, 8.9, 11.6, 14.7, 18.1,
        21.9, 26, 7, 9.4, 12.3, 15.6, 19.3, 23.2, 27.4, 32.1, 37, 42.4, 48, 54.2, 60.5,
        67.4, 74.5, 22, 24, 26, 28, 31, 33, 35, 38, 40, 43, 46, 49, 52, 55, 58, 61, 64, 67,
        71, 74, 78, 81, 85, 89, 93, 97, 101, 105, 109, 113, 118, 122, 126, 131, 97, 102,
        105, 109, 114, 118, 123, 127, 132, 137, 142, 146, 151, 157, 161, 167, 172, 177,
        182, 188, 194, 200, 205, 211
    ],
}

standard_height_tables = {
    'Arch': [
        # Concrete
        11, 13.5, 15.5, 18, 22.5, 26.625, 31.3125, 36, 40, 45, 54, 62, 72, 77.5, 87.125, 96.875, 106.5,
        # Corrugated Steel(2 - 2 / 3 x 1 / 2 inch Corrugation)
        13, 15, 18, 20, 24, 29, 33, 38, 43, 47, 52, 57,
        # Corrugated Steel(3 x 1 inch Corrugation)
        31, 36, 41, 46, 51, 55, 59, 63, 67, 71, 75, 79, 83, 87, 91,
        # Structural Plate(6 x 2 inch Corrugation - Bolted Seams 19 - inch Corner Radius
        55, 57, 59, 61, 63, 65, 67, 69, 71, 73, 75, 77, 79, 81, 83, 85, 87, 89, 91,
        93, 95, 97, 100, 101, 103, 105, 107, 109, 111, 113, 115, 118, 119, 121,

        # Structural Plate(6x2inch Corrugation - Bolted Seams 31 - inch Corner Radius
        112, 114, 116, 118, 120, 122, 124, 126, 128, 130, 132, 134,
        136, 138, 140, 142, 144, 146, 148, 150, 152, 154, 156, 158
    ]
}

standard_width_tables = {
    'Arch': [
        # Concrete
        18, 22, 26, 28.5, 36.25, 43.75, 51.125, 58.5, 65, 73, 88, 102, 115, 122, 138, 154, 168.75,
        # Corrugated Steel (2 2/3 x 1/2 inch corrugation)
        17, 21, 24, 28, 35, 42, 49, 57, 64, 71, 77, 83,
        # Corrugated Steel (3 x 1 inch Corrugation)
        40, 46, 53, 60, 66, 73, 81, 87, 95, 103, 112, 117, 128, 137, 142,
        # Structural Plate (6x2inch Corrugation - Bolted Seams 31-inch corner radius
        159, 162, 168, 170, 173, 179, 184, 187, 190, 195, 198, 204, 206, 209, 215, 217, 223, 225, 231, 234, 236, 239,
        245, 247
    ],
    'MinorAxis_Ellipse': [
        14, 19, 22, 24, 27, 29, 32, 34, 38, 43, 48, 53, 58, 63, 68, 72, 77, 82, 87, 92, 97, 106, 116
    ],
    'MajorAxis_Ellipse': [
        23, 30, 34, 38, 42, 45, 49, 53, 60, 68, 76, 83, 91, 98, 106, 113, 121, 128, 136, 143, 151, 166, 180
    ],
}


def get_case_insensitive_key(input_dict, key):
    return next((dict_key for dict_key, value in input_dict.items() if dict_key.lower() == key.lower()), None)


def is_open_channel(shape):
    return shape.upper() in ['RECT_OPEN', 'IRREGULAR']


def get_height_ratios(width_ratios):
    return np.arange(0.0, 1.01, 1.0 / (len(width_ratios) - 1))


def get_width_vs_height(name, full_height, full_width=None):
    width_ratios = width_ratios_list[name]
    height_ratios = get_height_ratios(width_ratios)

    if full_width is None:
        full_width = width_height_ratios[name]

    widths = width_ratios * full_width
    heights = height_ratios * full_height

    df_height_width = pd.DataFrame(
        {
            'width': widths,
            'height': heights,
        }
    )
    return df_height_width


def get_normalized_value(norm, table):
    nvalues = table.shape[0]
    xcoords = np.linspace(0.0, 1.0, nvalues)
    return np.interp(norm, xcoords, table)


def get_area_partial_circle(diameter, filled_height, full_area):
    return get_normalized_value(filled_height / diameter,
                                area_ratios['CIRCULAR']) * full_area


def get_inches_to_units_width(customary_units):
    conversion = (1.0 / 12.0) if customary_units else 0.0254
    return conversion


def get_inches_to_units_area(customary_units):
    return math.pow(get_inches_to_units_width(customary_units), 2.0)


def get_max_height(shape, customary_units, geom1, geom2=None, geom3=None, geom4=None):
    if shape == 'HORIZ_ELLIPSE':
        if geom3 > 0.0:
            index = int(math.floor(geom3) - 1)
            table = standard_width_tables['MinorAxis_Ellipse']
            if index < 1 or index >= len(table):
                raise ValueError("Invalid size code for horizontal ellipse")
            return table[index] * get_inches_to_units_width(customary_units)
        else:
            return geom1
    elif shape == 'VERT_ELLIPSE':
        if geom3 > 0.0:
            index = int(math.floor(geom3) - 1)
            table = standard_width_tables['MajorAxis_Ellipse']
            if index < 1 or index >= len(table):
                raise ValueError("Invalid size code for horizontal ellipse")
            return table[index] * get_inches_to_units_width(customary_units)
        else:
            return geom1
    elif shape == 'ARCH':
        if geom3 > 0.0:
            index = int(math.floor(geom3) - 1)
            table = standard_height_tables['Arch']
            if index < 1 or index >= len(table):
                raise ValueError("Invalid size code for horizontal ellipse")
            return table[index] * get_inches_to_units_width(customary_units)
        else:
            return geom1

    # Height is generally first field return it if not exception above
    return geom1


def get_max_width(shape, customary_units, geom1, geom2=None, geom3=None, geom4=None):
    if shape == 'CIRCULAR' or shape == 'FORCE_MAIN' or shape == 'FILLED_CIRCULAR':
        return geom1
    elif shape == 'EGGSHAPED':
        return 2.0 / 3.0 * geom1
    elif shape == 'HORSESHOE':
        return geom1
    elif shape == 'GOTHIC':
        return 0.84 * geom1
    elif shape == 'CATENARY':
        return 0.9 * geom1
    elif shape == 'SEMIELLIPTICAL':
        return geom1
    elif shape == 'BASKETHANDLE':
        return 0.944 * geom1
    elif shape == 'SEMICIRCULAR':
        return 1.64 * geom1
    elif shape == 'TRAPEZOIDAL':
        yfull = geom1
        ybot = geom2
        slope1 = geom3
        slope2 = geom4
        avg_slope = (slope1 + slope2) * 0.5
        rbot = math.sqrt(1.0 + slope1 * slope1) + math.sqrt(1.0 + slope2 * slope2)
        wmax = ybot + yfull * (slope1 + slope2)
        return wmax
    elif shape == 'HORIZ_ELLIPSE':
        if geom3 > 0.0:
            index = int(math.floor(geom3) - 1)
            table = standard_width_tables['MajorAxis_Ellipse']
            if index < 1 or index >= len(table):
                raise ValueError("Invalid size code for horizontal ellipse")
            return table[index] * get_inches_to_units_width(customary_units)
        else:
            wmax = geom2
            return wmax
    elif shape == 'VERT_ELLIPSE':
        if geom3 > 0.0:
            index = int(math.floor(geom3) - 1)
            table = standard_width_tables['MinorAxis_Ellipse']
            if index < 1 or index >= len(table):
                raise ValueError("Invalid size code for horizontal ellipse")
            return table[index] * get_inches_to_units_width(customary_units)
        else:
            wmax = geom2
            return wmax
    elif shape == 'ARCH':
        if geom3 > 0.0:
            index = int(math.floor(geom3) - 1)
            table = standard_width_tables['Arch']
            if index < 1 or index >= len(table):
                raise ValueError("Invalid size code for horizontal ellipse")
            return table[index] * get_inches_to_units_width(customary_units)
        else:
            wmax = geom2
            return wmax

    # Width is generally second field return it if not exception above
    return geom2


def get_max_area(shape, customary_units, geom1, geom2=None, geom3=None, geom4=None):
    if shape == 'CIRCULAR' or shape == 'FORCE_MAIN':
        return math.pi / 4.0 * geom1 * geom1
    elif shape == 'RECT_OPEN' or shape == 'RECT_CLOSED':
        return geom1 * geom2
    elif shape == 'FILLED_CIRCULAR':
        full_area = math.pi / 4.0 * geom1 * geom1
        return full_area - get_area_partial_circle(geom1, geom2, full_area)
    elif shape == 'EGGSHAPED':
        return 0.5105 * geom1 * geom1
    elif shape == 'HORSESHOE':
        return 0.8293 * geom1 * geom1
    elif shape == 'GOTHIC':
        return 0.6554 * geom1 * geom1
    elif shape == 'CATENARY':
        return 0.70277 * geom1 * geom1
    elif shape == 'SEMIELLIPTICAL':
        return 0.785 * geom1 * geom1
    elif shape == 'BASKETHANDLE':
        return 0.7862 * geom1 * geom1
    elif shape == 'SEMICIRCULAR':
        return 1.2697 * geom1 * geom1
    elif shape == 'RECT_TRIANG':
        yfull = geom1
        wmax = geom2
        ybot = geom3
        abot = ybot * wmax / 2.0
        area = wmax * (yfull - ybot / 2.0)
        return area
    elif shape == 'RECT_ROUND':
        yfull = geom1
        wmax = geom2
        rbot = geom3
        theta = 2.0 * math.asin(wmax / 2.0 / rbot)
        ybot = rbot * (1.0 - math.cos(theta / 2.0))
        abot = rbot * rbot / 2.0 * (theta - math.sin(theta))
        area = wmax * (yfull - ybot) + abot
        return area
    elif shape == 'MOD_BASKET':
        yfull = geom1
        wmax = geom2
        rbot = geom3

        if rbot < wmax / 2.0:
            rbot = wmax / 2.0

        theta = 2.0 * math.asin(wmax / 2.0 / rbot)
        ybot = rbot * (1.0 - math.cos(theta / 2.0))
        if ybot > yfull:
            raise ValueError("Invalid modified basket handle shape")

        abot = rbot * rbot / 2.0 * (theta - math.sin(theta))
        area = (yfull - ybot) * wmax + abot
        return area

    elif shape == 'TRAPEZOIDAL':
        yfull = geom1
        ybot = geom2
        slope1 = geom3
        slope2 = geom4
        avg_slope = (slope1 + slope2) * 0.5
        rbot = math.sqrt(1.0 + slope1 * slope1) + math.sqrt(1.0 + slope2 * slope2)
        wmax = ybot + yfull * (slope1 + slope2)
        area = (ybot + avg_slope * yfull) * yfull
        return area

    elif shape == 'TRIANGULAR':
        yfull = geom1
        wmax = geom2
        sbot = wmax / yfull / 2.0
        area = yfull * yfull * sbot
        return area

    elif shape == 'PARABOLIC':
        yfull = geom1
        wmax = geom2
        area = (2. / 3.) * yfull * wmax
        return area

    elif shape == 'POWERFUNC':
        yfull = geom1
        wmax = geom2
        sbot = 1.0 / geom3
        area = yfull * wmax / (sbot + 1)
        return area

    elif shape == 'HORIZ_ELLIPSE' or shape == 'VERT_ELLIPSE':
        if geom3 > 0.0:
            index = int(math.floor(geom3) - 1)
            table = standard_area_tables['Ellipse']
            if index < 1 or index >= len(table):
                raise ValueError("Invalid size code for horizontal ellipse")
            return table[index] * get_inches_to_units_area(customary_units)
        else:
            yfull = geom1
            wmax = geom2
            return math.pi * yfull / 2.0 * wmax / 2.0

    elif shape == 'ARCH':
        if geom3 > 0.0:
            index = int(math.floor(geom3) - 1)
            table = standard_area_tables['Arch']
            if index < 1 or index >= len(table):
                raise ValueError("Invalid size code for horizontal ellipse")
            return table[index] * get_inches_to_units_area(customary_units)
        else:
            yfull = geom1
            wmax = geom2
            return 0.7879 * yfull * wmax

    elif shape == 'IRREGULAR':
        return 1.0  # We can't compute it here but this avoids an error

    # Must not have a valid shape - just return 0 to prevent exception
    # raise ValueError(f"Invalid shape type: {shape}")
    return 0.0


# Returns coordinates for top half of shape ignores initial shape width decreases
def get_xz_top(shape, customary_units, lower_left, geom1, geom2=None, geom3=None, geom4=None):
    height = geom1
    width = geom2

    key = get_case_insensitive_key(width_ratios_list, shape)
    if key:
        shape = key

    df = get_width_vs_height(shape, geom1, geom2)

    # remove decreasing portion
    df['dwidth'] = df['width'] - df['width'].shift(-1)
    df = df.fillna(1.0)
    df = df[df['dwidth'] > 0]

    # renormalize
    df['height_renorm'] = df['height'] - df['height'].min()
    df['height_renorm'] = df['height_renorm'] / df['height_renorm'].max()

    df['width_renorm'] = df['width'] / df['width'].max()

    center_x = lower_left[0] + df['width'].max() / 2.0

    df['x1'] = center_x - df['width_renorm'] * width/2.0
    df['x2'] = center_x + df['width_renorm'] * width/2.0

    df['z'] = lower_left[1] + df['height_renorm'] * height

    x_arr = np.hstack([df['x1'].values, df['x2'].values[::-1]])
    z_arr = np.hstack([df['z'].values, df['z'].values[::-1]])

    return x_arr, z_arr


if __name__ == "__main__":
    df_basket = get_width_vs_height('BasketHandle', 2.0)

    df_arch = get_width_vs_height('Arch', 5.0, 15.0)
    print(df_arch)
