# service.shutdown.watchdog

kodi addon to inhibit shutdown or suspend when background processes are active.

This service addon will periodically reset the idle shutdown timer when it detetcs 
one of the monitored processes or connections active, or - in case the PVR backend 
is hosted locally - when a recording is due or remote PVR clients are connected.

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
