# Please do not change this hardware control module for Quisk.  Instead copy
# it to your own quisk_hardware.py and make changes there.
# See quisk_hardware_model.py for documentation.
#
# This hardware module sends the IF output of an AOR AR8600
# to the input of an SDR-IQ by RfSpace
#
# Note:  The AR8600 IF output in WFM mode seems to tune in 10kHz increments
#        no matter what the step size, even though the display reads a
#        different frequency.

import time
import _quisk as QS
from sdriqpkg import sdriq
import serial			# From the pyserial package

# Use the SDR-IQ hardware as the base class
from sdriqpkg import quisk_hardware as SdriqHardware
BaseHardware = SdriqHardware.Hardware

class Hardware(BaseHardware):
  def __init__(self, app, conf):
    BaseHardware.__init__(self, app, conf)
    self.vfo_frequency = 0		# current vfo frequency
    self.tty_name = '/dev/ttyUSB0'		# serial port name for AR8600
    self.serial = None			# the open serial port
    self.timer = 0.02			# time between AR8600 commands in seconds
    self.time0 = 0				# time of last AR8600 command
    self.serial_out = []		# send commands slowly
  def open(self):
    self.serial = serial.Serial(port=self.tty_name, baudrate=9600,
          stopbits=serial.STOPBITS_TWO, xonxoff=1, timeout=0)
    self.SendAR8600('MD0\r')		# set WFM mode so the IF output is available
    # The AR8600 inverts the spectrum of the 2 meter and 70 cm bands.
    # Other bands may not be inverted, so we may need to test the frequency.
    # But this is not currently implemented.
    QS.invert_spectrum(1)
    t = BaseHardware.open(self)		# save the message
    sdriq.freq_sdriq(10700000)
    return t
  def close(self):
    BaseHardware.close(self)
    if self.serial:
      self.serial.write('EX\r')
      time.sleep(1)			# wait for output to drain, but don't block
      self.serial.close()
      self.serial = None
  def ChangeFrequency(self, rx_freq, vfo_freq, source='', band='', event=None):
    vfo_freq = (vfo_freq + 5000) / 10000 * 10000		# round frequency
    if vfo_freq != self.vfo_frequency and vfo_freq >= 100000:
      self.vfo_frequency = vfo_freq
      self.SendAR8600('RF%010d\r' % vfo_freq)
    return rx_freq, vfo_freq
  def ChangeBand(self, band):	# Defeat base class method
    return
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
