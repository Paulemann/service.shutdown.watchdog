#!/usr/bin/python
# -*- coding: utf-8 -*-

# run standalone as check_idle.py
# or from main script do:
#import check_idle
#check_idle.check_idle(busy_action, idle_action)

#
# Source https://github.com/bluecube/service.inhibit_shutdown
#
from __future__ import print_function

import xbmc
import subprocess

import os
import time
import sys
import getopt
from socket import *

import json
import urllib2
from contextlib import closing

import codecs

try:
    from xbmc.xbmcclient import *
except:
    sys.exc_clear()
    #pass
    # we may ignore the exception
    # since the module is not required in this case

from lxml import etree

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


def usage():
    print('Usage: {} [OPTION]'.format(os.path.basename(sys.argv[0])))
    print('Check system for configured background activities. Optionally, send action to kodi depending on current state (idle/busy).')
    print('\nExit status: \t0 (No background activities detected) or \n\t\t1 (Backgroung activities detected)')
    print('\nMonitored background activities are defined in \'settings.xml\' if addon is intalled.')
    print('By default the following processes and connections are monitored: nfs, smb, ssh, HandbrakeCLI, ffmpeg, makemkv, and makemkvcon.')
    print('\nOptions:')
    print('  -?, --help              \tWill bring up this message.')
    print('  -b, --busy-action=ACTION\tSends ACTION to kodi when background activies are detected.')
    print('  -i, --idle-action=ACTION\tSends ACTION to kodi when no background activies are detected.')
    print('  ACTION                  \tSends ACTION to kodi when no background activies are detected.')
    print('\n  ACTION must be one of KODI\'s built-in functions.')
    print('  See: http://kodi.wiki/view/List_of_built-in_functions')
    print('\nExample: {} --idle-action="suspend"'.format(os.path.basename(sys.argv[0])))
    sys.exit(-1)


def get_opts():
    global idle_action, busy_action

    idle_action= ''
    busy_action = ''

    try:
        opts, args = getopt.getopt(sys.argv[1:], "i:b:?", ["idle-action=", "busy-action=", "help"])
    except getopt.GetoptError, err:
        usage()

    for opt, arg in opts:
        if opt in ("-?", "--help"):
            usage()
        elif opt in ("-i", "--idle-action"):
            idle_action = arg
        elif opt in ("-b", "--busy-action"):
            busy_action = arg
        else:
            usage()

    if len(args) == 1 and not idle_action:
        idle_action = args[0]

    if idle_action and ((idle_action[0] == '\'' and idle_action[-1] == '\'') or (idle_action[0] == '\"' and idle_action[-1] == '\"')):
        idle_action = idle_action[1:-1]

    if busy_action and ((busy_action[0] == '\'' and busy_action[-1] == '\'') or (busy_action[0] == '\"' and busy_action[-1] == '\"')):
        busy_action = busy_action[1:-1]

    return


def log(msg):
    if len(sys.argv) == 1:
        try:
            xbmc.log(msg='[{}] {}'.format(prefix, msg), level=xbmc.LOGNOTICE)
        except:
            print('[{}] {}'.format(prefix, msg))
    return


def get_pid(name):
    try:
        pid = subprocess.check_output(['pidof', name])
    except subprocess.CalledProcessError:
        pid = []

    return pid


def xbmc_send(action):
    ip = 'localhost'
    port = 9777

    try:
        xbmc.executebuiltin(action)
    except AttributeError:
        addr = (ip, port)
        sock = socket(AF_INET,SOCK_DGRAM)
        packet = PacketACTION(actionmessage=action, actiontype=ACTION_BUTTON)
        packet.send(sock, addr)

    return


def json_request(kodi_request, host):
    # http://host:8080/jsonrpc?request=kodi_request

    PORT   =    8080
    URL    =    'http://' + host + ':' + str(PORT) + '/jsonrpc'
    HEADER =    {'Content-Type': 'application/json'}

    try:
        if host == 'localhost':
            response = xbmc.executeJSONRPC(json.dumps(kodi_request))
            if response:
                return json.loads(response.decode('utf8','mixed'))
    except AttributeError:
        pass

    request = urllib2.Request(URL, json.dumps(kodi_request), HEADER)
    with closing(urllib2.urlopen(request)) as response:
        #return json.loads(response.read())
        #return json.loads(response.read().decode('utf8', errors='replace').replace(u'\ufffd','?'))
        return json.loads(response.read().decode('utf8', 'mixed'))


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
                log('Unknown port \'{}\'.'.format(p))
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


def parse_settings(xmlFile):
    settings = []

    try:
        context = etree.iterparse(xmlFile)
    except IOError:
        return settings

    for action, elem in context:
        if elem.tag == 'setting':
            if not elem.attrib:
                attrib = {}
            else:
                attrib = elem.attrib
            settings.append(attrib)

    return settings


def load_settings():
    global watched_local, watched_remote, watched_procs, pvr_local, pvr_port, pvr_minsecs, prefix, busy_notification

    prefix = time.strftime('%b %d %H:%M:%S') + ' ' + os.path.basename(sys.argv[0])

    # Defaults:
    busy_notification = 'Notification(Action cancelled, Background activities detected)'

    pvr_local = True  # PVR backend on local system
    pvr_port = 34890  # VDR-VNSI
    pvr_minsecs = 600 # 10 mins.

    watched_local = {445, 2049}      #smb, nfs, or 'set()' for empty set
    watched_remote = {22, 445}       #ssh, smb
    watched_procs = {'HandBrakeCLI', 'ffmpeg', 'makemkv' , 'makemkvcon'}

    try:
        # Parse settings.xml if addon is installed:
        GET_ADDON_PATH = {
            'jsonrpc': '2.0',
            'method': 'Addons.GetAddonDetails',
            'params': {
                'addonid': 'service.shutdown.watchdog',
                'properties': ['path']
            },
            'id': 1
        }
        data = json_request(GET_ADDON_PATH, 'localhost')
        if data['result']:
            path = data['result']['addon']['path']
            p1 = os.path.dirname(os.path.dirname(path))
            p2 = os.path.basename(path)
            #settings_xml = p1 + '/userdata/addon_data/' + p2 + '/settings.xml'
            settings_xml = os.path.join(p1, 'userdata', 'addon_data', p2, 'settings.xml')

            settings = parse_settings(settings_xml)
            if settings:
                log('Reading values from file {}.'.format(settings_xml))
                for set in settings:
                    if set['id'] == 'pvrlocal':
                        if set['value'] == 'false':
                            pvr_local = False
                        else:
                            pvr_local = True
                    elif set['id'] == 'pvrport':
                        pvr_port = int(set['value'])
                    elif set['id'] == 'pvrwaketime':
                        pvr_minsecs = int(set['value']) * 60
                    elif set['id'] == 'localports':
                        watched_local = read_set(set['value'])
                    elif set['id'] == 'remoteports':
                        watched_remote = read_set(set['value'])
                    elif set['id'] == 'procs':
                        watched_procs = read_set(set['value'])
            else:
                log('Could not read from file {}.'.format(settings_xml))
                log('Using default values.')

        GET_LOCALE = {
            'jsonrpc': '2.0',
            'method': 'Settings.GetSettingValue',
            'params': {
                'setting': 'locale.language'
            },
            'id': 1
        }
        data = json_request(GET_LOCALE, 'localhost')
        if data['result']:
            lang = data['result']['value'].split('.')[-1]
            if 'de' in lang:
                busy_notification = 'Notification(Aktion abgebrochen, Hintergrundaktivitäten festgestellt)'
    except:
        log('Could not query \'localhost\'. Check if kodi is running.')
        log('Using default values.')
        pass

    watched_local = port_trans(watched_local)
    watched_remote = port_trans(watched_remote)

    log('Watching for remote connections on port(s) {},\n\t\t\t\tlocal connections on port(s) {}, and\n\t\t\t\tactive process(es) of {}.'.format(
        ', '.join(str(x) for x in watched_remote),
        ', '.join(str(x) for x in watched_local),
        ', '.join(str(x) for x in watched_procs)))


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
                    log('Live TV is being watched from IP address {}.'.format(client))
                    return True # a client is watching live-tv
                elif 'pvr://' == urllib2.unquote(data['result']['item']['file'].encode('utf-8'))[:6]:
                    log('A recording is being watched from IP address {}.'.format(client))
                    return True # a client is watching a recording

        except:
            continue

    # log('No PVR clients connected.')
    return False


def check_timers():
    if not pvr_local or not get_pid('kodi.bin'):
        return False

    localhost = '127.0.0.1'

    if localhost not in find_clients(pvr_port, True):
        log('Check timers: localhost not connected to pvr backend.')
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
                    log('Recording scheduled in less than {} min.'.format(pvr_minsecs/60))
                    return True

                if secs_before_recording < 0:
                    log('Found active recording.')
                    return True

    # Sometimes we get a key error, maybe beacause pvr backend 
    # is not responding or busy.
    except KeyError:
        pass

    # log('No upcoming or ongoing recording found.')
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
            log('Found active process of {}.'.format(proc))
            return True

    # log('No active processes found.')
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
            log('Found connection from {} to {}:{}.'.format(remote_addr, local_addr, local_port))
            return True

    # log('No active connections found.')
    return False


def check_idle(arg_busy_action, arg_idle_action):
    if check_pvrclients() or check_timers() or check_services() or check_procs():
        log('Background activities detected.')

        if arg_busy_action:
            log('Sending action \'{}\' ...'.format(arg_busy_action))
            xbmc_send(arg_busy_action)

        elif arg_idle_action:
            log('Action \'{}\' cancelled.'.format(arg_idle_action))
            xbmc_send(busy_notification)

        return 1

    else:
        log('No background activities detected.')

        if arg_idle_action:
            log('Sending action \'{}\' ...'.format(arg_idle_action))
            xbmc_send(arg_idle_action)

        return 0


if __name__ == '__main__':
    get_opts()
    load_settings()
    sys.exit(check_idle(busy_action, idle_action))
