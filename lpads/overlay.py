import json
import time
import socket

try:
    from EDMCOverlay import edmcoverlay
except ImportError:
    try:
        from edmcoverlay import edmcoverlay
    except ImportError:
        edmcoverlay = None

# EDMC Overlay fixed settings
SERVER_ADDRESS = "127.0.0.1"
SERVER_PORT = 5010
VIRTUAL_WIDTH = 1280.0
VIRTUAL_HEIGHT = 1024.0
VIRTUAL_ORIGIN_X = 20.0
VIRTUAL_ORIGIN_Y = 40.0


class Overlay(object):
    """
    Client for EDMCOverlay
    """

    def __init__(self, logger, server=SERVER_ADDRESS, port=SERVER_PORT):
        self.server = server
        self.port = port
        self.conn = None
        self.logger = logger
        self._overlay = None
        if edmcoverlay is not None:
            if hasattr(edmcoverlay.Overlay, "send_command"):
                logger.info("most likely using edmcoverlay for linux")
                self._overlay = edmcoverlay.Overlay()
            elif hasattr(edmcoverlay.Overlay, "_emit_payload"):
                logger.info("most likely using EDMC-ModernOverlay")
                self._overlay = edmcoverlay.Overlay()
            else:
                logger.info("fallback to use original EDMCOverlay")

    def connect(self):
        """
        open the connection
        :return:
        """
        if self._overlay is not None:
            self._overlay.connect()
        elif self.conn is None:
            try:
                self.conn = socket.socket()
                self.conn.connect((self.server, self.port))
            except Exception as err:
                self.logger.warning("Can't connect to EDMC Overlay", exc_info=err)
                self.conn = None

    def send_raw(self, msg, delay=100):
        """
        Encode a dict and send it to the server
        :param msg:
        :return:
        """
        if self._overlay is not None:
            self._overlay.send_raw(msg)
            if delay:
                delay = min(max(delay, 0), 500)
                time.sleep(float(delay) / 1000.0)
        elif self.conn:
            try:
                self.conn.send(json.dumps(msg).encode())
                self.conn.send(b"\n")
                if delay:
                    delay = min(max(delay, 0), 500)
                    time.sleep(float(delay) / 1000.0)
            except Exception as err:
                self.logger.warning("Can't send to EDMC Overlay", exc_info=err)
                self.conn = None
