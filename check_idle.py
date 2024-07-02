#!/usr/bin/python
# -*- coding: utf-8 -*-

import xbmc
import xbmcaddon

#import psutil
import subprocess
import os
import base64

import time
import calendar
import _strptime
import sys
import getopt
import requests
import json
import codecs

try:
    from urllib.parse import unquote
except ImportError:
    from urllib2 import unquote

if sys.version_info.major < 3:
    INFO = xbmc.LOGNOTICE
else:
    INFO = xbmc.LOGINFO
DEBUG = xbmc.LOGDEBUG


__addon__    = xbmcaddon.Addon()
__setting__  = __addon__.getSetting
__addon_id__ = __addon__.getAddonInfo('id')
__localize__ = __addon__.getLocalizedString

kodi = 'kodi'
#kodi = 'kodi-standalone'


#
# Source https://github.com/bluecube/service.inhibit_shutdown
#

def translate(id):
    if sys.version_info.major < 3:
        return __localize__(id).encode('utf-8')
    else:
        return __localize__(id)


busy_notification = 'Notification({})'.format(translate(30008))


def get_opts():
    idle_action = ''
    busy_action = ''

    try:
        opts, args = getopt.getopt(sys.argv[1:], "i:b:", ["idle-action=", "busy-action="])
    except getopt.GetoptError as err:
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
    for element in str(read_val(item, default)).split(','):
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
    global do_cecstandby, rpc_port, rpc_username, rpc_password, sleep_time, watched_local, watched_remote, watched_procs, pvr_local, pvr_port, pvr_minsecs, nostdby_on_idle_pvrclient

    do_cecstandby             = read_val('cecstandby', False)            # Always send conn. devices to standby: False

    rpc_port                  = read_val('rpcport', 8080)                # Port for RPC
    rpc_username              = read_val('username', None)               # Username for RPC
    rpc_password              = read_val ('password', None)              # Password for RPC

    sleep_time                = read_val('sleep', 60)                    # 60 secs.
    pvr_minsecs               = read_val('pvrwaketime', 5) * 60          # 5 mins.
    pvr_port                  = read_val('pvrport', 34890)               # VDR-VNSI
    pvr_local                 = read_val('pvrlocal', True)               # PVR backend on local system: True
    nostdby_on_idle_pvrclient = read_val('pvridle', False)               # Keep system awake even for idle pvr clients: False

    watched_local             = read_set('localports', '445, 2049')      # smb, nfs, or 'set()' for empty set
    watched_remote            = read_set('remoteports', '22, 445')       # ssh, smb
    watched_procs             = read_set('procs', 'HandBrakeCLI, ffmpeg, makemkv, makemkvcon')

    watched_local  = port_trans(watched_local)
    watched_remote = port_trans(watched_remote)

    if __name__ != '__main__':
        xbmc_log('Settings loaded.')

    return


def get_sleep_time():
    return sleep_time


def utfy_dict(dic):
    if not sys.version_info.major < 3:
       return dic

    if isinstance(dic,unicode):
        return dic.encode("utf-8")
    elif isinstance(dic,dict):
        for key in dic:
            dic[key] = utfy_dict(dic[key])
        return dic
    elif isinstance(dic,list):
        new_l = []
        for e in dic:
            new_l.append(utfy_dict(e))
        return new_l
    else:
        return dic


#def mixed_decoder(error: UnicodeError) -> (str, int):
#     bs: bytes = error.object[error.start: error.end]
#     return bs.decode("cp1252"), error.start + 1

def mixed_decoder(unicode_error):
    err_str = unicode_error[1]
    err_len = unicode_error.end - unicode_error.start
    next_position = unicode_error.start + err_len
    replacement = err_str[unicode_error.start:unicode_error.end].decode('cp1252')

    if sys.version_info.major < 3:
        return u'%s' % replacement, next_position
    else:
        return '%s' % replacement, next_position

codecs.register_error('mixed', mixed_decoder)


def jsonrpc_request(method, host='localhost', params=None, port=8080, username=None, password=None):
    url     =    'http://{}:{}/jsonrpc'.format(host, port)
    headers =    {'Content-Type': 'application/json'}

    xbmc.log(msg='[{}] Initializing RPC request to host {} with method \'{}\'.'.format(__addon_id__, host, method), level=DEBUG)

    jsondata = {
        'jsonrpc': '2.0',
        'method': method,
        'id': method}

    if params:
        jsondata['params'] = params

    if username and password:
        auth_str = '{}:{}'.format(username, password)
        try:
            base64str = base64.encodestring(auth_str)[:-1]
        except:
            base64str = base64.b64encode(auth_str.encode()).decode()
        headers['Authorization'] = 'Basic {}'.format(base64str)

    try:
        if host in ['localhost', '127.0.0.1']:
            response = xbmc.executeJSONRPC(json.dumps(jsondata))
            if sys.version_info.major < 3:
                data = json.loads(response.decode('utf-8', 'mixed'))
            else:
                data = json.loads(response)
        else:
            response = requests.post(url, data=json.dumps(jsondata), headers=headers)
            if not response.ok:
                xbmc.log(msg='[{}] RPC request to host {} failed with status \'{}\'.'.format(__addon_id__, host, response.status_code), level=INFO)
                return None

            if sys.version_info.major < 3:
                data = json.loads(response.content.decode('utf-8', 'mixed'))
            else:
                data = json.loads(response.text)

        if data['id'] == method and 'result' in data:
            xbmc.log(msg='[{}] RPC request to host {} returns data \'{}\'.'.format(__addon_id__, host, data['result']), level=DEBUG)
            return utfy_dict(data['result'])

    except Exception as e:
        xbmc.log(msg='[{}] RPC request to host {} failed with error \'{}\'.'.format(__addon_id__, host, str(e)), level=INFO)
        pass

    return None


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
    global busy_notification

    if not pvr_local:
        return False

    for client in find_clients(pvr_port, False): # enumerate PVR clients, exclude localhost
        player = jsonrpc_request('Player.GetActivePlayers', host=client, port=rpc_port, username=rpc_username, password=rpc_password)

        if not player:
            xbmc_log('Unable to request player info. Check if rpc control is allowed on host {}.'.format(client))
            continue

        try:
            if player and player[0]['type'] == 'video':
                data = jsonrpc_request('Player.GetItem', params={'properties': ['title', 'file'],'playerid': 1}, host=client, port = rpc_port, username=rpc_username, password=rpc_password)

                if data and data['item']['type'] == 'channel':
                    busy_notification = busy_notification.format(translate(30009))
                    if __name__ == '__main__':
                        xbmc_log('Found pvr client {} watching live tv.'.format(client))
                    return True # a pvr client is watching live-tv
                elif data and 'pvr://' == unquote(data['item']['file'])[:6]:
                    busy_notification = busy_notification.format(translate(30010))
                    if __name__ == '__main__':
                        xbmc_log('Found pvr client {} watching a recording.'.format(client))
                    return True # a pvr client is watching a recording
            else: #NEW
                if nostdby_on_idle_pvrclient:
                    busy_notification = busy_notification.format(translate(30019))
                    if __name__ == '__main__':
                        xbmc_log('Found pvr client {} in idle state.'.format(client))
                    return True # keep system awake even as long as any pvr client is connected

        except KeyError:
            pass

    return False


def check_timers():
    global busy_notification

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
                    busy_notification = busy_notification.format(translate(30011))
                    if __name__ == '__main__':
                        xbmc_log('Recording about to start in less than {} seconds.'.format(pvr_minsecs))
                    return True

                if secs_before_recording < 0:
                    busy_notification = busy_notification.format(translate(30012))
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
    global busy_notification

    plist = [element.lower() for element in watched_procs]

    pname = active_proc(plist)
    if pname:
        busy_notification = busy_notification.format(translate(30013))
        busy_notification = busy_notification.format(pname)
        if __name__ == '__main__':
            xbmc_log('Found active process of {}.'.format(pname))
        return True

    return False


def check_services():
    global busy_notification

    for conn in active_conns():
        #if conn.status != psutil.CONN_ESTABLISHED or not conn.raddr:
        if conn.status != 'ESTABLISHED' or not conn.raddr:
            continue

        if ((conn.laddr[0] != conn.raddr[0]) and (int(conn.laddr[1]) in watched_remote)) or \
           ((conn.laddr[0] == conn.raddr[0]) and (int(conn.laddr[1]) in watched_local)):
            busy_notification = busy_notification.format(translate(30014))
            busy_notification = busy_notification.format(conn.laddr[1])
            if __name__ == '__main__':
                xbmc_log('Found active connection on port {}.'.format(conn.laddr[1]))
            return True

    return False


def check_idle(arg_idle_action, arg_busy_action):
    standby_actions = ['suspend', 'shutdown', 'hibernate', 'powerdown']

    if check_pvrclients() or check_timers() or check_services() or check_procs():
        if arg_busy_action:
            xbmc.executebuiltin(arg_busy_action)
        elif arg_idle_action:
            xbmc.executebuiltin(busy_notification)
            if (arg_idle_action.lower() in standby_actions) and do_cecstandby:
                if xbmc.Player().isPlaying():
                    xbmc.executebuiltin('PlayerControl(Stop)')
                time.sleep(3)
                xbmc.executebuiltin('CECStandby')
            if __name__ == '__main__':
                xbmc_log('Action \'{}\' cancelled. Background activities detected.'.format(arg_idle_action))
    else:
        if arg_idle_action:
            xbmc_log('System is idle. Executing requested action: \'{}\'.'.format(arg_idle_action))
            xbmc.executebuiltin(arg_idle_action)
    return


def xbmc_log(text):
    xbmc.log(msg='[{}] {}'.format(__addon_id__, text), level=INFO)


if __name__ == '__main__':
    if not kodi_is_running():
        sys.exit()
    xbmc_log('RunScript action started.')
    load_addon_settings()
    check_idle(*get_opts())
else:
    xbmc_log('Addon started.')
    load_addon_settings()
