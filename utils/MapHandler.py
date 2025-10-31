from plyer import gps
from kivy.utils import platform

class MapHandler:
    def __init__(self, map_view):
        self.map_view = map_view
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

    def on_location(self, **kwargs):
        """Called when GPS location is updated"""
        self.lat = kwargs.get('lat')
        self.lon = kwargs.get('lon')
        if self.lat and self.lon:
            self.map_view.center_on(self.lat, self.lon)

    def center_map_on_user_location(self):
        """Center map on current GPS location"""
        if self.lat and self.lon:
            self.map_view.center_on(self.lat, self.lon)