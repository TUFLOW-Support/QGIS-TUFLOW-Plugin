import os
import glob


class Path_:
    """Dodgy implementation of Path class if using QGIS version that doesn't have a recent Python version."""

    def __init__(self, p=None):
        self._path = p
        self._fo = None
        self.name = ''
        if p is not None:
            self.name = os.path.basename(p)
        self.suffix = ''
        if p is not None:
            self.suffix = os.path.splitext(p)[1]
        self.stem = ''
        if p is not None:
            self.stem = os.path.splitext(self.name)[0]
        self.parent = ''
        if p is not None and p != os.path.dirname(p):
            self.parent = Path_(os.path.dirname(p))

    def __str__(self):
        return self._path

    def __enter__(self):
        return self._fo

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __truediv__(self, other):
        return Path_(os.path.join(self._path, other))

    def __bool__(self):
        return self._path

    @property
    def parts(self):
        p = os.path.normpath(self._path)
        return p.split(os.sep)

    def open(self, mode='r'):
        self._fo = open(self._path, mode)
        return self._fo

    def close(self):
        if self._fo is not None:
            self._fo.close()
            self._fo = None

    def exists(self):
        return os.path.exists(self._path)

    def with_suffix(self, suffix):
        return Path_('{0}{1}'.format(os.path.splitext(self._path)[0], suffix))

    def with_name(self, name):
        if self.parent:
            return self.parent / name
        else:
            return Path_(name)

    def iterdir(self):
        for file in os.listdir(str(self)):
            yield Path_(os.path.join(str(self), file))

    def is_dir(self):
        return os.path.isdir(str(self))

    def glob(self, pattern):
        for file in glob.glob(os.path.join(str(self), pattern)):
            yield Path_(file)

    def resolve(self):
        return Path_(os.path.realpath(self._path))

    def mkdir(self, mode=0o777, parents=False, exist_ok=False):
        if parents:
            os.makedirs(str(self._path.resolve()), mode, exist_ok)
        else:
            if exist_ok and self.exists():
                return
            os.mkdir(str(self._path.resolve()), mode=mode)
