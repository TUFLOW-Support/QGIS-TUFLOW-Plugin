from collections import OrderedDict

from .tvlogging import QgisTuflowLoggingHandler
from qgis.PyQt.QtCore import QSettings
import logging
from time import perf_counter
logger = logging.getLogger('tuflow_viewer')


def set_log_level(level: str):
    logger.setLevel(level)
    for hnd in logger.handlers:
        if isinstance(hnd, QgisTuflowLoggingHandler):
            hnd.setLevel(level)


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class Task:

    def __init__(self):
        self.prev_time = perf_counter()
        self.total_time = 0.
        self.running = True

    def update(self):
        curr_time = perf_counter()
        if self.running:
            elapsed = curr_time - self.prev_time
            self.total_time += elapsed
            self.running = False
        else:
            self.prev_time = curr_time
            self.running = True


class Profiler(metaclass=Singleton):

    def __init__(self):
        self._tasks = OrderedDict()

    def __call__(self, key: str = None):
        if key not in self._tasks:
            self._tasks[key] = Task()
        else:
            self._tasks[key].update()

    def report(self):
        for key, task in reversed(self._tasks.items()):
            if task.running:
                task.update()
            logger.info(f'Profiler: {key}: {task.total_time:.4f} seconds')
        self._tasks.clear()
