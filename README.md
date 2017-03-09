# service.shutdown.watchdog

Kodi addon to inhibit shutdown or suspend when background activities are detected.

This service addon will periodically reset the idle shutdown timer when it detetcs 
one of the monitored processes or connections active, or - in case the PVR backend 
is hosted locally - when a recording is due or remote PVR clients are connected.

In the configuration dialog one may enter either the specific tcp port to be monitored or use 
the following protocol identifiers:
```
protocol id         tcp port
----------------------------
'ftp-data'                20 
'ftp'                     21 
'ssh'                     22 
'telnet'                  23 
'tftp'                    69
'http'                    80 
'https'                  443
'smb'                    445 
'lpd'                    515 
'rtps'                   554 
'ipsec'                 1293
'l2tp'                  1701 
'lt2p-ipsec'            1707 
'pptp'                  1723
'nfs'                   2049 
'upnp'                  5000
'rtp'                   5004 
'rtcp'                  5005
'kodi-web'              8080 
'hts'                   9981 
'tvh'                   9983 
'vnsi-server'          34890
```

Both incoming (local ports) and outgoing (remote ports) connections are monitored.

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
The addon supports only Linux platforms. Currently only German and English 
translations are provided.

The addon was developed and tested on Ubuntu Desktop 16.04 with Kodi 17 
(Krypton). However, use at your own risk and please be aware that the 
addon code is still in beta status.

To install simply download the addon files as zip file and install from
the Kodi addon section.

My special credits go to blucube and his service.inhibit_shutdown addon
https://github.com/bluecube/service.inhibit_shutdown from whom I "borrowed"
the initial code and idea.
