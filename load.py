# -*- coding: utf-8 -*-
#
# Display the "LandigPad" position for Starports.
#

import logging
import os
import math
import json
import time
import socket

import tkinter as tk
from tkinter import ttk

import myNotebook as nb
from ttkHyperlinkLabel import HyperlinkLabel
from config import appname, config

PLUGIN_NAME = os.path.basename(os.path.dirname(__file__))
logger = logging.getLogger(f"{appname}.{PLUGIN_NAME}")

__version_info__ = (2, 0, 4)
__version__ = ".".join(map(str, __version_info__))

PLUGIN_URL = 'https://github.com/bgol/LandingPad'
PREFSNAME_BACKWARD = "landingpad_backward"
PREFSNAME_MAX_WIDTH = "landingpad_max_width"
PREFSNAME_HIDE_CANVAS = "landingpad_hide_canvas"
PREFSNAME_STN_OVERLAY = "landingpad_stn_overlay"
PREFSNAME_COL_OVERLAY = "landingpad_col_overlay"
PREFSNAME_SCR_OVERLAY = "landingpad_scr_overlay"
PREFSNAME_USE_OVERLAY = "landingpad_use_overlay"
PREFSNAME_MS_DELAY = "landingpad_ms_delay"
OPTIONS_GREENSIDE = ["right", "left"]
MAX_WIDTH_MINIMUM = 150

class This():
    """For holding module globals"""
    # general settings
    col_stn: str = "black"
    col_pad: str = "blue"
    backward: bool = False
    max_width: int = 0
    use_canvas: bool = True

    # EDMC Overlay settings
    use_overlay: bool = False
    over_radius: int = 100
    over_center_x: int = 100
    over_center_y: int = 490
    over_aspect_x: int = 1
    over_ms_delay: int = 100
    over_color_stn: str = "#ffffff"
    over_color_pad: str = "yellow"
    over_ttl: int = 10*60

    # other used globals
    id_list = []
    curr_show: bool = None
    hide_events: set[str] = {'Docked', 'DockingCancelled', 'DockingTimeout', 'StartJump', 'Shutdown'}
    show_types: set[str] = {'bernal', 'coriolis', 'orbis', 'asteroidbase', 'ocellus'}

    # GUI elements
    stn_frame: tk.Frame = None
    dummy: tk.Frame = None
    stn_canvas: 'LandingPads' = None
    greenside: tk.StringVar = None
    prefs_max_width: tk.IntVar = None
    prefs_hide_canvas: tk.BooleanVar = None
    overlay: 'Overlay' = None
    prefs_radius: tk.IntVar = None
    prefs_center_x: tk.IntVar = None
    prefs_center_y: tk.IntVar = None
    prefs_screen_w: tk.IntVar = None
    prefs_screen_h: tk.IntVar = None
    prefs_use_over: tk.BooleanVar = None
    prefs_ms_delay: tk.IntVar = None

    def __str__(self) -> str:
        return ("\n".join(line for line in ("",
            f"{self.col_stn = }",
            f"{self.col_pad = }",
            f"{self.backward = }",
            f"{self.max_width = }",
            f"{self.use_canvas = }",
            f"{self.use_overlay = }",
            f"{self.over_radius = }",
            f"{self.over_center_x = }",
            f"{self.over_center_y = }",
            f"{self.over_aspect_x = }",
            f"{self.over_ms_delay = }",
            f"{self.over_color_stn = }",
            f"{self.over_color_pad = }",
            f"{self.over_ttl = }",
            f"{self.hide_events = }",
            f"{self.show_types = }",
        )))

this = This()

# EDMC Overlay fixed settings
SERVER_ADDRESS = "127.0.0.1"
SERVER_PORT = 5010
VIRTUAL_WIDTH = 1280.0
VIRTUAL_HEIGHT = 1024.0
VIRTUAL_ORIGIN_X = 20.0
VIRTUAL_ORIGIN_Y = 40.0

# For compatibility with pre-5.0.0
if not hasattr(config, "get_int"):
    config.get_int = config.getint
if not hasattr(config, 'get_bool'):
    config.get_bool = lambda key, default=False: bool(config.getint(key))
if not hasattr(config, "get_str"):
    config.get_str = config.get

def round_away(val):
    val += -0.5 if val < 0 else 0.5
    return int(val)

def calc_aspect_x(sw, sh):
    return (VIRTUAL_WIDTH+32) / (VIRTUAL_HEIGHT+18) * (sh-2*VIRTUAL_ORIGIN_Y) / (sw-2*VIRTUAL_ORIGIN_X)

class Overlay(object):
    """
    Client for EDMCOverlay
    """

    def __init__(self, server=SERVER_ADDRESS, port=SERVER_PORT):
        self.server = server
        self.port = port
        self.conn = None

    def connect(self):
        """
        open the connection
        :return:
        """
        if self.conn is None:
            try:
                self.conn = socket.socket()
                self.conn.connect((self.server, self.port))
            except Exception as err:
                logger.warning("Can't connect to EDMC Overlay", exc_info=err)
                self.conn = None

    def send_raw(self, msg, delay=100):
        """
        Encode a dict and send it to the server
        :param msg:
        :return:
        """
        if self.conn:
            try:
                self.conn.send(json.dumps(msg).encode())
                self.conn.send(b"\n")
                if delay:
                    delay = min(max(delay, 0), 500)
                    time.sleep(float(delay) / 1000.0)
            except Exception as err:
                logger.warning("Can't send to EDMC Overlay", exc_info=err)
                self.conn = None

class LandingPads(tk.Canvas):

    pad_list = [
        (0,0), (0,0), (0,2), (0,2),
        (1,0), (1,0), (1,1), (1,2),
        (2,0), (2,2),
        (3,0), (3,0), (3,1), (3,2), (3,2),
    ]
    shell_scale = (1, 0.625, 0.455, 0.25)

    def __init__(
        self, parent, cur_pad=None, backward=False,
        col_stn="black", col_pad="blue", **kwargs
    ):
        tk.Canvas.__init__(self, parent, **kwargs)
        self.bind("<Configure>", self.on_resize)
        self.width = self.winfo_reqwidth()
        if this.max_width:
            self.width = min(self.width, this.max_width)
        self.height = self.width
        self.cur_pad = cur_pad
        self.col_pad = col_pad
        self.col_stn = col_stn
        self.pad_obj = None
        self.stn_obj = False
        self.backward = backward
        self.calc_values()

    def calc_values(self):
        self.alpha = math.radians(15)
        self.sin15 = math.sin(self.alpha)
        self.cos15 = math.cos(self.alpha)
        self.sin45 = math.sqrt(2) / 2
        self.sin60 = math.sqrt(3) / 2
        self.dodecagon = [
            (+self.cos15, -self.sin15),
            (+self.sin45, -self.sin45),
            (+self.sin15, -self.cos15),
            (-self.sin15, -self.cos15),
            (-self.sin45, -self.sin45),
            (-self.cos15, -self.sin15),
            (-self.cos15, +self.sin15),
            (-self.sin45, +self.sin45),
            (-self.sin15, +self.cos15),
            (+self.sin15, +self.cos15),
            (+self.sin45, +self.sin45),
            (+self.cos15, +self.sin15),
        ]
        self.pad_sectors = [
            ( 0, +1), (-0.5, +self.sin60), (-self.sin60, +0.5),
            (-1,  0), (-self.sin60, -0.5), (-0.5, -self.sin60),
            ( 0, -1), (+0.5, -self.sin60), (+self.sin60, -0.5),
            (+1,  0), (+self.sin60, +0.5), (+0.5, +self.sin60),
        ]

    def config(self, **kwargs):
        self.col_stn = kwargs.pop("col_stn", self.col_stn)
        self.col_pad = kwargs.pop("col_pad", self.col_pad)
        self.cur_pad = kwargs.pop("cur_pad", self.cur_pad)
        self.backward = kwargs.pop("backward", self.backward)
        if this.max_width and "width" in kwargs:
            kwargs["width"] = min(kwargs["width"], this.max_width)
            kwargs["height"] = kwargs["width"]
        tk.Canvas.config(self, **kwargs)
        self.draw_station()
        self.draw_pad(self.cur_pad)

    def on_resize(self, event):
        # resize the canvas
        self.width = self.height = event.width
        self.config(width=self.width, height=self.height)

    def get_poly_points(self, cx, cy, r):
        return [
            (
                cx + round_away(dx*r),
                cy + round_away(dy*r),
            )
            for (dx, dy) in self.dodecagon
        ]

    def get_toaster(self, r, s=0):
        dx = round_away(r * 0.75)
        dy = round_away(r * self.shell_scale[-1])
        dr = round_away(dy * 0.08)
        toaster = [
            (+0,     -dy-s),
            (+dx-dr, -dy-s),
            (+dx+dr, -dy+2*dr-s),
            (+r-dr,  -dy+2*dr-s),
            (+r-s,   -dy+3*dr-s),
            (+r-s,   +dy-3*dr+s),
            (+r-dr,  +dy-2*dr+s),
            (+dx+dr, +dy-2*dr+s),
            (+dx-dr, +dy+s),
            (+0,     +dy+s),
        ]
        return toaster

    def draw_station(self):
        # redraw
        self.delete("all")
        self.pad_obj = None
        self.stn_obj = False
        self.centerX = centerX = int(self.width/2 + 0.5)
        self.centerY = centerY = int(self.height/2 + 0.5)
        minval = min(centerX, centerY)
        strong = 4 - (minval < 250) - (minval < 150) - (minval < 50)
        self.radiusP = radiusP = minval - strong

        strong = 4 - (radiusP < 250) - (radiusP < 150) - (radiusP < 50)
        shellList = []
        lenScale = len(self.shell_scale)
        for p, scale in enumerate(self.shell_scale):
            r = radiusP * scale
            polyPoints = self.get_poly_points(centerX, centerY, r)
            if 0 < p < lenScale-1:
                lw = max(1, strong-1)
            else:
                lw = strong
            self.create_polygon(*polyPoints, width=lw, outline=self.col_stn, fill='', joinstyle=tk.ROUND)
            shellList.append(polyPoints)

        for (x1, y1), (x2, y2) in zip(shellList[0], shellList[-1]):
            self.create_line(x1, y1, x2, y2, width=strong, fill=self.col_stn, capstyle=tk.ROUND)

        toaster = self.get_toaster(radiusP)
        green = "red" if self.backward else "green"
        red = "green" if self.backward else "red"
        self.create_line(*[(centerX+dx, centerY+dy) for (dx, dy) in toaster],width=2*strong,fill=green,capstyle=tk.BUTT, joinstyle=tk.ROUND)
        self.create_line(*[(centerX-dx, centerY+dy) for (dx, dy) in toaster],width=2*strong,fill=red,capstyle=tk.BUTT, joinstyle=tk.ROUND)
        self.stn_obj = True

    def get_pad_coords(self, pad):
        pad %= 45
        s, t = self.pad_list[pad % 15]
        s += int(pad / 15) * 4
        return (s, t)

    def draw_pad(self, pad):
        if self.pad_obj:
            self.delete(self.pad_obj)
            self.pad_obj = None
        if not self.stn_obj:
            self.draw_station()
        self.cur_pad = pad
        if pad:
            if isinstance(pad, tuple):
                s, t = pad
            else:
                s, t = self.get_pad_coords(pad-1)
                if self.backward:
                    s = (s+6) % 12
            dx, dy = self.pad_sectors[s]
            dot = self.radiusP * (self.shell_scale[0] - self.shell_scale[1]) / 4
            td = (self.shell_scale[t] + self.shell_scale[t+1]) / 2
            ov = dot * (3-t) / (4-t)
            rt = self.radiusP * self.cos15 * td
            rx = self.centerX + round_away(rt*dx)
            ry = self.centerY + round_away(rt*dy)
            self.pad_obj = self.create_oval(rx-ov, ry-ov, rx+ov, ry+ov, fill=self.col_pad)

def frame_resize(event):
    # reset the grid settings for the frame
    event.widget.grid(sticky=tk.EW)
    this.stn_canvas.config(width=event.width, height=event.width)

def show_canvas():
    if this.use_canvas:
        this.stn_frame.grid()
        this.dummy.grid_remove()

def hide_canvas():
    this.stn_frame.grid_remove()
    this.dummy.grid()

def show_station(show):
    if this.curr_show != show:
        this.curr_show = show
        if show:
            show_canvas()
            show_overlay()
        else:
            hide_canvas()
            hide_overlay()

def get_overlay_prefs(parent):

    this.use_overlay = config.get_bool(PREFSNAME_USE_OVERLAY, default=False)
    if config.get_str(PREFSNAME_MS_DELAY) is not None:
        this.over_ms_delay = int(config.get_str(PREFSNAME_MS_DELAY))

    split_me = config.get_str(PREFSNAME_STN_OVERLAY)
    if split_me:
        vals = split_me.split(":")
        this.over_center_x = int(vals[0])
        this.over_center_y = int(vals[1])
        this.over_radius = int(vals[2])

    split_me = config.get_str(PREFSNAME_COL_OVERLAY)
    if split_me:
        vals = split_me.split(":")
        this.over_color_stn = vals[0]
        this.over_color_pad = vals[1]

    split_me = config.get_str(PREFSNAME_SCR_OVERLAY)
    if split_me:
        vals = split_me.split("x")
        sw = float(vals[0])
        sh = float(vals[1])
    else:
        sw = float(parent.winfo_screenwidth())
        sh = float(parent.winfo_screenheight())
    this.over_aspect_x = calc_aspect_x(sw, sh)

    this.prefs_radius = tk.IntVar(value=this.over_radius)
    this.prefs_center_x = tk.IntVar(value=this.over_center_x)
    this.prefs_center_y = tk.IntVar(value=this.over_center_y)
    this.prefs_screen_w = tk.IntVar(value=int(sw))
    this.prefs_screen_h = tk.IntVar(value=int(sh))
    this.prefs_use_over = tk.BooleanVar(value=this.use_overlay)
    this.prefs_ms_delay = tk.IntVar(value=this.over_ms_delay)

def try_overlay():
    # test for EDMC Overlay
    if this.use_overlay:
        try:
            this.overlay = Overlay()
            this.overlay.connect()
        except:
            this.overlay = None
        if not this.overlay:
            logger.warning("EDMC Overlay not available")

def plugin_start3(plugin_dir):
    logger.info(f"{__version__ = }")
    return PLUGIN_NAME

def plugin_app(parent):
    # adapt to theme
    theme = config.get_int('theme')
    this.col_stn = config.get_str('dark_highlight') if theme else "black"
    this.col_pad = "yellow" if theme else "blue"

    # which side is green
    this.backward = config.get_bool(PREFSNAME_BACKWARD, default=False)
    this.greenside = tk.StringVar(value=OPTIONS_GREENSIDE[1 if this.backward else 0])

    # maximum plugin width for EDMC window
    this.max_width = config.get_int(PREFSNAME_MAX_WIDTH)
    if this.max_width != 0:
        this.max_width = max(this.max_width, MAX_WIDTH_MINIMUM)
    this.prefs_max_width = tk.IntVar(value=this.max_width)

    frame = tk.Frame(parent)           # outer frame
    this.stn_frame = tk.Frame(frame)   # station frame
    this.dummy = tk.Frame(frame)       # dummy frame for resize

    # station canvas
    this.use_canvas = not config.get_bool(PREFSNAME_HIDE_CANVAS, default=False)
    this.prefs_hide_canvas = tk.BooleanVar(value=not this.use_canvas)
    this.stn_canvas = LandingPads(
        this.stn_frame, highlightthickness=0,
        col_stn=this.col_stn, col_pad=this.col_pad, backward=this.backward,
    )
    this.stn_canvas.grid()

    # don't show the station
    show_station(False)

    # keep the station size in sync
    frame.bind("<Configure>", frame_resize)

    try_overlay()
    get_overlay_prefs(parent)

    logger.debug(f"{this = !s}")

    return frame

def plugin_prefs(parent, cmdr, is_beta):
    # EDMC defaults
    PADX, PADY = 5, 2

    frame = nb.Frame(parent)
    frame.columnconfigure(2, weight=1)

    HyperlinkLabel(
        frame, text=PLUGIN_NAME,
        background=nb.Label().cget('background'),
        url=PLUGIN_URL, underline=True
    ).grid(row=1, columnspan=2, padx=2*PADX, sticky=tk.W)
    nb.Label(frame, text=f'Version {__version__}').grid(row=1, column=2, padx=PADX, sticky=tk.E)

    nb.Label(frame, text='Greenside').grid(row=10, padx=2*PADX, pady=(PADX, 0), sticky=tk.W)
    nb.OptionMenu(frame, this.greenside, this.greenside.get(), *OPTIONS_GREENSIDE).grid(row=10, column=1, columnspan=2, padx=PADX, sticky=tk.W)

    nb.Label(frame, text='max. Width').grid(row=11, padx=2*PADX, pady=(PADX, 0), sticky=tk.W)
    nb.EntryMenu(frame, textvariable=this.prefs_max_width).grid(row=11, column=1, columnspan=2, padx=PADX, pady=PADY, sticky=tk.W)

    nb.Checkbutton(frame, text='Hide station canvas', variable=this.prefs_hide_canvas).grid(row=12, column=1, columnspan=2, padx=PADX, pady=PADY, sticky=tk.W)

    nb.Label(frame).grid(sticky=tk.W)
    nb.Label(frame, text='Overlay').grid(row=15, padx=2*PADX, pady=(PADX, 0), sticky=tk.W)
    nb.Checkbutton(frame, text='Use overlay if available', variable=this.prefs_use_over).grid(row=15, column=2, padx=PADX, sticky=tk.W)
    ttk.Separator(frame, orient=tk.HORIZONTAL).grid(columnspan=3, padx=PADX, pady=PADY, sticky=tk.EW)

    nb.Label(frame, text='Station').grid(row=20, padx=2*PADX, sticky=tk.W)
    nb.Label(frame, text='Radius').grid(row=20, column=1, padx=PADX, sticky=tk.E)
    nb.EntryMenu(frame, textvariable=this.prefs_radius).grid(row=20, column=2, padx=PADX, pady=PADY, sticky=tk.EW)

    nb.Label(frame, text='Center coordinates').grid(row=21, padx=2*PADX, sticky=tk.W)
    nb.Label(frame, text='X').grid(row=21, column=1, padx=PADX, sticky=tk.E)
    nb.EntryMenu(frame, textvariable=this.prefs_center_x).grid(row=21, column=2, padx=PADX, pady=PADY, sticky=tk.EW)
    nb.Label(frame, text='Y').grid(row=22, column=1, padx=PADX, sticky=tk.E)
    nb.EntryMenu(frame, textvariable=this.prefs_center_y).grid(row=22, column=2, padx=PADX, pady=PADY, sticky=tk.EW)

    nb.Label(frame, text='Screen').grid(row=23, padx=2*PADX, sticky=tk.W)
    nb.Label(frame, text='Width').grid(row=23, column=1, padx=PADX, sticky=tk.E)
    nb.EntryMenu(frame, textvariable=this.prefs_screen_w).grid(row=23, column=2, padx=PADX, pady=PADY, sticky=tk.EW)
    nb.Label(frame, text='Height').grid(row=24, column=1, padx=PADX, sticky=tk.E)
    nb.EntryMenu(frame, textvariable=this.prefs_screen_h).grid(row=24, column=2, padx=PADX, pady=PADY, sticky=tk.EW)

    nb.Label(frame, text='Drawing delay').grid(row=31, padx=2*PADX, sticky=tk.W)
    nb.Label(frame, text='msec').grid(row=31, column=1, padx=PADX, sticky=tk.E)
    nb.EntryMenu(frame, textvariable=this.prefs_ms_delay).grid(row=31, column=2, padx=PADX, pady=PADY, sticky=tk.EW)

    return frame

def prefs_changed(cmdr, is_beta):
    # adapt to theme
    theme = config.get_int('theme')
    this.col_stn = config.get_str('dark_highlight') if theme else "black"
    this.col_pad = "yellow" if theme else "blue"

    if this.greenside.get() == OPTIONS_GREENSIDE[1]:
        this.backward = True
    else:
        this.backward = False
    config.set(PREFSNAME_BACKWARD, this.backward)

    this.max_width = this.prefs_max_width.get()
    if this.max_width != 0:
        if this.max_width < 0:
            this.max_width = this.stn_frame.master.winfo_width()
        else:
            this.max_width = max(this.max_width, MAX_WIDTH_MINIMUM)
        this.prefs_max_width.set(this.max_width)
    config.set(PREFSNAME_MAX_WIDTH, this.max_width)

    this.use_canvas = not this.prefs_hide_canvas.get()
    config.set(PREFSNAME_HIDE_CANVAS, not this.use_canvas)

    this.use_overlay = this.prefs_use_over.get()
    config.set(PREFSNAME_USE_OVERLAY, this.use_overlay)

    this.over_radius = this.prefs_radius.get()
    this.over_center_x = this.prefs_center_x.get()
    this.over_center_y = this.prefs_center_y.get()
    stn_prefs = "%d:%d:%d" % (this.over_center_x, this.over_center_y, this.over_radius)
    config.set(PREFSNAME_STN_OVERLAY, stn_prefs)

    sw = this.prefs_screen_w.get()
    sh = this.prefs_screen_h.get()
    scr_prefs = "%dx%d" % (sw, sh)
    config.set(PREFSNAME_SCR_OVERLAY, scr_prefs)
    this.over_aspect_x = calc_aspect_x(float(sw), float(sh))

    this.over_ms_delay = this.prefs_ms_delay.get()
    config.set(PREFSNAME_MS_DELAY, str(this.over_ms_delay))

    # update station
    width = this.stn_frame.master.winfo_width()
    if this.max_width:
        width = min(width, this.max_width)
    this.stn_canvas.config(col_stn=this.col_stn, col_pad=this.col_pad, backward=this.backward, width=width)
    if this.curr_show:
        hide_overlay()
        if this.use_overlay:
            show_overlay()
    if not this.use_overlay:
        this.overlay = None

def aspect(x):
    return round_away(this.over_aspect_x * x)

def draw_overlay_station():
    centerX = this.over_center_x
    centerY = this.over_center_y
    radiusP = this.over_radius
    # draw dodecagons
    for p, scale in enumerate(this.stn_canvas.shell_scale):
        r = radiusP * scale
        polyPoints = this.stn_canvas.get_poly_points(centerX, centerY, r)
        vectorShell = [
            {
                "x": aspect(x),
                "y": y,
            }
            for (x, y) in polyPoints + [polyPoints[0]]
        ]
        msg = {
            "id": "shell-%d" % p,
            "color": this.over_color_stn,
            "shape": "vect",
            "ttl": this.over_ttl,
            "vector": vectorShell
        }
        this.id_list.append(msg["id"])
        this.overlay.send_raw(msg, delay=this.over_ms_delay)

    # draw sector lines
    vectorFrom = this.stn_canvas.get_poly_points(centerX, centerY, radiusP * this.stn_canvas.shell_scale[0])
    vectorTo = this.stn_canvas.get_poly_points(centerX, centerY, radiusP * this.stn_canvas.shell_scale[-1])
    for l, ((x1, y1), (x2, y2)) in enumerate(zip(vectorFrom, vectorTo)):
        msg = {
            "id": "line-%d" % l,
            "color": this.over_color_stn,
            "shape": "vect",
            "ttl": this.over_ttl,
            "vector": [
                {
                    "x": aspect(x1),
                    "y": y1,
                },
                {
                    "x": aspect(x2),
                    "y": y2,
                },
            ]
        }
        this.id_list.append(msg["id"])
        this.overlay.send_raw(msg, delay=this.over_ms_delay)

def draw_overlay_toaster():
    centerX = this.over_center_x
    centerY = this.over_center_y
    radiusP = this.over_radius
    # draw toaster
    for ds in range(2):
        toaster = this.stn_canvas.get_toaster(radiusP, s=ds)
        vectorRight = [{"x": aspect(centerX+dx), "y": centerY+dy} for (dx, dy) in toaster]
        vectorLeft = [{"x": aspect(centerX-dx), "y": centerY+dy} for (dx, dy) in toaster]
        colorRight = "red" if this.backward else "green"
        colorLeft = "green" if this.backward else "red"
        for (id, color, vector) in [
            (f"toaster-right-{ds}", colorRight, vectorRight),
            (f"toaster-left-{ds}", colorLeft, vectorLeft),
        ]:
            msg = {
                "id": id,
                "color": color,
                "shape": "vect",
                "ttl": this.over_ttl,
                "vector": vector
            }
            this.id_list.append(msg["id"])
            this.overlay.send_raw(msg, delay=this.over_ms_delay)

def draw_overlay_pad(pad):
    if this.curr_show and pad:
        centerX = this.over_center_x
        centerY = this.over_center_y
        radiusP = this.over_radius
        s, t = this.stn_canvas.get_pad_coords(pad-1)
        if this.backward:
            s = (s+6) % 12
        dx, dy = this.stn_canvas.pad_sectors[s]
        rt = radiusP * (this.stn_canvas.shell_scale[t] + this.stn_canvas.shell_scale[t+1]) / 2
        rt = rt * this.stn_canvas.cos15
        rx = centerX + round_away(rt*dx)
        ry = centerY + round_away(rt*dy)
        for i, (px, py) in enumerate([(3, 9), (7, 7), (9, 3)]):
            x = rx - px // 2
            y = ry - py // 2
            msg = {
                "id": f"pad-{pad}-{i}",
                "shape": "rect",
                "color": this.over_color_pad,
                "fill": this.over_color_pad,
                "ttl": this.over_ttl,
                "x": aspect(x),
                "y": y,
                "w": aspect(px),
                "h": py,
            }
            this.id_list.append(msg["id"])
            this.overlay.send_raw(msg, delay=this.over_ms_delay)

def hide_overlay():
    for gfxID in reversed(this.id_list):
        this.overlay.send_raw({"id": gfxID, "ttl": 0}, delay=this.over_ms_delay)
    del this.id_list[:]

def show_overlay():
    if this.overlay is None:
        try_overlay()
    if this.overlay:
        draw_overlay_station()
        draw_overlay_toaster()
        draw_overlay_pad(this.stn_canvas.cur_pad)

def update_overlay():
    if this.curr_show:
        hide_overlay()
        show_overlay()

def journal_entry(cmdr, is_beta, system, station, entry, state):
    if entry['event'] == 'DockingGranted':
        typ = entry.get('StationType', 'Unknown')
        if typ.lower() in this.show_types:
            # starports only
            pad = int(entry['LandingPad'])
            this.stn_canvas.config(cur_pad=pad)
            update_overlay()
            show_station(True)
    elif entry['event'] in this.hide_events:
        show_station(False)
    elif entry['event'] == 'Music':
        if entry['MusicTrack'] == "MainMenu":
            # only way I know, if the user logged out
            show_station(False)
    elif entry["event"] == "SendText":
        if entry["Message"].startswith("!pad"):
            try:
                pad = int(entry["Message"][4:])
            except ValueError:
                pad = None
            if pad:
                this.stn_canvas.config(cur_pad=pad)
                update_overlay()
                show_station(True)
            else:
                show_station(False)
