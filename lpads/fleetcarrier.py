from enum import Enum

from .base import LandingPads
from .misc import round_away


FLEETCARRIER_BOX_WIDTH = 48
FLEETCARRIER_BOX_HEIGHT = 76
SQUADRON_CARRIER_OFFSET = FLEETCARRIER_BOX_WIDTH / 2 + 2


class CarrierType(Enum):
    FleetCarrier = 1
    SquadronCarrier = 2
    ColonisationShip = 3

class FleetCarrierPads(LandingPads):

    pad_list: list[tuple[int, int]] = []

    def __init__(
            self, parent, cur_pad=None, backward=False, col_stn="black", col_pad="blue",
            max_with=0, carrier_type=CarrierType.FleetCarrier, **kwargs
    ):
        self.strong = 1
        self.carrier_type = carrier_type
        super().__init__(parent, cur_pad, backward, col_stn, col_pad, max_with, **kwargs)
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
            for y in (22, 2, -18, -38):
                for x in (-12, 2):
                    self.pad_list.append((x+x_offset, y, x+x_offset+10, y+16))
            # 4 medium pads
            for x in (-22, 15):
                for y in (25, 10):
                    self.pad_list.append((x+x_offset, y, x+x_offset+7, y+11))
            # 4 small pads
            y = 0
            if self.carrier_type == CarrierType.FleetCarrier:
                small_pads_list = (-24, 14, 20, -18)
            else:
                small_pads_list = (-24, -18, 14, 20)
            for x in small_pads_list:
                self.pad_list.append((x+x_offset, y, x+x_offset+4, y+6))
        self.pad_count = len(self.pad_list)

    def update_values(self):
        if self.carrier_type == CarrierType.SquadronCarrier:
            self.calc_values([SQUADRON_CARRIER_OFFSET, -SQUADRON_CARRIER_OFFSET])
        else:
            self.calc_values()

    def config(self, **kwargs):
        if "carrier_type" in kwargs:
            self.carrier_type = kwargs.pop("carrier_type")
            self.update_values()
            self.calc_unit_length()
        super().config(**kwargs)

    def calc_unit_length(self):
        if self.carrier_type == CarrierType.SquadronCarrier:
            ux = ((self.width - 4) / (2 * SQUADRON_CARRIER_OFFSET + FLEETCARRIER_BOX_WIDTH))
        else:
            ux = ((self.width - 4) / FLEETCARRIER_BOX_WIDTH)
        uy = ((self.height - 4) / FLEETCARRIER_BOX_HEIGHT)
        self._unit_length = max(min(ux, uy), 1)

    def on_resize(self, event):
        # resize the canvas
        self.width = self.height = event.width
        self.calc_unit_length()
        self.config(width=self.width, height=self.height)

    def get_pad_boxes(self):
        return [
            (
                self.center_x + x1 * self.unit_length,
                self.center_y + y1 * self.unit_length,
                self.center_x + x2 * self.unit_length,
                self.center_y + y2 * self.unit_length,
            )
            for (x1, y1, x2, y2) in self.pad_list
        ]

    def draw_station(self):
        # redraw
        self.delete("all")
        self.pad_obj = None
        self.stn_obj = False
        self.center_x = self.width / 2
        self.center_y = self.height / 2
        testval = abs(self.unit_length)
        self.strong = 4 - (testval < 16) - (testval < 9) - (testval < 4)
        for x1, y1, x2, y2 in self.get_pad_boxes():
            self.create_rectangle(x1, y1, x2, y2, width=self.strong, outline=self.col_stn, fill='')
        self.stn_obj = True

    def get_pad_rectangle(self, pad):
        x1, y1, x2, y2 = self.pad_list[pad % self.pad_count]
        return (
            self.center_x + x1 * self.unit_length,
            self.center_y + y1 * self.unit_length,
            self.center_x + x2 * self.unit_length,
            self.center_y + y2 * self.unit_length
        )

    def draw_pad(self, pad):
        if self.pad_obj:
            self.delete(self.pad_obj)
            self.pad_obj = None
        if not self.stn_obj:
            self.draw_station()
        self.cur_pad = pad
        if pad:
            x1, y1, x2, y2 = self.get_pad_rectangle(pad-1)
            self.pad_obj = self.create_rectangle(x1, y1, x2, y2, width=self.strong, outline=self.col_stn, fill=self.col_pad)

class FleetCarrierPadsOverlay():

    id_list_pad: list = []
    id_list_station: list = []
    config_attr_set = {
        "overlay", "backward", "radius", "center_x", "center_y", "ms_delay",
        "color_stn", "color_pad", "ttl", "cur_pad", "fleetcarrier_canvas", "carrier_type",
    }

    def __init__(
            self, overlay, backward, radius, center_x, center_y, screen_w, screen_h,
            ms_delay, color_stn, color_pad, ttl, cur_pad, fleetcarrier_canvas,
            carrier_type=CarrierType.FleetCarrier,
    ):
        self.overlay = overlay
        self.backward = backward
        self.radius = radius
        self.center_x = center_x
        self.center_y = center_y
        if self.overlay is not None:
            self.overlay.config(screen_w, screen_h)
            self.aspect_x = self.overlay.calc_aspect_x(screen_w, screen_h)
            self.max_x, self.max_y = self.overlay.calc_max_xy(self.aspect_x)
        else:
            self.aspect_x = 1.0
            self.max_x = screen_w
            self.max_y = screen_h
        self.ms_delay = ms_delay
        self.color_stn = color_stn
        self.color_pad = color_pad
        self.ttl = ttl
        self.cur_pad = cur_pad
        self.fleetcarrier_canvas = fleetcarrier_canvas
        self.carrier_type = carrier_type
        self.id_prefix = f"LandingPad-{carrier_type.name}-"
        self.show = False
        self.calc_unit_length()

    def aspect(self, x):
        return round_away(self.aspect_x * x)

    @property
    def unit_length(self):
        return -self._unit_length if self.backward else self._unit_length

    @property
    def diameter(self):
        return self.radius * 2

    def calc_unit_length(self):
        if self.carrier_type == CarrierType.SquadronCarrier:
            ux = self.diameter / (2 * SQUADRON_CARRIER_OFFSET + FLEETCARRIER_BOX_WIDTH)
        else:
            ux = self.diameter / FLEETCARRIER_BOX_WIDTH
        uy = self.diameter / FLEETCARRIER_BOX_HEIGHT
        self._unit_length = max(min(ux, uy), 1)

    def config(self, **kwargs):
        for attr_name in (self.config_attr_set & kwargs.keys()):
            setattr(self, attr_name, kwargs[attr_name])
            if attr_name == "carrier_type":
                self.id_prefix = f"LandingPad-{self.carrier_type.name}-"

        if all(val in kwargs for val in ("screen_w", "screen_h")):
            if self.overlay is not None:
                self.overlay.config(kwargs["screen_w"], kwargs["screen_h"])
                self.aspect_x = self.overlay.calc_aspect_x(kwargs["screen_w"], kwargs["screen_h"])
                self.max_x, self.max_y = self.overlay.calc_max_xy(self.aspect_x)
            else:
                self.aspect_x = 1.0
                self.max_x = kwargs["screen_w"]
                self.max_y = kwargs["screen_h"]

        if any(val in kwargs for val in ("radius", "carrier_type")):
            self.calc_unit_length()

        if self.show:
            if len(kwargs) == 1 and "cur_pad" in kwargs:
                # redraw pad only
                self.draw_overlay_pad(self.cur_pad)
            else:
                # redraw station with a very small delay
                old_ms_delay = self.ms_delay
                self.ms_delay = min(old_ms_delay, 5)
                self.hide_overlay()
                self.show_overlay()
                self.ms_delay = old_ms_delay

    def check_station_box(self):
        min_x = max_x = self.center_x
        min_y = max_y = self.center_y
        for x1, y1, x2, y2 in self.fleetcarrier_canvas.pad_list:
            for check_x in (round_away(self.center_x + x * self.unit_length) for x in (x1, x2)):
                min_x = min(min_x, check_x)
                max_x = max(max_x, check_x)
            for check_y in (round_away(self.center_y + y * self.unit_length) for y in (y1, y2)):
                min_y = min(min_y, check_y)
                max_y = max(max_y, check_y)
        if min_x < 0:
            self.center_x -= min_x
            max_x -= min_x
        if min_y < 0:
            self.center_y -= min_y
            max_y -= min_y
        if max_x > self.max_x:
            self.center_x -= (max_x - self.max_x)
        if max_y > self.max_y:
            self.center_y -= (max_y - self.max_y)

    def convert_coords_to_rect(self, x1, y1, x2, y2):
        x1 = self.aspect(self.center_x + x1 * self.unit_length)
        y1 = round_away(self.center_y + y1 * self.unit_length)
        x2 = self.aspect(self.center_x + x2 * self.unit_length)
        y2 = round_away(self.center_y + y2 * self.unit_length)
        return min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1)

    def draw_overlay_station(self):
        if not self.overlay:
            return
        self.check_station_box()
        for i, (x1, y1, x2, y2) in enumerate(self.fleetcarrier_canvas.pad_list):
            x, y, w, h = self.convert_coords_to_rect(x1, y1, x2, y2)
            msg = {
                "id": f"{self.id_prefix}station-{i}",
                "shape": "rect",
                "color": self.color_stn,
                "ttl": self.ttl,
                "x": x, "y": y,
                "w": w, "h": h,
            }
            self.id_list_station.append(msg["id"])
            self.overlay.send_raw(msg, delay=self.ms_delay)

    def draw_overlay_pad(self, pad):
        if len(self.id_list_pad) > 0:
            for gfx_id in reversed(self.id_list_pad):
                self.overlay.send_raw({"id": gfx_id, "ttl": 0}, delay=self.ms_delay)
            del self.id_list_pad[:]
        self.cur_pad = pad
        if not self.cur_pad:
            return

        pad_index = (pad - 1) % self.fleetcarrier_canvas.pad_count
        x1, y1, x2, y2 = self.fleetcarrier_canvas.pad_list[pad_index]
        x, y, w, h = self.convert_coords_to_rect(x1, y1, x2, y2)
        msg = {
            "id": f"{self.id_prefix}pad-{pad}",
            "shape": "rect",
            "color": self.color_pad,
            "fill": self.color_pad,
            "ttl": self.ttl,
            "x": x, "y": y,
            "w": w, "h": h,
        }
        self.id_list_pad.append(msg["id"])
        self.overlay.send_raw(msg, delay=self.ms_delay)

    def hide_overlay(self):
        if self.show and self.overlay:
            for del_list in (self.id_list_pad, self.id_list_station):
                for gfx_id in reversed(del_list):
                    self.overlay.send_raw({"id": gfx_id, "ttl": 0}, delay=self.ms_delay)
                del del_list[:]
            self.show = False

    def show_overlay(self):
        if self.overlay:
            self.draw_overlay_station()
            self.draw_overlay_pad(self.cur_pad)
            self.show = True
