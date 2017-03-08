#!/usr/bin/python
# -*- coding: utf-8 -*-

import xbmc
import xbmcaddon

import check_idle, load_addon_settings, sleep_time


__addon__ = xbmcaddon.Addon()
__addon_id__ = __addon__.getAddonInfo('id')


class MyMonitor( xbmc.Monitor ):
    def __init__( self, *args, **kwargs ):
        xbmc.Monitor.__init__( self )

    def onSettingsChanged( self ):
        load_addon_settings()

        
if __name__ == '__main__':
    monitor = MyMonitor()

    while not monitor.abortRequested():
        check_idle('InhibitIdleShutdown(false)', 'InhibitIdleShutdown(true)')
        if monitor.waitForAbort(float(sleep_time())):
            break
