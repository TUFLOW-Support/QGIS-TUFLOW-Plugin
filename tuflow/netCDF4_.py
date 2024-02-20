import ctypes
import os
from collections import OrderedDict

import numpy as np

ncdll_path = None
ncdll = None


def qgis_nc_dll_path():
    from qgis.core import QgsApplication
    netcdf_dll_path = os.path.dirname(os.path.join(os.path.dirname(os.path.dirname(QgsApplication.pkgDataPath()))))
    netcdf_dll_path = os.path.join(netcdf_dll_path, "bin", "netcdf.dll")
    if os.path.exists(netcdf_dll_path):
        return netcdf_dll_path


ncdll_test = qgis_nc_dll_path()
if ncdll_test is None:
    raise ImportError('Unable to load netCDF c library')


def load_ncdll(fpath=None):
    global ncdll, ncdll_path
    if fpath:
        ncdll_path = fpath
    if ncdll_path is None:
        ncdll_path = qgis_nc_dll_path()
    if ncdll is None:
        ncdll = ctypes.cdll.LoadLibrary(ncdll_path)
    return ncdll


class NC_Error:
    NC_NOERR = 0
    NC_EBADID = -33
    NC_ENOTVAR = -49
    NC_EBADDIM = -46
    NC_EPERM = -37
    NC_ENFILE = -34
    NC_ENOMEM = -61
    NC_EHDFERR = -101
    NC_EDIMMETA = -106

    @staticmethod
    def message(error):
        error2message = {
            NC_Error.NC_NOERR: "No error",
            NC_Error.NC_EBADID: "Invalid ncid",
            NC_Error.NC_ENOTVAR: "Invalid Variable ID",
            NC_Error.NC_EBADDIM: "Invalid Dimension ID",
            NC_Error.NC_EPERM: "Attempting to create a netCDF file in a directory where you do not have permission to open files",
            NC_Error.NC_ENFILE: "Too many files open",
            NC_Error.NC_ENOMEM: "Out of memory",
            NC_Error.NC_EHDFERR: "HDF5 error. (NetCDF-4 files only.)",
            NC_Error.NC_EDIMMETA: "Error in netCDF-4 dimension metadata. (NetCDF-4 files only.)"
        }

        if error in error2message:
            return error2message[error]
        else:
            return "code {0}".format(error)


class NC_DType:
    NC_BYTE = 1
    NC_CHAR = 2
    NC_SHORT = 3
    NC_INT = 4
    NC_FLOAT = 5
    NC_DOUBLE = 6
    NC_UBYTE = 7
    NC_USHORT = 8
    NC_UINT = 9
    NC_INT64 = 10
    NC_UINT64 = 11
    NC_STRING = 12

    @staticmethod
    def np_dtype(dtype):
        dtype2np = {
            NC_DType.NC_BYTE: 'i1',
            NC_DType.NC_CHAR: 'S1',
            NC_DType.NC_SHORT: 'i2',
            NC_DType.NC_INT: 'i4',
            NC_DType.NC_FLOAT: 'f4',
            NC_DType.NC_DOUBLE: 'f8',
            NC_DType.NC_UBYTE: 'B',
            NC_DType.NC_USHORT: 'H',
            NC_DType.NC_UINT: 'I',
            NC_DType.NC_INT64: 'i8',
            NC_DType.NC_UINT64: 'Q',
            NC_DType.NC_STRING: 'U'
        }
        if dtype in dtype2np:
            return np.dtype(dtype2np[dtype])
        else:
            return dtype


def dtype2ctype(dtype, size, allocate_memory=False):
    dtype2ctype = {
        np.dtype('i1'): ctypes.c_byte,
        np.dtype('i2'): ctypes.c_short,
        np.dtype('i4'): ctypes.c_int,
        np.dtype('i8'): ctypes.c_longlong,
        np.dtype('B'): ctypes.c_ubyte,
        np.dtype('H'): ctypes.c_ushort,
        np.dtype('I'): ctypes.c_uint,
        np.dtype('Q'): ctypes.c_ulonglong,
        np.dtype('f4'): ctypes.c_float,
        np.dtype('f8'): ctypes.c_double,
        np.dtype('U'): ctypes.c_char_p,
        np.dtype('S1'): ctypes.c_char_p,
    }
    if dtype in dtype2ctype:
        ctype = dtype2ctype[dtype]
        if ctype == ctypes.c_char_p:
            return (ctypes.c_char * size)()
        else:
            if allocate_memory:
                return (ctype * size)()
            return ctypes.pointer(ctype())
    else:
        return None


def ctype_value2value(ctype_value, size, dtype):
    try:
        if not size:
            return
        if dtype == np.dtype('S1') or dtype == np.dtype('U'):
            return ctype_value.value.decode('utf-8')
        if size == 1:
            return ctype_value.contents.value
        return np.array([ctype_value[i] for i in range(size)], dtype=dtype)
    except AttributeError:
        return ctype_value.value.decode('utf-8')


class Dimension:

    def __init__(self, id, name, size):
        self.id = id
        self.name = name
        self.size = size
        self.unlimited = False

    def __eq__(self, other):
        if isinstance(other, Dimension):
            return self.name == other.name
        elif isinstance(other, str):
            return self.name == other
        return False

    def __repr__(self):
        return f'<class \'NetCDF Dimension\'>: name = \'{self.name}\', size = {self.size}'


class Variable:

    def __init__(self, ncdll, ncid, id, name, dtype, dims, atts, no_fill, fill_value):
        self._ncdll = ncdll
        self._ncid = ncid
        self.id = id
        self.name = name
        self.dtype = dtype
        self.dimensions = dims
        self.ndim = len(dims)
        self.shape = tuple([dim.size for dim in dims])
        self.dim_names = tuple([dim.name for dim in dims])
        self.unlimited = [dim.name for dim in dims if dim.unlimited]
        self.atts = atts
        self.filling = not no_fill
        self.fill_value = fill_value
        for key, value in atts.items():
            setattr(self, key, value)
        self._attr_repr = '\n'.join([f"    {key}: {value}" for key, value in self.atts.items()])
        if self.filling:
            self._filling_repr = f'filling on, default _FillValue of {self.fill_value} used'
        else:
            self._filling_repr = f'filling off, no default _FillValue used'
        self._value = None

    def __repr__(self):
        return (
            f'<class \'NetCDF Variable\'>\n'
            f'{self.dtype} {self.name}({", ".join(self.dim_names)})\n'
            f'{self._attr_repr}\n'
            f'unlimited dimensions: {",".join(self.unlimited)}\n'
            f'current shape: {self.shape}\n'
            f'{self._filling_repr}'
        )

    def __getitem__(self, item):
        if self._value is None:
            self._value = self._get_value()
        return self._value.__getitem__(item)

    def __eq__(self, other):
        if isinstance(other, Variable):
            return self.name == other.name
        elif isinstance(other, str):
            return self.name == other
        return False

    def _get_value(self):
        ctype = dtype2ctype(self.dtype, np.prod(self.shape), True)
        err = self._ncdll.nc_get_var(self._ncid, ctypes.c_int(self.id), ctypes.byref(ctype))
        if err:
            raise Exception('Error getting variable value: {}'.format(NC_Error.message(err)))
        value = ctype_value2value(ctype, np.prod(self.shape), self.dtype)
        if len(self.shape) > 1:
            value = np.reshape(value, self.shape)
        if self.filling:
            mask = value == self.fill_value
            value = np.ma.masked_array(value, mask=mask)
        return value


class Dataset_:

    def __init__(self, fpath, mode='r'):
        self.fpath = fpath
        self.ndim = 0
        self.nvar = 0
        self.natt = 0
        self.nunlimdim = 0
        self.dimensions = OrderedDict({})
        self.variables = OrderedDict({})
        self.atts = OrderedDict({})
        self.init_ctypes(fpath)
        self.open(fpath)

    def __repr__(self):
        return f'<NetCDF Dataset: {os.path.basename(os.path.splitext(self.fpath)[0])}>'

    def __getitem__(self, item):
        return self.variables.__getitem__(item)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def init_ctypes(self, fpath):
        self._ncdll = load_ncdll()
        if self._ncdll is None:
            raise Exception('Unable to load netCDF c library')
        self._file = ctypes.c_char_p(str.encode(fpath))
        self._NC_NOWRITE = ctypes.c_int(0)
        self._ncid_p = ctypes.pointer(ctypes.c_int())
        self._ncid = None
        self._ndim_p = ctypes.pointer(ctypes.c_int())
        self._nvar_p = ctypes.pointer(ctypes.c_int())
        self._natt_p = ctypes.pointer(ctypes.c_int())
        self._unlimdim_p = ctypes.pointer(ctypes.c_int())

    def open(self, fpath):
        err = self._ncdll.nc_open(self._file, self._NC_NOWRITE, self._ncid_p)
        if err:
            raise Exception('Error opening file: {}'.format(NC_Error.message(err)))
        self._ncid = self._ncid_p.contents
        self.get_content_counts()
        self.atts = self.get_attributes(-1, self.natt)
        for key, value in self.atts.items():
            setattr(self, key, value)
        self.get_dimensions()
        self.get_variables()

    def close(self):
        if self._ncid:
            err = self._ncdll.nc_close(self._ncid)
            if err:
                raise Exception('Error closing file: {}'.format(NC_Error.message(err)))
            self._ncid = None

    def get_content_counts(self):
        err = self._ncdll.nc_inq(self._ncid, self._ndim_p, self._nvar_p, self._natt_p, self._unlimdim_p)
        if err:
            self.close()
            raise Exception('Error getting dimension, variable, attribute counts: {}'.format(NC_Error.message(err)))
        self.ndim = self._ndim_p.contents.value
        self.nvar = self._nvar_p.contents.value
        self.natt = self._natt_p.contents.value
        self.nunlimdim = self._unlimdim_p.contents.value

    def get_attributes(self, varid, natts):
        atts = OrderedDict({})
        for i in range(natts):
            # get the name first
            name_p = (ctypes.c_char * 256)()
            err = self._ncdll.nc_inq_attname(self._ncid, ctypes.c_int(varid), ctypes.c_int(i), ctypes.byref(name_p))
            if err:
                self.close()
                raise Exception('Error getting attribute name: {}'.format(NC_Error.message(err)))
            name = name_p.value.decode('utf-8')
            name_p = ctypes.c_char_p(str.encode(name))

            # get the type
            dtype_p = ctypes.pointer(ctypes.c_int())
            err = self._ncdll.nc_inq_atttype(self._ncid, ctypes.c_int(varid), name_p, dtype_p)
            if err:
                self.close()
                raise Exception('Error getting attribute type: {}'.format(NC_Error.message(err)))
            dtype = dtype_p.contents.value

            # get the length
            len_p = ctypes.pointer(ctypes.c_size_t())
            err = self._ncdll.nc_inq_attlen(self._ncid, ctypes.c_int(varid), name_p, len_p)
            if err:
                self.close()
                raise Exception('Error getting attribute length: {}'.format(NC_Error.message(err)))
            len_ = len_p.contents.value

            # get the value
            ctype = dtype2ctype(NC_DType.np_dtype(dtype), len_)
            err = self._ncdll.nc_get_att(self._ncid, ctypes.c_int(varid), name_p, ctype)
            if err:
                self.close()
                raise Exception('Error getting attribute value: {}'.format(NC_Error.message(err)))
            value = ctype_value2value(ctype, len_, NC_DType.np_dtype(dtype))

            atts[name] = value

        return atts

    def get_dimensions(self):
        for i in range(self.ndim):
            cstr_array = (ctypes.c_char * 256)()
            cint_p = ctypes.pointer(ctypes.c_int())
            err = self._ncdll.nc_inq_dim(self._ncid, ctypes.c_int(i), ctypes.byref(cstr_array), cint_p)
            if err:
                self.close()
                raise Exception('Error getting dimension: {}'.format(NC_Error.message(err)))
            name = cstr_array.value.decode('utf-8')
            size = cint_p.contents.value
            self.dimensions[name] = Dimension(i, name, size)

        if self.nunlimdim > 0:
            nunlimdim_p = ctypes.pointer(ctypes.c_int())
            unlimdim_p = ctypes.pointer(ctypes.c_int())
            err = self._ncdll.nc_inq_unlimdims(self._ncid, nunlimdim_p, unlimdim_p)
            if err:
                self.close()
                raise Exception('Error getting unlimited dimension: {}'.format(NC_Error.message(err)))
            if self.nunlimdim == 1:
                ids = [unlimdim_p.contents.value]
            else:
                ids = [unlimdim_p[i] for i in range(self.nunlimdim)]
            for id in ids:
                self.dimensions[self.get_dim_name(id)].unlimited = True


    def get_variables(self):
        for i in range(self.nvar):
            name_p = (ctypes.c_char * 256)()
            dtype_p = ctypes.pointer(ctypes.c_int())
            ndims_p = ctypes.pointer(ctypes.c_int())
            dimids_p = ctypes.pointer(ctypes.c_int())
            natts_p = ctypes.pointer(ctypes.c_int())

            err = self._ncdll.nc_inq_var(self._ncid, ctypes.c_int(i), name_p, dtype_p, ndims_p, dimids_p, natts_p)
            if err:
                self.close()
                raise Exception('Error getting variable: {}'.format(NC_Error.message(err)))

            name = name_p.value.decode('utf-8')
            dtype = dtype_p.contents.value
            ndims = ndims_p.contents.value
            dimids = []
            if ndims == 1:
                dimids = [dimids_p.contents.value]
            elif ndims > 1:
                dimids = [dimids_p[i] for i in range(ndims)]
            natts = natts_p.contents.value

            dtype = NC_DType.np_dtype(dtype)
            dims = [self.dimensions[self.get_dim_name(j)] for j in dimids]

            no_fill_p = ctypes.pointer(ctypes.c_int())
            void_p = ctypes.pointer(ctypes.c_double())
            err = self._ncdll.nc_inq_var_fill(self._ncid, ctypes.c_int(i), no_fill_p, void_p)
            if err:
                self.close()
                raise Exception('Error getting fill value: {}'.format(NC_Error.message(err)))

            no_fill = no_fill_p.contents.value
            fill_value = None
            if not no_fill:  # i.e. there is fill
                ctype = dtype2ctype(dtype, 1)
                err = self._ncdll.nc_inq_var_fill(self._ncid, ctypes.c_int(i), no_fill_p, ctype)
                if err:
                    self.close()
                    raise Exception('Error getting fill value: {}'.format(NC_Error.message(err)))
                fill_value = ctype_value2value(ctype, 1, dtype)

            atts = self.get_attributes(i, natts)

            self.variables[name] = Variable(self._ncdll, self._ncid, i, name, dtype, dims, atts,  no_fill, fill_value)

    def get_dim_name(self, ind):
        return list(self.dimensions.keys())[ind]




if __name__ == '__main__':
    ncdll_path = r"C:\TUFLOW\dev\QGIS\bin\netcdf.dll"
    with Dataset_(r"C:\TUFLOW\working\TPD20-1026\model\example_models\results\EG11\plot\EG11_001_TS.nc") as nc:
        a = nc['channel_flow_regime_1d'][:]
    print(a)
    # nc.close()
