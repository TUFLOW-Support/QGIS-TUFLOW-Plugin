import socket
import threading
from pathlib import Path

from qgis.core import QgsMapLayer, QgsVectorLayer, QgsRasterLayer, QgsProject
from qgis.PyQt.QtCore import QObject, pyqtSignal

from tuflow.gui.logging import Logging
from tuflow.tuflowqgis_library import tuflowqgis_apply_check_tf_clayer


class QgisListener(QObject):

    receivedPath = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._socket = None
        self.receivedPath.connect(self.log_received_path)

    def log_received_path(self, path: str):
        """Log the received path."""
        Logging.info(f"Received path: {path}")

    def start(self):
        if self._socket is not None:
            Logging.warning("QGIS socket listener is already running.")
            return

        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.bind(('localhost', 9999))
        self._socket.listen(1)
        Logging.info("QGIS socket listener running...")

        def handle():
            while True:
                conn, _ = self._socket.accept()
                uri = db = conn.recv(1024).decode('utf-8')
                self.receivedPath.emit(uri)
                if '|layername=' in uri:
                    db, lyrname = uri.split('|layername=', 1)
                else:
                    lyrname = Path(db).stem
                provider = 'ogr' if Path(db).suffix in ['.shp', '.gpkg', '.mif'] else 'gdal'
                layer = QgsVectorLayer(uri, lyrname, provider) if provider == 'ogr' else QgsRasterLayer(uri, lyrname, provider)
                if layer.isValid():
                    if layer.type() == QgsMapLayer.VectorLayer:
                        tuflowqgis_apply_check_tf_clayer(None, layer=layer)
                    QgsProject.instance().addMapLayer(layer)
                conn.close()

        threading.Thread(target=handle, daemon=True).start()

    def stop(self):
        if self._socket is None:
            Logging.warning("QGIS socket listener is not running.")
            return
        self._socket.close()
        self._socket = None
        Logging.info("QGIS socket listener stopped.")
