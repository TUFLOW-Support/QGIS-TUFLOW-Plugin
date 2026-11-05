"""
Background worker for running the pytuflow ``arr`` tool off the GUI thread.

:meth:`Arr2026Dock._on_run_clicked` builds the pytuflow json config(s) on the main
thread (this requires QGIS layer/``processing`` access - see
:class:`generate_pytuflow_json.GenerateARRjson`), then hands the already-built
json/config(s) to :class:`ArrRunWorker`, which is moved to a ``QThread`` to perform
the (potentially slow) network request(s), engine computation and output writing
without blocking the QGIS GUI. This mirrors the worker/``QThread`` pattern used
elsewhere in this plugin (see ``SCS/engine.py``, ``ReFH2/refh2.py``).
"""

from __future__ import annotations

from typing import Optional

from qgis.PyQt.QtCore import QObject, pyqtSignal

from ..pt.pytuflow.arr.api_client import ArrApiClient
from ..pt.pytuflow.arr.config import ArrConfig
from ..pt.pytuflow.arr.engine import ArrEngine
from ..pt.pytuflow.arr.writers import write_outputs
from ..pt.pytuflow.arr.working_data import write_working_data
from .arr_shared_functionality import write_json_configs

# Filename prefix used for every generated json config written to disk during a run - see
# :func:`arr_shared_functionality.write_json_configs`.
_GENERATED_JSON_NAME_PREFIX = 'generated_input'


class ArrRunWorker(QObject):
    """``QObject`` worker that runs the pytuflow ``arr`` tool (network fetch + engine +
    output writing) for an already-built json config (single catchment) or set of
    configs (multiple catchments). Intended to be moved to a ``QThread`` via
    ``moveToThread`` so this work doesn't block the QGIS GUI thread - see
    :meth:`Arr2026Dock._on_run_clicked`.

    Signals
    -------
    log_message(str, str)
        Emitted as ``(message, level)`` - mirrors :meth:`Arr2026Dock._log`'s signature.
        Also used as the target of the ``pytuflow`` logging bridge (see
        :class:`pytuflow_log_bridge._PytuflowLogBridge`) so log messages raised from
        this worker's thread are safely marshalled back to the GUI thread.
    progress(int)
        Emitted with a percentage (0-100) as multi-catchment runs progress.
        The json config generation step (completed before this worker is created) is the first of ``total_steps``;
        one step per catchment run through pytuflow is done here.
    finished(str)
        Emitted once the run has finished - an empty string indicates success,
        otherwise the error message describing why the run failed.
    """

    log_message = pyqtSignal(str, str)
    progress = pyqtSignal(int)
    finished = pyqtSignal(str)

    def __init__(
            self, multiple_catchments: bool,
            pytuflow_json: Optional[dict] = None,
            build_result: Optional[dict] = None,
            total_steps: Optional[int] = None,
    ) -> None:
        """
        :param multiple_catchments: whether this is a "multiple catchments" run
            (``build_result`` must be supplied) or a single-catchment run
            (``pytuflow_json`` must be supplied).
        :param pytuflow_json: the already-built pytuflow json config dict for a
            single-catchment run (see ``GenerateARRjson.build_json``).
        :param build_result: the already-built result dict for a multiple-catchments
            run (see ``GenerateARRjson.build_json_multiple``).
        :param total_steps: total number of progress bar steps for this run - 1 (the json
            config generation step, already completed by the time this worker runs) plus
            one per catchment that will be run through pytuflow. Defaults to 2 for a
            single-catchment run, or ``1 + len(build_result['configs'])`` for a
            multi catchment run.
        """

        super().__init__()
        self._multiple_catchments = multiple_catchments
        self._pytuflow_json = pytuflow_json
        self._build_result = build_result
        if total_steps is not None:
            self._total_steps = total_steps
        elif multiple_catchments and build_result is not None:
            self._total_steps = 1 + len(build_result['configs'])
        else:
            self._total_steps = 2

    def _log_info(self, message: str) -> None:
        self.log_message.emit(message, 'info')

    def _log_warning(self, message: str) -> None:
        self.log_message.emit(message, 'warning')

    def _log_error(self, message: str) -> None:
        self.log_message.emit(message, 'error')

    def run(self) -> None:
        """Entry point connected to ``QThread.started`` - runs the single- or
        multiple-catchment pytuflow ``arr`` tool (whichever this worker was
        constructed for) and emits :attr:`finished` with an empty string on success,
        or the error message on failure."""

        try:
            if self._multiple_catchments:
                self._run_multiple_catchments(self._build_result)
            else:
                self._run_single_catchment(self._pytuflow_json)
        except Exception as e:
            self.finished.emit(str(e))
            return
        self.finished.emit('')

    def _run_single_catchment(self, pytuflow_json: dict) -> None:
        """Runs the pytuflow ``arr`` tool for a single already-built json config.
        This is used when there is only one catchment/site, i.e. the
        ``inputs_catchment_multiple_catchments_checkbox`` checkbox is unchecked."""

        config = ArrConfig.from_dict(pytuflow_json)
        client = ArrApiClient()
        response = client.fetch(config)
        engine = ArrEngine(config, response)
        results = engine.run()
        write_working_data(config, response, engine)
        write_outputs(config, results)
        # This catchment's step passed to pytuflow is now complete
        self.progress.emit(int(round((1 + 1) / self._total_steps * 100)))

        write_json_configs(
            config.output.path, [{'site_name': config.site.name, 'json': pytuflow_json}],
            name_prefix=_GENERATED_JSON_NAME_PREFIX)

    def _run_multiple_catchments(self, build_result: dict) -> None:
        """Runs the pytuflow ``arr`` tool once per already-built catchment json config.
        This is used when there are multiple catchments/sites, i.e. the
        ``inputs_catchment_multiple_catchments_checkbox`` checkbox is checked.

        Each catchment's json is run independently so if one fails, a warning is
        output and that catchment is skipped. It will then move to the next
        catchment. At the end of the log, every skipped catchment is summarised in
        an error message to ensure nothing is missed by the user.

        Every generated json config is written into the same folder
        (``working_data``), then loaded back via ``ArrConfig.from_files`` (pytuflow's
        method) multiple-configuration-file input option.
        """

        configs = build_result['configs']
        # (site name, error message) pairs
        aborted: list[tuple[str, str]] = [
            (error['catchment'], error['error']) for error in build_result['errors']
        ]
        total_catchments = len(configs) + len(build_result['errors'])

        if not configs:
            raise ValueError("No catchment json configs could be built - see log above for details.")

        # Write every catchment's json config out to disk ('working_data') folder.
        output_path = configs[0]['json']['output']['path']
        named_configs = [
            {'site_name': entry['site_name'] or f'catchment {i + 1}', 'json': entry['json']}
            for i, entry in enumerate(configs)
        ]
        config_paths = write_json_configs(output_path, named_configs, name_prefix=_GENERATED_JSON_NAME_PREFIX)

        # Load every catchment's json config and run via pytuflow multiple-configuration-file input option
        try:
            parsed_configs = ArrConfig.from_files(config_paths)
        except Exception as e:
            raise ValueError(f"Failed to load generated catchment json config(s): {e}") from e

        client = ArrApiClient()
        succeeded = 0
        for i, (config_path, config) in enumerate(zip(config_paths, parsed_configs)):
            site_name = config.site.name or config_path.stem
            self._log_info(f"Processing catchment {i + 1} of {len(parsed_configs)}: '{site_name}'")
            try:
                response = client.fetch(config)
                engine = ArrEngine(config, response)
                results = engine.run()
                write_working_data(config, response, engine)
                write_outputs(config, results, append=succeeded > 0)
                succeeded += 1
            except Exception as e:
                self._log_warning(f"Skipping catchment '{site_name}': {e}")
                aborted.append((site_name, str(e)))
            finally:
                # This catchment's step passed to pytuflow is now complete
                self.progress.emit(int(round((1 + i + 1) / self._total_steps * 100)))

        if aborted:
            summary = '\n'.join(f"  - '{name}': {error}" for name, error in aborted)
            self._log_error(
                f"{len(aborted)} of {total_catchments} catchment(s) were aborted and skipped:\n{summary}"
            )

        if succeeded == 0:
            raise ValueError("Every catchment failed - see log above for details.")
