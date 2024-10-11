# used for parsing ARR data file from datahub
# hopefully can replace with json at some point in the future
import typing
import io
from datetime import datetime

import pandas as pd


class DataBlock:
    """Loads in a data block from the ARR data file based on the starting text indicator.
    e.g. CCF finds the climate change block and loads all sub-blocks between [CCF] and [END_CCF].
    """

    def __init__(self, fi: typing.TextIO, start_text: str, header: bool) -> None:
        """
        Parameters
        ----------
        fi : io.FileIO
            File object to read from.
        start_text : str
            Text to search for to start reading the data block
        header : bool
            Whether data stored outside of a sub-block has a header - i.e. when the data is read into a DataFrame,
            should the first row be used as the header.
        """
        self.fi = fi
        self.start_text = start_text
        self.end_text = 'END_{0}'.format(start_text.strip('[]'))
        self.header = header
        self.finished = False
        self.data = {}
        self.df = pd.DataFrame()
        self.time_accessed = None
        self.version = ''
        self.version_int = -1
        self.note = ''
        self._line = ''
        self._collect()

    def empty(self) -> bool:
        """Returns whether the data block is empty.

        Returns
        -------
        bool
            Whether the data block is empty.
        """
        return self.df.empty and len(self.data) == 0

    def get(self, item: str, default: typing.Any = None) -> typing.Any:
        """Returns a sub-block from the parsed data block.

        Parameters
        ----------
        item: str
            Name of the sub-block to return.
        default: typing.Any, optional
            Default value to return if the sub-block is not found.

        Returns
        -------
        typing.Any
            The sub-block data requested.
        """
        if item == self.start_text:
            return self.df
        if item in self.data:
            return self.data[item]
        if item in self.df.index:
            return self.df.loc[item].iloc[0]
        return default

    def _find_start(self) -> bool:
        for line in self.fi:
            if self.start_text in line:
                return True
        self.fi.seek(0)
        return False

    def _next_sub_block(self) -> bool:
        if self.end_text in self._line:
            return False
        if '[' in self._line and 'END' not in self._line:
            return True
        for self._line in self.fi:
            if self.end_text in self._line:
                return False
            if self._line.strip():
                return True
        return False

    def _collect(self):
        if not self._find_start():
            return
        while not self.finished:
            self._block()
        self.fi.seek(0)

    def _block(self):
        if not self._next_sub_block():
            self.finished = True
            return

        buf = io.StringIO()
        name = None
        if '[' in self._line:
            name = self._line.strip('[]\n')
            if 'META' in name:
                self._meta_block()
                return
        else:
            buf.write(self._line)

        for self._line in self.fi:
            if 'END' in self._line or 'META' in self._line:
                break
            buf.write(self._line)
        buf.seek(0)
        header = 'infer' if name or self.header else None
        df = pd.read_csv(buf, index_col=0, header=header)

        if name:
            self.data[name] = df
        else:
            self.df = df

    def _meta_block(self):
        self._line = self.fi.readline()
        line_split = self._line.split()
        if len(line_split) > 1 and 'time accessed' in line_split[0].lower():
            self.time_accessed = line_split[1].strip()
            try:
                self.time_accessed = datetime.strptime(self.time_accessed, '%d %B %Y %I:%M%p')
            except:
                pass
        else:
            self.note = self._line.strip()
        self._line = self.fi.readline()
        if 'version' in self._line.lower():
            self.version = self._line.split(',')[1].strip()
            try:
                major, minor = self.version.split('_', 1)
                self.version_int = int(major) * 1000 + int(minor.strip('v')) * 100
            except:
                pass
            self._line = self.fi.readline()
        elif 'END' not in self._line:
            if self.note:
                self.note = f'{self.note} {self._line.strip()}'
            else:
                self.note = self._line.strip()
            self._line = self.fi.readline()
        if 'END' not in self._line:
            self.note = self._line.strip()
