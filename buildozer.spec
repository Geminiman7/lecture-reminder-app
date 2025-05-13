[app]
title = LectureReminder
package.name = lecturereminder
package.domain = org.kivy
source.dir = .
source.include_exts = py,kv,db
version = 1.0
requirements = python3,kivy,plyer
orientation = portrait
fullscreen = 0

[buildozer]
log_level = 2
warn_on_root = 1

[android]
android.permissions = INTERNET,RECEIVE_BOOT_COMPLETED
android.api = 31
android.minapi = 21
android.ndk = 23b
android.archs = armeabi-v7a
