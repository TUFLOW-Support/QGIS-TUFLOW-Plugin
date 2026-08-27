from qgis.core import QgsProcessingParameterEnum, QgsProcessingParameterDefinition, Qgis, QgsProcessingContext
from qgis.gui import QgsGui, QgsAbstractProcessingParameterWidgetWrapper, QgsProcessingParameterWidgetFactoryInterface

from .processing_parameter_attach_signal import ProcessingParameterAttachSignalMixin


FLAG_OPTIONAL = Qgis.ProcessingParameterFlag.Optional if Qgis.QGIS_VERSION_INT >= 33600 else QgsProcessingParameterDefinition.FlagOptional


class CustomProcessingParameterEnum(QgsProcessingParameterEnum):
    """Subclass QgsProcessingParameterEnum so that signals can
    be setup. e.g. can setup signals to enable/disable based on the value
    of another widget.
    """
    TYPE = 'CustomProcessingParameterEnum'

    def type(self):
        return self.TYPE

    def clone(self):
        c = CustomProcessingParameterEnum(
            self.name(), self.description(), self.options(),
            self.allowMultiple(), self.defaultValue()
        )
        c.setFlags(self.flags())
        return c

    def checkValueIsAcceptable(self, value, context: QgsProcessingContext | None = None) -> bool:  # noqa: N802
        if value is None:
            return bool(self.flags() & FLAG_OPTIONAL)
        return super().checkValueIsAcceptable(value, context)

    @classmethod
    def registerWidget(cls) -> None:
        """Register the widget factory. Call once at plugin load time."""
        QgsGui.processingGuiRegistry().addParameterWidgetFactory(
            _CustomProcessingEnumWidgetFactory()
        )


class _CustomProcessingEnumWidgetWrapper(QgsAbstractProcessingParameterWidgetWrapper, ProcessingParameterAttachSignalMixin):

    def __init__(self, parameter, dialog_type, parent=None):
        super().__init__(parameter, dialog_type, parent)
        self.widget = None

    def postInitialize(self, wrappers):
        setup_callbacks = self.setupCallbacks(wrappers)
        for callback, wrapper in setup_callbacks:
            callback(self, wrapper, wrappers)

    def setOptions(self, options: list[str]):
        self.parameterDefinition().setOptions(options)
        self._inner.parameterDefinition().setOptions(options)

    def createWidget(self):
        defn = self.parameterDefinition()
        self._inner_defn = QgsProcessingParameterEnum(
            defn.name(), defn.description(), options=defn.options(), allowMultiple=defn.allowMultiple()
            )
        
        self._inner = QgsGui.processingGuiRegistry().createParameterWidgetWrapper(
            self._inner_defn, self.type()
            )
        self._inner.widgetValueHasChanged.connect(self.widgetValueHasChanged.emit)
        self.widget = self._inner.createWidget()
        return self.widget

    def setWidgetValue(self, value, context):
        self._inner.setWidgetValue(value, context)

    def widgetValue(self):
        return self._inner.widgetValue()

    def parameterLabelString(self):
        return self.parameterDefinition().description()


class _CustomProcessingEnumWidgetFactory(QgsProcessingParameterWidgetFactoryInterface):

    def parameterType(self) -> str:  # noqa: N802
        return CustomProcessingParameterEnum.TYPE

    def createWidgetWrapper(self, parameter, type_, parent=None):  # noqa: N802
        return _CustomProcessingEnumWidgetWrapper(parameter, type_, parent)

    def compatibleParameterTypes(self) -> list[str]:  # noqa: N802
        return [CustomProcessingParameterEnum.TYPE]

    def compatibleOutputTypes(self) -> list[str]:  # noqa: N802
        return []
        