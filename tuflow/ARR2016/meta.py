class ArrMeta:
    def __init__(self):
        self.time_accessed = None
        self.version = None

    def read(self, fi):
        line = next(fi).strip('\n')
        data = line.split(',')
        self.time_accessed = data[1]
        line = next(fi).strip('\n')
        data = line.split(',')
        self.version = data[1]