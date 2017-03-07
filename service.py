#!/usr/bin/python

import sys
import xbmc
import xbmcaddon

from check_idle import check_idle


__addon__ = xbmcaddon.Addon()
__setting__ = __addon__.getSetting
__addon_id__ = __addon__.getAddonInfo('id')


class MyMonitor( xbmc.Monitor ):
    def __init__( self, *args, **kwargs ):
        xbmc.Monitor.__init__( self )

    def onSettingsChanged( self ):
        load_settings()


def load_settings():
    try:
        sleep_time = int(__setting__('sleep'))
    except ValueError:
        xbmc.log(msg='[{}] Error loading settings. Abort.'.format(__addon_id__), level=xbmc.LOGNOTICE)
        return False

    xbmc.log(msg='[{}] Settings loaded.'.format(__addon_id__), level=xbmc.LOGNOTICE)
    return True


if __name__ == '__main__':
    monitor = MyMonitor()
    xbmc.log(msg='[{}] Addon started.'.format(__addon_id__), level=xbmc.LOGNOTICE)

    if not load_settings()
        sys.exit(1)

    while not monitor.abortRequested():
        #cmd = 'RunScript(' + __addon_id__ + '\'InhibitIdleShutdown(true)\', \'InhibitIdleShutdown(false)\')'
        #xbmc.executebuiltin(cmd)
        check_idle('InhibitIdleShutdown(true)', 'InhibitIdleShutdown(false)')
        if monitor.waitForAbort(float(sleep_time)):
            break
            
    sys.exit(0)
