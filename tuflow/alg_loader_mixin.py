import os
import sys
from pathlib import Path
import re
import importlib

try:
    import traceback
except ImportError:
    traceback = None

from qgis.core import Qgis, QgsMessageLog


class Directive:

    def __new__(cls, line: str):
        if DirectiveQgisVersion.matches(line):
            cls = DirectiveQgisVersion
        self = super().__new__(cls)
        self.valid = False
        self._init(line)
        return self

    def __bool__(self):
        return self.valid

    def _init(self, line: str):
        self.line = line

    def qualifies(self):
        return True


class DirectiveQgisVersion(Directive):

    def _init(self, line: str):
        super()._init(line)
        try:
            self.version = int(re.findall(r'\d{5}', line)[0])
            self.check = re.findall(r'[><=]{1,2}', line)[0]
            self.valid = True
        except Exception as e:
            print(f'Error: {e}')

    @staticmethod
    def matches(line) -> bool:
        r = r'^# QGIS_VERSION[><=]{1,2}\d{5}'
        return bool(re.findall(r, line))

    def qualifies(self):
        qv = Qgis.QGIS_VERSION_INT
        if self.check == '>':
            return qv > self.version
        elif self.check == '>=':
            return qv >= self.version
        elif self.check == '<':
            return qv < self.version
        elif self.check == '<=':
            return qv <= self.version
        elif self.check == '==':
            return qv == self.version
        else:
            return True


class AlgorithmLoaderMixin:

    def load_scripts_from_folder(self, script_folder):
        """
        Loads all scripts found under the specified sub-folder
        """
        if not os.path.exists(script_folder):
            return

        algs = []
        for file in Path(script_folder).glob('*.py'):
            alg = self.algorithmName(file)
            if alg is not None:
                try:
                    # Construct the module path (e.g., '.alg.my_script')
                    module_path = f".alg.{file.parent.name}.{file.stem}"

                    # Import the module relative to the current package
                    # __package__ provides the necessary context for the relative dot notation
                    module = importlib.import_module(module_path, package=__package__)

                    # Get the class/function from the module
                    alg_class = getattr(module, alg)

                    # Instantiate and append
                    algs.append(alg_class())

                except (ImportError, AttributeError) as err:
                    QgsMessageLog.logMessage(f"Failed to load {alg} from {file.stem}: {str(err)}",
                                             'TUFLOW', level=Qgis.Warning)
                except SyntaxError as err:
                    QgsMessageLog.logMessage(f"Syntax error loading processing algorithm from file: {file}\n"
                                             f"  {err.__class__.__name__} {err.args[0]} on line {err.lineno}",
                                             'TUFLOW',
                                             level=Qgis.Warning)
                except Exception as err:
                    cl, exc, tb = sys.exc_info()
                    if traceback:
                        line_number = traceback.extract_tb(tb)[-1][1]
                        QgsMessageLog.logMessage(f"Exception loading processing algorithm from file: {file}\n"
                                                 f"  {err.__class__.__name__} {err.args[0]}\n"
                                                 f"  {traceback.format_exc()}",
                                                 'TUFLOW',
                                                 level=Qgis.Warning)
                    else:
                        QgsMessageLog.logMessage(f"Exception loading processing algorithm from file: {file}\n"
                                                 f"  {err.__class__.__name__} {err.args[0]}",
                                                 'TUFLOW',
                                                 level=Qgis.Warning)
                    continue

        return algs

    def algorithmName(self, file):
        """Extract the algorithm name from python file - assumes only one exists in file."""
        with open(file, 'r') as f:
            in_multi_line_comment = False
            for line in f:
                directive = Directive(line)
                if directive and not directive.qualifies():
                    return None
                text = [x.strip() for x in line.split('#', 1)]
                if len(text) == 2:
                    text, comment = text
                else:
                    text = text[0]
                text = [x.strip() for x in text.split('"""', 1)]
                if len(text) == 2:
                    code, comment = text
                else:
                    code = text[0]
                if not code.strip():
                    continue

                if code and not in_multi_line_comment:
                    if re.findall(r'^class [A-z]*\(QgsProcessingAlgorithm\):', code):
                        return code.split('class ')[1].split('(')[0]

                if code and not in_multi_line_comment:
                    if re.findall(r'^class [A-z]*\(QgsProcessingFeatureBasedAlgorithm\):', code):
                        return code.split('class ')[1].split('(')[0]

                if re.findall(r'"{3}', line):
                    multi_line_comment = len(re.findall(r'"{3}', line)) % 2 != 0
                    if multi_line_comment:
                        in_multi_line_comment = not in_multi_line_comment

        return None
