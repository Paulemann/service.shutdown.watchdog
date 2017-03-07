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
        load_addon_settings()


def load_addon_settings():
    try:
        sleep_time = int(__setting__('sleep'))
    except ValueError:
        sleep_time = 60

    xbmc.log(msg='[{}] Settings loaded.'.format(__addon_id__), level=xbmc.LOGNOTICE)

    return


if __name__ == '__main__':
    monitor = MyMonitor()
    xbmc.log(msg='[{}] Addon started.'.format(__addon_id__), level=xbmc.LOGNOTICE)

    load_addon_settings()

    while not monitor.abortRequested():
        #cmd = 'RunScript(' + __addon_id__ + '\'InhibitIdleShutdown(true)\', \'InhibitIdleShutdown(false)\')'
        #xbmc.executebuiltin(cmd)
        check_idle('InhibitIdleShutdown(true)', 'InhibitIdleShutdown(false)')
        if monitor.waitForAbort(float(sleep_time)):
            break
