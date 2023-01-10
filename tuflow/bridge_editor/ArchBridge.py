from pathlib import Path


class ArchBridgeOpening:

    def __init__(self, start, end, springing, soffit):
        self.start = start
        self.end = end
        self.springing = springing
        self.soffit = soffit


class ArchBridge:

    def __init__(self, csv):
        self.csv = csv
        self.error = False
        self.msg = ''
        self.nopenings = 0
        self.openings = []
        with open(csv) as f:
            startRead = False
            for i, line in enumerate(f):
                if startRead:
                    if not self.parseOpening(line, i+1):
                        return
                else:
                    attr = line.split(',')
                    if len(attr) >= 4:
                        for a in attr:
                            if not a:
                                continue
                            try:
                                float(a)
                                startRead = True
                            except ValueError:
                                break
                            if not self.parseOpening(line, i+1):
                                return
                            break

    def parseOpening(self, line, lineNo):
        attr = line.split(',')
        if len(attr) < 4:
            self.error = True
            self.msg = 'Error reading line {0} - not enough data'.format(lineNo)
            return False

        for i, a in enumerate(attr):
            if not a:
                continue
            try:
                start, end, springing, soffit = attr[i:i+4]
                start, end, springing, soffit = float(start), float(end), float(springing), float(soffit)
                self.openings.append(ArchBridgeOpening(start, end, springing, soffit))
                self.nopenings += 1
                return True
            except ValueError:
                self.error = True
                self.msg = 'Error reading line {0} - not able to convert value to a float'.format(lineNo)
                return False

        return False