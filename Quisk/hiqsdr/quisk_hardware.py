# This is a sample hardware file for UDP control.  Use this file for my 2010 transceiver
# described in QEX and for the improved version HiQSDR.  To turn on the extended
# features in HiQSDR, update your FPGA firmware to version 1.1 or later and use use_rx_udp = 2.

from __future__ import print_function

import struct, socket, math, traceback
import _quisk as QS

from quisk_hardware_model import Hardware as BaseHardware

DEBUG = 0

class Hardware(BaseHardware):
  def __init__(self, app, conf):
    BaseHardware.__init__(self, app, conf)
    self.got_udp_status = ''		# status from UDP receiver
	# want_udp_status is a 14-byte string with numbers in little-endian order:
	#	[0:2]		'St'
	#	[2:6]		Rx tune phase
	#	[6:10]		Tx tune phase
	#	[10]		Tx output level 0 to 255
	#	[11]		Tx control bits:
	#		0x01	Enable CW transmit
	#		0x02	Enable all other transmit
	#		0x04	Use the HiQSDR extended IO pins not present in the 2010 QEX ver 1.0
	#		0x08	The key is down (software key)
	#		bits 5 and 4: Transmit sample rate
	#			0b00 48k
	#			0b01 192k
	#			0b10 480k
	#			0b11 8k
	#		0x40	odyssey: Spot button is in use
	#		0x80	odyssey: Mic Boost 20dB
	#	[12]	Rx control bits
	#		bits 5 through 0
	#			Second stage decimation less one, 1-39, six bits
	#		bits 7, 6
	#		0b00	Prescaler 8, 3-byte samples I and Q; 1440 / 6 = 240 samples per UDP packet
	#		0b01	Prescaler 2, 2-byte samples
	#		0b10	Prescaler 40, 3-byte samples
	#		0b11	Prescaler 2, 1-byte samples
	#	[13]	zero or firmware version number
	# The above is used for firmware  version 1.0.
	# Version 1.1 adds eight more bytes for the HiQSDR conntrol ports:
	#	[14]	X1 connector:  Preselect pins 69, 68, 65, 64; Preamp pin 63, Tx LED pin 57
	#	[15]	Attenuator pins 84, 83, 82, 81, 80
	#	[16]	More bits: AntSwitch pin 41 is 0x01
	#	[17:22] The remaining five bytes are sent as zero.
	# Version 1.2 uses the same format as 1.1, but adds the "Qs" command (see below).
	# Version 1.3 adds features needed by the new quisk_vna.py program:
	#	[17]	The sidetone volume 0 to 255
	#	[18:20]	This is vna_count, the number of VNA data points; or zero for normal operation
	#	[20]	The CW delay as specified in the config file
	#	[21]	Control bits:
	#		0x01	Switch on tx mirror on rx for adaptive predistortion
	#	[22:24]	Noise blanker level

# The "Qs" command is a two-byte UDP packet sent to the control port.  It returns the hardware status
# as the above string, except that the string starts with "Qs" instead of "St".  Do not send the "Qs" command
# from Quisk, as it interferes with the "St" command.  The "Qs" command is meant to be used from an
# external program, such as HamLib or a logging program.

# When vna_count != 0, we are in VNA mode.  The start frequency is rx_phase, and for each point tx_phase is added
# to advance the frequency.  A zero sample is added to mark the blocks.  The samples are I and Q averaged at DC.

    self.rx_phase = 0
    self.tx_phase = 0
    self.tx_level = 0
    self.tx_control = 0
    self.rx_control = 0
    QS.set_sample_bytes(3)
    self.vna_count = 0	# VNA scan count; MUST be zero for non-VNA operation
    self.cw_delay = conf.cw_delay
    self.index = 0
    self.mode = None
    self.usingSpot = False
    self.band = None
    self.rf_gain = 0
    self.sidetone_volume = 0		# sidetone volume 0 to 255
    self.repeater_freq = None		# original repeater output frequency
    self.HiQSDR_Connector_X1 = 0
    self.HiQSDR_Attenuator = 0
    self.HiQSDR_Bits = 0
    try:
      if conf.radio_sound_mic_boost:
        self.tx_control = 0x80
    except:
      pass
    if conf.use_rx_udp == 2:	# Set to 2 for the HiQSDR
      self.rf_gain_labels = ('RF 0 dB', 'RF +10', 'RF -10', 'RF -20', 'RF -30')
      self.antenna_labels = ('Ant 1', 'Ant 2')
    self.firmware_version = None	# firmware version is initially unknown
    self.rx_udp_socket = None
    self.vfo_frequency = 0		# current vfo frequency
    self.tx_frequency = 0
    self.decimations = []		# supported decimation rates
    for dec in (40, 20, 10, 8, 5, 4, 2):
      self.decimations.append(dec * 64)
    self.decimations.append(80)
    self.decimations.append(64)
    if self.conf.fft_size_multiplier == 0:
      self.conf.fft_size_multiplier = 6		# Set size needed by VarDecim
  def open(self):
    # Create the proper broadcast address for rx_udp_ip.
    nm = self.conf.rx_udp_ip_netmask.split('.')
    ip = self.conf.rx_udp_ip.split('.')
    nm = map(int, nm)
    ip = map(int, ip)
    bc = ''
    for i in range(4):
      x = (ip[i] | ~ nm[i]) & 0xFF
      bc = bc + str(x) + '.'
    self.broadcast_addr = bc[:-1]
    # This socket is used for the Simple Network Discovery Protocol by AE4JY
    self.socket_sndp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    self.socket_sndp.setblocking(0)
    self.socket_sndp.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    self.sndp_request = chr(56) + chr(0) + chr(0x5A) + chr(0xA5) + chr(0) * 52
    self.sndp_active = self.conf.sndp_active
    # conf.rx_udp_port is used for returning ADC samples
    # conf.rx_udp_port + 1 is used for control
    self.rx_udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    self.rx_udp_socket.setblocking(0)
    self.rx_udp_socket.connect((self.conf.rx_udp_ip, self.conf.rx_udp_port + 1))
    return QS.open_rx_udp(self.conf.rx_udp_ip, self.conf.rx_udp_port)
  def close(self):
    if self.rx_udp_socket:
      self.rx_udp_socket.close()
      self.rx_udp_socket = None
  def ReturnFrequency(self):	# Return the current tuning and VFO frequency
    return None, None		# frequencies have not changed
  def ReturnVfoFloat(self, freq=None):	# Return the accurate VFO as a float
    if freq is None:
      rx_phase = self.rx_phase
    else:
      rx_phase = int(float(freq) / self.conf.rx_udp_clock * 2.0**32 + 0.5) & 0xFFFFFFFF
    return float(rx_phase) * self.conf.rx_udp_clock / 2.0**32
  def ChangeFrequency(self, tx_freq, vfo_freq, source='', band='', event=None):
    if vfo_freq != self.vfo_frequency:
      self.vfo_frequency = vfo_freq
      self.rx_phase = int(float(vfo_freq - self.transverter_offset) / self.conf.rx_udp_clock * 2.0**32 + 0.5) & 0xFFFFFFFF
    if tx_freq and tx_freq > 0:
      self.tx_frequency = tx_freq
      self.tx_phase = int(float(tx_freq - self.transverter_offset) / self.conf.rx_udp_clock * 2.0**32 + 0.5) & 0xFFFFFFFF
    self.NewUdpStatus()
    return tx_freq, vfo_freq
  def RepeaterOffset(self, offset=None):	# Change frequency for repeater offset during Tx
    if offset is None:		# Return True if frequency change is complete
      self.HeartBeat()
      return self.want_udp_status == self.got_udp_status
    if offset == 0:			# Change back to the original frequency
      if self.repeater_freq is None:		# Frequency was already reset
        return self.want_udp_status == self.got_udp_status
      self.tx_frequency = self.repeater_freq
      self.repeater_freq = None
    else:			# Shift to repeater input frequency
      self.repeater_freq = self.tx_frequency
      offset = int(offset * 1000)	# Convert kHz to Hz
      self.tx_frequency += offset
    self.tx_phase = int(float(self.tx_frequency - self.transverter_offset) / self.conf.rx_udp_clock * 2.0**32 + 0.5) & 0xFFFFFFFF
    self.NewUdpStatus(True)
    return False
  def ChangeMode(self, mode):
    # mode is a string: "USB", "AM", etc.
    self.mode = mode
    self.tx_control &= ~0x03	# Erase last two bits
    if self.vna_count:
      pass
    elif self.usingSpot:
      self.tx_control |= 0x02
    elif mode in ("CWL", "CWU"):
      self.tx_control |= 0x01
    else:
      self.tx_control |= 0x02
    self.SetTxLevel()
  def ChangeBand(self, band):
    # band is a string: "60", "40", "WWV", etc.
    BaseHardware.ChangeBand(self, band)
    self.band = band
    self.HiQSDR_Connector_X1 &= ~0x0F	# Mask in the last four bits
    self.HiQSDR_Connector_X1 |= self.conf.HiQSDR_BandDict.get(band, 0) & 0x0F
    self.SetTxLevel()
  def SetTxLevel(self):
    # As tx_level varies from 50 to 200, the output level changes from 263 to 752 mV
    # So 0 to 255 is 100 to 931, or 1.0 to 9.31; v = 1.0 + 0.0326 * level
    if not self.vna_count:
      try:
        self.tx_level = self.conf.tx_level[self.band]
      except KeyError:
        self.tx_level = self.conf.tx_level.get(None, 127)	# The default
      if self.mode[0:3] in ('DGT', 'FDV'):			# Digital modes; change power by a percentage
        reduc = self.application.digital_tx_level
      else:
        reduc = self.application.tx_level
      level = 1.0 + self.tx_level * 0.0326
      level *= math.sqrt(reduc / 100.0)      # Convert from a power to an amplitude
      self.tx_level = int((level - 1.0) / 0.0326 + 0.5)
      if self.tx_level < 0:
        self.tx_level = 0
      elif self.tx_level > 255:
        self.tx_level = 255
    self.NewUdpStatus()
  def OnButtonRfGain(self, event):
    # The HiQSDR attenuator is five bits: 2, 4, 8, 10, 20 dB
    btn = event.GetEventObject()
    n = btn.index
    self.HiQSDR_Connector_X1 &= ~0x10	# Mask in the preamp bit
    if n == 0:		# 0dB
      self.HiQSDR_Attenuator = 0
      self.rf_gain = 0
    elif n == 1:	# +10
      self.HiQSDR_Attenuator = 0
      self.HiQSDR_Connector_X1 |= 0x10
      self.rf_gain = 10
    elif n == 2:	# -10
      self.HiQSDR_Attenuator = 0x08
      self.rf_gain = -10
    elif n == 3:	# -20
      self.HiQSDR_Attenuator = 0x10
      self.rf_gain = -20
    elif n == 4:	# -30
      self.HiQSDR_Attenuator = 0x18
      self.rf_gain = -30
    else:
      self.HiQSDR_Attenuator = 0
      self.rf_gain = 0
      print ('Unknown RfGain')
    self.NewUdpStatus()
  def OnButtonPTT(self, event):
    # This feature requires firmware version 1.1 or higher
    if self.firmware_version:
      btn = event.GetEventObject()
      if btn.GetValue():		# Turn the software key bit on or off
        self.tx_control |= 0x08
      else:
        self.tx_control &= ~0x08
      self.NewUdpStatus(True)	# Prompt update for PTT
  def OnButtonAntenna(self, event):
    # This feature requires extended IO
    btn = event.GetEventObject()
    if btn.index:
      self.HiQSDR_Bits |= 0x01
    else:
      self.HiQSDR_Bits &= ~0x01
    self.NewUdpStatus()
  def ChangeSidetone(self, value):		# The sidetone volume changed
    self.sidetone_volume = int(value * 255.1)		# Change 0.0-1.0 to 0-255
    self.NewUdpStatus()
  def HeartBeat(self):
    if self.sndp_active:	# AE4JY Simple Network Discovery Protocol - attempt to set the FPGA IP address
      try:
        self.socket_sndp.sendto(self.sndp_request, (self.broadcast_addr, 48321))
        data = self.socket_sndp.recv(1024)
        # print(repr(data))
      except:
        # traceback.print_exc()
        pass
      else:
        if len(data) == 56 and data[5:14] == 'HiQSDR-v1':
          ip = self.conf.rx_udp_ip.split('.')
          t = (data[0:4] + chr(2) + data[5:37] + chr(int(ip[3])) + chr(int(ip[2])) + chr(int(ip[1])) + chr(int(ip[0]))
               + chr(0) * 12 + chr(self.conf.rx_udp_port & 0xFF) + chr(self.conf.rx_udp_port >> 8) + chr(0))
          # print(repr(t))
          self.socket_sndp.sendto(t, (self.broadcast_addr, 48321))
    try:	# receive the old status if any
      data = self.rx_udp_socket.recv(1024)
      if DEBUG:
        self.PrintStatus(' got ', data)
    except:
      pass
    else:
      if data[0:2] == 'St':
        self.got_udp_status = data
    if self.firmware_version is None:		# get the firmware version
      if self.want_udp_status[0:13] != self.got_udp_status[0:13]:
        try:
          self.rx_udp_socket.send(self.want_udp_status)
          if DEBUG:
            self.PrintStatus('Start', self.want_udp_status)
        except:
          pass
      else:		# We got a correct response.
        self.firmware_version = ord(self.got_udp_status[13])	# Firmware version is returned here
        if DEBUG:
          print ('Got version',  self.firmware_version)
        if self.firmware_version > 0 and self.conf.use_rx_udp == 2:
          self.tx_control |= 0x04	# Use extra control bytes
        self.sndp_active = False
        self.NewUdpStatus()
    else:
      if self.want_udp_status != self.got_udp_status:
        if DEBUG:
          self.PrintStatus('Have ', self.got_udp_status)
          self.PrintStatus(' send', self.want_udp_status)
        try:
          self.rx_udp_socket.send(self.want_udp_status)
        except:
          pass
      elif DEBUG:
        self.rx_udp_socket.send('Qs')
  def PrintStatus(self, msg, string):
    print (msg, ' ', end=' ')
    print (string[0:2], end=' ')
    for c in string[2:]:
      print ("%2X" % ord(c), end=' ')
    print ()
  def GetFirmwareVersion(self):
    return self.firmware_version
  def OnSpot(self, level):
    # level is -1 for Spot button Off; else the Spot level 0 to 1000.
    # The Spot button sets the mode to SSB-equivalent for CW so that the Spot level works.
    if level >= 0 and not self.usingSpot:		# Spot was turned on
      self.usingSpot = True
      self.tx_control |= 0x40
      self.ChangeMode(self.mode)
    elif level < 0 and self.usingSpot:			# Spot was turned off
      self.usingSpot = False
      self.tx_control &= ~0x40
      self.ChangeMode(self.mode)
  def OnBtnFDX(self, is_fdx):   # Status of FDX button, 0 or 1
    if is_fdx:
      self.HiQSDR_Connector_X1 |= 0x20     # Mask in the FDX bit
    else:
      self.HiQSDR_Connector_X1 &= ~0x20
    self.NewUdpStatus()
  def VarDecimGetChoices(self):		# return text labels for the control
    clock = self.conf.rx_udp_clock
    l = []			# a list of sample rates
    for dec in self.decimations:
      l.append(str(int(float(clock) / dec / 1e3 + 0.5)))
    return l
  def VarDecimGetLabel(self):		# return a text label for the control
    return "Sample rate ksps"
  def VarDecimGetIndex(self):		# return the current index
    return self.index
  def VarDecimSet(self, index=None):		# set decimation, return sample rate
    if index is None:		# initial call to set decimation before the call to open()
      rate = self.application.vardecim_set		# May be None or from different hardware
      try:
        dec = int(float(self.conf.rx_udp_clock // rate + 0.5))
        self.index = self.decimations.index(dec)
      except:
        try:
          self.index = self.decimations.index(self.conf.rx_udp_decimation)
        except:
          self.index = 0
    else:
      self.index = index
    dec = self.decimations[self.index]
    if dec >= 128: 
      self.rx_control = dec // 64 - 1		# Second stage decimation less one
      QS.set_sample_bytes(3)
    else:
      self.rx_control = dec // 16 - 1		# Second stage decimation less one
      self.rx_control |= 0b01000000			# Change prescaler to 2 (instead of 8)
      QS.set_sample_bytes(2)
    self.NewUdpStatus()
    return int(float(self.conf.rx_udp_clock) / dec + 0.5)
  def VarDecimRange(self):
    return (48000, 960000)
  def NewUdpStatus(self, do_tx=False):
    s = "St"
    s = s + struct.pack("<L", self.rx_phase)
    s = s + struct.pack("<L", self.tx_phase)
    s = s + chr(self.tx_level) + chr(self.tx_control)
    s = s + chr(self.rx_control)
    if self.firmware_version:	# Add the version
      s = s + chr(self.firmware_version)	# The firmware version will be returned
      if self.tx_control & 0x04:	# Use extra HiQSDR control bytes
        s = s + chr(self.HiQSDR_Connector_X1)
        s = s + chr(self.HiQSDR_Attenuator)
        s = s + chr(self.HiQSDR_Bits)
      else:
        s = s + chr(0) * 3
      s = s + chr(self.sidetone_volume)
      s = s + struct.pack("<H", self.vna_count)
      s = s + chr(self.cw_delay)
      s = s + chr(0)
    else:		# firmware version 0 or None
      s = s + chr(0)	# assume version 0
    self.want_udp_status = s
    if do_tx:
      try:
        self.rx_udp_socket.send(s)
      except:
        pass
  def SetVNA(self, key_down=None, vna_start=None, vna_stop=None, vna_count=None, do_tx=False):
    if key_down is None:
      pass
    elif key_down:
      self.tx_control |= 0x08
    else:
      self.tx_control &= ~0x08
    if vna_count is not None:
      self.vna_count = vna_count	# Number of scan points
    if vna_start is not None:	# Set the start and stop frequencies.  The tx_phase is the frequency delta.
      self.rx_phase = int(float(vna_start) / self.conf.rx_udp_clock * 2.0**32 + 0.5) & 0xFFFFFFFF
      self.tx_phase = int(float(vna_stop - vna_start) / (self.vna_count - 1) / self.conf.rx_udp_clock * 2.0**32 + 0.5) & 0xFFFFFFFF
    self.tx_control &= ~0x03	# Erase last two bits
    self.rx_control = 40 - 1
    self.tx_level = 255
    self.NewUdpStatus(do_tx)
    start = int(float(self.rx_phase) * self.conf.rx_udp_clock / 2.0**32 + 0.5)
    phase = self.rx_phase + self.tx_phase * (self.vna_count - 1)
    stop = int(float(phase) * self.conf.rx_udp_clock / 2.0**32 + 0.5)
    return start, stop		# return the start and stop frequencies after integer rounding
