# These are the configuration parameters for receiving the
# 10.7 MHz IF output of the AOR AR8600 receiver with my
# transceiver.  This results in a 100 kHz to 3 GHz
# wide range receiver with pan adapter.
#
# Due to noise starting at 11.18 MHz when tuned to 449.0 MHz, we tune to 10.5 MHz center.
#
# Note:  The AR8600 IF output in WFM mode seems to tune in 10kHz increments
#        no matter what the step size, even though the display reads a
#        different frequency.

# The AR8600 inverts the spectrum of these bands: 10, 2, 220, 440, 900
# The AR8600 does not invert these bands: 1240
# The change from inverted to non-inverted is about 1040 MHz.

# Please do not change this sample file.
# Instead copy it to your own .quisk_conf.py and make changes there.
# See quisk_conf_defaults.py for more information.

import time, traceback, os
import _quisk as QS
import serial			# From the pyserial package

from n2adr.quisk_conf import *
from n2adr import scanner_widgets as quisk_widgets

settings_file_path = "../quisk_settings.json"

bandLabels = [ ('60',) * 5, '40', '20',
	'15', '12', '10', '2', '220', '440', '900', '1240', ('Time',) * len(bandTime)]

# Define the Hardware class in this config file instead of a separate file.

from hiqsdr.quisk_hardware import Hardware as BaseHardware

class Hardware(BaseHardware):
  def __init__(self, app, conf):
    BaseHardware.__init__(self, app, conf)
    self.ar8600_frequency = 0	# current AR8600 tuning  frequency
    self.hware_frequency = 0	# current hardware VFO frequency
    self.vfo_frequency = 0		# current Quisk VFO frequency
    self.invert = 1				# The frequency spectrum is backwards
    self.serial = None			# the open serial port
    self.timer = 0.02			# time between AR8600 commands in seconds
    self.time0 = 0				# time of last AR8600 command
    self.serial_out = []		# send commands slowly
    self.offset = 10700000		# frequency offset from AR8600 tuning freq to IF output
    self.tx_freq = 0			# current frequency
    conf.BandEdge['220'] = (222000000, 225000000)
    conf.BandEdge['440'] = (420000000, 450000000)
    conf.BandEdge['900'] = (902000000, 928000000)
    conf.BandEdge['1240'] = (1240000000, 1300000000)
    rpt_file = os.path.normpath(os.path.join(os.getcwd(), '..'))
    rpt_file = os.path.join(rpt_file, 'MetroCor.txt')
    fp = open(rpt_file, 'r')
    self.repeaters = {}
    for line in fp:
      line = line.strip()
      if line and line[0] != '#':
        line = line.split('\t')
        fout = int(float(line[0]) * 1000000 + 0.1)
        text = "%s  %s, %s" % (line[2], line[3], line[5])
        if fout in self.repeaters:
          self.repeaters[fout] = "%s ; %s" % (self.repeaters[fout], text)
        else:
          self.repeaters[fout] = text
    fp.close()
    rpt_file = os.path.normpath(os.path.join(os.getcwd(), '..'))
    rpt_file = os.path.join(rpt_file, 'ARCC.csv')
    fp = open(rpt_file, 'r')
    for line in fp:
      line = line.strip()
      if line and line[0] != '#':
        line = line.split(',')
        fout = float(line[3])
        if fout >= 2000.0:
          continue
        fout = int(fout * 1000000 + 0.1)
        text = "%s  %s, %s" % (line[5], line[2], line[0])
        if fout in self.repeaters:
          self.repeaters[fout] = "%s ; %s" % (self.repeaters[fout], text)
        else:
          self.repeaters[fout] = text
    fp.close()
    rpt_file = os.path.normpath(os.path.join(os.getcwd(), '..'))
    rpt_file = os.path.join(rpt_file, 'Repeaters.csv')
    fp = open(rpt_file, 'r')
    for line in fp:
      line = line.strip()
      if line and line[0] != '#':
        line = line.split(',')
        fout = float(line[3])
        if fout >= 2000.0:
          continue
        fout = int(fout * 1000000 + 0.1)
        if line[0]:
          text = "%s  %s, %s" % (line[5], line[2], line[0])
        else:
          text = line[5]
        if fout in self.repeaters:
          self.repeaters[fout] = "%s ; %s" % (self.repeaters[fout], text)
        else:
          self.repeaters[fout] = text
    fp.close()
    for freq, text in self.repeaters.items():
      if len(text) > 80:
        t =''
        stations = text.split(';')
        for s in stations:
          s = s.strip()
          t = t + s.split()[0] + ' ' + s.split(',')[1] + '; '
        self.repeaters[freq] = t
    self.rpt_freq_list = self.repeaters.keys()
    self.rpt_freq_list.sort()
  def OpenPort(self):
    if sys.platform == "win32":
      tty_list = ("COM7", "COM8")
    else:
      tty_list = ("/dev/ttyUSB0", "/dev/ttyUSB1", "/dev/ttyUSB2")
    for tty_name in tty_list:
      try:
        port = serial.Serial(port=tty_name, baudrate=9600,
          stopbits=serial.STOPBITS_TWO, xonxoff=1, timeout=0)
      except:
        #traceback.print_exc()
        pass
      else:
        time.sleep(0.1)
        for i in range(3):
          port.write('VR\r')
          time.sleep(0.1)
          chars = port.read(1024)
          if "VR0101" in chars:
            self.serial = port
            port.write('MD0\r')		# set WFM mode so the IF output is available
            break
        if self.serial:
          break
        else:
          port.close()
  def open(self):
    self.OpenPort()
    QS.invert_spectrum(self.invert)
    t = BaseHardware.open(self)		# save the message
    return t
  def close(self):
    BaseHardware.close(self)
    if self.serial:
      self.serial.write('EX\r')
      time.sleep(1)			# wait for output to drain, but don't block
      self.serial.close()
      self.serial = None
  def ChangeFrequency(self, tx_freq, vfo_freq, source='', band='', event=None):
    self.tx_freq = tx_freq
    try:
      rpt = self.repeaters[tx_freq]
    except KeyError:
      self.application.bottom_widgets.UpdateText('')
    else:
      self.application.bottom_widgets.UpdateText(rpt)
    if vfo_freq != self.vfo_frequency and vfo_freq >= 10000:
      self.vfo_frequency = vfo_freq
      # Calculate new AR8600 and hardware frequencies
      ar8600 = (vfo_freq + 50000) / 100000 * 100000 - 200000
      if self.ar8600_frequency != ar8600:
        self.ar8600_frequency = ar8600
        self.SendAR8600('RF%010d\r' % ar8600)
        if ar8600 < 1040000000:
          self.invert = 1
        else:
          self.invert = 0
        QS.invert_spectrum(self.invert)
      if self.invert:
        hware = self.offset - vfo_freq + self.ar8600_frequency
      else:
        hware = self.offset + vfo_freq - self.ar8600_frequency
      if self.hware_frequency != hware:
        self.hware_frequency = hware
        BaseHardware.ChangeFrequency(self, 0, hware)
      #print 'AR8600 Hware', self.ar8600_frequency, self.hware_frequency
    return tx_freq, vfo_freq
  def SendAR8600(self, msg):	# Send commands to the AR8600, but not too fast
    if self.serial:
      if time.time() - self.time0 > self.timer:
        self.serial.write(msg)			# send message now
        self.time0 = time.time()
      else:
        self.serial_out.append(msg)		# send message later
  def HeartBeat(self):	# Called at about 10 Hz by the main
    BaseHardware.HeartBeat(self)
    if self.serial:
      chars = self.serial.read(1024)
      #if chars:
      #  print chars
      if self.serial_out and time.time() - self.time0 > self.timer:
        self.serial.write(self.serial_out[0])
        self.time0 = time.time()
        del self.serial_out[0]
