import numpy as np
from collections import OrderedDict
import re


def read_data(line):
    d = [float(x) for x in line[18:].split(' ') if x]
    return np.reshape(np.array(d), (len(d), 1))


def read_eof(eof):
    abdgs = OrderedDict({})
    with open(eof, 'r') as f:
        for line in f:
            if 'ARCH BRIDGE CHANNEL' in line:
                id = line.split('ARCH BRIDGE CHANNEL')[-1].strip()
                a = []  # array
                h = []  # headers
                for subline in f:
                    if re.findall(r'Elevation|XS Area|BG Area|Blockage', subline):
                        h.append(re.findall(r'Elevation|XS Area|BG Area|Blockage', subline)[0])
                        a.append(read_data(subline))
                        if 'Blockage' in subline:
                            break

                b = a[0]
                for ar in a[1:]:
                    b = np.append(b, ar, axis=1)
                abdgs[id] = np.array(b)

    return abdgs


class EofParser:

    def __init__(self):
        self.bridges = {}

    def load(self, eof):
        self.bridges = read_eof(eof)
