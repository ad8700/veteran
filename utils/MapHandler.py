from kivy.garden.geolocation import Geolocation

class MapHandler:
    def __init__(self, google_map):
        self.google_map = google_map
        self.geolocation = Geolocation()

    def request_location_permission(self):
        self.geolocation.ask_permission()

    def center_map_on_user_location(self):
        latitude = self.geolocation.latitude
        longitude = self.geolocation.longitude
        self.google_map.center = [latitude, longitude]

    def set_satellite_view(self):
        self.google_map.maptype = GoogleMap.MAPTYPE_SATELLITE