import re


def sanitize_name(name_in: str) -> str:
    name_out = name_in.strip().replace('"', '')
    name_out = name_out.replace(' ', '_')
    # Some testing in SWMM suggested these are okay
    #name_out = re.sub('[^a-zA-Z0-9_.]', '-', name_out)
    return name_out
