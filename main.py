# -*- coding: utf-8 -*-
"""Humanizer - Kivy app (Android).

Pick an image, process it through the deterministic core and save the
humanized copy to the phone's Downloads folder.
"""
import os
import threading

from kivy.app import App
from kivy.clock import mainthread
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.graphics import Color, RoundedRectangle, Line

import pixel
import android_io

COLORS = {
    "primary": (0.19, 0.42, 0.95, 1.0),
    "on_primary": (1.0, 1.0, 1.0, 1.0),
    "surface": (0.98, 0.98, 1.0, 1.0),
    "surface_container": (0.93, 0.94, 0.98, 1.0),
    "on_surface": (0.10, 0.11, 0.14, 1.0),
    "on_surface_variant": (0.45, 0.47, 0.53, 1.0),
    "outline": (0.72, 0.74, 0.80, 1.0),
    "error": (0.73, 0.18, 0.16, 1.0),
}


class RoundedButton(Button):
    """Flat button with rounded corners; filled or outlined."""

    def __init__(self, filled=True, **kwargs):
        kwargs.setdefault("background_normal", "")
        kwargs.setdefault("background_down", "")
        kwargs.setdefault("background_color", (0, 0, 0, 0))
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", dp(56))
        kwargs.setdefault("font_size", sp(16))
        self.filled = filled
        self.radius = dp(14)
        super().__init__(**kwargs)
        self.bind(pos=self._redraw, size=self._redraw, disabled=self._redraw)
        self._redraw()

    def _redraw(self, *args):
        self.canvas.before.clear()
        if self.filled:
            bg = list(COLORS["primary"])
            if self.disabled:
                bg[3] = 0.4
            with self.canvas.before:
                Color(*bg)
                RoundedRectangle(pos=self.pos, size=self.size, radius=[self.radius])
        else:
            with self.canvas.before:
                Color(*COLORS["outline"])
                Line(
                    rounded_rectangle=(self.x, self.y, self.width, self.height, self.radius),
                    width=1.2,
                )


class RootWidget(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.padding = dp(24)
        self.spacing = dp(16)

        self.status = "empty"
        self.message = ""
        self.input_path = ""
        self.output_path = ""

        self._build_ui()
        self._update_ui()

        if android_io.IS_ANDROID:
            try:
                from android import activity
                activity.bind(on_activity_result=self._on_activity_result)
            except Exception as e:  # noqa: BLE001
                print("[humanizer] activity.bind failed:", e)

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        title = Label(
            text="Humanizer",
            font_size=sp(30),
            bold=True,
            size_hint_y=None,
            height=dp(46),
            halign="left",
            valign="middle",
            color=COLORS["on_surface"],
        )
        title.bind(size=lambda *_: setattr(title, "text_size", title.size))
        self.add_widget(title)

        subtitle = Label(
            text="Pick an AI image, get a humanized copy.",
            font_size=sp(14),
            size_hint_y=None,
            height=dp(24),
            halign="left",
            valign="top",
            color=COLORS["on_surface_variant"],
        )
        subtitle.bind(size=lambda *_: setattr(subtitle, "text_size", subtitle.size))
        self.add_widget(subtitle)

        # Preview card
        self.preview_box = BoxLayout(size_hint_y=1)
        self.preview_box.bind(pos=self._draw_card, size=self._draw_card)
        self.add_widget(self.preview_box)

        self.placeholder = Label(
            text="No image selected",
            font_size=sp(16),
            color=COLORS["on_surface_variant"],
            halign="center",
            valign="middle",
        )
        self.placeholder.bind(
            size=lambda *_: setattr(self.placeholder, "text_size", self.placeholder.size)
        )
        self.preview_box.add_widget(self.placeholder)

        self.preview = Image(fit_mode="contain")
        self.preview_box.add_widget(self.preview)

        # Status line
        self.status_label = Label(
            text="",
            font_size=sp(14),
            size_hint_y=None,
            height=dp(24),
            halign="center",
            color=COLORS["on_surface_variant"],
        )
        self.status_label.bind(
            size=lambda *_: setattr(self.status_label, "text_size", self.status_label.size)
        )
        self.add_widget(self.status_label)

        # Buttons (secondary above primary, primary sits in the thumb zone)
        self.secondary = RoundedButton(filled=False, text="")
        self.secondary.color = COLORS["primary"]
        self.secondary.bind(on_release=self._on_secondary)
        self.add_widget(self.secondary)

        self.primary = RoundedButton(filled=True, text="Choose image")
        self.primary.color = COLORS["on_primary"]
        self.primary.bind(on_release=self._on_primary)
        self.add_widget(self.primary)

    def _draw_card(self, *args):
        self.preview_box.canvas.before.clear()
        with self.preview_box.canvas.before:
            Color(*COLORS["surface_container"])
            RoundedRectangle(
                pos=self.preview_box.pos, size=self.preview_box.size, radius=[dp(18)]
            )

    # ------------------------------------------------------------- state
    def _update_ui(self):
        self.status_label.color = COLORS["on_surface_variant"]
        s = self.status

        if s == "empty":
            self.placeholder.opacity = 1
            self.preview.opacity = 0
            self.status_label.text = ""
            self.primary.text = "Choose image"
            self.primary.disabled = False
            self._set_secondary("", False)

        elif s == "ready":
            self.placeholder.opacity = 0
            self.preview.opacity = 1
            self.status_label.text = os.path.basename(self.input_path)
            self.primary.text = "Humanize"
            self.primary.disabled = False
            self._set_secondary("Change image", True)

        elif s == "loading":
            self.status_label.text = "Processing..."
            self.primary.text = "Processing..."
            self.primary.disabled = True
            self._set_secondary("", False)

        elif s == "done":
            self.placeholder.opacity = 0
            self.preview.opacity = 1
            self.status_label.text = os.path.basename(self.output_path)
            self.primary.text = "Save to phone"
            self.primary.disabled = False
            self._set_secondary("New image", True)

        elif s == "error":
            self.status_label.text = self.message
            self.status_label.color = COLORS["error"]
            self.primary.text = "Choose image"
            self.primary.disabled = False
            self._set_secondary("", False)

    def _set_secondary(self, text, visible):
        self.secondary.text = text
        self.secondary.disabled = not visible
        self.secondary.opacity = 1 if visible else 0
        self.secondary.height = dp(56) if visible else 0

    # ----------------------------------------------------------- actions
    def _on_primary(self, *args):
        s = self.status
        if s in ("empty", "error"):
            self.choose_image()
        elif s == "ready":
            self.humanize()
        elif s == "done":
            self.save()

    def _on_secondary(self, *args):
        s = self.status
        if s == "ready":
            self.choose_image()
        elif s == "done":
            self.reset()

    def choose_image(self):
        if not android_io.IS_ANDROID:
            self._show_error("Image picking works only on Android.")
            return
        try:
            from jnius import autoclass, cast
            Intent = autoclass("android.content.Intent")
            intent = Intent(Intent.ACTION_GET_CONTENT)
            intent.addCategory(Intent.CATEGORY_OPENABLE)
            intent.setType("image/*")
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            currentActivity = cast("android.app.Activity", PythonActivity.mActivity)
            currentActivity.startActivityForResult(intent, 0x1001)
            print("[humanizer] picker launched")
        except Exception as e:  # noqa: BLE001
            print("[humanizer] choose_image error:", e)
            self._show_error("Could not open the picker: " + str(e))

    @mainthread
    def _on_activity_result(self, request_code, result_code, data):
        print("[humanizer] on_activity_result", request_code, result_code, data)
        if data is None:
            print("[humanizer] result data is None (cancelled?)")
            return
        try:
            uri = data.getData()
            if uri is None:
                print("[humanizer] result uri is None")
                return
            self._process_picked(uri.toString())
        except Exception as e:  # noqa: BLE001
            print("[humanizer] result error:", e)
            self._show_error("Error reading the picker result: " + str(e))

    def _process_picked(self, uri_str):
        try:
            name = os.path.basename(android_io.get_display_name(uri_str))
            cache = App.get_running_app().user_data_dir
            dest = os.path.join(cache, name)
            print("[humanizer] picked", uri_str, "->", dest)
            if not android_io.copy_uri_to_file(uri_str, dest):
                self._show_error("Could not read the selected image.")
                return
            self.input_path = dest
            self.output_path = ""
            self.message = ""
            self._set_preview(dest)
            self.status = "ready"
            self._update_ui()
        except Exception as e:  # noqa: BLE001
            print("[humanizer] process_picked error:", e)
            self._show_error("Error: " + str(e))

    def humanize(self):
        if not self.input_path:
            return
        self.status = "loading"
        self._update_ui()
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        try:
            out = pixel.process_image(self.input_path)
        except Exception as exc:  # noqa: BLE001
            print("[humanizer] process error:", exc)
            self._on_error(str(exc))
            return
        self._on_done(out)

    @mainthread
    def _on_done(self, out):
        self.output_path = out
        self.status = "done"
        self._set_preview(out)
        self._update_ui()

    @mainthread
    def _on_error(self, msg):
        self.message = "Error: " + msg
        self.status = "error"
        self._update_ui()

    def save(self):
        if not self.output_path:
            return
        name = os.path.basename(self.output_path)
        ok = android_io.save_to_downloads(self.output_path, name)
        if ok:
            self.status_label.text = "Saved to Downloads: " + name
            self.status_label.color = COLORS["primary"]
        else:
            self.status_label.text = "Saved to: " + self.output_path
            self.status_label.color = COLORS["on_surface_variant"]

    def reset(self):
        self.input_path = ""
        self.output_path = ""
        self.message = ""
        self.status = "empty"
        self._set_preview("")
        self._update_ui()

    def _show_error(self, msg):
        self.message = msg
        self.status = "error"
        self._update_ui()

    def _set_preview(self, path):
        self.preview.source = path or ""
        if path:
            self.preview.reload()


class HumanizerApp(App):
    title = "Humanizer"

    def build(self):
        from kivy.core.window import Window
        Window.clearcolor = COLORS["surface"]
        return RootWidget()


if __name__ == "__main__":
    HumanizerApp().run()
