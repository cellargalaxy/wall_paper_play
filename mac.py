#!/usr/bin/python
try:
    from AppKit import NSWorkspace
except ImportError:
    print("Can't import AppKit -- maybe you're running python( from brew?")
    print("Try running with Apple's /usr/bin/python instead.")
    exit(1)

from time import sleep

last_active_name = None
while True:
    active_app = NSWorkspace.sharedWorkspace().activeApplication()
    if active_app['NSApplicationName'] != last_active_name:
        last_active_name = active_app['NSApplicationName']
        print('%s [%s]' % (active_app['NSApplicationName'], active_app['NSApplicationPath']))
    sleep(1)
