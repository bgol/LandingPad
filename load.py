# -*- coding: utf-8 -*-
#
# Display the "LandigPad" position for Starports.
#

import sys
import math
import Tkinter as tk

from config import config

VERSION = '0.1'

this = sys.modules[__name__]	# For holding module globals
this.stn_frame = None
this.stn_canvas = None
this.curr_show = None
this.col_stn = "black"
this.col_pad = "blue"
this.hide_events = ('Docked', 'DockingCancelled', 'DockingTimeout', 'StartJump', 'Shutdown')
this.show_types = ('bernal', 'coriolis', 'orbis')

def round_away(val):
    val += -0.5 if val < 0 else 0.5
    return int(val)

class LandingPads(tk.Canvas):

    pad_map = {
          1:  (0,0),  2:  (0,0), 3: (0,2), 4: (0,2),
          5:  (1,0),  6:  (1,0), 7: (1,1), 8: (1,2),
          9:  (2,0), 10:  (2,2),
         11:  (3,0), 12:  (3,0), 13: (3,1), 14: (3,2), 15: (3,2),
         16:  (4,0), 17:  (4,0), 18: (4,2), 19: (4,2),
         20:  (5,0), 21:  (5,0), 22: (5,1), 23: (5,2),
         24:  (6,0), 25:  (6,2),
         26:  (7,0), 27:  (7,0), 28: (7,1), 29: (7,2), 30: (7,2),
         31:  (8,0), 32:  (8,0), 33: (8,2), 34: (8,2),
         35:  (9,0), 36:  (9,0), 37: (9,1), 38: (9,2),
         39: (10,0), 40: (10,2),
         41: (11,0), 42: (11,0), 43: (11,1), 44: (11,2), 45: (11,2),
    }
    shell_scale = (1, 0.70, 0.5, 0.25)

    def __init__(self, parent, cur_pad=None, col_stn="black", col_pad="blue", **kwargs):
        tk.Canvas.__init__(self, parent, **kwargs)
        self.bind("<Configure>", self.on_resize)
        self.width = self.winfo_reqwidth()
        self.height = self.winfo_reqheight()
        self.cur_pad = cur_pad
        self.col_pad = col_pad
        self.col_stn = col_stn
        self.pad_obj = None
        self.stn_obj = False
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
        tk.Canvas.config(self, **kwargs)
        self.draw_station()
        self.draw_pad(self.cur_pad)

    def on_resize(self, event):
        # resize the canvas
        self.width = self.height = event.width
        self.config(width=self.width, height=self.height)

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
            polyPoints = []
            for (dx, dy) in self.dodecagon:
                dx = r * dx
                dy = r * dy
                x = centerX + round_away(dx)
                y = centerY + round_away(dy)
                polyPoints.append((x, y))

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

        dx = round_away(radiusP * 0.75)
        dy = round_away(radiusP * self.shell_scale[-1])
        dr = round_away(dy * 0.08)
        toaster = [
            (+0,          -dy),
            (+dx-dr,      -dy),
            (+dx+dr,      -dy+2*dr),
            (+radiusP-dr, -dy+2*dr),
            (+radiusP,    -dy+3*dr),
            (+radiusP,    +dy-3*dr),
            (+radiusP-dr, +dy-2*dr),
            (+dx+dr,      +dy-2*dr),
            (+dx-dr,      +dy),
            (+0,          +dy),
        ]
        self.create_line(*[(centerX+dx, centerY+dy) for (dx, dy) in toaster],width=2*strong,fill="green",capstyle=tk.BUTT, joinstyle=tk.ROUND)
        self.create_line(*[(centerX-dx, centerY+dy) for (dx, dy) in toaster],width=2*strong,fill="red",capstyle=tk.BUTT, joinstyle=tk.ROUND)
        self.stn_obj = True

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
                s, t = self.pad_map.get(pad, (0,0))
            dx, dy = self.pad_sectors[s]
            dot = self.radiusP * (self.shell_scale[0] - self.shell_scale[1]) / 4
            td = (self.shell_scale[t] + self.shell_scale[t+1]) / 2
            ov = dot * (3-t) / (4-t)
            rt = self.radiusP * self.cos15 * td
            rx = self.centerX + int(rt*dx)
            ry = self.centerY + int(rt*dy)
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
        else:
            this.stn_frame.grid_remove()
            this.dummy.grid()

def plugin_start():
    # nothing to do
    return 'LandingPad'

def plugin_app(parent):
    # adapt to theme
    theme = config.getint('theme')
    this.col_stn = config.get('dark_highlight') if theme else "black"
    this.col_pad = "yellow" if theme else "blue"

    frame = tk.Frame(parent)           # outer frame
    this.stn_frame = tk.Frame(frame)   # station frame
    this.dummy = tk.Frame(frame)       # dummy frame for resize

    # station canvas
    this.stn_canvas = LandingPads(
        this.stn_frame, highlightthickness=0,
        col_stn=this.col_stn, col_pad=this.col_pad,
    )
    this.stn_canvas.grid()

    # don't show the station
    show_station(False)

    # keep the station size in sync
    frame.bind("<Configure>", frame_resize)

    return frame

def prefs_changed(cmdr, is_beta):
    # adapt to theme
    theme = config.getint('theme')
    this.col_stn = config.get('dark_highlight') if theme else "black"
    this.col_pad = "yellow" if theme else "blue"

    # update station
    this.stn_canvas.config(col_stn=this.col_stn, col_pad=this.col_pad)

def journal_entry(cmdr, is_beta, system, station, entry, state):
    if entry['event'] == 'DockingGranted':
        typ = entry.get('StationType', 'Unknown')
        if typ.lower() in this.show_types:
            # starports only
            pad = int(entry['LandingPad'])
            this.stn_canvas.config(cur_pad=pad)
            show_station(True)
    elif entry['event'] in this.hide_events:
        show_station(False)
    elif entry['event'] == 'Music':
        if entry['MusicTrack'] == "MainMenu":
            # only way I know, if the user logged out
            show_station(False)
