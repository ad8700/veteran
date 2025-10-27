from kivy.garden.geolocation import Geolocation

class MapHandler:
    def __init__(self, map_view):
        self.map_view = map_view
        self.geolocation = Geolocation()

    def request_location_permission(self):
        self.geolocation.configure(on_location=self.on_location)
        self.geolocation.start()

    def on_location(self, **kwargs):
        """Called when GPS location is updated"""
        self.map_view.center_on(kwargs['lat'], kwargs['lon'])

    def center_map_on_user_location(self):
        if self.geolocation.lat and self.geolocation.lon:
            self.map_view.center_on(self.geolocation.lat, self.geolocation.lon)