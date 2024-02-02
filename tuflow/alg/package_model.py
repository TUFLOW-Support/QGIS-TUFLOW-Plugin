import os
import shutil
import subprocess
import typing
import tempfile
import zipfile
import re

from PyQt5.QtCore import QCoreApplication
from qgis._core import (QgsProcessingAlgorithm, QgsProcessingParameterFile, QgsProcessingParameterEnum,
                        QgsProcessingParameterBoolean, QgsProcessingParameterDefinition, QgsProcessingContext,
                        QgsProcessingFeedback, QgsProcessingMultiStepFeedback, QgsProcessingParameterString)

from ..compatibility_routines import Path
from ..tuflowqgis_settings import TF_Settings


def create_command(command: str, value: str) -> str:
    a1, a2 = value.split('==', 1)
    a1 = a1.replace('~', '')
    a1 = re.sub(command, '', a1, flags=re.IGNORECASE)
    return '{0} ~{1}~ == {2}\n'.format(command, a1.strip(), a2.strip())


class PackageModel(QgsProcessingAlgorithm):

    def initAlgorithm(self, configuration: typing.Dict[str, typing.Any] = ...) -> None:
        # TUFLOW exe
        tf_settings = TF_Settings()
        tf_settings.Load()
        default = tf_settings.combined.tf_exe
        self.addParameter(
            QgsProcessingParameterFile(
                'tf_exe',
                'TUFLOW exe',
                behavior=QgsProcessingParameterFile.File,
                fileFilter='executable (*.exe)',
                defaultValue=default
            )
        )
        # TCF
        self.addParameter(
            QgsProcessingParameterFile(
                'tcf',
                'Model TCF to Package',
                behavior=QgsProcessingParameterFile.File,
                fileFilter='TCF (*.tcf *.TCF)',
                defaultValue=None
            )
        )
        # xf files
        self.addParameter(
            QgsProcessingParameterEnum(
                'xf',
                'XF Files',
                options=['Do not copy xf files', 'Copy all', 'Copy only xf files'],
                defaultValue=0
                )
        )
        # which files to include
        self.addParameter(
            QgsProcessingParameterBoolean(
                'all_files',
                'Copy All File Extensions',
                defaultValue=False
            )
        )
        self.addParameter(
            QgsProcessingParameterBoolean(
                'list_files',
                'List Files Only',
                defaultValue=False
            )
        )
        # Output directory
        self.addParameter(
            QgsProcessingParameterFile(
                'outdir',
                'Output Directory',
                behavior=QgsProcessingParameterFile.Folder,
                defaultValue=None,
                optional=True
            )
        )
        # Zip output
        self.addParameter(
            QgsProcessingParameterBoolean(
                'zip',
                'Zip Output',
                defaultValue=False,
                optional=True
            )
        )
        # Base directory
        param = QgsProcessingParameterFile(
                'basedir',
                'Base Directory',
                behavior=QgsProcessingParameterFile.Folder,
                defaultValue=None,
                optional=True
            )
        param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(param)
        # scenarios
        param = QgsProcessingParameterString(
            'scenarios',
            'Scenarios ( s<n> == <scenario name> | <scenario name> | ... )',
            multiLine=True,
            defaultValue='',
            optional=True
        )
        param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(param)
        # events
        param = QgsProcessingParameterString(
            'events',
            'Events ( e<n> == <event name> | <event name> | ... )',
            multiLine=True,
            defaultValue='',
            optional=True
        )
        param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(param)

    def processAlgorithm(
            self,
            parameters: typing.Dict[str, typing.Any],
            context: 'QgsProcessingContext',
            feedback: 'QgsProcessingFeedback'
    ) -> typing.Dict[str, typing.Any]:
        results = {}

        # setup feedback
        steps = 2
        if parameters['zip']:
            steps += 1
        feedback_ = QgsProcessingMultiStepFeedback(steps, feedback)
        feedback_.setCurrentStep(0)

        # save TUFLOW exe
        if Path(parameters['tf_exe']).exists():
            tf_settings = TF_Settings()
            tf_settings.Load()
            tf_settings.project_settings.tf_exe = parameters['tf_exe']
            tf_settings.Save_Project()
            tf_settings.global_settings.tf_exe = parameters['tf_exe']
            tf_settings.Save_Global()

        tcf = Path(parameters['tcf'])
        outdir = tcf.parent / 'pm_{0}'.format(tcf.stem)

        # start building args list
        args = [parameters['tf_exe']]

        # setup ini
        ini_file = ''
        use_ini = parameters['outdir'] or parameters['basedir'] or parameters['scenarios'] or parameters['events']
        if use_ini:
            feedback_.pushInfo('Creating ini file...\n')
            tmpdir = tempfile.mkdtemp(prefix='package_model_')
            ini_file = Path(tmpdir) / 'package_model.ini'
            with ini_file.open('w') as f:
                if parameters['basedir']:
                    f.write('Base Folder == {0}\n'.format(parameters["basedir"]))
                if parameters['outdir']:
                    f.write('Copy Destination == {0}\n'.format(parameters["outdir"]))
                    outdir = Path(parameters['outdir'])
                if parameters['scenarios']:
                    for line in parameters['scenarios'].splitlines():
                        if '==' not in line:
                            feedback_.reportError('Invalid scenario line (missing "=="): {0}'.format(line))
                        f.write(create_command('Model Scenario', line))
                if parameters['events']:
                    for line in parameters['events'].splitlines():
                        if '==' not in line:
                            feedback_.reportError('Invalid event line (missing "=="): {0}'.format(line))
                        f.write(create_command('Model Event', line))

            # echo ini file
            feedback_.pushInfo('\n\n')
            with ini_file.open() as f:
                feedback_.pushInfo(f.read())
            feedback_.pushInfo('\n\n')

        # pm flag
        pm = '-pm'
        if parameters['all_files']:
            pm = '{0}All'.format(pm)
        if parameters['list_files']:
            pm = '{0}L'.format(pm)
        if use_ini:
            pm = '{0}ini'.format(pm)
        args.append(pm)
        if use_ini:
            args.append(ini_file)

        # xf flag
        xf = parameters['xf']
        if xf == 0:
            xf_ = '-xf0'
        elif xf == 1:
            xf_ = '-xf1'
        elif xf == 2:
            xf_ = '-xf2'
        else:
            feedback_.reportError('Invalid xf option')
            return results
        args.append(xf_)

        args.append('-nmb')
        args.append(parameters['tcf'])

        # run TUFLOW
        feedback_.pushInfo('Running TUFLOW with the following arguments...')
        args_ = args[1:]
        while args_:
            a = args_.pop(0)
            if '-pm' in a and 'ini' in a:
                feedback_.pushInfo('{0} {1}'.format(a, args_.pop(0)))
            else:
                feedback_.pushInfo(a)
        feedback_.pushInfo('\n')
        feedback_.setCurrentStep(1)
        proc = subprocess.run(args)

        if use_ini:
            feedback_.pushInfo('Deleting ini file...')
            shutil.rmtree(tmpdir)
            feedback_.pushInfo('Success\n')
        feedback_.setCurrentStep(2)

        # list files
        if parameters['list_files']:
            feedback_.pushInfo('Listing files...\n')
            file = outdir / 'pm.tcl'
            if file.exists():
                with file.open() as f:
                    feedback_.pushInfo(f.read())

        # zip output
        if parameters['zip']:
            if parameters['list_files']:
                feedback_.pushWarning('Cannot zip output when listing files only')
            else:
                feedback_.pushInfo('Zipping output...')
                folder_name = [x for x in outdir.iterdir() if x.is_dir()]
                if not folder_name:
                    feedback_.reportError('Could not find copied model in output folder')
                    return results
                model_dir = folder_name[0]
                zip_file_name = outdir / '{0}.zip'.format(model_dir.name)
                zip_file = zipfile.ZipFile(zip_file_name, 'w', zipfile.ZIP_DEFLATED)
                for (path, dirs, files) in os.walk(str(model_dir)):
                    archive_path = os.path.relpath(path, str(model_dir))
                    found_file = False
                    for file in files:
                        archive_file = os.path.join(archive_path, file)
                        feedback_.pushInfo('Adding {0} to zip file...'.format(archive_file))
                        zip_file.write(os.path.join(path, file), archive_file)
                        found_file = True
                    if not found_file:
                        zip_file.writestr(os.path.join(archive_path, 'placeholder.txt'),
                                          "(Empty directory)")
            feedback_.setCurrentStep(3)

        results['OUTPUT'] = str(outdir)

        return results

    def name(self) -> typing.AnyStr:
        return 'Package Model'

    def displayName(self) -> typing.AnyStr:
        return self.tr(self.name())

    def group(self) -> typing.AnyStr:
        return self.tr(self.groupId())

    def groupId(self) -> typing.AnyStr:
        return ''

    def shortHelpString(self) -> typing.AnyStr:
        folder = Path(os.path.realpath(__file__)).parent
        help_filename = folder / 'help' / 'html' / 'package_model.html'
        return self.tr(help_filename.open().read().replace('\n', '<p>'))

    def shortDescription(self) -> typing.AnyStr:
        return self.tr("Package a TUFLOW model")

    def createInstance(self) -> 'PackageModel':
        return PackageModel()

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)
