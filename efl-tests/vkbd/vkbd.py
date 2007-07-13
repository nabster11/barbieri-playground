#!/usr/bin/python

WIDTH = 800
HEIGHT = 480
FS = False
TITLE = "Virtual Keyboard"
WM_INFO = ("Virtual Keyboard", "vkbd")

import evas
import edje
import ecore
import ecore.evas

edje.init()
ecore.evas.init()
ecore.init()

def on_resize(ee):
    x, y, w, h = ee.evas.viewport
    ee.data["main"].size = w, h


def on_delete_request(ee):
    ecore.main_loop_quit()


def on_key_down(obj, event, ee):
    if event.keyname in ("F6", "f"):
        ee.fullscreen = not ee.fullscreen
    elif event.keyname == "Escape":
        ecore.main_loop_quit()


class VirtualKeyboard(edje.Edje):
    def __init__(self, canvas):
        edje.Edje.__init__(self, canvas)
        self.file_set("default.edj", "main")
        self.obj_alpha = self.part_swallow_get("alpha")
        self.is_shift_down = False
        self.is_mouse_down = False
        self._setup_events()
        self.press_shift()

    def _setup_events(self):
        self.signal_callback_add("key_down", "*", self.on_edje_signal_key_down)
        self.on_mouse_down_add(self.on_mouse_down)
        self.on_mouse_up_add(self.on_mouse_up)

    def press_shift(self):
        self.obj_alpha.signal_emit("press_shift", "")
        self.is_shift_down = True

    def release_shift(self):
        self.obj_alpha.signal_emit("release_shift", "")
        self.is_shift_down = False

    def toggle_shift(self):
        if self.is_shift_down:
            self.release_shift()
        else:
            self.press_shift()

    @staticmethod
    def on_edje_signal_key_down(self, emission, source):
        t = self.part_text_get("field") or ""
        key = source.split(":", 1)[1]
        if key == "enter":
            self.part_text_set("field", "")
            self.press_shift()
        elif key == "backspace":
            self.part_text_set("field", t[:-1])
        elif key == "shift":
            self.toggle_shift()
        elif key in (".?123", "ABC", "#+=", ".?12"):
            pass
        else:
            if self.is_shift_down:
                self.release_shift()
                key = key.upper()
            else:
                key = key.lower()
            self.part_text_set("field", t + key)

    @staticmethod
    def on_edje_signal_mouse_over_key(self, emission, source):
        print "mouse_over:", emission, source

    @staticmethod
    def on_mouse_down(self, event):
        if event.button != 1:
            return
        self.is_mouse_down = True
        print "mouse_down:", event

    @staticmethod
    def on_mouse_up(self, event):
        if event.button != 1:
            return
        self.is_mouse_down = False
        print "mouse_up:", event


if ecore.evas.engine_type_supported_get("software_x11_16"):
    ee = ecore.evas.SoftwareX11_16(w=WIDTH, h=HEIGHT)
else:
    ee = ecore.evas.SoftwareX11(w=WIDTH, h=HEIGHT)

canvas = ee.evas
o = VirtualKeyboard(canvas)
o.size = canvas.size
o.focus = True
o.show()
o.on_key_down_add(on_key_down, ee)

o.signal_callback_add("mouse_over_key", "*",
                      VirtualKeyboard.on_edje_signal_mouse_over_key)
#o.signal_callback_del("mouse_over_key", "*",
#                      VirtualKeyboard.on_edje_signal_mouse_over_key)

ee.data["main"] = o
ee.callback_delete_request = on_delete_request
ee.callback_resize = on_resize
ee.title = TITLE
ee.name_class = WM_INFO
ee.fullscreen = FS
ee.show()

ecore.main_loop_begin()
