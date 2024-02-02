from collections.abc import Sequence
from collections import defaultdict

has_gpd = False
try:
    import fiona
    import geopandas as gpd

    has_gpd = True
except ImportError:
    pass  # defaulted to false
import numpy as np
import pandas as pd

from tuflow_swmm import swmm_sections
from tuflow_swmm.version import __version__ as tuflow_swmm_version

all_sections = swmm_sections.swmm_section_definitions()


def is_tuflow_swmm_file(filename):
    layers = fiona.listlayers(filename)
    return 'TUFLOW_SWMM_VERSION' in layers


def write_tuflow_version(filename):
    df_file_version = pd.DataFrame(
        {'version': [tuflow_swmm_version]}
    )
    gdf_file_version = gpd.GeoDataFrame(
        df_file_version,
        geometry=[None],
    )
    gdf_file_version.to_file(filename,
                             driver='GPKG',
                             layer='TUFLOW_SWMM_VERSION')


def format_line(items: Sequence[str], header: bool = False, column_width: int = 19, allow_none: bool = False) -> str:
    items_copy = list(items)
    if not allow_none:
        items_copy = ["" if x == 'None' else x for x in items_copy]

    if header:
        # First item start with ;;
        items_copy[0] = ';;' + items_copy[0]
    line = " ".join([f'{x: <{column_width - 1}}' for x in items_copy]) + '\n'

    return line


def df_to_swmm_section(df: pd.DataFrame,
                       title: str,
                       allow_none: bool = False,
                       allow_blanks_in_middle: bool = False) -> str:
    column_width = 20
    section = ''

    df = df.replace(np.nan, None)

    descriptions = None
    if 'Description' in df:
        descriptions = df.pop('Description')
        # print(descriptions)

    sections_to_not_sort = [
        'OPTIONS',
        'CURVES',
        'VERTICES',
        'POLYGONS',
        'TEMPERATURE',
        'TIMESERIES',
        'TRANSECTS',
    ]
    if title.upper() not in sections_to_not_sort:
        df = df.sort_values(str(df.columns[0]), kind='stable')

    # Write section title
    section += f'[{title.upper()}]\n'

    column_width = max(column_width, df.iloc[:, 0].str.len().max() + 1)
    # print(f'Column width: {column_width}')

    # Write headers
    section += format_line([str(x) for x in df.columns], True, column_width, allow_none)
    section_def = list(filter(lambda x: x.name == title, all_sections))
    if not section_def:
        raise ValueError(f"Unable to find section: {title}")
    section_def = section_def[0]
    # Add alternative headings
    if section_def.section_type == swmm_sections.SectionType.KEYWORDS:
        for keyword, value in section_def.cols_keywords.items():
            comm_cols_text = [''] * len(section_def.cols_common_start)
            comm_cols_text[section_def.keyword_col] = keyword
            all_cols = comm_cols_text
            if value is not None:
                all_cols.extend([x[0] for x in value])
            if section_def.cols_common_end is not None:
                all_cols.extend([y[0] for y in section_def.cols_common_end])
            section += format_line(all_cols, True, column_width, allow_none)
    elif section_def.section_type == swmm_sections.SectionType.WIDE:
        for keyword, value in section_def.cols_keywords.items():
            comm_cols_text = ['Name']
            if keyword != '':
                comm_cols_text.append(keyword.upper())
            all_cols = comm_cols_text
            if value is not None:
                all_cols.extend([x[0] for x in value])
            if section_def.cols_common_end is not None:
                all_cols.extend([y[0] for y in section_def.cols_common_end])
            section += format_line(all_cols, True, column_width, allow_none)

    section += format_line(['-' * (column_width - 4) + ' '] * len(df.columns), True, column_width, allow_none)

    for index, row in df.iterrows():
        # if we have descriptions write in front if not blank
        if descriptions is not None:
            description_value = descriptions[index]
            if description_value is not None and description_value != '' and description_value != 'None':
                section += f';{description_value}\n'
        row_vals = [str(x) for x in row]
        # TODO - give error message if not enough values provided (may be influenced by keyword)
        if not allow_blanks_in_middle:
            # if we have blanks in the middle replace with 0 otherwise SWMM will skip whitespace and have value in wrong
            # column
            last_non_blank = 0
            for i in range(len(row_vals)):
                if row_vals[i] != '':
                    last_non_blank = i
            for i in range(len(row_vals)):
                if row_vals[i] == '' and i < last_non_blank:
                    row_vals[i] = '0'
        section += format_line(row_vals, False, column_width, allow_none)
    return section


def parse_sections(filename):
    # sections is a dictionary by "SectionName" with values (header_lines, [lines]))
    sections = dict()
    curr_section = None
    header_lines = []
    curr_lines = []
    with open(filename, "r") as file:
        for line in file:
            sec_title_start = line.find('[')
            sec_title_end = line.find(']')
            if sec_title_start != -1 and sec_title_end != -1:
                # Start of new section
                if curr_section is not None:
                    # print(curr_section)
                    # print(header_lines)
                    # print(curr_lines)
                    sections[curr_section] = (tuple(header_lines), curr_lines.copy())
                    header_lines.clear()
                    curr_lines.clear()
                curr_section = line[sec_title_start:sec_title_end + 1].upper()
                # print(f'Start section: {curr_section}')
                header_lines.append(line)
            else:
                # ignore blank lines
                line = line.replace('\n', '')
                if line.strip() == "":
                    continue
                # If we have a comment with nothing before it we are a header line
                # Descriptions can use just one ; so only skip two which are used by headers
                comment_pos = line.find(';;')
                if comment_pos != -1 and line[:comment_pos].strip() == "":
                    header_lines.append(line)
                else:
                    curr_lines.append(line)
    # Add the last section
    # print(curr_section)
    # print(header_lines)
    # print(curr_lines)
    sections[curr_section] = (header_lines, curr_lines.copy())

    return sections


def parse_sections_to_dicts(filename):
    # sections is a dictionary by "SectionName" with values (header_lines, dict{entries} = [lines]))
    sections = dict()
    curr_section = None
    header_lines = []
    curr_lines = defaultdict(list)
    with open(filename, "r") as file:
        for line in file:
            sec_title_start = line.find('[')
            sec_title_end = line.find(']')
            if sec_title_start != -1 and sec_title_end != -1:
                # Start of new section
                if curr_section is not None:
                    # print(curr_section)
                    # print(header_lines)
                    # print(curr_lines)
                    sections[curr_section] = (tuple(header_lines), curr_lines.copy())
                    header_lines.clear()
                    curr_lines.clear()
                curr_section = line[sec_title_start:sec_title_end + 1]
                # print(f'Start section: {curr_section}')
                header_lines.append(line)
            else:
                # ignore blank lines
                if line.strip() == "":
                    continue
                # If we have a comment with nothing before it we are a header line
                comment_pos = line.find(';')
                if comment_pos != -1 and line[:comment_pos].strip() == "":
                    header_lines.append(line)
                else:
                    # None header lines add to ordered dict for section based upon first entry (key)
                    line_id = line.split(' ')[0]
                    curr_lines[line_id].append(line)
    # Add the last section
    # print(curr_section)
    # print(header_lines)
    # print(curr_lines)
    sections[curr_section] = (header_lines, curr_lines)

    return sections
