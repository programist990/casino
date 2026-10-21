[app]

# --- about the app ---
title = Lucky Casino
package.name = luckycasino
# change "example" to anything you like (for example your nickname, lowercase)
package.domain = org.example
version = 0.2

# --- what goes into the apk ---
source.dir = .
source.include_exts = py,png,ttf,wav
source.exclude_dirs = myenv,venv,.venv,__pycache__,.git,.buildozer,bin,apk
# these scripts only generate pictures and sounds on the computer, the phone does not need them
source.exclude_patterns = make_*.py

# --- python side ---
# same Kivy version as on the computer (2.3.1) and as in the python-for-android recipe
requirements = python3,kivy==2.3.1
p4a.branch = master

# --- look ---
orientation = portrait
fullscreen = 1
icon.filename = %(source.dir)s/assets/android/icon.png
presplash.filename = %(source.dir)s/assets/android/presplash.png
android.presplash_color = #02170F

# --- android ---
# the game needs no internet; the only permission is the vibration of the phone
android.permissions = VIBRATE
# 64-bit only: faster build, works on every phone of the last ~8 years.
# For very old 32-bit phones use: arm64-v8a, armeabi-v7a
android.archs = arm64-v8a
android.accept_sdk_license = True

# android.api, android.minapi and android.ndk are left at the buildozer defaults
# on purpose: they match the python-for-android "master" branch used above.

[buildozer]
log_level = 2
warn_on_root = 1
