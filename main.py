# -*- coding: utf-8 -*-
"""Humanizer - Kivy app.

Pick an AI-generated image, process it through the deterministic core and
save the humanized copy to the phone's Downloads folder.
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
from kivy.graphics import Color, Rectangle

import pixel
import android_io

COLORS = {
    "primary": (0.20, 0.40, 0.95, 1.0),
    "on_primary": (1.0, 1.0, 1.0, 1.0),
    "surface": (0.98, 0.98, 1.0, 1.0),
    "surface_container": (0.92, 0.94, 0.98, 1.0),
    "on_surface": (0.10, 0.11, 0.14, 1.0),
    "on_surface_variant": (0.44, 0.46, 0.52, 1.0),
    "error": (0.73, 0.18, 0.16, 1.0),
}


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

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        title = Label(
            text="Humanizer",
            font_size=sp(30),
            bold=True,
            size_hint_y=None,
            height=dp(44),
            halign="left",
            valign="middle",
            color=COLORS["on_surface"],
        )
        title.bind(size=lambda *_: setattr(title, "text_size", title.size))
        self.add_widget(title)

        subtitle = Label(
            text="Pick an AI-generated image and get a humanized copy.",
            font_size=sp(14),
            size_hint_y=None,
            height=dp(24),
            halign="left",
            valign="top",
            color=COLORS["on_surface_variant"],
        )
        subtitle.bind(size=lambda *_: setattr(subtitle, "text_size", subtitle.size))
        self.add_widget(subtitle)

        # Preview area
        self.preview_box = BoxLayout(size_hint_y=1)
        with self.preview_box.canvas.before:
            Color(*COLORS["surface_container"])
            self._bg = Rectangle(pos=self.preview_box.pos, size=self.preview_box.size)
        self.preview_box.bind(pos=self._update_bg, size=self._update_bg)
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

        # Status / message line
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

        # Buttons (secondary above primary, so the primary CTA sits at the
        # bottom, inside the thumb zone).
        self.secondary = self._make_button("", (1, 1, 1, 0), COLORS["primary"])
        self.secondary.bind(on_release=self._on_secondary)
        self.add_widget(self.secondary)

        self.primary = self._make_button("Choose image", COLORS["primary"], COLORS["on_primary"])
        self.primary.bind(on_release=self._on_primary)
        self.add_widget(self.primary)

    def _make_button(self, text, bg, fg):
        return Button(
            text=text,
            size_hint_y=None,
            height=dp(56),
            font_size=sp(16),
            background_normal="",
            background_color=bg,
            color=fg,
        )

    def _update_bg(self, *args):
        self._bg.pos = self.preview_box.pos
        self._bg.size = self.preview_box.size

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
            self.status_label.text = "Error: " + self.message
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
        from plyer import filechooser
        filechooser.open_file(
            on_selection=self._on_pick,
            filters=[("JPEG images", "*.jpg", "*.jpeg")],
        )

    def _on_pick(self, selection):
        if not selection:
            return
        uri_or_path = selection[0]

        name = os.path.basename(android_io.get_display_name(uri_or_path))
        cache = App.get_running_app().user_data_dir
        dest = os.path.join(cache, name)
        resolved = android_io.resolve_input(uri_or_path, dest)

        self.input_path = resolved
        self.output_path = ""
        self.message = ""
        self._set_preview(resolved)
        self.status = "ready"
        self._update_ui()

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
        self.message = msg
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
