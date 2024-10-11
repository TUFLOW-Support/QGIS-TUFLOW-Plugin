try:
    from qgis.core import QgsNetworkAccessManager
    from PyQt5.QtNetwork import QNetworkRequest
    from PyQt5.QtCore import QUrl
except ImportError:
    QgsNetworkAccessManager = None
    QNetworkRequest = None
    QUrl = None

import requests
from PyQt5.QtCore import QSettings, QEventLoop


class Downloader:
    """Downloader class that uses QgsNetworkAccessManager which inherits proxy settings from QGIS."""

    def __new__(cls, url, headers=None):
        if Downloader.has_qgis_libs():
            cls = DownloaderQGIS
        else:
            cls = DownloaderRequests
        return object.__new__(cls)

    def __init__(self, url, headers=None):
        self.url = url
        self.headers = {} if headers is None else headers
        self.data = None
        self.ret_code = None
        self.error_string = ''

    @staticmethod
    def has_qgis_libs():
        if QgsNetworkAccessManager is None or QNetworkRequest is None or QUrl is None:
            return False
        return True

    def type(self):
        pass

    def ok(self):
        return self.ret_code == 200

    def error_string(self):
        pass

    def download(self):
       pass


class DownloaderQGIS(Downloader):

    def type(self):
        return 'QGIS'

    def error_string(self):
        return self.reply.errorString()

    def download(self):
        old_user_agent = None
        netman = QgsNetworkAccessManager.instance()
        req = QNetworkRequest(QUrl(self.url))
        for k, v in self.headers.items():
            req.setRawHeader(k.encode(), v.encode())
            if k == 'User-Agent':
                if QSettings().contains('/qgis/networkAndProxy/userAgent'):
                    old_user_agent = QSettings().value('/qgis/networkAndProxy/userAgent')
                QSettings().setValue('/qgis/networkAndProxy/userAgent', v)
        reply = netman.get(req)
        evloop = QEventLoop()
        reply.finished.connect(evloop.quit)
        evloop.exec_(QEventLoop.ExcludeUserInputEvents)
        if old_user_agent:
            QSettings().setValue('/qgis/networkAndProxy/userAgent', old_user_agent)
        else:
            QSettings().remove('/qgis/networkAndProxy/userAgent')
        self.ret_code = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
        if self.ret_code != 200:
            self.error_string = reply.errorString()
            return
        self.data = bytearray(reply.readAll())
        content_type = reply.rawHeader(b'Content-Type')
        if b'zip' not in content_type:
            self.data = self.data.decode('utf-8')



class DownloaderRequests(Downloader):

    def type(self):
        return 'Requests'

    def download(self):
        r = requests.get(self.url, headers=self.headers)
        self.ret_code = r.status_code
        if not r.ok:
            self.error_string = r.text
            return
        if 'zip' not in r.headers.get('content-type') and isinstance(r.content, bytes):
            self.data = r.content.decode('utf-8')
        else:
            self.data = r.content
