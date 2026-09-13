[app]

# (str) Title of your application
title = Humanizer

# (str) Package name
package.name = humanizer

# (str) Package domain (needed for android/ios packaging)
package.domain = org.example

# (str) Source code where the main.py live
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,jpg,jpeg,png

# (str) Application versioning (method 1)
version = 0.1

# (list) Application requirements
# comma separated e.g. requirements = sqlite3,kivy
# NOTE: python3 must stay unpinned (it auto-matches hostpython3 3.14.2).
requirements = python3,kivy,opencv,numpy,pillow,pyjnius

# (str) Supported orientation (one of landscape, sensorLandscape, portrait or all)
orientation = portrait

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0


#
# Android specific
#

# (list) Permissions (empty: the flow needs none on Android 10+)
android.permissions =

# (int) Target Android API
android.api = 34

# (int) Minimum API your APK will support
android.minapi = 29

# (list) Architecture(s) to build for
# arm64-v8a only: covers all modern phones and halves the OpenCV build time.
android.archs = arm64-v8a

# (bool) Automatically accept the Android SDK license agreements
android.accept_sdk_license = True

# Use the develop branch: master still runs the broken "pip install -U pip".
p4a.branch = develop


[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug)
log_level = 2

# (int) Display warning if buildozer is run as root
warn_on_root = 1

# (str) Path to build artifact storage
# bin_dir = ./bin
