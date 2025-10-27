import kivy
from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy_garden.mapview import MapView, MapMarker
from kivy.garden.geolocation import Geolocation
import sqlite3

# Import our custom utilities
from utils.MapHandler import MapHandler
from utils.veteran_info import VeteranInfoPopup

class VeteranGraveMarker(App):
    def get_gps_location(self):
        """Get current GPS location from the device"""
        # Access the geolocation from map_handler
        if hasattr(self, 'map_handler') and self.map_handler.geolocation:
            geo = self.map_handler.geolocation
            # Check if we have valid GPS coordinates
            if geo.lat is not None and geo.lon is not None:
                return geo.lat, geo.lon
            else:
                print("GPS location not yet available. Waiting for signal...")
                return None, None
        else:
            print("MapHandler not initialized.")
            return None, None

    def add_point(self, latitude, longitude):
        """Add a grave location to the database and return its ID"""
        # Connect to the database
        conn = sqlite3.connect("VeteranGraveMarker.db")
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

    def build(self):
        layout = GridLayout(cols=1)
        label = Label(text="Welcome")
        layout.add_widget(label)

        # Create MapView and MapHandler
        map_view = MapView(zoom=15, lat=39.8283, lon=-98.5795)  # Default to center of USA
        self.map_handler = MapHandler(map_view)  # Save as instance variable
        self.map_handler.request_location_permission()  # Start GPS
        layout.add_widget(map_view)

        drop_pin_button = Button(text="Drop Pin", on_press=self.drop_pin)
        layout.add_widget(drop_pin_button)

        return layout

    def drop_pin(self, instance):
        """Called when user presses 'Drop Pin' button"""
        # Get the current map coordinates
        latitude, longitude = self.get_gps_location()

        # Check if GPS location is available
        if latitude is None or longitude is None:
            print("Cannot drop pin: GPS location not available yet")
            return

        # Add the point to database and get its ID
        grave_id = self.add_point(latitude, longitude)

        # Show the popup for adding veteran information
        popup = VeteranInfoPopup(grave_id)
        popup.open()

if __name__ == "__main__":
    VeteranGraveMarker().run()
    

    