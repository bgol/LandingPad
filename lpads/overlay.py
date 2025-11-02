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

from .misc import round_away

# EDMC Overlay fixed settings
SERVER_ADDRESS = "127.0.0.1"
SERVER_PORT = 5010


class Overlay(object):
    """
    Client for EDMCOverlay
    """

    VIRTUAL_ORIGIN_X = 20
    VIRTUAL_ORIGIN_Y = 40
    VIRTUAL_WIDTH = 1280
    VIRTUAL_HEIGHT = 1024
    WIDTH_SCALE_ADD = 32
    HEIGHT_SCALE_ADD = 18

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
                self.VIRTUAL_ORIGIN_X = 0
                self.VIRTUAL_ORIGIN_Y = 0
                self.WIDTH_SCALE_ADD = 0
                self.HEIGHT_SCALE_ADD = 0
            elif hasattr(edmcoverlay.Overlay, "_emit_payload"):
                logger.info("most likely using EDMC-ModernOverlay")
                self._overlay = edmcoverlay.Overlay()
                self.VIRTUAL_ORIGIN_X = 0
                self.VIRTUAL_ORIGIN_Y = 0
                self.WIDTH_SCALE_ADD = 0
                self.HEIGHT_SCALE_ADD = 0
            else:
                logger.info("fallback to use original EDMCOverlay")

    def config(self, width, height):
        if self._overlay is not None:
            self.VIRTUAL_WIDTH = width
            self.VIRTUAL_HEIGHT = height
        else:
            self.VIRTUAL_WIDTH = 1280
            self.VIRTUAL_HEIGHT = 1024
        self.logger.info("Overlay is set to:")
        self.logger.info(f"\t{self.VIRTUAL_ORIGIN_X = }")
        self.logger.info(f"\t{self.VIRTUAL_ORIGIN_Y = }")
        self.logger.info(f"\t{self.VIRTUAL_WIDTH = }")
        self.logger.info(f"\t{self.VIRTUAL_HEIGHT = }")
        self.logger.info(f"\t{self.WIDTH_SCALE_ADD = }")
        self.logger.info(f"\t{self.HEIGHT_SCALE_ADD = }")

    def calc_aspect_x(self, screen_w, screen_h):
        if self._overlay is not None:
            ret_value = 1.0
        else:
            ret_value = (
                (self.VIRTUAL_WIDTH + self.WIDTH_SCALE_ADD)
                / (self.VIRTUAL_HEIGHT + self.HEIGHT_SCALE_ADD)
                * (screen_h - 2 * self.VIRTUAL_ORIGIN_Y)
                / (screen_w - 2 * self.VIRTUAL_ORIGIN_X)
            )
        self.logger.info(f"calc_aspect_x({screen_w}, {screen_h}) -> {ret_value}")
        return ret_value

    def calc_max_xy(self, aspect_x):
        if self._overlay is not None:
            ret_value = self.VIRTUAL_WIDTH, self.VIRTUAL_HEIGHT
        else:
            ret_value = (
                round_away((self.VIRTUAL_WIDTH + self.WIDTH_SCALE_ADD - 1) / aspect_x),
                round_away(self.VIRTUAL_HEIGHT + self.HEIGHT_SCALE_ADD - 1)
            )
        self.logger.info(f"calc_max_xy({aspect_x}) -> {ret_value}")
        return ret_value

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
