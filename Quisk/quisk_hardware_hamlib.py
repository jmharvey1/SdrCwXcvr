# This is a hardware file for control of a rig using the Hamlib rigctld daemon.
# This hardware will not start the daemon rigctld, so you must start it yourself.
# This hardware will connect to rigctld, and rigctld connects to the rig.  You can test
# rigctld with the command rigctl. See the hamlib documentation for rigctld and rigctl.
#
# If you change the frequency in Quisk, the change is sent to rigctld.  This hardware
# will query (poll) rigctld for its frequency at intervals to see if the rig changed
# the frequency.  If it did, the change is sent to Quisk.
#
# These are the attributes we watch:  Rx frequency, mode

from __future__ import print_function

DEBUG = 0

import socket, time, traceback
import _quisk as QS

from quisk_hardware_model import Hardware as BaseHardware

class Hardware(BaseHardware):
  def __init__(self, app, conf):
    BaseHardware.__init__(self, app, conf)
    self.hamlib_rigctld_port = 4532		# Standard rigctld control port
    self.hamlib_poll_seconds = 0.2		# Time interval to poll for changes
    self.hamlib_connected = False
    self.radio_freq = None
    self.radio_mode = None
    self.quisk_freq = None
    self.quisk_vfo = None
    self.quisk_mode = 'USB'
    self.received = ''
    self.toggle = False
    self.time0 = 0
  def open(self):
    ret = BaseHardware.open(self)
    self.hamlib_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self.hamlib_socket.settimeout(0.0)
    self.ConnectRigctld()
    return ret
  def close(self):
    self.hamlib_socket.close()
    self.hamlib_connected = False
    return BaseHardware.close(self)
  def ConnectRigctld(self):
    if self.hamlib_connected:
      return True
    try:
      self.hamlib_socket.connect(('localhost', self.hamlib_rigctld_port))
    except:
      return False      # Failure to connect
    self.hamlib_connected = True
    if DEBUG: print("rigctld connected")
    return True         # Success
  def ChangeFrequency(self, tune, vfo, source='', band='', event=None):
    self.quisk_freq = tune
    self.quisk_vfo = tune
    if DEBUG: print('Change', source, tune)
    return self.quisk_freq, self.quisk_vfo
  def ReturnFrequency(self):
    # Return the current tuning and VFO frequency.  If neither have changed,
    # you can return (None, None).  This is called at about 10 Hz by the main.
    return self.quisk_freq, self.quisk_vfo
  def ChangeMode(self, mode):		# Change the tx/rx mode
    # mode is a string: "USB", "AM", etc.
    if mode == 'CWU':
      mode = 'CW'
    elif mode == 'CWL':
      mode = 'CW'
    elif mode[0:4] == 'DGT-':
      mode = 'USB'
    self.quisk_mode = mode
    if DEBUG: print('Change', mode)
  def ChangeBand(self, band):
    # band is a string: "60", "40", "WWV", etc.
    pass
  def HeartBeat(self):	# Called at about 10 Hz by the main
    if not self.hamlib_connected:	# Continually try to connect
      try:
        self.hamlib_socket.connect(('localhost', self.hamlib_rigctld_port))
      except:
        return
      else:
        self.hamlib_connected = True
        if DEBUG: print("rigctld Connected")
    self.ReadHamlib()
    if time.time() - self.time0 < self.hamlib_poll_seconds:
      return
    self.time0 = time.time()
    if self.quisk_mode != self.radio_mode:
      self.HamlibSend("|M %s 0\n" % self.quisk_mode)
    elif self.quisk_freq != self.radio_freq:
      self.HamlibSend("|F %d\n" % self.quisk_freq)
    elif self.toggle:
      self.toggle = False
      self.HamlibSend("|f\n")		# Poll for frequency
    else:
      self.toggle = True
      self.HamlibSend("|m\n")		# Poll for mode
  def HamlibSend(self, text):
    if DEBUG: print('Send', text, end=' ')
    try:
      self.hamlib_socket.sendall(text)
    except socket.error:
      pass
  def ReadHamlib(self):
    if not self.hamlib_connected:
      return
    try:	# Read any data from the socket
      text = self.hamlib_socket.recv(1024)
    except socket.timeout:	# This does not work
      pass
    except socket.error:	# Nothing to read
      pass
    else:					# We got some characters
      self.received += text
    while '\n' in self.received:	# A complete response ending with newline is available
      reply, self.received = self.received.split('\n', 1)	# Split off the reply, save any further characters
      reply = reply.strip()		# Here is our reply
      if reply[-6:] != 'RPRT 0':
        if DEBUG: print('Reject', reply)
        continue
      try:
        if reply[0:9] == 'set_freq:':		# set_freq: 18120472|RPRT 0
          freq, status = reply[9:].split('|')
          freq = int(freq)
          if DEBUG: print('  Radio S freq', freq)
          self.radio_freq = freq
        elif reply[0:9] == 'get_freq:':	# get_freq:|Frequency: 18120450|RPRT 0
          z, freq, status = reply.split('|')
          z, freq = freq.split(':')
          freq = int(freq)
          if DEBUG: print('    Radio G freq', freq)
          if self.quisk_freq == self.radio_freq:
            self.radio_freq = freq
            self.ChangeFrequency(freq, self.quisk_vfo, 'hamlib')
        elif reply[0:9] == 'set_mode:':	# set_mode: FM 0|RPRT 0
          mode, status = reply[9:].split('|')
          mode, z = mode.split()
          if DEBUG: print('  Radio S mode', mode)
          self.radio_mode = mode
        elif reply[0:9] == 'get_mode:':	# get_mode:|Mode: FM|Passband: 12000|RPRT 0
          z, mode, passb, status = reply.split('|')
          z, mode = mode.split()
          if DEBUG: print('    Radio G mode', mode)
          if self.quisk_mode == self.radio_mode:
            if self.radio_mode != mode:		# The radio changed the mode
              self.radio_mode = mode
              self.quisk_mode = mode
              if mode in ('CW', 'CWR'):
                mode = 'CWU'
              self.application.OnBtnMode(None, mode)		# Set mode
        else:
          if DEBUG: print('Unknown', reply)
      except:
        if DEBUG: traceback.print_exc()
