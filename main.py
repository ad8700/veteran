import kivy
from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.clock import Clock
from kivy_garden.mapview import MapView, MapMarker
import sqlite3
import os

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


class MainScreen(Screen):
    """Main app screen with map and controls"""

    def __init__(self, app, **kwargs):
        super(MainScreen, self).__init__(**kwargs)
        self.name = 'main'
        self.app = app
        self._build_ui()

    def _build_ui(self):
        layout = GridLayout(cols=1, rows=5)

        # User status bar
        self.user_status = UserStatusBar(on_sign_out=self.app.show_login_screen)
        layout.add_widget(self.user_status)

        # GPS Status Label
        self.app.gps_status_label = Label(text="GPS: Acquiring signal...", size_hint_y=0.08)
        layout.add_widget(self.app.gps_status_label)

        # Create MapView and MapHandler
        map_view = MapView(zoom=15, lat=39.8283, lon=-98.5795)  # Default to center of USA
        self.app.map_handler = MapHandler(map_view, self.app)
        layout.add_widget(map_view)

        # Button row
        button_layout = BoxLayout(size_hint_y=0.12, spacing=10, padding=[10, 5])

        drop_pin_button = Button(text="Drop Pin", on_press=self.app.drop_pin)
        button_layout.add_widget(drop_pin_button)

        self.app.sync_button = Button(text="Sync", on_press=self.app.sync_data)
        button_layout.add_widget(self.app.sync_button)

        layout.add_widget(button_layout)

        self.add_widget(layout)

    def on_enter(self):
        """Called when screen is shown"""
        # Update user status bar
        if hasattr(self, 'user_status'):
            self.user_status.update()


class VeteranGraveMarker(App):
    def get_db_path(self):
        """Get the database path in the app's data directory"""
        return os.path.join(self.user_data_dir, "VeteranGraveMarker.db")

    def get_gps_location(self):
        """Get current GPS location from the device"""
        if hasattr(self, 'map_handler'):
            if self.map_handler.lat is not None and self.map_handler.lon is not None:
                return self.map_handler.lat, self.map_handler.lon
            else:
                print("GPS location not yet available. Waiting for signal...")
                return None, None
        else:
            print("MapHandler not initialized.")
            return None, None

    def add_point(self, latitude, longitude):
        """Add a grave location to the database and return its ID"""
        db_path = self.get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get user ID from auth manager
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
        """Initialize the database and create tables if they don't exist"""
        db_path = self.get_db_path()
        conn = sqlite3.connect(db_path)

        # Create the Grave_Locations table
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
        """Update the GPS status label - must be called from main thread"""
        def update_ui(dt):
            if hasattr(self, 'gps_status_label'):
                self.gps_status_label.text = status_text
                print(f"GPS status updated to: {status_text}")

        Clock.schedule_once(update_ui, 0)

    def on_start(self):
        """Called when the app starts - request permissions and check for OAuth callback"""
        # Check for OAuth callback (app opened via veterangravemarker://callback URL)
        self._check_oauth_callback()

        if platform == 'android':
            print("=== App Started - Requesting Location Permissions ===")
            self.update_gps_status("Requesting location permission...")

            request_permissions([
                Permission.ACCESS_FINE_LOCATION,
                Permission.ACCESS_COARSE_LOCATION
            ])

            Clock.schedule_once(self.start_gps_after_permission, 3.0)

    def _check_oauth_callback(self):
        """Check if app was opened via OAuth callback URL"""
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
                    print(f"OAuth callback URL: {callback_url}")

                    if 'veterangravemarker://callback' in callback_url:
                        # Handle the OAuth callback
                        self._handle_oauth_callback(callback_url)

                        # Clear the intent data to prevent re-processing
                        intent.setData(None)

        except Exception as e:
            print(f"Error checking OAuth callback: {e}")
            import traceback
            traceback.print_exc()

    def _handle_oauth_callback(self, callback_url):
        """Process OAuth callback and complete sign-in"""
        print(f"Processing OAuth callback: {callback_url}")

        auth_manager = get_auth_manager()

        def on_success(user_info):
            print(f"OAuth sign-in successful: {user_info}")
            self.on_login_complete()
            # Show success message
            popup = Popup(
                title='Signed In',
                content=Label(text=f'Welcome, {auth_manager.get_user_display_name()}!'),
                size_hint=(0.8, 0.3)
            )
            popup.open()

        def on_error(error):
            print(f"OAuth sign-in failed: {error}")
            popup = Popup(
                title='Sign In Failed',
                content=Label(text=f'Error: {error}'),
                size_hint=(0.8, 0.3)
            )
            popup.open()

        auth_manager.handle_oauth_callback(callback_url, on_success, on_error)

    def start_gps_after_permission(self, dt):
        """Start GPS after giving user time to grant permissions"""
        print("=== Starting GPS (assuming permissions granted) ===")
        self.update_gps_status("GPS: Acquiring signal...")
        if hasattr(self, 'map_handler'):
            self.map_handler.start_gps_without_permission_request()

    def build(self):
        # Initialize the database
        self.init_database()

        # Initialize sync manager
        self.sync_manager = SyncManager(self.get_db_path())

        # Create screen manager
        self.screen_manager = ScreenManager()

        # Create login screen
        self.login_screen = LoginScreen(on_login_complete=self.on_login_complete)
        self.screen_manager.add_widget(self.login_screen)

        # Create main screen
        self.main_screen = MainScreen(self)
        self.screen_manager.add_widget(self.main_screen)

        # Check if user has previously made an auth choice
        auth_manager = get_auth_manager()
        if auth_manager.has_chosen:
            # Skip to main screen if user previously chose to sign in or continue as guest
            self.screen_manager.current = 'main'

        return self.screen_manager

    def on_login_complete(self):
        """Called when login is complete"""
        self.screen_manager.current = 'main'
        # Update user status bar
        if hasattr(self.main_screen, 'user_status'):
            self.main_screen.user_status.update()

    def show_login_screen(self):
        """Show the login screen"""
        self.screen_manager.current = 'login'

    def sync_data(self, instance):
        """Sync local data with AWS backend"""
        self.sync_button.text = "Syncing..."
        self.sync_button.disabled = True

        def on_sync_complete(result):
            self.sync_button.text = "Sync"
            self.sync_button.disabled = False
            uploaded = result.get('uploaded', 0)
            downloaded = len(result.get('downloaded', []))
            popup = Popup(
                title='Sync Complete',
                content=Label(text=f'Uploaded: {uploaded} records\nDownloaded: {downloaded} records'),
                size_hint=(0.8, 0.3)
            )
            popup.open()

        def on_sync_error(error):
            self.sync_button.text = "Sync"
            self.sync_button.disabled = False
            popup = Popup(
                title='Sync Failed',
                content=Label(text=f'Error: {error}\n\nMake sure you have internet connection.'),
                size_hint=(0.8, 0.3)
            )
            popup.open()

        self.sync_manager.sync(on_complete=on_sync_complete, on_error=on_sync_error)

    def drop_pin(self, instance):
        """Called when user presses 'Drop Pin' button"""
        latitude, longitude = self.get_gps_location()

        if latitude is None or longitude is None:
            print("Cannot drop pin: GPS location not available yet")
            popup = Popup(
                title='GPS Not Ready',
                content=Label(text='Waiting for GPS signal...\n\nMake sure you are outdoors with clear sky view.\nGPS may take 30-60 seconds to acquire signal.'),
                size_hint=(0.8, 0.4)
            )
            popup.open()
            return

        grave_id = self.add_point(latitude, longitude)

        popup = VeteranInfoPopup(grave_id, self.get_db_path(), latitude, longitude)
        popup.open()


if __name__ == "__main__":
    VeteranGraveMarker().run()
