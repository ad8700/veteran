"""
Custom Android GPS implementation that works with Android 13+ (API 33)
Fixes the plyer GPS bug where onLocationChanged doesn't handle List<Location>
"""

from kivy.utils import platform

if platform == 'android':
    from jnius import autoclass, PythonJavaClass, java_method
    from android.permissions import request_permissions, Permission

    # Android Java classes
    LocationManager = autoclass('android.location.LocationManager')
    Context = autoclass('android.content.Context')
    PythonActivity = autoclass('org.kivy.android.PythonActivity')


class AndroidGPS:
    """GPS implementation that properly handles Android 13+ location API"""

    def __init__(self, on_location_callback=None):
        self.on_location_callback = on_location_callback
        self.location_manager = None
        self.location_listener = None
        self.lat = None
        self.lon = None
        self.accuracy = None

    def configure(self, on_location=None):
        """Configure the GPS with a callback"""
        if on_location:
            self.on_location_callback = on_location

    def start(self, min_time=1000, min_distance=0):
        """Start receiving GPS updates"""
        if platform != 'android':
            print("GPS only available on Android")
            return

        try:
            # Request permissions
            request_permissions([
                Permission.ACCESS_FINE_LOCATION,
                Permission.ACCESS_COARSE_LOCATION
            ])

            # Get location manager
            activity = PythonActivity.mActivity
            context = activity.getApplicationContext()
            self.location_manager = context.getSystemService(Context.LOCATION_SERVICE)

            # Create location listener
            self.location_listener = AndroidLocationListener(self)

            # Request location updates from GPS provider
            self.location_manager.requestLocationUpdates(
                LocationManager.GPS_PROVIDER,
                min_time,  # minimum time interval in ms
                min_distance,  # minimum distance in meters
                self.location_listener
            )

            print("GPS started successfully")

        except Exception as e:
            print(f"Error starting GPS: {e}")
            import traceback
            traceback.print_exc()

    def stop(self):
        """Stop receiving GPS updates"""
        if self.location_manager and self.location_listener:
            try:
                self.location_manager.removeUpdates(self.location_listener)
                print("GPS stopped")
            except Exception as e:
                print(f"Error stopping GPS: {e}")

    def _on_location_changed(self, location):
        """Internal callback when location changes"""
        try:
            self.lat = location.getLatitude()
            self.lon = location.getLongitude()
            self.accuracy = location.getAccuracy()

            print(f"GPS location: lat={self.lat}, lon={self.lon}, accuracy={self.accuracy}m")

            # Call user's callback
            if self.on_location_callback:
                self.on_location_callback(
                    lat=self.lat,
                    lon=self.lon,
                    accuracy=self.accuracy,
                    altitude=location.getAltitude() if location.hasAltitude() else None,
                    speed=location.getSpeed() if location.hasSpeed() else None,
                    bearing=location.getBearing() if location.hasBearing() else None
                )
        except Exception as e:
            print(f"Error processing location: {e}")
            import traceback
            traceback.print_exc()


class AndroidLocationListener(PythonJavaClass):
    """
    Java interface implementation for Android LocationListener
    Properly handles both old (single Location) and new (List<Location>) API
    """
    __javainterfaces__ = ['android/location/LocationListener']
    __javacontext__ = 'app'

    def __init__(self, gps_instance):
        super().__init__()
        self.gps = gps_instance

    # Handle new Android 13+ API: onLocationChanged(List<Location>)
    @java_method('(Ljava/util/List;)V')
    def onLocationChanged(self, locations):
        """Called with a list of locations (Android 13+)"""
        try:
            if locations and locations.size() > 0:
                # Get the most recent location (last in list)
                location = locations.get(locations.size() - 1)
                self.gps._on_location_changed(location)
        except Exception as e:
            print(f"Error in onLocationChanged(List): {e}")

    # Also handle old API: onLocationChanged(Location) for backwards compatibility
    @java_method('(Landroid/location/Location;)V')
    def onLocationChanged_single(self, location):
        """Called with single location (older Android)"""
        try:
            if location:
                self.gps._on_location_changed(location)
        except Exception as e:
            print(f"Error in onLocationChanged(Location): {e}")

    @java_method('(Ljava/lang/String;)V')
    def onProviderEnabled(self, provider):
        """Called when location provider is enabled"""
        print(f"GPS provider enabled: {provider}")

    @java_method('(Ljava/lang/String;)V')
    def onProviderDisabled(self, provider):
        """Called when location provider is disabled"""
        print(f"GPS provider disabled: {provider}")

    @java_method('(Ljava/lang/String;ILandroid/os/Bundle;)V')
    def onStatusChanged(self, provider, status, extras):
        """Called when provider status changes"""
        print(f"GPS status changed: provider={provider}, status={status}")
