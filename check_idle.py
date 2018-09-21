#!/usr/bin/python
# -*- coding: utf-8 -*-

#
# Source https://github.com/bluecube/service.inhibit_shutdown
#
import xbmc
import xbmcaddon

#import psutil
import subprocess
import os

import time
import calendar
import _strptime
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

kodi = 'kodi'
#kodi = 'kodi-standalone'

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

    if idle_action:
        idle_action = idle_action.strip('\'\"')

    if busy_action:
        busy_action = busy_action.strip('\'\"')

    return idle_action, busy_action


def kodi_is_running():
    if active_proc(kodi):
        return True

    return False


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


def read_set(item, default):
    ret = set()
    for element in read_val(item, default).split(','):
        try:
            item = int(element)
        except ValueError:
            item = element.strip()
        ret.add(item)
    return ret


def read_val(item, default):
    try:
        value = int(__setting__(item))
    except ValueError:
        try:
            if __setting__(item).lower() == 'true' or __setting__(item).lower() == 'false':
                value = bool(__setting__(item).lower() == 'true')
            else:
                value = __setting__(item)
        except ValueError:
            value = default

    return value


def load_addon_settings():
    global sleep_time, watched_local, watched_remote, watched_procs, pvr_local, pvr_port, pvr_minsecs, busy_notification

    busy_notification = 'Notification({})'.format(__localize__(30008).encode('utf-8'))

    sleep_time     = read_val('sleep', 60)                    # 60 secs.
    pvr_minsecs    = read_val('pvrwaketime', 5) * 60          # 5 mins.
    pvr_port       = read_val('pvrport', 34890)               # VDR-VNSI
    pvr_local      = read_val('pvrlocal', True)               # PVR backend on local system

    watched_local  = read_set('localports', '445, 2049')      # smb, nfs, or 'set()' for empty set
    watched_remote = read_set('remoteports', '22, 445')       # ssh, smb
    watched_procs  = read_set('procs', 'HandBrakeCLI, ffmpeg, makemkv, makemkvcon')

    watched_local  = port_trans(watched_local)
    watched_remote = port_trans(watched_remote)

    if __name__ != '__main__':
        xbmc.log(msg='[{}] Settings loaded.'.format(__addon_id__), level=xbmc.LOGNOTICE)

    return


def get_sleep_time():
    return sleep_time


def jsonrpc_request(method, params=None, host='localhost', port=8080, username=None, password=None):
    # e.g. KodiJRPC_Get("PVR.GetProperties", {"properties": ["recording"]})

    url = 'http://{}:{}/jsonrpc'.format(host, port)
    header = {'Content-Type': 'application/json'}

    jsondata = {
        'jsonrpc': '2.0',
        'method': method,
        'id': method}

    if params:
        jsondata['params'] = params

    if username and password:
        base64str = base64.encodestring('{}:{}'.format(username, password))[:-1]
        header['Authorization'] = 'Basic {}'.format(base64str)

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
    clients = set()

    for conn in active_conns():
        #if conn.status != psutil.CONN_ESTABLISHED or not conn.raddr:
        if conn.status != 'ESTABLISHED' or not conn.raddr:
            continue

        if int(conn.laddr[1]) == port:
            if conn.raddr[0] != conn.laddr[0] or include_localhost:
                clients.add(conn.raddr[0])

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
            for i in range(len(timers)):
                starttime = int(calendar.timegm(time.strptime(timers[i]['starttime'], '%Y-%m-%d %H:%M:%S')))
                endtime = int(calendar.timegm(time.strptime(timers[i]['endtime'], '%Y-%m-%d %H:%M:%S')))
                now = int(calendar.timegm(time.gmtime()))

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


#def active_conns():
#    return psutil.net_connections(kind='tcp4')


from collections import namedtuple

def active_conns():
    my_env = os.environ.copy()
    my_env['LC_ALL'] = 'en_EN'
    netstat = subprocess.check_output(['netstat', '-tn'], universal_newlines=True, env=my_env)

    connections = []
    connection = namedtuple('connection', 'laddr raddr status')
    for line in netstat.split('\n')[2:]:
        if len(line) > 5:
            conn = connection(line.split()[3].rsplit(':', 1), line.split()[4].rsplit(':', 1), line.split()[5])
            connections.append(conn)

    return connections


#def active_proc(list):
#    for proc in psutil.process_iter(attrs=['pid', 'name']):
#        if proc.status() != psutil.STATUS_ZOMBIE and proc.info['name'].lower() in list:
#            return proc.info['name']
#
#    return None


def active_proc(list):
    response = subprocess.check_output(['ps', 'cax'], universal_newlines=True)
    procs = [line.split()[-1].lower() for line in response.split('\n')[1:] if line]
    for proc in procs:
       if proc in list:
           return proc

    return None


def check_procs():
    plist = [element.lower() for element in watched_procs]

    pname = active_proc(plist)
    if pname:
        if __name__ == '__main__':
            xbmc_log('Found active process of {}.'.format(pname))
        return True

    return False


def check_services():
    for conn in active_conns():
        #if conn.status != psutil.CONN_ESTABLISHED or not conn.raddr:
        if conn.status != 'ESTABLISHED' or not conn.raddr:
            continue

        if ((conn.laddr[0] != conn.raddr[0]) and (int(conn.laddr[1]) in watched_remote)) or \
           ((conn.laddr[0] == conn.raddr[0]) and (int(conn.laddr[1]) in watched_local)):
            if __name__ == '__main__':
                xbmc_log('Found active connection on port {}.'.format(conn.laddr[1]))
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
            xbmc_log('System is idle. Executing requested action: \'{}\'.'.format(arg_idle_action))
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
