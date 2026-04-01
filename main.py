import kivy
from kivy.app import App
from kivy.core.window import Window
from kivy.uix.label import Label
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.clock import Clock
from kivy.graphics import Color, RoundedRectangle, Rectangle
from kivy_garden.mapview import MapView, MapMarker
import sqlite3
import os

# Set keyboard mode to resize window (fixes keyboard covering input fields)
Window.softinput_mode = 'below_target'

# Import our custom utilities
from utils.MapHandler import MapHandler
from utils.veteran_info import VeteranInfoPopup
from utils.SyncManager import SyncManager
from utils.LoginScreen import LoginScreen, UserStatusBar
from utils.AuthManager import get_auth_manager

# Import Android permissions if on Android
from kivy.utils import platform
if platform == 'android':
    from android.permissions import request_permissions, Permission, check_permission

# ── Color Palette ──
COLORS = {
    'bg':          (0.11, 0.11, 0.16, 1),
    'surface':     (0.16, 0.17, 0.23, 1),
    'primary':     (0.20, 0.50, 0.90, 1),
    'primary_dark':(0.12, 0.35, 0.70, 1),
    'accent':      (0.00, 0.59, 0.53, 1),
    'danger':      (0.90, 0.30, 0.25, 1),
    'text':        (0.93, 0.93, 0.96, 1),
    'text_dim':    (0.55, 0.57, 0.63, 1),
    'white':       (1, 1, 1, 1),
    'success':     (0.18, 0.72, 0.40, 1),
}


def styled_button(text, color_key='primary', height=48, font_size='16sp', **kwargs):
    """Create a modern flat button"""
    bg = COLORS.get(color_key, COLORS['primary'])
    btn = Button(
        text=text,
        size_hint_y=None,
        height=height,
        font_size=font_size,
        background_normal='',
        background_color=bg,
        color=COLORS['white'],
        bold=True,
        **kwargs
    )
    return btn


class MainScreen(Screen):
    """Main app screen with map and controls"""

    def __init__(self, app, **kwargs):
        super(MainScreen, self).__init__(**kwargs)
        self.name = 'main'
        self.app = app
        self._build_ui()

    def _build_ui(self):
        # Root layout with dark background
        root = BoxLayout(orientation='vertical')
        with root.canvas.before:
            Color(*COLORS['bg'])
            self._bg_rect = Rectangle(size=root.size, pos=root.pos)
        root.bind(size=self._update_bg, pos=self._update_bg)

        # User status bar
        self.user_status = UserStatusBar(on_sign_out=self.app.show_login_screen)
        root.add_widget(self.user_status)

        # GPS Status Label
        self.app.gps_status_label = Label(
            text="GPS: Acquiring signal...",
            size_hint_y=None,
            height=36,
            font_size='13sp',
            color=COLORS['text_dim'],
            bold=True
        )
        root.add_widget(self.app.gps_status_label)

        # Map
        map_view = MapView(zoom=15, lat=39.8283, lon=-98.5795)
        self.app.map_handler = MapHandler(map_view, self.app)
        root.add_widget(map_view)

        # Bottom button bar
        btn_bar = BoxLayout(
            size_hint_y=None,
            height=64,
            spacing=12,
            padding=[16, 8, 16, 8]
        )
        with btn_bar.canvas.before:
            Color(*COLORS['surface'])
            self._btn_bg = Rectangle(size=btn_bar.size, pos=btn_bar.pos)
        btn_bar.bind(
            size=lambda w, v: setattr(self._btn_bg, 'size', v),
            pos=lambda w, v: setattr(self._btn_bg, 'pos', v)
        )

        drop_pin_btn = styled_button("Drop Pin", 'accent', height=48, font_size='17sp')
        drop_pin_btn.bind(on_press=self.app.drop_pin)
        btn_bar.add_widget(drop_pin_btn)

        self.app.sync_button = styled_button("Sync", 'primary', height=48, font_size='17sp')
        self.app.sync_button.bind(on_press=self.app.sync_data)
        btn_bar.add_widget(self.app.sync_button)

        root.add_widget(btn_bar)
        self.add_widget(root)

    def _update_bg(self, widget, value):
        self._bg_rect.size = widget.size
        self._bg_rect.pos = widget.pos

    def on_enter(self):
        if hasattr(self, 'user_status'):
            self.user_status.update()


class VeteranGraveMarker(App):
    def get_db_path(self):
        return os.path.join(self.user_data_dir, "VeteranGraveMarker.db")

    def get_gps_location(self):
        if hasattr(self, 'map_handler'):
            if self.map_handler.lat is not None and self.map_handler.lon is not None:
                return self.map_handler.lat, self.map_handler.lon
            else:
                print("GPS location not yet available")
                return None, None
        else:
            print("MapHandler not initialized")
            return None, None

    def add_point(self, latitude, longitude):
        db_path = self.get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        auth_manager = get_auth_manager()
        user_id = auth_manager.get_user_id()

        cursor.execute("""
            INSERT INTO Grave_Locations (latitude, longitude, timestamp, user_id)
            VALUES (?, ?, CURRENT_TIMESTAMP, ?)
        """, (latitude, longitude, user_id))
        conn.commit()

        grave_id = cursor.lastrowid
        conn.close()
        return grave_id

    def init_database(self):
        db_path = self.get_db_path()
        conn = sqlite3.connect(db_path)

        conn.execute("""CREATE TABLE IF NOT EXISTS Grave_Locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            shapefile_id INTEGER,
            accuracy REAL,
            veteran_name STRING,
            branch_of_service STRING,
            birth_year SMALLINT,
            death_year SMALLINT,
            cemetary_name STRING,
            notes TEXT,
            photo_path STRING,
            user_id STRING,
            cloud_id STRING,
            sync_status STRING DEFAULT 'pending',
            last_synced TEXT
        )""")

        conn.commit()
        conn.close()

    def update_gps_status(self, status_text):
        def update_ui(dt):
            if hasattr(self, 'gps_status_label'):
                self.gps_status_label.text = status_text
        Clock.schedule_once(update_ui, 0)

    def on_start(self):
        # Bind new intent handler for OAuth
        if platform == 'android':
            from android import activity
            activity.bind(on_new_intent=self.on_new_intent)

        self._check_oauth_callback()

        # Start GPS with proper permission callback (no fixed delay)
        if platform == 'android':
            print("=== App Started - Requesting GPS ===")
            if hasattr(self, 'map_handler'):
                self.map_handler.request_location_permission()

    def _check_oauth_callback(self):
        if platform != 'android':
            return
        try:
            from jnius import autoclass
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            activity = PythonActivity.mActivity
            intent = activity.getIntent()

            if intent:
                uri = intent.getData()
                if uri:
                    callback_url = uri.toString()
                    if 'veterangravemarker://' in callback_url or 'code=' in callback_url:
                        Clock.schedule_once(
                            lambda dt: self._handle_oauth_callback(callback_url), 0.5
                        )
                        intent.setData(None)
                        self._oauth_callback_processed = True
        except Exception as e:
            print(f"Error checking OAuth callback: {e}")
            import traceback
            traceback.print_exc()

    def on_new_intent(self, intent):
        try:
            uri = intent.getData()
            if uri:
                callback_url = uri.toString()
                if 'veterangravemarker://' in callback_url or 'code=' in callback_url:
                    Clock.schedule_once(
                        lambda dt: self._handle_oauth_callback(callback_url), 0.5
                    )
        except Exception as e:
            print(f"Error in on_new_intent: {e}")

    def _handle_oauth_callback(self, callback_url):
        if 'error=' in callback_url:
            error_start = callback_url.find('error=') + 6
            error_end = callback_url.find('&', error_start)
            error = callback_url[error_start:error_end if error_end > 0 else None]
            popup = Popup(
                title='Sign In Failed',
                content=Label(text=f'OAuth Error: {error}'),
                size_hint=(0.8, 0.3)
            )
            popup.open()
            return

        auth_manager = get_auth_manager()

        def on_success(user_info):
            self.screen_manager.current = 'main'
            if hasattr(self.main_screen, 'user_status'):
                self.main_screen.user_status.update()
            Clock.schedule_once(
                lambda dt: self._show_welcome_popup(auth_manager.get_user_display_name()),
                0.5
            )

        def on_error(error):
            popup = Popup(
                title='Sign In Failed',
                content=Label(text=f'Error: {str(error)[:100]}'),
                size_hint=(0.8, 0.4)
            )
            popup.open()

        auth_manager.handle_oauth_callback(callback_url, on_success, on_error)

    def _show_welcome_popup(self, name):
        popup = Popup(
            title='Signed In',
            content=Label(text=f'Welcome, {name}!'),
            size_hint=(0.8, 0.3)
        )
        popup.open()

    def build(self):
        self.init_database()
        self.sync_manager = SyncManager(self.get_db_path())

        self.screen_manager = ScreenManager()

        self.login_screen = LoginScreen(on_login_complete=self.on_login_complete)
        self.screen_manager.add_widget(self.login_screen)

        self.main_screen = MainScreen(self)
        self.screen_manager.add_widget(self.main_screen)

        auth_manager = get_auth_manager()
        if auth_manager.has_chosen:
            self.screen_manager.current = 'main'

        return self.screen_manager

    def on_login_complete(self):
        self.screen_manager.current = 'main'
        if hasattr(self.main_screen, 'user_status'):
            self.main_screen.user_status.update()

    def show_login_screen(self):
        self.screen_manager.current = 'login'

    def sync_data(self, instance):
        self.sync_button.text = "Syncing..."
        self.sync_button.disabled = True

        def on_sync_complete(result):
            self.sync_button.text = "Sync"
            self.sync_button.disabled = False
            uploaded = result.get('uploaded', 0)
            downloaded = len(result.get('downloaded', []))
            popup = Popup(
                title='Sync Complete',
                content=Label(text=f'Uploaded: {uploaded}\nDownloaded: {downloaded}'),
                size_hint=(0.8, 0.3)
            )
            popup.open()

        def on_sync_error(error):
            self.sync_button.text = "Sync"
            self.sync_button.disabled = False
            popup = Popup(
                title='Sync Failed',
                content=Label(text=f'Error: {error}\n\nCheck your internet connection.'),
                size_hint=(0.8, 0.3)
            )
            popup.open()

        self.sync_manager.sync(on_complete=on_sync_complete, on_error=on_sync_error)

    def drop_pin(self, instance):
        latitude, longitude = self.get_gps_location()

        if latitude is None or longitude is None:
            popup = Popup(
                title='GPS Not Ready',
                content=Label(
                    text='Waiting for GPS signal...\n\n'
                         'Make sure Location Services are enabled\n'
                         'and you have a clear view of the sky.',
                    halign='center'
                ),
                size_hint=(0.85, 0.35)
            )
            popup.open()
            return

        grave_id = self.add_point(latitude, longitude)

        # Pin drop automatically opens the veteran info form
        popup = VeteranInfoPopup(grave_id, self.get_db_path(), latitude, longitude)
        popup.open()


if __name__ == "__main__":
    VeteranGraveMarker().run()
