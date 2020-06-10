#! /usr/bin/python

# All QUISK software is Copyright (C) 2006-2018 by James C. Ahlstrom.
# This free software is licensed for use under the GNU General Public
# License (GPL), see http://www.opensource.org.
# Note that there is NO WARRANTY AT ALL.  USE AT YOUR OWN RISK!!

"""The main program for Quisk, a software defined radio.

Usage:  python quisk.py [-c | --config config_file_path]
This can also be installed as a package and run as quisk.main().
"""

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

# Change to the directory of quisk.py.  This is necessary to import Quisk packages
# and to load other extension modules that link against _quisk.so.  It also helps to
# find ./__init__.py and ./help.html.
import sys, os
os.chdir(os.path.normpath(os.path.dirname(__file__)))
if sys.path[0] != "'.'":		# Make sure the current working directory is on path
  sys.path.insert(0, '.')

import wx, wx.html, wx.lib.stattext, wx.lib.colourdb, wx.grid, wx.richtext
import math, cmath, time, traceback, string, select, subprocess
import threading, pickle, webbrowser
try:
  from xmlrpc.client import ServerProxy
except ImportError:
  from xmlrpclib import ServerProxy
import _quisk as QS
from types import *
from quisk_widgets import *
from filters import Filters
import dxcluster
import configure

DEBUGSHELL = False
if DEBUGSHELL:
  from wx.py.crust import CrustFrame
  from wx.py.shell import ShellFrame

# Fldigi XML-RPC control opens a local socket.  If socket.setdefaulttimeout() is not
# called, the timeout on Linux is zero (1 msec) and on Windows is 2 seconds.  So we
# call it to insure consistent behavior.
import socket
socket.setdefaulttimeout(0.005)

HAMLIB_DEBUG = 0

application = None

# Command line parsing: be able to specify the config file.
from optparse import OptionParser
parser = OptionParser()
parser.add_option('-c', '--config', dest='config_file_path',
		help='Specify the configuration file path')
parser.add_option('', '--config2', dest='config_file_path2', default='',
		help='Specify a second configuration file to read after the first')
parser.add_option('-a', '--ask', action="store_true", dest='AskMe', default=False,
		help='Ask which radio to use when starting')
parser.add_option('', '--local', dest='local_option', default='',
		help='Specify a custom option that you have programmed yourself')
argv_options = parser.parse_args()[0]
ConfigPath = argv_options.config_file_path	# Get config file path
ConfigPath2 = argv_options.config_file_path2
LocalOption = argv_options.local_option
if sys.platform == 'win32':
  path = os.getenv('HOMEDRIVE', '') + os.getenv('HOMEPATH', '')
  for dir in ("Documents", "My Documents", "Eigene Dateien", "Documenti", "Mine Dokumenter"):
    config_dir = os.path.join(path, dir)
    if os.path.isdir(config_dir):
      break
  else:
    config_dir = os.path.join(path, "My Documents")
  try:
    try:
      import winreg as Qwinreg
    except ImportError:
      import _winreg as Qwinreg
    key = Qwinreg.OpenKey(Qwinreg.HKEY_CURRENT_USER,
       r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders")
    val = Qwinreg.QueryValueEx(key, "Personal")
    val = Qwinreg.ExpandEnvironmentStrings(val[0])
    Qwinreg.CloseKey(key)
    if os.path.isdir(val):
      DefaultConfigDir = val
    else:
      DefaultConfigDir = config_dir
  except:
    traceback.print_exc()
    DefaultConfigDir = config_dir
  if not ConfigPath:
    ConfigPath = os.path.join(DefaultConfigDir, "quisk_conf.py")
    if not os.path.isfile(ConfigPath):
      path = os.path.join(config_dir, "quisk_conf.py")
      if os.path.isfile(path):
        ConfigPath = path
  del config_dir
else:
  DefaultConfigDir = os.path.expanduser('~')
  if not ConfigPath:
    ConfigPath = os.path.join(DefaultConfigDir, ".quisk_conf.py")

# These FFT sizes have multiple small factors, and are prefered for efficiency.  FFT size must be an even number.
fftPreferedSizes = []
for f2 in range(1, 13):
  for y in (1, 3, 5, 7, 9, 11, 13, 15):
    for z in (1, 3, 5, 7, 9, 11, 13, 15):
      x = 2**f2 * y * z
      if 300 <= x <= 5000 and x not in fftPreferedSizes:
        fftPreferedSizes.append(x)
fftPreferedSizes.sort()

def round(x):	# round float to nearest integer
  if x >= 0:
    return int(x + 0.5)
  else:
    return - int(-x + 0.5)
    
def str2freq (freq):
  if '.' in freq:
    freq = int(float(freq) * 1E6 + 0.1)
  else:
    freq = int(freq)
  return freq    

def get_filter_tx(mode):	# Return the bandwidth, center of the Tx filters
  if mode in ('LSB', 'USB'):
    bw = 2700
    center = 1650
  elif mode in ('CWL', 'CWU'):
    bw = 10
    center = 0
  elif mode in ('AM', 'DGT-IQ'):
    bw = 6000
    center = 0
  elif mode in ('FM', 'DGT-FM'):
    bw = 10000
    center = 0
  elif mode in ('FDV-L', 'FDV-U'):
    bw = 2700
    center = 1500
  else:
    bw = 2700
    center = 1650
  if mode in ('CWL', 'LSB', 'DGT-L', 'FDV-L'):
    center = - center
  return bw, center

Mode2Index = {'CWL':0, 'CWU':1, 'LSB':2, 'USB':3, 'AM':4, 'FM':5, 'EXT':6, 'DGT-U':7, 'DGT-L':8, 'DGT-IQ':9,
      'IMD':10, 'FDV-U':11, 'FDV-L':12, 'DGT-FM':13}

class Timer:
  """Debug: measure and print times every ptime seconds.

  Call with msg == '' to start timer, then with a msg to record the time.
  """
  def __init__(self, ptime = 1.0):
    self.ptime = ptime		# frequency to print in seconds
    self.time0 = 0			# time zero; measure from this time
    self.time_print = 0		# last time data was printed
    self.timers = {}		# one timer for each msg
    self.names = []			# ordered list of msg
    self.heading = 1		# print heading on first use
  def __call__(self, msg):
    tm = time.time()
    if msg:
      if not self.time0:		# Not recording data
        return
      if msg in self.timers:
        count, average, highest = self.timers[msg]
      else:
        self.names.append(msg)
        count = 0
        average = highest = 0.0
      count += 1
      delta = tm - self.time0
      average += delta
      if highest < delta:
        highest = delta
      self.timers[msg] = (count, average, highest)
      if tm - self.time_print > self.ptime:	# time to print results
        self.time0 = 0		# end data recording, wait for reset
        self.time_print = tm
        if self.heading:
          self.heading = 0
          print ("count, msg, avg, max (msec)")
        print("%4d" % count, end=' ')
        for msg in self.names:		# keep names in order
          count, average, highest = self.timers[msg]
          if not count:
            continue
          average /= count
          print("  %s  %7.3f  %7.3f" % (msg, average * 1e3, highest * 1e3), end=' ')
          self.timers[msg] = (0, 0.0, 0.0)
        print()
    else:	# reset the time to zero
      self.time0 = tm		# Start timer
      if not self.time_print:
        self.time_print = tm

## T = Timer()		# Make a timer instance

class HamlibHandlerSerial:
  "Create a serial port for Hamlib control that emulates the FlexRadio PowerSDR 2.x command set."
  # This implements some Kenwood TS-2000 commands, but it is far from complete.
  Mo2CoKen = {'CWL':7, 'CWU':3, 'LSB':1, 'USB':2, 'AM':5, 'FM':4, 'DGT-U':9, 'DGT-L':6, 'DGT-FM':4, 'DGT-IQ':9}
  Co2MoKen = {1:'LSB', 2:'USB', 3:'CWU', 4:'FM', 5:'AM', 6:'DGT-L', 7:'CWL', 9:'DGT-U'}
  Mo2CoFlex = {'CWL':3, 'CWU':4, 'LSB':0, 'USB':1, 'AM':6, 'FM':5, 'DGT-U':7, 'DGT-L':9, 'DGT-FM':5, 'DGT-IQ':7}
  Co2MoFlex = {0:'LSB', 1:'USB', 3:'CWL', 4:'CWU', 5:'FM', 6:'AM', 7:'DGT-U', 9:'DGT-L'}
  def __init__(self, app, public_name):
    self.app = app
    self.port = None
    self.received = ''
    self.radio_id = '019'
    self.public_name = public_name	# the public name for the serial port
    if sys.platform == 'win32':
      try:
        import serial
      except:
        print ("Please install the pyserial module.")
      else:
        try:
          self.port = serial.Serial(public_name, timeout=0, write_timeout=0)
        except:
          print ("The serial port %s could not be opened." % public_name)
    else:
      import tty
      if os.path.lexists(public_name):
        try:
          os.remove(public_name)
        except:
          print ("Can not remove the file", public_name)
      try:
        self.port, slave = os.openpty()	# we are the master device fd, slave is a pseudo tty
        tty.setraw(self.port)
        tty.setraw(slave)
      except:
        print ("Can not create the serial port")
        self.port = None
      else:
        try:
          os.symlink(os.ttyname(slave), public_name)	# create a link from the specified name to the slave device
        except:
          print ("Can not create a link named", public_name)
          self.port = None
        else:
          if HAMLIB_DEBUG: print ("Create", public_name, "from", os.ttyname(slave))
  def open(self):
    return
  def close(self):
    if sys.platform != 'win32':
      if self.public_name:
        try:
          os.remove(self.public_name)
        except:
          pass
  def Read(self):
    if self.port is None:
      return
    if sys.platform == 'win32':
      self.received += str(self.port.read(99))
    else:
      while True:
        r, w, x = select.select((self.port,), (), (), 0)
        if not r:
          break
        self.received += os.read(self.port, 1)
  def Process(self):
    """This is the main processing loop, and is called frequently.  It reads and satisfies requests."""
    self.Read()
    if ';' in self.received:	# A complete command ending with semicolon is available
      cmd, self.received = self.received.split(';', 1)	# Split off the command, save any further characters
    else:
      return
    cmd = cmd.strip()		# Here is our command and data
    if cmd[0:2] in ('ZZ', 'zz', 'Zz', 'zZ'):
      data = cmd[4:]
      cmd = cmd[0:4].upper()
      func = cmd
    else:
      data = cmd[2:]
      cmd = cmd[0:2].upper()
      if cmd in ('FA', 'FB', 'IF', 'PS'):	# Use the ZZxx command method
        func = 'ZZ' + cmd
      else:			# Use the two-letter method
        func = cmd
    if data:
      if HAMLIB_DEBUG: print ("Process command  :", cmd, data)
    try:
      func = getattr(self, func)
    except:
      print ("Unimplemented serial port function", func, 'cmd', cmd, 'data', data)
      self.Write('?;')
      return
    func(cmd, data, len(data))
  def Error(self, cmd, data):
    self.Write('?;')
    print ("*** Error for cmd %s data %s" % (cmd, data))
  def Write(self, data):
    if HAMLIB_DEBUG: print ("Serial port write:", data)
    if self.port is None:
      return
    if sys.platform == 'win32':
      self.port.write(data)
    else:
      r, w, x = select.select((), (self.port,), (), 0)
      if w:
        os.write(self.port, data)
  def AG(self, cmd, data, length):	# audio gain
    if length == 1:
      self.Write("%s%s120;" % (cmd, data[0]))
  def ZZAG(self, cmd, data, length):	# audio gain
    if length == 0:
      self.Write("%s050;" % cmd)
  def ZZAI(self, cmd, data, length):	# broadcast changes
    if length == 0:
      self.Write("%s0;" % cmd)
    elif length == 1 and data[0] == '0':
      pass
    else:
      self.Error(cmd, data)
  def ZZFA(self, cmd, data, length):	# frequency of VFO A, the receive frequency
    if length == 0:
      self.Write("%s%011d;" % (cmd, self.app.rxFreq + self.app.VFO))
    elif length == 11:
      freq = int(data, base=10)
      tune = freq - self.app.VFO
      d = self.app.sample_rate * 45 // 100
      if -d <= tune <= d:	# Frequency is on-screen
        vfo = self.app.VFO
      else:					# Change the VFO
        vfo = (freq // 5000) * 5000 - 5000
        tune = freq - vfo
      self.app.BandFromFreq(freq)
      self.app.ChangeHwFrequency(tune, vfo, 'FreqEntry')
      if HAMLIB_DEBUG: print ("New Freq rx,tx", self.app.txFreq + self.app.VFO, self.app.rxFreq + self.app.VFO)
    else:
      self.Error(cmd, data)
  def ZZFB(self, cmd, data, length):	# frequency of VFO B
    if length == 0:
      self.Write("%s%011d;" % (cmd, self.app.txFreq + self.app.VFO))
    elif length == 11:
      freq = int(data, base=10)
      tune = freq - self.app.VFO
      d = self.app.sample_rate * 45 // 100
      if -d <= tune <= d:	# Frequency is on-screen
        vfo = self.app.VFO
      else:					# Change the VFO
        vfo = (freq // 5000) * 5000 - 5000
        tune = freq - vfo
      self.app.BandFromFreq(freq)
      self.app.ChangeHwFrequency(tune, vfo, 'FreqEntry')
    else:
      self.Error(cmd, data)
  def FR(self, cmd, data, length):	# receive VFO is always VFO A
    if length == 0:
      self.Write("%s0;" % cmd)
    elif length == 1 and data[0] == '0':
      pass
    else:
      self.Error(cmd, data)
  def FT(self, cmd, data, length):	# transmit VFO
    if self.app.split_rxtx:
      vfo = '1'
    else:
      vfo = '0'
    if length == 0:
      self.Write("%s%s;" % (cmd, vfo))
    elif length == 1 and data[0] == vfo:
      pass
    else:
      self.Error(cmd, data)
  def ID(self, cmd, data, length):	# return radio ID
    if length == 0:
      self.Write('%s%s;' % (cmd, self.radio_id))
    else:
      self.Error(cmd, data)
  def ZZID(self, cmd, data, length):	# set radio id to Flex
    if length == 0:
      self.radio_id = '900'
    else:
      self.Error(cmd, data)
  def ZZIF(self, cmd, data, length):	# return information for ZZIF and IF
    ritFreq = self.app.ritScale.GetValue()
    if self.app.ritButton.GetValue():
      rit = 1
    else:
      rit = 0
    mode = self.app.mode
    info = cmd
    info += "%011d" % (self.app.rxFreq + self.app.VFO)	# frequency, ZZFA
    info += '0000'
    if ritFreq < 0:	# RIT freq
      info += "-%05d" % -ritFreq
    else:
      info += "+%05d" % ritFreq
    info += "%d" % rit	# RIT status
    info += '0000'
    if QS.is_key_down():	# MOX, key down
      info += '1'
    else:
      info += '0'
    if len(cmd) == 4:	# Flex ZZIF
      code = self.Mo2CoFlex.get(mode, 1)
      info += "%02d" % code	# operating mode
    else:		# Kenwood IF
      code = self.Mo2CoKen.get(mode, 1)
      info += "%d" % code	# operating mode
    info += '00'
    if self.app.split_rxtx:	# VFO split status
      info += '1'
    else:
      info += '0'
    info += '0000'
    info += ';'
    self.Write(info)
  def MD(self, cmd, data, length):	# the mode; USB, CW, etc.
    if length == 0:
      mode = self.app.mode
      code = self.Mo2CoKen.get(mode, 2)
      self.Write("%s%d;" % (cmd, code))
    elif length == 1:
      code = int(data, base=10)
      mode = self.Co2MoKen.get(code, 'USB')
      self.app.OnBtnMode(None, mode)		# Set mode
    else:
      self.Error(cmd, data)
  def ZZMD(self, cmd, data, length):	# the mode; USB, CW, etc.
    if length == 0:
      mode = self.app.mode
      code = self.Mo2CoFlex.get(mode, 1)
      self.Write("%s%02d;" % (cmd, code))
    elif length == 2:
      code = int(data, base=10)
      mode = self.Co2MoFlex.get(code, 'USB')
      self.app.OnBtnMode(None, mode)	# Set mode
    else:
      self.Error(cmd, data)
  def ZZMU(self, cmd, data, length):	# MultiRx on/off
    if length == 0:
      self.Write("%s0;" % cmd)
  def OI(self, cmd, data, length):      # return information
    self.ZZIF(cmd, data, length)
  def ZZPS(self, cmd, data, length):	# power status
    if length == 0:
      self.Write("%s1;" % cmd)
  def ZZRS(self, cmd, data, length):	# the RX2 status
    if length == 0:
      self.Write("%s0;" % cmd)
    elif length == 1 and data[0] == '0':
      pass
    else:
      self.Error(cmd, data)
  def RX(self, cmd, data, length):	# turn off MOX
    if length == 0:
      if self.app.pttButton:
        self.app.pttButton.SetValue(0, True)
      else:
        self.Error(cmd, data)
    else:
      self.Error(cmd, data)
  def ZZSP(self, cmd, data, length):	# the split status
    if length == 0:
      if self.app.split_rxtx:
        self.Write("%s1;" % cmd)
      else:
        self.Write("%s0;" % cmd)
    else:
      self.Error(cmd, data)
  def ZZSW(self, cmd, data, length):	# transmit VFO is A or B
    if length == 0:
      if self.app.split_rxtx:
        self.Write("%s1;" % cmd)
      else:
        self.Write("%s0;" % cmd)
  def TX(self, cmd, data, length):	# turn on MOX
    if length == 0:
      if self.app.pttButton:
        self.app.pttButton.SetValue(1, True)
      else:
        self.Error(cmd, data)
    else:
      self.Error(cmd, data)
  def ZZTX(self, cmd, data, length):	# the MOX status
    if length == 0:
      if QS.is_key_down():
        self.Write("%s1;" % cmd)
      else:
        self.Write("%s0;" % cmd)
    elif length == 1:
      if self.app.pttButton:
        if data[0] == '0':
          self.app.pttButton.SetValue(0, True)
        else:
          self.app.pttButton.SetValue(1, True)
      else:
        self.Error(cmd, data)
    else:
      self.Error(cmd, data)
  def ZZVE(self, cmd, data, length):	# is VOX enabled
    if length == 0:
      if self.app.useVOX:
        self.Write("%s1;" % cmd)
      else:
        self.Write("%s0;" % cmd)
    else:
      self.Error(cmd, data)
  def XT(self, cmd, data, length):	# the XIT
    if length == 0:
      self.Write("%s0;" % cmd)
    elif length == 1 and data[0] == '0':
      pass
    else:
      self.Error(cmd, data)

class HamlibHandlerRig2:
  """This class is created for each connection to the server.  It services requests from each client"""
  SingleLetters = {		# convert single-letter commands to long commands
    '_':'info',
    'f':'freq',
    'i':'split_freq',
    'm':'mode',
    's':'split_vfo',
    't':'ptt',
    'v':'vfo',
    }
# I don't understand the need for dump_state, nor what it means.
# A possible response to the "dump_state" request:
  dump1 = """ 2
2
2
150000.000000 1500000000.000000 0x1ff -1 -1 0x10000003 0x3
0 0 0 0 0 0 0
0 0 0 0 0 0 0
0x1ff 1
0x1ff 0
0 0
0x1e 2400
0x2 500
0x1 8000
0x1 2400
0x20 15000
0x20 8000
0x40 230000
0 0
9990
9990
10000
0
10 
10 20 30 
0x3effffff
0x3effffff
0x7fffffff
0x7fffffff
0x7fffffff
0x7fffffff
"""

# Another possible response to the "dump_state" request:
  dump2 = """ 0
2
2
150000.000000 30000000.000000  0x900af -1 -1 0x10 000003 0x3
0 0 0 0 0 0 0
150000.000000 30000000.000000  0x900af -1 -1 0x10 000003 0x3
0 0 0 0 0 0 0
0 0
0 0
0
0
0
0


0x0
0x0
0x0
0x0
0x0
0
"""
  def __init__(self, app, sock, address):
    self.app = app		# Reference back to the "hardware"
    self.sock = sock
    sock.settimeout(0.0)
    self.address = address
    self.received = ''
    h = self.Handlers = {}
    h[''] = self.ErrProtocol
    h['dump_state']	= self.DumpState
    h['chk_vfo']	= self.ChkVfo	# Thanks to Franco Spinelli, IW2DHW
    h['get_freq']	= self.GetFreq
    h['set_freq']	= self.SetFreq
    h['get_info']	= self.GetInfo
    h['get_mode']	= self.GetMode
    h['set_mode']	= self.SetMode
    h['get_vfo']	= self.GetVfo
    h['get_ptt']	= self.GetPtt
    h['set_ptt']	= self.SetPtt
    h['get_split_freq']	= self.GetSplitFreq
    h['set_split_freq']	= self.SetSplitFreq
    h['get_split_vfo']	= self.GetSplitVfo
    h['set_split_vfo']	= self.SetSplitVfo
  def Send(self, text):
    """Send text back to the client."""
    try:
      self.sock.sendall(text)
    except socket.error:
      self.sock.close()
      self.sock = None
  def Reply(self, *args):	# args is name, value, name, value, ..., int
    """Create a string reply of name, value pairs, and an ending integer code."""
    if self.extended:			# Use extended format
      t = "%s:" % self.cmd		# Extended format echoes the command and parameters
      for param in self.params:
        t = "%s %s" % (t, param)
      t += self.extended
      for i in range(0, len(args) - 1, 2):
        t = "%s%s: %s%c" % (t, args[i], args[i+1], self.extended)
      t += "RPRT %d\n" % args[-1]
    elif len(args) > 1:		# Use simple format
      t = ''
      for i in range(1, len(args) - 1, 2):
        t = "%s%s\n" % (t, args[i])
    else:		# No names; just the required integer code
      t = "RPRT %d\n" % args[0]
    # print 'Reply', t
    self.Send(t)
  def ErrParam(self):		# Invalid parameter
    self.Reply(-1)
  def UnImplemented(self):	# Command not implemented
    self.Reply(-4)
  def ErrProtocol(self):	# Protocol error
    self.Reply(-8)
  def Process(self):
    """This is the main processing loop, and is called frequently.  It reads and satisfies requests."""
    if not self.sock:
      return 0
    try:	# Read any data from the socket
      text = self.sock.recv(1024)
    except socket.timeout:	# This does not work
      pass
    except socket.error:	# Nothing to read
      pass
    else:					# We got some characters
      self.received += text
    if '\n' in self.received:	# A complete command ending with newline is available
      cmd, self.received = self.received.split('\n', 1)	# Split off the command, save any further characters
    else:
      return 1
    cmd = cmd.strip()		# Here is our command
    # print 'Get', cmd
    if not cmd:			# ??? Indicates a closed connection?
      # print 'empty command'
      self.sock.close()
      self.sock = None
      return 0
    # Parse the command and call the appropriate handler
    if cmd[0] == '+':			# rigctld Extended Response Protocol
      self.extended = '\n'
      cmd = cmd[1:].strip()
    elif cmd[0] in ';|,':		# rigctld Extended Response Protocol
      self.extended = cmd[0]
      cmd = cmd[1:].strip()
    else:
      self.extended = None
    if cmd[0:1] == '\\':		# long form command starting with backslash
      args = cmd[1:].split()
      self.cmd = args[0]
      self.params = args[1:]
      self.Handlers.get(self.cmd, self.UnImplemented)()
    else:						# single-letter command
      self.params = cmd[1:].strip()
      cmd = cmd[0:1]
      if cmd in 'Qq':	# Quit command
        return 0
      try:
        t = self.SingleLetters[cmd.lower()]
      except KeyError:
        self.UnImplemented()
      else:
        if cmd in string.uppercase:
          self.cmd = 'set_' + t
        else:
          self.cmd = 'get_' + t
        self.Handlers.get(self.cmd, self.UnImplemented)()
    return 1
  # These are the handlers for each request
  def DumpState(self):
    self.Send(self.dump2)
  def ChkVfo(self):
    self.Send('CHKVFO 0')
  def GetFreq(self):
    self.Reply('Frequency', self.app.rxFreq + self.app.VFO, 0)
  def SetFreq(self):
    try:
      freq = float(self.params)
      self.Reply(0)
    except:
      self.ErrParam()
    else:
      freq = int(freq + 0.5)
      self.app.ChangeRxTxFrequency(freq, None)
  def GetSplitFreq(self):
    self.Reply('TX Frequency', self.app.txFreq + self.app.VFO, 0)
  def SetSplitFreq(self):
    try:
      freq = float(self.params)
      self.Reply(0)
    except:
      self.ErrParam()
    else:
      freq = int(freq + 0.5)
      if self.app.split_rxtx and not self.app.split_hamlib_tx:
        self.app.ChangeRxTxFrequency(freq, None)
      else:
        self.app.ChangeRxTxFrequency(None, freq)
  def GetSplitVfo(self):
    # I am not sure if "VFO" is a suitable response
    if self.app.split_rxtx:
      self.Reply('Split', 1, 'TX VFO', 'VFO', 0)
    else:
      self.Reply('Split', 0, 'TX VFO', 'VFO', 0)
  def SetSplitVfo(self):
    # Currently (Aug 2012) hamlib fails to send the "split" parameter, so this fails
    try:
      split, vfo = self.params.split()
      split = int(split)
      self.Reply(0)
    except:
      # traceback.print_exc()
      self.ErrParam()
    else:
      self.app.splitButton.SetValue(split, True)
  def GetInfo(self):
    self.Reply("Info", self.app.main_frame.title, 0)
  def GetMode(self):
    mode = self.app.mode
    if mode == 'CWU':
      mode = 'CW'
    elif mode == 'CWL':		# Is this what CWR means?
      mode = 'CWR'
    elif mode == 'DGT-FM':
      mode = 'FM'
    elif mode[0:4] == 'DGT-':
      mode = 'USB'
    self.Reply('Mode', mode, 'Passband', self.app.filter_bandwidth, 0)
  def SetMode(self):
    try:
      mode, bw = self.params.split()
      bw = int(float(bw) + 0.5)
    except:
      self.ErrParam()
      return
    if mode in ('USB', 'LSB', 'AM', 'FM'):
      self.Reply(0)
    elif mode[0:4] == 'DGT-':
      self.Reply(0)
    elif mode == 'CW':
      mode = 'CWU'
      self.Reply(0)
    elif mode == 'CWR':
      mode = 'CWL'
      self.Reply(0)
    else:
      self.ErrParam()
      return
    self.app.OnBtnMode(None, mode)		# Set mode
    if bw <= 0:		# use default bandwidth
      return
    # Choose button closest to requested bandwidth
    buttons = self.app.filterButns.GetButtons()
    Lab = buttons[0].GetLabel()
    diff = abs(int(Lab) - bw)
    for i in range(1, len(buttons) - 1):
      label = buttons[i].GetLabel()
      df = abs(int(label) - bw)
      if df < diff:
        Lab = label
        diff = df
    self.app.OnBtnFilter(None, int(Lab))
  def GetVfo(self):
    self.Reply('VFO', "VFO", 0)		# The type of VFO we have
  def GetPtt(self):
    if QS.is_key_down():
      self.Reply('PTT', 1, 0)
    else:
      self.Reply('PTT', 0, 0)
  def SetPtt(self):
    if not self.app.pttButton:
      self.UnImplemented()
      return
    try:
      ptt = int(self.params)
      self.Reply(0)
    except:
      self.ErrParam()
    else:
      self.app.pttButton.SetValue(ptt, True)

class SoundThread(threading.Thread):
  """Create a second (non-GUI) thread to read, process and play sound."""
  def __init__(self):
    self.do_init = 1
    threading.Thread.__init__(self)
    self.doQuit = threading.Event()
    self.doQuit.clear()
  def run(self):
    """Read, process, play sound; then notify the GUI thread to check for FFT data."""
    if self.do_init:	# Open sound using this thread
      self.do_init = 0
      QS.start_sound()
      wx.CallAfter(application.PostStartup)
    while not self.doQuit.isSet():
      QS.read_sound()
      wx.CallAfter(application.OnReadSound)
    QS.close_sound()
  def stop(self):
    """Set a flag to indicate that the sound thread should end."""
    self.doQuit.set()

class ConfigScreen(wx.Panel):
  """Display a notebook with status and configuration data"""
  def __init__(self, parent, width, fft_size):
    self.y_scale = 0
    self.y_zero = 0
    self.finish_pages = True
    self.width = width
    wx.Panel.__init__(self, parent)
    self.notebook = notebook = wx.Notebook(self)
    font = wx.Font(conf.config_font_size, wx.FONTFAMILY_SWISS, wx.NORMAL,
          wx.FONTWEIGHT_NORMAL, False, conf.quisk_typeface)
    notebook.SetFont(font)
    sizer = wx.BoxSizer()
    sizer.Add(notebook, 1, wx.EXPAND)
    self.SetSizer(sizer)
    # create the page windows
    self.status = ConfigStatus(notebook, width, fft_size)
    self.SetBackgroundColour(self.status.bg_color)
    self.SetForegroundColour(self.status.tfg_color)
    notebook.bg_color = self.status.bg_color
    notebook.tfg_color = self.status.tfg_color
    notebook.AddPage(self.status, "Status")
    self.config = ConfigConfig(notebook, width)
    notebook.AddPage(self.config, "Config")
    self.sound = ConfigSound(notebook, width)
    notebook.AddPage(self.sound, "Sound")
    self.favorites = ConfigFavorites(notebook, width)
    notebook.AddPage(self.favorites, "Favorites")
    self.tx_audio = ConfigTxAudio(notebook, width)
    notebook.AddPage(self.tx_audio, "Tx Audio")
    self.tx_audio.status = self.status
  def FinishPages(self):
    if self.finish_pages:
      self.finish_pages = False
      application.local_conf.AddPages(self.notebook, self.width)
  def ChangeYscale(self, y_scale):
    pass
  def ChangeYzero(self, y_zero):
    pass
  def OnIdle(self, event):
    pass
  def SetTxFreq(self, tx_freq, rx_freq):
    pass
  def OnGraphData(self, data=None):
    self.status.OnGraphData(data)
    self.tx_audio.OnGraphData(data)
  def InitBitmap(self):		# Initial construction of bitmap
    self.status.InitBitmap()

class ConfigStatus(wx.ScrolledWindow):
  """Display the status screen."""
  def __init__(self, parent, width, fft_size):
    wx.ScrolledWindow.__init__(self, parent)
    self.Bind(wx.EVT_PAINT, self.OnPaint)
    self.bg_color = self.GetBackgroundColour()
    self.tfg_color = wx.Colour(20, 20, 20)	# use for text foreground
    self.width = width
    self.fft_size = fft_size
    self.scroll_height = None
    self.interupts = 0
    self.read_error = -1
    self.write_error = -1
    self.underrun_error = -1
    self.fft_error = -1
    self.latencyCapt = -1
    self.latencyPlay = -1
    self.y_scale = 0
    self.y_zero = 0
    self.rate_min = -1
    self.rate_max = -1
    self.chan_min = -1
    self.chan_max = -1
    self.mic_max_display = 0
    self.err_msg = "No response"
    self.msg1 = ""
    self.font = wx.Font(conf.status_font_size, wx.FONTFAMILY_SWISS, wx.NORMAL,
          wx.FONTWEIGHT_NORMAL, False, conf.quisk_typeface)
    if wxVersion in ('2', '3'):
      self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
    else:
      self.SetBackgroundStyle(wx.BG_STYLE_PAINT)
    self.SetFont(self.font)
    charx = self.charx = self.GetCharWidth()
    chary = self.chary = self.GetCharHeight()
    self.dy = chary		# line spacing
    self.rjustify1 = (0, 1, 0)
    self.tabstops1 = [0] * 3
    self.tabstops1[0] = x = charx
    self.tabstops1[1] = x = x + self.GetTextExtent("FFT number of errors 1234567890")[0]
    self.tabstops1[2] = x = x + self.GetTextExtent("XXXX")[0]
    self.rjustify2 = (0, 0, 1, 1, 1)
    self.tabstops2 = []
  def MakeTabstops(self):
    luse = lname = 0
    for use, name, rate, latency, errors in QS.sound_errors():
      name = self.TrimName(name)
      w, h = self.GetTextExtent(use)
      luse = max(luse, w)
      w, h = self.GetTextExtent(name)
      lname = max(lname, w)
    if luse == 0:
      return
    charx = self.charx
    self.tabstops2 = [0] * 5
    self.tabstops2[0] = x = charx
    self.tabstops2[1] = x = x + luse + charx * 6
    self.tabstops2[2] = x = x + lname + self.GetTextExtent("Sample rateXXXXXX")[0]
    self.tabstops2[3] = x = x + charx * 12
    self.tabstops2[4] = x = x + charx * 12
  def TrimName(self, name):
    if len(name) > 50:
      name = name[0:30] + '|||' + name[-17:]
    return name
  def OnPaint(self, event):
    # Make and blit variable data
    self.MakeBitmap()
    dc = wx.AutoBufferedPaintDC(self)
    x, y = self.GetViewStart()
    dc.Blit(0, 0, self.mem_width, self.mem_height, self.mem_dc, x, y)
  def MakeRow2(self, *args):
    for col in range(len(args)):
      t = args[col]
      if t is None:
        continue
      t = str(t)
      x = self.tabstops[col]
      if self.rjustify[col]:
        w, h = self.mem_dc.GetTextExtent(t)
        x -= w
      if ("Error" in t or "Stream error" in t) and t != "Errors":
        self.mem_dc.SetTextForeground('Red')
        self.mem_dc.DrawText(t, x, self.mem_y)
        self.mem_dc.SetTextForeground(self.tfg_color)
      else:
        self.mem_dc.DrawText(t, x, self.mem_y)
    self.mem_y += self.dy
  def InitBitmap(self):		# Initial construction of bitmap
    self.mem_height = application.screen_height
    self.mem_width = application.screen_width
    self.bitmap = EmptyBitmap(self.mem_width, self.mem_height)
    self.mem_dc = wx.MemoryDC()
    self.mem_rect = wx.Rect(0, 0, self.mem_width, self.mem_height)
    self.mem_dc.SelectObject(self.bitmap)
    br = wx.Brush(self.bg_color)
    self.mem_dc.SetBackground(br)
    self.mem_dc.SetFont(self.font)
    self.mem_dc.SetTextForeground(self.tfg_color)
    self.mem_dc.Clear()
  def MakeBitmap(self):
    self.mem_dc.Clear()
    self.mem_y = self.charx
    self.tabstops = self.tabstops1
    self.rjustify = self.rjustify1
    if conf.config_file_exists:
      cfile = "Configuration file:  %s" % conf.config_file_path
    else:
      cfile = "Configuration file not found %s" % conf.config_file_path
    if conf.microphone_name:
      level = "%3.0f" % self.mic_max_display
    else:
      level = "None"
    if self.err_msg:
      err_msg = self.err_msg
    else:
      err_msg = None
    self.MakeRow2("Sample interrupts", self.interupts, cfile)
    self.MakeRow2("Microphone or DGT level dB", level, application.config_text)
    self.MakeRow2("FFT number of points", self.fft_size, err_msg)
    if conf.dxClHost:		# connection to dx cluster
      nSpots = len(application.dxCluster.dxSpots)
      if nSpots > 0:
        msg = str(nSpots) + ' DX spot' + ('' if nSpots==1 else 's') + ' received from ' + application.dxCluster.getHost()
      else:
        msg = "No DX Cluster data from %s" % conf.dxClHost
      self.MakeRow2("FFT number of errors", self.fft_error, msg)
    else:
      self.MakeRow2("FFT number of errors", self.fft_error)
    self.mem_y += self.dy
    if not self.tabstops2:
      return
    self.tabstops = self.tabstops2
    self.rjustify = self.rjustify2
    self.font.SetUnderlined(True)
    self.mem_dc.SetFont(self.font)
    self.MakeRow2("Device", "Name", "Sample rate", "Latency", "Errors")
    self.font.SetUnderlined(False)
    self.mem_dc.SetFont(self.font)
    self.mem_y += self.dy * 3 // 10
    if conf.use_sdriq:
      self.MakeRow2("Capture radio samples", "SDR-IQ", application.sample_rate, self.latencyCapt, self.read_error)
    elif conf.use_rx_udp:
      self.MakeRow2("Capture radio samples", "UDP", application.sample_rate, self.latencyCapt, self.read_error)
    elif conf.use_soapy:
      self.MakeRow2("Capture radio samples", "SoapySDR", application.sample_rate, self.latencyCapt, self.read_error)
    for use, name, rate, latency, errors in QS.sound_errors():
      self.MakeRow2(use, self.TrimName(name), rate, latency, errors)
    if self.scroll_height is None:
      self.scroll_height = self.mem_y + self.dy
      self.SetScrollbars(1, 1, 100, self.scroll_height)
  def OnGraphData(self, data=None):
    if not self.tabstops2:      # Must wait for sound to start
      self.MakeTabstops()
    (self.rate_min, self.rate_max, sample_rate, self.chan_min, self.chan_max,
         self.msg1, self.unused, self.err_msg,
         self.read_error, self.write_error, self.underrun_error,
         self.latencyCapt, self.latencyPlay, self.interupts, self.fft_error, self.mic_max_display,
         self.data_poll_usec
     ) = QS.get_state()
    self.mic_max_display = 20.0 * math.log10((self.mic_max_display + 1) / 32767.0)
    self.RefreshRect(self.mem_rect)

class ConfigConfig(wx.ScrolledWindow):
  def __init__(self, parent, width):
    wx.ScrolledWindow.__init__(self, parent)
    self.width = width
    self.font = wx.Font(conf.config_font_size, wx.FONTFAMILY_SWISS, wx.NORMAL,
          wx.FONTWEIGHT_NORMAL, False, conf.quisk_typeface)
    self.SetFont(self.font)
    self.SetBackgroundColour(parent.bg_color)
    self.charx = charx = self.GetCharWidth()
    self.chary = chary = self.GetCharHeight()
    self.dy = self.chary
    self.rx_phase = None
    self.radio_group = None
    # Make controls FIRST column
    tab0 = charx * 4
    # Receive phase
    rx = wx.StaticText(self, -1, "Adjust receive amplitude and phase")
    tx = wx.StaticText(self, -1, "Adjust transmit amplitude and phase")
    x1, y1 = tx.GetSize().Get()
    self.rx_phase = ctrl = QuiskPushbutton(self, self.OnBtnPhase, "Rx Phase...")
    ctrl.SetColorGray()
    if not conf.name_of_sound_capt:
      ctrl.Enable(0)
    x2, y2 = ctrl.GetSize().Get()
    tab1 = tab0 + x1 + charx * 2
    tab2 = tab1 + x2
    tab3 = tab2 + charx * 8
    self.y = self.yyy = y2 + self.chary
    self.dy = y2 * 12 // 10
    self.offset = (y2 - y1) // 2
    rx.SetPosition((tab0, self.y))
    ctrl.SetPosition((tab1, self.y - self.offset))
    self.y += self.dy
    # Transmit phase
    self.tx_phase = ctrl = QuiskPushbutton(self, self.OnBtnPhase, "Tx Phase...")
    ctrl.SetColorGray()
    if not conf.name_of_mic_play:
      ctrl.Enable(0)
    tx.SetPosition((tab0, self.y))
    ctrl.SetPosition((tab1, self.y - self.offset))
    self.y += self.dy
    # Choice (combo) box for decimation
    lst = Hardware.VarDecimGetChoices()
    if lst:
      txt = Hardware.VarDecimGetLabel()
      index = Hardware.VarDecimGetIndex()
    else:
      txt = "Variable decimation"
      lst = ["None"]
      index = 0
    t = wx.StaticText(self, -1, txt)
    ctrl = wx.Choice(self, -1, choices=lst, size=(x2, y2))
    if lst:
      self.Bind(wx.EVT_CHOICE, application.OnBtnDecimation, ctrl)
      ctrl.SetSelection(index)
    t.SetPosition((tab0, self.y))
    ctrl.SetPosition((tab1, self.y - self.offset))
    self.y += self.dy
    # Transmit level controls
    if hasattr(Hardware, "SetTxLevel"):
      SliderBoxH(self, "Tx level %d%%  ", 100, 0, 100, self.OnTxLevel, True, (tab0, self.y), tab2-tab0)
      self.y += self.dy
      level = conf.digital_tx_level
      SliderBoxH(self, "Digital Tx level %d%%  ", level, 0, level, self.OnDigitalTxLevel, True, (tab0, self.y), tab2-tab0)
      self.y += self.dy
    # mic_out_volume
    if conf.name_of_mic_play:
      level = int(conf.mic_out_volume * 100.0 + 0.1)
      SliderBoxH(self, "SftRock Tx level %d%%  ", level, 0, 100, self.OnSrTxLevel, True, (tab0, self.y), tab2-tab0)
      self.y += self.dy
    self.scroll_height = self.y
    #### Make controls SECOND column
    self.y = self.yyy
    self.tab3 = tab3
    self.charx = charx
    ## Record buttons
    self.st = st = wx.StaticText(self, -1, "The file-record button will:", pos=(tab3 - charx * 2, self.y))
    self.dy = st.GetSize().GetHeight() * 14 // 10
    self.y += self.dy
    # File for recording speaker audio
    text = "Record Rx audio to WAV file "
    path = conf.file_name_audio
    self.file_button_rec_speaker = self.MakeFileButton(text, path, 0)
    # File for recording samples
    text = "Record I/Q samples to WAV file "
    path = conf.file_name_samples
    self.file_button_rec_iq = self.MakeFileButton(text, path, 1)
    # File for recording the microphone
    text = "Record the mic to make a CQ message"
    path = ''
    self.file_button_rec_mic = self.MakeFileButton(text, path, 2)
    ## Play buttons
    wx.StaticText(self, -1, "The file-play button will:", pos=(tab3 - charx * 2, self.y))
    self.y += self.dy
    # File for playing speaker audio
    text = "Play Rx audio from a WAV file"
    path = ''
    self.file_button_play_speaker = self.MakeFileButton(text, path, 10)
    # file for playing samples
    text = "Receive saved I/Q samples from a file"
    path = ''
    self.file_button_play_iq = self.MakeFileButton(text, path, 11)
    # File for playing a file to the mic input for a CQ message
    text = "Repeat a CQ message until a station answers"
    path = conf.file_name_playback
    self.file_button_play_mic = self.MakeFileButton(text, path, 12)
    SliderBoxH(self, "Repeat secs %.1f  ", 0, 0, 100, self.OnPlayFileRepeat, True, (tab3 + charx * 4, self.y), tab2-tab0, 0.1)
    self.y += self.dy
    if self.y > self.scroll_height:
      self.scroll_height = self.y
    self.SetScrollbars(1, 1, 100, self.scroll_height)
  def MakeFileButton(self, text, path, index):
    if index < 10:	# record buttons
      cb = wx.CheckBox(self, -1, text, pos=(self.tab3, self.y))
      self.Bind(wx.EVT_CHECKBOX, self.OnCheckRecPlay, cb)
    elif self.radio_group:
      cb = wx.RadioButton(self, -1, text, pos=(self.tab3, self.y))
      self.Bind(wx.EVT_RADIOBUTTON, self.OnCheckRecPlay, cb)
    else:
      self.radio_group = True
      cb = wx.RadioButton(self, -1, text, pos=(self.tab3, self.y), style=wx.RB_GROUP)
      self.Bind(wx.EVT_RADIOBUTTON, self.OnCheckRecPlay, cb)
    x = self.tab3 + cb.GetSize().GetWidth()
    bsz = wx.Size(self.charx * 3, cb.GetSize().GetHeight())
    b = wx.Button(self, -1, "...", pos=(x, self.y), size=bsz)
    b.check_box = cb
    b.index = cb.index = index
    b.path = cb.path = path
    QS.set_file_name(b.index, name=path, enable=0)
    self.Bind(wx.EVT_BUTTON, self.OnBtnFileName, b)
    x = x + b.GetSize().GetWidth() + self.charx
    dddy = (cb.GetSize().GetHeight() - self.st.GetSize().GetHeight()) // 2
    if not path:
      cb.Enable(False)
      path = "(No file)"
    b.txt_ctrl = wx.StaticText(self, -1, path, pos=(x, self.y + dddy))
    self.y += self.dy
    return b
  def OnTxLevel(self, event):
    application.tx_level = event.GetEventObject().GetValue()
    Hardware.SetTxLevel()
  def OnSrTxLevel(self, event):
    level = event.GetEventObject().GetValue()
    QS.set_mic_out_volume(level)
  def OnDigitalTxLevel(self, event):
    application.digital_tx_level = event.GetEventObject().GetValue()
    Hardware.SetTxLevel()
  def OnBtnPhase(self, event):
    btn = event.GetEventObject()
    if btn.GetLabel()[0:2] == 'Tx':
      rx_tx = 'tx'
    else:
      rx_tx = 'rx'
    application.screenBtnGroup.SetLabel('Graph', do_cmd=True)
    if application.w_phase:
      application.w_phase.Raise()
    else:
      application.w_phase = QAdjustPhase(self, self.width, rx_tx)
  def OnBtnFileName(self, event):
    btn = event.GetEventObject()
    dr, fn = os.path.split(btn.path)
    if btn.index < 10:	# record buttons
      dlg = wx.FileDialog(self, 'Choose WAV file', dr, fn, style=wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT, wildcard="Wave files (*.wav)|*.wav")
    else:
      dlg = wx.FileDialog(self, 'Choose WAV file', dr, fn, style=wx.FD_OPEN, wildcard="Wave files (*.wav)|*.wav")
    if dlg.ShowModal() == wx.ID_OK:
      path = dlg.GetPath()
      if path[-4:].lower() != '.wav':
        path = path + '.wav'
      QS.set_file_name(btn.index, name=path)
      btn.txt_ctrl.SetLabel(path)
      btn.path = path
      btn.check_box.path = path
      btn.check_box.Enable(True)
      if btn.index >= 10:	# play buttons
        btn.check_box.SetValue(True)
        application.file_play_source = btn.index
        QS.set_file_name(btn.index, enable=1)
        QS.open_wav_file_play(path)
      self.EnableRecPlay()
    dlg.Destroy()
  def EnableRecPlay(self):
    enable_rec = (self.file_button_rec_speaker.check_box.GetValue() or
        self.file_button_rec_iq.check_box.GetValue() or
        self.file_button_rec_mic.check_box.GetValue())
    enable_play = ((self.file_button_play_speaker.path and self.file_button_play_speaker.check_box.GetValue()) or
        self.file_button_play_iq.check_box.GetValue() or
        self.file_button_play_mic.check_box.GetValue())
    application.btn_file_record.Enable(enable_rec)
    application.btnFilePlay.Enable(enable_play)
  def OnCheckRecPlay(self, event):
    btn = event.GetEventObject()
    if btn.GetValue():
      if btn.index >= 10:	# play button
        QS.open_wav_file_play(btn.path)
        application.file_play_source = btn.index
      QS.set_file_name(btn.index, enable=1)
    else:
      QS.set_file_name(btn.index, enable=0)
    self.EnableRecPlay()
  def OnPlayFileRepeat(self, event):
    application.file_play_repeat = event.GetEventObject().GetValue() * 0.1

class ConfigSound(wx.ScrolledWindow):
  """Display the available sound devices."""
  def __init__(self, parent, width):
    wx.ScrolledWindow.__init__(self, parent)
    self.Bind(wx.EVT_PAINT, self.OnPaint)
    self.width = width
    self.dev_capt, self.dev_play = QS.sound_devices()
    self.tfg_color = parent.tfg_color
    self.font = wx.Font(conf.config_font_size, wx.FONTFAMILY_SWISS, wx.NORMAL,
          wx.FONTWEIGHT_NORMAL, False, conf.quisk_typeface)
    self.SetFont(self.font)
    self.SetBackgroundColour(parent.bg_color)
    self.charx = self.GetCharWidth()
    self.chary = self.GetCharHeight()
    self.dy = self.chary
    height = self.chary * (3 + len(self.dev_capt) + len(self.dev_play))
    if sys.platform != 'win32' and conf.show_pulse_audio_devices:
      height += self.chary * (3 + 3 * len(application.pa_dev_capt) + 3 * len(application.pa_dev_play))
    self.SetScrollbars(1, 1, 100, height)
  def OnPaint(self, event):
    dc = wx.PaintDC(self)
    dc.Clear()
    self.DoPrepareDC(dc)
    dc.SetFont(self.font)
    dc.SetTextForeground(self.tfg_color)
    x0 = self.charx
    self.y = self.chary // 3
    dc.DrawText("Available devices for capture:", x0, self.y)
    self.y += self.dy
    for name in self.dev_capt:
      dc.DrawText('    ' + name, x0, self.y)
      self.y += self.dy
    dc.DrawText("Available devices for playback:", x0, self.y)
    self.y += self.dy
    for name in self.dev_play:
      dc.DrawText('    ' + name, x0, self.y)
      self.y += self.dy
    if sys.platform != 'win32' and conf.show_pulse_audio_devices:
      dc.DrawText("Available PulseAudio devices for capture (sources):", x0, self.y)
      self.y += self.dy
      for n0, n1, n2 in application.pa_dev_capt:
        dc.DrawText(' ' * 4 + n1, x0, self.y)
        self.y += self.dy
        dc.DrawText(' ' * 8 + n0, x0, self.y)
        self.y += self.dy
        if n2:
          dc.DrawText(' ' * 8 + n2, x0, self.y)
          self.y += self.dy
      dc.DrawText("Available PulseAudio devices for playback (sinks):", x0, self.y)
      self.y += self.dy
      for n0, n1, n2 in application.pa_dev_play:
        dc.DrawText(' ' * 4 + n1, x0, self.y)
        self.y += self.dy
        dc.DrawText(' ' * 8 + n0, x0, self.y)
        self.y += self.dy
        if n2:
          dc.DrawText(' ' * 8 + n2, x0, self.y)
          self.y += self.dy

class ConfigFavorites(wx.grid.Grid):
  def __init__(self, parent, width):
    wx.grid.Grid.__init__(self, parent)
    self.changed = False
    self.RepeaterDict = {}
    font = wx.Font(conf.favorites_font_size, wx.FONTFAMILY_SWISS, wx.NORMAL,
          wx.FONTWEIGHT_BOLD, False, conf.quisk_typeface)
    self.SetFont(font)
    self.SetBackgroundColour(parent.bg_color)
    self.SetLabelFont(font)
    font = wx.Font(conf.favorites_font_size, wx.FONTFAMILY_SWISS, wx.NORMAL,
          wx.FONTWEIGHT_NORMAL, False, conf.quisk_typeface)
    self.SetDefaultCellFont(font)
    self.SetDefaultRowSize(self.GetCharHeight()+3)
    self.Bind(wx.grid.EVT_GRID_LABEL_RIGHT_CLICK, self.OnRightClickLabel)
    self.Bind(wx.grid.EVT_GRID_LABEL_LEFT_CLICK, self.OnLeftClickLabel)
    if wxVersion in ('2', '3'):
      self.Bind(wx.grid.EVT_GRID_CELL_CHANGE, self.OnChange)    # wxPython 3
    else:
      self.Bind(wx.grid.EVT_GRID_CELL_CHANGED, self.OnChange)   # wxPython 4
    self.Bind(wx.grid.EVT_GRID_LABEL_LEFT_DCLICK, self.OnLeftDClick)
    self.CreateGrid(0, 6)
    self.EnableDragRowSize(False)
    w = self.GetTextExtent(' 999 ')[0]
    self.SetRowLabelSize(w)
    self.SetColLabelValue(0,  'Name')
    self.SetColLabelValue(1,  'Freq MHz')
    self.SetColLabelValue(2,  'Mode')	# This column has a choice editor
    self.SetColLabelValue(3,  'Description')
    self.SetColLabelValue(4,  'Offset kHz')
    self.SetColLabelValue(5,  'Tone Hz')
    w = self.GetTextExtent("xFrequencyx")[0]
    self.SetColSize(0, w * 3 // 2)
    self.SetColSize(1, w)
    self.SetColSize(4, w)
    self.SetColSize(5, w)
    self.SetColSize(2, w)
    ww = width - w * 7 - self.GetRowLabelSize() - 20
    if ww < w:
      ww = w
    self.SetColSize(3, ww)
    if conf.favorites_file_path:
      self.init_path = conf.favorites_file_path
    else:
      self.init_path = os.path.join(os.path.dirname(ConfigPath), 'quisk_favorites.txt')
    conf.favorites_file_in_use = self.init_path
    self.ReadIn()
    if self.GetNumberRows() < 1:
      self.AppendRows()
    # Make a popup menu
    self.popupmenu = wx.Menu()
    item = self.popupmenu.Append(-1, 'Tune to')
    self.Bind(wx.EVT_MENU, self.OnPopupTuneto, item)
    self.popupmenu.AppendSeparator()
    item = self.popupmenu.Append(-1, 'Append')
    self.Bind(wx.EVT_MENU, self.OnPopupAppend, item)
    item = self.popupmenu.Append(-1, 'Insert')
    self.Bind(wx.EVT_MENU, self.OnPopupInsert, item)
    item = self.popupmenu.Append(-1, 'Delete')
    self.Bind(wx.EVT_MENU, self.OnPopupDelete, item)
    self.popupmenu.AppendSeparator()
    item = self.popupmenu.Append(-1, 'Move Up')
    self.Bind(wx.EVT_MENU, self.OnPopupMoveUp, item)
    item = self.popupmenu.Append(-1, 'Move Down')
    self.Bind(wx.EVT_MENU, self.OnPopupMoveDown, item)
    # Make a timer
    self.timer = wx.Timer(self)
    self.Bind(wx.EVT_TIMER, self.OnTimer)
  def SetModeEditor(self, mode_names):
    self.mode_names = mode_names
    for row in range(self.GetNumberRows()):
      self.SetCellEditor(row, 2, wx.grid.GridCellChoiceEditor(mode_names, True))
  def FormatFloat(self, freq):
    freq = "%.6f" % freq
    for i in range(3):
      if freq[-1] == '0':
        freq = freq[:-1]
      else:
        break
    return freq
  def ReadIn(self):
    try:
      fp = open(self.init_path, 'rb')
      lines = fp.readlines()
      fp.close()
    except:
      lines = ("my net|7210000|LSB|My net 2030 UTC every Thursday",
               "10m FM 1|29.620|FM|Fm local 10 meter repeater")
    for row in range(len(lines)):
      self.AppendRows()
      fields = lines[row].split('|')
      for col in range(len(fields)):
        if col == 1:    # Correct old entries made in Hertz
          freq = fields[1]
          try:
            freq = float(freq)
          except:
            pass
          else:
            if freq > 30000.0:    # Must be in Hertz
              freq *= 1E-6
              fields[1] = self.FormatFloat(freq)
        if col <= 5:
          self.SetCellValue(row, col, fields[col].strip())
    self.MakeRepeaterDict()
  def WriteOut(self):
    ncols = self.GetNumberCols()
    if ncols != 6:
      print ("Bad logic in favorites WriteOut()")
      return
    self.changed = False
    try:
      fp = open(self.init_path, 'wb')
    except:
      return
    for row in range(self.GetNumberRows()):
      out = []
      for col in range(0, ncols):
        cell = self.GetCellValue(row, col)
        cell = cell.replace('|', ';')
        out.append(cell)
      t = "%20s | %10s | %10s | %30s | %10s | %10s\r\n" % tuple(out)
      fp.write(t)
    fp.close()
  def AddNewFavorite(self):
    self.InsertRows(0)
    self.SetCellValue(0, 0, 'New station');
    freq = (application.rxFreq + application.VFO) * 1E-6    # convert to megahertz
    freq = self.FormatFloat(freq)
    self.SetCellValue(0, 1, freq)
    self.SetCellValue(0, 2, application.mode);
    self.SetCellEditor(0, 2, wx.grid.GridCellChoiceEditor(self.mode_names, True))
    self.OnChange()
  def OnRightClickLabel(self, event):
    event.Skip()
    self.menurow = event.GetRow()
    if self.menurow >= 0:
      pos = event.GetPosition()
      self.PopupMenu(self.popupmenu, pos)
  def OnLeftClickLabel(self, event):
    pass
  def OnLeftDClick(self, event):		# Thanks to Christof, DJ4CM
    self.menurow = event.GetRow()
    if self.menurow >= 0:
      self.OnPopupTuneto(event)
  def OnPopupAppend(self, event):
    self.InsertRows(self.menurow + 1)
    self.SetCellEditor(self.menurow + 1, 2, wx.grid.GridCellChoiceEditor(self.mode_names, True))
    self.OnChange()
  def OnPopupInsert(self, event):
    self.InsertRows(self.menurow)
    self.SetCellEditor(self.menurow, 2, wx.grid.GridCellChoiceEditor(self.mode_names, True))
    self.OnChange()
  def OnPopupDelete(self, event):
    self.DeleteRows(self.menurow)
    if self.GetNumberRows() < 1:
      self.AppendRows()
      self.SetCellEditor(0, 2, wx.grid.GridCellChoiceEditor(self.mode_names, True))
    self.OnChange()
  def OnPopupMoveUp(self, event):
    row = self.menurow
    if row < 1:
      return
    for i in range(self.GetNumberCols()):
      c = self.GetCellValue(row - 1, i)
      self.SetCellValue(row - 1, i, self.GetCellValue(row, i))
      self.SetCellValue(row, i, c)
  def OnPopupMoveDown(self, event):
    row = self.menurow
    if row == self.GetNumberRows() - 1:
      return
    for i in range(self.GetNumberCols()):
      c = self.GetCellValue(row + 1, i)
      self.SetCellValue(row + 1, i, self.GetCellValue(row, i))
      self.SetCellValue(row, i, c)
  def OnPopupTuneto(self, event):
    freq = self.GetCellValue(self.menurow, 1)
    if not freq:
      return
    try:
      freq = str2freq (freq)
    except ValueError:
      print('Bad frequency')
      return
    if self.changed:
      if self.timer.IsRunning():
        self.timer.Stop()
      self.WriteOut()
    application.ChangeRxTxFrequency(None, freq)
    mode = self.GetCellValue(self.menurow, 2)
    mode = mode.upper()
    application.OnBtnMode(None, mode)
    application.screenBtnGroup.SetLabel(conf.default_screen, do_cmd=True)
  def MakeRepeaterDict(self):
    self.RepeaterDict = {}
    for row in range(self.GetNumberRows()):
      offset = self.GetCellValue(row, 4)
      offset = offset.strip()
      if not offset:
        continue
      freq = self.GetCellValue(row, 1)
      tone = self.GetCellValue(row, 5)
      tone = tone.strip()
      if not tone:
        tone = '0'
      try:
        offset = float(offset)
        freq = float(freq)
        tone = float(tone)
      except:
        traceback.print_exc()
      else:
        freq = int(freq * 1E6 + 0.5)	# frequency in Hertz
        freq = (freq + 500) // 1000		# frequency in units of 1 kHz
        self.RepeaterDict[freq * 1000] = (offset, tone)
  def OnChange(self, event=None):
    self.MakeRepeaterDict()
    self.changed = True
    if self.timer.IsRunning():
      self.timer.Stop()
    self.timer.Start(5000, oneShot=True)
  def OnTimer(self, event):
    if self.changed:
      self.WriteOut()

class ConfigTxAudio(wx.ScrolledWindow):
  """Display controls for the transmit audio."""
  def __init__(self, parent, width):
    wx.ScrolledWindow.__init__(self, parent)
    self.width = width
    self.font = wx.Font(conf.config_font_size, wx.FONTFAMILY_SWISS, wx.NORMAL,
          wx.FONTWEIGHT_NORMAL, False, conf.quisk_typeface)
    self.SetFont(self.font)
    self.SetBackgroundColour(parent.bg_color)
    self.charx = charx = self.GetCharWidth()
    self.chary = chary = self.GetCharHeight()
    self.tmp_playing = False
    # Make controls
    tab0 = charx * 4
    self.y = chary
    t = "This is a test screen for transmit audio.  SSB, AM and FM have separate settings."
    wx.StaticText(self, -1, t, pos=(tab0, self.y))
    self.btn_record = QuiskCheckbutton(self, self.OnBtnRecord, "Record")
    self.btn_record.SetColorGray()
    x2, y2 = self.btn_record.GetSize().Get()
    self.dy = y2 * 12 // 10
    self.offset = (y2 - chary) // 2
    self.y += self.dy
    # Record and Playback
    ctl = wx.StaticText(self, -1, "Listen to transmit audio", pos=(tab0, self.y))
    x1, y1 = ctl.GetSize().Get()
    x = tab0 + x1 + charx * 3
    y = self.y - self.offset
    self.btn_record.SetPosition((x, y))
    self.btn_playback = QuiskCheckbutton(self, self.OnBtnPlayback, "Playback")
    self.btn_playback.SetColorGray()
    self.btn_playback.SetPosition((x + x2 + charx * 3, y))
    self.btn_playback.Enable(0)
    if not conf.microphone_name:
      self.btn_record.Enable(0)
    tab1 = x + x2
    tab2 = tab1 + charx * 3
    self.y += self.dy
    # mic level
    self.mic_text = wx.StaticText(self, -1, "Peak microphone audio level   None", pos=(tab0, self.y))
    t = "Adjust the peak audio level to a few dB below zero."
    wx.StaticText(self, -1, t, pos=(tab2, self.y))
    self.y += self.dy
    # Vox level
    SliderBoxH(self, "VOX %d dB  ", application.levelVOX, -40, 0, application.OnLevelVOX, True, (tab0, self.y), tab1-tab0)
    t = "Audio level that triggers VOX (all modes)."
    wx.StaticText(self, -1, t, pos=(tab2, self.y))
    self.y += self.dy
    # VOX hang
    SliderBoxH(self, "VOX %0.2f  ", application.timeVOX, 0, 4000, application.OnTimeVOX, True, (tab0, self.y), tab1-tab0, 0.001)
    t = "Time to hold VOX after end of audio in seconds."
    wx.StaticText(self, -1, t, pos=(tab2, self.y))
    self.y += self.dy
    # Tx Audio clipping
    application.CtrlTxAudioClip = SliderBoxH(self, "Clip %2d  ", 0, 0, 20, application.OnTxAudioClip, True, (tab0, self.y), tab1-tab0)
    t = "Tx audio clipping level in dB for this mode."
    wx.StaticText(self, -1, t, pos=(tab2, self.y))
    self.y += self.dy
    # Tx Audio preemphasis
    application.CtrlTxAudioPreemph = SliderBoxH(self, "Preemphasis %4.2f  ", 0, 0, 100, application.OnTxAudioPreemph, True, (tab0, self.y), tab1-tab0, 0.01)
    t = "Tx audio preemphasis of high frequencies."
    wx.StaticText(self, -1, t, pos=(tab2, self.y))
    self.y += self.dy
    self.SetScrollbars(1, 1, 100, self.y)
  def OnGraphData(self, data=None):
    if conf.microphone_name:
      txt = "Peak microphone audio level %3.0f dB" % self.status.mic_max_display
      self.mic_text.SetLabel(txt)
    if self.tmp_playing and QS.set_record_state(-1):	# poll to see if playback is finished
      self.tmp_playing = False
      self.btn_playback.SetValue(False)
      self.btn_record.Enable(1)
  def OnBtnRecord(self, event):
    if event.GetEventObject().GetValue():
      QS.set_kill_audio(1)
      self.btn_playback.Enable(0)
      QS.set_record_state(4)
    else:
      QS.set_kill_audio(0)
      self.btn_playback.Enable(1)
      QS.set_record_state(1)
  def OnBtnPlayback(self, event):
    if event.GetEventObject().GetValue():
      self.btn_record.Enable(0)
      QS.set_record_state(2)
      self.tmp_playing = True
    else:
      self.btn_record.Enable(1)
      QS.set_record_state(3)
      self.tmp_playing = False

class GraphDisplay(wx.Window):
  """Display the FFT graph within the graph screen."""
  def __init__(self, parent, x, y, graph_width, height, chary):
    wx.Window.__init__(self, parent,
       pos = (x, y),
       size = (graph_width, height),
       style = wx.NO_BORDER)
    self.parent = parent
    self.chary = chary
    self.graph_width = graph_width
    self.display_text = ""
    self.line = [(0, 0), (1,1)]		# initial fake graph data
    self.SetBackgroundColour(conf.color_graph)
    self.Bind(wx.EVT_PAINT, self.OnPaint)
    self.Bind(wx.EVT_LEFT_DOWN, parent.OnLeftDown)
    self.Bind(wx.EVT_RIGHT_DOWN, parent.OnRightDown)
    self.Bind(wx.EVT_LEFT_UP, parent.OnLeftUp)
    self.Bind(wx.EVT_MOTION, parent.OnMotion)
    self.Bind(wx.EVT_MOUSEWHEEL, parent.OnWheel)
    self.tune_tx = graph_width // 2	# Current X position of the Tx tuning line
    self.tune_rx = 0				# Current X position of Rx tuning line or zero
    self.scale = 20				# pixels per 10 dB
    self.peak_hold = 9999		# time constant for holding peak value
    self.height = 10
    self.y_min = 1000
    self.y_max = 0
    self.max_height = application.screen_height
    self.backgroundPen = wx.Pen(self.GetBackgroundColour(), 1)
    self.tuningPenTx = wx.Pen(conf.color_txline, 1)
    self.tuningPenRx = wx.Pen(conf.color_rxline, 1)
    self.backgroundBrush = wx.Brush(self.GetBackgroundColour())
    self.filterBrush = wx.Brush(conf.color_bandwidth, wx.SOLID)
    self.horizPen = wx.Pen(conf.color_gl, 1, wx.SOLID)
    self.font = wx.Font(conf.graph_msg_font_size, wx.FONTFAMILY_SWISS, wx.NORMAL,
          wx.FONTWEIGHT_NORMAL, False, conf.quisk_typeface)
    self.SetFont(self.font)
    if sys.platform == 'win32':
      self.Bind(wx.EVT_ENTER_WINDOW, self.OnEnter)
    if wxVersion in ('2', '3'):
      self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
    else:
      self.SetBackgroundStyle(wx.BG_STYLE_PAINT)
  def OnEnter(self, event):
    if not application.w_phase:
      self.SetFocus()	# Set focus so we get mouse wheel events
  def OnPaint(self, event):
    #print 'GraphDisplay', self.GetUpdateRegion().GetBox()
    dc = wx.AutoBufferedPaintDC(self)
    dc.Clear()
    # Draw the tuning line and filter display to the screen.
    # If self.tune_rx is zero, draw the Rx filter at the Tx tuning line. There is no separate Rx display.
    # Otherwise draw both an Rx and Tx tuning display.
    self.DrawFilter(dc)
    dc.SetPen(wx.Pen(conf.color_graphline, 1))
    dc.DrawLines(self.line)
    dc.SetPen(self.horizPen)
    for y in self.parent.y_ticks:
      dc.DrawLine(0, y, self.graph_width, y)	# y line
    if self.display_text:
      dc.SetFont(self.font)
      dc.SetTextBackground(conf.color_graph_msg_bg)
      dc.SetTextForeground(conf.color_graph_msg_fg)
      dc.SetBackgroundMode(wx.SOLID)
      dc.DrawText(self.display_text, 0, 0)
  def DrawFilter(self, dc):
    dc.SetPen(wx.TRANSPARENT_PEN)
    dc.SetLogicalFunction(wx.COPY)
    scale = 1.0 / self.parent.zoom / self.parent.sample_rate * self.graph_width
    dc.SetBrush(self.filterBrush)
    if self.tune_rx:
      x, w, rit = self.parent.GetFilterDisplayXWR(rx_filters=False)
      dc.DrawRectangle(self.tune_tx + x, 0, w, self.height)
      x, w, rit = self.parent.GetFilterDisplayXWR(rx_filters=True)
      dc.DrawRectangle(self.tune_rx + rit + x, 0, w, self.height)
      dc.SetPen(self.tuningPenRx)
      dc.DrawLine(self.tune_rx, 0, self.tune_rx, self.height)
    else:
      x, w, rit = self.parent.GetFilterDisplayXWR(rx_filters=True)
      dc.DrawRectangle(self.tune_tx + rit + x, 0, w, self.height)
    dc.SetPen(self.tuningPenTx)
    dc.DrawLine(self.tune_tx, 0, self.tune_tx, self.height)
    return rit
  def SetHeight(self, height):
    self.height = height
    self.SetSize((self.graph_width, height))
  def OnGraphData(self, data):
    x = 0
    for y in data:	# y is in dB, -130 to 0
      y = self.zeroDB - int(y * self.scale / 10.0 + 0.5)
      try:
        y0 = self.line[x][1]
      except IndexError:
        self.line.append([x, y])
      else:
        if y > y0:
          y = min(y, y0 + self.peak_hold)
        self.line[x] = [x, y]
      x = x + 1
    self.Refresh()
  def SetTuningLine(self, tune_tx, tune_rx):
    dc = wx.ClientDC(self)
    rit = self.parent.GetFilterDisplayRit()
    # Erase the old display
    dc.SetPen(self.backgroundPen)
    if self.tune_rx:
      dc.DrawLine(self.tune_rx, 0, self.tune_rx, self.height)
    dc.DrawLine(self.tune_tx, 0, self.tune_tx, self.height)
    # Draw a new display
    if self.tune_rx:
      dc.SetPen(self.tuningPenRx)
      dc.DrawLine(tune_rx, 0, tune_rx, self.height)
    dc.SetPen(self.tuningPenTx)
    dc.DrawLine(tune_tx, 0, tune_tx, self.height)
    self.tune_tx = tune_tx
    self.tune_rx = tune_rx

class GraphScreen(wx.Window):
  """Display the graph screen X and Y axis, and create a graph display."""
  def __init__(self, parent, data_width, graph_width, in_splitter=0):
    wx.Window.__init__(self, parent, pos = (0, 0))
    self.in_splitter = in_splitter	# Are we in the top of a splitter window?
    self.split_unavailable = False		# Are we a multi receive graph or waterfall window?
    if in_splitter:
      self.y_scale = conf.waterfall_graph_y_scale
      self.y_zero = conf.waterfall_graph_y_zero
    else:
      self.y_scale = conf.graph_y_scale
      self.y_zero = conf.graph_y_zero
    self.y_ticks = []
    self.VFO = 0
    self.filter_mode = 'AM'
    self.filter_bandwidth = 0
    self.filter_center = 0
    self.ritFreq = 0				# receive incremental tuning frequency offset
    self.mouse_x = 0
    self.WheelMod = conf.mouse_wheelmod		# Round frequency when using mouse wheel
    self.txFreq = 0
    self.sample_rate = application.sample_rate
    self.zoom = 1.0
    self.zoom_deltaf = 0
    self.data_width = data_width
    self.graph_width = graph_width
    self.doResize = False
    self.pen_tick = wx.Pen(conf.color_graphticks, 1)
    self.pen_label = wx.Pen(conf.color_graphlabels, 1)
    self.font = wx.Font(conf.graph_font_size, wx.FONTFAMILY_SWISS, wx.NORMAL,
          wx.FONTWEIGHT_NORMAL, False, conf.quisk_typeface)
    self.SetFont(self.font)
    w = self.GetCharWidth() * 14 // 10
    h = self.GetCharHeight()
    self.charx = w
    self.chary = h
    self.tick = max(2, h * 3 // 10)
    self.originX = w * 5
    self.offsetY = h + self.tick
    self.width = self.originX + self.graph_width + self.tick + self.charx * 2
    self.height = application.screen_height * 3 // 10
    self.x0 = self.originX + self.graph_width // 2		# center of graph
    self.tuningX = self.x0
    self.originY = 10
    self.zeroDB = 10	# y location of zero dB; may be above the top of the graph
    self.scale = 10
    self.mouse_is_rx = False
    self.SetSize((self.width, self.height))
    self.SetSizeHints(self.width, 1, self.width)
    self.SetBackgroundColour(conf.color_graph)
    self.backgroundBrush = wx.Brush(conf.color_graph)
    self.Bind(wx.EVT_SIZE, self.OnSize)
    self.Bind(wx.EVT_PAINT, self.OnPaint)
    self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
    self.Bind(wx.EVT_RIGHT_DOWN, self.OnRightDown)
    self.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
    self.Bind(wx.EVT_MOTION, self.OnMotion)
    self.Bind(wx.EVT_MOUSEWHEEL, self.OnWheel)
    self.MakeDisplay()
  def MakeDisplay(self):
    self.display = GraphDisplay(self, self.originX, 0, self.graph_width, 5, self.chary)
    self.display.zeroDB = self.zeroDB
  def SetDisplayMsg(self, text=''):
    self.display.display_text = text
    self.display.Refresh()
  def ScrollMsg(self, chars):	# Add characters to a scrolling message
    self.display.display_text = self.display.display_text + chars
    self.display.display_text = self.display.display_text[-50:]
    self.display.Refresh()
  def OnPaint(self, event):
    dc = wx.PaintDC(self)
    dc.SetBackground(self.backgroundBrush)
    dc.Clear()
    dc.SetFont(self.font)
    dc.SetTextForeground(conf.color_graphlabels)
    if self.in_splitter:
      self.MakeYTicks(dc)
    else:
      self.MakeYTicks(dc)
      self.MakeXTicks(dc)
  def OnIdle(self, event):
    if self.doResize:
      self.ResizeGraph()
  def OnSize(self, event):
    self.doResize = True
    event.Skip()
  def ResizeGraph(self):
    """Change the height of the graph.

    Changing the width interactively is not allowed because the FFT size is fixed.
    Call after changing the zero or scale to recalculate the X and Y axis marks.
    """
    w, h = self.GetClientSize()
    if self.in_splitter:	# Splitter window has no X axis scale
      self.height = h
      self.originY = h
    else:
      self.height = h - self.chary		# Leave space for X scale
      self.originY = self.height - self.offsetY
    if self.originY < 0:
      self.originY = 0
    self.MakeYScale()
    self.display.SetHeight(self.originY)
    self.display.scale = self.scale
    self.doResize = False
    self.Refresh()
  def ChangeYscale(self, y_scale):
    self.y_scale = y_scale
    self.doResize = True
  def ChangeYzero(self, y_zero):
    self.y_zero = y_zero
    self.doResize = True
  def ChangeZoom(self, zoom, deltaf):
    self.zoom = zoom
    self.zoom_deltaf = deltaf
    self.doResize = True
  def MakeYScale(self):
    chary = self.chary
    scale = (self.originY - chary)  * 10 // (self.y_scale + 20)	# Number of pixels per 10 dB
    scale = max(1, scale)
    q = (self.originY - chary ) // scale // 2
    zeroDB = chary + q * scale - self.y_zero * scale // 10
    if zeroDB > chary:
      zeroDB = chary
    self.scale = scale
    self.zeroDB = zeroDB
    self.display.zeroDB = self.zeroDB
    QS.record_graph(self.originX, self.zeroDB, self.scale)
  def MakeYTicks(self, dc):
    chary = self.chary
    x1 = self.originX - self.tick * 3	# left of tick mark
    x2 = self.originX - 1		# x location of y axis
    x3 = self.originX + self.graph_width	# end of graph data
    dc.SetPen(self.pen_tick)
    dc.DrawLine(x2, 0, x2, self.originY + 1)	# y axis
    y = self.zeroDB
    del self.y_ticks[:]
    y_old = y
    for i in range(0, -99999, -10):
      if y >= chary // 2:
        dc.SetPen(self.pen_tick)
        dc.DrawLine(x1, y, x2, y)	# y tick
        self.y_ticks.append(y)
        t = repr(i)
        w, h = dc.GetTextExtent(t)
        # draw text on Y axis
        if y - y_old > h:
          if y + h // 2 <= self.originY:	
            dc.DrawText(repr(i), x1 - w, y - h // 2)
          elif h < self.scale:
            dc.DrawText(repr(i), x1 - w, self.originY - h)
          y_old = y
      y = y + self.scale
      if y >= self.originY - 3:
        break
  def MakeXTicks(self, dc):
    sample_rate = int(self.sample_rate * self.zoom)
    VFO = self.VFO + self.zoom_deltaf
    originY = self.originY
    x3 = self.originX + self.graph_width	# end of fft data
    charx , z = dc.GetTextExtent('-30000XX')
    tick0 = self.tick
    tick1 = tick0 * 2
    tick2 = tick0 * 3
    # Draw the X axis
    dc.SetPen(self.pen_tick)
    dc.DrawLine(self.originX, originY, x3, originY)
    # Draw the band plan colors below the X axis
    x = self.originX
    f = float(x - self.x0) * sample_rate / self.data_width
    c = None
    y = originY + 1
    for freq, color in conf.BandPlan:
      freq -= VFO
      if f < freq:
        xend = int(self.x0 + float(freq) * self.data_width / sample_rate + 0.5)
        if c is not None:
          dc.SetPen(wx.TRANSPARENT_PEN)
          dc.SetBrush(wx.Brush(c))
          dc.DrawRectangle(x, y, min(x3, xend) - x, tick0)  # x axis
        if xend >= x3:
          break
        x = xend
        f = freq
      c = color
    # check the width of the frequency label versus frequency span
    df = charx * sample_rate // self.data_width
    if VFO >= 10E9:     # Leave room for big labels
      df *= 1.33
    elif VFO >= 1E9:
      df *= 1.17
    # tfreq: tick frequency for labels in Hertz
    # stick: small tick in Hertz
    # mtick: medium tick
    # ltick: large tick
    s2 = 1000
    tfreq = None
    while tfreq is None:
      if df < s2:
        tfreq = s2
        stick = s2 // 10
        mtick = s2 // 2
        ltick = tfreq
      elif df < s2 * 2:
        tfreq = s2 * 2
        stick = s2 // 10
        mtick = s2 // 2
        ltick = s2
      elif df < s2 * 5:
        tfreq = s2 * 5
        stick = s2 // 2
        mtick = s2
        ltick = tfreq
      s2 *= 10
    # Draw the X axis ticks and frequency in kHz
    dc.SetPen(self.pen_tick)
    freq1 = VFO - sample_rate // 2
    freq1 = (freq1 // stick) * stick
    freq2 = freq1 + sample_rate + stick + 1
    y_end = 0
    for f in range (freq1, freq2, stick):
      x = self.x0 + int(float(f - VFO) / sample_rate * self.data_width)
      if self.originX <= x <= x3:
        if f % ltick == 0:		# large tick
          dc.DrawLine(x, originY, x, originY + tick2)
        elif f % mtick == 0:	# medium tick
          dc.DrawLine(x, originY, x, originY + tick1)
        else:					# small tick
          dc.DrawLine(x, originY, x, originY + tick0)
        if f % tfreq == 0:		# place frequency label
          t = str(f//1000)
          w, h = dc.GetTextExtent(t)
          dc.DrawText(t, x - w // 2, originY + tick2)
          y_end = originY + tick2 + h
    if y_end:		# mark the center of the display
      dc.DrawLine(self.x0, y_end, self.x0, application.screen_height)
  def OnGraphData(self, data):
    i1 = (self.data_width - self.graph_width) // 2
    i2 = i1 + self.graph_width
    self.display.OnGraphData(data[i1:i2])
  def SetVFO(self, vfo):
    self.VFO = vfo
    self.doResize = True
  def SetTxFreq(self, tx_freq, rx_freq):
    sample_rate = int(self.sample_rate * self.zoom)
    self.txFreq = tx_freq
    tx_x = self.x0 + int(float(tx_freq - self.zoom_deltaf) / sample_rate * self.data_width)
    self.tuningX = tx_x
    rx_x = self.x0 + int(float(rx_freq - self.zoom_deltaf) / sample_rate * self.data_width)
    if abs(tx_x - rx_x) < 2:		# Do not display Rx line for small frequency offset
      self.display.SetTuningLine(tx_x - self.originX, 0)
    else:
      self.display.SetTuningLine(tx_x - self.originX, rx_x - self.originX)
  def GetFilterDisplayXWR(self, rx_filters):
    mode = self.filter_mode
    rit = self.ritFreq
    if rx_filters:	# return Rx filter
      bandwidth = self.filter_bandwidth
      center = self.filter_center
    else:	# return Tx filter
      bandwidth, center = get_filter_tx(mode)
    x = center - bandwidth // 2
    scale = 1.0 / self.zoom / self.sample_rate * self.data_width
    x = int(x * scale + 0.5)
    bandwidth = int(bandwidth * scale + 0.5)
    if bandwidth < 2:
      bandwidth = 1
    rit = int(rit * scale + 0.5)
    #print(mode, x, bandwidth, rit, center )
    return x, bandwidth, rit		# Starting x, bandwidth and RIT frequency
  def GetFilterDisplayRit(self):
    rit = self.ritFreq
    scale = 1.0 / self.zoom / self.sample_rate * self.data_width
    rit = int(rit * scale + 0.5)
    return rit
  def GetMousePosition(self, event):
    """For mouse clicks in our display, translate to our screen coordinates."""
    mouse_x, mouse_y = event.GetPosition()
    win = event.GetEventObject()
    if win is not self:
      x, y = win.GetPosition().Get()
      mouse_x += x
      mouse_y += y
    return mouse_x, mouse_y
  def FreqRound(self, tune, vfo):
    if conf.freq_spacing and not conf.freq_round_ssb:
      freq = tune + vfo
      n = int(freq) - conf.freq_base
      if n >= 0:
        n = (n + conf.freq_spacing // 2) // conf.freq_spacing
      else:
        n = - ( - n + conf.freq_spacing // 2) // conf.freq_spacing
      freq = conf.freq_base + n * conf.freq_spacing
      return freq - vfo
    else:
      return tune
  def OnRightDown(self, event):
    sample_rate = int(self.sample_rate * self.zoom)
    VFO = self.VFO + self.zoom_deltaf
    mouse_x, mouse_y = self.GetMousePosition(event)
    freq = float(mouse_x - self.x0) * sample_rate / self.data_width
    freq = int(freq)
    if VFO > 0:
      vfo = VFO + freq - self.zoom_deltaf
      if sample_rate > 40000:
        vfo = (vfo + 5000) // 10000 * 10000	# round to even number
      elif sample_rate > 5000:
        vfo = (vfo + 500) // 1000 * 1000
      else:
        vfo = (vfo + 50) // 100 * 100
      tune = freq + VFO - vfo
      tune = self.FreqRound(tune, vfo)
      self.ChangeHwFrequency(tune, vfo, 'MouseBtn3', event=event)
  def OnLeftDown(self, event):
    sample_rate = int(self.sample_rate * self.zoom)
    mouse_x, mouse_y = self.GetMousePosition(event)
    if mouse_x <= self.originX:		# click left of Y axis
      return
    if mouse_x >= self.originX + self.graph_width:	# click past FFT data
      return
    shift = wx.GetKeyState(wx.WXK_SHIFT)
    if shift:
      mouse_x -= self.filter_center * self.data_width / sample_rate
    self.mouse_x = mouse_x
    x = mouse_x - self.originX
    if self.split_unavailable:
      self.mouse_is_rx = False
    elif application.split_rxtx and application.split_locktx:
      self.mouse_is_rx = True
    elif self.display.tune_rx and abs(x - self.display.tune_tx) > abs(x - self.display.tune_rx):
      self.mouse_is_rx = True
    else:
      self.mouse_is_rx = False
    if mouse_y < self.originY:		# click above X axis
      freq = float(mouse_x - self.x0) * sample_rate / self.data_width + self.zoom_deltaf
      freq = int(freq)
      if self.mouse_is_rx:
        application.rxFreq = freq
        application.screen.SetTxFreq(self.txFreq, freq)
        QS.set_tune(freq + application.ritFreq, self.txFreq)
      else:
        rnd = conf.freq_round_ssb
        if rnd and not shift:
          if application.mode in ('LSB', 'USB', 'AM', 'FM', 'FDV-U', 'FDV-L'):
            freq = (freq + rnd//2) // rnd * rnd
        else:
          freq = self.FreqRound(freq, self.VFO)
        self.ChangeHwFrequency(freq, self.VFO, 'MouseBtn1', event=event)
    self.CaptureMouse()
  def OnLeftUp(self, event):
    if self.HasCapture():
      self.ReleaseMouse()
      freq = self.FreqRound(self.txFreq, self.VFO)
      if freq != self.txFreq:
        self.ChangeHwFrequency(freq, self.VFO, 'MouseMotion', event=event)
  def OnMotion(self, event):
    sample_rate = int(self.sample_rate * self.zoom)
    if event.Dragging() and event.LeftIsDown():
      mouse_x, mouse_y = self.GetMousePosition(event)
      if wx.GetKeyState(wx.WXK_SHIFT):
        mouse_x -= self.filter_center * self.data_width / sample_rate
      if conf.mouse_tune_method:		# Mouse motion changes the VFO frequency
        x = (mouse_x - self.mouse_x)	# Thanks to VK6JBL
        self.mouse_x = mouse_x
        freq = float(x) * sample_rate / self.data_width
        freq = int(freq)
        self.ChangeHwFrequency(self.txFreq, self.VFO - freq, 'MouseMotion', event=event)
      else:		# Mouse motion changes the tuning frequency
        # Frequency changes more rapidly for higher mouse Y position
        speed = max(10, self.originY - mouse_y) / float(self.originY + 1)
        x = (mouse_x - self.mouse_x)
        self.mouse_x = mouse_x
        freq = speed * x * sample_rate / self.data_width
        freq = int(freq)
        if self.mouse_is_rx:	# Mouse motion changes the receive frequency
          application.rxFreq += freq
          application.screen.SetTxFreq(self.txFreq, application.rxFreq)
          QS.set_tune(application.rxFreq + application.ritFreq, self.txFreq)
        else:					# Mouse motion changes the transmit frequency
          self.ChangeHwFrequency(self.txFreq + freq, self.VFO, 'MouseMotion', event=event)
  def OnWheel(self, event):
    if conf.freq_spacing:
      wm = conf.freq_spacing
    else:
      wm = self.WheelMod		# Round frequency when using mouse wheel
    mouse_x, mouse_y = self.GetMousePosition(event)
    x = mouse_x - self.originX
    if self.split_unavailable:
      self.mouse_is_rx = False
    elif application.split_rxtx and application.split_locktx:
      self.mouse_is_rx = True
    elif self.display.tune_rx and abs(x - self.display.tune_tx) > abs(x - self.display.tune_rx):
      self.mouse_is_rx = True
    else:
      self.mouse_is_rx = False
    if self.mouse_is_rx:
      freq = application.rxFreq + self.VFO + wm * event.GetWheelRotation() // event.GetWheelDelta()
      if conf.freq_spacing:
        freq = self.FreqRound(freq, 0)
      elif freq >= 0:
        freq = freq // wm * wm
      else:		# freq can be negative when the VFO is zero
        freq = - (- freq // wm * wm)
      tune = freq - self.VFO
      application.rxFreq = tune
      application.screen.SetTxFreq(self.txFreq, tune)
      QS.set_tune(tune + application.ritFreq, self.txFreq)
    else:
      freq = self.txFreq + self.VFO + wm * event.GetWheelRotation() // event.GetWheelDelta()
      if conf.freq_spacing:
        freq = self.FreqRound(freq, 0)
      elif freq >= 0:
        freq = freq // wm * wm
      else:		# freq can be negative when the VFO is zero
        freq = - (- freq // wm * wm)
      tune = freq - self.VFO
      self.ChangeHwFrequency(tune, self.VFO, 'MouseWheel', event=event)
  def ChangeHwFrequency(self, tune, vfo, source='', band='', event=None):
    application.ChangeHwFrequency(tune, vfo, source, band, event)
  def PeakHold(self, name):
    if name == 'GraphP1':
      self.display.peak_hold = int(self.display.scale * conf.graph_peak_hold_1)
    elif name == 'GraphP2':
      self.display.peak_hold = int(self.display.scale * conf.graph_peak_hold_2)
    else:
      self.display.peak_hold = 9999
    if self.display.peak_hold < 1:
      self.display.peak_hold = 1

class StationScreen(wx.Window):		# This code was contributed by Christof, DJ4CM.  Many Thanks!!
  """Create a window below the graph X axis to display interesting frequencies."""
  def __init__(self, parent, width, lines):
    self.lineMargin = 2
    self.lines = lines
    self.mouse_x = 0
    self.stationList = []
    graph = self.graph = application.graph
    height = lines * (graph.GetCharHeight() + self.lineMargin)	# The height may be zero
    wx.Window.__init__(self, parent, size=(graph.width, height), style = wx.NO_BORDER)
    self.font = wx.Font(conf.graph_font_size, wx.FONTFAMILY_SWISS, wx.NORMAL,
          wx.FONTWEIGHT_NORMAL, False, conf.quisk_typeface)
    self.SetFont(self.font)
    self.SetBackgroundColour(conf.color_graph)
    self.width = application.screen_width
    self.Bind(wx.EVT_PAINT, self.OnPaint)
    if lines:
      self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
      self.Bind(wx.EVT_MOTION, self.OnMotion)
      self.Bind(wx.EVT_LEAVE_WINDOW, self.OnLeaveWindow)
      # handle station info
      self.stationWindow = wx.PopupWindow (parent)
      self.stationInfo = wx.richtext.RichTextCtrl(self.stationWindow)
      self.stationInfo.SetFont(wx.Font(conf.status_font_size, wx.FONTFAMILY_SWISS, wx.NORMAL,
          wx.FONTWEIGHT_NORMAL, False, conf.quisk_typeface))
      self.stationWindow.Hide(); 
      self.firstStationInRange = None
      self.lastStationX = 0
      self.nrStationInRange = 0
      self.tunedStation = 0
  def OnPaint(self, event):
    dc = wx.PaintDC(self)
    if not self.lines:
      return
    dc.SetFont(self.font)
    graph = self.graph
    dc.SetTextForeground(conf.color_graphlabels)
    dc.SetPen(graph.pen_tick)
    originX = graph.originX
    originY = graph.originY
    endX = originX + graph.graph_width    # end of fft data
    sample_rate = int(graph.sample_rate * graph.zoom)
    VFO = graph.VFO + graph.zoom_deltaf
    hl = self.GetCharHeight()
    y = 0
    for i in range (self.lines):
      dc.DrawLine(originX, y, endX, y)
      y += hl + self.lineMargin
    # create a sorted list of favorites in the frequency range  
    freq1 = VFO - sample_rate // 2
    freq2 = VFO + sample_rate // 2
    self.stationList = []
    fav = application.config_screen.favorites
    for row in range (fav.GetNumberRows()):
      fav_f = fav.GetCellValue(row, 1) 
      if fav_f:
        try:
          fav_f = str2freq(fav_f)
          if freq1 < fav_f < freq2:
            self.stationList.append((fav_f, conf.Xsym_stat_fav, fav.GetCellValue(row, 0),
                fav.GetCellValue(row, 2), fav.GetCellValue(row, 3)))
        except ValueError:
          pass            
    # add memory stations
    for mem_f, mem_band, mem_vfo, mem_txfreq, mem_mode in application.memoryState:
      if freq1 < mem_f < freq2:
        self.stationList.append((mem_f, conf.Xsym_stat_mem, '', mem_mode, ''))
    #add dx spots
    if application.dxCluster:
      for entry in application.dxCluster.dxSpots:
        if freq1 < entry.getFreq() < freq2:
          for i in range (0, entry.getLen()):
            descr = entry.getSpotter(i) + '\t' + entry.getTime(i) + '\t' + entry.getLocation(i) + '\n' + entry.getComment(i)
            if i < entry.getLen()-1:
              descr += '\n'
          self.stationList.append((entry.freq, conf.Xsym_stat_dx, entry.dx, '', descr))           
    # draw stations on graph
    self.stationList.sort(cmp=None, key=None, reverse=False)
    lastX = []
    line = 0
    for i in range (0, self.lines):
      lastX.append(graph.width)
    for statFreq, symbol, statName, statMode, statDscr in reversed (self.stationList):
      ws = dc.GetTextExtent(symbol)[0]
      statX = graph.x0 + int(float(statFreq - VFO) / sample_rate * graph.data_width)
      w, h = dc.GetTextExtent(statName)
      # shorten name until it fits into remaining space
      maxLen = 25
      tName = statName 
      while (w > lastX[line] - statX - ws - 4) and maxLen > 0:
        maxLen -= 1
        tName = statName[:maxLen] + '..'
        w, h = dc.GetTextExtent(tName)
      dc.DrawLine(statX, line * (hl+self.lineMargin), statX, line * (hl+self.lineMargin) + 4)                    
      dc.DrawText(symbol + ' ' + tName, statX - ws//2, line * (hl+self.lineMargin) + self.lineMargin//2+1)
      lastX[line] = statX
      line = (line+1)%self.lines
  def OnLeftDown(self, event):
    if self.firstStationInRange != None:
      # tune to station
      if self.tunedStation >= self.nrStationInRange:
        self.tunedStation = 0      
      freq, symbol, name, mode, dscr = self.stationList[self.firstStationInRange+self.tunedStation]
      self.tunedStation += 1
      if mode != '': # information about mode available
        mode = mode.upper()
        application.OnBtnMode(None, mode)
      application.ChangeRxTxFrequency(None, freq)
  def OnMotion(self, event):
    mouse_x, mouse_y = event.GetPosition()
    x = (mouse_x - self.mouse_x)
    application.isTuning = False
    # show detailed station info
    if abs(self.lastStationX - mouse_x) > 30:
      self.firstStationInRange = None   
    found = False
    graph = self.graph
    sample_rate = int(graph.sample_rate * graph.zoom)
    VFO = graph.VFO + graph.zoom_deltaf
    if abs(x) > 5: # ignore small mouse moves
      for index in range (0, len(self.stationList)):
        statFreq, symbol, statName, statMode, statDscr = self.stationList[index]
        statX = graph.x0 + int(float(statFreq - VFO) / sample_rate * graph.data_width)
        if abs(mouse_x-statX) < 10: 
          self.lastStationX = mouse_x
          if found == False:
            self.firstStationInRange = index
            self.nrStationInRange = 0
            self.stationInfo.Clear()
            found = True
          self.nrStationInRange += 1
          attr = self.stationInfo.GetBasicStyle()
          attr.SetFlags(wx.TEXT_ATTR_TABS)
          attr.SetTabs((40, 400, 700))
          self.stationInfo.SetBasicStyle(attr)
          self.stationInfo.BeginSymbolBullet(symbol, 0, 40) 
          self.stationInfo.BeginBold()      
          self.stationInfo.WriteText(statName + '\t')
          self.stationInfo.EndBold()
          self.stationInfo.WriteText (str(statFreq) + ' Hz\t' + statMode)
          self.stationInfo.Newline()
          self.stationInfo.EndSymbolBullet() 
          self.stationInfo.BeginLeftIndent(40)
          if len(statDscr) > 0:
            self.stationInfo.WriteText(statDscr)
            self.stationInfo.Newline()
          self.stationInfo.EndLeftIndent()   
          self.mouse_x = mouse_x   
    if self.firstStationInRange != None:
      line = self.stationInfo.GetVisibleLineForCaretPosition(self.stationInfo.GetCaretPosition()) 
      cy = line.GetAbsolutePosition()[1]
      self.stationWindow.SetClientSize((340, cy+2))
      self.stationInfo.SetClientSize((340, cy+2))
      # convert coordinates to screen
      sx, sy = self.ClientToScreen(wx.Point(mouse_x, mouse_y))
      w, h = self.stationInfo.GetClientSize()
      self.stationWindow.Move((sx - w * sx//graph.width, sy - h - 4)) 
      if not self.stationWindow.IsShown():
        self.stationWindow.Show()
    else:
      self.stationWindow.Hide()
  def OnLeaveWindow(self, event):
    self.stationWindow.Hide() 
                              

class WaterfallDisplay(wx.Window):
  """Create a waterfall display within the waterfall screen."""
  def __init__(self, parent, x, y, graph_width, height, margin):
    wx.Window.__init__(self, parent,
       pos = (x, y),
       size = (graph_width, height),
       style = wx.NO_BORDER)
    self.parent = parent
    self.graph_width = graph_width
    self.margin = margin
    self.height = 10
    self.zoom = 1.0
    self.zoom_deltaf = 0
    self.rf_gain = 0	# Keep waterfall colors constant for variable RF gain
    self.sample_rate = application.sample_rate
    self.SetBackgroundColour('Black')
    self.Bind(wx.EVT_PAINT, self.OnPaint)
    self.Bind(wx.EVT_LEFT_DOWN, parent.OnLeftDown)
    self.Bind(wx.EVT_RIGHT_DOWN, parent.OnRightDown)
    self.Bind(wx.EVT_LEFT_UP, parent.OnLeftUp)
    self.Bind(wx.EVT_MOTION, parent.OnMotion)
    self.Bind(wx.EVT_MOUSEWHEEL, parent.OnWheel)
    self.tune_tx = graph_width // 2	# Current X position of the Tx tuning line
    self.tune_rx = 0				# Current X position of Rx tuning line or zero
    self.marginPen = wx.Pen(conf.color_graph, 1)
    self.tuningPen = wx.Pen('White', 3)
    self.tuningPenTx = wx.Pen(conf.color_txline, 3)
    self.tuningPenRx = wx.Pen(conf.color_rxline, 3)
    self.filterBrush = wx.Brush(conf.color_bandwidth, wx.SOLID)
    #self.backgroundBrush = wx.Brush(conf.color_graph)
    # Size of top faster scroll region is (top_key + 2) * (top_key - 1) // 2
    self.top_key = 8
    self.top_size = (self.top_key + 2) * (self.top_key - 1) // 2
    # Make the palette
    if conf.waterfall_palette == 'B':
      pal2 = conf.waterfallPaletteB
    elif conf.waterfall_palette == 'C':
      pal2 = conf.waterfallPaletteC
    else:
      pal2 = conf.waterfallPalette
    red = []
    green = []
    blue = []
    n = 0
    for i in range(256):
      if i > pal2[n+1][0]:
         n = n + 1
      red.append((i - pal2[n][0]) *
       (pal2[n+1][1] - pal2[n][1]) //
       (pal2[n+1][0] - pal2[n][0]) + pal2[n][1])
      green.append((i - pal2[n][0]) *
       (pal2[n+1][2] - pal2[n][2]) //
       (pal2[n+1][0] - pal2[n][0]) + pal2[n][2])
      blue.append((i - pal2[n][0]) *
       (pal2[n+1][3] - pal2[n][3]) //
       (pal2[n+1][0] - pal2[n][0]) + pal2[n][3])
    self.red = red
    self.green = green
    self.blue = blue
    row = "\000\000\000\000"
    if wxVersion in ('2', '3'):
      bmp = wx.BitmapFromBufferRGBA(1, 1, row)
    else:
      bmp = wx.Bitmap().FromBufferRGBA(1, 1, row)
    bmp.x_origin = 0
    self.bitmaps = [bmp] * application.screen_height
    if sys.platform == 'win32':
      self.Bind(wx.EVT_ENTER_WINDOW, self.OnEnter)
  def OnEnter(self, event):
    if not application.w_phase:
      self.SetFocus()	# Set focus so we get mouse wheel events
  def OnPaint(self, event):
    sample_rate = int(self.sample_rate * self.zoom)
    dc = wx.BufferedPaintDC(self)
    dc.SetTextForeground(conf.color_graphlabels)
    dc.SetBackground(wx.Brush('Black'))
    dc.Clear()
    rit = self.DrawFilter(dc)
    dc.SetLogicalFunction(wx.COPY)
    x_origin = int(float(self.VFO) / sample_rate * self.data_width + 0.5)
    y = self.margin
    index = 0
    if conf.waterfall_scroll_mode:	# Draw the first few lines multiple times
      for i in range(self.top_key, 1, -1):
        b = self.bitmaps[index]
        x = b.x_origin - x_origin
        for j in range(0, i):
          dc.DrawBitmap(b, x, y)
          y += 1
        index += 1
    while y < self.height:
      b = self.bitmaps[index]
      x = b.x_origin - x_origin
      dc.DrawBitmap(b, x, y)
      y += 1
      index += 1
    dc.SetPen(self.tuningPen)
    dc.SetLogicalFunction(wx.XOR)
    dc.DrawLine(self.tune_tx, self.margin, self.tune_tx, self.height)
    if self.tune_rx:
      dc.DrawLine(self.tune_rx, self.margin, self.tune_rx, self.height)
  def SetHeight(self, height):
    self.height = height
    self.SetSize((self.graph_width, height))
  def DrawFilter(self, dc):
    # Erase area at the top of the waterfall
    dc.SetPen(wx.TRANSPARENT_PEN)
    dc.SetLogicalFunction(wx.COPY)
    dc.SetBrush(self.parent.backgroundBrush)
    dc.DrawRectangle(0, 0, self.graph_width, self.margin)
    # Draw the filter and top tuning lines
    scale = 1.0 / self.zoom / self.sample_rate * self.data_width
    dc.SetBrush(self.filterBrush)
    if self.tune_rx:
      x, w, rit = self.parent.GetFilterDisplayXWR(rx_filters=False)
      dc.DrawRectangle(self.tune_tx + x, 0, w, self.margin)
      x, w, rit = self.parent.GetFilterDisplayXWR(rx_filters=True)
      dc.DrawRectangle(self.tune_rx + rit + x, 0, w, self.margin)
      dc.SetPen(self.tuningPenRx)
      dc.DrawLine(self.tune_rx, 0, self.tune_rx, self.margin)
    else:
      x, w, rit = self.parent.GetFilterDisplayXWR(rx_filters=True)
      dc.DrawRectangle(self.tune_tx + rit + x, 0, w, self.margin)
    dc.SetPen(self.tuningPenTx)
    dc.DrawLine(self.tune_tx, 0, self.tune_tx, self.margin)
    return rit
  def OnGraphData(self, data, y_zero, y_scale):
    sample_rate = int(self.sample_rate * self.zoom)
    #T('graph start')
    row = ''		# Make a new row of pixels for a one-line image
    gain = self.rf_gain
    for x in data:	# x is -130 to 0, or so (dB)
      l = int((x - gain + y_zero // 3 + 100) * y_scale / 10)
      l = max(l, 0)
      l = min(l, 255)
      row = row + "%c%c%c%c" % (chr(self.red[l]), chr(self.green[l]), chr(self.blue[l]), chr(255))
    #T('graph string')
    if wxVersion in ('2', '3'):
      bmp = wx.BitmapFromBufferRGBA(len(row) // 4, 1, row)
    else:
      bmp = wx.Bitmap().FromBufferRGBA(len(row) // 4, 1, row)
    bmp.x_origin = int(float(self.VFO) / sample_rate * self.data_width + 0.5)
    self.bitmaps.insert(0, bmp)
    del self.bitmaps[-1]
    #self.ScrollWindow(0, 1, None)
    #self.Refresh(False, (0, 0, self.graph_width, self.top_size + self.margin))
    self.Refresh(False)
    #T('graph end')
  def SetTuningLine(self, tune_tx, tune_rx):
    dc = wx.ClientDC(self)
    rit = self.DrawFilter(dc)
    dc.SetPen(self.tuningPen)
    dc.SetLogicalFunction(wx.XOR)
    dc.DrawLine(self.tune_tx, self.margin, self.tune_tx, self.height)
    if self.tune_rx:
      dc.DrawLine(self.tune_rx, self.margin, self.tune_rx, self.height)
      dc.DrawLine(tune_rx, self.margin, tune_rx, self.height)
    dc.DrawLine(tune_tx, self.margin, tune_tx, self.height)
    self.tune_tx = tune_tx
    self.tune_rx = tune_rx
  def ChangeZoom(self, zoom, deltaf):
    self.zoom = zoom
    self.zoom_deltaf = deltaf

class WaterfallScreen(wx.SplitterWindow):
  """Create a splitter window with a graph screen and a waterfall screen"""
  def __init__(self, frame, width, data_width, graph_width):
    self.y_scale = conf.waterfall_y_scale
    self.y_zero = conf.waterfall_y_zero
    wx.SplitterWindow.__init__(self, frame)
    self.SetSizeHints(width, -1, width)
    self.SetSashGravity(0.50)
    self.SetMinimumPaneSize(1)
    self.SetSize((width, conf.waterfall_graph_size + 100))	# be able to set sash size
    self.pane1 = GraphScreen(self, data_width, graph_width, 1)
    self.pane2 = WaterfallPane(self, data_width, graph_width)
    self.SplitHorizontally(self.pane1, self.pane2, conf.waterfall_graph_size)
  def SetDisplayMsg(self, text=''):
    self.pane1.SetDisplayMsg(text)
  def ScrollMsg(self, char):	# Add a character to a scrolling message
    self.pane1.ScrollMsg(char)
  def OnIdle(self, event):
    self.pane1.OnIdle(event)
    self.pane2.OnIdle(event)
  def SetTxFreq(self, tx_freq, rx_freq):
    self.pane1.SetTxFreq(tx_freq, rx_freq)
    self.pane2.SetTxFreq(tx_freq, rx_freq)
  def SetVFO(self, vfo):
    self.pane1.SetVFO(vfo)
    self.pane2.SetVFO(vfo) 
  def ChangeYscale(self, y_scale):		# Test if the shift key is down
    if wx.GetKeyState(wx.WXK_SHIFT):	# Set graph screen
      self.pane1.ChangeYscale(y_scale)
    else:			# Set waterfall screen
      self.y_scale = y_scale
      self.pane2.ChangeYscale(y_scale)
  def ChangeYzero(self, y_zero):		# Test if the shift key is down
    if wx.GetKeyState(wx.WXK_SHIFT):	# Set graph screen
      self.pane1.ChangeYzero(y_zero)
    else:			# Set waterfall screen
      self.y_zero = y_zero
      self.pane2.ChangeYzero(y_zero)
  def SetPane2(self, ysz):
    y_scale, y_zero = ysz
    self.y_scale = y_scale
    self.pane2.ChangeYscale(y_scale)
    self.y_zero = y_zero
    self.pane2.ChangeYzero(y_zero)
  def OnGraphData(self, data):
    self.pane1.OnGraphData(data)
    self.pane2.OnGraphData(data)
  def ChangeRfGain(self, gain):		# Set the correction for RF gain
    self.pane2.display.rf_gain = gain

class WaterfallPane(GraphScreen):
  """Create a waterfall screen with an X axis and a waterfall display."""
  def __init__(self, frame, data_width, graph_width):
    GraphScreen.__init__(self, frame, data_width, graph_width)
    self.y_scale = conf.waterfall_y_scale
    self.y_zero = conf.waterfall_y_zero
    self.oldVFO = self.VFO
    self.filter_mode = 'AM'
    self.filter_bandwidth = 0
    self.filter_center = 0
    self.ritFreq = 0				# receive incremental tuning frequency offset
  def MakeDisplay(self):
    self.display = WaterfallDisplay(self, self.originX, 0, self.graph_width, 5, self.chary)
    self.display.VFO = self.VFO
    self.display.data_width = self.data_width
  def SetVFO(self, vfo):
    GraphScreen.SetVFO(self, vfo)
    self.display.VFO = vfo
    if self.oldVFO != vfo:
      self.oldVFO = vfo
      self.Refresh()
  def MakeYTicks(self, dc):
    pass
  def ChangeYscale(self, y_scale):
    self.y_scale = y_scale
  def ChangeYzero(self, y_zero):
    self.y_zero = y_zero
  def OnGraphData(self, data):
    i1 = (self.data_width - self.graph_width) // 2
    i2 = i1 + self.graph_width
    self.display.OnGraphData(data[i1:i2], self.y_zero, self.y_scale)

class MultiRxGraph(GraphScreen):
  # The screen showing each added receiver
  the_modes = ('CWL', 'CWU', 'LSB', 'USB', 'AM', 'FM', 'DGT-U', 'DGT-L', 'DGT-FM', 'DGT-IQ')
  def __init__(self, parent, data_width, graph_width, index):
    multi_rx = application.multi_rx_screen
    width = multi_rx.rx_data_width
    GraphScreen.__init__(self, parent, width, width)
    self.graph_display = self.display
    self.waterfall_display = WaterfallDisplay(self, self.originX, 0, self.graph_width, 5, self.chary)
    self.waterfall_display.Hide()
    self.waterfall_display.VFO = self.VFO
    self.waterfall_display.data_width = self.data_width
    self.waterfall_y_scale = conf.waterfall_y_scale
    self.waterfall_y_zero = conf.waterfall_y_zero
    self.split_unavailable = True
    width = self.originX + self.graph_width
    self.tabX = width + (multi_rx.graph.width - width - multi_rx.rx_btn_width) // 2
    self.popupX = self.tabX - multi_rx.rx_btn_width * 2
    self.multirx_index = index
    self.is_playing = False
    self.mode_index = 0
    self.band = '40'
    # Create controls
    posY = 0
    half_width = multi_rx.rx_btn_width // 2
    half_size = half_width, multi_rx.rx_btn_height
    self.rx_btn = QuiskPushbutton(self, self.OnPopButton, "Rx %d .." % (index + 1))
    self.rx_btn.SetSize(half_size)
    self.rx_btn.SetPosition((self.tabX, posY))
    self.play_btn = QuiskCheckbutton(self, self.OnPlayButton, "Play")
    self.play_btn.SetSize(half_size)
    self.play_btn.SetPosition((self.tabX + half_width, posY))
    posY += multi_rx.rx_btn_height
    btn1 = QuiskPushbutton(self, self.OnBtnDownBand, conf.Xbtn_text_range_dn, use_right=True)
    btn2 = QuiskPushbutton(self, self.OnBtnUpBand, conf.Xbtn_text_range_up, use_right=True)
    btn1.SetSize(half_size)
    btn2.SetSize(half_size)
    btn1.SetPosition((self.tabX, posY))
    btn2.SetPosition((self.tabX + half_width, posY))
    posY += multi_rx.rx_btn_height
    self.sliderYs = SliderBoxV(self, 'Ys', self.y_scale, 160, self.OnChangeYscale, True)
    self.sliderYz = SliderBoxV(self, 'Yz', self.y_zero, 160, self.OnChangeYzero, True)
    x = self.tabX + (half_width * 2 - self.sliderYs.width - self.sliderYz.width) // 2
    self.sliderYs.SetDimension(x, posY, self.sliderYs.width, 100)
    x += self.sliderYs.width
    self.sliderYz.SetDimension(x, posY, self.sliderYz.width, 100)
    # Create menu
    self.multi_rx_menu = wx.Menu()
    item = self.multi_rx_menu.Append(-1, 'Show graph')
    self.Bind(wx.EVT_MENU, self.OnShowGraph, item)
    item = self.multi_rx_menu.Append(-1, 'Show waterfall')
    self.Bind(wx.EVT_MENU, self.OnShowWaterfall, item)
    self.multi_rx_menu.AppendSeparator()
    menu = wx.Menu()
    self.multi_rx_menu.AppendSubMenu(menu, "Band")
    for band in conf.bandLabels:
      if type(band) not in (UnicodeType, StringType):
        band = band[0]
        if band == 'Time':
          continue
      item = menu.Append(-1, band)
      self.Bind(wx.EVT_MENU, self.OnChangeBand, item)
    self.mode_menu = wx.Menu()
    self.multi_rx_menu.AppendSubMenu(self.mode_menu, "Mode")
    for mode in self.the_modes:
      item = self.mode_menu.AppendRadioItem(-1, mode)
      self.Bind(wx.EVT_MENU, self.OnChangeMode, item)
    self.filter_menu = wx.Menu()
    self.multi_rx_menu.AppendSubMenu(self.filter_menu, "Filter")
    for i in range(6):
      item = self.filter_menu.AppendRadioItem(-1, '0')
      self.Bind(wx.EVT_MENU, self.OnChangeFilter, item)
    self.multi_rx_menu.AppendSeparator()
    item = self.multi_rx_menu.Append(-1, 'Delete receiver')
    self.Bind(wx.EVT_MENU, self.OnDeleteReceiver, item)
    self.ChangeBand(application.lastBand)
    if multi_rx.rx_zero == multi_rx.waterfall:
      self.OnShowWaterfall()
  def ResizeGraph(self):
    GraphScreen.ResizeGraph(self)
    w, h = self.GetClientSize()
    x, y = self.sliderYs.GetPosition()
    height = max(h - y, self.sliderYs.text_height * 2)
    self.sliderYs.SetDimension(x, y, self.sliderYs.width, height)
    x, y = self.sliderYz.GetPosition()
    self.sliderYz.SetDimension(x, y, self.sliderYz.width, height)
  def MakeYTicks(self, dc):
    if self.display == self.graph_display:
      GraphScreen.MakeYTicks(self, dc)
  def OnPopButton(self, event):
    pos = (self.popupX, 10)
    self.PopupMenu(self.multi_rx_menu, pos)
  def OnDeleteReceiver(self, event):
    if self.is_playing:
      QS.set_multirx_play_channel(-1)
    application.multi_rx_screen.DeleteReceiver(self)
  def OnShowGraph(self, event):
    self.waterfall_display.Hide()
    self.display = self.graph_display
    self.SetTxFreq(self.txFreq, self.txFreq)
    self.sliderYs.SetValue(self.y_scale)
    self.sliderYz.SetValue(self.y_zero)
    self.display.Show()
    self.doResize = True
  def OnShowWaterfall(self, event=None):
    self.graph_display.Hide()
    self.display = self.waterfall_display
    self.SetTxFreq(self.txFreq, self.txFreq)
    self.sliderYs.SetValue(self.waterfall_y_scale)
    self.sliderYz.SetValue(self.waterfall_y_zero)
    self.display.Show()
    self.doResize = True
  def OnGraphData(self, data):
    if self.display == self.graph_display:
      self.display.OnGraphData(data)
    else:
      self.display.OnGraphData(data, self.waterfall_y_zero, self.waterfall_y_scale)
  def OnPlayButton(self, event):
    application.multi_rx_screen.StopPlaying(self)
    self.is_playing = event.GetEventObject().GetValue()
    if self.is_playing:
      QS.set_filters(self.filter_I, self.filter_Q, self.filter_bandwidth, 0, 1)
      QS.set_multirx_play_channel(self.multirx_index)
    else:
      QS.set_multirx_play_channel(-1)
  def SetVFO(self, vfo):
    GraphScreen.SetVFO(self, vfo)
    self.waterfall_display.VFO = self.VFO
    self.waterfall_display.Refresh()
  def OnChangeBand(self, event):
    idd = event.GetId()
    band = event.GetEventObject().GetLabel(idd)
    self.ChangeBand(band)
  def OnChangeMode(self, event=None):
    if event is None:
      try:
        idx = self.the_modes.index(self.mode)
      except ValueError:
        self.mode = 'USB'
        idx = self.the_modes.index(self.mode)
      self.mode_menu.FindItemByPosition(idx).Check(True)
    else:
      idd = event.GetId()
      self.mode = event.GetEventObject().GetLabel(idd)
    bws = application.Mode2Filters(self.mode)
    self.mode_index = Mode2Index.get(self.mode, 3)
    QS.set_multirx_mode(self.multirx_index, self.mode_index)
    for i in range(6):
      item = self.filter_menu.FindItemByPosition(i)
      item.SetItemLabel(str(bws[i]))
      if i == 2:
        item.Check(True)
    self.filter_bandwidth = bws[2]
    self.OnChangeFilter()
  def OnChangeFilter(self, event=None):
    if event is not None:
      idd = event.GetId()
      self.filter_bandwidth = int(event.GetEventObject().GetLabel(idd))
    center = application.GetFilterCenter(self.mode, self.filter_bandwidth)
    frate = QS.get_filter_rate(Mode2Index.get(self.mode, 3), self.filter_bandwidth)
    self.filter_I, self.filter_Q = application.MakeFilterCoef(frate, None, self.filter_bandwidth, center)
    if self.is_playing:
      QS.set_filters(self.filter_I, self.filter_Q, self.filter_bandwidth, 0, 1)	# filter for receiver that is playing sound
    if self.multirx_index == 0:
      QS.set_filters(self.filter_I, self.filter_Q, self.filter_bandwidth, 0, 2)	# filter for digital mode output to sound device
    self.filter_mode = self.mode
    self.filter_center = center
  def ChangeBand(self, band):
    self.band = band
    try:
      vfo, tune, self.mode = application.bandState[band]
      #print (vfo, tune, self.mode)
    except:
      try:
        f1, f2 = conf.BandEdge[band]
      except KeyError:
        f1, f2 = 10000000, 12000000
      vfo = (f1 + f2) // 2
      vfo = vfo // 10000
      vfo *= 10000
      if vfo < 9000000:
        self.mode = 'LSB'
      else:
        self.mode = 'USB'
      tune = 0
    self.OnChangeMode()
    self.ChangeHwFrequency(tune, vfo, 'ChangeBand')
    if hasattr(application.Hardware, "ChangeBandFilters"):
      application.Hardware.ChangeBandFilters()
  def OnBtnDownBand(self, event):
    self.OnBtnUpBand(event, True)
  def OnBtnUpBand(self, event, is_band_down=False):
    sample_rate = application.sample_rate
    btn = event.GetEventObject()
    oldvfo = self.VFO
    if btn.direction > 0:		# left button was used, move a bit
      d = int(sample_rate // 9)
    else:						# right button was used, move to edge
      d = int(sample_rate * 45 // 100)
    if is_band_down:
      d = -d
    vfo = self.VFO + d
    if sample_rate > 40000:
      vfo = (vfo + 5000) // 10000 * 10000	# round to even number
      delta = 10000
    elif sample_rate > 5000:
      vfo = (vfo + 500) // 1000 * 1000
      delta = 1000
    else:
      vfo = (vfo + 50) // 100 * 100
      delta = 100
    if oldvfo == vfo:
      if is_band_down:
        d = -delta
      else:
        d = delta
    else:
      d = vfo - oldvfo
    self.ChangeHwFrequency(self.txFreq - d, self.VFO + d, 'BandUpDown', event=event)
  def OnChangeYscale(self, event):
    y_scale = self.sliderYs.GetValue()
    if self.display == self.graph_display:
      self.ChangeYscale(y_scale)
    else:
      self.waterfall_y_scale = y_scale
  def OnChangeYzero(self, event):
    y_zero = self.sliderYz.GetValue()
    if self.display == self.graph_display:
      self.ChangeYzero(y_zero)
    else:
      self.waterfall_y_zero = y_zero
  def ChangeHwFrequency(self, tune, vfo, source='', band='', event=None):
    self.SetTxFreq(tune, tune)
    self.SetVFO(vfo)
    Hardware.MultiRxFrequency(self.multirx_index, vfo)
    QS.set_multirx_freq(self.multirx_index, tune)

class MultiReceiverScreen(wx.SplitterWindow):
  # The top level screen showing a graph, waterfall and any additional receivers.
  # The first receiver is zero; additional receivers are in self.receiver_list[]
  def __init__(self, frame, data_width, graph_width):
    application.multi_rx_screen = self		# prevent phase error
    self.data_width = data_width
    self.graph_width = graph_width
    wx.SplitterWindow.__init__(self, frame)
    self.SetSashGravity(0.50)
    self.receiver_list = []
    self.graph = GraphScreen(self, data_width, graph_width)
    self.width = self.graph.width
    self.waterfall = WaterfallScreen(self, self.width, data_width, graph_width)
    self.rx_zero = self.graph
    self.Initialize(self.rx_zero)
    self.waterfall.Hide()
    self.SetSizeHints(self.width, -1, self.width)
    # Calculate control width
    rx_btn = QuiskPushbutton(self, None, "Rx 8....", style=wx.BU_EXACTFIT)
    self.rx_btn_width, self.rx_btn_height = rx_btn.GetSize().Get()
    self.rx_btn_width *= 2
    rx_btn.Destroy()
    del rx_btn
    self.SetMinimumPaneSize(self.rx_btn_height)
    self.rx_btn_border = 5
    width = data_width - self.rx_btn_width - self.rx_btn_border * 2
    self.rx_data_width = fftPreferedSizes[0]
    for x in fftPreferedSizes:
      if x >= width:
        break
      else:
        self.rx_data_width = x
  def __getattr__(self, name):
    return getattr(self.rx_zero, name)
  def ChangeRxZero(self, show_graph):
    if self.IsSplit():
      old = self.GetWindow2()
    else:
      old = self.GetWindow1()
    if show_graph:
      new = self.graph
    else:
      new = self.waterfall
    if old != new:
      self.ReplaceWindow(old, new)
      new.Show()
      old.Hide()
      self.rx_zero = new
  def StopPlaying(self, excpt):		# change to not playing on all panes except excpt
    for pane in self.receiver_list:
      if pane != excpt:
        pane.play_btn.SetValue(False)
        pane.is_playing = False
  def OnAddReceiver(self, event):
    index = len(self.receiver_list)
    if index >= 7:
      return
    if index == 0:
      pane2 = self.rx_zero
      splitter = pane2.GetParent()
      pane1 = MultiRxGraph(self, self.data_width, self.graph_width, index)
      self.receiver_list.append(pane1)
      splitter.SplitHorizontally(pane1, self.rx_zero)
    else:
      pane2 = self.receiver_list[-1]
      parent = pane2.GetParent()
      splitter = wx.SplitterWindow(parent)
      splitter.SetSizeHints(self.width, -1, self.width)
      splitter.SetMinimumPaneSize(self.rx_btn_height)
      splitter.SetSashGravity(0.50)
      pane1 = MultiRxGraph(splitter, self.data_width, self.graph_width, index)
      self.receiver_list.append(pane1)
      pane2.Reparent(splitter)
      parent.ReplaceWindow(pane2, splitter)
      splitter.SplitHorizontally(pane1, pane2)
    self.SizeEqually()
    index += 1		# len(self.receiver_list)
    Hardware.MultiRxCount(index)
    pane1.ChangeBand(application.lastBand)
  def DeleteReceiver(self, pane):
    Hardware.MultiRxCount(len(self.receiver_list) - 1)
    if len(self.receiver_list) == 1:
      self.Unsplit(pane)
      self.receiver_list.remove(pane)
      del pane
    elif pane in self.receiver_list[-2:]:
      self.receiver_list.remove(pane)
      splitter2 = pane.GetParent()
      splitter1 = splitter2.GetParent()
      del pane
      pane = self.receiver_list[-1]
      pane.Reparent(splitter1)
      splitter1.ReplaceWindow(splitter2, pane)
      splitter2.Destroy()
    else:
      self.receiver_list.remove(pane)
      splitter2 = pane.GetParent()
      splitter1 = splitter2.GetParent()
      splitter3 = splitter2.GetWindow1()
      del pane
      splitter3.Reparent(splitter1)
      splitter1.ReplaceWindow(splitter2, splitter3)
      splitter2.Destroy()
    index = 0
    for pane in self.receiver_list:
      pane.multirx_index = index
      pane.rx_btn.SetLabel("Rx %d" % (index + 1))
      QS.set_multirx_mode(index, pane.mode_index)
      QS.set_multirx_freq(index, pane.txFreq)
      index += 1
    if hasattr(application.Hardware, "ChangeBandFilters"):
      application.Hardware.ChangeBandFilters()
  def SizeEqually(self):
    w, h = self.GetClientSize()
    num = len(self.receiver_list)
    self.SetSashPosition(h * num // (num + 1))
    for rx in self.receiver_list[:-1]:
      splitter = rx.GetParent()
      w, h = splitter.GetClientSize()
      num -= 1
      splitter.SetSashPosition(h * num // (num + 1))
  def OnIdle(self, event):
    self.rx_zero.OnIdle(event)
    for pane in self.receiver_list:
      pane.OnIdle(event)
  def OnGraphData(self, data, index=None):
    if index is None:		# data is for the principal receiver
      self.waterfall.OnGraphData(data)	# Save data for switch to waterfall
      if self.rx_zero == self.graph:
        self.graph.OnGraphData(data)
    elif index < len(self.receiver_list):
      self.receiver_list[index].OnGraphData(data)
  def ChangeSampleRate(self, rate):
    self.graph.sample_rate = rate
    self.waterfall.pane1.sample_rate = rate
    self.waterfall.pane2.sample_rate = rate
    self.waterfall.pane2.display.sample_rate = rate
    for pane in self.receiver_list:
      pane.sample_rate = rate
      tune = pane.txFreq
      vfo = pane.VFO
      pane.txFreq = pane.VFO = -1		# demand change
      pane.ChangeHwFrequency(tune, vfo, 'NewDecim')

class ScopeScreen(wx.Window):
  """Create an oscilloscope screen (mostly used for debug)."""
  def __init__(self, parent, width, data_width, graph_width):
    wx.Window.__init__(self, parent, pos = (0, 0),
       size=(width, -1), style = wx.NO_BORDER)
    self.SetBackgroundColour(conf.color_graph)
    self.font = wx.Font(conf.config_font_size, wx.FONTFAMILY_SWISS, wx.NORMAL,
          wx.FONTWEIGHT_NORMAL, False, conf.quisk_typeface)
    self.SetFont(self.font)
    self.Bind(wx.EVT_SIZE, self.OnSize)
    self.Bind(wx.EVT_PAINT, self.OnPaint)
    self.horizPen = wx.Pen(conf.color_gl, 1, wx.SOLID)
    self.y_scale = conf.scope_y_scale
    self.y_zero = conf.scope_y_zero
    self.yscale = 1
    self.running = 1
    self.doResize = False
    self.width = width
    self.height = 100
    self.originY = self.height // 2
    self.data_width = data_width
    self.graph_width = graph_width
    w = self.charx = self.GetCharWidth()
    h = self.chary = self.GetCharHeight()
    tick = max(2, h * 3 // 10)
    self.originX = w * 3
    self.width = self.originX + self.graph_width + tick + self.charx * 2
    self.line = [(0,0), (1,1)]	# initial fake graph data
    self.fpout = None #open("jim96.txt", "w")
  def OnIdle(self, event):
    if self.doResize:
      self.ResizeGraph()
  def OnSize(self, event):
    self.doResize = True
    event.Skip()
  def ResizeGraph(self, event=None):
    # Change the height of the graph.  Changing the width interactively is not allowed.
    w, h = self.GetClientSize()
    self.height = h
    self.originY = h // 2
    self.doResize = False
    self.Refresh()
  def OnPaint(self, event):
    dc = wx.PaintDC(self)
    dc.SetFont(self.font)
    dc.SetTextForeground(conf.color_graphlabels)
    self.MakeYTicks(dc)
    self.MakeXTicks(dc)
    self.MakeText(dc)
    dc.SetPen(wx.Pen(conf.color_graphline, 1))
    dc.DrawLines(self.line)
  def MakeYTicks(self, dc):
    chary = self.chary
    originX = self.originX
    x3 = self.x3 = originX + self.graph_width	# end of graph data
    dc.SetPen(wx.Pen(conf.color_graphticks,1))
    dc.DrawLine(originX, 0, originX, self.originY * 3)	# y axis
    # Find the size of the Y scale markings
    themax = 2.5e9 * 10.0 ** - ((160 - self.y_scale) / 50.0)	# value at top of screen
    themax = int(themax)
    l = []
    for j in (5, 6, 7, 8):
      for i in (1, 2, 5):
        l.append(i * 10 ** j)
    for yvalue in l:
      n = themax // yvalue + 1			# Number of lines
      ypixels = self.height // n
      if n < 20:
        break
    dc.SetPen(self.horizPen)
    for i in range(1, 1000):
      y = self.originY - ypixels * i
      if y < chary:
        break
      # Above axis
      dc.DrawLine(originX, y, x3, y)	# y line
      # Below axis
      y = self.originY + ypixels * i
      dc.DrawLine(originX, y, x3, y)	# y line
    self.yscale = float(ypixels) / yvalue
    self.yvalue = yvalue
  def MakeXTicks(self, dc):
    originY = self.originY
    x3 = self.x3
    # Draw the X axis
    dc.SetPen(wx.Pen(conf.color_graphticks,1))
    dc.DrawLine(self.originX, originY, x3, originY)
    # Find the size of the X scale markings in microseconds
    for i in (20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000, 50000, 100000):
      xscale = i			# X scale in microseconds
      if application.sample_rate * xscale * 0.000001 > self.width // 30:
        break
    # Draw the X lines
    dc.SetPen(self.horizPen)
    for i in range(1, 999):
      x = int(self.originX + application.sample_rate * xscale * 0.000001 * i + 0.5)
      if x > x3:
        break
      dc.DrawLine(x, 0, x, self.height)	# x line
    self.xscale = xscale
  def MakeText(self, dc):
    if self.running:
      t = "   RUN"
    else:
      t = "   STOP"
    if self.xscale >= 1000:
      t = "%s    X: %d millisec/div" % (t, self.xscale // 1000)
    else:
      t = "%s    X: %d microsec/div" % (t, self.xscale)
    t = "%s   Y: %.0E/div" % (t, self.yvalue)
    dc.DrawText(t, self.originX, self.height - self.chary)
  def OnGraphData(self, data):
    if not self.running:
      if self.fpout:
        for cpx in data:
          re = int(cpx.real)
          im = int(cpx.imag)
          ab = int(abs(cpx))
          ph = math.atan2(im, re) * 360. / (2.0 * math.pi)
          self.fpout.write("%12d %12d %12d %12.1d\n" % (re, im, ab, ph))
      return		# Preserve data on screen
    line = []
    x = self.originX
    ymax = self.height
    for cpx in data:	# cpx is complex raw samples +/- 0 to 2**31-1
      y = cpx.real
      #y = abs(cpx)
      y = self.originY - int(y * self.yscale + 0.5)
      if y > ymax:
        y = ymax
      elif y < 0:
        y = 0
      line.append((x, y))
      x = x + 1
    self.line = line
    self.Refresh()
  def ChangeYscale(self, y_scale):
    self.y_scale = y_scale
    self.doResize = True
  def ChangeYzero(self, y_zero):
    self.y_zero = y_zero
  def SetTxFreq(self, tx_freq, rx_freq):
    pass

class BandscopeScreen(WaterfallScreen):
  def __init__(self, frame, width, data_width, graph_width):
    WaterfallScreen.__init__(self, frame, width, data_width, graph_width)
    try:
      clock = conf.rx_udp_clock
    except:	# In case this is not defined
      clock = 73000000
    self.pane1.sample_rate = self.pane2.sample_rate = clock // 2
    self.VFO = clock // 4
    self.SetVFO(self.VFO)
  def SetTxFreq(self, tx_freq, rx_freq):
    freq = tx_freq + application.VFO - self.VFO
    WaterfallScreen.SetTxFreq(self, freq, freq)
  def SetFrequency(self, freq):		# freq is 7000000, not the offset from VFO
    freq = freq - self.VFO
    WaterfallScreen.SetTxFreq(self, freq, freq)

class FilterScreen(GraphScreen):
  """Create a graph of the receive filter response."""
  def __init__(self, parent, data_width, graph_width):
    GraphScreen.__init__(self, parent, data_width, graph_width)
    self.y_scale = conf.filter_y_scale
    self.y_zero = conf.filter_y_zero
    self.VFO = 0
    self.txFreq = 0
    self.data = []
    self.sample_rate = QS.get_filter_rate(-1, -1)
  def NewFilter(self):
    self.sample_rate = QS.get_filter_rate(-1, -1)
    self.data = QS.get_filter()
    mx = -1000
    for x in self.data:
      if mx < x:
        mx = x
    mx -= 3.0
    f1 = None
    for i in range(len(self.data)):
      x = self.data[i]
      if x > mx:
        if f1 is None:
          f1 = i
        f2 = i
    bw3 = float(f2 - f1) / len(self.data) * self.sample_rate
    mx -= 3.0
    f1 = None
    for i in range(len(self.data)):
      x = self.data[i]
      if x > mx:
        if f1 is None:
          f1 = i
        f2 = i
    bw6 = float(f2 - f1) / len(self.data) * self.sample_rate
    self.display.display_text = "Filter 3 dB bandwidth %.0f, 6 dB %.0f" % (bw3, bw6)
    #self.data = QS.get_tx_filter()
    self.doResize = True
  def OnGraphData(self, data):
    GraphScreen.OnGraphData(self, self.data)
  def ChangeHwFrequency(self, tune, vfo, source='', band='', event=None):
    GraphScreen.SetTxFreq(self, tune, tune)
    application.freqDisplay.Display(tune)
  def SetTxFreq(self, tx_freq, rx_freq):
    pass

class AudioFFTScreen(GraphScreen):
  """Create an FFT graph of the transmit audio."""
  def __init__(self, parent, data_width, graph_width, sample_rate):
    GraphScreen.__init__(self, parent, data_width, graph_width)
    self.y_scale = conf.filter_y_scale
    self.y_zero = conf.filter_y_zero
    self.VFO = 0
    self.txFreq = 0
    self.sample_rate = sample_rate
  def OnGraphData(self, data):
    GraphScreen.OnGraphData(self, data)
  def ChangeHwFrequency(self, tune, vfo, source='', band='', event=None):
    GraphScreen.SetTxFreq(self, tune, tune)
    application.freqDisplay.Display(tune)
  def SetTxFreq(self, tx_freq, rx_freq):
    pass

class HelpScreen(wx.html.HtmlWindow):
  """Create the screen for the Help button."""
  def __init__(self, parent, width, height):
    wx.html.HtmlWindow.__init__(self, parent, -1, size=(width, height))
    self.y_scale = 0
    self.y_zero = 0
    if "gtk2" in wx.PlatformInfo:
      self.SetStandardFonts()
    self.SetFonts("", "", [10, 12, 14, 16, 18, 20, 22])
    # read in text from file help.html in the directory of this module
    self.LoadFile('help.html')
  def OnGraphData(self, data):
    pass
  def ChangeYscale(self, y_scale):
    pass
  def ChangeYzero(self, y_zero):
    pass
  def OnIdle(self, event):
    pass
  def SetTxFreq(self, tx_freq, rx_freq):
    pass
  def OnLinkClicked(self, link):
    webbrowser.open(link.GetHref(), new=2)

class QMainFrame(wx.Frame):
  """Create the main top-level window."""
  def __init__(self, width, height):
    fp = open('__init__.py')		# Read in the title
    self.title = fp.readline().strip()[1:]
    fp.close()
    x = conf.window_posX
    y = conf.window_posY
    wx.Frame.__init__(self, None, -1, self.title, (x, y),
        (width, height), wx.DEFAULT_FRAME_STYLE, 'MainFrame')
    self.SetBackgroundColour(conf.color_bg)
    self.SetForegroundColour(conf.color_bg_txt)
    self.Bind(wx.EVT_CLOSE, self.OnBtnClose)
    if DEBUGSHELL:
      #debugshell = CrustFrame()
      debugshell = ShellFrame(parent=self)
      debugshell.Show()
      debugshell.shell.write("hw=quisk.application.Hardware")
  def OnBtnClose(self, event):
    application.OnBtnClose(event)
    self.Destroy()
  def SetConfigText(self, text):
    if len(text) > 100:
      text = text[0:80] + '|||' + text[-17:]
    self.SetTitle("Radio %s   %s   %s" % (configure.Settings[1], self.title, text))

## Note: The new amplitude/phase adjustments have ideas provided by Andrew Nilsson, VK6JBL
class QAdjustPhase(wx.Frame):
  """Create a window with amplitude and phase adjustment controls"""
  f_ampl = "Amplitude adjustment %.6f"
  f_phase = "Phase adjustment degrees %.6f"
  def __init__(self, parent, width, rx_tx):
    self.rx_tx = rx_tx		# Must be "rx" or "tx"
    if rx_tx == 'tx':
      self.is_tx = 1
      t = "Adjust Sound Card Transmit Amplitude and Phase"
    else:
      self.is_tx = 0
      t = "Adjust Sound Card Receive Amplitude and Phase"
    wx.Frame.__init__(self, application.main_frame, -1, t, pos=(50, 100), style=wx.CAPTION)
    panel = wx.Panel(self)
    self.MakeControls(panel, width)
    self.Show()
  def MakeControls(self, panel, width):		# Make controls for phase/amplitude adjustment
    self.old_amplitude, self.old_phase = application.GetAmplPhase(self.is_tx)
    self.new_amplitude, self.new_phase = self.old_amplitude, self.old_phase
    sl_max = width * 4 // 10		# maximum +/- value for slider
    self.ampl_scale = float(conf.rx_max_amplitude_correct) / sl_max
    self.phase_scale = float(conf.rx_max_phase_correct) / sl_max
    font = wx.Font(conf.default_font_size, wx.FONTFAMILY_SWISS, wx.NORMAL,
          wx.FONTWEIGHT_NORMAL, False, conf.quisk_typeface)
    chary = self.GetCharHeight()
    y = chary * 3 // 10
    # Print available data points
    if "panadapter" in conf.bandAmplPhase:
      self.band = "panadapter"
    else:
      self.band = application.lastBand
    app_vfo = (application.VFO + 500) // 1000
    ap = application.bandAmplPhase
    if self.band not in ap:
      ap[self.band] = {}
    if self.rx_tx not in ap[self.band]:
      ap[self.band][self.rx_tx] = []
    lst = ap[self.band][self.rx_tx]
    freq_in_list = False
    if lst:
      t = "Band %s: VFO" % self.band
      for l in lst:
        vfo = (l[0] + 500) // 1000
        if vfo == app_vfo:
          freq_in_list = True
        t = t + (" %d" % vfo)
    else:
      t = "Band %s: No data." % self.band
    txt = wx.StaticText(panel, -1, t, pos=(0, y))
    txt.SetFont(font)
    y += txt.GetSize().GetHeight()
    self.t_ampl = wx.StaticText(panel, -1, self.f_ampl % self.old_amplitude, pos=(0, y))
    self.t_ampl.SetFont(font)
    y += self.t_ampl.GetSize().GetHeight()
    self.ampl1 = wx.Slider(panel, -1, 0, -sl_max, sl_max,
      pos=(0, y), size=(width, -1))
    y += self.ampl1.GetSize().GetHeight()
    self.ampl2 = wx.Slider(panel, -1, 0, -sl_max, sl_max,
      pos=(0, y), size=(width, -1))
    y += self.ampl2.GetSize().GetHeight()
    self.PosAmpl(self.old_amplitude)
    self.t_phase = wx.StaticText(panel, -1, self.f_phase % self.old_phase, pos=(0, y))
    self.t_phase.SetFont(font)
    y += self.t_phase.GetSize().GetHeight()
    self.phase1 = wx.Slider(panel, -1, 0, -sl_max, sl_max,
      pos=(0, y), size=(width, -1))
    y += self.phase1.GetSize().GetHeight()
    self.phase2 = wx.Slider(panel, -1, 0, -sl_max, sl_max,
      pos=(0, y), size=(width, -1))
    y += self.phase2.GetSize().GetHeight()
    sv = QuiskPushbutton(panel, self.OnBtnSave, 'Save %d' % app_vfo)
    ds = QuiskPushbutton(panel, self.OnBtnDiscard, 'Destroy %d' % app_vfo)
    cn = QuiskPushbutton(panel, self.OnBtnCancel, 'Cancel')
    w, h = ds.GetSize().Get()
    sv.SetSize((w, h))
    cn.SetSize((w, h))
    y += h // 4
    x = (width - w * 3) // 4
    sv.SetPosition((x, y))
    ds.SetPosition((x*2 + w, y))
    cn.SetPosition((x*3 + w*2, y))
    sv.SetBackgroundColour('light blue')
    ds.SetBackgroundColour('light blue')
    cn.SetBackgroundColour('light blue')
    if not freq_in_list:
      ds.Disable()
    y += h
    y += h // 4
    self.ampl1.SetBackgroundColour('aquamarine')
    self.ampl2.SetBackgroundColour('orange')
    self.phase1.SetBackgroundColour('aquamarine')
    self.phase2.SetBackgroundColour('orange')
    self.PosPhase(self.old_phase)
    self.SetClientSize(wx.Size(width, y))
    self.ampl1.Bind(wx.EVT_SCROLL, self.OnChange)
    self.ampl2.Bind(wx.EVT_SCROLL, self.OnAmpl2)
    self.phase1.Bind(wx.EVT_SCROLL, self.OnChange)
    self.phase2.Bind(wx.EVT_SCROLL, self.OnPhase2)
  def PosAmpl(self, ampl):	# set pos1, pos2 for amplitude
    pos2 = round(ampl / self.ampl_scale)
    remain = ampl - pos2 * self.ampl_scale
    pos1 = round(remain / self.ampl_scale * 50.0)
    self.ampl1.SetValue(pos1)
    self.ampl2.SetValue(pos2)
  def PosPhase(self, phase):	# set pos1, pos2 for phase
    pos2 = round(phase / self.phase_scale)
    remain = phase - pos2 * self.phase_scale
    pos1 = round(remain / self.phase_scale * 50.0)
    self.phase1.SetValue(pos1)
    self.phase2.SetValue(pos2)
  def OnChange(self, event):
    ampl = self.ampl_scale * self.ampl1.GetValue() / 50.0 + self.ampl_scale * self.ampl2.GetValue()
    if abs(ampl) < self.ampl_scale * 3.0 / 50.0:
      ampl = 0.0
    self.t_ampl.SetLabel(self.f_ampl % ampl)
    phase = self.phase_scale * self.phase1.GetValue() / 50.0 + self.phase_scale * self.phase2.GetValue()
    if abs(phase) < self.phase_scale * 3.0 / 50.0:
      phase = 0.0
    self.t_phase.SetLabel(self.f_phase % phase)
    QS.set_ampl_phase(ampl, phase, self.is_tx)
    self.new_amplitude, self.new_phase = ampl, phase
  def OnAmpl2(self, event):		# re-center the fine slider when the coarse slider is adjusted
    ampl = self.ampl_scale * self.ampl1.GetValue() / 50.0 + self.ampl_scale * self.ampl2.GetValue()
    self.PosAmpl(ampl)
    self.OnChange(event)
  def OnPhase2(self, event):	# re-center the fine slider when the coarse slider is adjusted
    phase = self.phase_scale * self.phase1.GetValue() / 50.0 + self.phase_scale * self.phase2.GetValue()
    self.PosPhase(phase)
    self.OnChange(event)
  def DeleteEqual(self):	# Remove entry with the same VFO
    ap = application.bandAmplPhase
    lst = ap[self.band][self.rx_tx]
    vfo = (application.VFO + 500) // 1000
    for i in range(len(lst)-1, -1, -1):
      if (lst[i][0] + 500) // 1000 == vfo:
        del lst[i]
  def OnBtnSave(self, event):
    data = (application.VFO, application.rxFreq, self.new_amplitude, self.new_phase)
    self.DeleteEqual()
    ap = application.bandAmplPhase
    lst = ap[self.band][self.rx_tx]
    lst.append(data)
    lst.sort()
    application.w_phase = None
    self.Destroy()
  def OnBtnDiscard(self, event):
    self.DeleteEqual()
    self.OnBtnCancel()
  def OnBtnCancel(self, event=None):
    QS.set_ampl_phase(self.old_amplitude, self.old_phase, self.is_tx)
    application.w_phase = None
    self.Destroy()

class Spacer(wx.Window):
  """Create a bar between the graph screen and the controls"""
  def __init__(self, parent):
    wx.Window.__init__(self, parent, pos = (0, 0),
       size=(-1, 6), style = wx.NO_BORDER)
    self.Bind(wx.EVT_PAINT, self.OnPaint)
    r, g, b = parent.GetBackgroundColour().Get(False)
    dark = (r * 7 // 10, g * 7 // 10, b * 7 // 10)
    light = (r + (255 - r) * 5 // 10, g + (255 - g) * 5 // 10, b + (255 - b) * 5 // 10)
    self.dark_pen = wx.Pen(dark, 1, wx.SOLID)
    self.light_pen = wx.Pen(light, 1, wx.SOLID)
    self.width = application.screen_width
  def OnPaint(self, event):
    dc = wx.PaintDC(self)
    w = self.width
    dc.SetPen(self.dark_pen)
    dc.DrawLine(0, 0, w, 0)
    dc.DrawLine(0, 1, w, 1)
    dc.DrawLine(0, 2, w, 2)
    dc.SetPen(self.light_pen)
    dc.DrawLine(0, 3, w, 3)
    dc.DrawLine(0, 4, w, 4)
    dc.DrawLine(0, 5, w, 5)

class App(wx.App):
  """Class representing the application."""
  StateNames = [		# Names of state attributes to save and restore
  'bandState', 'bandAmplPhase', 'lastBand', 'VFO', 'txFreq', 'mode',
  'vardecim_set', 'filterAdjBw1', 'levelAGC', 'levelOffAGC', 'volumeAudio', 'levelSpot',
  'levelSquelch', 'levelSquelchSSB', 'levelVOX', 'timeVOX', 'sidetone_volume', 
  'txAudioClipUsb', 'txAudioClipAm','txAudioClipFm', 'txAudioClipFdv',
  'txAudioPreemphUsb', 'txAudioPreemphAm', 'txAudioPreemphFm', 'txAudioPreemphFdv',
  'wfallScaleZ', 'graphScaleZ', 'split_rxtx_play', 'modeFilter']
  def __init__(self):
    global application
    application = self
    self.init_path = None
    self.bottom_widgets = None
    self.dxCluster = None
    self.startup_quisk = False
    if sys.stdout.isatty():
      wx.App.__init__(self, redirect=False)
    else:
      wx.App.__init__(self, redirect=True)
  def QuiskText(self, *args, **kw):			# Make our text control available to widget files
    return QuiskText(*args, **kw)
  def QuiskText1(self, *args, **kw):			# Make our text control available to widget files
    return QuiskText1(*args, **kw)
  def QuiskPushbutton(self, *args, **kw):	# Make our buttons available to widget files
    return QuiskPushbutton(*args, **kw)
  def  QuiskRepeatbutton(self, *args, **kw):
    return QuiskRepeatbutton(*args, **kw)
  def QuiskCheckbutton(self, *args, **kw):
    return QuiskCheckbutton(*args, **kw)
  def QuiskCycleCheckbutton(self, *args, **kw):
    return QuiskCycleCheckbutton(*args, **kw)
  def RadioButtonGroup(self, *args, **kw):
    return RadioButtonGroup(*args, **kw)
  def SliderBoxHH(self, *args, **kw):
    return SliderBoxHH(*args, **kw)
  def OnInit(self):
    """Perform most initialization of the app here (called by wxPython on startup)."""
    wx.lib.colourdb.updateColourDB()	# Add additional color names
    import quisk_widgets		# quisk_widgets needs the application object
    quisk_widgets.application = self
    del quisk_widgets
    global conf		# conf is the module for all configuration data
    import quisk_conf_defaults as conf
    setattr(conf, 'config_file_path', ConfigPath)
    setattr(conf, 'DefaultConfigDir', DefaultConfigDir)
    if os.path.isfile(ConfigPath):	# See if the user has a config file
      setattr(conf, 'config_file_exists', True)
      d = {}
      d.update(conf.__dict__)		# make items from conf available
      exec(compile(open(ConfigPath).read(), ConfigPath, 'exec'), d)		# execute the user's config file
      if os.path.isfile(ConfigPath2):	# See if the user has a second config file
        exec(compile(open(ConfigPath2).read(), ConfigPath2, 'exec'), d)	# execute the user's second config file
      for k in d:		# add user's config items to conf
        v = d[k]
        if k[0] != '_':				# omit items starting with '_'
          setattr(conf, k, v)
    else:
      setattr(conf, 'config_file_exists', False)
    QS.set_params(quisk_is_vna=0)	# We are not the VNA program
    # Read in configuration from the selected radio
    self.local_conf = configure.Configuration(self, argv_options.AskMe)
    self.local_conf.UpdateConf()
    # Choose whether to use Unicode or text symbols
    for k in ('sym_stat_mem', 'sym_stat_fav', 'sym_stat_dx',
        'btn_text_range_dn', 'btn_text_range_up', 'btn_text_play', 'btn_text_rec', 'btn_text_file_rec', 
		'btn_text_file_play', 'btn_text_fav_add',
        'btn_text_fav_recall', 'btn_text_mem_add', 'btn_text_mem_next', 'btn_text_mem_del'):
      if conf.use_unicode_symbols:
        setattr(conf, 'X' + k, getattr(conf, 'U' + k))
      else:
        setattr(conf, 'X' + k, getattr(conf, 'T' + k))
    MakeWidgetGlobals()
    if conf.invertSpectrum:
      QS.invert_spectrum(1)
    if conf.use_sdriq:
      sample_rate = int(66666667.0 / conf.sdriq_decimation + 0.5)
    if conf.use_sdriq or conf.use_rx_udp:
      name_of_sound_capt = ''
      name_of_mic_play = ''
    self.wfallScaleZ = {}		# scale and zero for the waterfall pane2
    self.graphScaleZ = {}		# scale and zero for the graph
    self.bandState = {}			# for key band, the current (self.VFO, self.txFreq, self.mode)
    self.bandState.update(conf.bandState)
    self.memoryState = []		# a list of (freq, band, self.VFO, self.txFreq, self.mode)
    self.bandAmplPhase = conf.bandAmplPhase
    self.modeFilter = {			# the filter button index in use for each mode
      'CW'  : 3,
      'SSB' : 3,
      'AM'  : 3,
      'FM'  : 3,
      'DGT' : 1,
      'FDV' : 2,
      'IMD' : 3,
      conf.add_extern_demod : 3,
      }
    if sys.platform == 'win32' and (conf.hamlib_com1_name or conf.hamlib_com2_name):
      try:      # make sure the pyserial module exists
        import serial
      except:
        dlg = wx.MessageDialog(None, "The Python pyserial module is required but not installed. Do you want me to install it?",
          "Install Python pyserial", style = wx.YES|wx.NO)
        if dlg.ShowModal() == wx.ID_YES:
          subprocess.call([sys.executable, "-m", "pip", "install", "pyserial"])
          try:
            import serial
          except:
            dlg = wx.MessageDialog(None, "Installation of Python pyserial failed. Please install it by hand.",
               "Installation failed", style=wx.OK)
            dlg.ShowModal()
    # Open hardware file
    global Hardware
    if self.local_conf.GetHardware():
      pass
    else:
      if hasattr(conf, "Hardware"):	# Hardware defined in config file
        self.Hardware = conf.Hardware(self, conf)
        hname =  ConfigPath
      else:
        self.Hardware = conf.quisk_hardware.Hardware(self, conf)
        hname =  conf.quisk_hardware.__file__
      if hname[-3:] == 'pyc':
        hname = hname[0:-1]
      setattr(conf, 'hardware_file_name',  hname)
      if conf.quisk_widgets:
        hname =  conf.quisk_widgets.__file__
        if hname[-3:] == 'pyc':
          hname = hname[0:-1]
        setattr(conf, 'widgets_file_name',  hname)
      else:
        setattr(conf, 'widgets_file_name',  '')
    Hardware = self.Hardware
    # Initialization - may be over-written by persistent state
    self.local_conf.Initialize()
    self.clip_time0 = 0		# timer to display a CLIP message on ADC overflow
    self.smeter_db_count = 0	# average the S-meter
    self.smeter_db_sum = 0
    self.smeter_db = 0
    self.smeter_avg_seconds = 1.0	# seconds for S-meter average
    self.smeter_sunits = -87.0
    self.smeter_usage = "smeter"	# specify use of s-meter display
    self.timer = time.time()		# A seconds clock
    self.heart_time0 = self.timer	# timer to call HeartBeat at intervals
    self.save_time0 = self.timer
    self.smeter_db_time0 = self.timer
    self.smeter_sunits_time0 = self.timer
    self.fewsec_time0 = self.timer
    self.multi_rx_index = 0
    self.multi_rx_timer = self.timer
    self.band_up_down = 0			# Are band Up/Down buttons in use?
    self.lastBand = 'Audio'
    self.filterAdjBw1 = 1000
    self.levelAGC = 500				# AGC level ON control, 0 to 1000
    self.levelOffAGC = 100			# AGC level OFF control, 0 to 1000
    self.levelSquelch = 500			# FM squelch level, 0 to 1000
    self.levelSquelchSSB = 200			# SSB squelch level, 0 to 1000
    self.levelVOX = -20				# audio level that triggers VOX
    self.timeVOX = 500				# hang time for VOX
    self.useVOX = False				# Is the VOX button down?
    self.txAudioClipUsb = 5			# Tx audio clip level in dB
    self.txAudioClipAm = 0
    self.txAudioClipFm = 0
    self.txAudioClipFdv = 0
    self.txAudioPreemphUsb = 70		# Tx audio preemphasis 0 to 100
    self.txAudioPreemphAm = 0
    self.txAudioPreemphFm = 0
    self.txAudioPreemphFdv = 0
    self.levelSpot = 500			# Spot level control, 0 to 1000
    self.volumeAudio = 300			# audio volume
    self.VFO = 0					# frequency of the VFO
    self.ritFreq = 0				# receive incremental tuning frequency offset
    self.txFreq = 0				# Transmit frequency as +/- sample_rate/2
    self.rxFreq = 0				# Receive  frequency as +/- sample_rate/2
    self.tx_level = 100				# initially 100%; Caution: there is also a conf.tx_level dictionary
    self.digital_tx_level = conf.digital_tx_level
    self.hot_key_ptt_state = 0
    self.hot_key_ptt_stateH = 0
    self.hardware_ptt_key_state = 0
    self.fft_size = 1
    self.accel_list = []
    if conf.do_repeater_offset and hasattr(Hardware, "RepeaterOffset"):
      QS.tx_hold_state(1)
    # Quisk control by Hamlib through a serial port
    if conf.hamlib_com1_name:
      self.hamlib_com1_handler = HamlibHandlerSerial(self, conf.hamlib_com1_name)
    else:
      self.hamlib_com1_handler = None
    if conf.hamlib_com2_name:
      self.hamlib_com2_handler = HamlibHandlerSerial(self, conf.hamlib_com2_name)
    else:
      self.hamlib_com2_handler = None
    # Quisk control by Hamlib through rig 2
    self.hamlib_clients = []	# list of TCP connections to handle
    if conf.hamlib_port:
      try:
        self.hamlib_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.hamlib_socket.bind((conf.hamlib_ip, conf.hamlib_port))
        self.hamlib_socket.settimeout(0.0)
        self.hamlib_socket.listen(0)	# listen for TCP connections from multiple clients
      except:
        self.hamlib_socket = None
        # traceback.print_exc()
    else:
      self.hamlib_socket = None
    # Quisk control by fldigi
    self.fldigi_new_freq = None
    self.fldigi_freq = None
    if conf.digital_xmlrpc_url:
      self.fldigi_server = ServerProxy(conf.digital_xmlrpc_url)
    else:
      self.fldigi_server = None
    self.fldigi_rxtx = 'rx'
    self.fldigi_timer = 0
    self.oldRxFreq = 0			# Last value of self.rxFreq
    self.screen = None
    # Display the audio FFT instead of the RX filter or bandscope when self.rate_audio_fft > 0.
    # The sample rate is self.rate_audio_fft. Add an instance of quisk_calc_audio_graph() to C code to provide data.
    self.rate_audio_fft = 0
    self.audio_fft_screen = None
    self.audio_volume = 0.0		# Set output volume, 0.0 to 1.0
    self.sidetone_volume = 0	# sidetone control value 0 to 1000
    self.sidetone_0to1 = 0		# log taper sidetone volume 0.0 to 1.0
    self.sound_thread = None
    self.mode = conf.default_mode
    self.color_list = None
    self.color_index = 0
    self.vardecim_set = None
    self.w_phase = None
    self.zoom = 1.0
    self.filter_bandwidth = 1000    # filter bandwidth
    self.zoom_deltaf = 0
    self.zooming = False
    self.split_rxtx = False		# Are we in split Rx/Tx mode?
    self.split_locktx = False	# Split mode Tx frequency is fixed.
    self.split_hamlib_tx = True	# Hamlib controls the Tx frequency when split; else the Rx frequency
    self.split_rxtx_play = 2    # Play 1=both, high on Right; 2=both, high on Left; 3=only Rx; 4=only Tx
    self.savedState = {}
    self.pttButton = None
    self.tmp_playing = False
    self.file_play_state = 0	# 0 == not playing a file, 1 == playing a file, 2 == waiting for the repeat time
    self.file_play_repeat = 0	# Repeat time in seconds, or zero for no repeat
    self.file_play_timer = 0
    self.file_play_source = 0	# 10 == play audio file, 11 == play I/Q sample file, 12 == play CQ message
    # get the screen size - thanks to Lucian Langa
    x, y, self.screen_width, self.screen_height = wx.Display().GetGeometry()	# Using display index 0
    self.Bind(wx.EVT_IDLE, self.OnIdle)
    self.Bind(wx.EVT_QUERY_END_SESSION, self.OnEndSession)
    # Restore persistent program state
    if conf.persistent_state:
      self.init_path = os.path.join(os.path.dirname(ConfigPath), '.quisk_init.pkl')
      try:
        fp = open(self.init_path, "rb")
        d = pickle.load(fp)
        fp.close()
        for k in d:
          v = d[k]
          if k in self.StateNames:
            self.savedState[k] = v
            attr = getattr(self, k)
            if type(attr) is DictType:
              attr.update(v)
            else:
              setattr(self, k, v)
      except:
        pass #traceback.print_exc()
      for k, (vfo, tune, mode) in list(self.bandState.items()):	# Historical: fix bad frequencies
        try:
          f1, f2 = conf.BandEdge[k]
          if not f1 <= vfo + tune <= f2:
            self.bandState[k] = conf.bandState[k]
        except KeyError:
          pass
    if self.bandAmplPhase and type(list(self.bandAmplPhase.values())[0]) is not DictType:
      print("""Old sound card amplitude and phase corrections must be re-entered (sorry).
The new code supports multiple corrections per band.""")
      self.bandAmplPhase = {}
    if Hardware.VarDecimGetChoices():	# Hardware can change the decimation.
      self.sample_rate = Hardware.VarDecimSet()	# Get the sample rate.
      self.vardecim_set = self.sample_rate
      try:
        var_rate1, var_rate2 = Hardware.VarDecimRange()
      except:
        var_rate1, var_rate2 = (48000, 960000)
    else:		# Use the sample rate from the config file.
      var_rate1 = None
      self.sample_rate = conf.sample_rate
    if not hasattr(conf, 'playback_rate'):
      if conf.use_sdriq or conf.use_rx_udp:
        conf.playback_rate = 48000
      else:
        conf.playback_rate = conf.sample_rate
    # Check for PulseAudio names and substitute the actual device name for abbreviations
    self.pulse_in_use = False
    if sys.platform != 'win32' and conf.show_pulse_audio_devices:
      self.pa_dev_capt, self.pa_dev_play = QS.pa_sound_devices()
      for key in ("name_of_sound_play", "name_of_mic_play", "digital_output_name", "digital_rx1_name", "sample_playback_name"):
        value = getattr(conf, key)		# playback devices
        if value[0:6] == "pulse:":
          self.pulse_in_use = True
          for n0, n1, n2 in self.pa_dev_play:
            for n in (n0, n1, n2):
              if value[6:] in n:
                setattr(conf, key, "pulse:" + n0)
      for key in ("name_of_sound_capt", "microphone_name", "digital_input_name"):
        value = getattr(conf, key)		# capture devices
        if value[0:6] == "pulse:":
          self.pulse_in_use = True
          for n0, n1, n2 in self.pa_dev_capt:
            for n in (n0, n1, n2):
              if value[6:] in n:
                setattr(conf, key, "pulse:" + n0)
    # Create the main frame
    if conf.window_width > 0:	# fixed width of the main frame
      self.width = conf.window_width
    else:
      self.width = self.screen_width * 8 // 10
    if conf.window_height > 0:	# fixed height of the main frame
      self.height = conf.window_height
    else:
      self.height = self.screen_height * 5 // 10
    self.main_frame = frame = QMainFrame(self.width, self.height)
    self.SetTopWindow(frame)
    #w, h = frame.GetSize().Get()
    #ww, hh = frame.GetClientSizeTuple()
    #print ('Main frame: size', w, h, 'client', ww, hh)
    # Find the data width from a list of prefered sizes; it is the width of returned graph data.
    # The graph_width is the width of data_width that is displayed.
    if conf.window_width > 0:
      wFrame, h = frame.GetClientSize().Get()				# client window width
      graph = GraphScreen(frame, self.width//2, self.width//2, None)	# make a GraphScreen to calculate borders
      self.graph_width = wFrame - (graph.width - graph.graph_width)		# less graph borders equals actual graph_width
      graph.Destroy()
      del graph
      if self.graph_width % 2 == 1:		# Both data_width and graph_width are even numbers
        self.graph_width -= 1
      width = int(self.graph_width / conf.display_fraction)		# estimated data width
      for x in fftPreferedSizes:
        if x >= width:
          self.data_width = x
          break
      else:
        self.data_width = fftPreferedSizes[-1]
    else:		# use conf.graph_width to determine the width
      width = self.screen_width * conf.graph_width		# estimated graph width
      percent = conf.display_fraction		# display central fraction of total width
      percent = int(percent * 100.0 + 0.4)
      width = width * 100 // percent		# estimated data width
      for x in fftPreferedSizes:
        if x > width:
          self.data_width = x
          break
      else:
        self.data_width = fftPreferedSizes[-1]
      self.graph_width = self.data_width * percent // 100
      if self.graph_width % 2 == 1:		# Both data_width and graph_width are even numbers
        self.graph_width += 1
    #print('graph_width', self.graph_width, 'data_width', self.data_width)
    # The FFT size times the average_count controls the graph refresh rate
    factor = float(self.sample_rate) / conf.graph_refresh / self.data_width
    ifactor = int(factor + 0.5)		# fft size multiplier * average count
    if conf.fft_size_multiplier >= 999:	# Use large FFT and average count 1
      fft_mult = ifactor
      average_count = 1
    elif conf.fft_size_multiplier > 0:		# Specified fft_size_multiplier
      fft_mult = conf.fft_size_multiplier
      average_count = int(factor / fft_mult + 0.5)
      if average_count < 1:
        average_count = 1
    elif var_rate1 is None:		# Calculate an equal split between fft size and average
      fft_mult = 1
      for mult in (32, 27, 24, 18, 16, 12, 9, 8, 6, 4, 3, 2, 1):	# product of small factors
        average_count = int(factor / mult + 0.5)
        if average_count >= mult:
          fft_mult = mult
          break
      average_count = int(factor / fft_mult + 0.5)
      if average_count < 1:
        average_count = 1
    else:		# Calculate a compromise for variable rates
      fft_mult = int(float(var_rate1) / conf.graph_refresh / self.data_width + 0.5)	# large fft_mult at low rate
      if fft_mult > 8:
        fft_mult = 8
      elif fft_mult == 5:
        fft_mult = 4
      elif fft_mult == 7:
        fft_mult = 6
      average_count = int(factor / fft_mult + 0.5)
      if average_count < 1:
        average_count = 1
    self.fft_size = self.data_width * fft_mult
    # Record the basic application parameters
    self.multi_rx_screen = MultiReceiverScreen(frame, self.data_width, self.graph_width)
    if sys.platform == 'win32':
      h = self.main_frame.GetHandle()
    else:
      h = 0
    QS.record_app(self, conf, self.data_width, self.graph_width, self.fft_size,
                 self.multi_rx_screen.rx_data_width, self.sample_rate, h)
    #print ('data_width %d, FFT size %d, FFT mult %d, average_count %d, rate %d, Refresh %.2f Hz' % (
    #    self.data_width, self.fft_size, self.fft_size / self.data_width, average_count, self.sample_rate,
    #    float(self.sample_rate) / self.fft_size / average_count))
    QS.record_graph(0, 0, 1.0)
    QS.set_tx_audio(vox_level=20, vox_time=self.timeVOX)	# Turn off VOX, set VOX time
    # Make all the screens and hide all but one.  MultiReceiver creates the graph and waterfall screens.
    self.screen = self.multi_rx_screen
    self.graph = self.multi_rx_screen.graph
    self.waterfall = self.multi_rx_screen.waterfall
    width = self.multi_rx_screen.graph.width
    self.config_screen = ConfigScreen(frame, width, self.fft_size)
    self.config_screen.Hide()
    self.scope = ScopeScreen(frame, width, self.data_width, self.graph_width)
    self.scope.Hide()
    self.bandscope_screen = BandscopeScreen(frame, width, self.graph_width, self.graph_width)
    self.bandscope_screen.Hide()
    self.filter_screen = FilterScreen(frame, self.data_width, self.graph_width)
    self.filter_screen.Hide()
    if self.rate_audio_fft:
      self.audio_fft_screen = AudioFFTScreen(frame, self.data_width, self.graph_width, self.rate_audio_fft)
      self.audio_fft_screen.Hide()
    self.help_screen = HelpScreen(frame, width, self.screen_height // 10)
    self.help_screen.Hide()
    self.station_screen = StationScreen(frame, width, conf.station_display_lines)
    self.station_screen.Hide()
    # Make a vertical box to hold all the screens and the bottom box
    vertBox = self.vertBox = wx.BoxSizer(wx.VERTICAL)
    frame.SetSizer(vertBox)
    # Add the screens
    vertBox.Add(self.config_screen, 1, wx.EXPAND)
    vertBox.Add(self.multi_rx_screen, 1)
    vertBox.Add(self.scope, 1)
    vertBox.Add(self.bandscope_screen, 1)
    vertBox.Add(self.filter_screen, 1)
    if self.rate_audio_fft:
      vertBox.Add(self.audio_fft_screen, 1)
    vertBox.Add(self.help_screen, 1)
    vertBox.Add(self.station_screen)
    # Add the spacer
    vertBox.Add(Spacer(frame), 0, wx.EXPAND)
    # Add the sizer for the controls
    gap = 2
    gbs = wx.GridBagSizer(gap, gap)
    self.gbs = gbs
    vertBox.Add(gbs, flag=wx.EXPAND)
    gbs.SetEmptyCellSize((5, 5))
    # Add the bottom spacer
    vertBox.AddSpacer(5)		# Thanks to Christof, DJ4CM
    # End of vertical box.
    self.MakeButtons(frame, gbs)
    minw = width = self.graph.width
    maxw = maxh = -1
    minh = 100
    if conf.window_width > 0:
      minw = width = maxw = conf.window_width
    if conf.window_height > 0:
      minh = maxh = self.height = conf.window_height
    self.main_frame.SetSizeHints(minw, minh, maxw, maxh)
    self.main_frame.SetClientSize(wx.Size(width, self.height))
    if hasattr(Hardware, 'pre_open'):       # pre_open() is called before open()
      Hardware.pre_open()
    if self.local_conf.GetWidgets(self, Hardware, conf, frame, gbs, vertBox):
      pass
    elif conf.quisk_widgets:
      self.bottom_widgets = conf.quisk_widgets.BottomWidgets(self, Hardware, conf, frame, gbs, vertBox)
    if self.bottom_widgets:		# Extend the sliders to the bottom of the screen
      try:
        i = self.bottom_widgets.num_rows_added		# No way to get total rows until ver 2.9 !!
      except:
        i = 1
      rows = self.widget_row + i
      for i in self.slider_columns:
        item = gbs.FindItemAtPosition((0, i))
        item.SetSpan((rows, 1))
    if conf.use_rx_udp and conf.use_rx_udp != 10:
      self.add_version = True		# Add firmware version to config text
    else:
      self.add_version = False
    if conf.use_rx_udp == 10:		# Hermes UDP protocol
      if conf.tx_ip == '':
        conf.tx_ip = Hardware.hermes_ip
      elif conf.tx_ip == 'disable':
        conf.tx_ip = ''
      if conf.tx_audio_port == 0:
        conf.tx_audio_port = conf.rx_udp_port
    elif conf.use_rx_udp:
      conf.rx_udp_decimation = 8 * 8 * 8
      if conf.tx_ip == '':
        conf.tx_ip = conf.rx_udp_ip
      elif conf.tx_ip == 'disable':
        conf.tx_ip = ''
      if conf.tx_audio_port == 0:
        conf.tx_audio_port = conf.rx_udp_port + 2
    # Open the hardware.  This must be called before open_sound().
    self.config_text = Hardware.open()
    if self.config_text:
      self.main_frame.SetConfigText(self.config_text)
    else:
      self.config_text = "Missing config_text"
    if QS.open_key(conf.key_method):
      print('open_key failed for name "%s"' % conf.key_method)
    if hasattr(conf, 'mixer_settings'):
      for dev, numid, value in conf.mixer_settings:
        err_msg = QS.mixer_set(dev, numid, value)
        if err_msg:
          print("Mixer", err_msg)
    QS.capt_channels (conf.channel_i, conf.channel_q)
    QS.play_channels (conf.channel_i, conf.channel_q)
    QS.micplay_channels (conf.mic_play_chan_I, conf.mic_play_chan_Q)
    # Note: Subsequent calls to set channels must not name a higher channel number.
    #       Normally, these calls are only used to reverse the channels.
    QS.open_sound(conf.name_of_sound_capt, conf.name_of_sound_play, 0,
                conf.data_poll_usec, conf.latency_millisecs,
                conf.microphone_name, conf.tx_ip, conf.tx_audio_port,
                conf.mic_sample_rate, conf.mic_channel_I, conf.mic_channel_Q,
				conf.mic_out_volume, conf.name_of_mic_play, conf.mic_playback_rate)
    tune, vfo = Hardware.ReturnFrequency()	# Request initial frequency
    if tune is None or vfo is None:		# Set last-used frequency
      self.bandBtnGroup.SetLabel(self.lastBand, do_cmd=True)
    else:			# Set requested frequency
      self.BandFromFreq(tune)
      self.ChangeDisplayFrequency(tune - vfo, vfo)
    # Record filter rate for the filter screen
    self.filter_screen.sample_rate = QS.get_filter_rate(-1, -1)
    self.config_screen.InitBitmap()
    self.screenBtnGroup.SetLabel(conf.default_screen, do_cmd=True)
    frame.Show()
    self.Yield()
    self.sound_thread = SoundThread()
    self.sound_thread.start()
##    if conf.dxClHost:
##      # create DX Cluster and register listener for change notification
##      self.dxCluster = dxcluster.DxCluster()
##      self.dxCluster.setListener(self.OnDxClChange)
##      self.dxCluster.start()
    # Create shortcut keys for buttons
    if conf.button_layout == 'Large screen':
      for button in self.modeButns.GetButtons():	# mode buttons
        if button.char_shortcut:
          rid = wx.NewId()
          self.main_frame.Bind(wx.EVT_MENU, self.modeButns.Shortcut, id=rid)
          self.accel_list.append(wx.AcceleratorEntry(wx.ACCEL_ALT, ord(button.char_shortcut), rid))
      for button in self.bandBtnGroup.GetButtons():	# band buttons
        if button.char_shortcut:
          rid = wx.NewId()
          self.main_frame.Bind(wx.EVT_MENU, self.bandBtnGroup.Shortcut, id=rid)
          self.accel_list.append(wx.AcceleratorEntry(wx.ACCEL_ALT, ord(button.char_shortcut), rid))
    # Create a shortcut for the PTT key
    if conf.hot_key_ptt1 and not conf.hot_key_ptt_if_hidden:
      rid = wx.NewId()
      frame.Bind(wx.EVT_MENU, self.OnHotKey, id=rid)
      self.accel_list.append(wx.AcceleratorEntry(conf.hot_key_ptt2, conf.hot_key_ptt1, rid))
    self.main_frame.SetAcceleratorTable(wx.AcceleratorTable(self.accel_list))
    self.OnBtnMode(None, self.mode)
  #  self.OnTestTimer(None)
    return True
  #def OnTestTimer(self, event):		# temporary code to switch bands and look for a bug
  #  if event is None:
  #    self.test_time0 = 0
  #    self.test_band = '40'
  #    self.test_timer = wx.Timer(self)
  #    self.Bind(wx.EVT_TIMER, self.OnTestTimer)
  #    self.test_timer.Start(1000, oneShot=True)
  #    return
  #  self.bandBtnGroup.SetLabel(self.test_band, do_cmd=True)
  #  if self.test_band == '40':
  #    self.test_timer.Start(250, oneShot=True)
  #    self.test_band = '30'
  #  else:
  #    self.test_timer.Start(250, oneShot=True)
  #    self.test_band = '40'
  def OnDxClChange(self):
    self.station_screen.Refresh()
  def OnIdle(self, event):
    if self.screen:
      self.screen.OnIdle(event)
  def OnEndSession(self, event):
    event.Skip()
    self.OnBtnClose(event)
  def OnBtnClose(self, event):
    QS.set_file_name(record_button=0)	# Turn off file recording
    time.sleep(0.1)
    if self.sound_thread:
      self.sound_thread.stop()
    for i in range(0, 20):
      if threading.activeCount() == 1:
        break
      time.sleep(0.1)
  def OnExit(self):
    if self.dxCluster:
      self.dxCluster.stop()
    QS.close_rx_udp()
    Hardware.close()
    self.SaveState()
    self.local_conf.SaveState()
    if self.hamlib_com1_handler:
      self.hamlib_com1_handler.close()
    if self.hamlib_com2_handler:
      self.hamlib_com2_handler.close()
    return 0
  def ImmediateChange(self, name):
    value = getattr(conf, name)
    if name == "keyupDelay" and conf.use_rx_udp == 10:		# Hermes UDP protocol
      if value > 1023:
        value = 1023
      Hardware.SetControlByte(0x10, 2, value & 0x3)		# cw_hang_time
      Hardware.SetControlByte(0x10, 1, (value >> 2) & 0xFF)	# cw_hang_time
    QS.ImmediateChange(name)
  def CheckState(self):		# check whether state has changed
    changed = False
    if self.init_path:		# save current program state
      for n in self.StateNames:
        try:
          if getattr(self, n) != self.savedState[n]:
            changed = True
            break
        except:
          changed = True
          break
    return changed
  def SaveState(self):
    if self.init_path:		# save current program state
      d = {}
      for n in self.StateNames:
        d[n] = v = getattr(self, n)
        self.savedState[n] = v
      try:
        fp = open(self.init_path, "wb")
        pickle.dump(d, fp)
        fp.close()
      except:
        pass #traceback.print_exc()
  def Mode2Filters(self, mode):		# return the list of filter bandwidths for each mode
    if mode in ('CWL', 'CWU'):
      return conf.FilterBwCW
    if mode in ('LSB', 'USB'):
      return conf.FilterBwSSB
    if mode == 'AM':
      return conf.FilterBwAM
    if mode in ('FM', 'DGT-FM', 'DGT-IQ'):
      return conf.FilterBwFM
    if mode in ('DGT-U', 'DGT-L'):
      return conf.FilterBwDGT
    if mode[0:4] == 'FDV-':
      return conf.FilterBwFDV
    if mode == 'IMD':
      return conf.FilterBwIMD
    if mode == 'EXT':
      return conf.FilterBwEXT
    return conf.FilterBwSSB
  def OnSmeterRightDown(self, event):
    try:
      pos = event.GetPosition()		# works for right-click
      self.smeter.TextCtrl.PopupMenu(self.smeter_menu, pos)
    except:
      btn = event.GetEventObject()	# works for button
      btn.PopupMenu(self.smeter_menu, (0,0))
  def OnSmeterMeterA(self, event):
    self.smeter_avg_seconds = 1.0
    self.smeter_usage = "smeter"
    QS.measure_frequency(0)
  def OnSmeterMeterB(self, event):
    self.smeter_avg_seconds = 5.0
    self.smeter_usage = "smeter"
    QS.measure_frequency(0)
  def OnSmeterFrequencyA(self, event):
    self.smeter_usage = "freq"
    QS.measure_frequency(2)
  def OnSmeterFrequencyB(self, event):
    self.smeter_usage = "freq"
    QS.measure_frequency(10)
  def OnSmeterAudioA(self, event):
    self.smeter_usage = "audio"
    QS.measure_audio(1)
  def OnSmeterAudioB(self, event):
    self.smeter_usage = "audio"
    QS.measure_audio(5)
  def MakeAccel(self, button):
    rid = wx.NewId()
    self.main_frame.Bind(wx.EVT_MENU, button.Shortcut, id=rid)
    self.accel_list.append(wx.AcceleratorEntry(wx.ACCEL_ALT, ord(button.char_shortcut), rid))
  def MakeButtons(self, frame, gbs):
    from quisk_widgets import button_text_width
    margin = button_text_width
    # Make one or two sliders on the left
    self.sliderVol = SliderBoxV(frame, 'Vol', self.volumeAudio, 1000, self.ChangeVolume)
    self.ChangeVolume()		# set initial volume level
    if Hardware.use_sidetone:
      self.sliderSto = SliderBoxV(frame, 'STo', self.sidetone_volume, 1000, self.ChangeSidetone)
      self.ChangeSidetone()
    else:
      self.sliderSto = None
    # Make four sliders on the right
    self.ritScale = SliderBoxV(frame, 'Rit', self.ritFreq, 2000, self.OnRitScale, False, themin=-2000)
    self.sliderYs = SliderBoxV(frame, 'Ys', 0, 160, self.ChangeYscale, True)
    self.sliderYz = SliderBoxV(frame, 'Yz', 0, 160, self.ChangeYzero, True)
    self.sliderZo = SliderBoxV(frame, 'Zo', 0, 1000, self.OnChangeZoom)
    self.sliderZo.SetValue(0)
    flag = wx.EXPAND
    # Add band buttons
    if conf.button_layout == 'Large screen':
      self.widget_row = 4		# Next available row for widgets
      shortcuts = []
      for label in conf.bandLabels:
        if type(label) in (ListType, TupleType):
          label = label[0]
        shortcuts.append(conf.bandShortcuts.get(label, ''))
      self.bandBtnGroup = RadioButtonGroup(frame, self.OnBtnBand, conf.bandLabels, None, shortcuts)
    else:
      self.widget_row = 6		# Next available row for widgets
      self.bandBtnGroup = RadioBtnPopup(frame, self.OnBtnBand, conf.bandLabels, None)
    # Add sliders on the left
    gbs.Add(self.sliderVol, (0, 0), (self.widget_row, 1), flag=wx.EXPAND|wx.LEFT, border=margin)
    if Hardware.use_sidetone:
      button_start_col = 2
      self.slider_columns = [0, 1]
      gbs.Add(self.sliderSto, (0, 1), (self.widget_row, 1), flag=flag)
    else:
      self.slider_columns = [0]
      button_start_col = 1
    # Receive button row: Mute, AGC
    left_row2 = []
    b = b_mute = QuiskCheckbutton(frame, self.OnBtnMute, text='Mute')
    b.char_shortcut = 'u'
    self.MakeAccel(b)
    left_row2.append(b)
    agc = QuiskCheckbutton(frame, self.OnBtnAGC, 'AGC')
    agc.char_shortcut = 'G'
    self.MakeAccel(agc)
    b = WrapSlider(agc, self.OnBtnAGC, display=True)
    b.SetDual(True)
    b.SetSlider(value_off=self.levelOffAGC, value_on=self.levelAGC)
    agc.SetValue(True, True)
    left_row2.append(b)
    b = self.BtnSquelch = QuiskCheckbutton(frame, self.OnBtnSquelch, text='Sqlch')
    b.char_shortcut = 'q'
    self.MakeAccel(b)
    self.sliderSquelch = WrapSlider(b, self.OnBtnSquelch, display=True)
    left_row2.append(self.sliderSquelch)
    b = QuiskCycleCheckbutton(frame, self.OnBtnNB, ('NB', 'NB 1', 'NB 2', 'NB 3'))
    b.char_shortcut = 'B'
    self.MakeAccel(b)
    left_row2.append(b)
    b = QuiskCheckbutton(frame, self.OnBtnAutoNotch, text='Notch')
    b.char_shortcut = 'h'
    self.MakeAccel(b)
    left_row2.append(b)
    try:
      gain_labels = Hardware.rf_gain_labels
    except:
      gain_labels = ()
    try:
      ant_labels = Hardware.antenna_labels
    except:
      ant_labels = ()
    self.BtnRfGain = None
    add_2 = 0	# Add two more buttons
    if gain_labels:
      b = self.BtnRfGain = QuiskCycleCheckbutton(frame, Hardware.OnButtonRfGain, gain_labels)
      left_row2.append(b)
      add_2 += 1
    if ant_labels:
      b = QuiskCycleCheckbutton(frame, Hardware.OnButtonAntenna, ant_labels)
      left_row2.append(b)
      add_2 += 1
    if add_2 == 0:
      b = QuiskCheckbutton(frame, None, text='RfGain')
      b.Enable(False)
      left_row2.append(b)
      add_2 += 1
    if add_2 == 1:
      if 0:	# Display a color chooser
        #b_test1 = QuiskPushbutton(frame, self.OnBtnColorDialog, 'Color')
        b_test1 = QuiskRepeatbutton(frame, self.OnBtnColor, 'Color', use_right=True)
      else:
        b_test1 = self.test1Button = QuiskCheckbutton(frame, self.OnBtnTest1, 'Test 1', color=conf.color_test)
      left_row2.append(b_test1)
    else:
      b_test1 = None
    # Transmit button row: Spot
    left_row3=[]
    bt = QuiskCheckbutton(frame, self.OnBtnSpot, 'Spot', color=conf.color_test)
    b = WrapSlider(bt, self.OnBtnSpot, slider_value=self.levelSpot, display=True)
    if hasattr(Hardware, 'OnSpot'):
      bt.char_shortcut = 'o'
      self.MakeAccel(bt)
    else:
      b.Enable(False)
    left_row3.append(b)
    # Split button
    self.split_menu = wx.Menu()
    item1 = self.split_menu.AppendRadioItem(-1, 'Play both, High Freq on R')
    self.Bind(wx.EVT_MENU, self.OnMenuSplitPlay1, item1)
    item2 = self.split_menu.AppendRadioItem(-1, 'Play both, High Freq on L')
    self.Bind(wx.EVT_MENU, self.OnMenuSplitPlay2, item2)
    item3 = self.split_menu.AppendRadioItem(-1, 'Play only Rx')
    self.Bind(wx.EVT_MENU, self.OnMenuSplitPlay3, item3)
    item4 = self.split_menu.AppendRadioItem(-1, 'Play only Tx')
    self.Bind(wx.EVT_MENU, self.OnMenuSplitPlay4, item4)
    if self.split_rxtx_play == 1:
      item1.Check()
    elif self.split_rxtx_play == 2:
      item2.Check()
    elif self.split_rxtx_play == 3:
      item3.Check()
    elif self.split_rxtx_play == 4:
      item4.Check()
    self.split_menu.AppendSeparator()
    item = self.split_menu.Append(-1, 'Reverse Rx and Tx')
    self.Bind(wx.EVT_MENU, self.OnMenuSplitRev, item)
    item = self.split_menu.AppendCheckItem(-1, 'Lock Tx Frequency')
    self.Bind(wx.EVT_MENU, self.OnMenuSplitLock, item)
    self.split_menu.AppendSeparator()
    item = self.split_menu.AppendRadioItem(-1, 'Hamlib control Tx')
    self.Bind(wx.EVT_MENU, self.OnMenuSplitCtlTx, item)
    item = self.split_menu.AppendRadioItem(-1, 'Hamlib control Rx')
    self.Bind(wx.EVT_MENU, self.OnMenuSplitCtlRx, item)
    b = QuiskCheckbutton(frame, self.OnBtnSplit, "Split")
    b.char_shortcut = 'l'
    self.MakeAccel(b)
    self.splitButton = WrapMenu(b, self.split_menu)
    if conf.mouse_tune_method:		# Mouse motion changes the VFO frequency
      self.splitButton.Enable(False)
    left_row3.append(self.splitButton)
    b = QuiskCheckbutton(frame, self.OnBtnFDX, 'FDX', color=conf.color_test)
    if conf.add_fdx_button:
      b.char_shortcut = 'X'
      self.MakeAccel(b)
    else:
      b.Enable(False)
    left_row3.append(b)
    if hasattr(Hardware, 'OnButtonPTT'):
      b = QuiskCheckbutton(frame, self.OnButtonPTT, 'PTT', color='red')
      self.pttButton = b
      left_row3.append(b)
      b = QuiskCheckbutton(frame, self.OnButtonVOX, 'VOX')
      b.char_shortcut = 'V'
      self.MakeAccel(b)
      left_row3.append(b)
    else:
      b = QuiskCheckbutton(frame, None, 'PTT')
      b.Enable(False)
      left_row3.append(b)
      b = QuiskCheckbutton(frame, None, 'VOX')
      b.Enable(False)
      left_row3.append(b)
    # add another receiver
    self.multi_rx_menu = wx.Menu()
    item = self.multi_rx_menu.AppendRadioItem(-1, 'Play only')
    self.Bind(wx.EVT_MENU, self.OnMultirxPlayBoth, item)
    item = self.multi_rx_menu.AppendRadioItem(-1, 'Play on left')
    self.Bind(wx.EVT_MENU, self.OnMultirxPlayLeft, item)
    item = self.multi_rx_menu.AppendRadioItem(-1, 'Play on right')
    self.Bind(wx.EVT_MENU, self.OnMultirxPlayRight, item)
    btn_addrx = QuiskPushbutton(frame, self.multi_rx_screen.OnAddReceiver, "Add Rx")
    btn_addrx = WrapMenu(btn_addrx, self.multi_rx_menu)
    if not hasattr(Hardware, 'MultiRxCount'):
      btn_addrx.Enable(False)
    # Record and Playback buttons
    b = self.btnTmpRecord = QuiskCheckbutton(frame, self.OnBtnTmpRecord, text=conf.Xbtn_text_rec)
    #left_row3.append(b)
    b = self.btnTmpPlay = QuiskCheckbutton(frame, self.OnBtnTmpPlay, text=conf.Xbtn_text_play)
    b.Enable(0)
    #left_row3.append(b)
    self.btn_file_record = QuiskCheckbutton(frame, self.OnBtnFileRecord, conf.Xbtn_text_file_rec)
    self.btn_file_record.Enable(0)
    left_row3.append(self.btn_file_record)
    self.btnFilePlay = QuiskCheckbutton(frame, self.OnBtnFilePlay, conf.Xbtn_text_file_play)
    self.btnFilePlay.Enable(0)
    left_row3.append(self.btnFilePlay)
    ### Right bank of buttons
    mode_names = ['CWL', 'CWU', 'LSB', 'USB', 'AM', 'FM', 'DGT-U', 'DGT-L', 'DGT-FM', 'DGT-IQ', 'FDV-U', 'FDV-L', 'IMD']
    labels = [('CWL', 'CWU'), ('LSB', 'USB'), 'AM', 'FM', ('DGT-U', 'DGT-L', 'DGT-FM', 'DGT-IQ')]
    shortcuts = ['C', 'S', 'A', 'M', 'D']
    count = 5	# There is room for seven buttons
    if conf.add_freedv_button:
      n_freedv = count
      count += 1
      labels.append('FDV-U')
      shortcuts.append('F')
    if conf.add_imd_button:
      n_imd = count
      count += 1
      labels.append('IMD')
      shortcuts.append('I')
    if count < 7 and conf.add_extern_demod:
      labels.append(conf.add_extern_demod)
      mode_names.append(conf.add_extern_demod)
      shortcuts.append('')
    while count < 7:
      count += 1
      labels.append('')
      shortcuts.append('')
    mode_names.sort()
    self.config_screen.favorites.SetModeEditor(mode_names)
    if conf.button_layout == 'Large screen':
      self.modeButns = RadioButtonGroup(frame, self.OnBtnMode, labels, None, shortcuts)
    else:
      labels = ['CWL', 'CWU', 'LSB', 'USB', 'AM', 'FM', 'DGT-U', 'DGT-L', 'DGT-FM', 'DGT-IQ', 'FDV-U', 'IMD']
      self.modeButns = RadioBtnPopup(frame, self.OnBtnMode, labels, None)
    self.freedv_menu_items = {}
    if conf.add_freedv_button:
      self.freedv_menu = wx.Menu()
      item = self.freedv_menu.Append(-1, 'Upper sideband')
      self.Bind(wx.EVT_MENU, self.OnFreedvMenu, item)
      item = self.freedv_menu.Append(-1, 'Lower sideband')
      self.Bind(wx.EVT_MENU, self.OnFreedvMenu, item)
      self.freedv_menu.AppendSeparator()
      msg = conf.freedv_tx_msg
      QS.freedv_set_options(mode=conf.freedv_modes[0][1], tx_msg=msg, DEBUG=0, squelch=1)
      for mode, index in conf.freedv_modes:
        item = self.freedv_menu.AppendRadioItem(-1, mode)
        self.freedv_menu_items[index] = item
        self.Bind(wx.EVT_MENU, self.OnFreedvMenu, item)
        if '700D' in mode:
          item.Check()
          QS.freedv_set_options(mode=index)
      if conf.button_layout == 'Large screen':
        b = QuiskCheckbutton(frame, self.OnBtnMode, 'FDV-U')
        b.char_shortcut = 'F'
        self.btnFreeDV = WrapMenu(b, self.freedv_menu)
        self.modeButns.ReplaceButton(n_freedv, self.btnFreeDV)
      else:
        self.btnFreeDV = self.modeButns.AddMenu('FDV-U', self.freedv_menu)
      try:
        ok = QS.freedv_open()
      except:
        traceback.print_exc()
        ok = 0
      if not ok:
        conf.add_freedv_button = False
        if conf.button_layout == 'Large screen':
          self.modeButns.GetButtons()[n_freedv].Enable(0)
        else:
          self.modeButns.Enable('FDV-U', False)
    if conf.add_imd_button:
      val = 500
      QS.set_imd_level(val)
      if conf.button_layout == 'Large screen':
        b = QuiskCheckbutton(frame, None, 'IMD', color=conf.color_test)
        b.char_shortcut = 'I'
        b = WrapSlider(b, self.OnImdSlider, slider_value=val, display=True)
        self.modeButns.ReplaceButton(n_imd, b)
      else:
        self.modeButns.AddSlider('IMD', self.OnImdSlider, slider_value=val, display=True)
    labels = ('2000', '2000', '2000', '2000', '2000', '2000')
    self.filterButns = RadioButtonGroup(frame, self.OnBtnFilter, labels, None)
    b = QuiskCheckbutton(frame, None, str(self.filterAdjBw1))
    b = WrapSlider(b, self.OnBtnAdjFilter, slider_value=self.filterAdjBw1, wintype='filter')
    self.filterButns.ReplaceButton(5, b)
    right_row2 = self.filterButns.GetButtons()
    if self.rate_audio_fft:
      t = "Audio FFT"
    elif conf.use_rx_udp == 10:		# Hermes UDP protocol
      t = "Bscope"
    else:
      t = "RX Filter"
    if conf.button_layout == 'Large screen':
      labels = (('Graph', 'GraphP1', 'GraphP2'), 'WFall', ('Scope', 'Scope'), 'Config', t, 'Help')
      self.screenBtnGroup = RadioButtonGroup(frame, self.OnBtnScreen, labels, conf.default_screen)
      right_row3 = self.screenBtnGroup.GetButtons()
    else:
      labels = ('Graph', 'GraphP1', 'GraphP2', 'WFall', 'Scope', 'Config', t)
      self.screenBtnGroup = RadioBtnPopup(frame, self.OnBtnScreen, labels, conf.default_screen)
    # Top row -----------------
    # Band down button
    szr = wx.BoxSizer(wx.HORIZONTAL)	# add control to box sizer for centering
    b_bandupdown = szr
    b = QuiskRepeatbutton(frame, self.OnBtnDownBand, conf.Xbtn_text_range_dn,
             self.OnBtnUpDnBandDone, use_right=True)
    szr.Add(b, 1, flag=wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, border=1)
    # Band up button
    b = QuiskRepeatbutton(frame, self.OnBtnUpBand, conf.Xbtn_text_range_up,
             self.OnBtnUpDnBandDone, use_right=True)
    szr.Add(b, 1, flag=wx.ALIGN_CENTER_VERTICAL|wx.LEFT, border=1)
    # Memory buttons
    szr = wx.BoxSizer(wx.HORIZONTAL)	# add control to box sizer for centering
    b_membtn = szr
    b = QuiskPushbutton(frame, self.OnBtnMemSave, conf.Xbtn_text_mem_add)
    szr.Add(b, 1, flag=wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, border=1)
    b = self.memNextButton = QuiskPushbutton(frame, self.OnBtnMemNext, conf.Xbtn_text_mem_next)
    b.Enable(False)
    self.Bind(wx.EVT_RIGHT_DOWN, self.OnRightClickMemory, b)
    szr.Add(b, 1, flag=wx.ALIGN_CENTER_VERTICAL|wx.LEFT|wx.RIGHT, border=1)
    b = self.memDeleteButton = QuiskPushbutton(frame, self.OnBtnMemDelete, conf.Xbtn_text_mem_del)
    b.Enable(False)
    szr.Add(b, 1, flag=wx.ALIGN_CENTER_VERTICAL|wx.LEFT, border=1)
    # Favorites buttons
    szr = wx.BoxSizer(wx.HORIZONTAL)	# add control to box sizer for centering
    b_fav = szr
    b = self.StationNewButton = QuiskPushbutton(frame, self.OnBtnFavoritesNew, conf.Xbtn_text_fav_add)
    szr.Add(b, 1, flag=wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, border=1)
    b = self.StationNewButton = QuiskPushbutton(frame, self.OnBtnFavoritesShow, conf.Xbtn_text_fav_recall)
    szr.Add(b, 1, flag=wx.ALIGN_CENTER_VERTICAL|wx.LEFT, border=1)
    # Add another receiver
    szr = wx.BoxSizer(wx.HORIZONTAL)	# add control to box sizer for centering
    b_addrx = szr
    szr.Add(btn_addrx, 1, flag=wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, border=1)
    # Temporary play and record
    szr = wx.BoxSizer(wx.HORIZONTAL)	# add control to box sizer for centering
    b_tmprec = szr
    szr.Add(self.btnTmpRecord, 1, flag=wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, border=1)
    szr.Add(self.btnTmpPlay, 1, flag=wx.ALIGN_CENTER_VERTICAL|wx.LEFT, border=1)
    # RIT button
    szr = wx.BoxSizer(wx.HORIZONTAL)	# add control to box sizer for centering
    b_rit = szr
    self.ritButton = QuiskCheckbutton(frame, self.OnBtnRit, "RIT")
    szr.Add(self.ritButton, 1, flag=wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, border=1)
    self.ritButton.SetLabel("RIT %d" % self.ritFreq)
    self.ritButton.Refresh()
    # Frequency display
    bw, bh = b_mute.GetMinSize()
    b_freqdisp = self.freqDisplay = FrequencyDisplay(frame, 99999, bh * 15 // 10)
    self.freqDisplay.Display(self.txFreq + self.VFO)
    # Frequency entry
    if conf.button_layout == 'Large screen':
      e = wx.TextCtrl(frame, -1, '', size=(10, bh), style=wx.TE_PROCESS_ENTER)
      font = wx.Font(10, wx.FONTFAMILY_SWISS, wx.NORMAL, wx.FONTWEIGHT_NORMAL, False, conf.quisk_typeface)
      e.SetFont(font)
      e.SetBackgroundColour(conf.color_entry)
      e.SetForegroundColour(conf.color_entry_txt)
      szr = wx.BoxSizer(wx.HORIZONTAL)	# add control to box sizer for centering
      b_freqenter = szr
      szr.Add(e, 1, flag=wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL)
      frame.Bind(wx.EVT_TEXT_ENTER, self.FreqEntry, source=e)
    # S-meter
    self.smeter = QuiskText(frame, ' S9+23 -166.00 dB ', bh, wx.ALIGN_LEFT, True)
    b = QuiskPushbutton(frame, self.OnSmeterRightDown, '..')
    szr = wx.BoxSizer(wx.HORIZONTAL)
    b_smeter = szr
    szr.Add(self.smeter, 1, flag=wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL)
    szr.Add(b, 0, flag=wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL)
    self.smeter.TextCtrl.Bind(wx.EVT_RIGHT_DOWN, self.OnSmeterRightDown)
    self.smeter.TextCtrl.SetBackgroundColour(conf.color_freq)
    self.smeter.TextCtrl.SetForegroundColour(conf.color_freq_txt)
    # Make a popup menu for the s-meter
    self.smeter_menu = wx.Menu()
    item = self.smeter_menu.Append(-1, 'S-meter 1')
    self.Bind(wx.EVT_MENU, self.OnSmeterMeterA, item)
    item = self.smeter_menu.Append(-1, 'S-meter 5')
    self.Bind(wx.EVT_MENU, self.OnSmeterMeterB, item)
    item = self.smeter_menu.Append(-1, 'Frequency 2')
    self.Bind(wx.EVT_MENU, self.OnSmeterFrequencyA, item)
    item = self.smeter_menu.Append(-1, 'Frequency 10')
    self.Bind(wx.EVT_MENU, self.OnSmeterFrequencyB, item)
    item = self.smeter_menu.Append(-1, 'Audio 1')
    self.Bind(wx.EVT_MENU, self.OnSmeterAudioA, item)
    item = self.smeter_menu.Append(-1, 'Audio 5')
    self.Bind(wx.EVT_MENU, self.OnSmeterAudioB, item)
    # Make a popup menu for the memory buttons
    self.memory_menu = wx.Menu()
    # Place the buttons on the screen
    if conf.button_layout == 'Large screen':
      # There are fourteen columns, a small gap column, and then twelve more columns
      band_buttons = self.bandBtnGroup.buttons
      if len(band_buttons) <= 7:
        bmax = 7
        span = 2
      else:
        bmax = 14
        span = 1
      col = 0
      for b in band_buttons[0:bmax]:
        gbs.Add(b, (1, button_start_col + col), (1, span), flag=flag)
        col += span
      while col < 14:
        b = QuiskCheckbutton(frame, None, text='')
        gbs.Add(b, (1, button_start_col + col), (1, span), flag=flag)
        col += span
      col = button_start_col
      for b in left_row2:
        gbs.Add(b, (2, col), (1, 2), flag=flag)
        col += 2
      col = button_start_col
      for b in left_row3:
        gbs.Add(b, (3, col), (1, 2), flag=flag)
        col += 2
      col = 15
      for b in  self.modeButns.GetButtons():
        if col in (19, 20):		# single column
          gbs.Add(b, (1, button_start_col + col), flag=flag)
          col += 1
        else:						# double column
          gbs.Add(b, (1, button_start_col + col), (1, 2), flag=flag)
          col += 2
      col = button_start_col + 15
      for i in range(0, 6):
        gbs.Add(right_row2[i], (2, col), (1, 2), flag=flag)
        gbs.Add(right_row3[i], (3, col), (1, 2), flag=flag)
        col += 2
      gbs.Add(b_freqdisp, (0, button_start_col), (1, 6),
         flag=wx.EXPAND | wx.TOP | wx.BOTTOM, border=self.freqDisplay.border)
      gbs.Add(b_freqenter,  (0, button_start_col + 6), (1, 2), flag = wx.EXPAND|wx.LEFT|wx.RIGHT, border=5)
      gbs.Add(b_bandupdown, (0, button_start_col + 8), (1, 2), flag=wx.EXPAND)
      gbs.Add(b_membtn,     (0, button_start_col + 11), (1, 3), flag = wx.EXPAND)
      gbs.Add(b_fav,        (0, button_start_col + 15), (1, 2), flag=wx.EXPAND)        
      gbs.Add(b_tmprec,     (0, button_start_col + 17), (1, 2), flag=wx.EXPAND)        
      gbs.Add(b_addrx,      (0, button_start_col + 19), (1, 2), flag=wx.EXPAND)        
      gbs.Add(b_smeter,     (0, button_start_col + 21), (1, 4), flag=wx.EXPAND)
      gbs.Add(b_rit,        (0, button_start_col + 25), (1, 2), flag=wx.EXPAND)
      col = button_start_col + 28
      self.slider_columns += [col, col + 1, col + 2, col + 3]
      gbs.Add(self.ritScale, (0, col    ), (self.widget_row, 1), flag=wx.EXPAND|wx.LEFT, border=margin)
      gbs.Add(self.sliderYs, (0, col + 1), (self.widget_row, 1), flag=flag)
      gbs.Add(self.sliderYz, (0, col + 2), (self.widget_row, 1), flag=flag)
      gbs.Add(self.sliderZo, (0, col + 3), (self.widget_row, 1), flag=flag)
      for i in range(button_start_col, button_start_col + 14):
        gbs.AddGrowableCol(i,1)
      for i in range(button_start_col + 15, button_start_col + 27):
        gbs.AddGrowableCol(i,1)
    else:
      gbs.Add(b_freqdisp, (0, button_start_col), (1, 6),
         flag=wx.EXPAND | wx.TOP | wx.BOTTOM, border=self.freqDisplay.border)
      gbs.Add(b_bandupdown, (0, button_start_col + 6), (1, 2), flag=wx.EXPAND)
      gbs.Add(b_smeter,    (0, button_start_col + 8), (1, 4), flag=wx.EXPAND)

      gbs.Add(self.bandBtnGroup.GetPopControl(),   (1, button_start_col), (1, 2), flag=flag)
      gbs.Add(self.modeButns.GetPopControl(),      (3, button_start_col), (1, 2), flag=flag)
      gbs.Add(self.screenBtnGroup.GetPopControl(), (4, button_start_col), (1, 2), flag=flag)
      b = QuiskCheckbutton(frame, self.OnBtnHelp, 'Help')
      gbs.Add(b, (5, button_start_col), (1, 2), flag=flag)

      gbs.Add(b_membtn, (1, button_start_col + 2), (1, 3), flag = wx.EXPAND)
      gbs.Add(b_fav,    (1, button_start_col + 5), (1, 2), flag = wx.EXPAND)
      gbs.Add(b_tmprec, (1, button_start_col + 7), (1, 2), flag=wx.EXPAND)        
      b = QuiskPushbutton(frame, None, '')
      gbs.Add(b,        (1, button_start_col + 9), (1, 1), flag=wx.EXPAND)        
      gbs.Add(b_rit,    (1, button_start_col + 10), (1, 2), flag=wx.EXPAND)        

      row = 2
      col = button_start_col
      for b in self.filterButns.GetButtons():
        gbs.Add(b, (row, col), (1, 2), flag=flag)
        col += 2

      buttons = left_row2 + left_row3
      if b_test1:
        buttons.remove(b_test1)
        buttons += [b_test1, btn_addrx]
      else:
        buttons += [btn_addrx]
      row = 3
      col = 2
      for b in buttons:
        gbs.Add(b, (row, button_start_col + col), (1, 2), flag=flag)
        col += 2
        if col >= 12:
          row += 1
          col = 2
      col = button_start_col + 12
      self.slider_columns += [col, col + 1, col + 2, col + 3]
      gbs.Add(self.ritScale, (0, col), (self.widget_row, 1), flag=wx.EXPAND|wx.LEFT, border=margin)
      gbs.Add(self.sliderYs, (0, col + 1), (self.widget_row, 1), flag=flag)
      gbs.Add(self.sliderYz, (0, col + 2), (self.widget_row, 1), flag=flag)
      gbs.Add(self.sliderZo, (0, col + 3), (self.widget_row, 1), flag=flag)
      for i in range(button_start_col, button_start_col + 12):
        gbs.AddGrowableCol(i,1)
    self.button_start_col = button_start_col
  def MeasureAudioVoltage(self):
    v = QS.measure_audio(-1)
    t = "%11.3f" % v
    t = t[0:1] + ' ' + t[1:4] + ' ' + t[4:] + ' uV'
    self.smeter.SetLabel(t)
  def MeasureFrequency(self):
    vfo = Hardware.ReturnVfoFloat()
    if vfo is None:
      vfo = self.VFO
    vfo += Hardware.transverter_offset
    t = '%13.2f' % (QS.measure_frequency(-1) + vfo)
    t = t[0:4] + ' ' + t[4:7] + ' ' + t[7:] + ' Hz'
    self.smeter.SetLabel(t)
  def NewDVmeter(self):
    if conf.add_freedv_button:
      snr = QS.freedv_get_snr()
      txt = QS.freedv_get_rx_char()
      self.graph.ScrollMsg(txt)
      self.waterfall.ScrollMsg(txt)
    else:
      snr = 0.0
    t = "  SNR %3.0f" % snr
    self.smeter.SetLabel(t)
  def NewSmeter(self):
    self.smeter_db_count += 1		# count for average
    x = QS.get_smeter()
    self.smeter_db_sum += x		# sum for average
    if self.timer - self.smeter_db_time0 > self.smeter_avg_seconds:		# average time reached
      self.smeter_db = self.smeter_db_sum / self.smeter_db_count
      self.smeter_db_count = self.smeter_db_sum = 0 
      self.smeter_db_time0 = self.timer
    if self.smeter_sunits < x:		# S-meter moves to peak value
      self.smeter_sunits = x
    else:			# S-meter decays at this time constant
      self.smeter_sunits -= (self.smeter_sunits - x) * (self.timer - self.smeter_sunits_time0)
    self.smeter_sunits_time0 = self.timer
    s = self.smeter_sunits / 6.0	# change to S units; 6db per S unit
    s += Hardware.correct_smeter	# S-meter correction for the gain, band, etc.
    if s < 0:
      s = 0
    if s >= 9.5:
      s = (s - 9.0) * 6
      t = "  S9+%2.0f %7.2f dB" % (s, self.smeter_db)
    else:
      t = "  S%.0f  %7.2f dB" % (s, self.smeter_db)
    self.smeter.SetLabel(t)
  def MakeFilterButtons(self, args):
    # Change the filter selections depending on the mode: CW, SSB, etc.
    # Do not change the adjustable filter buttons.
    buttons = self.filterButns.GetButtons()
    for i in range(0, len(buttons) - 1):
      label = str(args[i])
      buttons[i].SetLabel(label)
      buttons[i].Refresh()
      if label:
        buttons[i].Enable(1)
      else:
        buttons[i].Enable(0)
  def MakeFilterCoef(self, rate, N, bw, center):
    """Make an I/Q filter with rectangular passband."""
    center = abs(center)
    lowpass = bw * 24000 // rate // 2
    if lowpass in Filters:
      filtD = Filters[lowpass]
      #print ("Custom filter key %d rate %d bandwidth %d size %d" % (lowpass, rate, bw, len(filtD)))
    else:
      #print ("Window filter key %d rate %d bandwidth %d" % (lowpass, rate, bw))
      if N is None:
        shape = 1.5       # Shape factor at 88 dB
        trans = (bw / 2.0 / rate) * (shape - 1.0)     # 88 dB atten
        N = int(4.0 / trans)
        if N > 1000:
          N = 1000
        N = (N // 2) * 2 + 1
      K = bw * N // rate
      filtD = []
      pi = math.pi
      sin = math.sin
      cos = math.cos
      for k in range(-N//2, N//2 + 1):
        # Make a lowpass filter
        if k == 0:
          z = float(K) / N
        else:
          z = 1.0 / N * sin(pi * k * K / N) / sin(pi * k / N)
        # Apply a windowing function
        if 1:	# Blackman window
          w = 0.42 + 0.5 * cos(2. * pi * k / N) + 0.08 * cos(4. * pi * k / N)
        elif 0:	# Hamming
          w = 0.54 + 0.46 * cos(2. * pi * k / N)
        elif 0:	# Hanning
          w = 0.5 + 0.5 * cos(2. * pi * k / N)
        else:
          w = 1
        z *= w
        filtD.append(z)
    if center:
      # Make a bandpass filter by tuning the low pass filter to new center frequency.
      # Make two quadrature filters.
      filtI = []
      filtQ = []
      tune = -1j * 2.0 * math.pi * center / rate;
      NN = len(filtD)
      D = (NN - 1.0) / 2.0;
      for i in range(NN):
        z = 2.0 * cmath.exp(tune * (i - D)) * filtD[i]
        filtI.append(z.real)
        filtQ.append(z.imag)
      return filtI, filtQ
    return filtD, filtD
  def SetFilterByMode(self, mode):
    index = self.modeFilter[mode]
    try:
      bw = int(self.filterButns.buttons[index].GetLabel())
    except:
      bw = int(self.filterButns.buttons[0].GetLabel())
    self.OnBtnFilter(None, bw)
  def GetFilterCenter(self, mode, bandwidth):
    if mode in ('CWU', 'CWL'):
      center = max(conf.cwTone, bandwidth // 2)
    elif mode in ('LSB', 'USB'):
      center = 300 + bandwidth // 2
    elif mode in ('AM',):
      center = 0
    elif mode in ('FM',):
      center = 0
    elif mode in ('DGT-U', 'DGT-L'):
      center = max(1500, bandwidth // 2)
    elif mode in ('DGT-IQ', 'DGT-FM'):
      center = 0
    elif mode in ('FDV-U', 'FDV-L'):
      center = max(1500, bandwidth // 2)
    elif mode in ('IMD',):
      center = 300 + bandwidth // 2
    else:
      center = 300 + bandwidth // 2
    if mode in ('CWL', 'LSB', 'DGT-L', 'FDV-L'):
      center = - center
    return center
  def OnBtnAdjFilter(self, event):
    btn = event.GetEventObject()
    bw = int(btn.GetLabel())
    self.filterAdjBw1 = bw
    if self.filterButns.GetIndex() == 5:
      self.OnBtnFilter(event)
  def OnBtnFilter(self, event, bw=None):
    if event is None:	# called by application
      self.filterButns.SetLabel(str(bw))
    else:		# called by button
      btn = event.GetEventObject()
      bw = int(btn.GetLabel())
    index = self.filterButns.GetIndex()
    mode = self.mode
    frate = QS.get_filter_rate(Mode2Index.get(mode, 3), bw)
    bw = min(bw, frate // 2)
    self.filter_bandwidth = bw
    center = self.GetFilterCenter(mode, bw)
    # save and restore filter when changing modes
    if mode in ('CWU', 'CWL'):
      self.modeFilter['CW'] = index
    elif mode in ('LSB', 'USB'):
      self.modeFilter['SSB'] = index
    elif mode in ('AM',):
      self.modeFilter['AM'] = index
    elif mode in ('FM',):
      self.modeFilter['FM'] = index
    elif mode in ('DGT-U', 'DGT-L'):
      self.modeFilter['DGT'] = index
    elif mode in ('DGT-IQ', 'DGT-FM'):
      self.modeFilter['DGT'] = index
    elif mode in ('FDV-U', 'FDV-L'):
      self.modeFilter['FDV'] = index
    elif mode in ('IMD',):
      self.modeFilter['IMD'] = index
    print("frate: %d" %frate)  
    filtI, filtQ = self.MakeFilterCoef(frate, None, bw, center)
##    for i in range( 10):
##      print(filtI[i])
    lower_edge = center - bw // 2
    QS.set_filters(filtI, filtQ, bw, lower_edge, 0)
    #print("mode: %s; frate: %d; filtI: %d; filtQ: %d; center: %d; bw: %d; lower_edge: %d" %(mode, frate, 0, 0, center, bw, lower_edge,))
    self.multi_rx_screen.graph.filter_mode = mode
    self.multi_rx_screen.graph.filter_bandwidth = bw
    self.multi_rx_screen.graph.filter_center = center
    self.multi_rx_screen.waterfall.pane1.filter_mode = mode
    self.multi_rx_screen.waterfall.pane1.filter_bandwidth = bw
    self.multi_rx_screen.waterfall.pane1.filter_center = center
    self.multi_rx_screen.waterfall.pane2.filter_mode = mode
    self.multi_rx_screen.waterfall.pane2.filter_bandwidth = bw
    self.multi_rx_screen.waterfall.pane2.filter_center = center
    if self.screen is self.filter_screen:
      self.screen.NewFilter()
  def OnFreedvMenu(self, event):
    idd = event.GetId()
    text = self.freedv_menu.GetLabel(idd)
    if text[0:5] == 'Upper':
      self.btnFreeDV.SetLabel('FDV-U')
      self.btnFreeDV.Refresh()
      self.OnBtnMode(None, 'FDV-U')
      return
    if text[0:5] == 'Lower':
      self.btnFreeDV.SetLabel('FDV-L')
      self.btnFreeDV.Refresh()
      self.OnBtnMode(None, 'FDV-L')
      return
    for mode, index in conf.freedv_modes:
      if mode == text:
        break
    else:
      print ("Failure in OnFreedvMenu")
      return
    mode = QS.freedv_set_options(mode=index)
    if mode != index:		# change to new mode failed
      self.freedv_menu_items[mode].Check(1)
      pos = (self.width//2, self.height//2)
      dlg = wx.MessageDialog(self.main_frame, "No codec2 support for mode " + text, "FreeDV Modes", wx.OK, pos)
      dlg.ShowModal()
  def OnBtnHelp(self, event):
    if event.GetEventObject().GetValue():
      self.OnBtnScreen(None, 'Help')
    else:
      self.OnBtnScreen(None, self.screenBtnGroup.GetLabel())
  def OnBtnScreen(self, event, name=None):
    if event is not None:
      win = event.GetEventObject()
      name = win.GetLabel()
    self.screen.Hide()
    self.station_screen.Hide()
    if name == 'Config':
      self.config_screen.FinishPages()
      self.screen = self.config_screen
    elif name[0:5] == 'Graph':
      self.screen = self.multi_rx_screen
      self.screen.ChangeRxZero(True)
      self.screen.SetTxFreq(self.txFreq, self.rxFreq)
      self.freqDisplay.Display(self.VFO + self.txFreq)
      self.screen.PeakHold(name)
      self.station_screen.Show()
    elif name == 'WFall':
      self.screen = self.multi_rx_screen
      self.screen.ChangeRxZero(False)
      self.screen.SetTxFreq(self.txFreq, self.rxFreq)
      self.freqDisplay.Display(self.VFO + self.txFreq)
      sash = self.screen.GetSashPosition()
      self.station_screen.Show()
    elif name == 'Scope':
      if win.direction:				# Another push on the same button
        self.scope.running = 1 - self.scope.running		# Toggle run state
      else:				# Initial push of button
        self.scope.running = 1
      self.screen = self.scope
    elif name == 'RX Filter':
      self.screen = self.filter_screen
      self.freqDisplay.Display(self.screen.txFreq)
      self.screen.NewFilter()
    elif name == 'Bscope':
      self.screen = self.bandscope_screen
      self.screen.SetTxFreq(self.txFreq, self.rxFreq)
    elif name == 'Audio FFT':
      self.screen = self.audio_fft_screen
      self.freqDisplay.Display(self.screen.txFreq)
    elif name == 'Help':
      self.screen = self.help_screen
    self.screen.Show()
    self.vertBox.Layout()	# This destroys the initialized sash position!
    self.sliderYs.SetValue(self.screen.y_scale)
    self.sliderYz.SetValue(self.screen.y_zero)
    if name == 'WFall':
      self.screen.SetSashPosition(sash)
  def OnBtnFileRecord(self, event):
    if event.GetEventObject().GetValue():
      QS.set_file_name(record_button=1)
    else:
      QS.set_file_name(record_button=0)
  def ChangeYscale(self, event):
    self.screen.ChangeYscale(self.sliderYs.GetValue())
    if self.screen == self.multi_rx_screen:
      if self.multi_rx_screen.rx_zero == self.waterfall:
        self.wfallScaleZ[self.lastBand] = (self.waterfall.y_scale, self.waterfall.y_zero)
      elif self.multi_rx_screen.rx_zero == self.graph:
        self.graphScaleZ[self.lastBand] = (self.graph.y_scale, self.graph.y_zero)
  def ChangeYzero(self, event):
    self.screen.ChangeYzero(self.sliderYz.GetValue())
    if self.screen == self.multi_rx_screen:
      if self.multi_rx_screen.rx_zero == self.waterfall:
        self.wfallScaleZ[self.lastBand] = (self.waterfall.y_scale, self.waterfall.y_zero)
      elif self.multi_rx_screen.rx_zero == self.graph:
        self.graphScaleZ[self.lastBand] = (self.graph.y_scale, self.graph.y_zero)
  def OnChangeZoom(self, event):
    x = self.sliderZo.GetValue()
    if x < 50:
      self.zoom = 1.0	# change back to not-zoomed mode
      self.zoom_deltaf = 0
      self.zooming = False
    else:
      a = 1000.0 * self.sample_rate / (self.sample_rate - 2500.0)
      self.zoom = 1.0 - x / a
      if not self.zooming:		# set deltaf when zoom mode starts
        center = self.multi_rx_screen.graph.filter_center
        freq = self.rxFreq + center
        self.zoom_deltaf = freq
        self.zooming = True
    zoom = self.zoom
    deltaf = self.zoom_deltaf
    self.graph.ChangeZoom(zoom, deltaf)
    self.waterfall.pane1.ChangeZoom(zoom, deltaf)
    self.waterfall.pane2.ChangeZoom(zoom, deltaf)
    self.waterfall.pane2.display.ChangeZoom(zoom, deltaf)
    self.screen.SetTxFreq(self.txFreq, self.rxFreq)
    self.station_screen.Refresh()
  def OnLevelVOX(self, event):
    self.levelVOX = event.GetEventObject().GetValue()
    if self.useVOX:
      QS.set_tx_audio(vox_level=self.levelVOX)
  def OnTimeVOX(self, event):
    self.timeVOX = event.GetEventObject().GetValue()
    QS.set_tx_audio(vox_time=self.timeVOX)
  def OnButtonVOX(self, event):
    self.useVOX = event.GetEventObject().GetValue()
    if self.useVOX:
      QS.set_tx_audio(vox_level=self.levelVOX)
    else:
      QS.set_tx_audio(vox_level=20)
      if self.pttButton.GetValue():
        self.pttButton.SetValue(0, True)
  def OnButtonPTT(self, event):
    if self.file_play_source == 12 and self.btnFilePlay.GetValue():	# playing CQ file
      self.btnFilePlay.SetValue(False, True)
    Hardware.OnButtonPTT(event)
  def SetPTT(self, value):
    if self.pttButton:
      self.pttButton.SetValue(value, False)
      event = wx.PyEvent()
      event.SetEventObject(self.pttButton)
      Hardware.OnButtonPTT(event)
  def OnTxAudioClip(self, event):
    v = event.GetEventObject().GetValue()
    if self.mode in ('USB', 'LSB'):
      self.txAudioClipUsb = v
    elif self.mode == 'AM':
      self.txAudioClipAm = v
    elif self.mode == 'FM':
      self.txAudioClipFm = v
    elif self.mode in ('FDV-U', 'FDV-L'):
      self.txAudioClipFdv = v
    else:
      return
    QS.set_tx_audio(mic_clip=v)
  def OnTxAudioPreemph(self, event):
    v = event.GetEventObject().GetValue()
    if self.mode in ('USB', 'LSB'):
      self.txAudioPreemphUsb = v
    elif self.mode == 'AM':
      self.txAudioPreemphAm = v
    elif self.mode == 'FM':
      self.txAudioPreemphFm = v
    elif self.mode in ('FDV-U', 'FDV-L'):
      self.txAudioPreemphFdv = v
    else:
      return
    QS.set_tx_audio(mic_preemphasis = v * 0.01)
  def SetTxAudio(self):
    if self.mode[0:3] in ('CWL', 'CWU', 'FDV', 'DGT'):
      self.CtrlTxAudioClip.slider.Enable(False)
      self.CtrlTxAudioPreemph.slider.Enable(False)
    else:
      self.CtrlTxAudioClip.slider.Enable(True)
      self.CtrlTxAudioPreemph.slider.Enable(True)
    if self.mode in ('USB', 'LSB'):
      clp = self.txAudioClipUsb
      pre = self.txAudioPreemphUsb
    elif self.mode == 'AM':
      clp = self.txAudioClipAm
      pre = self.txAudioPreemphAm
    elif self.mode == 'FM':
      clp = self.txAudioClipFm
      pre = self.txAudioPreemphFm
    else:
      clp = 0
      pre = 0
    QS.set_tx_audio(mic_clip=clp, mic_preemphasis=pre * 0.01)
    self.CtrlTxAudioClip.SetValue(clp)
    self.CtrlTxAudioPreemph.SetValue(pre)
  def OnBtnMute(self, event):
    btn = event.GetEventObject()
    if btn.GetValue():
      QS.set_volume(0)
    else:
      QS.set_volume(self.audio_volume)
  def OnMultirxPlayBoth(self, event):
    QS.set_multirx_play_method(0)
  def OnMultirxPlayLeft(self, event):
    QS.set_multirx_play_method(1)
  def OnMultirxPlayRight(self, event):
    QS.set_multirx_play_method(2)
  def OnBtnDecimation(self, event=None, rate=None):
    if event:
      i = event.GetSelection()
      rate = Hardware.VarDecimSet(i)
    self.vardecim_set = rate
    if rate != self.sample_rate:
      self.sample_rate = rate
      self.multi_rx_screen.ChangeSampleRate(rate)
      QS.change_rate(rate, 1)
      #print ('FFT size %d, FFT mult %d, average_count %d, rate %d, Refresh %.2f Hz' % (
      #  self.fft_size, self.fft_size / self.data_width, average_count, rate,
      #  float(rate) / self.fft_size / average_count))
      tune = self.txFreq
      vfo = self.VFO
      self.txFreq = self.VFO = -1		# demand change
      self.ChangeHwFrequency(tune, vfo, 'NewDecim')
  def ChangeVolume(self, event=None):
    # Caution: event can be None
    value = self.sliderVol.GetValue()
    self.volumeAudio = value
    # Simulate log taper pot
    B = 50.0		# This controls the gain at mid-volume
    x = (B ** (value/1000.0) - 1.0) / (B - 1.0)		# x is 0.0 to 1.0
    #print ("Vol %3d   %10.6f" % (value, x))
    self.audio_volume = x	# audio_volume is 0 to 1.000
    QS.set_volume(x)
  def ChangeSidetone(self, event=None):
    # Caution: event can be None
    value = self.sliderSto.GetValue()
    self.sidetone_volume = value
    # Simulate log taper pot
    B = 50.0		# This controls the gain at mid-volume
    x = (B ** (value/1000.0) - 1.0) / (B - 1.0)		# x is 0.0 to 1.0
    self.sidetone_0to1 = x
    QS.set_sidetone(value, x, self.ritFreq, conf.keyupDelay)
    if hasattr(Hardware, 'ChangeSidetone'):
      Hardware.ChangeSidetone(x)
  def OnRitScale(self, event=None):	# Called when the RIT slider is moved
    # Caution: event can be None
    value = self.ritScale.GetValue()
    self.ritButton.SetLabel("RIT %d" % value)
    self.ritButton.Refresh()
    if self.ritButton.GetValue():
      value = int(value)
      self.ritFreq = value
      self.graph.ritFreq = value
      self.waterfall.pane1.ritFreq = value
      self.waterfall.pane2.ritFreq = value
      QS.set_tune(self.rxFreq + self.ritFreq, self.txFreq)
      QS.set_sidetone(self.sidetone_volume, self.sidetone_0to1, self.ritFreq, conf.keyupDelay)
  def OnBtnSplit(self, event):	# Called when the Split check button is pressed
    self.split_rxtx = self.splitButton.GetValue()
    if self.split_rxtx:
      QS.set_split_rxtx(self.split_rxtx_play)
      self.rxFreq = self.oldRxFreq
      d = self.sample_rate * 49 // 100	# Move rxFreq on-screen
      if self.rxFreq < -d:
        self.rxFreq = -d
      elif self.rxFreq > d:
        self.rxFreq = d
    else:
      QS.set_split_rxtx(0)
      self.oldRxFreq = self.rxFreq
      self.rxFreq = self.txFreq
    self.screen.SetTxFreq(self.txFreq, self.rxFreq)
    QS.set_tune(self.rxFreq + self.ritFreq, self.txFreq)
  def OnMenuSplitPlay1(self, event):
    self.split_rxtx_play = 1
    if self.split_rxtx:
      QS.set_split_rxtx(1)
  def OnMenuSplitPlay2(self, event):
    self.split_rxtx_play = 2
    if self.split_rxtx:
      QS.set_split_rxtx(2)
  def OnMenuSplitPlay3(self, event):
    self.split_rxtx_play = 3
    if self.split_rxtx:
      QS.set_split_rxtx(3)
  def OnMenuSplitPlay4(self, event):
    self.split_rxtx_play = 4
    if self.split_rxtx:
      QS.set_split_rxtx(4)
  def OnMenuSplitLock(self, event):
    if self.split_locktx:
      self.split_locktx = False
      self.splitButton.SetLabel("Split")
    else:
      self.split_locktx = True
      self.splitButton.SetLabel("LkSplit")
    self.splitButton.Refresh()
  def OnMenuSplitRev(self, event):	# Called when the Split Reverse button is pressed
    if self.split_rxtx:
      rx = self.rxFreq
      self.rxFreq = self.txFreq
      self.ChangeHwFrequency(rx, self.VFO, 'FreqEntry')
  def OnMenuSplitCtlTx(self, event):
    self.split_hamlib_tx = True
  def OnMenuSplitCtlRx(self, event):
    self.split_hamlib_tx = False
  def OnBtnRit(self, event=None):	# Called when the RIT check button is pressed
    # Caution: event can be None
    if self.ritButton.GetValue():
      self.ritFreq = self.ritScale.GetValue()
    else:
      self.ritFreq = 0
    self.graph.ritFreq = self.ritFreq
    self.waterfall.pane1.ritFreq = self.ritFreq
    self.waterfall.pane2.ritFreq = self.ritFreq
    QS.set_tune(self.rxFreq + self.ritFreq, self.txFreq)
    #print("rxFreq: %d; ritFreq: %d; txFreq: %d" %(self.rxFreq, self.ritFreq, self.txFreq))
    QS.set_sidetone(self.sidetone_volume, self.sidetone_0to1, self.ritFreq, conf.keyupDelay)
    #print("sidetone_volume: %d; sidetone_0to1: %d; ritFreq: %d; keyupDelay: %d" %(self.sidetone_volume, self.sidetone_0to1, self.ritFreq, conf.keyupDelay))
  def SetRit(self, freq):
    if freq:
      self.ritButton.SetValue(1)
    else:
      self.ritButton.SetValue(0)
    self.ritScale.SetValue(freq)
    self.ritButton.SetLabel("RIT %d" % freq)
    self.ritButton.Refresh()
    self.OnBtnRit()
  def OnBtnFDX(self, event):
    btn = event.GetEventObject()
    if btn.GetValue():
      QS.set_fdx(1)
      if hasattr(Hardware, 'OnBtnFDX'):
        Hardware.OnBtnFDX(1)
    else:
      QS.set_fdx(0)
      if hasattr(Hardware, 'OnBtnFDX'):
        Hardware.OnBtnFDX(0)
  def OnImdSlider(self, event):
    value = event.GetEventObject().slider_value
    QS.set_imd_level(value)
  def OnBtnSpot(self, event):
    btn = event.GetEventObject()
    self.levelSpot = btn.slider_value
    if btn.GetValue():
      value = btn.slider_value
    else:
      value = -1
    QS.set_spot_level(value)
    Hardware.OnSpot(value)
    if conf.spot_button_keys_tx and self.pttButton:
      Hardware.OnButtonPTT(event)
  def OnBtnTmpRecord(self, event):
    btn = event.GetEventObject()
    if btn.GetValue():
      self.btnTmpPlay.Enable(0)
      QS.set_record_state(0)
    else:
      self.btnTmpPlay.Enable(1)
      QS.set_record_state(1)
  def OnBtnTmpPlay(self, event):
    btn = event.GetEventObject()
    if btn.GetValue():
      if QS.is_key_down() and conf.mic_sample_rate != conf.playback_rate:
        self.btnTmpPlay.SetValue(False, False)
      else:
        self.btnTmpRecord.Enable(0)
        QS.set_record_state(2)
        self.tmp_playing = True
    else:
      self.btnTmpRecord.Enable(1)
      QS.set_record_state(3)
      self.tmp_playing = False
  def OnBtnFilePlay(self, event):
    btn = event.GetEventObject()
    enable = btn.GetValue()
    if enable:
      self.file_play_state = 1	# Start playing a file
      if self.file_play_source == 10:	# Play speaker audio file
        QS.set_record_state(5)
      elif self.file_play_source == 11:	# Play sample file
        QS.set_record_state(6)
      elif self.file_play_source == 12:	# Play CQ file
        QS.set_record_state(5)
        self.SetPTT(True)
    else:
      self.file_play_state = 0	# Not playing a file
      QS.set_record_state(3)
      if self.file_play_source == 12:	# Play CQ file
        self.SetPTT(False)
  def TurnOffFilePlay(self):
    self.btnFilePlay.SetValue(False, False)
    self.file_play_state = 0	# Not playing a file
    QS.set_record_state(3)
  def OnBtnTest1(self, event):
    btn = event.GetEventObject()
    if btn.GetValue():
      QS.add_tone(10000)
    else:
      QS.add_tone(0)
  def OnBtnTest2(self, event):
    return
  def OnBtnColorDialog(self, event):
    btn = event.GetEventObject()
    dlg = wx.ColourDialog(self.main_frame)
    dlg.GetColourData().SetChooseFull(True)
    if dlg.ShowModal() == wx.ID_OK:
      data = dlg.GetColourData()
      print (data.GetColour().Get(False))
      btn.text_color = data.GetColour().Get(False)
      btn.Refresh()
    dlg.Destroy()
  def OnBtnColor(self, event):
    if not self.color_list:
      clist = wx.lib.colourdb.getColourInfoList()
      self.color_list = [(0, clist[0][0])]
      self.color_index = 0
      for i in range(1, len(clist)):
        if  self.color_list[-1][1].replace(' ', '') != clist[i][0].replace(' ', ''):
          #if 'BLUE' in clist[i][0]:
            self.color_list.append((i, clist[i][0]))
    btn = event.GetEventObject()
    if btn.shift:
      del self.color_list[self.color_index]
    else:
      self.color_index += btn.direction
    if self.color_index >= len(self.color_list):
      self.color_index = 0
    elif self.color_index < 0:
      self.color_index = len(self.color_list) -1
    color = self.color_list[self.color_index][1]
    print(self.color_index, color)
    #self.main_frame.SetBackgroundColour(color)
    #self.main_frame.Refresh()
    #self.screen.Refresh()
    #btn.SetBackgroundColour(color)
    btn.text_color = color
    btn.Refresh()
  def OnBtnAGC(self, event):
    btn = event.GetEventObject()
    self.levelOffAGC = btn.slider_value_off
    self.levelAGC = btn.slider_value_on
    value = btn.GetValue()
    if value:
      level = self.levelAGC
    else:
      level = self.levelOffAGC
    # Simulate log taper pot.  Volume is 0 to 1.
    x = (10.0 ** (float(level) * 0.003000434077) - 0.99999) / 1000.0
    QS.set_agc(x * conf.agc_max_gain)
  def OnBtnSquelch(self, event=None):
    btn = self.BtnSquelch
    value = btn.GetValue()
    if self.mode == 'FM':
      self.levelSquelch = btn.slider_value
      if value:
        QS.set_squelch(self.levelSquelch / 12.0 - 120.0)
      else:
        QS.set_squelch(-999.0)
    else:
      self.levelSquelchSSB = btn.slider_value
      if value:
        QS.set_ssb_squelch(1, self.levelSquelchSSB)
      else:
        QS.set_ssb_squelch(0, self.levelSquelchSSB)
  def OnBtnAutoNotch(self, event):
    if event.GetEventObject().GetValue():
      QS.set_auto_notch(1)
    else:
      QS.set_auto_notch(0)
  def OnBtnNB(self, event):
    index = event.GetEventObject().index
    QS.set_noise_blanker(index)
  def FreqEntry(self, event):
    freq = event.GetString()
    win = event.GetEventObject()
    win.Clear()
    if not freq:
      return
    try:
      freq = str2freq (freq)
    except ValueError:
      pass
    else:
      tune = freq % 10000
      vfo = freq - tune
      self.BandFromFreq(freq)
      self.ChangeHwFrequency(tune, vfo, 'FreqEntry')
  def ChangeHwFrequency(self, tune, vfo, source='', band='', event=None):
    """Change the VFO and tuning frequencies, and notify the hardware.

    tune:   the new tuning frequency in +- sample_rate/2;
    vfo:    the new vfo frequency in Hertz; this is the RF frequency at zero Hz audio
    source: a string indicating the source or widget requesting the change;
    band:   if source is "BtnBand", the band requested;
    event:  for a widget, the event (used to access control/shift key state).

    Try to update the hardware by calling Hardware.ChangeFrequency().
    The hardware will reply with the updated frequencies which may be different
    from those requested; use and display the returned tune and vfo.
    """
    if self.screen == self.bandscope_screen:
      freq = vfo + tune
      tune = freq % 10000
      vfo = freq - tune
    tune, vfo = Hardware.ChangeFrequency(vfo + tune, vfo, source, band, event)
    self.ChangeDisplayFrequency(tune - vfo, vfo)
  def ChangeDisplayFrequency(self, tune, vfo):
    'Change the frequency displayed by Quisk'
    change = 0
    if tune != self.txFreq:
      change = 1
      self.txFreq = tune
      if not self.split_rxtx:
        self.rxFreq = self.txFreq
      if self.screen == self.bandscope_screen:
        self.screen.SetFrequency(tune + vfo)
      else:
        self.screen.SetTxFreq(self.txFreq, self.rxFreq)
      QS.set_tune(self.rxFreq + self.ritFreq, self.txFreq)
    if vfo != self.VFO:
      change = 1
      self.VFO = vfo
      self.graph.SetVFO(vfo)
      self.waterfall.SetVFO(vfo)
      self.station_screen.Refresh()
      if self.w_phase:		# Phase adjustment screen can not change its VFO
        self.w_phase.Destroy()
        self.w_phase = None
      ampl, phase = self.GetAmplPhase(0)
      QS.set_ampl_phase(ampl, phase, 0)
      ampl, phase = self.GetAmplPhase(1)
      QS.set_ampl_phase(ampl, phase, 1)
    if change:
      self.freqDisplay.Display(self.txFreq + self.VFO)
      self.fldigi_new_freq = self.txFreq + self.VFO
    return change
  def ChangeRxTxFrequency(self, rx_freq=None, tx_freq=None):
    if not self.split_rxtx and not tx_freq:
      tx_freq = rx_freq
    if tx_freq:
      tune = tx_freq - self.VFO
      d = self.sample_rate * 45 // 100
      if -d <= tune <= d:	# Frequency is on-screen
        vfo = self.VFO
      else:					# Change the VFO
        vfo = (tx_freq // 5000) * 5000 - 5000
        tune = tx_freq - vfo
        self.BandFromFreq(tx_freq)
      self.ChangeHwFrequency(tune, vfo, 'FreqEntry')
    if rx_freq and self.split_rxtx:		# Frequency must be on-screen
      tune = rx_freq - self.VFO
      self.rxFreq = tune
      self.screen.SetTxFreq(self.txFreq, tune)
      QS.set_tune(tune + self.ritFreq, self.txFreq)
  def OnBtnMode(self, event, mode=None):
    if event is None:	# called by application
      self.modeButns.SetLabel(mode)
    else:		# called by button
      mode = self.modeButns.GetLabel()
    Hardware.ChangeMode(mode)
    self.mode = mode
    self.MakeFilterButtons(self.Mode2Filters(mode))
    QS.set_rx_mode(Mode2Index.get(mode, 3))
    #print("mode: %s; Index: %d" %(mode, Mode2Index.get(mode, 3)))
    if mode == 'CWL':
      self.SetRit(conf.cwTone)
    elif mode == 'CWU':
      self.SetRit(-conf.cwTone)
    else:
      self.SetRit(0)
    if mode in ('CWL', 'CWU'):
      self.SetFilterByMode('CW')
    elif mode in ('LSB', 'USB'):
      self.SetFilterByMode('SSB')
    elif mode == 'AM':
      self.SetFilterByMode('AM')
    elif mode == 'FM':
      self.SetFilterByMode('FM')
    elif mode[0:4] == 'DGT-':
      self.SetFilterByMode('DGT')
    elif mode[0:4] == 'FDV-':
      self.SetFilterByMode('FDV')
    elif mode == 'IMD':
      self.SetFilterByMode('IMD')
    elif mode == conf.add_extern_demod:
      self.SetFilterByMode(conf.add_extern_demod)
    self.sliderSquelch.DeleteSliderWindow()
    if mode == 'FM':
      self.sliderSquelch.SetSlider(self.levelSquelch)
    else:
      self.sliderSquelch.SetSlider(self.levelSquelchSSB)
    self.OnBtnSquelch()
    if mode not in ('FDV-L', 'FDV-U'):
      self.graph.SetDisplayMsg()
      self.waterfall.SetDisplayMsg()
    self.SetTxAudio()
  def MakeMemPopMenu(self):
    self.memory_menu.Destroy()
    self.memory_menu = wx.Menu()
    for data in self.memoryState:
      txt = FreqFormatter(data[0])
      item = self.memory_menu.Append(-1, txt)
      self.Bind(wx.EVT_MENU, self.OnPopupMemNext, item)
  def OnPopupMemNext(self, event):
    frq = self.memory_menu.GetLabel(event.GetId())
    frq = frq.replace(' ','')
    frq = int(frq)
    for freq, band, vfo, txfreq, mode in self.memoryState:
      if freq == frq:
        break
    else:
      return
    if band == self.lastBand:	# leave band unchanged
      self.OnBtnMode(None, mode)
      self.ChangeHwFrequency(txfreq, vfo, 'FreqEntry')
    else:		# change to new band
      self.bandState[band] = (vfo, txfreq, mode)
      self.bandBtnGroup.SetLabel(band, do_cmd=True)
  def OnBtnMemSave(self, event):
    frq = self.VFO + self.txFreq
    for i in range(len(self.memoryState)):
      data = self.memoryState[i]
      if data[0] == frq:
        self.memoryState[i] = (self.VFO + self.txFreq, self.lastBand, self.VFO, self.txFreq, self.mode)
        return
    self.memoryState.append((self.VFO + self.txFreq, self.lastBand, self.VFO, self.txFreq, self.mode))
    self.memoryState.sort()
    self.memNextButton.Enable(True)
    self.memDeleteButton.Enable(True)
    self.MakeMemPopMenu()
    self.station_screen.Refresh()
  def OnBtnMemNext(self, event):
    frq = self.VFO + self.txFreq
    for freq, band, vfo, txfreq, mode in self.memoryState:
      if freq > frq:
        break
    else:
      freq, band, vfo, txfreq, mode = self.memoryState[0]
    if band == self.lastBand:	# leave band unchanged
      self.OnBtnMode(None, mode)
      self.ChangeHwFrequency(txfreq, vfo, 'FreqEntry')
    else:		# change to new band
      self.bandState[band] = (vfo, txfreq, mode)
      self.bandBtnGroup.SetLabel(band, do_cmd=True)
  def OnBtnMemDelete(self, event):
    frq = self.VFO + self.txFreq
    for i in range(len(self.memoryState)):
      data = self.memoryState[i]
      if data[0] == frq:
        del self.memoryState[i]
        break
    self.memNextButton.Enable(bool(self.memoryState))
    self.memDeleteButton.Enable(bool(self.memoryState))
    self.MakeMemPopMenu()
    self.station_screen.Refresh()
  def OnRightClickMemory(self, event):
    event.Skip()
    pos = event.GetPosition()
    self.memNextButton.PopupMenu(self.memory_menu, pos)
  def OnBtnFavoritesShow(self, event):
    self.screenBtnGroup.SetLabel("Config", do_cmd=False)
    self.screen.Hide()
    self.config_screen.FinishPages()
    self.screen = self.config_screen
    self.config_screen.notebook.SetSelection(3)
    self.screen.Show()
    self.vertBox.Layout()    # This destroys the initialized sash position!
  def OnBtnFavoritesNew(self, event):
    self.config_screen.favorites.AddNewFavorite();
    self.OnBtnFavoritesShow(event)
  def OnBtnBand(self, event):
    band = self.lastBand	# former band in use
    try:
      f1, f2 = conf.BandEdge[band]
      if f1 <= self.VFO + self.txFreq <= f2:
        self.bandState[band] = (self.VFO, self.txFreq, self.mode)
    except KeyError:
      pass
    btn = event.GetEventObject()
    band = btn.GetLabel()	# new band
    self.lastBand = band
    try:
      vfo, tune, mode = self.bandState[band]
    except KeyError:
      vfo, tune, mode = (1000000, 0, 'LSB')
    if band == '60':
      if self.mode in ('CWL', 'CWU'):
        freq60 = []
        for f in conf.freq60:
          freq60.append(f + 1500)
      else:
        freq60 = conf.freq60
      freq = vfo + tune
      if btn.direction:
        vfo = self.VFO
        if 5100000 < vfo < 5600000:
          if btn.direction > 0:		# Move up
            for f in freq60:
              if f > vfo + self.txFreq:
                freq = f
                break
            else:
              freq = freq60[0]
          else:			# move down
            l = list(freq60)
            l.reverse()
            for f in l: 
              if f < vfo + self.txFreq:
                freq = f
                break
              else:
                freq = freq60[-1]
      half = self.sample_rate // 2 * self.graph_width // self.data_width
      while freq - vfo <= -half + 1000:
        vfo -= 10000
      while freq - vfo >= +half - 5000:
        vfo += 10000
      tune = freq - vfo
    elif band == 'Time':
      vfo, tune, mode = conf.bandTime[btn.index]
    self.OnBtnMode(None, mode)
    self.txFreq = self.VFO = -1		# demand change
    self.ChangeBand(band)
    self.ChangeHwFrequency(tune, vfo, 'BtnBand', band=band)
    if self.pttButton:
      if band in ('Time', 'Audio') or conf.tx_level.get(band, 127) == 0:
        self.pttButton.Enable(False)
      else:
        self.pttButton.Enable(True)
  def BandFromFreq(self, frequency):	# Change to a new band based on the frequency
    try:
      f1, f2 = conf.BandEdge[self.lastBand]
      if f1 <= frequency <= f2:
        return						# We are within the current band
    except KeyError:
      f1 = f2 = -1
    # Frequency is not within the current band.  Save the current band data.
    if f1 <= self.VFO + self.txFreq <= f2:
      self.bandState[self.lastBand] = (self.VFO, self.txFreq, self.mode)
    # Change to the correct band based on frequency.
    for band in conf.BandEdge:
      f1, f2 = conf.BandEdge[band]
      if f1 <= frequency <= f2:
        self.lastBand = band
        self.bandBtnGroup.SetLabel(band, do_cmd=False)
        try:
          vfo, tune, mode = self.bandState[band]
        except KeyError:
          vfo, tune, mode = (0, 0, 'LSB')
        self.OnBtnMode(None, mode)
        self.ChangeBand(band)
        break
  def ChangeBand(self, band):
    Hardware.ChangeBand(band)
    self.waterfall.SetPane2(self.wfallScaleZ.get(band, (conf.waterfall_y_scale, conf.waterfall_y_zero)))
    s, z = self.graphScaleZ.get(band, (conf.graph_y_scale, conf.graph_y_zero))
    self.graph.ChangeYscale(s)
    self.graph.ChangeYzero(z)
    if self.screen == self.multi_rx_screen and self.multi_rx_screen.rx_zero in (self.waterfall, self.graph):
      self.sliderYs.SetValue(self.screen.y_scale)
      self.sliderYz.SetValue(self.screen.y_zero)
  def OnBtnUpDnBandDelta(self, event, is_band_down):
    sample_rate = int(self.sample_rate * self.zoom)
    oldvfo = self.VFO
    btn = event.GetEventObject()
    if btn.direction > 0:		# left button was used, move a bit
      d = int(sample_rate // 9)
    else:						# right button was used, move to edge
      d = int(sample_rate * 45 // 100)
    if is_band_down:
      d = -d
    vfo = self.VFO + d
    if sample_rate > 40000:
      vfo = (vfo + 5000) // 10000 * 10000	# round to even number
      delta = 10000
    elif sample_rate > 5000:
      vfo = (vfo + 500) // 1000 * 1000
      delta = 1000
    else:
      vfo = (vfo + 50) // 100 * 100
      delta = 100
    if oldvfo == vfo:
      if is_band_down:
        d = -delta
      else:
        d = delta
    else:
      d = vfo - oldvfo
    self.VFO += d
    self.txFreq -= d
    self.rxFreq -= d
    # Set the display but do not change the hardware
    self.graph.SetVFO(self.VFO)
    self.waterfall.SetVFO(self.VFO)
    self.station_screen.Refresh()
    self.screen.SetTxFreq(self.txFreq, self.rxFreq)
    self.freqDisplay.Display(self.txFreq + self.VFO)
  def OnBtnDownBand(self, event):
    self.band_up_down = 1
    self.OnBtnUpDnBandDelta(event, True)
  def OnBtnUpBand(self, event):
    self.band_up_down = 1
    self.OnBtnUpDnBandDelta(event, False)
  def OnBtnUpDnBandDone(self, event):
    self.band_up_down = 0
    tune = self.txFreq
    vfo = self.VFO
    self.txFreq = self.VFO = 0		# Force an update
    self.ChangeHwFrequency(tune, vfo, 'BtnUpDown')
  def GetAmplPhase(self, is_tx):
    if "panadapter" in conf.bandAmplPhase:
      band = "panadapter"
    else:
      band = self.lastBand
    try:
      if is_tx:
        lst = self.bandAmplPhase[band]["tx"]
      else:
        lst = self.bandAmplPhase[band]["rx"]
    except KeyError:
      return (0.0, 0.0)
    length = len(lst)
    if length == 0:
      return (0.0, 0.0)
    elif length == 1:
      return lst[0][2], lst[0][3]
    elif self.VFO < lst[0][0]:		# before first data point
      i1 = 0
      i2 = 1
    elif lst[length - 1][0] < self.VFO:	# after last data point
      i1 = length - 2
      i2 = length - 1
    else:
      # Binary search for the bracket VFO
      i1 = 0
      i2 = length
      index = (i1 + i2) // 2
      for i in range(length):
        diff = lst[index][0] - self.VFO
        if diff < 0:
          i1 = index
        elif diff > 0:
          i2 = index
        else:		# equal VFO's
          return lst[index][2], lst[index][3]
        if i2 - i1 <= 1:
          break
        index = (i1 + i2) // 2
    d1 = self.VFO - lst[i1][0]		# linear interpolation
    d2 = lst[i2][0] - self.VFO
    dx = d1 + d2
    ampl = (d1 * lst[i2][2] + d2 * lst[i1][2]) / dx
    phas = (d1 * lst[i2][3] + d2 * lst[i1][3]) / dx
    return ampl, phas
  def PostStartup(self):	# called once after sound attempts to start
    self.config_screen.OnGraphData(None)	# update config in case sound is not running
  def FldigiPoll(self):		# Keep Quisk and Fldigi frequencies equal; control Fldigi PTT from Quisk
    if self.fldigi_server is None:
      return
    if self.fldigi_new_freq:	# Our frequency changed; send to fldigi
      try:
        self.fldigi_server.main.set_frequency(float(self.fldigi_new_freq))
      except:
        # traceback.print_exc()
        pass
      self.fldigi_new_freq = None
      self.fldigi_timer = time.time()
      return
    try:
      freq = self.fldigi_server.main.get_frequency()
    except:
      # traceback.print_exc()
      return
    else:
      freq = int(freq + 0.5)
    try:
      rxtx = self.fldigi_server.main.get_trx_status()	# returns rx, tx, tune
    except:
      return
    if time.time() - self.fldigi_timer < 0.3:		# If timer is small, change originated in Quisk
      self.fldigi_rxtx = rxtx
      self.fldigi_freq = freq
      return
    if self.fldigi_freq != freq:
      self.fldigi_freq = freq
      #print "Change freq", freq
      self.ChangeRxTxFrequency(None, freq)
      self.fldigi_new_freq = None
    if self.fldigi_rxtx != rxtx:
      self.fldigi_rxtx = rxtx
      #print 'Fldigi changed to', rxtx
      if self.pttButton:
        if rxtx == 'rx':
          self.pttButton.SetValue(0, True)
        else:
          self.pttButton.SetValue(1, True)
        self.fldigi_timer = time.time()
    else:
      if QS.is_key_down():
        if rxtx == 'rx':
          self.fldigi_server.main.tx()
          self.fldigi_timer = time.time()
      else:	# key is up
        if rxtx != 'rx':
          self.fldigi_server.main.rx()
          self.fldigi_timer = time.time()
  def HamlibPoll(self):		# Poll for Hamlib commands
    if self.hamlib_socket:
      try:		# Poll for new client connections.
        conn, address = self.hamlib_socket.accept()
      except socket.error:
        pass
      else:
        # print 'Connection from', address
        self.hamlib_clients.append(HamlibHandlerRig2(self, conn, address))
      for client in self.hamlib_clients:	# Service existing clients
        if not client.Process():		# False return indicates a closed connection; remove the handler for this client
          self.hamlib_clients.remove(client)
          # print 'Remove', client.address
          break
  def OnHotKey(self, event):
    if self.hot_key_ptt_state == 0:	# PTT off, waiting for key press
      self.TurnOffFilePlay()
      self.hot_key_ptt_state = 1
    elif self.hot_key_ptt_state == 1 and conf.hot_key_ptt_toggle:	# second key press for toggle mode
      self.hot_key_ptt_state = 2
  def OnReadSound(self):	# called at frequent intervals
    if self.hamlib_com1_handler:
      self.hamlib_com1_handler.Process()
    if self.hamlib_com2_handler:
      self.hamlib_com2_handler.Process()
    if conf.do_repeater_offset:
      hold = QS.tx_hold_state(-1)
      if hold == 2:	# Tx is being held for an FM repeater TX frequency shift
        rdict = self.config_screen.favorites.RepeaterDict
        freq = self.txFreq + self.VFO
        freq = ((freq + 500) // 1000) * 1000
        if freq in rdict:
          offset, tone = rdict[freq]
          QS.set_ctcss(tone)
          Hardware.RepeaterOffset(offset)
          for i in range(100):
            time.sleep(0.010)
            if Hardware.RepeaterOffset():
              break
        QS.tx_hold_state(3)
      elif hold == 4:	# No delay necessary on key up
        Hardware.RepeaterOffset(0)
        QS.set_ctcss(0)
        QS.tx_hold_state(1)
    if self.pttButton:	# Manage the PTT button using VOX, hardware switch, hot keys and WAV file play
      ptt = None
      if self.hardware_ptt_key_state == 0 and QS.get_hardware_ptt() == 1:	# Wait for PTT switch ON
        ptt = True
        self.hardware_ptt_key_state = 1
      elif self.hardware_ptt_key_state == 1:	# Wait for PTT switch OFF
        if QS.get_hardware_ptt() == 1:
          ptt = True
        else:
          ptt = False
          self.hardware_ptt_key_state = 0
      if self.useVOX:
        if self.file_play_state == 0:
          if QS.is_vox():
            ptt = True
          else:
            ptt = False
        elif self.file_play_state == 2 and QS.is_vox():			# VOX tripped between file play repeats
          self.TurnOffFilePlay()
          ptt = True
      if self.file_play_state == 2 and QS.is_key_down():			# hardware key between file play repeats
        if time.time() > self.file_play_timer - self.file_play_repeat + 0.25:	# pause to allow key state to change
          self.TurnOffFilePlay()
          ptt = False
      if conf.hot_key_ptt1 and conf.hot_key_ptt_if_hidden:	# Hot key PTT operates even if Quisk is hidden
        if wx.GetKeyState(conf.hot_key_ptt1):
          ptt2 = conf.hot_key_ptt2
          if ptt2 is None or ptt2 == wx.ACCEL_NORMAL:
            hot_key = True
          elif ptt2 == wx.ACCEL_SHIFT:
            hot_key = wx.GetKeyState(wx.WXK_SHIFT)
          elif ptt2 == wx.ACCEL_CTRL:
            hot_key = wx.GetKeyState(wx.WXK_CONTROL)
          elif ptt2 == wx.ACCEL_ALT:
            hot_key = wx.GetKeyState(wx.WXK_ALT)
          elif ptt2 == wx.ACCEL_SHIFT | wx.ACCEL_CTRL:
            hot_key = wx.GetKeyState(wx.WXK_SHIFT) and wx.GetKeyState(wx.WXK_CONTROL)
          else:
            hot_key = True
        else:
          hot_key = False
        if conf.hot_key_ptt_toggle:
          if hot_key:
            if self.hot_key_ptt_stateH == 0:	# PTT off, waiting for first key press
              self.TurnOffFilePlay()
              ptt = True
              self.hot_key_ptt_stateH = 1
            elif self.hot_key_ptt_stateH == 2:	# Waiting for second press
              ptt = False
              self.hot_key_ptt_stateH = 3
          elif self.hot_key_ptt_stateH == 1:	# Waiting for first key release
            self.hot_key_ptt_stateH = 2
          elif self.hot_key_ptt_stateH == 3:	# Waiting for second release
            self.hot_key_ptt_stateH = 0
        else:
          if hot_key:
            ptt = True
            if self.hot_key_ptt_stateH == 0:
              self.TurnOffFilePlay()
              self.hot_key_ptt_stateH = 3
          elif self.hot_key_ptt_stateH == 3:
            if not self.useVOX:
              ptt = False
            self.hot_key_ptt_stateH = 0
      if self.hot_key_ptt_state != 0:		# Hot key PTT only operates if Quisk is on top
        if conf.hot_key_ptt_toggle:
          if self.hot_key_ptt_state == 1:	# PTT turned on, waiting for key release
            ptt = True
          elif self.hot_key_ptt_state == 2:	# second key press for toggle mode
            ptt = False
            self.hot_key_ptt_state = 0
        else:
          if wx.GetKeyState(conf.hot_key_ptt1):
            ptt = True
          else:
            self.hot_key_ptt_state = 0
            if not self.useVOX:
              ptt = False
      if ptt is True and not self.pttButton.GetValue():
        self.SetPTT(True)
      elif ptt is False and self.pttButton.GetValue():
        self.SetPTT(False)
    self.timer = time.time()
    if conf.use_rx_udp == 10:		# Hermes UDP protocol
      data = QS.get_graph(2, 1.0, 0)
      if data and self.screen == self.bandscope_screen:
        self.screen.OnGraphData(data)
    if self.screen == self.scope:
      data = QS.get_graph(0, 1.0, 0)	# get raw data
      if data:
        self.scope.OnGraphData(data)			# Send message to draw new data
        return 1		# we got new graph/scope data
    elif self.screen == self.audio_fft_screen:
      data = QS.get_graph(1, self.zoom, float(self.zoom_deltaf))	# get FFT data and discard
      audio_data = QS.get_audio_graph()		# Display the audio FFT
      if audio_data:
        self.screen.OnGraphData(audio_data)
    else:
      data = QS.get_graph(1, self.zoom, float(self.zoom_deltaf))	# get FFT data
      if data:
        #T('')
        if self.screen == self.bandscope_screen:
          d = QS.get_hermes_adc()
          if d < 1:
            d = 1.0
          self.smeter.SetLabel(" ADC %.0f%% %.0fdB" % (d / 20.48, 20 * math.log10(d / 2048)))
        elif self.smeter_usage == "smeter":		# update the S-meter
          if self.mode in ('FDV-U', 'FDV-L'):
            self.NewDVmeter()
          else:
            self.NewSmeter()
        elif self.smeter_usage == "freq":
          self.MeasureFrequency()	# display measured frequency
        else:
          self.MeasureAudioVoltage()		# display audio voltage
        if self.screen == self.config_screen:
          pass
        elif self.screen == self.bandscope_screen:
          pass
        else:
          self.screen.OnGraphData(data)			# Send message to draw new data
        #T('graph data')
        #application.Yield()
        #T('Yield')
        return 1		# We got new graph/scope data
    data, index = QS.get_multirx_graph()	# get FFT data for sub-receivers
    if data:
      self.multi_rx_screen.OnGraphData(data, index)
    if QS.get_overrange():
      self.clip_time0 = self.timer
      self.freqDisplay.Clip(1)
    if self.clip_time0:
      if self.timer - self.clip_time0 > 1.0:
        self.clip_time0 = 0
        self.freqDisplay.Clip(0)
    if self.timer - self.heart_time0 > 0.10:		# call hardware to perform background tasks
      self.heart_time0 = self.timer
      if self.screen == self.config_screen:
        self.screen.OnGraphData()			# Send message to draw new data
      Hardware.HeartBeat()
      if self.add_version and Hardware.GetFirmwareVersion() is not None:
        self.add_version = False
        self.config_text = "%s, firmware version 1.%d" % (self.config_text, Hardware.GetFirmwareVersion())
        self.main_frame.SetConfigText(self.config_text)
      if not self.band_up_down:
        # Poll the hardware for changed frequency.  This is used for hardware
        # that can change its frequency independently of Quisk; eg. K3.
        tune, vfo = Hardware.ReturnFrequency()
        if tune is not None and vfo is not None:
          self.BandFromFreq(tune)
          self.ChangeDisplayFrequency(tune - vfo, vfo)
        self.FldigiPoll()
        self.HamlibPoll()
      #if self.timer - self.fewsec_time0 > 3.0:
      #  self.fewsec_time0 = self.timer
      #  print ('fewswc')
      if self.timer - self.save_time0 > 20.0:
        self.save_time0 = self.timer
        if self.CheckState():
          self.SaveState()
        self.local_conf.SaveState()
      if self.tmp_playing and QS.set_record_state(-1):	# poll to see if playback is finished
        self.btnTmpPlay.SetValue(False, True)
      if self.file_play_state == 0:
        pass
      elif self.file_play_state == 1:
        if QS.set_record_state(-1):		# poll to see if playback is finished
          if  self.file_play_source == 12 and self.file_play_repeat:	# repeat the CW message
            self.file_play_state = 2	# Waiting for the timer to expire, and start another playback
            self.file_play_timer = self.timer + self.file_play_repeat
            self.SetPTT(False)
          else:
            self.btnFilePlay.SetValue(False, True)
      elif self.file_play_state == 2:
        if self.timer >= self.file_play_timer:
          QS.set_record_state(5)		# Start another playback
          self.file_play_state = 1
          self.SetPTT(True)

def main():
  """If quisk is installed as a package, you can run it with quisk.main()."""
  if application is None:
    App()
    application.startup_quisk = False
    application.MainLoop()
  while application.startup_quisk:
    time.sleep(1.0)
    App()
    application.startup_quisk = False
    application.MainLoop()

if __name__ == '__main__':
  main()

