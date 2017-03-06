#!/usr/bin/python

from __future__ import print_function

import xbmc
import xbmcaddon

import time
import check_idle


class MyMonitor( xbmc.Monitor ):
    def __init__( self, *args, **kwargs ):
        xbmc.Monitor.__init__( self )

    def onSettingsChanged( self ):
        load_addon_settings()


def load_addon_settings():
    global sleep_time
    check_idle.prefix = addon.getAddonInfo('id')

    s = addon.getSetting

    try:
        sleep_time = int(float(s('sleep')) * 1000)
    except ValueError:
        sleep_time = 60 * 1000

    try:
        check_idle.pvr_minsecs = int(float(s('pvrwaketime')) * 60)
    except ValueError:
        check_idle.pvr_minsecs = 5 * 60

    try:
        check_idle.pvr_port = int(s('pvrport'))
    except ValueError:
        check_idle.pvr_port = 34890

    try:
        if s('pvrlocal') == 'false':
            check_idle.pvr_local = False
        else:
            check_idle.pvr_local = True
    except ValueError:
        check_idle.pvr_local = True

    check_idle.watched_local = check_idle.read_set(s('localports'))
    check_idle.watched_remote = check_idle.read_set(s('remoteports'))
    check_idle.watched_procs = check_idle.read_set(s('procs'))

    check_idle.watched_local = check_idle.port_trans(check_idle.watched_local)
    check_idle.watched_remote = check_idle.port_trans(check_idle.watched_remote)

    xbmc.log(msg='[{}] Settings loaded.'.format(addon.getAddonInfo('id')), level=xbmc.LOGNOTICE)

    return


if __name__ == '__main__':
    addon = xbmcaddon.Addon()
    monitor = MyMonitor()
    xbmc.log(msg='[{}] Addon started.'.format(addon.getAddonInfo('id')), level=xbmc.LOGNOTICE)
    load_addon_settings()

    while not monitor.abortRequested():
        #state = check_idle.check_idle('InhibitIdleShutdown(false)', None)
        state = check_idle.check_idle('InhibitIdleShutdown(true)', 'InhibitIdleShutdown(false)')
        #if state == 0:
        #    xbmc.log(msg='[{}] No background sctivities detected. Idle system may shutdown or suspend.'.format(addon.getAddonInfo('id')), level=xbmc.LOGNOTICE)
        if monitor.waitForAbort(float(sleep_time) / 1000.0):
            break
