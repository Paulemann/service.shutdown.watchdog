#!/usr/bin/python
# -*- coding: utf-8 -*-

#
# Source https://github.com/bluecube/service.inhibit_shutdown
#
import xbmc
import xbmcaddon

import subprocess
import os
import time
import sys
import getopt

import json
import urllib2
from contextlib import closing

import codecs


__addon__ = xbmcaddon.Addon()
__setting__ = __addon__.getSetting
__addon_id__ = __addon__.getAddonInfo('id')
__localize__ = __addon__.getLocalizedString


#
# Source: http://stackoverflow.com/questions/10009753/python-dealing-with-mixed-encoding-files
#
def mixed_decoder(unicode_error):
    err_str = unicode_error[1]
    err_len = unicode_error.end - unicode_error.start
    next_position = unicode_error.start + err_len
    replacement = err_str[unicode_error.start:unicode_error.end].decode('cp1252')

    return u'%s' % replacement, next_position


codecs.register_error('mixed', mixed_decoder)


def get_opts():
    idle_action = ''
    busy_action = ''
    
    try:
        opts, args = getopt.getopt(sys.argv[1:], "i:b:?", ["idle-action=", "busy-action=", "help"])
    except getopt.GetoptError, err:
        return

    for opt, arg in opts:
        if opt in ("-i", "--idle-action"):
            idle_action = arg
        elif opt in ("-b", "--busy-action"):
            busy_action = arg

    if len(args) == 1 and not idle_action:
        idle_action = args[0]

    if idle_action and ((idle_action[0] == '\'' and idle_action[-1] == '\'') or (idle_action[0] == '\"' and idle_action[-1] == '\"')):
        idle_action = idle_action[1:-1]

    if busy_action and ((busy_action[0] == '\'' and busy_action[-1] == '\'') or (busy_action[0] == '\"' and busy_action[-1] == '\"')):
        busy_action = busy_action[1:-1]

    return idle_action, busy_action 


def get_pid(name):
    try:
        pid = subprocess.check_output(['pidof', name])
    except subprocess.CalledProcessError:
        pid = []

    return pid


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
    global sleep_interval, watched_local, watched_remote, watched_procs, pvr_local, pvr_port, pvr_minsecs, busy_notification

    busy_notification = 'Notification({})'.format(__localize__(30008).encode('utf-8'))

    try:
        sleep_interval = int(__setting__('sleep'))
    except ValueError:
        sleep_interval = 60  # 1 min.

    try:
        pvr_minsecs = int(float(__setting__('pvrwaketime')) * 60)
    except ValueError:
        pvr_minsecs = 300 # 5 mins.

    try:
        pvr_port = int(__setting__('pvrport'))
    except ValueErrror:
        pvr_port = 34890  # VDR-VNSI

    try:
        pvr_local = True if __setting__('pvrlocal').lower() == 'true' else False
    except:
        pvr_local = True  # PVR backend on local system

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
    
    return


def sleep_time():
    return sleep_interval


def json_request(kodi_request, host):
    # http://host:8080/jsonrpc?request=kodi_request

    PORT   =    8080
    URL    =    'http://' + host + ':' + str(PORT) + '/jsonrpc'
    HEADER =    {'Content-Type': 'application/json'}

    if host == 'localhost':
        response = xbmc.executeJSONRPC(json.dumps(kodi_request))
        if response:
            return json.loads(response.decode('utf8','mixed'))

    request = urllib2.Request(URL, json.dumps(kodi_request), HEADER)
    with closing(urllib2.urlopen(request)) as response:
        return json.loads(response.read().decode('utf8', 'mixed'))


def find_clients(port, include_localhost):
    #clients = set()
    clients = []

    netstat = subprocess.check_output(['/bin/netstat', '-t', '-n'], universal_newlines=True)

    for line in netstat.split('\n')[2:]:
        items = line.split()
        if len(items) < 6 or (items[5] != 'VERBUNDEN' and items[5] != 'ESTABLISHED'):
            continue

        local_addr, local_port = items[3].rsplit(':', 1)
        remote_addr, remote_port = items[4].rsplit(':', 1)

        if local_addr[0] == '[' and local_addr[-1] == ']':
            local_addr = local_addr[1:-1]

        if remote_addr[0] == '[' and remote_addr[-1] == ']':
            remote_addr = remote_addr[1:-1]

        local_port = int(local_port)

        if local_port == port:
            if remote_addr not in clients:
                if remote_addr != local_addr or include_localhost:
                    #clients.add(remote_addr) # doesn't require "if remote_addr not in clients:"
                    clients.append(remote_addr)

    return clients


def check_pvrclients():
    if not pvr_local or not get_pid('kodi.bin'):
        return False

    GET_PLAYER = {
        'jsonrpc': '2.0',
        'method': 'Player.GetActivePlayers',
        'id': 1
    }

    GET_ITEM = {
        'jsonrpc': '2.0',
        'method': 'Player.GetItem',
        'params': {
            'properties': ['title', 'file'],
            'playerid': 1
        },
        'id': 'VideoGetItem'
    }

    for client in find_clients(pvr_port, False): # enumerate PVR clients, exclude localhost
        try:
            data = json_request(GET_PLAYER, client)
            if data['result'] and data['result'][0]['type'] == 'video':
                data = json_request(GET_ITEM, client)

                if  data['result']['item']['type'] == 'channel':
                    return True # a client is watching live-tv
                elif 'pvr://' == urllib2.unquote(data['result']['item']['file'].encode('utf-8'))[:6]:
                    return True # a client is watching a recording

        except:
            continue

    return False


def check_timers():
    if not pvr_local or not get_pid('kodi.bin'):
        return False

    localhost = '127.0.0.1'

    if localhost not in find_clients(pvr_port, True):
        return False

    #if int(subprocess.check_output(['/bin/pidof', '-s', 'vdr'])) > 0:
    #   return False

    GET_TIMERS = {
        'jsonrpc': '2.0',
        'method': 'PVR.GetTimers',
        'params': {
            'properties': ['title', 'starttime', 'endtime']
        },
        'id': 1
    }
    data = json_request(GET_TIMERS, 'localhost')

    try:
        if data['result']:
            list = data['result']['timers']
            for i in range(0, len(list)-1):
                starttime = int(time.mktime(time.strptime(list[i]['starttime'], '%Y-%m-%d %H:%M:%S')))
                endtime = int(time.mktime(time.strptime(list[i]['endtime'], '%Y-%m-%d %H:%M:%S')))
                now = int(time.mktime(time.gmtime()))

                if starttime <= 0 or endtime <= now:
                    continue
                else:
                    secs_before_recording = starttime - now

                if secs_before_recording > 0 and secs_before_recording < pvr_minsecs:
                    return True

                if secs_before_recording < 0:
                    return True

    # Sometimes we get a key error, maybe beacause pvr backend 
    # is not responding or busy.
    except KeyError:
        pass

    return False


def check_procs():
    procs = subprocess.check_output(['/bin/ps', 'cax'], universal_newlines=True)

    for line in procs.split('\n')[1:]:
        items = line.split()
        if len(items) < 5:
            continue

        proc = items[4];
        #if proc in watched_procs:
        if proc.lower() in [element.lower() for element in watched_procs]:
            return True

    return False


def check_services():
    netstat = subprocess.check_output(['/bin/netstat', '-t', '-n'], universal_newlines=True)

    for line in netstat.split('\n')[2:]:
        items = line.split()
        if len(items) < 6 or (items[5] != 'VERBUNDEN' and items[5] != 'ESTABLISHED'):
            continue

        local_addr, local_port = items[3].rsplit(':', 1)
        remote_addr, remote_port = items[4].rsplit(':', 1)

        if local_addr[0] == '[' and local_addr[-1] == ']':
            local_addr = local_addr[1:-1]

        if remote_addr[0] == '[' and remote_addr[-1] == ']':
            remote_addr = remote_addr[1:-1]

        local_port = int(local_port)

        if ((local_addr != remote_addr) and (local_port in watched_remote)) or \
            ((local_addr == remote_addr) and (local_port in watched_local)):
            return True

    return False


def check_idle(arg_idle_action, arg_busy_action):
    if check_pvrclients() or check_timers() or check_services() or check_procs():
        if arg_busy_action:
            xbmc.executebuiltin(arg_busy_action)
        elif arg_idle_action:
            xbmc.executebuiltin(busy_notification)
            xbmc.log(msg='[{}] Action \'{}\' cancelled. Background activities detected.'.format(__addon_id__, arg_idle_action), level=xbmc.LOGNOTICE)
    else:
        if arg_idle_action:
            xbmc.executebuiltin(arg_idle_action)
    return


load_addon_settings()


if __name__ == '__main__':
    idle_action, busy_action = get_opts()
    sys.exit(check_idle(idle_action, busy_action))
