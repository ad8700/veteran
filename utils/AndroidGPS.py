"""
Custom Android GPS implementation that works with Android 13+ (API 33)
Fixes the plyer GPS bug where onLocationChanged doesn't handle List<Location>

Key improvements:
- Uses both GPS and NETWORK providers for better reliability
- Checks if location providers are enabled
- Gets last known location to "prime" the GPS
- Better error handling and logging
"""

from kivy.utils import platform
from kivy.clock import Clock

if platform == 'android':
    from jnius import autoclass, PythonJavaClass, java_method, cast
    from android.permissions import request_permissions, Permission, check_permission

    # Android Java classes
    LocationManager = autoclass('android.location.LocationManager')
    Context = autoclass('android.content.Context')
    PythonActivity = autoclass('org.kivy.android.PythonActivity')
    Intent = autoclass('android.content.Intent')
    Settings = autoclass('android.provider.Settings')


class AndroidGPS:
    """GPS implementation that properly handles Android 13+ location API"""

    def __init__(self, on_location_callback=None):
        self.on_location_callback = on_location_callback
        self.location_manager = None
        self.location_listener = None
        self.lat = None
        self.lon = None
        self.accuracy = None
        self.gps_enabled = False
        self.network_enabled = False

    def configure(self, on_location=None):
        """Configure the GPS with a callback"""
        if on_location:
            self.on_location_callback = on_location

    def check_permissions(self):
        """Check if location permissions are granted"""
        if platform != 'android':
            return False

        fine = check_permission(Permission.ACCESS_FINE_LOCATION)
        coarse = check_permission(Permission.ACCESS_COARSE_LOCATION)
        print(f"Permission check: FINE={fine}, COARSE={coarse}")
        return fine or coarse

    def start(self, min_time=1000, min_distance=0):
        """Start receiving GPS updates (DEPRECATED - use start_without_requesting_permissions)"""
        if platform != 'android':
            print("GPS only available on Android")
            return

        try:
            print("=== Starting GPS ===")

            # Request permissions first
            print("Requesting location permissions...")
            request_permissions([
                Permission.ACCESS_FINE_LOCATION,
                Permission.ACCESS_COARSE_LOCATION
            ])

            # Wait a moment for permissions, then check
            Clock.schedule_once(lambda dt: self._start_after_permission(min_time, min_distance), 0.5)

        except Exception as e:
            print(f"Error starting GPS: {e}")
            import traceback
            traceback.print_exc()

    def start_without_requesting_permissions(self, min_time=1000, min_distance=0):
        """Start GPS - assumes permissions already granted"""
        if platform != 'android':
            print("GPS only available on Android")
            return

        print("=== AndroidGPS: Starting GPS (permissions already requested) ===")
        # Start immediately - no permission request, no delay
        self._start_after_permission(min_time, min_distance)

    def _start_after_permission(self, min_time, min_distance):
        """Start GPS after permissions have been requested"""
        try:
            print("Initializing LocationManager...")

            # Get location manager
            activity = PythonActivity.mActivity
            context = activity.getApplicationContext()
            self.location_manager = context.getSystemService(Context.LOCATION_SERVICE)

            # Check which providers are enabled
            self.gps_enabled = self.location_manager.isProviderEnabled(LocationManager.GPS_PROVIDER)
            self.network_enabled = self.location_manager.isProviderEnabled(LocationManager.NETWORK_PROVIDER)

            print(f"GPS Provider enabled: {self.gps_enabled}")
            print(f"Network Provider enabled: {self.network_enabled}")

            if not self.gps_enabled and not self.network_enabled:
                print("ERROR: No location providers are enabled!")
                print("Please enable GPS in device settings")
                return

            # Create location listener
            self.location_listener = AndroidLocationListener(self)

            # Try to get last known location first (helps "prime" the GPS)
            self._get_last_known_location()

            # Request location updates from GPS provider
            if self.gps_enabled:
                print(f"Requesting GPS updates (minTime={min_time}ms, minDistance={min_distance}m)...")
                self.location_manager.requestLocationUpdates(
                    LocationManager.GPS_PROVIDER,
                    min_time,
                    float(min_distance),
                    self.location_listener
                )
                print("GPS updates requested")

            # Also request from network provider as fallback
            if self.network_enabled:
                print(f"Requesting NETWORK updates (minTime={min_time}ms, minDistance={min_distance}m)...")
                self.location_manager.requestLocationUpdates(
                    LocationManager.NETWORK_PROVIDER,
                    min_time,
                    float(min_distance),
                    self.location_listener
                )
                print("Network updates requested")

            print("GPS initialization complete")

        except Exception as e:
            print(f"Error in _start_after_permission: {e}")
            import traceback
            traceback.print_exc()

    def _get_last_known_location(self):
        """Get the last known location to initialize GPS faster"""
        try:
            # Try GPS first
            if self.gps_enabled:
                last_loc = self.location_manager.getLastKnownLocation(LocationManager.GPS_PROVIDER)
                if last_loc:
                    print("Got last known GPS location")
                    self._on_location_changed(last_loc)
                    return

            # Try network provider
            if self.network_enabled:
                last_loc = self.location_manager.getLastKnownLocation(LocationManager.NETWORK_PROVIDER)
                if last_loc:
                    print("Got last known NETWORK location")
                    self._on_location_changed(last_loc)
                    return

            print("No last known location available")

        except Exception as e:
            print(f"Error getting last known location: {e}")

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

            # Get provider name
            provider = location.getProvider()

            print(f"=== Location Update ===")
            print(f"Provider: {provider}")
            print(f"Latitude: {self.lat}")
            print(f"Longitude: {self.lon}")
            print(f"Accuracy: {self.accuracy}m")

            # Call user's callback
            if self.on_location_callback:
                print("Calling user callback...")
                self.on_location_callback(
                    lat=self.lat,
                    lon=self.lon,
                    accuracy=self.accuracy,
                    altitude=location.getAltitude() if location.hasAltitude() else None,
                    speed=location.getSpeed() if location.hasSpeed() else None,
                    bearing=location.getBearing() if location.hasBearing() else None,
                    provider=provider
                )
                print("User callback complete")
        except Exception as e:
            print(f"ERROR in _on_location_changed: {e}")
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
            print(f"onLocationChanged(List) called with {locations.size() if locations else 0} locations")
            if locations and locations.size() > 0:
                # Get the most recent location (last in list)
                location = locations.get(locations.size() - 1)
                self.gps._on_location_changed(location)
        except Exception as e:
            print(f"ERROR in onLocationChanged(List): {e}")
            import traceback
            traceback.print_exc()

    # Also handle old API: onLocationChanged(Location) for backwards compatibility
    @java_method('(Landroid/location/Location;)V')
    def onLocationChanged_single(self, location):
        """Called with single location (older Android)"""
        try:
            print("onLocationChanged(Location) called")
            if location:
                self.gps._on_location_changed(location)
        except Exception as e:
            print(f"ERROR in onLocationChanged(Location): {e}")
            import traceback
            traceback.print_exc()

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
