# This class has functions matching QgsProcessingFeedback. Using the same signatures allows us to
# run outside of QGIS (use the default screenProcessingFeedback) or through a QGIS Processing Tool
# pass QGIS Feedback object
class ScreenProcessingFeedback:
    def pushCommandInfo(self, info: str):
        print(info)

    def pushConsoleInfo(self, info: str):
        print(info)

    def pushDebugInfo(self, info: str):
        print(info)

    def pushInfo(self, info: str):
        print(info)

    def pushWarning(self, warning: str):
        CRED = '\033[95m'
        CEND = '\033[0m'
        print(CRED + warning + CEND)

    def reportError(self, error: str, fatalError: bool = False):
        if fatalError:
            raise ValueError(error)
        CRED = '\033[91m'
        CEND = '\033[0m'
        print(CRED + error + CEND)


class LogProcessingFeedback:

    def __init__(self, logfilename):
        self.logFile = open(logfilename, 'w')

    def __del__(self):
        if self.logFile:
            self.close()

    def close(self):
        self.logFile.close()
        self.logFile = None

    def pushCommandInfo(self, info: str):
        self.logFile.write(info)
        self.logFile.flush()

    def pushConsoleInfo(self, info: str):
        self.logFile.write(info + '\n')
        self.logFile.flush()

    def pushDebugInfo(self, info: str):
        self.logFile.write(info + '\n')
        self.logFile.flush()

    def pushInfo(self, info: str):
        self.logFile.write(info + '\n')
        self.logFile.flush()

    def pushWarning(self, info: str):
        self.logFile.write(info + '\n')
        self.logFile.flush()

    def reportError(self, error: str, fatalError: bool = False):
        self.logFile.write(error + '\n')
        self.logFile.flush()
        if fatalError:
            raise ValueError(error)
