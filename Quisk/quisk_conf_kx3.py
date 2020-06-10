# Please do not change this configuration file for Quisk.  Copy it to
# your own config file and make changes there.
#
# This config file is for hamlib control of a KX3 through hamlib, with Quisk
# acting as a panadapter.  The daemon rigctld must be running.  The open() method
# below tries to start it, or you can start it by hand.

import sys, os

if sys.platform == "win32":
  name_of_sound_capt = 'Primary'
  name_of_sound_play = 'Primary'
  latency_millisecs = 150
  data_poll_usec = 20000
else:
  name_of_sound_capt = 'hw:0'
  name_of_sound_play = 'hw:0'
  latency_millisecs = 150
  data_poll_usec = 5000

# Use the hamlib hardware module to talk to the KX3
from quisk_hardware_hamlib import Hardware as BaseHardware

class Hardware(BaseHardware):
  def __init__(self, app, conf):
    BaseHardware.__init__(self, app, conf)
    # Change the port and timing parameters here:
    # self.hamlib_rigctld_port = 4532		# Standard rigctld control port
    # self.hamlib_poll_seconds = 0.2		# Time interval to poll for changes
  def open(self):
    ret = BaseHardware.open(self)
    if not self.hamlib_connected:	# rigctld is not started.  Try to start it.
      os.system("rigctld -m 229 -r /dev/ttyUSB0 -s 4800 & ")	# Check the baud rate menu setting
      # If this fails, start rigctld by hand.
    return ret

