#
# Minimize a specified window.
#
import sys
import ctypes
from ctypes import *

def _stdcall(dllname, restype, funcname, *argtypes):
    # a decorator for a generator.
    # The decorator loads the specified dll, retrieves the
    # function with the specified name, set its restype and argtypes,
    # it then invokes the generator which must yield twice: the first
    # time it should yield the argument tuple to be passed to the dll
    # function (and the yield returns the result of the call).
    # It should then yield the result to be returned from the
    # function call.
    def decorate(func):
        api = getattr(WinDLL(dllname), funcname)
        api.restype = restype
        api.argtypes = argtypes

        def decorated(*args, **kw):
            iterator = func(*args, **kw)
            nargs = iterator.next()
            if not isinstance(nargs, tuple):
                nargs = (nargs,)
            try:
                res = api(*nargs)
            except Exception, e:
                return iterator.throw(e)
            return iterator.send(res)
        return decorated
    return decorate

from ctypes.wintypes import HWND #, RECT, POINT
LPARAM = c_ulong

class metaENUM(type(ctypes.c_int)):
    def __init__(cls, name, bases, namespace):
        '''Convert enumeration names into attributes'''
        names = namespace.get('_names_', {})
        if hasattr(names, 'keys'):
            for (k,v) in names.items():
                setattr(cls, k, cls(v))
                names[v]=k
        else:
            for (i,k) in enumerate(names):
                setattr(cls, k, cls(i))
        super(metaENUM, cls).__init__(name, bases, namespace)

class ENUM(ctypes.c_int):
    '''Enumeration base class. Set _names_ attribute to a list
    of enumeration names (counting from 0)
    or a dictionary of name:value pairs.'''
    __metaclass__ = metaENUM
    def __str__(self):
        return self.__repr__(fmt="%(value)s")

    def __repr__(self, fmt="<%(name)s %(value)s>"):
        try:
            return self._names_[self.value]
        except:
            return fmt % dict(name=self.__class__.__name__, value=self.value)
    def __int__(self):
        return self.value

class BITMASK(ENUM):
    '''Some Microsoft 'enums' are actually bitmasks with several bits or'd together'''
    def __repr__(self, fmt="<%(name)s %(value)s>"):
        v = self.value
        values = []
        while v:
            bit = v&(~v+1)
            try:
                values.append(self._names_[bit])
            except (KeyError, IndexError):
                values.append(fmt % dict(name=self.__class__.__name__, value=self.value))
            v &= ~bit
        if not values:
            return '0'
        return '|'.join(values)
    def __or__(self, other):
        return type(self)(int(self.value)|int(other.value))

class SHOWCMD(ENUM):
    _names_ = '''SW_HIDE SW_NORMAL SW_SHOW_MINIMIZED SW_SHOW_MAXIMIZED
    SW_SHOW_NOACTIVATE SW_SHOW SW_MINIMIZE SW_SHOWMINNOACTIVE
    SW_SHOWNA SW_RESTORE SW_SHOWDEFAULT SW_FORCEMINIMIZE'''.split()

class WindowPlacementFlags(BITMASK):
    _names_ = dict(WPF_SETMINPOSITION = 1,
        WPF_RESTORETOMAXIMIZED = 2,
        WPF_ASYNCWINDOWPLACEMENT = 4)

class Structure(ctypes.Structure):
    """As ctypes Structure but with added repr and comparison testing"""
    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__,
            ", ".join("%s=%r" % (f, getattr(self, f)) for (f,t) in self._fields_))
    def __eq__(self, other):
        if self._fields_ != other._fields_:
            return False
        for (f,t) in self._fields_:
            if getattr(self,f) != getattr(other,f):
                return False
        return True

class RECT(Structure):
    _fields_ = [("left", c_long),
                ("top", c_long),
                ("right", c_long),
                ("bottom", c_long)]

class POINT(Structure):
    _fields_ = [("x", c_long),
                ("y", c_long)]

class StructureWithLength(Structure):
    _fields_ = [('length', ctypes.c_ulong)]
    def __init__(self):
        ctypes.Structure.__init__(self)
        self.length = ctypes.sizeof(self)

class WINDOWPLACEMENT(StructureWithLength):
    _fields_ = [
        ('flags', WindowPlacementFlags),
        ('showCmd', SHOWCMD),
        ('ptMinPosition', POINT),
        ('ptMaxPosition', POINT),
        ('rcNormalPosition', RECT),
        ]

def nonzero(result):
    # If the result is zero, and GetLastError() returns a non-zero
    # error code, raise a WindowsError
    if result == 0 and GetLastError():
        raise WinError()
    return result

WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_int, HWND, LPARAM)
@ _stdcall("user32", c_int, "EnumWindows", WNDENUMPROC, LPARAM)
def EnumWindows(callback, lparam=0):
    yield nonzero((yield WNDENUMPROC(callback), lparam))

@ _stdcall("user32", c_int, "GetWindowTextLengthW", HWND)
def GetWindowTextLength(hwnd):
    yield nonzero((yield hwnd,))

@ _stdcall("user32", c_int, "GetWindowTextW", HWND, c_wchar_p, c_int)
def GetWindowText(hwnd):
    len = GetWindowTextLength(hwnd)+1
    buf = create_unicode_buffer(len)
    nonzero((yield hwnd, buf, len))
    yield buf.value

@ _stdcall("user32", c_int, "GetClassNameW", HWND, c_wchar_p, c_int)
def GetClassName(hwnd):
    len = 256
    buf = create_unicode_buffer(len)
    nonzero((yield hwnd, buf, len))
    yield buf.value

@ _stdcall("user32", c_int, "GetWindowRect", HWND, POINTER(RECT))
def GetWindowRect(hwnd):
    buf = RECT()
    nonzero((yield hwnd, buf))
    yield buf

@ _stdcall("user32", c_int, "GetClientRect", HWND, POINTER(RECT))
def GetClientRect(hwnd):
    buf = RECT()
    nonzero((yield hwnd, buf))
    yield buf

@ _stdcall("user32", c_int, "GetWindowPlacement", HWND, POINTER(WINDOWPLACEMENT))
def GetWindowPlacement(hwnd):
    buf = WINDOWPLACEMENT()
    nonzero((yield hwnd, buf))
    yield buf

@ _stdcall("user32", c_int, "SetWindowPlacement", HWND, POINTER(WINDOWPLACEMENT))
def SetWindowPlacement(hwnd, placement):
    yield nonzero((yield hwnd, placement))

@ _stdcall("user32", c_int, "IsWindow", HWND)
def IsWindow(hwnd):
    yield bool((yield hwnd,))

@ _stdcall("user32", c_int, "ShowWindow", HWND, SHOWCMD)
def ShowWindow(hwnd, showcmd):
    yield bool((yield hwnd,showcmd))

def toplevelWindows():
    res = []
    def callback(hwnd, arg):
        res.append(hwnd)
        return True
    EnumWindows(callback, 0)
    return res

def iterWindows(klass, match):
    for hwnd in toplevelWindows():
        if IsWindow(hwnd):
            try:
                title = GetWindowText(hwnd)
            except WindowsError, e:
                continue
            if klass==GetClassName(hwnd) and match in title:
                yield hwnd

if __name__=='__main__':
    for hwnd in iterWindows("MozillaUIWindowClass", sys.argv[1]):
        wp = GetWindowPlacement(hwnd)
        ShowWindow(hwnd, SHOWCMD.SW_MINIMIZE)
    else:
        print "Sorry, I couldn't find the window"