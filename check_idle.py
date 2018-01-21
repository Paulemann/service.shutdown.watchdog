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
        opts, args = getopt.getopt(sys.argv[1:], "i:b:", ["idle-action=", "busy-action="])
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


def kodi_is_running():
    try:
        pid = subprocess.check_output(['pgrep', 'kodi-standalone'])

    except subprocess.CalledProcessError:
        return False

    return True


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

    busy_notification = 'Notification({})'.format(__localize__(30008).encode('utf-8'))

    try:
        sleep_time = int(__setting__('sleep'))
    except ValueError:
        sleep_time = 60  # 1 min.

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

    if __name__ != '__main__':
        xbmc.log(msg='[{}] Settings loaded.'.format(__addon_id__), level=xbmc.LOGNOTICE)

    return


def get_sleep_time():
    return sleep_time


def jsonrpc_request(method, params=None, host='localhost', port=8080):
    # e.g. KodiJRPC_Get("PVR.GetProperties", {"properties": ["recording"]})

    url = 'http://{}:{}/jsonrpc'.format(host, port)
    header = {'Content-Type': 'application/json'}

    jsondata = {
        'jsonrpc': '2.0',
        'method': method,
        'id': method}

    if params:
        jsondata['params'] = params

    try:
        if host == 'localhost':
            response = xbmc.executeJSONRPC(json.dumps(jsondata))
            data = json.loads(response.decode('utf-8','mixed'))

            if data['id'] == method and data.has_key('result'):
                return data['result']
        else:
            request = urllib2.Request(url, json.dumps(jsondata), header)
            with closing(urllib2.urlopen(request)) as response:
                data = json.loads(response.read().decode('utf8', 'mixed'))

                if data['id'] == method and data.has_key('result'):
                    return data['result']

    except:
        pass

    return False


def find_clients(port, include_localhost):
    #clients = set()
    clients = []

    my_env = os.environ.copy()
    my_env['LC_ALL'] = 'en_EN'
    netstat = subprocess.check_output(['netstat', '-t', '-n'], universal_newlines=True, env=my_env)

    for line in netstat.split('\n')[2:]:
        items = line.split()
        if len(items) < 6 or (items[5] != 'ESTABLISHED'):
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
    if not pvr_local:
        return False

    for client in find_clients(pvr_port, False): # enumerate PVR clients, exclude localhost
        try:
            player = jsonrpc_request('Player.GetActivePlayers', host=client)

            if player and player[0]['type'] == 'video':
                data = jsonrpc_request('Player.GetItem', params={'properties': ['title', 'file'],'playerid': 1}, host=client)

                if data and data['item']['type'] == 'channel':
                    if __name__ == '__main__':
                        xbmc_log('Found client {} watching live tv.'.format(client))
                    return True # a client is watching live-tv
                elif data and 'pvr://' == urllib2.unquote(data['item']['file'].encode('utf-8'))[:6]:
                    if __name__ == '__main__':
                        xbmc_log('Found client {} watching a recording.'.format(client))
                    return True # a client is watching a recording

        except KeyError:
            pass

    return False


def check_timers():
    if not pvr_local:
        return False

    localhost = '127.0.0.1'

    if localhost not in find_clients(pvr_port, True):
        return False

    data = jsonrpc_request('PVR.GetTimers', params={'properties': ['title', 'starttime', 'endtime']})

    try:
        if data:
            timers = data['timers']
            for i in range(0, len(timers)-1):
                starttime = int(time.mktime(time.strptime(timers[i]['starttime'], '%Y-%m-%d %H:%M:%S')))
                endtime = int(time.mktime(time.strptime(timers[i]['endtime'], '%Y-%m-%d %H:%M:%S')))
                now = int(time.mktime(time.gmtime()))

                if starttime <= 0 or endtime <= now:
                    continue
                else:
                    secs_before_recording = starttime - now

                if secs_before_recording > 0 and secs_before_recording < pvr_minsecs:
                    if __name__ == '__main__':
                        xbmc_log('Recording about to start in less than {} seconds.'.format(pvr_minsecs))
                    return True

                if secs_before_recording < 0:
                    if __name__ == '__main__':
                        xbmc_log('Found active recording.')
                    return True

    # Sometimes we get a key error, maybe beacause pvr backend
    # is not responding or busy.
    except KeyError:
        pass

    return False


def check_procs():
    procs = subprocess.check_output(['ps', 'cax'], universal_newlines=True)

    lines = procs.split('\n')[1:]

    for line in lines:
        items = line.split()
        if len(items) < 5:
            continue

        proc = items[4];
        #if proc in watched_procs:
        if proc.lower() in [element.lower() for element in watched_procs]:
            if __name__ == '__main__':
                xbmc_log('Found active process of {}.'.format(proc))
            return True

    return False


def check_services():
    my_env = os.environ.copy()
    my_env['LC_ALL'] = 'en_EN'
    netstat = subprocess.check_output(['netstat', '-t', '-n'], universal_newlines=True, env=my_env)

    lines = netstat.split('\n')[2:]

    for line in lines:
        items = line.split()
        if len(items) < 6 or (items[5] != 'ESTABLISHED'):
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
            if __name__ == '__main__':
                xbmc_log('Found active connection on port {}.'.format(local_port))
            return True

    return False


def check_idle(arg_idle_action, arg_busy_action):
    if check_pvrclients() or check_timers() or check_services() or check_procs():
        if arg_busy_action:
            xbmc.executebuiltin(arg_busy_action)
        elif arg_idle_action:
            xbmc.executebuiltin(busy_notification)
            if __name__ == '__main__':
                xbmc_log('Action \'{}\' cancelled. Background activities detected.'.format(arg_idle_action))
    else:
        if arg_idle_action:
            xbmc.executebuiltin(arg_idle_action)
    return


def xbmc_log(text):
    xbmc.log(msg='[{}] {}'.format(__addon_id__, text), level=xbmc.LOGNOTICE)


if __name__ == '__main__':
    if not kodi_is_running():
        sys.exit()
    xbmc_log('RunScript action started.')
    load_addon_settings()
    check_idle(*get_opts())
else:
    xbmc_log('Addon started.')
    load_addon_settings()
