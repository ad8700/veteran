[app]

# (str) Title of your application
title = Veteran Grave Marker

# (str) Package name - must be unique, no spaces, lowercase
package.name = veterangravemarker

# (str) Package domain (used to create unique app ID: com.yourname.appname)
package.domain = org.veterangraves

# (str) Source code where the main.py file is located
source.dir = .

# (str) The main entry point file
source.include_exts = py,png,jpg,kv,atlas,db

# (str) Application versioning (used in app stores)
version = 0.1

# (list) Application requirements - Python packages needed
# Separated by commas
requirements = python3,kivy,plyer

# (list) Garden requirements - Kivy Garden packages
garden_requirements = mapview

# (list) Permissions needed by the app
# IMPORTANT: These allow GPS and internet access
android.permissions = INTERNET,ACCESS_FINE_LOCATION,ACCESS_COARSE_LOCATION,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE

# (int) Target Android API - Android 10 (API 29) is widely compatible
android.api = 29

# (int) Minimum API your app supports - Android 5.0 (API 21)
android.minapi = 21

# (int) Android NDK version (Native Development Kit for C/C++ compilation)
android.ndk = 25b

# (bool) Copy library instead of making symbolic link (required on Windows)
android.copy_libs = 1

# (str) Android entry point - default is ok for Kivy apps
android.entrypoint = org.kivy.android.PythonActivity

# (str) Supported orientation (landscape, portrait, all)
orientation = portrait

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

# (list) Android features the app requires
android.features = android.hardware.location.gps

# (bool) Enable Android auto backup feature
android.allow_backup = True

# (int) Android SDK API to use - same as android.api for compatibility
android.sdk = 29

# (bool) If True, the app will use OpenSSL (needed for HTTPS connections)
# Required for MapView to load map tiles
requirements.ssl = True

# Python for Android recipe to use
p4a.branch = master

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug)
log_level = 2

# (int) Display warning if buildozer is run as root (0 = False, 1 = True)
warn_on_root = 1

# (str) Path to build artifacts and output APK
build_dir = ./.buildozer

# (str) Path to build output
bin_dir = ./bin
