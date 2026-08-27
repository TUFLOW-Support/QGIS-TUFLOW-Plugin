import logging
from logging import StreamHandler
from contextlib import contextmanager


class CustomLoggingHandler(StreamHandler):
    """Custom log handler so that logging can be checked. Use global instance below."""

    def __init__(self):
        super().__init__()
        self.msg_filters = []
        self.msg_count = 0
        self.caught_messages = []
        self.use_filter = False

    @contextmanager
    def catch(self):
        with self.catch_with_filter(None) as handler:
            handler.use_filter = False
            yield handler

    @contextmanager
    def catch_with_filter(self, msgs):
        """Use a context manager so that the previous handlers can be restored no matter how the test exits."""
        self.use_filter = True
        if msgs is None:
            self.msg_filters = None
        else:
            self.msg_filters = msgs.copy()
        pt_logger = logging.getLogger('pytuflow')
        viewer_logger = logging.getLogger('tuflow_viewer')
        exist_hdlrs = pt_logger.handlers.copy()
        for hdlr in exist_hdlrs:
            pt_logger.removeHandler(hdlr)
        viewer_handlers = viewer_logger.handlers.copy()
        for hdlr in viewer_handlers:
            viewer_logger.removeHandler(hdlr)
        pt_logger.addHandler(self)
        viewer_logger.addHandler(self)
        yield self
        pt_logger.removeHandler(self)
        viewer_logger.removeHandler(self)
        for hdlr in exist_hdlrs:
            pt_logger.addHandler(hdlr)
        for hdlr in viewer_handlers:
            viewer_logger.addHandler(hdlr)
        if self.msg_filters is not None:
            self.msg_filters.clear()
        self.msg_count = 0
        self.caught_messages.clear()

    def handle(self, record):
        if not self.use_filter or (self.msg_filters and record.msg in self.msg_filters):
            self.msg_count += 1
            self.caught_messages.append(record.msg)
        else:
            super().handle(record)


custom_log_handler = CustomLoggingHandler()
