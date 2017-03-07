#!/usr/bin/python

import xbmc
import xbmcaddon

from check_idle import check_idle


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
    xbmc.log(msg='[{}] Addon started.'.format(__addon_id__), level=xbmc.LOGNOTICE)

    try:
        sleep_time = int(__setting__('sleep'))
    except ValueError:
        sleep_time = 300   # default: check every 5 mins.
    xbmc.log(msg='[{}] Settings loaded.'.format(__addon_id__), level=xbmc.LOGNOTICE)

    while not monitor.abortRequested():
        #cmd = 'RunScript(' + __addon_id__ + '\'InhibitIdleShutdown(true)\', \'InhibitIdleShutdown(false)\')'
        #xbmc.executebuiltin(cmd)
        check_idle('InhibitIdleShutdown(true)', 'InhibitIdleShutdown(false)')
        if monitor.waitForAbort(float(sleep_time)):
            break
