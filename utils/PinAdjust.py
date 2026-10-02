from kivy.uix.modalview import ModalView
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.graphics import Color, Line, Ellipse
from kivy.metrics import dp, sp
from kivy_garden.mapview import MapView, MapMarker


class Crosshair(Widget):
    """Fixed crosshair drawn at the centre of its parent"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(pos=self._draw, size=self._draw)

    def _draw(self, *args):
        self.canvas.clear()
        cx, cy = self.center
        r = dp(22)
        with self.canvas:
            Color(0.9, 0.2, 0.2, 1)
            Line(circle=(cx, cy, r), width=dp(2))
            Line(points=[cx - r - dp(8), cy, cx + r + dp(8), cy], width=dp(2))
            Line(points=[cx, cy - r - dp(8), cx, cy + r + dp(8)], width=dp(2))
            Ellipse(pos=(cx - dp(3), cy - dp(3)), size=(dp(6), dp(6)))


class PinAdjustPopup(ModalView):
    """
    Full-screen map where the user pans the map under a fixed crosshair to
    place the pin precisely. on_confirm(lat, lon) gets the corrected position.
    """

    def __init__(self, lat, lon, accuracy, on_confirm, on_cancel=None, make_button=None, **kwargs):
        super().__init__(size_hint=(1, 1), auto_dismiss=False, background_color=(0, 0, 0, 1), **kwargs)
        self._on_confirm = on_confirm
        self._on_cancel = on_cancel
        self.gps_lat, self.gps_lon = lat, lon

        root = FloatLayout()
        self.map_view = MapView(lat=lat, lon=lon, zoom=19)
        root.add_widget(self.map_view)

        # Where GPS thinks we are (so the user can see how far they moved it)
        self.map_view.add_marker(MapMarker(lat=lat, lon=lon))

        root.add_widget(Crosshair(size_hint=(1, 1)))

        acc = f"  (GPS accuracy ~{accuracy:.0f}m)" if accuracy else ""
        hint = Label(
            text=f"Drag the map so the crosshair is on the grave{acc}",
            size_hint=(1, None), height=dp(56), pos_hint={'top': 1},
            font_size=sp(16), halign='center', valign='middle',
            color=(1, 1, 1, 1),
        )
        hint.bind(size=lambda w, s: setattr(w, 'text_size', (s[0] - dp(24), s[1])))
        with hint.canvas.before:
            Color(0, 0, 0, 0.65)
            from kivy.graphics import Rectangle
            bg = Rectangle(pos=hint.pos, size=hint.size)
        hint.bind(pos=lambda w, p: setattr(bg, 'pos', p), size=lambda w, s: setattr(bg, 'size', s))
        root.add_widget(hint)

        bar = BoxLayout(size_hint=(1, None), height=dp(64), pos_hint={'x': 0, 'y': 0},
                        padding=dp(8), spacing=dp(8))
        from kivy.uix.button import Button
        mk = make_button or (lambda text, key: Button(text=text))
        cancel = mk("Cancel", 'surface')
        use_gps = mk("Reset to GPS", 'primary_dark')
        ok = mk("Confirm Pin", 'success')
        cancel.bind(on_release=self._cancel)
        use_gps.bind(on_release=lambda *a: self.map_view.center_on(self.gps_lat, self.gps_lon))
        ok.bind(on_release=self._confirm)
        for b in (cancel, use_gps, ok):
            bar.add_widget(b)
        root.add_widget(bar)
        self.add_widget(root)

    def _confirm(self, *args):
        lat, lon = self.map_view.lat, self.map_view.lon
        self.dismiss()
        self._on_confirm(lat, lon)

    def _cancel(self, *args):
        self.dismiss()
        if self._on_cancel:
            self._on_cancel()
