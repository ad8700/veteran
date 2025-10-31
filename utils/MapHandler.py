from plyer import gps
from kivy.utils import platform

class MapHandler:
    def __init__(self, map_view, app=None):
        self.map_view = map_view
        self.app = app  # Reference to main app for status updates
        self.lat = None
        self.lon = None

    def request_location_permission(self):
        """Request GPS permission and start location updates"""
        if platform == 'android':
            # Request Android runtime permissions
            from android.permissions import request_permissions, Permission
            request_permissions([
                Permission.ACCESS_FINE_LOCATION,
                Permission.ACCESS_COARSE_LOCATION
            ])

        try:
            gps.configure(on_location=self.on_location, on_status=self.on_status)
            gps.start(minTime=1000, minDistance=0)
        except NotImplementedError:
            print("GPS not available on this platform")

    def on_status(self, stype, status):
        """Called when GPS status changes"""
        print(f"GPS status: {stype} = {status}")
        if self.app:
            if stype == 'provider-enabled':
                if status:
                    self.app.update_gps_status("GPS: Searching for satellites...")
                else:
                    self.app.update_gps_status("GPS: Disabled")

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