# This is the config file for the VHF/UHF receiver. 

from __future__ import print_function

import sys, struct, socket, traceback

from quisk_hardware_model import Hardware as BaseHardware
from n2adr import uhfrx_widgets as quisk_widgets
import _quisk as QS

DEBUG = 0
if sys.platform == "win32":
  n2adr_sound_pc_capt = 'Line In (Realtek High Definition Audio)'
  n2adr_sound_pc_play = 'Speakers (Realtek High Definition Audio)'
  n2adr_sound_usb_play = 'Primary'
  n2adr_sound_usb_mic = 'Line In (USB Multi-Channel'
  latency_millisecs = 150
  data_poll_usec = 20000
  favorites_file_path = "C:/pub/quisk_favorites.txt"
elif 0:		# portaudio devices
  name_of_sound_play = 'portaudio:CODEC USB'
  microphone_name = "portaudio:AK5370"
  latency_millisecs = 150
  data_poll_usec = 5000
  favorites_file_path = "/home/jim/pub/quisk_favorites.txt"
else:		# alsa devices
  n2adr_sound_pc_capt = 'alsa:ALC888-VD'
  n2adr_sound_pc_play = 'alsa:ALC888-VD'
  n2adr_sound_usb_play = 'alsa:USB Sound Device'
  n2adr_sound_usb_mic = 'alsa:USB Sound Device'
  latency_millisecs = 150
  data_poll_usec = 5000
  favorites_file_path = "/home/jim/pub/quisk_favorites.txt"

name_of_sound_capt = ""
name_of_sound_play = n2adr_sound_usb_play

playback_rate = 48000
agc_off_gain = 80

station_display_lines = 1
# DX cluster telent login data, thanks to DJ4CM.
dxClHost = ''
#dxClHost = 'dxc.w8wts.net'
dxClPort = 7373
user_call_sign = 'n2adr'

bandLabels = ['6', '2', '1.25', '70cm', '33cm', '23cm', 'WWV']
bandState['WWV'] = (19990000, 10000, 'AM')

use_rx_udp = 17		                    		# Get ADC samples from UDP
rx_udp_ip = "192.168.1.199"	                	# Sample source IP address
rx_udp_port = 0xAA53		                	# Sample source UDP port
rx_clock38 = 38879976                           # master clock frequency
rx_udp_clock = rx_clock38 * 32 / 2 / 9  		# ADC sample rate in Hertz
rx_udp_clock_nominal = 69120000                 # rate to display
sample_rate = 96000                             # 96, 192, 384, 768, 1152 (for 69120/3/10)
display_fraction = 1.00
fft_size_multiplier = 16

class Hardware(BaseHardware):
  def __init__(self, app, conf):
    BaseHardware.__init__(self, app, conf)
    self.use_sidetone = 0
    self.vfo_frequency = 52000000
    self.vfo_sample_rate = conf.sample_rate
    self.vfo_test = 0	# JIM
    self.adf4351_freq = 52E6
    self.tx_frequency = 0
    self.firmware_version = None	# firmware version is initially unknown
    self.rx_udp_socket = None
    self.got_udp_status = ''
    self.got_adf4351_status = ''
    self.rx_phase0 = self.rx_phase1 = 0
    self.tx_phase = 0
    self.scan_enable = 0
    self.scan_blocks = 0
    self.scan_samples = 1
    self.scan_phase = 0
    self.fft_scan_valid = 0.84
    self.adf4351_int_mode = 1               # integer one, fractional zero
    self.adf4351_aux_rf_out = 0b101
    self.adf4351_rf_divider = 4             # Fout = Fvco / 2 ** rf_divider
    self.adf4351_band_sel_clock_div = 40
    self.adf4351_r_counter = 8              # Fpfd = Fref / 2 / r_counter
    self.adf4351_int_value = 1317           # Fvco = Fpfd * (int_value + frac_value / modulus)
    self.adf4351_frac_value = 0
    self.adf4351_modulus = 23
    self.decim3 = 10
    self.SetDecim(192000)
    self.var_rates = ['31X', '19X', '9X', '5X', '3X', '2X', '1728', '1152', '768', '384', '192', '96', '48']	# supported sample rates as strings
    self.index = 0
    self.NewUdpStatus()
    self.NewAdf4351(self.adf4351_freq)
  def ChangeFrequency(self, tx_freq, vfo_freq, source='', band='', event=None):
    self.tx_frequency = tx_freq
    if not self.adf4351_freq - 3E6 < vfo_freq < self.adf4351_freq + 3E6:
      self.NewAdf4351(vfo_freq)
      self.vfo_frequency = -1
    if self.vfo_frequency != vfo_freq:
      self.vfo_frequency = vfo_freq
      self.scan_deltaf = int(1152E3 * self.fft_scan_valid + 0.5)
      self.scan_phase = int(1152.E3 * self.fft_scan_valid / self.conf.rx_udp_clock * 2.0**32 + 0.5)
      self.scan_vfo0 = vfo_freq
      rx_phase1 = int((vfo_freq - self.adf4351_freq) / self.conf.rx_udp_clock * 2.0**32 + 0.5)
      if self.scan_enable:
        self.scan_vfo0 = self.scan_vfo0 - self.scan_deltaf * (self.scan_blocks - 1) / 2
        rx_phase1 = rx_phase1 - int(self.scan_phase * (self.scan_blocks - 1) / 2.0 + 0.5)
      self.rx_phase1 = rx_phase1 & 0xFFFFFFFF
      rx_tune_freq = float(rx_phase1) * self.conf.rx_udp_clock / 2.0**32
      QS.change_rates(96000, tx_freq, self.vfo_sample_rate, vfo_freq)
      QS.change_scan(self.scan_blocks, 1152000, self.fft_scan_valid, self.scan_vfo0, self.scan_deltaf)
      if DEBUG:
        #print( "vfo", vfo_freq, "adf4351", self.adf4351_freq, "phase", rx_phase1, "rx_tune", self.adf4351_freq - vfo_freq, rx_tune_freq)
        #print ("VFO", self.adf4351_freq + rx_tune_freq)
        print ("Change to Tx %d Vfo %d; VFO %.0f = adf4351_freq %.0f + rx_tune_freq %.0f" % (tx_freq, vfo_freq, self.adf4351_freq + rx_tune_freq,
              self.adf4351_freq, rx_tune_freq))
        #print ("scan_enable %d, scan_blocks %d, scan_vfo0 %d, scan_deltaf %d" % (self.scan_enable, self.scan_blocks, self.scan_vfo0, self.scan_deltaf))
    else:
      QS.change_rates(96000, tx_freq, self.vfo_sample_rate, self.vfo_frequency)
    rx_phase0 = int((tx_freq - self.adf4351_freq) / self.conf.rx_udp_clock * 2.0**32 + 0.5)
    self.rx_phase0 = rx_phase0 & 0xFFFFFFFF
    self.NewUdpStatus()
    self.NewStatus()
    return tx_freq, vfo_freq
  def NewStatus(self):
    if self.application.bottom_widgets:
      Adf = self.adf4351_freq * 1e-6
      Frx = (self.ReturnVfoFloat() - self.adf4351_freq) * 1e-6
      t = "Div %d; ADF4351 %.6f + rx_tune %.6f = %.6f" % (2**self.adf4351_rf_divider, Adf, Frx, Adf + Frx)
      self.application.bottom_widgets.UpdateText(t)
  def ReturnVfoFloat(self):     # Return the accurate VFO as a float
    rx_phase1 = int((self.vfo_frequency - self.adf4351_freq) / self.conf.rx_udp_clock * 2.0**32 + 0.5)
    rx_tune_freq = float(rx_phase1) * self.conf.rx_udp_clock / 2.0**32
    return self.adf4351_freq + rx_tune_freq
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
    QS.change_rates(96000, 0, 96000, 0)
    self.application.splitButton.Enable(0)
    self.application.test1Button.Enable(0)
    return QS.open_rx_udp(self.conf.rx_udp_ip, self.conf.rx_udp_port)
  def close(self):
    if self.rx_udp_socket:
      self.rx_udp_socket.close()
      self.rx_udp_socket = None
  def PrintStatus(self, msg, string):
    print (msg, ' ', end=' ')
    print (string[0:2], end=' ')
    for c in string[2:]:
      print ("%2X" % ord(c), end=' ')
    print ()
  def GetFirmwareVersion(self):
    return self.firmware_version
  def HeartBeat(self):
    if self.sndp_active:	# AE4JY Simple Network Discovery Protocol - attempt to set the FPGA IP address
      try:
        self.socket_sndp.sendto(self.sndp_request, (self.broadcast_addr, 48321))
        data = self.socket_sndp.recv(1024)
        #print(repr(data))
      except:
        #traceback.print_exc()
        pass
      else:
        if len(data) == 56 and data[5:17] == 'QuiskUHFR-v1':
          ip = self.conf.rx_udp_ip.split('.')
          ip = map(int, ip)
          ip = map(chr, ip)
          if data[37] == ip[3] and data[38] == ip[2] and data[39] == ip[1] and data[40] == ip[0]:
            self.sndp_active = False
          else:
            t = (data[0:4] + chr(2) + data[5:37] + ip[3] + ip[2] + ip[1] + ip[0]
               + chr(0) * 12 + chr(self.conf.rx_udp_port & 0xFF) + chr(self.conf.rx_udp_port >> 8) + chr(0))
            # print(repr(t))
            self.socket_sndp.sendto(t, (self.broadcast_addr, 48321))
    for i in range(10):
      try:	# receive the old status if any
        data = self.rx_udp_socket.recv(1024)
        if DEBUG > 1:
          self.PrintStatus(' got ', data)
      except:
        break
      else:
        if data[0:2] == 'Sx':
          self.got_udp_status = data
        elif data[0:2] == 'S4':
          self.got_adf4351_status = data
    if self.want_udp_status[16:] == self.got_udp_status[16:]: # The first part returns information from the hardware
      self.sndp_active = False
      self.firmware_version = ord(self.got_udp_status[2])	# Firmware version is returned here
    else:
      if DEBUG > 1:
        self.PrintStatus('Havex', self.got_udp_status)
        self.PrintStatus(' send', self.want_udp_status)
      try:
        self.rx_udp_socket.send(self.want_udp_status)
      except:
        #traceback.print_exc()
        pass
    if self.want_adf4351_status != self.got_adf4351_status:
      if DEBUG > 1:
        self.PrintStatus('Have4', self.got_adf4351_status)
        self.PrintStatus(' send', self.want_adf4351_status)
      try:
        self.rx_udp_socket.send(self.want_adf4351_status)
      except:
        #traceback.print_exc()
        pass
    if 0:
      self.rx_udp_socket.send('Qs')
  def VarDecimGetChoices(self):		# return text labels for the control
    return self.var_rates
  def VarDecimGetLabel(self):		# return a text label for the control
    return "Sample rate ksps"
  def VarDecimGetIndex(self):		# return the current index
    return self.index
  def VarDecimRange(self):
    return (48000, 1152000)
  def VarDecimSet(self, index=None):		# set decimation, return sample rate
    if index is None:		# initial call to set decimation before the call to open()
      rate = self.application.vardecim_set		# May be None or from different hardware
      try:
        rate /= 1000
        if rate > 1152:
          rate = 1152
        index = self.var_rates.index(str(rate))
      except:
        rate = 192
        index = self.var_rates.index(str(rate))
    self.index = index
    rate = self.var_rates[index]
    if rate[-1] == 'X':
      self.scan_enable = 0x4	# set the correct bit
      self.scan_blocks = int(rate[0:-1])
      self.scan_samples = self.application.fft_size
      self.decim1 = 2
      self.decim2 = 3
      rate = 1152000 * self.scan_blocks
    else:
      self.scan_enable = 0x0
      self.scan_blocks = 0
      rate = int(rate)
      rate = rate * 1000
      self.SetDecim(rate)
    vfo = self.vfo_frequency
    self.vfo_frequency = -1
    self.vfo_sample_rate = rate
    self.ChangeFrequency(self.tx_frequency, vfo)
    self.NewUdpStatus()
    return rate
  def SetDecim(self, rate):
    # self.decim1, decim2, decim3 are the first, second, third decimations in the hardware
    if rate >= 1152000:
      self.decim1 = 2
    elif rate >= 192000:
      self.decim1 = 3
    elif rate == 96000:
      self.decim1 = 6
    else:
      self.decim1 = 12
    self.decim2 = self.conf.rx_udp_clock_nominal // rate // self.decim1 // self.decim3
  def NewUdpStatus(self, do_tx=False):
    s = "Sx"
    s += chr(0)      # Version number is returned here
    s += chr(0)
    s += chr(0) * 12
    # Start of data sent to the hardware; byte 16 to 62
    s += chr( 6 - 1)						#  0    Variable decimation less one channel 0 first
    s += chr(12 - 1)			        	#  1    Variable decimation less one channel 0 second
    s += struct.pack("<L", self.rx_phase0)	#  2: 6 Channel zero Rx tune phase
    s += struct.pack("<L", self.rx_phase1)	#  6:10 Channel one Rx tune phase)
    s += chr(0x3 | self.scan_enable)		# 10    Flags
        # 0: enable samples on channel 0
        # 1: enable samples on channel 1
        # 2: enable scan on channel 1
    s += chr(self.scan_blocks)						# 11    For scan, the number of frequency blocks
    s += struct.pack("<H", self.scan_samples)		# 12:14 For scan, the number of samples per block
    s += struct.pack("<L", self.scan_phase)			# 14:18 For scan, the tuning phase increment
    s += chr(self.decim1 - 1)				    	# 18    Variable decimation less one channel 1 first
    s += chr(self.decim2 - 1)		        		# 19    Variable decimation less one channel 1 second
    s += chr(0) * (62 - len(s))     # Fixed length message
    self.want_udp_status = s
    if do_tx:
      try:
        self.rx_udp_socket.send(self.want_udp_status)
      except:
        pass
  def NewAdf4351(self, vfo_freq, do_tx=False):
    # Set the adf4351 to the nearest integer-mode frequency
    Fpfd = self.conf.rx_clock38 / 2.0 / self.adf4351_r_counter
    vfo_freq += Fpfd * self.vfo_test / 8	# test the VFO at an offset from the center
    vfo = vfo_freq * 2      # Local oscillator runs at 2X frequency
    for div in range(0, 7):
      Fvco = vfo * 2 ** div
      if 2200E6 <= Fvco < 4400E6:
        self.adf4351_rf_divider = div
        self.adf4351_int_value = int(vfo * 2 ** div / Fpfd + 0.5)
        break
    else:
      if vfo < 500e6:
        self.adf4351_rf_divider = 6
        self.adf4351_int_value = int(2200E6 / Fpfd)
      else:
        self.adf4351_rf_divider = 0
        self.adf4351_int_value = int(4400E6 / Fpfd)
    self.adf4351_freq = 0.5 * Fpfd * self.adf4351_int_value / 2 ** div
    if DEBUG:
      #print ("int, div, Fvco, ADF4351", self.adf4351_int_value, div, int(vfo * 2 ** div / 1e6), self.adf4351_freq)
      print ("New adf4351_freq", self.adf4351_freq)
    # Number of bits for each field:
    # intNmode              1
    # aux_rf_out            3
    # rf_divider            3
    # band_sel_clock_div    8
    # r_counter             10  Fpfd = Fref / 2 / r_counter
    # int_value             16  Fvco = Fpfd * (int_value + frac_value / modulus)
    # frac_value            12
    # modulus               12
    s = "S4"
    reg = 0b00000000000000000000000000000000    # Register 0
    reg = reg | self.adf4351_int_value << 15 | self.adf4351_frac_value << 3
    s += struct.pack("<L", reg)
    reg = 0b00001000000000001000000000000001    # Register 1
    reg = reg | self.adf4351_modulus << 3
    s += struct.pack("<L", reg)
    reg = 0b00000001000000000001111001000010    # Register 2
    reg = reg | self.adf4351_r_counter << 14 | self.adf4351_int_mode << 8 | self.adf4351_int_mode << 7
    s += struct.pack("<L", reg)
    reg = 0b00000000000001000000000000000011    # Register 3
    reg = reg | self.adf4351_int_mode << 22 | self.adf4351_int_mode << 21 
    s += struct.pack("<L", reg)
    reg = 0b00000000100000000000010000111100    # Register 4
    reg = reg | self.adf4351_rf_divider << 20 | self.adf4351_band_sel_clock_div << 12 | self.adf4351_aux_rf_out << 6
    s += struct.pack("<L", reg)
    reg = 0b00000000010110000000000000000101    # Register 5
    s += struct.pack("<L", reg)
    self.want_adf4351_status = s
    if do_tx:
      try:
        self.rx_udp_socket.send(self.want_adf4351_status)
      except:
        pass
  def TestVfoPlus(self, event):
    self.vfo_test += 1
    self.adf4351_freq = 1
    self.ChangeFrequency(self.tx_frequency, self.vfo_frequency)
  def TestVfoMinus(self, event):
    self.vfo_test -= 1
    self.adf4351_freq = 1
    self.ChangeFrequency(self.tx_frequency, self.vfo_frequency)
