[app]

# --- about the app ---
title = Lucky Casino
package.name = luckycasino
# change "example" to anything you like (for example your nickname, lowercase)
package.domain = org.example
version = 0.1

# --- what goes into the apk ---
source.dir = .
source.include_exts = py,png,ttf,wav
source.exclude_dirs = myenv,venv,.venv,__pycache__,.git,.buildozer,bin
# these two only generate pictures and sounds on the computer, the phone does not need them
source.exclude_patterns = make_assets.py,make_blackjack_assets.py,make_android_assets.py

# --- python side ---
requirements = python3,kivy==2.3.0

# --- look ---
orientation = portrait
fullscreen = 1
icon.filename = %(source.dir)s/assets/android/icon.png
presplash.filename = %(source.dir)s/assets/android/presplash.png
android.presplash_color = #02170F

# --- android ---
# the game needs no internet and no other permissions
android.permissions =
android.archs = arm64-v8a
android.accept_sdk_license = True

# android.api, android.minapi, android.ndk and the rest are left at the
# buildozer defaults on purpose: they change between buildozer versions.

[buildozer]
log_level = 2
warn_on_root = 1
