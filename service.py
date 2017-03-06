#!/usr/bin/python

from __future__ import print_function

import xbmc
import xbmcaddon

import time
import check_idle


__addon__ = xbmcaddon.Addon()
__setting__ = __addon__.getSetting
__addon_id__ = __addon__.getAddonInfo('id')


class MyMonitor( xbmc.Monitor ):
    def __init__( self, *args, **kwargs ):
        xbmc.Monitor.__init__( self )

    def onSettingsChanged( self ):
        load_addon_settings()


def load_addon_settings():
    global sleep_time
    check_idle.prefix = __addon_id__
    
    try:
        sleep_time = int(__setting__('sleep'))
    except ValueError:
        sleep_time = 60

    try:
        check_idle.pvr_minsecs = int(float(__setting__('pvrwaketime')) * 60)
    except ValueError:
        check_idle.pvr_minsecs = 5 * 60

    try:
        check_idle.pvr_port = int(__setting__('pvrport'))
    except ValueError:
        check_idle.pvr_port = 34890

    try:
        if __setting__('pvrlocal') == 'false':
            check_idle.pvr_local = False
        else:
            check_idle.pvr_local = True
    except ValueError:
        check_idle.pvr_local = True

    check_idle.watched_local = check_idle.read_set(__setting__('localports'))
    check_idle.watched_remote = check_idle.read_set(__setting__('remoteports'))
    check_idle.watched_procs = check_idle.read_set(__setting__('procs'))

    check_idle.watched_local = check_idle.port_trans(check_idle.watched_local)
    check_idle.watched_remote = check_idle.port_trans(check_idle.watched_remote)

    xbmc.log(msg='[{}] Settings loaded.'.format(__addon_id__), level=xbmc.LOGNOTICE)

    return


if __name__ == '__main__':
    
    monitor = MyMonitor()
    xbmc.log(msg='[{}] Addon started.'.format(__addon_id__), level=xbmc.LOGNOTICE)
    load_addon_settings()

    while not monitor.abortRequested():
        state = check_idle.check_idle('InhibitIdleShutdown(true)', 'InhibitIdleShutdown(false)')
        #if state == 0:
        #    xbmc.log(msg='[{}] No background sctivities detected. Idle system may shutdown or suspend.'.format(__addon_id__), level=xbmc.LOGNOTICE)
        if monitor.waitForAbort(float(sleep_time)):
            break
