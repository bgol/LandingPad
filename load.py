# -*- coding: utf-8 -*-
#
# Display the "LandigPad" position for Starports.
#

import sys
import math
import json
import time
import socket
import Tkinter as tk
import ttk

import myNotebook as nb
from ttkHyperlinkLabel import HyperlinkLabel
from config import config

VERSION = '0.4'

PREFSNAME_BACKWARD = "landingpad_backward"
OPTIONS_GREENSIDE = [_("right"), _("left")]

this = sys.modules[__name__]	# For holding module globals
this.stn_frame = None
this.stn_canvas = None
this.curr_show = None
this.backward = False
this.col_stn = "black"
this.col_pad = "blue"
this.hide_events = ('Docked', 'DockingCancelled', 'DockingTimeout', 'StartJump', 'Shutdown')
this.show_types = ('bernal', 'coriolis', 'orbis', 'asteroidbase')

# EDMC Overlay settings
SERVER_ADDRESS = "127.0.0.1"
SERVER_PORT = 5010
this.overlay = None
this.use_overlay = False
this.over_radius = 100
this.over_center_x = 100
this.over_center_y = 490
this.over_aspect_x = 1
this.over_color_stn = "#ffffff"
this.over_color_pad = "yellow"
this.over_ttl = 10*60
this.id_list = []

PREFSNAME_STN_OVERLAY = "landingpad_stn_overlay"
PREFSNAME_COL_OVERLAY = "landingpad_col_overlay"
PREFSNAME_SCR_OVERLAY = "landingpad_scr_overlay"
PREFSNAME_USE_OVERLAY = "landingpad_use_overlay"

def round_away(val):
    val += -0.5 if val < 0 else 0.5
    return int(val)

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
                print "LandingPad: error in Overlay.connect: {}".format(err)
                self.conn = None

    def send_raw(self, msg):
        """
        Encode a dict and send it to the server
        :param msg:
        :return:
        """
        if self.conn:
            try:
                self.conn.send(json.dumps(msg))
                self.conn.send("\n")
                time.sleep(0.1)
            except Exception as err:
                print "LandingPad: error in Overlay.send_raw: {}".format(err)
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
        self.height = self.winfo_reqheight()
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
        tk.Canvas.config(self, **kwargs)
        self.draw_station()
        self.draw_pad(self.cur_pad)

    def on_resize(self, event):
        # resize the canvas
        self.width = self.height = event.width
        self.config(width=self.width, height=self.height)

    def get_poly_points(self, cx, cy, r):
        polyPoints = []
        for (dx, dy) in self.dodecagon:
            x = cx + round_away(dx*r)
            y = cy + round_away(dy*r)
            polyPoints.append((x, y))
        return polyPoints

    def get_toaster(self, r):
        dx = round_away(r * 0.75)
        dy = round_away(r * self.shell_scale[-1])
        dr = round_away(dy * 0.08)
        toaster = [
            (+0,     -dy),
            (+dx-dr, -dy),
            (+dx+dr, -dy+2*dr),
            (+r-dr,  -dy+2*dr),
            (+r,     -dy+3*dr),
            (+r,     +dy-3*dr),
            (+r-dr,  +dy-2*dr),
            (+dx+dr, +dy-2*dr),
            (+dx-dr, +dy),
            (+0,     +dy),
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
        for p in range(lenScale):
            r = radiusP * self.shell_scale[p]
            polyPoints = self.get_poly_points(centerX, centerY, r)
            if 0 < p < lenScale-1:
                lw = max(1, strong-1)
            else:
                lw = strong
            self.create_polygon(*polyPoints, width=lw, outline=self.col_stn, fill='', joinstyle=tk.ROUND)
            shellList.append(polyPoints)

        for i in range(len(self.dodecagon)):
            x1, y1 = shellList[0][i]
            x2, y2 = shellList[-1][i]
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

def show_station(show):
    if this.curr_show != show:
        this.curr_show = show
        if show:
            this.stn_frame.grid()
            this.dummy.grid_remove()
            show_overlay()
        else:
            this.stn_frame.grid_remove()
            this.dummy.grid()
            hide_overlay()

def get_overlay_prefs(parent):

    this.use_overlay = config.getint(PREFSNAME_USE_OVERLAY)

    split_me = config.get(PREFSNAME_STN_OVERLAY)
    if split_me:
        vals = split_me.split(":")
        this.over_center_x = int(vals[0])
        this.over_center_y = int(vals[1])
        this.over_radius = int(vals[2])

    split_me = config.get(PREFSNAME_COL_OVERLAY)
    if split_me:
        vals = split_me.split(":")
        this.over_color_stn = vals[0]
        this.over_color_pad = vals[1]

    split_me = config.get(PREFSNAME_SCR_OVERLAY)
    if split_me:
        vals = split_me.split("x")
        sw = float(vals[0])
        sh = float(vals[1])
    else:
        sw = float(parent.winfo_screenwidth())
        sh = float(parent.winfo_screenheight())
    this.over_aspect_x = 1350.0 / 1060.0 * sh / sw

    this.prefs_radius = tk.IntVar(value=this.over_radius)
    this.prefs_center_x = tk.IntVar(value=this.over_center_x)
    this.prefs_center_y = tk.IntVar(value=this.over_center_y)
    this.prefs_screen_w = tk.IntVar(value=int(sw))
    this.prefs_screen_h = tk.IntVar(value=int(sh))
    this.prefs_use_over = tk.IntVar(value=this.use_overlay)

def try_overlay():
    # test for EDMC Overlay
    if this.use_overlay:
        try:
            this.overlay = Overlay()
            this.overlay.connect()
        except:
            this.overlay = None
        if not this.overlay:
            print "LandingPad: overlay not available"

def plugin_start():
    # nothing to do
    return 'LandingPad'

def plugin_app(parent):
    # adapt to theme
    theme = config.getint('theme')
    this.col_stn = config.get('dark_highlight') if theme else "black"
    this.col_pad = "yellow" if theme else "blue"

    # which side is green
    this.backward = config.getint(PREFSNAME_BACKWARD)
    this.greenside = tk.StringVar(value=OPTIONS_GREENSIDE[this.backward])

    frame = tk.Frame(parent)           # outer frame
    this.stn_frame = tk.Frame(frame)   # station frame
    this.dummy = tk.Frame(frame)       # dummy frame for resize

    # station canvas
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

    return frame

def plugin_prefs(parent, cmdr, is_beta):
    # EDMC defaults
    PADX, PADY = 5, 2

    frame = nb.Frame(parent)
    frame.columnconfigure(2, weight=1)

    HyperlinkLabel(frame, text='LandingPad', background=nb.Label().cget('background'), url='https://github.com/bgol/LandingPad', underline=True).grid(row=1, columnspan=2, padx=2*PADX, sticky=tk.W)
    nb.Label(frame, text = 'Version %s' % VERSION).grid(row=1, column=2, padx=PADX, sticky=tk.E)

    nb.Label(frame, text=_('Greenside')).grid(row=10, padx=2*PADX, pady=(PADX, 0), sticky=tk.W)
    nb.OptionMenu(frame, this.greenside, this.greenside.get(), *OPTIONS_GREENSIDE).grid(row=10, column=1, columnspan=2, padx=PADX, sticky=tk.W)

    nb.Label(frame).grid(sticky=tk.W)
    nb.Label(frame, text=_('Overlay')).grid(row=15, padx=2*PADX, pady=(PADX, 0), sticky=tk.W)
    nb.Checkbutton(frame, text=_('Use overlay if available'), variable=this.prefs_use_over).grid(row=15, column=2, padx=PADX, sticky=tk.W)
    ttk.Separator(frame, orient=tk.HORIZONTAL).grid(columnspan=3, padx=PADX, pady=PADY, sticky=tk.EW)

    nb.Label(frame, text=_('Station')).grid(row=20, padx=2*PADX, sticky=tk.W)
    nb.Label(frame, text=_('Radius')).grid(row=20, column=1, padx=PADX, sticky=tk.E)
    nb.Entry(frame, textvariable=this.prefs_radius).grid(row=20, column=2, padx=PADX, pady=PADY, sticky=tk.EW)

    nb.Label(frame, text=_('Center coordinates')).grid(row=21, padx=2*PADX, sticky=tk.W)
    nb.Label(frame, text=_('X')).grid(row=21, column=1, padx=PADX, sticky=tk.E)
    nb.Entry(frame, textvariable=this.prefs_center_x).grid(row=21, column=2, padx=PADX, pady=PADY, sticky=tk.EW)
    nb.Label(frame, text=_('Y')).grid(row=22, column=1, padx=PADX, sticky=tk.E)
    nb.Entry(frame, textvariable=this.prefs_center_y).grid(row=22, column=2, padx=PADX, pady=PADY, sticky=tk.EW)

    nb.Label(frame, text=_('Screen')).grid(row=23, padx=2*PADX, sticky=tk.W)
    nb.Label(frame, text=_('Width')).grid(row=23, column=1, padx=PADX, sticky=tk.E)
    nb.Entry(frame, textvariable=this.prefs_screen_w).grid(row=23, column=2, padx=PADX, pady=PADY, sticky=tk.EW)
    nb.Label(frame, text=_('Height')).grid(row=24, column=1, padx=PADX, sticky=tk.E)
    nb.Entry(frame, textvariable=this.prefs_screen_h).grid(row=24, column=2, padx=PADX, pady=PADY, sticky=tk.EW)

    return frame

def prefs_changed(cmdr, is_beta):
    # adapt to theme
    theme = config.getint('theme')
    this.col_stn = config.get('dark_highlight') if theme else "black"
    this.col_pad = "yellow" if theme else "blue"

    if this.greenside.get() == OPTIONS_GREENSIDE[1]:
        this.backward = True
    else:
        this.backward = False
    config.set(PREFSNAME_BACKWARD, this.backward)

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
    this.over_aspect_x = 1350.0 / 1060.0 * float(sh) / float(sw)

    # update station
    this.stn_canvas.config(col_stn=this.col_stn, col_pad=this.col_pad, backward=this.backward)
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
    for p in range(len(this.stn_canvas.shell_scale)):
        vectorShell = []
        r = radiusP * this.stn_canvas.shell_scale[p]
        polyPoints = this.stn_canvas.get_poly_points(centerX, centerY, r)
        for (x, y) in polyPoints:
            vectorShell.append({
                "x": aspect(x),
                "y": y,
            })
        vectorShell.append({
            "x": aspect(polyPoints[0][0]),
            "y": polyPoints[0][1],
        })
        msg = {
            "id": "shell-%d" % p,
            "color": this.over_color_stn,
            "shape": "vect",
            "ttl": this.over_ttl,
            "vector": vectorShell
        }
        this.id_list.append(msg["id"])
        this.overlay.send_raw(msg)

    # draw sector lines
    vectorFrom = this.stn_canvas.get_poly_points(centerX, centerY, radiusP * this.stn_canvas.shell_scale[0])
    vectorTo = this.stn_canvas.get_poly_points(centerX, centerY, radiusP * this.stn_canvas.shell_scale[-1])
    for l in range(len(vectorFrom)):
        msg = {
            "id": "line-%d" % l,
            "color": this.over_color_stn,
            "shape": "vect",
            "ttl": this.over_ttl,
            "vector": [
                {
                    "x": aspect(vectorFrom[l][0]),
                    "y": vectorFrom[l][1],
                },
                {
                    "x": aspect(vectorTo[l][0]),
                    "y": vectorTo[l][1],
                },
            ]
        }
        this.id_list.append(msg["id"])
        this.overlay.send_raw(msg)

def draw_overlay_toaster():
    centerX = this.over_center_x
    centerY = this.over_center_y
    radiusP = this.over_radius
    # draw toaster
    toaster = this.stn_canvas.get_toaster(radiusP)
    vectorRight = [{"x": aspect(centerX+dx), "y": centerY+dy} for (dx, dy) in toaster]
    vectorLeft = [{"x": aspect(centerX-dx), "y": centerY+dy} for (dx, dy) in toaster]
    colorRight = "red" if this.backward else "green"
    colorLeft = "green" if this.backward else "red"
    for (id, color, vector) in [
        ("toaster-right", colorRight, vectorRight),
        ("toaster-left", colorLeft, vectorLeft),
    ]:
        msg = {
            "id": id,
            "color": color,
            "shape": "vect",
            "ttl": this.over_ttl,
            "vector": vector
        }
        this.id_list.append(msg["id"])
        this.overlay.send_raw(msg)

def draw_overlay_pad(pad):
    if this.curr_show and pad:
        centerX = this.over_center_x
        centerY = this.over_center_y
        radiusP = this.over_radius
        s, t = this.stn_canvas.get_pad_coords(pad-1)
        if this.backward:
            s = (s+6) % 12
        dx, dy = this.stn_canvas.pad_sectors[s]
        rd = radiusP * 0.08
        rt = radiusP * (this.stn_canvas.shell_scale[t] + this.stn_canvas.shell_scale[t+1]) / 2
        rt = rt * this.stn_canvas.cos15
        rx = centerX + round_away(rt*dx)
        ry = centerY + round_away(rt*dy)
        vectorPad = []
        for proz in [0.25, 0.5, 0.75]:
            polyPoints = this.stn_canvas.get_poly_points(rx, ry, rd * proz)
            for (x, y) in polyPoints:
                vectorPad.append({
                    "x": aspect(x),
                    "y": y,
                })
            vectorPad.append({
                "x": aspect(polyPoints[0][0]),
                "y": polyPoints[0][1],
            })
        msg = {
            "id": "pad",
            "shape": "vect",
            "color": this.over_color_pad,
            "ttl": this.over_ttl,
            "vector": vectorPad
        }
        this.id_list.append(msg["id"])
        this.overlay.send_raw(msg)

def hide_overlay():
    for gfxID in reversed(this.id_list):
        this.overlay.send_raw({
            "id": gfxID,
            "ttl": 0,
        })
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
