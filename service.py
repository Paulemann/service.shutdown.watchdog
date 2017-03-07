#!/usr/bin/python

import xbmc
import xbmcaddon

from check_idle import check_idle


__addon__ = xbmcaddon.Addon()
__addon_id__ = __addon__.getAddonInfo('id')


class MyMonitor( xbmc.Monitor ):
    def __init__( self, *args, **kwargs ):
        xbmc.Monitor.__init__( self )

    def onSettingsChanged( self ):
        load_addon_settings()


def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


def port_trans(plist):
    PORT_DICT = {'ftp-data': 20, 'ftp':21, 'ssh':22, 'telnet':23, 'tftp':69, 'http':80, 'https':443, 'smb':445, 'lpd':515, 'rtps':554, 'ipsec':1293, 'l2tp':1701, 'lt2p-ipsec':1707, 'pptp':1723, 'nfs':2049, 'upnp':5000, 'rtp':5004, 'rtcp':5005, 'kodi-web':8080, 'hts':9981, 'tvh':9983, 'vnsi-server':34890}

    ret = set()
    for p in plist:
        if is_number(p):
            ret.add(int(p))
        else:
            try:
                ret.add(int(PORT_DICT[p.lower()]))
            except:
                continue
    return ret


def read_set(string):
    ret = set()
    for element in string.split(','):
        try:
            item = int(element)
        except ValueError:
            item = element.strip()
        ret.add(item)
    return ret


def load_addon_settings():
    global sleep_time, watched_local, watched_remote, watched_procs, pvr_local, pvr_port, pvr_minsecs, busy_notification

    #busy_notification = 'Notification(Action cancelled, Background activities detected)'
    #busy_notification = 'Notification(Aktion abgebrochen, Hintergrundaktivitäten festgestellt)'
    busy_notification = 'Notification(' + __localize__('30008') + ')'

    try:
        sleep_time = int(__setting__('sleep'))
    except ValueError:
        sleep_time = 60

    try:
        pvr_minsecs = int(float(__setting__('pvrwaketime')) * 60)
    except ValueError:
        pvr_minsecs = 5 * 60

    try:
        pvr_port = int(__setting__('pvrport'))
    except ValueError:
        pvr_port = 34890

    try:
        if __setting__('pvrlocal') == 'false':
            pvr_local = False
        else:
            pvr_local = True
    except ValueError:
        pvr_local = True

    try:
        watched_local = read_set(__setting__('localports'))
    except:
        watched_local = {445, 2049}      #smb, nfs, or 'set()' for empty set

    try:
        watched_remote = read_set(__setting__('remoteports'))
    except:
        watched_remote = {22, 445}       #ssh, smb

    try:
        watched_procs = read_set(__setting__('procs'))
    except:
        watched_procs = {'HandBrakeCLI', 'ffmpeg', 'makemkv' , 'makemkvcon'}

    watched_local = port_trans(watched_local)
    watched_remote = port_trans(watched_remote)

    xbmc.log(msg='[{}] Settings loaded.'.format(__addon_id__), level=xbmc.LOGNOTICE)

    return


if __name__ == '__main__':
    monitor = MyMonitor()
    xbmc.log(msg='[{}] Addon started.'.format(__addon_id__), level=xbmc.LOGNOTICE)
    load_addon_settings()

    while not monitor.abortRequested():
        #xbmc.ExecuteBuiltIn('RunnScript...')
        check_idle('InhibitIdleShutdown(true)', 'InhibitIdleShutdown(false)')
        if monitor.waitForAbort(float(sleep_time)):
            break
