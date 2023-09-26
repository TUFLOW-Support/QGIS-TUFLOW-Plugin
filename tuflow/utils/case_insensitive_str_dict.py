class CaseInsStrDict(dict):
    """Case-insensitive string key dictionary."""

    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        self._key_lower = {k.lower(): k for k in self.keys()}

    def __getitem__(self, key):
        return dict.__getitem__(self, self._key_lower[key.lower()])

    def __contains__(self, item):
        return item.lower() in self._key_lower

    def __setitem__(self, key, value):
        dict.__setitem__(self, key, value)
        self._key_lower[key.lower()] = key

    def get(self, key, default=None):
        return dict.get(self, self._key_lower[key.lower()], default)
