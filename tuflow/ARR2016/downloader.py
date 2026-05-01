from time import sleep

try:
    from qgis.core import QgsNetworkAccessManager
    from qgis.PyQt.QtNetwork import QNetworkRequest
    from qgis.PyQt.QtCore import QUrl
except ImportError:
    QgsNetworkAccessManager = None
    QNetworkRequest = None
    QUrl = None

import requests
from qgis.PyQt.QtCore import QSettings, QEventLoop

import logging
logger = logging.getLogger('ARR2019')


from ..compatibility_routines import QT_EVENT_LOOP_EXCLUDE_USER_INPUT_EVENTS, QT_NETWORK_REQUEST_HTTP_STATUS_CODE_ATTRIBUTE


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

    def download(self, retry_count = 5, retry_interval = range(5, 30, 5), validator = None):
        old_user_agent = None
        netman = QgsNetworkAccessManager.instance()
        # QgsNetworkAccessManager.instance().cache().remove(QUrl(self.url))  # tmp
        req = QNetworkRequest(QUrl(self.url))
        for k, v in self.headers.items():
            req.setRawHeader(k.encode(), v.encode())
            if k == 'User-Agent':
                if QSettings().contains('/qgis/networkAndProxy/userAgent'):
                    old_user_agent = QSettings().value('/qgis/networkAndProxy/userAgent')
                QSettings().setValue('/qgis/networkAndProxy/userAgent', v)
        try_count = -1
        retry_interval = list(retry_interval)
        data = bytearray(b'')
        while True:
            try_count += 1
            reply = netman.get(req)
            evloop = QEventLoop()
            reply.finished.connect(evloop.quit)
            evloop.exec(QT_EVENT_LOOP_EXCLUDE_USER_INPUT_EVENTS)
            if old_user_agent:
                QSettings().setValue('/qgis/networkAndProxy/userAgent', old_user_agent)
            else:
                QSettings().remove('/qgis/networkAndProxy/userAgent')
            self.ret_code = reply.attribute(QT_NETWORK_REQUEST_HTTP_STATUS_CODE_ATTRIBUTE)
            if self.ret_code == 200:
                data = bytearray(reply.readAll())
            if self.ret_code != 200:
                logger.info(f'HTTP get failed with code: {self.ret_code}')
                if try_count < retry_count:
                    t = retry_interval[try_count]
                    logger.info(f'Trying again in {t} seconds...')
                    sleep(t)
                    logger.info(f'Retry attempt #{try_count+1}')
                    continue
                self.error_string = reply.errorString()
            elif validator is not None and not validator(data):
                if try_count < retry_count:
                    t = retry_interval[try_count]
                    logger.info(f'Trying again in {t} seconds...')
                    sleep(t)
                    logger.info(f'Retry attempt #{try_count + 1}')
                    QgsNetworkAccessManager.instance().cache().remove(QUrl(self.url))
                    continue
                self.ret_code = None
                self.error_string = 'Downloaded data is invalid or incomplete.'
            break
        if self.error_string:
            return
        content_type = reply.rawHeader(b'Content-Type')
        if b'zip' not in content_type:
            self.data = data.decode('utf-8')
        else:
            self.data = data



class DownloaderRequests(Downloader):

    def type(self):
        return 'Requests'

    def download(self):
        r = requests.get(self.url, headers=self.headers, timeout=20)
        self.ret_code = r.status_code
        if not r.ok:
            self.error_string = r.text
            return
        if 'zip' not in r.headers.get('content-type') and isinstance(r.content, bytes):
            self.data = r.content.decode('utf-8')
        else:
            self.data = r.content
