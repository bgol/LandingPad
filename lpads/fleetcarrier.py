import tkinter as tk

from .base import LandingPads
from .misc import round_away


FLEETCARRIER_BOX_WIDTH = 34
FLEETCARRIER_BOX_HEIGHT = 54
SQUADRON_CARRIER_OFFSET = FLEETCARRIER_BOX_WIDTH / 2 + 2

class FleetCarrierPads(LandingPads):

    pad_list: list[tuple[int, int]] = []

    def __init__(
            self, parent, cur_pad=None, backward=False, col_stn="black", col_pad="blue",
            max_with=0, squadron_carrier=False, **kwargs
    ):
        super().__init__(parent, cur_pad, backward, col_stn, col_pad, max_with, **kwargs)
        self.squadron_carrier = squadron_carrier
        self.update_values()
        self.calc_unit_length()

    @property
    def unit_length(self):
        return -self._unit_length if self.backward else self._unit_length

    def calc_values(self, x_offset_list=None):
        self.pad_list.clear()
        x_offset_list = x_offset_list or [0]
        for x_offset in x_offset_list:
            # 8 large pads
            for y in (15, 1, -13, -27):
                for x in (-9, 1):
                    self.pad_list.append((x+x_offset, y, x+x_offset+8, y+12))
            # 4 medium pads
            for x in (-15, 11):
                for y in (17, 7):
                    self.pad_list.append((x+x_offset, y, x+x_offset+4, y+8))
            # 4 small pads
            y = 1
            for x in (-17, 10, 14, -13):
                self.pad_list.append((x+x_offset, y, x+x_offset+3, y+4))
        self.pad_count = len(self.pad_list)

    def update_values(self):
        if self.squadron_carrier:
            self.calc_values([SQUADRON_CARRIER_OFFSET, -SQUADRON_CARRIER_OFFSET])
        else:
            self.calc_values()

    def config(self, **kwargs):
        if "squadron_carrier" in kwargs:
            self.squadron_carrier = kwargs.pop("squadron_carrier")
            self.update_values()
            self.calc_unit_length()
        super().config(**kwargs)

    def calc_unit_length(self):
        if self.squadron_carrier:
            ux = int(self.width / (2 * SQUADRON_CARRIER_OFFSET + FLEETCARRIER_BOX_WIDTH))
        else:
            ux = int(self.width / FLEETCARRIER_BOX_WIDTH)
        uy = int(self.height / FLEETCARRIER_BOX_HEIGHT)
        self._unit_length = max(min(ux, uy), 1)

    def on_resize(self, event):
        # resize the canvas
        self.width = self.height = event.width
        self.calc_unit_length()
        self.config(width=self.width, height=self.height)

    def get_pad_boxes(self, cx, cy):
        return [
            (
                cx + x1 * self.unit_length,
                cy + y1 * self.unit_length,
                cx + x2 * self.unit_length,
                cy + y2 * self.unit_length,
            )
            for (x1, y1, x2, y2) in self.pad_list
        ]

    def draw_station(self):
        # redraw
        self.delete("all")
        self.pad_obj = None
        self.stn_obj = False
        self.center_x = center_x = round_away(self.width / 2)
        self.center_y = center_y = round_away(self.height / 2)
        testval = abs(self.unit_length)
        strong = 4 - (testval < 16) - (testval < 9) - (testval < 4)
        for x1, y1, x2, y2 in self.get_pad_boxes(center_x, center_y):
            self.create_rectangle(x1, y1, x2, y2, width=strong, outline=self.col_stn, fill='')
        self.stn_obj = True

    def get_pad_center(self, pad):
        x1, y1, x2, y2 = self.pad_list[pad % self.pad_count]
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        return (cx, cy)

    def draw_pad(self, pad):
        if self.pad_obj:
            self.delete(self.pad_obj)
            self.pad_obj = None
        if not self.stn_obj:
            self.draw_station()
        self.cur_pad = pad
        if pad:
            cx, cy = self.get_pad_center(pad-1)
            dot = 2 if ((pad-1) % 16) < 8 else 1
            ov = dot * self.unit_length
            rx = self.center_x + round_away(cx * self.unit_length)
            ry = self.center_y + round_away(cy * self.unit_length)
            self.pad_obj = self.create_oval(rx-ov, ry-ov, rx+ov, ry+ov, fill=self.col_pad)
