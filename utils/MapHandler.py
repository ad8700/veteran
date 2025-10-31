from kivy.utils import platform
from utils.AndroidGPS import AndroidGPS

if platform == 'android':
    from jnius import autoclass
    Log = autoclass('android.util.Log')

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
            print("MapHandler.request_location_permission() called")
            if platform == 'android':
                Log.i("VeteranGraveApp", "MapHandler.request_location_permission() - creating AndroidGPS")

            # Use our custom GPS implementation
            self.gps = AndroidGPS(on_location_callback=self.on_location)

            print("AndroidGPS instance created, calling start()")
            if platform == 'android':
                Log.i("VeteranGraveApp", "AndroidGPS instance created, calling start()")

            self.gps.start(min_time=1000, min_distance=0)

            print("GPS start() completed")
            if platform == 'android':
                Log.i("VeteranGraveApp", "GPS start() completed successfully")

            # Update status
            if self.app:
                self.app.update_gps_status("GPS: Searching for satellites...")
        except Exception as e:
            error_msg = f"GPS not available: {e}"
            print(error_msg)
            if platform == 'android':
                Log.e("VeteranGraveApp", error_msg)
            if self.app:
                self.app.update_gps_status("GPS: Error starting GPS")
            import traceback
            traceback.print_exc()

    def on_location(self, **kwargs):
        """Called when GPS location is updated"""
        self.lat = kwargs.get('lat')
        self.lon = kwargs.get('lon')
        accuracy = kwargs.get('accuracy', 0)

        location_msg = f"GPS location updated: lat={self.lat}, lon={self.lon}, accuracy={accuracy}m"
        print(location_msg)
        if platform == 'android':
            Log.i("VeteranGraveApp", location_msg)

        if self.lat and self.lon:
            if platform == 'android':
                Log.i("VeteranGraveApp", "Centering map on GPS location")
            self.map_view.center_on(self.lat, self.lon)
            # Update status label
            if self.app:
                self.app.update_gps_status(f"GPS: Ready (±{accuracy:.0f}m)")

    def center_map_on_user_location(self):
        """Center map on current GPS location"""
        if self.lat and self.lon:
            self.map_view.center_on(self.lat, self.lon)