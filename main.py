import kivy
from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button
 
import Button
from kivy.maps.googlemap import GoogleMap, GoogleMapMarker
from kivy.modules.googlemaps import GoogleMapWidget
from kivy.garden.geolocation import Geolocation
import sqlite3
from pygeocoder import Geocoder

class VeteranGraveMarker(App):
    def get_gps_location(self):
        # Use the Geocoder class with GPS provider
        location = Geocoder.geocode(method="gps")
        if location:
            latitude = location.latitude
            longitude = location.longitude
            return latitude, longitude
        else:
            print("Unable to get GPS location.")
            return None, None

    def add_point(self, latitude, longitude):
        # Connect to the database
        conn = sqlite3.connect("VeteranGraveMarker.db")

        # Insert the point into the Grave_Locations table
        conn.execute("""
            INSERT INTO Grave_Locations (latitude, longitude, timestamp)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        """, (latitude, longitude))
        conn.commit()

        # Close the database connection
        conn.close()

    def build(self):
        layout = GridLayout(cols=1)
        label = Label(text="Welcome")
        layout.add_widget(label)

        # Create GoogleMapWidget and MapHandler
        google_map = GoogleMapWidget()
        map_handler = MapHandler(google_map)
        layout.add_widget(google_map)

        # Create database connection
        conn = sqlite3.connect("VeteranGraveMarker.db")

        drop_pin_button = Button(text="Drop Pin", on_press=self.drop_pin)
        layout.add_widget(drop_pin_button)

        return layout

    def drop_pin(self, instance):
        # Get the current map coordinates
        latitude, longitude = self.get_gps_location()
        self.add_point(latitude, longitude)

        # Show the popup for adding veteran information
        popup = VeteranInfoPopup(conn.lastrowid)
        popup.open()

if __name__ == "__main__":
    VeteranGraveMarker().run()
    

    