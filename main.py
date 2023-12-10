import kivy
from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.gridlayout import GridLayout
from kivy.maps.googlemap import GoogleMap, GoogleMapMarker
from kivy.modules.googlemaps import GoogleMapWidget
from kivy.garden.geolocation import Geolocation 
import sqlite3

class VeteranGraveMarker(App):
    def build(self):
        layout = GridLayout(cols=1)
        label = Label(text="Welcome")
        layout.add_widget(label)
        return layout
if __name__ == "__main__":
    VeteranGraveMarker().run()
    
# Create GoogleMapWidget
google_map = GoogleMapWidget()
layout.add_widget(google_map)

# Create MapHandler class to manage map functionalities
map_handler = MapHandler(google_map)

#Create database connection
conn = sqlite3.connect('veteran_graves.db')
    