#!/usr/bin/python
# -*- coding: utf-8 -*-

import xbmc
import xbmcaddon

xbmc.log(msg='[{}] Addon started.'.format(__addon_id__), level=xbmc.LOGNOTICE)

import check_idle, load_addon_settings, sleep_time

__addon__ = xbmcaddon.Addon()
__setting__ = __addon__.getSetting
__addon_id__ = __addon__.getAddonInfo('id')
__localize__ = __addon__.getLocalizedString


class MyMonitor( xbmc.Monitor ):
    def __init__( self, *args, **kwargs ):
        xbmc.Monitor.__init__( self )

    def onSettingsChanged( self ):
        load_addon_settings()

        
if __name__ == '__main__':
    monitor = MyMonitor()

    while not monitor.abortRequested():
        check_idle('InhibitIdleShutdown(true)', 'InhibitIdleShutdown(false)')
        if monitor.waitForAbort(float(sleep_time())):
            break
