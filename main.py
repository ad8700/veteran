import kivy
from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.clock import Clock
from kivy_garden.mapview import MapView, MapMarker
import sqlite3
import os

# Import our custom utilities
from utils.MapHandler import MapHandler
from utils.veteran_info import VeteranInfoPopup
from utils.SyncManager import SyncManager

# Import Android permissions if on Android
from kivy.utils import platform
if platform == 'android':
    from android.permissions import request_permissions, Permission, check_permission

class VeteranGraveMarker(App):
    def get_db_path(self):
        """Get the database path in the app's data directory"""
        return os.path.join(self.user_data_dir, "VeteranGraveMarker.db")

    def get_gps_location(self):
        """Get current GPS location from the device"""
        # Access the location from map_handler
        if hasattr(self, 'map_handler'):
            # Check if we have valid GPS coordinates
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
        # Connect to the database
        db_path = self.get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Insert the point into the Grave_Locations table
        cursor.execute("""
            INSERT INTO Grave_Locations (latitude, longitude, timestamp)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        """, (latitude, longitude))
        conn.commit()

        # Get the ID of the newly inserted row
        grave_id = cursor.lastrowid

        # Close the database connection
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
            photo_path STRING
        )""")

        conn.commit()
        conn.close()

    def update_gps_status(self, status_text):
        """Update the GPS status label - must be called from main thread"""
        # Use Clock.schedule_once to ensure UI update happens on main thread
        def update_ui(dt):
            if hasattr(self, 'gps_status_label'):
                self.gps_status_label.text = status_text
                print(f"GPS status updated to: {status_text}")

        Clock.schedule_once(update_ui, 0)

    def on_start(self):
        """Called when the app starts - request permissions here"""
        if platform == 'android':
            print("=== App Started - Requesting Location Permissions ===")
            self.update_gps_status("Requesting location permission...")

            # Request permissions
            request_permissions([
                Permission.ACCESS_FINE_LOCATION,
                Permission.ACCESS_COARSE_LOCATION
            ])

            # Give user 3 seconds to grant permissions, then start GPS
            # (don't check - just try to start and handle errors)
            Clock.schedule_once(self.start_gps_after_permission, 3.0)

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

        layout = GridLayout(cols=1, rows=4)

        # GPS Status Label
        self.gps_status_label = Label(text="GPS: Acquiring signal...", size_hint_y=0.1)
        layout.add_widget(self.gps_status_label)

        # Create MapView and MapHandler
        map_view = MapView(zoom=15, lat=39.8283, lon=-98.5795)  # Default to center of USA
        self.map_handler = MapHandler(map_view, self)  # Pass app instance for status updates
        # GPS will be started in on_start() after permissions are granted
        layout.add_widget(map_view)

        # Button row
        button_layout = BoxLayout(size_hint_y=0.15, spacing=10, padding=[10, 5])

        drop_pin_button = Button(text="Drop Pin", on_press=self.drop_pin)
        button_layout.add_widget(drop_pin_button)

        self.sync_button = Button(text="Sync", on_press=self.sync_data)
        button_layout.add_widget(self.sync_button)

        layout.add_widget(button_layout)

        return layout

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
        # Get the current map coordinates
        latitude, longitude = self.get_gps_location()

        # Check if GPS location is available
        if latitude is None or longitude is None:
            print("Cannot drop pin: GPS location not available yet")
            # Show popup to user
            popup = Popup(
                title='GPS Not Ready',
                content=Label(text='Waiting for GPS signal...\n\nMake sure you are outdoors with clear sky view.\nGPS may take 30-60 seconds to acquire signal.'),
                size_hint=(0.8, 0.4)
            )
            popup.open()
            return

        # Add the point to database and get its ID
        grave_id = self.add_point(latitude, longitude)

        # Show the popup for adding veteran information
        popup = VeteranInfoPopup(grave_id, self.get_db_path(), latitude, longitude)
        popup.open()

if __name__ == "__main__":
    VeteranGraveMarker().run()
    

    