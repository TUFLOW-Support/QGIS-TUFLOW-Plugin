import typing

from qgis.gui import QgsAbstractProcessingParameterWidgetWrapper


class ProcessingParameterAttachSignalMixin:

    def setupCallbacks(self, wrappers) -> list[tuple[typing.Callable, QgsAbstractProcessingParameterWidgetWrapper]]:
        setup_callbacks = []
        meta = self.parameterDefinition().metadata()
        for callback_config in meta.get('callbacks', []):
            ctrl = callback_config.get('control')
            callback = callback_config.get('callback')
            if not ctrl or not callback:
                continue
            wrapper = [x for x in wrappers if x.parameterDefinition().name() == ctrl]
            if not wrapper:
                continue
            wrapper = wrapper[0]

            wrapper.widgetValueHasChanged.connect(lambda w, cb=callback, wr=wrapper: cb(self, wr, wrappers))

            setup_callbacks.append((callback, wrapper))

        return setup_callbacks
