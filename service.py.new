#!/usr/bin/python

import xbmc
import xbmcaddon

from check_idle import check_idle, load_addon_settings, sleep_time


__addon__ = xbmcaddon.Addon()
__addon_id__ = __addon__.getAddonInfo('id')


class MyMonitor( xbmc.Monitor ):
    def __init__( self, *args, **kwargs ):
        xbmc.Monitor.__init__( self )

    def onSettingsChanged( self ):
        load_addon_settings()


if __name__ == '__main__':
    monitor = MyMonitor()
    xbmc.log(msg='[{}] Addon started.'.format(__addon_id__), level=xbmc.LOGNOTICE)
    load_addon_settings()

    while not monitor.abortRequested():
        state = check_idle('InhibitIdleShutdown(true)', 'InhibitIdleShutdown(false)')
        #if state == 0:
        #    xbmc.log(msg='[{}] No background sctivities detected. Idle system may shutdown or suspend.'.format(addon.getAddonInfo('id')), level=xbmc.LOGNOTICE)
        if monitor.waitForAbort(float(sleep_time)):
            break
