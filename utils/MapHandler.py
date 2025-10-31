from kivy.utils import platform
from utils.AndroidGPS import AndroidGPS

class MapHandler:
    def __init__(self, map_view, app=None):
        self.map_view = map_view
        self.app = app  # Reference to main app for status updates
        self.lat = None
        self.lon = None
        self.gps = None

    def request_location_permission(self):
        """Request GPS permission and start location updates"""
        try:
            # Use our custom GPS implementation
            self.gps = AndroidGPS(on_location_callback=self.on_location)
            self.gps.start(min_time=1000, min_distance=0)

            # Update status
            if self.app:
                self.app.update_gps_status("GPS: Searching for satellites...")
        except Exception as e:
            print(f"GPS not available: {e}")
            if self.app:
                self.app.update_gps_status("GPS: Error starting GPS")

    def on_location(self, **kwargs):
        """Called when GPS location is updated"""
        self.lat = kwargs.get('lat')
        self.lon = kwargs.get('lon')
        accuracy = kwargs.get('accuracy', 0)

        print(f"GPS location updated: lat={self.lat}, lon={self.lon}, accuracy={accuracy}m")

        if self.lat and self.lon:
            self.map_view.center_on(self.lat, self.lon)
            # Update status label
            if self.app:
                self.app.update_gps_status(f"GPS: Ready (±{accuracy:.0f}m)")

    def center_map_on_user_location(self):
        """Center map on current GPS location"""
        if self.lat and self.lon:
            self.map_view.center_on(self.lat, self.lon)