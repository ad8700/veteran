from kivy.utils import platform
from kivy_garden.mapview import MapMarker
from utils.AndroidGPS import AndroidGPS

class MapHandler:
    def __init__(self, map_view, app=None):
        self.map_view = map_view
        self.app = app  # Reference to main app for status updates
        self.lat = None
        self.lon = None
        self.gps = None
        self.user_marker = None  # Marker showing user's current location

    def request_location_permission(self):
        """Request GPS permission and start location updates (DEPRECATED - permissions now requested in main.py)"""
        # This method is kept for compatibility but does nothing
        # Permissions and GPS start are now handled in main.py on_start()
        print("MapHandler.request_location_permission() called - permissions handled in main.py")
        pass

    def start_gps_without_permission_request(self):
        """Start GPS without requesting permissions (permissions already granted)"""
        try:
            print("=== MapHandler: Starting GPS ===")
            # Use our custom GPS implementation
            self.gps = AndroidGPS(on_location_callback=self.on_location)
            self.gps.start_without_requesting_permissions(min_time=1000, min_distance=0)

            # Update status
            if self.app:
                self.app.update_gps_status("GPS: Searching for satellites...")
        except Exception as e:
            print(f"GPS not available: {e}")
            import traceback
            traceback.print_exc()
            if self.app:
                self.app.update_gps_status("GPS: Error starting GPS")

    def on_location(self, **kwargs):
        """Called when GPS location is updated"""
        self.lat = kwargs.get('lat')
        self.lon = kwargs.get('lon')
        accuracy = kwargs.get('accuracy', 0)
        provider = kwargs.get('provider', 'unknown')

        print(f"GPS location updated: lat={self.lat}, lon={self.lon}, accuracy={accuracy}m, provider={provider}")

        if self.lat and self.lon:
            # Center map on user's location
            print(f"Centering map on: {self.lat}, {self.lon}")
            self.map_view.center_on(self.lat, self.lon)

            # Update or create user location marker
            if self.user_marker:
                # Update existing marker position
                self.user_marker.lat = self.lat
                self.user_marker.lon = self.lon
                print("Updated user marker position")
            else:
                # Create new marker for user's location (default red pin)
                self.user_marker = MapMarker(lat=self.lat, lon=self.lon)
                self.map_view.add_marker(self.user_marker)
                print("Created user location marker on map")

            # Update status label
            if self.app:
                self.app.update_gps_status(f"GPS: Ready (±{accuracy:.0f}m)")

    def center_map_on_user_location(self):
        """Center map on current GPS location"""
        if self.lat and self.lon:
            self.map_view.center_on(self.lat, self.lon)