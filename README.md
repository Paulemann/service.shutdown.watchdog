# service.shutdown.watchdog

kodi addon to inhibit shutdown or suspend when background processes are active.

This service addon will periodically reset the idle shutdown timer when it detetcs 
one of the monitored processes or connections active, or - in case the PVR backend 
is hosted locally - when a recording is due or remote PVR clients are connected.

In the configuration dialog one may enter either the specific tcp port to be monitored or use 
the following keywords for well known tcp connections:
```
'ftp-data': 20, 
'ftp':21, 
'ssh':22, 
'telnet':23, 
'tftp':69, 
'http':80, 
'https':443, 
'smb':445, 
'lpd':515, 
'rtps':554, 
'ipsec':1293, 
'l2tp':1701, 
'lt2p-ipsec':1707, 
'pptp':1723, 
'nfs':2049, 
'upnp':5000, 
'rtp':5004, 
'rtcp':5005, 
'kodi-web':8080, 
'hts':9981, 
'tvh':9983, 
'vnsi-server':34890
```

One may also leverage the addon to prevent shutdown or suspend while background
activities are deteted when the respective action is triggered by a remote 
or power button press. To this purpose you need to add the following lines to
the the keymap.xml file in ~/.kodi/userdata/keymaps:
```
</keymap>
  <global>
    <keyboard>
      <power>RunScript(service.shutdown.watchdog, 'shutdown')</power>
      <sleep>RunScript(service.shutdown.watchdog, 'suspend')</sleep>
     </keyboard>
  </global>
</keymap>
```
