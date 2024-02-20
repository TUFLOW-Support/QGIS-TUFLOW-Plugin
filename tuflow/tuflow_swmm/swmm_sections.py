from __future__ import annotations

from collections import defaultdict
from datetime import datetime, date
from enum import Enum
from itertools import chain
from typing import List, Any, Sequence, Union

import numpy as np
import pandas as pd
import warnings

from tuflow_swmm.swmm_processing_feedback import ScreenProcessingFeedback


class SectionType(Enum):
    NO_KEYWORDS = 0  # No keywords defining different options
    KEYWORDS = 1
    GEOMETRY = 2
    WIDE = 3  # Similar to keywords but options are converted from multi-line to wide format


class GeometryType(Enum):
    NODES = 0
    CONDUITS = 1
    LINKS = 2
    INLETS = 3
    SUBCATCHMENTS = 4
    MISC = 5


# These are used to build the COORDINATES dataframe
primary_node_sections = {
    'Junctions',
    'Outfalls',
    'Dividers',
    'Inflows',
    'Storage',
}

primary_link_sections = {
    'Conduits',
    'Pumps',
    'Weirs',
    'Orifices',
    'Outlets',
}

# Section merges: list of tuplies (prefix, table, merge_col1, merge_col2)
sections_to_append = {
    'Conduits': [
        ('xsec', 'XSections', 'Name', 'Link'),
        ('losses', 'Losses', 'Name', 'Link'),
    ],
    'Orifices': [
        ('xsec', 'XSections', 'Name', 'Link'),
    ],
    'Weirs': [
        ('xsec', 'XSections', 'Name', 'Link'),
    ],
    'Subcatchments': [
        ('Subareas', 'Subareas', 'Name', 'Subcatchment'),
        ('Infiltration', 'Infiltration', 'Name', 'Subcatchment'),
    ]
}

# Tables that have the tag option and the object type
tag_table_type = {
    'Conduits': 'Link',
    'Orifices': 'Link',
    'Outlets': 'Link',
    'Pumps': 'Link',
    'Weirs': 'Link',
    'Dividers': 'Node',
    'Junctions': 'Node',
    'Outfalls': 'Node',
    'Storage': 'Node',
    'Subcatchments': 'Subcatch',
    'Raingages': 'RainGage',
}

# These are the tables that support descriptions
tables_with_description = {
    'Raingages',
    'Subcatchments',
    'Landuses',
    'Junctions',
    'Outfalls',
    'Dividers',
    'Storage',
    'Conduits',
    'Pumps',
    'Weirs',
    'Orifices',
    'Outlets',
    'Curves',
    'Timeseries',
    'Patterns',
}


class SwmmSection:
    name: str

    def __init__(self,
                 name: str,
                 prefix: str,
                 geomtype: Union[GeometryType, None],
                 sec_type: SectionType,
                 cols_common_start: Sequence[tuple[str, Any]],
                 cols_keywords: dict[str, Sequence[tuple[str, Any]]] = None,
                 keyword_col: Union[int, None] = None,
                 cols_common_end: Sequence[tuple[str, Any]] | None = None):
        self.name = name
        self.prefix = prefix
        self.geometry = geomtype
        self.section_type = sec_type
        self.cols_common_start = cols_common_start
        self.cols_keywords = cols_keywords
        self.keyword_col = keyword_col  # 0 based
        self.cols_common_end = cols_common_end
        self.custom_mapping = False  # Don't pass as argument set separately because it is rare

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.__str__()

    def long_name(self):
        return f'{self.prefix}--{self.name}' if self.prefix != '' else self.name

    def get_all_columns(self):
        all_cols = {x[0]: x[1] for x in self.cols_common_start}

        if self.section_type == SectionType.KEYWORDS:
            for keyword_cols in filter(lambda z: z is not None, self.cols_keywords.values()):
                all_cols.update({x[0]: x[1] for x in filter(lambda y: y is not None, keyword_cols)})

            # Add common columns at the end
            if self.cols_common_end:
                all_cols.update({x[0]: x[1] for x in self.cols_common_end})

        return all_cols

    def get_all_column_types(self):
        return self.get_all_columns().values()

    def get_all_column_names(self):
        return self.get_all_columns().keys()

    def convert_gpkg_df_to_swmm(self, df, feedback=ScreenProcessingFeedback()):
        swmm_cols = []

        # We want nullable integers and have to use 'Int64' (see
        # https://pandas.pydata.org/pandas-docs/stable/user_guide/integer_na.html)
        for col, coltype in self.cols_common_start:
            if coltype == int:
                df[col] = df[col].astype('float').astype('Int64')

        # Coverages and loadings work fine using the non-custom method for this direction
        if self.custom_mapping and self.name not in ["Coverages", "Loadings", "Patterns"]:
            # Temp
            swmm_cols = [x[0] for x in self.cols_common_start]
            if 'Description' in df.columns:
                swmm_cols.append('Description')

            if self.name == 'Transects':
                nc_cols = ['Name', 'Nleft', 'Nright', 'Nchanl']
                df_nc = df[nc_cols].copy(deep=True)
                df_nc['Datatype'] = 'NC'
                df_nc = df_nc[['Datatype'] + nc_cols]

                df['Datatype'] = 'X1'
                df['Name2'] = df['Name']
                df['Nsta'] = 'Nsta'  # Will be replaced layer
                df['dummy1'] = '0'
                df['dummy2'] = '0'
                df['dummy3'] = '0'
                df_x1 = df[[
                    'Datatype',
                    'Name',
                    'Name2',
                    'Nsta',
                    'Xleft',
                    'Xright',
                    'dummy1',
                    'dummy2',
                    'dummy3',
                    'Lfactor',
                    'Wfactor',
                    'Eoffset']]
                # We need a name, datatype, and param columns
                df_nc.columns = ['Datatype', 'Name'] + [f'Param{x + 1}' for x, _ in enumerate(df_nc.columns[2:])]
                df_x1.columns = ['Datatype', 'Name'] + [f'Param{x + 1}' for x, _ in enumerate(df_x1.columns[2:])]
                df_nc = df_nc.astype(str)
                df_x1 = df_x1.astype(str)
                df_out = pd.concat([df_nc, df_x1]).sort_values('Name', kind='stable')

                df = df_out
            elif self.name == 'Transects_coords':
                df['Datatype'] = 'GR'
                df = df[['Datatype', 'Name', 'Elev', 'Station']]
                df = df.rename(columns={
                    'Elev': 'Param1',
                    'Station': 'Param2',
                })
            elif self.name == 'Inlets':
                # This may end up being split between two lines
                swmm_cols = ['Name', 'Type', 'Param1', 'Param2', 'Param3', 'Param4', 'Param5']

                combo_rows = df['Type'] == 'COMBINATION'
                # Duplicate combo-rows and assign them to 'CURB'
                df_combo_curb = df[combo_rows].copy(deep=True)
                df_combo_curb['Type'] = 'CURB'
                # Set original combo rows to GRATE and merge curb in
                df.loc[combo_rows, 'Type'] = 'GRATE'

                df = pd.concat([df, df_combo_curb], axis=0)
                # print(df)

                grate_rows = (df['Type'].str.upper() == 'GRATE') | (df['Type'].str.upper() == 'DROP_GRATE')
                curb_rows = (df['Type'].str.upper() == 'CURB') | (df['Type'].str.upper() == 'DROP_CURB')
                slotted_rows = df['Type'].str.upper() == 'SLOTTED'
                custom_rows = df['Type'].str.upper() == 'CUSTOM'

                # initialize Param1-5 columns
                for col in swmm_cols[2:]:
                    df[col] = None

                # Copy values from appropriate columns
                df.loc[grate_rows, 'Param1'] = df.loc[grate_rows, 'Grate_Length']
                df.loc[grate_rows, 'Param2'] = df.loc[grate_rows, 'Grate_Width']
                df.loc[grate_rows, 'Param3'] = df.loc[grate_rows, 'Grate_Type']
                df.loc[grate_rows, 'Param4'] = df.loc[grate_rows, 'Grate_Aopen']
                df.loc[grate_rows, 'Param5'] = df.loc[grate_rows, 'Grate_vsplash']

                df.loc[curb_rows, 'Param1'] = df.loc[curb_rows, 'Curb_Length']
                df.loc[curb_rows, 'Param2'] = df.loc[curb_rows, 'Curb_Height']
                df.loc[curb_rows, 'Param3'] = df.loc[curb_rows, 'Curb_Throat']

                df.loc[slotted_rows, 'Param1'] = df.loc[slotted_rows, 'Slotted_Length']
                df.loc[slotted_rows, 'Param2'] = df.loc[slotted_rows, 'Slotted_Width']

                df.loc[custom_rows, 'Param1'] = df.loc[custom_rows, 'Custom_Curve']

                df = df[swmm_cols]

            elif self.name == 'Timeseries':
                swmm_cols = ['Name', 'Date', 'Time', 'Value']
                if 'Description' in df.columns:
                    swmm_cols.append('Description')
                # if Fname is filled in we are reading from a file date->FILE and Time->Filename
                df.loc[~df['Fname'].isnull(), 'Date'] = 'FILE'
                df.loc[~df['Fname'].isnull(), 'Time'] = df.loc[~df['Fname'].isnull(), 'Fname']
                df['Value'] = df['Value'].astype(str).replace({'nan': '', '<NA': ''})

                df = df[swmm_cols]

            elif self.name == 'Curves':
                # Just replace nan with spaces and it will be a valid file
                df = df[swmm_cols].astype(str).replace({'nan': '', '<NA>': ''})
            else:
                raise ValueError("Need to finish for case")
        elif self.section_type == SectionType.WIDE:
            # for common columns nothing needed except convert to text
            swmm_cols = [x[0] for x in self.cols_common_start]

            # for variable columns and end columns they will be reduced to a few with generic names (Param1, Param2)
            # convert to nullable integers
            for k, v in self.cols_keywords.items():
                if v:
                    for col, coltype in v:
                        if coltype == int:
                            df[col] = df[col].astype('Int64')

            # We need to stack the dataframe
            df_lines = []
            for prefix, cols in self.cols_keywords.items():
                cols = swmm_cols + [f'{prefix}_{col[0]}'.lstrip('_') for col in cols]
                df_line = df[cols].copy(deep=True)
                # Need to insert prefix if it is not ''
                old_cols = df_line.columns
                if prefix != '':
                    df_line.loc[:, 'Prefix'] = prefix.upper()
                    new_cols = [old_cols[0]] + ['Prefix'] + list(old_cols[1:])
                    df_line = df_line[new_cols]
                df_line.columns = [df_line.columns[0]] + [f'Param_{i + 1}' for i, _ in enumerate(df_line.columns[1:])]
                df_line = df_line.reindex(sorted(df_line.columns), axis=1)

                # Remove blank lines
                if prefix != '':
                    df_line = df_line.dropna(how='all', subset=df_line.columns[2:])

                df_lines.append(df_line)

            df = pd.concat(df_lines)
        else:
            # for common columns nothing needed except convert to text
            swmm_cols = [x[0] for x in self.cols_common_start]

            # for variable columns and end columns they will be reduced to a few with generic names (Param1, Param2)
            if self.section_type == SectionType.KEYWORDS:
                # convert ot nullable integers
                for k, v in self.cols_keywords.items():
                    if v:
                        for col, coltype in v:
                            if coltype == int:
                                df[col] = df[col].astype('Int64')

                num_variable_columns = max([len(x) for x in self.cols_keywords.values() if x is not None])
                variable_cols = [f'Param{x}' for x in range(1, num_variable_columns + 1)]
                swmm_cols.extend(variable_cols)
                if self.cols_common_end:
                    swmm_cols.extend([x[0] for x in self.cols_common_end])

                df[variable_cols] = None

                for k, v in self.cols_keywords.items():
                    param_num = 1
                    col_keyword_name = df.columns[self.keyword_col]
                    if k == 'Default':
                        keyword_rows = ~df[col_keyword_name].isin(self.cols_keywords.keys())
                    else:
                        keyword_rows = df[col_keyword_name] == k
                    if v:
                        for gpkg_col in v:
                            with warnings.catch_warnings():
                                warnings.simplefilter(action='ignore', category=FutureWarning)
                                df.loc[keyword_rows, f'Param{param_num}'] = \
                                    df.loc[keyword_rows, gpkg_col[0]]
                            param_num = param_num + 1

            # Add tag column if it exists
            if 'Tag' in df.columns:
                swmm_cols.append('Tag')

            # Keep description column if it exists
            if 'Description' in df.columns:
                swmm_cols.append('Description')

            df = df[swmm_cols].astype(str).replace({'nan': '', '<NA>': ''})
            # df = df[swmm_cols].applymap(lambda x: str(x) if pd.isnull(x) else None)

        # If we are the options table we may need to convert date formats
        if self.name == 'Options':
            date_fields = ['START_DATE', 'REPORT_START_DATE', 'END_DATE']
            for date_field in date_fields:
                if len(df[df['Option'] == date_field]) > 0:
                    date_text = df.loc[df['Option'] == date_field, 'Value'].iloc[0]
                    try:
                        conv_date = datetime.fromisoformat(date_text).date()
                        df.loc[df['Option'] == date_field, 'Value'] = conv_date.strftime('%m/%d/%Y')
                    except ValueError:
                        # Wasn't an isoformat nothing to do
                        pass

        return df

    def convert_text_to_dataframe(self, text_array, extra_dfs, feedback=ScreenProcessingFeedback()):

        # Strip out any description statements (use a single ;) and store
        descriptions = {}
        curr_descript = ''
        out_lines = []
        for line in text_array:
            if line.startswith(';'):
                curr_descript = line[1:]
            else:
                start_word = line.split(' ')[0]
                if curr_descript != '':
                    descriptions[start_word] = curr_descript
                    curr_descript = ''
                out_lines.append(line)

        text_array = out_lines

        df = None
        if self.custom_mapping:
            if self.name.upper() == 'TRANSECTS':
                section_text_values = \
                    [[y.strip() for y in x.split()] for x in text_array]

                section_data = {
                    'Name': [],
                    'Xleft': [],
                    'Xright': [],
                    'Lfactor': [],
                    'Wfactor': [],
                    'Eoffset': [],
                    'Nleft': [],
                    'Nright': [],
                    'Nchanl': [],
                }
                section_data_coords = {
                    'Name': [],
                    'Elev': [],
                    'Station': [],
                }
                curr_name = None
                curr_n_values = None
                curr_elev_stations = []
                for row in section_text_values:
                    data_type = row[0]
                    if data_type.upper() == 'NC':
                        curr_n_values = [float(x) for x in row[1:4]]
                    elif data_type.upper() == 'X1':
                        curr_name = row[1]
                        section_data['Name'].append(curr_name)
                        # Skip Nsta because we are not going to store
                        section_data['Xleft'].append(row[3])
                        section_data['Xright'].append(row[4])
                        # Skip unused 0 0 0
                        lfactor = 0.
                        wfactor = 0.
                        eoffset = 0.
                        try:
                            lfactor = row[8]
                            wfactor = row[9]
                            eoffset = row[10]
                        except:
                            pass  # defaulted
                        section_data['Lfactor'].append(lfactor)
                        section_data['Wfactor'].append(wfactor)
                        section_data['Eoffset'].append(eoffset)
                        # Add the current n values
                        section_data['Nleft'].append(curr_n_values[0])
                        section_data['Nright'].append(curr_n_values[1])
                        section_data['Nchanl'].append(curr_n_values[2])
                    elif data_type.upper() == 'GR':
                        # starting with row1 we have pairs of elev/station
                        for elev, station in zip(row[1::2], row[2::2]):
                            section_data_coords['Name'].append(curr_name)
                            section_data_coords['Elev'].append(elev)
                            section_data_coords['Station'].append(station)
                    # Create the dataframe
                    df = pd.DataFrame(section_data)
                    # Create the coords dataframe
                    extra_dfs['Transects_coords'] = pd.DataFrame(section_data_coords)

            if self.name == 'Patterns':
                section_data = {x[0]: list() for x in self.cols_common_start}
                section_text_values = \
                    [[y.strip() for y in x.split()] for x in text_array]

                curr_name = None
                curr_interval = None
                curr_factors = []
                for row in section_text_values:
                    row_vals = {x[0]: None for x in self.cols_common_start}

                    name = row[0]

                    if curr_name is not None:
                        if name == curr_name:
                            # Continuing from previous addd to factors
                            for icol in range(1, len(row)):
                                curr_factors.append(float(row[icol]))
                        else:
                            # We finished an entry
                            row_vals['Name'] = curr_name
                            row_vals['Interval'] = curr_interval
                            for ifact in range(0, len(curr_factors)):
                                row_vals[f'Factor{ifact + 1}'] = curr_factors[ifact]

                            # Add row to the table
                            for row_col, row_val in row_vals.items():
                                section_data[row_col].append(row_val)

                            # Start next entry
                            curr_name = name
                            curr_interval = row[1]
                            curr_factors = []

                            for icol in range(2, len(row)):
                                curr_factors.append(float(row[icol]))
                    else:  # No current entry
                        # Start next entry
                        curr_name = name
                        curr_interval = row[1]
                        curr_factors = []

                        for icol in range(2, len(row)):
                            curr_factors.append(float(row[icol]))

                # Do the final entry
                row_vals = {x[0]: None for x in self.cols_common_start}
                row_vals['Name'] = curr_name
                row_vals['Interval'] = curr_interval
                for ifact in range(0, len(curr_factors)):
                    row_vals[f'Factor{ifact + 1}'] = curr_factors[ifact]
                for row_col, row_val in row_vals.items():
                    section_data[row_col].append(row_val)

                # Create the dataframe
                df = pd.DataFrame(section_data)

            elif self.name == 'Timeseries':
                section_data = {x[0]: list() for x in self.cols_common_start}
                section_text_values = \
                    [[y.strip() for y in x.split()] for x in text_array]

                for row in section_text_values:
                    row_vals = {x[0]: None for x in self.cols_common_start}

                    row_vals['Name'] = row[0]

                    # See if we are a file
                    if row[1] == 'FILE':
                        row_vals['Fname'] = row[2]
                    else:
                        # See if the next entry is a date
                        date = None
                        try:
                            try:
                                # print(row[1])
                                date = datetime.strptime(row[1], '%m-%d-%Y')
                                # print(date)
                            except:
                                try:
                                    date = datetime.strptime(row[1], '%m/%d/%Y')
                                except:
                                    # Must not have been a date field
                                    # print('Not date')
                                    pass
                            curr_date = date
                        except BaseException as e:
                            # print(e)
                            pass

                        # If we have a date the time should be in the next column
                        timecol = 1
                        if date:
                            row_vals['Date'] = row[1]
                            timecol = 2

                        # We can have pairs of time/value on lines that we will write as multiple entries
                        for icol in range(timecol, len(row) - 1, 2):
                            row_vals['Time'] = row[icol]
                            row_vals['Value'] = float(row[icol + 1])

                            # Add row to the table
                            for row_col, row_val in row_vals.items():
                                section_data[row_col].append(row_val)
                df = pd.DataFrame(section_data)

            if self.name == 'Coverages' or self.name == 'Loadings':
                # After the first column can be any number of pairs of Landuse/Percent add to different rows
                section_data = {x[0]: list() for x in self.cols_common_start}
                section_text_values = \
                    [[y.strip() for y in x.split()] for x in text_array]

                for row in section_text_values:
                    # print(row)
                    subcatchment = str(row[0])
                    for i in range(1, len(row) - 1):
                        section_data[self.cols_common_start[0][0]].append(str(subcatchment))
                        section_data[self.cols_common_start[1][0]].append(str(row[i]))
                        section_data[self.cols_common_start[2][0]].append(float(row[i + 1]))

                df = pd.DataFrame(section_data)

            if self.name == 'Curves':
                # Read curves where First row with a new curve has a type
                # row1 may have first curve points x,y
                # after row1 there is no type just x and y values
                section_text_values = \
                    [[y.strip() for y in x.split()] for x in text_array]

                curves_data = {x[0]: list() for x in self.cols_common_start}

                curr_curve = None
                curr_type = None
                first_points = True

                for row in section_text_values:
                    # print(row)
                    curve_name = row[0]

                    coord_col = 1
                    if curve_name != curr_curve:
                        # New curve
                        curr_curve = curve_name
                        curr_type = row[1]
                        coord_col = 2
                        first_points = True

                    # Read pairs of coordinates and add to curve
                    while coord_col + 1 < len(row):
                        x = float(row[coord_col])
                        y = float(row[coord_col + 1])
                        # print(x)
                        # print(y)

                        curves_data['Name'].append(curve_name)
                        curves_data['Type'].append(curr_type if first_points else None)
                        curves_data['xval'].append(x)
                        curves_data['yval'].append(y)
                        first_points = False

                        coord_col += 2
                df = pd.DataFrame(curves_data)

            elif self.name == 'Inlets':  # Use wide format and use COMBINATION for Curb/Grate combination
                section_text_values = \
                    [[y.strip() for y in x.split()] for x in text_array]
                inlet_cols_list = [x[0] for x in self.cols_common_start]
                # print(inlet_cols_list)
                inlet_data = {x: list() for x in inlet_cols_list}
                # print(inlet_data.keys())

                curr_name = None
                row_vals = None

                for row in section_text_values:
                    name = row[0]
                    type = row[1]

                    if name == curr_name:  # Continued from before
                        row_vals['Type'] = 'COMBINATION'
                    else:
                        if curr_name:  # We previously set row values
                            for row_col, row_val in row_vals.items():
                                inlet_data[row_col].append(row_val)
                        # default values
                        row_vals = {x: None for x in inlet_data.keys()}
                        row_vals['Name'] = name
                        row_vals['Type'] = type
                        curr_name = name

                    if type.upper() == 'GRATE' or type.upper() == 'DROP_GRATE':
                        row_vals['Grate_Length'] = float(row[2])
                        row_vals['Grate_Width'] = float(row[3])
                        row_vals['Grate_Type'] = row[4]
                        row_vals['Grate_Aopen'] = float(row[5]) if len(row) > 5 else None
                        row_vals['Grate_vsplash'] = float(row[6]) if len(row) > 6 else None
                    elif type.upper() == 'CURB' or type.upper() == 'DROP_CURB':
                        row_vals['Curb_Length'] = float(row[2])
                        row_vals['Curb_Height'] = float(row[3])
                        row_vals['Curb_Throat'] = row[4] if len(row) > 4 else None
                    elif type.upper() == 'SLOTTED':
                        row_vals['Slotted_Length'] = float(row[2])
                        row_vals['Slotted_Width'] = float(row[3])
                    else:  # Must be custom
                        row_vals['Custom_Curve'] = row[2]

                # Add the last row of values
                if curr_name:  # We previously set row values
                    for row_col, row_val in row_vals.items():
                        inlet_data[row_col].append(row_val)

                df = pd.DataFrame(inlet_data)
        else:
            if self.section_type == SectionType.KEYWORDS:
                # Handle non-keyword columns (front)
                section_text_values = \
                    [[y.strip() for y in x.split()] for x in text_array]

                section_data = {}
                for i_col, (col_name, col_type) in enumerate(self.cols_common_start):
                    values = [col_type(x[i_col]) if i_col < len(x) else None for x in section_text_values]
                    section_data[col_name] = values

                # Handle keyword columns
                keyword_cols_list = [[z[0] for z in y] for y in self.cols_keywords.values() if y is not None]
                # print(keyword_cols_list)
                keyword_cols = {x: list() for x in chain.from_iterable(keyword_cols_list)}
                # print(keyword_cols.keys())

                # Prep non-keyword end columns
                end_cols = None
                if self.cols_common_end:
                    end_cols = {x[0]: list() for x in self.cols_common_end}

                i_first_key_col = len(self.cols_common_start)
                for irow, row in enumerate(section_text_values):
                    # print(row)
                    # default values
                    row_vals = {x: None for x in keyword_cols.keys()}

                    key_val = row[self.keyword_col].upper()
                    # print(key_val)
                    key_definitions = self.cols_keywords[key_val] if key_val in self.cols_keywords else \
                        self.cols_keywords['Default']
                    # print(key_definitions)

                    last_key_col = i_first_key_col
                    if key_definitions is not None:
                        for i_key_col, (k, v) in enumerate(key_definitions):
                            i_key_col_actual = i_key_col + i_first_key_col
                            if i_key_col_actual < len(row):
                                if v == int:
                                    try:
                                        row_vals[k] = v(row[i_key_col_actual])
                                    except ValueError:
                                        # Couldn't convert try double first
                                        feedback.pushInfo(f'Expecting integer for {irow + 1} of section {self.name}. '
                                                          f'Converting as float.')
                                        row_vals[k] = v(float(row[i_key_col_actual]))
                                else:
                                    row_vals[k] = v(row[i_key_col_actual])
                                last_key_col = i_key_col_actual
                            else:
                                row_vals[k] = None

                    for row_col, row_val in row_vals.items():
                        keyword_cols[row_col].append(row_val)

                    # Handle non-keyword columns end
                    if self.cols_common_end:
                        i_first_end_col = last_key_col + 1
                        for i_col, (col_name, col_type) in enumerate(self.cols_common_end):
                            end_col = i_col + i_first_end_col
                            end_cols[col_name].append(col_type(row[end_col]) if end_col < len(row) else None)

                #     values = [col_type(x[end_col]) if end_col < len(x) else None for x in
                #               section_text_values]

                section_data.update(keyword_cols)
                if self.cols_common_end:
                    section_data.update(end_cols)
                # print(section_data)

                # Handle non-keyword columns end
                # i_first_end_col = i_first_key_col + len(keyword_cols.keys())
                # for i_col, (col_name, col_type) in enumerate(self.cols_common_end):
                #     end_col = i_col + i_first_end_col
                #     print(end_col)
                #     values = [col_type(x[end_col]) if end_col < len(x) else None for x in
                #               section_text_values]
                #     print(values)
                #     section_data[col_name] = values

            elif self.section_type == SectionType.WIDE:
                # Handle non-keyword columns (front)
                section_text_values = \
                    [[y.strip() for y in x.split()] for x in text_array]

                # Handle keyword columns
                # keyword_cols_list = [[z[0] for z in y] for y in self.cols_keywords.values() if y is not None]
                keyword_cols_list = [[f'{prefix}_{z[0]}' for z in y] for prefix, y in
                                     self.cols_keywords.items() if y is not None]
                keyword_cols = {x: list() for x in chain.from_iterable(keyword_cols_list)}
                # remove initial _ (blank prefix)
                keyword_cols = {k.lstrip('_'): v for k, v in keyword_cols.items()}

                prefixes = [x.upper() for x in self.cols_keywords.keys() if x != '']
                prefix_col = len(self.cols_common_start)

                # Prep non-keyword end columns
                end_cols = None
                if self.cols_common_end:
                    end_cols = {x[0]: list() for x in self.cols_common_end}

                # print(section_text_values)

                # We need to combine the values from multiple rows based on the initial value (some kind of id field)
                curr_index = -1
                curr_name = None
                curr_values = {}

                all_values = []

                for irow, row in enumerate(section_text_values):
                    name = row[0]
                    # print(name)

                    if name != curr_name:
                        if curr_name is not None:
                            # print(curr_values)
                            all_values.append(curr_values)

                        curr_index = curr_index + 1
                        curr_name = name
                        curr_values = {self.cols_common_start[0][0]: name}
                        curr_values.update({x: None for x in keyword_cols.keys()})

                    # Handle common values for row - only support first row (name) for now
                    # for i_col, (col_name, col_type) in enumerate(self.cols_common_start):
                    #    curr_values[col_name] = col_type(row[i_col]) if i_col < len(row) else None

                    # Handle keywords
                    keyword = row[prefix_col].lower()

                    if keyword in self.cols_keywords.keys():
                        key_definitions = self.cols_keywords[keyword]
                        if key_definitions is not None:
                            for i_key_col, (k, v) in enumerate(key_definitions):
                                i_key_col_actual = i_key_col + prefix_col + 1
                                if i_key_col_actual < len(row):
                                    col = f'{keyword}_{k}'
                                    if v == int:
                                        try:
                                            curr_values[col] = v(row[i_key_col_actual])
                                        except ValueError:
                                            # Couldn't convert try double first
                                            feedback.pushInfo(
                                                f'Expecting integer for {irow + 1} of section {self.name}. '
                                                f'Converting as float.')
                                            curr_values[col] = v(float(row[i_key_col_actual]))
                                    else:
                                        curr_values[col] = v(row[i_key_col_actual])
                                    last_key_col = i_key_col_actual
                    else:
                        # row is for assigning to empty prefix
                        curr_values[self.cols_keywords[''][0][0]] = keyword

                # Get the last values
                if curr_name is not None:
                    # print(curr_values)
                    all_values.append(curr_values)

                section_data = defaultdict(list)
                for values in all_values:
                    # print(values)
                    for k, v in values.items():
                        section_data[k].append(v)
            else:
                if len(self.cols_common_start) == 1:
                    section_text_values = [[x] for x in text_array]
                else:
                    section_text_values = \
                        [[y.strip() for y in x.split(maxsplit=len(self.cols_common_start) - 1)] for x in text_array]

                section_data = {}
                for i_col, (col_name, col_type) in enumerate(self.cols_common_start):
                    values = [col_type(x[i_col]) if i_col < len(x) else None for x in section_text_values]
                    section_data[col_name] = values

            df = pd.DataFrame(
                data=section_data,
            )

        # Handle descriptions
        if self.name in tables_with_description:
            if descriptions:
                df_descript = pd.DataFrame.from_dict(
                    descriptions,
                    orient='index',
                    columns=['Description']
                )
                # print(df_descript)
                df = df.merge(df_descript, how='left', left_on=df.columns[0], right_index=True)
                # We only want to keep the first item
                duplicate_rows = df.duplicated(subset=df.columns[0])
                df.loc[duplicate_rows, 'Description'] = ''
            else:
                df['Description'] = ''

        return df


def swmm_section_definitions() -> list[SwmmSection]:
    swmm_sections_info: list[SwmmSection] = []

    swmm_sections_info.append(
        SwmmSection(
            'Title',
            'Project',
            None,
            SectionType.NO_KEYWORDS,
            [('Title', str)],
        )
    )

    swmm_sections_info.append(
        SwmmSection(
            'Options',
            'Project',
            None,
            SectionType.NO_KEYWORDS,
            [('Option', str),
             ('Value', str)],
        )
    )

    swmm_sections_info.append(
        SwmmSection(
            'Files',
            'Project',
            None,
            SectionType.NO_KEYWORDS,
            [
                ('Operation', str),
                ('Filetype', str),
                ('Filename', str),
            ],
        )
    )

    swmm_sections_info.append(
        SwmmSection(
            'Evaporation',
            'Hydrology',
            None,
            SectionType.KEYWORDS,
            [
                ('Format', str)
            ],
            {
                'CONSTANT': [('evap', float)],
                'MONTHLY': [(f'e{x}', float) for x in range(1, 13)],
                'TIMESERIES': [('Tseries', str)],
                'TEMPERATURE': [],
                'FILE': [(f'p{x}', float) for x in range(1, 13)],
                'RECOVERY': [('patternId', str)],
                'DRY_ONLY': (('DryYesNo', str),)
            },
            0
        )
    )

    swmm_sections_info.append(
        SwmmSection(
            'Temperature',
            'Hydrology',
            None,
            SectionType.NO_KEYWORDS,
            [
                ('Option', str),
                ('Value', str)
            ],
            None,
            0
        )
    )

    swmm_sections_info.append(
        SwmmSection(
            'Raingages',
            'Hydrology',
            None,
            SectionType.KEYWORDS,
            [
                ('Name', str),
                ('Form', str),
                ('Intvl', str),
                ('SnowCatchDeficiency', float),
                ('Format', str),
            ],
            {
                'TIMESERIES': [('Tseries', str)],
                'FILE': [('Fname', str),
                         ('Sta', str),
                         ('Units', str)],
            },
            4
        )
    )

    swmm_sections_info.append(
        SwmmSection(
            'Adjustments',
            'Hydrology',
            None,
            SectionType.NO_KEYWORDS,
            [
                ('Format', str),
            ] +
            [
                (f'month{x}', float) for x in range(1, 13)
            ],
            {
                'TIMESERIES': [('Tseries', str)],
                'File': [('Fname', str),
                         ('Sta', str),
                         ('Units', str)],
            },
            0
        )
    )

    snow_shared_items = [
        ('Cmin', float),
        ('Cmax', float),
        ('Tbase', float),
        ('FWF', float),
        ('SD0', float),
        ('FW0', float),
    ]
    swmm_sections_info.append(
        SwmmSection(
            'Snowpacks',
            'Hydrology',
            None,
            SectionType.KEYWORDS,
            (('Name', str),
             ('Type', str),
             ),
            {
                'PLOWABLE': snow_shared_items + [('SNN0', float)],
                'IMPERVIOUS': snow_shared_items + [('SD100', float)],
                'PERVIOUS': snow_shared_items + [('SD100', float)],
                'REMOVAL': (('Dplow', str),
                            ('Fout', float),
                            ('Fimp', float),
                            ('Fperv', float),
                            ('Fimelt', float),
                            ('Fsub', float),
                            ('Scatch', str),)
            },
            1,
        )
    )

    swmm_sections_info.append(
        SwmmSection(
            'Subcatchments',
            'Hydrology',
            GeometryType.SUBCATCHMENTS,
            SectionType.NO_KEYWORDS,
            (('Name', str),
             ('Rain Gage', str),
             ('Outlet', str),
             ('Area', float),
             ('PctImperv', float),
             ('Width', float),
             ('PctSlope', float),
             ('CurbLen', float),
             ('SnowPack', str))
        )
    )

    swmm_sections_info.append(
        SwmmSection(
            'Subareas',
            'Hydrology',
            GeometryType.SUBCATCHMENTS,
            SectionType.NO_KEYWORDS,
            (('Subcatchment', str),
             ('Nimp', float),
             ('Nperv', float),
             ('Simp', float),
             ('Sperv', float),
             ('PctZero', float),
             ('RouteTo', str),
             ('PctRouted', float))
        )
    )

    swmm_sections_info.append(
        SwmmSection(
            'Infiltration',
            'Hydrology',
            GeometryType.SUBCATCHMENTS,
            SectionType.NO_KEYWORDS,
            (('Subcatchment', str),
             ('p1', float),
             ('p2', float),
             ('p3', float),
             ('p4', float),
             ('p5', float),
             ('Method', str),
             ),
        ),
    )

    swmm_sections_info.append(
        SwmmSection(
            'Aquifers',
            'Groundwater',
            None,
            SectionType.NO_KEYWORDS,
            (('Name', str),
             ('Por', float),
             ('WP', float),
             ('FC', float),
             ('Ksat', float),
             ('Kslope', float),
             ('Tslope', float),
             ('ETu', float),
             ('ETs', float),
             ('Seep', float),
             ('Ebot', float),
             ('Egw', float),
             ('Umc', float),
             ('ETupat', float),),
        )
    )

    swmm_sections_info.append(
        SwmmSection(
            'Groundwater',
            'Groundwater',
            GeometryType.SUBCATCHMENTS,
            SectionType.NO_KEYWORDS,
            (('Subcatchment', str),
             ('Aquifer', str),
             ('Node', str),
             ('Esurf', float),
             ('A1', float),
             ('B1', float),
             ('A2', float),
             ('B2', float),
             ('A3', float),
             ('Dsw', float),
             ('Egwt', float),
             ('Ebot', float),
             ('Wgr', float),
             ('Umc', float),)
        )
    )

    swmm_sections_info.append(
        SwmmSection(
            'GWF',
            'Groundwater',
            GeometryType.SUBCATCHMENTS,
            SectionType.NO_KEYWORDS,
            (('Subcatchment', str),
             ('Type', str),
             ('Expr', str),),
        )
    )

    swmm_sections_info.append(
        SwmmSection(
            'Pollutants',
            'WQ',
            None,
            SectionType.NO_KEYWORDS,
            (('Name', str),
             ('Units', str),
             ('Crain', float),
             ('Cgw', float),
             ('cii', float),
             ('Kdecay', float),
             ('Sflag', str),
             ('CoPoll', str),
             ('CoFract', float),
             ('Cdwf', float),
             ('Cinit', float),
             ),
        )
    )

    swmm_sections_info.append(
        SwmmSection(
            'Treatment',
            'WQ',
            GeometryType.NODES,
            SectionType.NO_KEYWORDS,
            (('Node', str),
             ('Pollut', str),
             ('Result', str),
             ('Func', str),
             )
        )
    )

    swmm_sections_info.append(
        SwmmSection(
            'Landuses',
            'WQ',
            None,
            SectionType.NO_KEYWORDS,
            (('Name', str),
             ('SweepIntervalDays', float),
             ('AvailabilityFract', float),
             ('LastSweepDays', float))
        )
    )

    coverages = SwmmSection(
        'Coverages',
        'WQ',
        GeometryType.SUBCATCHMENTS,
        SectionType.NO_KEYWORDS,
        (('Subcatchment', str),
         ('Landuse', str),
         ('Percent', float),
         )
    )
    coverages.custom_mapping = True
    swmm_sections_info.append(coverages)

    loadings = SwmmSection(
        'Loadings',
        'WQ',
        GeometryType.SUBCATCHMENTS,
        SectionType.NO_KEYWORDS,
        (('Subcatchment', str),
         ('Landuse', str),
         ('Percent', float),)
    )
    loadings.custom_mapping = True
    swmm_sections_info.append(loadings)

    swmm_sections_info.append(
        SwmmSection(
            'Buildup',
            'WQ',
            None,
            SectionType.NO_KEYWORDS,
            (('Landuse', str),
             ('Pollutant', str),
             ('FuncType', str),
             ('C1', float),
             ('C2', float),
             ('C3', float),
             ('PerUnit', str),
             )
        )
    )

    swmm_sections_info.append(
        SwmmSection(
            'Washoff',
            'WQ',
            None,
            SectionType.NO_KEYWORDS,
            (('Landuse', str),
             ('Pollutant', str),
             ('FuncType', str),
             ('C1', float),
             ('C2', float),
             ('SweepRmv1', float),
             ('BmpRmv1', float),
             )
        )
    )

    # TODO - Removals can have multiple entries
    swmm_sections_info.append(
        SwmmSection(
            'LID_Controls',
            'LID',
            None,
            SectionType.WIDE,
            (('Name', str),
             ),
            {
                '': (('Type', str),),
                'surface': (('StorHt', float),
                            ('VegFrac', float),
                            ('Rough', float),
                            ('Slope', float),
                            ('Xslope', float)),
                'soil': (('Thick', float),
                         ('Por', float),
                         ('FC', float),
                         ('WP', float),
                         ('Ksat', float),
                         ('Kcoeff', float),
                         ('Suct', float)),
                'pavement': (('Thick', float),
                             ('Vratio', float),
                             ('FracImp', float),
                             ('Perm', float),
                             ('Vclog', float),
                             ('Treg', float),
                             ('Freg', float),
                             ),
                'storage': (('Height', float),
                            ('Vratio', float),
                            ('Seepage', float),
                            ('Vclog', float),
                            ('Covrd', str)),
                'drain': (('Coeff', float),
                          ('Expon', float),
                          ('Offset', float),
                          ('Delay', float),
                          ('Hopen', float),
                          ('Hclose', float),
                          ('Qcrv', float)),
                'drainmat': (('Thick', float),
                             ('Vratio', float),
                             ('Rough', float)),
                # Handle removals later
                #                'REMOVALS': (('Pollut', float),
                #                             ('Rmvl', float))
            },
            1,
        )
    )

    swmm_sections_info.append(
        SwmmSection(
            'LID_Usage',
            'LID',
            GeometryType.SUBCATCHMENTS,
            SectionType.NO_KEYWORDS,
            (('Subcatchment', str),
             ('LID', str),
             ('Number', int),
             ('Area', float),
             ('Width', float),
             ('InitSat', float),
             ('FromImp', float),
             ('ToPerv', float),
             ('RptFile', str),
             ('DrainTo', str),
             ('FromPerv', float),)
        )
    )

    swmm_sections_info.append(
        SwmmSection(
            'Junctions',
            'Nodes',
            GeometryType.NODES,
            SectionType.NO_KEYWORDS,
            (('Name', str),
             ('Elev', float),
             ('Ymax', float),
             ('Y0', float),
             ('Ysur', str),
             ('Apond', float),
             ),
        )
    )

    swmm_sections_info.append(
        SwmmSection(
            'Outfalls',
            'Nodes',
            GeometryType.NODES,
            SectionType.KEYWORDS,
            (('Name', str),
             ('Elev', float),
             ('Type', str),
             ),
            {
                'FREE': None,
                'FIXED': (('Stage', str),),
                'TIDAL': (('Tcurve', str),),
                'TIMESERIES': (('Tseries', str),),
            },
            2,
            (('Gated', str),
             ('RouteTo', str),
             ),
        )
    )

    swmm_sections_info.append(
        SwmmSection(
            'Dividers',
            'Nodes',
            GeometryType.NODES,
            SectionType.KEYWORDS,
            (('Name', str),
             ('Elev', float),
             ('DivLink', str),
             ('Type', str)),
            {
                'OVERFLOW': None,
                'CUTOFF': (('Qmin', float),),
                'TABULAR': (('Dcurve', float),),
                'WEIR': (('Qmin', float),
                         ('Ht', float),
                         ('Cd', float))
            },
            3,
            (('Ymax', float),
             ('Y0', float),
             ('Ysur', float),
             ('Apond', float))
        )
    )

    swmm_sections_info.append(
        SwmmSection(
            'Storage',
            'Nodes',
            GeometryType.NODES,
            SectionType.KEYWORDS,
            (('Name', str),
             ('Elev', float),
             ('Ymax', float),
             ('Y0', float),
             ('TYPE', str)),
            {
                'TABULAR': (('Acurve', str),),
                'FUNCTIONAL': (('A1', float),
                               ('A2', float),
                               ('A0', float)),
                'Default': (('L', float),
                            ('W', float),
                            ('Z', float)),
            },
            4,
            (('Ysur', float),
             ('Fevap', float),
             ('Psi', float),
             ('Ksat', float),
             ('IMD', float)),
        )
    )

    swmm_sections_info.append(
        SwmmSection(
            'Conduits',
            'Links',
            GeometryType.LINKS,
            SectionType.NO_KEYWORDS,
            (('Name', str),
             ('From Node', str),
             ('To Node', str),
             ('Length', float),
             ('Roughness', float),
             ('InOffset', float),
             ('OutOffset', float),
             ('InitFlow', float),
             ('MaxFlow', float),
             ),
        )
    )

    swmm_sections_info.append(
        SwmmSection(
            'Pumps',
            'Links',
            GeometryType.LINKS,
            SectionType.NO_KEYWORDS,
            (('Name', str),
             ('From Node', str),
             ('To Node', str),
             ('Pcurve', str),
             ('Status', str),
             ('Startup', float),
             ('Shutoff', float)),
        )
    )

    swmm_sections_info.append(
        SwmmSection(
            'Weirs',
            'Links',
            GeometryType.LINKS,
            SectionType.NO_KEYWORDS,
            (('Name', str),
             ('From Node', str),
             ('To Node', str),
             ('Type', str),
             ('CrestHt', float),
             ('Cd', float),
             ('Gated', str),
             ('EC', str),
             ('Cd2', float),
             ('Sur', str),
             ('Road_Width', float),
             ('Road_Surf', str))
        )
    )

    swmm_sections_info.append(
        SwmmSection(
            'Orifices',
            'Links',
            GeometryType.LINKS,
            SectionType.NO_KEYWORDS,
            (('Name', str),
             ('From Node', str),
             ('To Node', str),
             ('Type', str),
             ('Offset', float),
             ('Qcoeff', float),
             ('Gated', str),
             ('CloseTime', float),
             ),
        )
    )

    swmm_sections_info.append(
        SwmmSection(
            'Outlets',
            'Links',
            GeometryType.LINKS,
            SectionType.KEYWORDS,
            (('Name', str),
             ('From Node', str),
             ('To Node', str),
             ('Offset', float),
             ('Type', str),
             ),
            {
                'TABULAR/DEPTH': (('QCurve', str),),
                'TABULAR/HEAD': (('QCurve', str),),
                'FUNCTIONAL/DEPTH': (('C1', float), ('C2', float)),
                'FUNCTIONAL/HEAD': (('C1', float), ('C2', float)),
            },
            4,
            (('Gated', str),),
        )
    )

    swmm_sections_info.append(
        SwmmSection(
            'Losses',
            'Links',
            None,
            SectionType.NO_KEYWORDS,
            (('Link', str),
             ('Kentry', float),
             ('Kexit', float),
             ('Kavg', float),
             ('Flap', str),
             ('Seepage', float),
             ),
        )
    )

    swmm_sections_info.append(
        SwmmSection(
            'XSections',
            'Links',
            None,
            SectionType.KEYWORDS,
            (
                ('Link', str),
                ('XsecType', str),
            ),
            {
                'Default': (('Geom1', float),
                            ('Geom2', float),
                            ('Geom3', float),
                            ('Geom4', float),
                            ('Barrels', int),
                            ('Culvert', str),
                            ),
                'CUSTOM': (('Geom1', float),
                           ('Curve', str),
                           ('Geom3', float),  # SWMM seems to require this even though it is not used/needed
                           ('Geom4', float),  # SWMM seems to require this even though it is not used/needed
                           ('Barrels', int),
                           ),
                'IRREGULAR': (('Tsect', str),
                              ),
                'STREET': (('Street', str),
                           ),
            },
            1,
        )
    )

    # Split Transects into two tables Transects and Transects_coords and switched Manning N to required for each
    transects = \
        SwmmSection(
            'Transects',
            'Links',
            None,
            SectionType.NO_KEYWORDS,
            (('Name', str),
             ('Xleft', float),
             ('Xright', float),
             ('Lfactor', float),
             ('Wfactor', float),
             ('Eoffset', float),
             ('Nleft', float),
             ('Nright', float),
             ('Nchan1', float),
             )
        )
    transects.custom_mapping = True
    swmm_sections_info.append(transects)

    transects_coords = \
        SwmmSection(
            'Transects_coords',
            'Links',
            None,
            SectionType.NO_KEYWORDS,
            (('Name', str),
             ('Elev', float),
             ('Station', float),
             )
        )
    transects_coords.custom_mapping = True
    swmm_sections_info.append(transects_coords)

    swmm_sections_info.append(
        SwmmSection(
            'Streets',
            'Links',
            None,
            SectionType.NO_KEYWORDS,
            (('Name', str),
             ('Tcrown', float),
             ('Hcurb', float),
             ('Sx', float),
             ('nRoad', float),
             ('a', float),
             ('W', float),
             ('Sides', int),
             ('Tback', float),
             ('Sback', float),
             ('nBack', float),
             )
        )
    )

    # ('TRANSECTS', 'Links',
    #  (('Type',) + tuple([f'Param{x}' for x in range(1, 11)])), None),

    # columns we want (map to multiple lines potentially)
    # Name
    # Type - (new option COMBINATION) - GRATE, CURB, COMBINATION, SLOTTED, CUSTOM
    # DropGrate (T/F), Grate_Length, Grate_Width, Grate_Type, Grate_Aopen, Grate_vsplash
    # DropCurb, Curb_Length, Curb_Height, Curb_Throat
    # Slotted_Length, Slotted_width
    # Custom_curve

    inlets = SwmmSection(
        'Inlets',
        'Inlets',
        None,
        SectionType.NO_KEYWORDS,
        cols_common_start=(('Name', str),
                           ('Type', str),
                           ('Grate_Length', float),
                           ('Grate_Width', float),
                           ('Grate_Type', str),
                           ('Grate_Aopen', float),
                           ('Grate_vsplash', float),
                           ('Curb_Length', float),
                           ('Curb_Height', float),
                           ('Curb_Throat', str),
                           ('Slotted_Length', float),
                           ('Slotted_Width', float),
                           ('Custom_Curve', str),
                           )
    )
    inlets.custom_mapping = True
    swmm_sections_info.append(inlets)

    swmm_sections_info.append(
        SwmmSection(
            'Inlet_Usage',
            'Inlets',
            GeometryType.INLETS,
            SectionType.NO_KEYWORDS,
            (('Conduit', str),
             ('Inlet', str),
             ('Node', str),
             ('Number', int),
             ('PctClogged', float),
             ('Qmax', float),
             ('aLocal', float),
             ('wLocal', float),
             ('Placement', str),
             )
        )
    )

    # This is for Inlet Usage defined externally to the SWMM inp file. It is included here for use with estry_to_swmm
    swmm_sections_info.append(
        SwmmSection(
            'Inlet_Usage_ext',
            '',
            GeometryType.INLETS,
            SectionType.NO_KEYWORDS,
            (('Inlet', str),
             ('StreetXSEC', str),
             ('Elevation', float),
             ('SlopePct_Long', float),
             ('Number', int),
             ('CloggedPct', float),
             ('Qmax', float),
             ('aLocal', float),
             ('wLocal', float),
             ('Placement', str),
             ('Conn1D_2D', str),
             ('Conn_width', float),
             )
        )
    )

    swmm_sections_info.append(
        SwmmSection(
            'Inflows',
            'BC',
            GeometryType.NODES,
            SectionType.KEYWORDS,
            (('Node', str),
             ('Type', str)),
            {
                # Default handles all pollutants
                'Default': (('Tseries', str),
                            ('PollutType', str),
                            ('Mfactor', float),
                            ),
                'FLOW': (('Tseries', str),
                         ('SeriesType', str),
                         ('Factor1', float),),
            },
            1,
            (('Sfactor', float),
             ('Base', float),
             ('Pat', str),
             ),
        )
    )

    swmm_sections_info.append(
        SwmmSection(
            'Controls',
            'Links',
            None,
            SectionType.NO_KEYWORDS,
            (('Text', str),),
        )
    )

    swmm_sections_info.append(
        SwmmSection(
            'DWF',
            'Nodes',
            GeometryType.NODES,
            SectionType.NO_KEYWORDS,
            (('Node', str),
             ('Type', str),
             ('Base', float),
             ('Pat1', str),
             ('Pat2', str),
             ('Pat3', str),
             ('Pat4', str),
             ),
        )
    )

    swmm_sections_info.append(
        SwmmSection(
            'RDII',
            'Hydrology',
            GeometryType.NODES,
            SectionType.NO_KEYWORDS,
            (('Node', str),
             ('UHgroup', str),
             ('SewerArea', float),
             ),
        )
    )

    swmm_sections_info.append(
        SwmmSection(
            'Hydrographs',
            'Hydrology',
            None,
            SectionType.NO_KEYWORDS,
            (('Name', str),
             ('RaingageOrMonth', str),
             ('Term', str),
             ('R', float),
             ('T', float),
             ('K', float),
             ('Dmax', float),
             ('Drec', float),
             ('D0', float),
             ),
        )
    )

    timeseries = SwmmSection(
        'Timeseries',
        'Curves',
        None,
        SectionType.NO_KEYWORDS,
        (('Name', str),
         ('Fname', str),
         ('Date', str),
         ('Time', str),
         ('Value', float),
         ),
    )
    timeseries.custom_mapping = True
    swmm_sections_info.append(timeseries)

    curves = SwmmSection(
        'Curves',
        'Curves',
        None,
        SectionType.NO_KEYWORDS,
        (('Name', str),
         ('Type', str),
         ('xval', float),
         ('yval', float),
         ),
    )
    curves.custom_mapping = True
    swmm_sections_info.append(curves)

    patterns = SwmmSection(
        'Patterns',
        'Hydrology',
        None,
        SectionType.NO_KEYWORDS,
        [('Name', str),
         ('Interval', str)] +
        [(f'Factor{x}', float) for x in range(1, 25)],
    )
    patterns.custom_mapping = True
    swmm_sections_info.append(patterns)

    swmm_sections_info.append(
        SwmmSection(
            'Report',
            'Project',
            None,
            SectionType.NO_KEYWORDS,
            (('Format', str),
             ('Value', str),
             ),
        )
    )

    # don't create tags section will add tags column to relevant tables
    swmm_sections_info.append(
        SwmmSection(
            'Tags',
            'Misc',
            None,
            SectionType.NO_KEYWORDS,
            (('Object_type', str),
             ('Object', str),
             ('Tag', str),),
        )
    )

    swmm_sections_info.append(
        SwmmSection(
            'Map',
            'Misc',
            None,
            SectionType.NO_KEYWORDS,
            (('Option', str),
             ('Value', str),
             ),
        )
    )

    swmm_sections_info.append(
        SwmmSection(
            'Symbols',
            'Misc',
            GeometryType.MISC,
            SectionType.GEOMETRY,
            (('Gage', str),
             ('X-Coord', float),
             ('Y-Coord', float),
             ),
        )
    )

    swmm_sections_info.append(
        SwmmSection(
            'Labels',
            'Misc',
            GeometryType.MISC,
            SectionType.GEOMETRY,
            (
                ('X-Coord', float),
                ('Y-Coord', float),
                ('Label', str),
            ),
        )
    )

    swmm_sections_info.append(
        SwmmSection(
            'Backdrop',
            'Misc',
            None,
            SectionType.NO_KEYWORDS,
            (
                ('Option', str),
                ('Value', str),
            ),
        )
    )

    swmm_sections_info.append(
        SwmmSection(
            'Coordinates',
            '',
            GeometryType.NODES,
            SectionType.GEOMETRY,
            (('Node', str),
             ('X-Coord', float),
             ('Y-Coord', float),
             )
        )
    )

    swmm_sections_info.append(
        SwmmSection(
            'Vertices',
            '',
            GeometryType.LINKS,
            SectionType.GEOMETRY,
            (('Link', str),
             ('X-Coord', float),
             ('Y-Coord', float),)
        )
    )

    swmm_sections_info.append(
        SwmmSection(
            'Polygons',
            '',
            GeometryType.SUBCATCHMENTS,
            SectionType.GEOMETRY,
            (('Subcatchment', str),
             ('X-Coord', float),
             ('Y-Coord', float),
             )
        )
    )

    return swmm_sections_info


if __name__ == "__main__":
    # Generate text to add sections to C++
    for name, _, column_names, _ in swmm_sections_def:
        print('m_sectionList.push_back(')
        print('\tstd::make_pair(')
        print(f'\t\tstd::string("{name}"),')
        quoted_columns = [f'"{x}"' for x in column_names]
        print(f'\t\tstd::vector<std::string>({{{",".join(quoted_columns)}}})')
        print(f'\t\t)')
        print(f'\t);')
        # print(name)
        # print(column_names)
