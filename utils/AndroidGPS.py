"""
Custom Android GPS implementation that works reliably on Android 5+ (API 21+)

Key improvements over original:
- Fixed LocationListener method dispatch (onLocationChanged must match Java name)
- Uses permission callbacks instead of fixed delays
- Aggressive last-known-location priming for instant position
- Automatic timeout and retry if GPS takes too long
- Uses both GPS and NETWORK providers for better reliability
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
    """GPS implementation that works reliably on all Android versions (API 21+)"""

    def __init__(self, on_location_callback=None, on_status_callback=None):
        self.on_location_callback = on_location_callback
        self.on_status_callback = on_status_callback
        self.location_manager = None
        self.location_listener = None
        self.lat = None
        self.lon = None
        self.accuracy = None
        self.gps_enabled = False
        self.network_enabled = False
        self._has_fix = False
        self._retry_event = None
        self._started = False

    def configure(self, on_location=None, on_status=None):
        """Configure the GPS with callbacks"""
        if on_location:
            self.on_location_callback = on_location
        if on_status:
            self.on_status_callback = on_status

    def _update_status(self, status):
        """Send status update to callback"""
        if self.on_status_callback:
            self.on_status_callback(status)

    def check_permissions(self):
        """Check if location permissions are granted"""
        if platform != 'android':
            return False
        fine = check_permission(Permission.ACCESS_FINE_LOCATION)
        coarse = check_permission(Permission.ACCESS_COARSE_LOCATION)
        return fine or coarse

    def request_permissions_and_start(self, min_time=1000, min_distance=0):
        """Request permissions with a callback, then start GPS when granted"""
        if platform != 'android':
            print("GPS only available on Android")
            return

        self._update_status("Requesting location permission...")

        if self.check_permissions():
            # Already have permission, start immediately
            print("Permissions already granted, starting GPS immediately")
            self._start_location_updates(min_time, min_distance)
            return

        def _on_permissions(permissions, grants):
            """Called when user responds to permission dialog"""
            granted = any(grants) if grants else False
            print(f"Permission result: permissions={permissions}, grants={grants}, granted={granted}")
            if granted:
                Clock.schedule_once(
                    lambda dt: self._start_location_updates(min_time, min_distance), 0.1
                )
            else:
                self._update_status("GPS: Permission denied")
                print("Location permission denied by user")

        request_permissions(
            [Permission.ACCESS_FINE_LOCATION, Permission.ACCESS_COARSE_LOCATION],
            _on_permissions
        )

    def start(self, min_time=1000, min_distance=0):
        """Start GPS - uses permission callback (not a fixed delay)"""
        self.request_permissions_and_start(min_time, min_distance)

    def start_without_requesting_permissions(self, min_time=1000, min_distance=0):
        """Start GPS - assumes permissions already granted"""
        if platform != 'android':
            print("GPS only available on Android")
            return
        self._start_location_updates(min_time, min_distance)

    def _start_location_updates(self, min_time, min_distance):
        """Initialize LocationManager and begin receiving updates"""
        if self._started:
            print("GPS already started, skipping")
            return
        self._started = True
        self._min_time = min_time
        self._min_distance = min_distance

        try:
            print("=== Starting GPS location updates ===")
            self._update_status("GPS: Initializing...")

            # Get location manager
            activity = PythonActivity.mActivity
            context = activity.getApplicationContext()
            self.location_manager = context.getSystemService(Context.LOCATION_SERVICE)

            # Check which providers are available
            self.gps_enabled = self.location_manager.isProviderEnabled(
                LocationManager.GPS_PROVIDER
            )
            self.network_enabled = self.location_manager.isProviderEnabled(
                LocationManager.NETWORK_PROVIDER
            )

            print(f"GPS Provider: {self.gps_enabled}, Network Provider: {self.network_enabled}")

            if not self.gps_enabled and not self.network_enabled:
                self._update_status("GPS: Please enable Location Services")
                print("No location providers enabled!")
                return

            # Create listener
            self.location_listener = AndroidLocationListener(self)

            # Get last known location immediately (no waiting)
            self._prime_with_last_known()

            # Request continuous updates from available providers
            # Wrap each individually so one failing doesn't block the other
            if self.gps_enabled:
                try:
                    self.location_manager.requestLocationUpdates(
                        LocationManager.GPS_PROVIDER,
                        min_time,
                        float(min_distance),
                        self.location_listener
                    )
                    print("Registered for GPS provider updates")
                except Exception as e:
                    print(f"Failed to register GPS provider: {e}")

            if self.network_enabled:
                try:
                    self.location_manager.requestLocationUpdates(
                        LocationManager.NETWORK_PROVIDER,
                        min_time,
                        float(min_distance),
                        self.location_listener
                    )
                    print("Registered for Network provider updates")
                except Exception as e:
                    print(f"Failed to register Network provider: {e}")

            if not self._has_fix:
                self._update_status("GPS: Searching for satellites...")

            # Schedule a retry check - if no fix after 10s, try to recover
            self._retry_event = Clock.schedule_once(self._check_gps_timeout, 10.0)

        except Exception as e:
            print(f"Error starting GPS: {e}")
            import traceback
            traceback.print_exc()
            self._update_status("GPS: Retrying...")
            # Allow retry - reset _started so retry can re-attempt
            self._started = False
            self._retry_event = Clock.schedule_once(self._retry_start, 3.0)

    def _retry_start(self, dt):
        """Retry GPS initialization after an error"""
        print("Retrying GPS start...")
        self._start_location_updates(self._min_time, self._min_distance)

    def _prime_with_last_known(self):
        """Get last known location immediately to avoid waiting for a fix"""
        try:
            best_location = None
            best_time = 0

            # Check all providers for last known location
            for provider in [LocationManager.GPS_PROVIDER, LocationManager.NETWORK_PROVIDER]:
                try:
                    loc = self.location_manager.getLastKnownLocation(provider)
                    if loc and loc.getTime() > best_time:
                        best_location = loc
                        best_time = loc.getTime()
                except Exception:
                    pass

            if best_location:
                print(f"Primed with last known location from {best_location.getProvider()}")
                self._on_location_changed(best_location)
            else:
                print("No last known location available")

        except Exception as e:
            print(f"Error getting last known location: {e}")

    def _check_gps_timeout(self, dt):
        """If we still don't have a GPS fix, try to recover"""
        if self._has_fix:
            return

        print("GPS timeout - no fix after 10 seconds, retrying...")
        self._update_status("GPS: Still searching...")

        # Try last known location one more time
        self._prime_with_last_known()

        # Schedule another check
        self._retry_event = Clock.schedule_once(self._check_gps_timeout, 15.0)

    def stop(self):
        """Stop receiving GPS updates"""
        self._started = False
        if self._retry_event:
            self._retry_event.cancel()
            self._retry_event = None

        if self.location_manager and self.location_listener:
            try:
                self.location_manager.removeUpdates(self.location_listener)
                print("GPS stopped")
            except Exception as e:
                print(f"Error stopping GPS: {e}")

    def _on_location_changed(self, location):
        """Process a new location fix"""
        try:
            self.lat = location.getLatitude()
            self.lon = location.getLongitude()
            self.accuracy = location.getAccuracy()
            provider = location.getProvider()
            self._has_fix = True

            print(f"Location: {self.lat:.6f}, {self.lon:.6f} +/-{self.accuracy:.0f}m [{provider}]")

            if self.on_location_callback:
                self.on_location_callback(
                    lat=self.lat,
                    lon=self.lon,
                    accuracy=self.accuracy,
                    altitude=location.getAltitude() if location.hasAltitude() else None,
                    speed=location.getSpeed() if location.hasSpeed() else None,
                    bearing=location.getBearing() if location.hasBearing() else None,
                    provider=provider
                )
        except Exception as e:
            print(f"Error processing location: {e}")
            import traceback
            traceback.print_exc()


class AndroidLocationListener(PythonJavaClass):
    """
    Java LocationListener implementation.

    CRITICAL: The method must be named 'onLocationChanged' (matching the Java
    interface method name) with the single-Location JNI signature.
    This works on ALL Android versions:
    - API < 31: System calls onLocationChanged(Location) directly
    - API 31+: Default onLocationChanged(List<Location>) iterates and calls
               onLocationChanged(Location) for each entry
    """
    __javainterfaces__ = ['android/location/LocationListener']
    __javacontext__ = 'app'

    def __init__(self, gps_instance):
        super().__init__()
        self.gps = gps_instance

    @java_method('(Landroid/location/Location;)V')
    def onLocationChanged(self, location):
        """Called when location changes - works on all Android versions"""
        try:
            if location:
                self.gps._on_location_changed(location)
        except Exception as e:
            print(f"Error in onLocationChanged: {e}")
            import traceback
            traceback.print_exc()

    @java_method('(Ljava/lang/String;)V')
    def onProviderEnabled(self, provider):
        print(f"Location provider enabled: {provider}")

    @java_method('(Ljava/lang/String;)V')
    def onProviderDisabled(self, provider):
        print(f"Location provider disabled: {provider}")
        if self.gps.on_status_callback:
            self.gps._update_status(f"GPS: {provider} disabled")

    @java_method('(Ljava/lang/String;ILandroid/os/Bundle;)V')
    def onStatusChanged(self, provider, status, extras):
        print(f"Provider status: {provider} = {status}")
