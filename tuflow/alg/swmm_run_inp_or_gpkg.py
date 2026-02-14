from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingOutputFile,
    QgsProcessingParameterFile,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterDateTime,
    QgsProcessingParameterString,
    QgsApplication,
    QgsTask,
    QgsMessageLog,
    Qgis,
)

import os
import shutil
import subprocess
import sys
import traceback
import re

from tuflow.tuflow_swmm.gis_to_swmm import gis_to_swmm

try:
    from pathlib import Path
except ImportError:
    from pathlib_ import Path_ as Path


class RunSWMMInp(QgsProcessingAlgorithm):
    """
    Run a SWMM inp file using a SWMM executable.
    """

    def __init__(self):
        super().__init__()
        self.feedback = None

    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return RunSWMMInp()

    def name(self):
        return 'RunSWMMInp'

    def displayName(self):
        return self.tr('Run SWMM - GPKG or INP')

    def flags(self):
        return super().flags()

    def group(self):
        return self.tr('SWMM')

    def groupId(self):
        return 'TuflowSWMM_Tools'

    def shortHelpString(self):
        folder = Path(os.path.realpath(__file__)).parent
        help_filename = folder / 'help/html/alg_swmm_run_inp_or_gpkg.html'
        return help_filename.read_text()

    def initAlgorithm(self, config=None):
        date_type = getattr(QgsProcessingParameterDateTime, 'TypeDate', None)
        time_type = getattr(QgsProcessingParameterDateTime, 'TypeTime', None)
        if date_type is None or time_type is None:
            date_type = getattr(QgsProcessingParameterDateTime, 'Date', None)
            time_type = getattr(QgsProcessingParameterDateTime, 'Time', None)
        if date_type is None or time_type is None:
            type_enum = getattr(QgsProcessingParameterDateTime, 'Type', None)
            if type_enum is not None:
                date_type = getattr(type_enum, 'Date', date_type)
                time_type = getattr(type_enum, 'Time', time_type)

        self.addParameter(
            QgsProcessingParameterFile(
                'INPUT_FILE',
                self.tr('SWMM Input File (Inp or GPKG)'),
                fileFilter=self.tr('SWMM inputs (*.inp *.gpkg)'),
                optional=False,
            )
        )
        self.addParameter(
            QgsProcessingParameterFile(
                'SWMM_EXE',
                self.tr('SWMM Executable'),
                extension='exe',
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterBoolean(
                'RUN_AS_TASK',
                self.tr('Run in background (QGIS task)'),
                defaultValue=False,
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                'OUTPUT_BASENAME',
                self.tr('Save with new name (saves next to selected INP or GPKG and applies to INP/RPT/OUT)'),
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterDateTime(
                'START_DATE',
                self.tr('Start Date'),
                type=date_type,
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterDateTime(
                'START_TIME',
                self.tr('Start Time'),
                type=time_type,
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterDateTime(
                'END_DATE',
                self.tr('End Date'),
                type=date_type,
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterDateTime(
                'END_TIME',
                self.tr('End Time'),
                type=time_type,
                optional=True,
            )
        )

        existing_outputs = {o.name() for o in self.outputDefinitions()}
        if 'OUTPUT_RPT' not in existing_outputs:
            self.addOutput(
                QgsProcessingOutputFile(
                    'OUTPUT_RPT',
                    self.tr('Report File (RPT)')
                )
            )
        if 'OUTPUT_OUT' not in existing_outputs:
            self.addOutput(
                QgsProcessingOutputFile(
                    'OUTPUT_OUT',
                    self.tr('Output File (OUT)')
                )
            )

    def processAlgorithm(self, parameters, context, feedback):
        self.feedback = feedback
        log_tag = 'TUFLOW'

        input_file = self.parameterAsFile(parameters, 'INPUT_FILE', context)
        if not input_file or not Path(input_file).exists():
            message = self.tr(f'SWMM input file does not exist: {input_file}')
            self.feedback.reportError(message, fatalError=True)
            QgsMessageLog.logMessage(message, log_tag, level=Qgis.Critical)
        input_path = Path(input_file)
        if input_path.suffix.lower() == '.gpkg':
            try:
                target_inp_file = self._resolve_output_inp_file(parameters, context, gpkg_file=input_file)
                gis_to_swmm(
                    input_file,
                    target_inp_file,
                    feedback=self.feedback,
                )
                inp_file = target_inp_file
            except Exception as e:
                message = f'Exception thrown converting GeoPackage to SWMM: {str(e)}'
                try:
                    exc_type, exc_value, exc_traceback = sys.exc_info()
                    message += ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
                finally:
                    del exc_type, exc_value, exc_traceback
                self.feedback.reportError(message, fatalError=True)
                QgsMessageLog.logMessage(message, log_tag, level=Qgis.Critical)
        elif input_path.suffix.lower() == '.inp':
            inp_file = self._copy_inp_if_needed(parameters, context, input_file)
        else:
            message = self.tr(f'Unsupported input type: {input_path.suffix}')
            self.feedback.reportError(message, fatalError=True)
            QgsMessageLog.logMessage(message, log_tag, level=Qgis.Critical)

        swmm_exe = self.parameterAsFile(parameters, 'SWMM_EXE', context)
        if swmm_exe:
            if not Path(swmm_exe).exists():
                message = self.tr(f'SWMM executable does not exist: {swmm_exe}')
                self.feedback.reportError(message, fatalError=True)
                QgsMessageLog.logMessage(message, log_tag, level=Qgis.Critical)
        else:
            swmm_exe = (self._find_runswmm_exe() or
                        shutil.which('runswmm.exe'))
            if not swmm_exe:
                message = self.tr('SWMM executable not provided and swmm5 was not found on PATH.')
                self.feedback.reportError(message, fatalError=True)
                QgsMessageLog.logMessage(message, log_tag, level=Qgis.Critical)

        report_file = str(Path(inp_file).with_suffix('.rpt'))
        output_file = str(Path(inp_file).with_suffix('.out'))

        Path(report_file).parent.mkdir(parents=True, exist_ok=True)
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)

        start_date_dt = self.parameterAsDateTime(parameters, 'START_DATE', context)
        start_time_dt = self.parameterAsDateTime(parameters, 'START_TIME', context)
        end_date_dt = self.parameterAsDateTime(parameters, 'END_DATE', context)
        end_time_dt = self.parameterAsDateTime(parameters, 'END_TIME', context)
        start_date = start_date_dt.toString('MM/dd/yyyy') if start_date_dt.isValid() else ''
        start_time = start_time_dt.toString('HH:mm:ss') if start_time_dt.isValid() else ''
        end_date = end_date_dt.toString('MM/dd/yyyy') if end_date_dt.isValid() else ''
        end_time = end_time_dt.toString('HH:mm:ss') if end_time_dt.isValid() else ''
        if any([start_date, start_time, end_date, end_time]):
            self._apply_date_overrides(inp_file, start_date, start_time, end_date, end_time, log_tag)

        args = [swmm_exe, inp_file, report_file, output_file]
        self.feedback.pushInfo(self.tr(f'Running SWMM: {" ".join(args)}'))

        run_as_task = self.parameterAsBool(parameters, 'RUN_AS_TASK', context)
        if run_as_task:
            self._start_swmm_task(args, inp_file, report_file, log_tag)
        else:
            exit_code = self._run_swmm_process(args, inp_file, report_file, log_tag, feedback=self.feedback)
            if exit_code != 0:
                message = self.tr(f'SWMM exited with a non-zero exit code: {exit_code}')
                self.feedback.reportError(message, fatalError=True)
                QgsMessageLog.logMessage(message, log_tag, level=Qgis.Critical)

        return {
            'OUTPUT_RPT': report_file,
            'OUTPUT_OUT': output_file,
        }

    def _start_swmm_task(self, args, inp_file, report_file, log_tag):
        task_name = f'Run SWMM: {Path(inp_file).name}'

        def run_task(task):
            return self._run_swmm_process(args, inp_file, report_file, log_tag, task=task)

        def task_finished(result, exception):
            if exception:
                message = f'SWMM task failed: {exception}'
                QgsMessageLog.logMessage(message, log_tag, level=Qgis.Critical)
                return
            if result != 0:
                message = f'SWMM task exited with a non-zero exit code: {result}'
                QgsMessageLog.logMessage(message, log_tag, level=Qgis.Critical)
                return
            QgsMessageLog.logMessage('SWMM task completed.', log_tag, level=Qgis.Info)

        task = QgsTask.fromFunction(task_name, run_task, on_finished=task_finished)
        QgsApplication.taskManager().addTask(task)
        QgsMessageLog.logMessage('SWMM task started in background.', log_tag, level=Qgis.Info)

    def _run_swmm_process(self, args, inp_file, report_file, log_tag, feedback=None, task=None):
        creation_flags = 0
        if hasattr(subprocess, 'CREATE_NO_WINDOW'):
            creation_flags = subprocess.CREATE_NO_WINDOW
        startupinfo = None
        if os.name == 'nt' and hasattr(subprocess, 'STARTUPINFO'):
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0

        def is_canceled():
            if feedback and feedback.isCanceled():
                return True
            if task and task.isCanceled():
                return True
            return False

        try:
            with subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                cwd=str(Path(inp_file).parent),
                creationflags=creation_flags,
                startupinfo=startupinfo,
            ) as proc:
                if proc.stdout:
                    for line in proc.stdout:
                        if line.strip():
                            if feedback:
                                feedback.pushInfo(line.rstrip())
                            QgsMessageLog.logMessage(line.rstrip(), log_tag, level=Qgis.Info)
                        if is_canceled():
                            proc.terminate()
                            break
                exit_code = proc.wait()
        except Exception as e:
            message = f'Exception thrown running SWMM: {str(e)}\n'
            try:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                message += '\n'.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
            finally:
                del exc_type, exc_value, exc_traceback
            if feedback:
                feedback.reportError(message)
            QgsMessageLog.logMessage(message, log_tag, level=Qgis.Critical)
            return 1

        self._scan_report(report_file, log_tag, feedback=feedback)
        return exit_code

    def _scan_report(self, report_file, log_tag, feedback=None):
        if not Path(report_file).exists():
            return
        try:
            max_rpt_messages = 10
            rpt_message_count = 0
            rpt_truncated = False
            with open(report_file, 'r', encoding='utf-8', errors='replace') as rpt:
                for line in rpt:
                    line_stripped = line.strip()
                    if not line_stripped:
                        continue
                    line_upper = line_stripped.upper()
                    if (line_upper.startswith('ERROR') or
                            line_upper.startswith('WARNING')):
                        if rpt_message_count >= max_rpt_messages:
                            rpt_truncated = True
                            break
                        if feedback:
                            feedback.pushWarning(line_stripped)
                        QgsMessageLog.logMessage(line_stripped, log_tag, level=Qgis.Warning)
                        rpt_message_count += 1
            if rpt_truncated:
                if feedback:
                    feedback.pushWarning('...')
                QgsMessageLog.logMessage('...', log_tag, level=Qgis.Warning)
        except Exception as e:
            message = f'Unable to scan report for warnings/errors: {str(e)}'
            if feedback:
                feedback.pushWarning(message)
            QgsMessageLog.logMessage(message, log_tag, level=Qgis.Warning)

    def _apply_date_overrides(self, inp_file, start_date, start_time, end_date, end_time, log_tag):
        try:
            with open(inp_file, 'r', encoding='utf-8', errors='replace') as inp:
                lines = inp.read().splitlines(True)
        except Exception as e:
            QgsMessageLog.logMessage(f'Unable to read inp for date overrides: {e}', log_tag, level=Qgis.Warning)
            return

        newline = '\n'
        for line in lines:
            if line.endswith('\r\n'):
                newline = '\r\n'
                break

        section_start = None
        section_end = None
        for i, line in enumerate(lines):
            text = line.strip()
            if text.upper() == '[OPTIONS]':
                section_start = i
                continue
            if section_start is not None and text.startswith('[') and text.endswith(']'):
                section_end = i
                break

        if section_start is None:
            section_start = len(lines)
            lines.append(f'[OPTIONS]{newline}')
            section_end = len(lines)
        elif section_end is None:
            section_end = len(lines)

        key_to_value = {}
        if start_date:
            key_to_value['START_DATE'] = start_date
        if start_time:
            key_to_value['START_TIME'] = start_time
        if end_date:
            key_to_value['END_DATE'] = end_date
        if end_time:
            key_to_value['END_TIME'] = end_time

        option_line_index = {}
        for i in range(section_start + 1, section_end):
            text = lines[i].strip()
            if not text or text.startswith(';'):
                continue
            parts = text.split()
            if not parts:
                continue
            option_line_index[parts[0].upper()] = i

        def _format_option_line(key, value, existing_line=None):
            if existing_line is None:
                return f'{key}    {value}{newline}'
            leading = existing_line[:len(existing_line) - len(existing_line.lstrip())]
            sep = '\t' if '\t' in existing_line else '    '
            return f'{leading}{key}{sep}{value}{newline}'

        for key, value in key_to_value.items():
            if key in option_line_index:
                idx = option_line_index[key]
                lines[idx] = _format_option_line(key, value, lines[idx])
            else:
                lines.insert(section_end, _format_option_line(key, value))
                section_end += 1

        try:
            with open(inp_file, 'w', encoding='utf-8', errors='replace') as inp:
                inp.writelines(lines)
        except Exception as e:
            QgsMessageLog.logMessage(f'Unable to write inp date overrides: {e}', log_tag, level=Qgis.Warning)

    def _resolve_output_inp_file(self, parameters, context, gpkg_file):
        base_name = self.parameterAsString(parameters, 'OUTPUT_BASENAME', context)
        if base_name:
            base_name = base_name.strip()
        if not base_name:
            return str(Path(gpkg_file).with_suffix('.inp'))

        base_path = Path(base_name)
        if base_path.suffix:
            base_path = base_path.with_suffix('')
        if not base_path.is_absolute():
            base_path = Path(gpkg_file).parent / base_path
        return str(base_path.with_suffix('.inp'))

    def _copy_inp_if_needed(self, parameters, context, inp_file):
        base_name = self.parameterAsString(parameters, 'OUTPUT_BASENAME', context)
        if base_name:
            base_name = base_name.strip()
        if not base_name:
            return inp_file

        base_path = Path(base_name)
        if base_path.suffix:
            base_path = base_path.with_suffix('')
        if not base_path.is_absolute():
            base_path = Path(inp_file).parent / base_path
        target_inp = base_path.with_suffix('.inp')

        if str(Path(inp_file)) != str(target_inp):
            target_inp.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(inp_file, target_inp)
        return str(target_inp)

    def _find_runswmm_exe(self):
        program_files = [os.environ.get('ProgramFiles'), os.environ.get('ProgramFiles(x86)')]
        roots = [Path(p) for p in program_files if p]
        candidates = []
        for root in roots:
            try:
                swmm_dirs = list(root.glob('EPA SWMM*'))
            except Exception:
                continue
            for swmm_dir in swmm_dirs:
                exe_path = swmm_dir / 'runswmm.exe'
                if exe_path.exists():
                    candidates.append(exe_path)

        if not candidates:
            return None

        def version_key(path):
            match = re.search(r'(\d+)\.(\d+)\.(\d+)', str(path))
            if match:
                return tuple(int(x) for x in match.groups())
            return (0, 0, 0)

        candidates.sort(key=lambda p: (version_key(p), str(p).lower()))
        return str(candidates[-1])
