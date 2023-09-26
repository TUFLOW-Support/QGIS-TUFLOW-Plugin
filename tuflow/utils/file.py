import os
import typing

from ..compatibility_routines import Path


def find_parent_dir(start_loc: typing.Union[str, Path], dir_name: str, max_levels: int = -1) -> Path:
    start_loc = Path(start_loc)
    nparts = len(start_loc.parts)
    if max_levels == -1 and dir_name.lower() in [x.lower() for x in start_loc.parts]:
        for i, part in enumerate(reversed(start_loc.parts)):
            if part.lower() == dir_name.lower():
                return Path(os.path.join(*start_loc.parts[:nparts - i]))
    elif dir_name.lower() in [x.lower() for x in start_loc.parts[nparts-max_levels:]]:
        for i, part in enumerate(reversed(start_loc.parts)):
            if part.lower() == dir_name.lower():
                return Path(os.path.join(*start_loc.parts[:nparts - i]))


def find_highest_matching_file(start_loc: typing.Union[str, Path], pattern: str) -> Path:
    start_loc = Path(start_loc)
    files = [file for file in start_loc.glob('**/{0}'.format(pattern))]
    if files:
        nparts = 1000
        chosen_file = None
        for file in files:
            if len(file.parts) < nparts:
                nparts = len(file.parts)
                chosen_file = file
        return chosen_file
