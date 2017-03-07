#!/usr/bin/python
# -*- coding: utf-8 -*-

import xbmc
import xbmcaddon

import check_idle


__addon__ = xbmcaddon.Addon()
__setting__ = __addon__.getSetting
__addon_id__ = __addon__.getAddonInfo('id')
__localize__ = __addon__.getLocalizedString


class MyMonitor( xbmc.Monitor ):
    def __init__( self, *args, **kwargs ):
        xbmc.Monitor.__init__( self )

    def onSettingsChanged( self ):
        load_addon_settings()


def load_addon_settings():
    global sleep_time

    try:
        sleep_time = int(__setting__('sleep'))
    except ValueError:
        sleep_time = 60  # 1 min.

    check_idle.busy_notification = 'Notification(' + __localize__(30008) + ')'

    try:
        check_idle.pvr_minsecs = int(float(__setting__('pvrwaketime')) * 60)
    except ValueError:
        check_idle.pvr_minsecs = 300  # 5 mins.

    try:
        check_idle.pvr_port = int(__setting__('pvrport'))
    except ValueErrror:
        check_idle.pvr_port = 34890  # VDR-VNSI

    try:
        check_idle.pvr_local = True if __setting__('pvrlocal').lower() == 'true' else False
    except:
        check_idle.pvr_local = True  # PVR backend on local system

    try:
        check_idle.watched_local = check_idle.read_set(__setting__('localports'))
    except:
        check_idle.watched_local = {445, 2049}  #smb, nfs, or 'set()' for empty set

    try:
        check_idle.watched_remote = check_idle.read_set(__setting__('remoteports'))
    except:
        check_idle.watched_remote = {22, 445}   #ssh, smb

    try:
        check_idle.watched_procs = check_idle.read_set(__setting__('procs'))
    except:
        check_idle.watched_procs = {'HandBrakeCLI', 'ffmpeg', 'makemkv' , 'makemkvcon'}

    check_idle.watched_local = check_idle.port_trans(check_idle.watched_local)
    check_idle.watched_remote = check_idle.port_trans(check_idle.watched_remote)

    xbmc.log(msg='[{}] Settings loaded.'.format(__addon_id__), level=xbmc.LOGNOTICE)

    return


if __name__ == '__main__':
    monitor = MyMonitor()
    xbmc.log(msg='[{}] Addon started.'.format(__addon_id__), level=xbmc.LOGNOTICE)

    load_addon_settings()

    while not monitor.abortRequested():
        #cmd = 'RunScript(' + __addon_id__ + '\'InhibitIdleShutdown(true)\', \'InhibitIdleShutdown(false)\')'
        #xbmc.executebuiltin(cmd)
        check_idle.check_idle('InhibitIdleShutdown(true)', 'InhibitIdleShutdown(false)')
        if monitor.waitForAbort(float(sleep_time)):
            break
