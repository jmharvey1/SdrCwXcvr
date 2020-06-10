# This is the config file for the VHF/UHF receiver and transmitter.

from __future__ import print_function

import sys, struct, socket, traceback

from quisk_hardware_model import Hardware as BaseHardware
from n2adr import uhfrx_widgets as quisk_widgets
import _quisk as QS

settings_file_path = "../quisk_settings.json"

DEBUG = 0
if sys.platform == "win32":
  n2adr_sound_pc_capt = 'Line In (Realtek High Definition Audio)'
  n2adr_sound_pc_play = 'Speakers (Realtek High Definition Audio)'
  n2adr_sound_usb_play = 'Primary'
  n2adr_sound_usb_mic = 'Primary'
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
microphone_name = n2adr_sound_usb_mic

playback_rate = 48000
agc_off_gain = 80
do_repeater_offset = True

station_display_lines = 1
# DX cluster telent login data, thanks to DJ4CM.
dxClHost = ''
#dxClHost = 'dxc.w8wts.net'
dxClPort = 7373
user_call_sign = 'n2adr'

bandLabels = ['6', '2', '1.25', '70cm', '33cm', '23cm', 'WWV']
bandState['WWV'] = (19990000, 10000, 'AM')
BandEdge['WWV'] = (19500000, 20500000)

use_rx_udp = 17		                    		# Get ADC samples from UDP
rx_udp_ip = "192.168.1.199"	                	# Sample source IP address
rx_udp_port = 0xAA53		                	# Sample source UDP port
rx_clock38 = 38880000 - 30                      # master clock frequency, 38880 kHz nominal
rx_udp_clock = rx_clock38 * 32 / 2 / 9  		# ADC sample rate in Hertz
rx_udp_clock_nominal = 69120000                 # rate to display
sample_rate = 96000                             # 96, 192, 384, 768, 1152 (for 69120/3/10)
display_fraction = 1.00
fft_size_multiplier = 16
tx_ip = "192.168.1.201"
tx_audio_port = 0xBC79
tx_clock80 = 80000000 + 14
add_imd_button = 1
add_fdx_button = 1
CorrectTxDc = {
'23cm':(1270.0, 0.167081, 0.150557),
'2':(146.0, 0.018772, 0.038658),
'33cm':(915.0, 0.140150, 0.051967),
'6':(52.0, 0.020590, 0.024557),
'70cm':(435.0, 0.004495, 0.096879),
'1.25':(223.5, 0.042958, 0.055212),
}

class Adf4351:      # class to hold adf4351 attributes
  def __init__(self, receiver, clock, r_counter):
    self.receiver = receiver
    self.clock = clock
    self.r_counter = r_counter
    self.int_mode = 1                # integer one, fractional zero
    self.band_sel_clock_div = 40
    self.aux_rf_out = 0b000          # enable 1/0, power 00 to 11
    self.frac_value = 0
    self.modulus = 23
    self.changed = 0

class Hardware(BaseHardware):
  def __init__(self, app, conf):
    BaseHardware.__init__(self, app, conf)
    self.use_sidetone = 0
    self.vfo_frequency = 52000000
    self.vfo_sample_rate = conf.sample_rate
    self.vfo_test = 0	# JIM
    self.tx_frequency = 0
    self.firmware_version = None	# firmware version is initially unknown
    self.rx_udp_socket = None
    self.tx_udp_socket = None
    self.got_rx_udp_status = ''
    self.got_tx_udp_status = ''
    self.band = ''
    self.rx_phase0 = self.rx_phase1 = 0
    self.tx_phase = 0
    self.button_PTT = 0
    self.mode_is_cw = 0
    self.scan_enable = 0
    self.scan_blocks = 0
    self.scan_samples = 1
    self.scan_phase = 0
    self.fft_scan_valid = 0.84
    self.Rx4351 = Adf4351(True, conf.rx_clock38, 8)
    self.Tx4351 = Adf4351(False, 10700000, 2)
    self.Tx4351.aux_rf_out = 0b000  # enable aux RF out 0b111 or turn off 0b000
    self.decim3 = 10
    self.SetDecim(192000)
    self.var_rates = ['31X', '19X', '9X', '5X', '3X', '2X', '1728', '1152', '768', '384', '192', '96', '48']	# supported sample rates as strings
    self.index = 0
    self.DcI, self.DcQ = (0.0, 0.0)
    self.NewAdf4351(self.Rx4351, 146E6)
    self.NewAdf4351(self.Tx4351, 146E6)
    self.NewAd9951(52e6)
    self.NewUdpStatus()
  def ChangeFrequency(self, tx_freq, vfo_freq, source='', band='', event=None):
    self.tx_frequency = tx_freq
    if not self.Rx4351.frequency - 3E6 < vfo_freq < self.Rx4351.frequency + 3E6:
      self.NewAdf4351(self.Rx4351, vfo_freq)
      self.vfo_frequency = -1
    self.NewAd9951(tx_freq)
    if abs(self.ad9951_freq - 10.7e6) > 15000:
      self.NewAdf4351(self.Tx4351, tx_freq)
      self.NewAd9951(tx_freq)
    self.NewAd9951(tx_freq)
    if self.vfo_frequency != vfo_freq:
      self.vfo_frequency = vfo_freq
      self.scan_deltaf = int(1152E3 * self.fft_scan_valid + 0.5)
      self.scan_phase = int(1152.E3 * self.fft_scan_valid / self.conf.rx_udp_clock * 2.0**32 + 0.5)
      self.scan_vfo0 = vfo_freq
      rx_phase1 = int((vfo_freq - self.Rx4351.frequency) / self.conf.rx_udp_clock * 2.0**32 + 0.5)
      if self.scan_enable:
        self.scan_vfo0 = self.scan_vfo0 - self.scan_deltaf * (self.scan_blocks - 1) / 2
        rx_phase1 = rx_phase1 - int(self.scan_phase * (self.scan_blocks - 1) / 2.0 + 0.5)
      self.rx_phase1 = rx_phase1 & 0xFFFFFFFF
      rx_tune_freq = float(rx_phase1) * self.conf.rx_udp_clock / 2.0**32
      QS.change_rates(96000, tx_freq, self.vfo_sample_rate, vfo_freq)
      QS.change_scan(self.scan_blocks, 1152000, self.fft_scan_valid, self.scan_vfo0, self.scan_deltaf)
      if DEBUG:
        #print( "vfo", vfo_freq, "adf4351", self.Rx4351.frequency, "phase", rx_phase1, "rx_tune", self.Rx4351.frequency - vfo_freq, rx_tune_freq)
        #print ("VFO", self.Rx4351.frequency + rx_tune_freq)
        print ("Change to Tx %d Vfo %d; VFO %.0f = adf4351_freq %.0f + rx_tune_freq %.0f" % (tx_freq, vfo_freq,
              self.Rx4351.frequency + rx_tune_freq, self.Rx4351.frequency, rx_tune_freq))
        #print ("scan_enable %d, scan_blocks %d, scan_vfo0 %d, scan_deltaf %d" % (self.scan_enable, self.scan_blocks, self.scan_vfo0, self.scan_deltaf))
    else:
      QS.change_rates(96000, tx_freq, self.vfo_sample_rate, self.vfo_frequency)
    rx_phase0 = int((tx_freq - self.Rx4351.frequency) / self.conf.rx_udp_clock * 2.0**32 + 0.5)
    self.rx_phase0 = rx_phase0 & 0xFFFFFFFF
    self.NewUdpStatus()
    if self.application.bottom_widgets:
      Rx1 = self.Rx4351.frequency * 1e-6
      Rx2 = (self.ReturnVfoFloat() - self.Rx4351.frequency) * 1e-6
      t = "Rx Div %d; ADF4351 %.6f + rx_tune %.6f = %.6f    Tx Adf4351 %.6f AD9951 %.6f" % (
         2**self.Rx4351.rf_divider, Rx1, Rx2, Rx1 + Rx2, self.Tx4351.frequency * 1e-6, self.ad9951_freq * 1e-6)
      self.application.bottom_widgets.UpdateText(t)
    return tx_freq, vfo_freq
  def RepeaterOffset(self, offset=None):	# Change frequency for repeater offset during Tx
    if offset is None:		# Return True if frequency change is complete
      self.HeartBeat()
      return self.want_rx_udp_status[16:] == self.got_tx_udp_status[16:]
    if offset == 0:			# Change back to the original frequency
      if self.repeater_freq is None:		# Frequency was already reset
        return self.want_rx_udp_status[16:] == self.got_tx_udp_status[16:]
      self.ChangeFrequency(self.repeater_freq, self.vfo_frequency)
      self.repeater_freq = None
    else:			# Shift to repeater input frequency
      self.repeater_freq = self.tx_frequency
      offset = int(offset * 1000)	# Convert kHz to Hz
      self.ChangeFrequency(self.tx_frequency + offset, self.vfo_frequency)
    return False
  def ReturnVfoFloat(self):     # Return the accurate VFO as a float
    rx_phase1 = int((self.vfo_frequency - self.Rx4351.frequency) / self.conf.rx_udp_clock * 2.0**32 + 0.5)
    rx_tune_freq = float(rx_phase1) * self.conf.rx_udp_clock / 2.0**32
    return self.Rx4351.frequency + rx_tune_freq
  def open(self):
    ##self.application.config_screen.config.tx_phase.Enable(1)
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
    self.sndp_rx_active = True
    # conf.rx_udp_port is used for returning ADC samples
    # conf.rx_udp_port + 1 is used for control
    self.rx_udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    self.rx_udp_socket.setblocking(0)
    self.rx_udp_socket.connect((self.conf.rx_udp_ip, self.conf.rx_udp_port + 1))
    # conf.tx_audio_port + 1 is used for control
    if self.conf.tx_ip:
      self.sndp_tx_active = True
      self.tx_udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
      self.tx_udp_socket.setblocking(0)
      self.tx_udp_socket.connect((self.conf.tx_ip, self.conf.tx_audio_port + 1))
    else:
      self.sndp_tx_active = False
    QS.change_rates(96000, 0, 96000, 0)
    self.application.test1Button.Enable(0)
    return QS.open_rx_udp(self.conf.rx_udp_ip, self.conf.rx_udp_port)
  def close(self):
    if self.rx_udp_socket:
      self.rx_udp_socket.close()
      self.rx_udp_socket = None
    if self.tx_udp_socket:
      self.tx_udp_socket.close()
      self.tx_udp_socket = None
  def PrintStatus(self, msg, string):
    print (msg, ' ', end=' ')
    print (string[0:2], end=' ')
    for c in string[2:]:
      print ("%2X" % ord(c), end=' ')
    print ()
  def GetFirmwareVersion(self):
    return self.firmware_version
  def ChangeMode(self, mode):
    # mode is a string: "USB", "AM", etc.
    if mode in ("CWL", "CWU"):
      self.mode_is_cw = 1
    else:
      self.mode_is_cw = 0
    self.NewUdpStatus()
  def ChangeBand(self, band):
    # band is a string: "60", "40", "WWV", etc.
    self.band = band
    try:
      freq, DcI, DcQ = self.conf.CorrectTxDc[band]
    except KeyError:
      DcI, DcQ = (0.0, 0.0)
    self.NewUdpCorrect(DcI, DcQ)
  def NewUdpCorrect(self, DcI, DcQ):
    self.DcI = DcI
    self.DcQ = DcQ
    QS.set_udp_tx_correct(DcI, DcQ, 0.828)
    self.NewUdpStatus()
  def PrintUdpCorrect(self):
    for band, (freq, DcI, DcQ) in self.conf.CorrectTxDc.items():
      print ("'%s':(%.1f, %.6f, %.6f)," % (band, freq, DcI, DcQ))
  def OnButtonPTT(self, event):
    btn = event.GetEventObject()
    if btn.GetValue():		# Turn the software key bit on or off
      self.button_PTT = 1
    else:
      self.button_PTT = 0
    QS.set_key_down(self.button_PTT)
    self.NewUdpStatus()
  def OnSpot(self, level):
    # level is -1 for Spot button Off; else the Spot level 0 to 1000.
    pass
  def Sndp(self):	# AE4JY Simple Network Discovery Protocol - attempt to set the FPGA IP address
    try:
      self.socket_sndp.sendto(self.sndp_request, (self.broadcast_addr, 48321))
    except:
      if DEBUG:
        traceback.print_exc()
      return
    for i in range(5):
      try:
        data = self.socket_sndp.recv(1024)
      except:
        break
      if len(data) != 56:
        continue
      if data[5:17] == 'QuiskUHFR-v1':
        ip = self.conf.rx_udp_ip.split('.')
        ip = map(int, ip)
        ip = map(chr, ip)
        if data[37] == ip[3] and data[38] == ip[2] and data[39] == ip[1] and data[40] == ip[0]:
          self.sndp_rx_active = False
          if DEBUG: print("SNDP success for Rx")
        else:
          t = (data[0:4] + chr(2) + data[5:37] + ip[3] + ip[2] + ip[1] + ip[0]
             + chr(0) * 12 + chr(self.conf.rx_udp_port & 0xFF) + chr(self.conf.rx_udp_port >> 8) + chr(0))
          self.socket_sndp.sendto(t, (self.broadcast_addr, 48321))
      elif data[5:17] == 'QuiskUHFT-v1':
        if self.conf.tx_ip:
          ip = self.conf.tx_ip.split('.')
          ip = map(int, ip)
          ip = map(chr, ip)
          if data[37] == ip[3] and data[38] == ip[2] and data[39] == ip[1] and data[40] == ip[0]:
            self.sndp_tx_active = False
            if DEBUG: print("SNDP success for Tx")
          else:
            t = (data[0:4] + chr(2) + data[5:37] + ip[3] + ip[2] + ip[1] + ip[0]
               + chr(0) * 12 + chr(self.conf.tx_audio_port & 0xFF) + chr(self.conf.tx_audio_port >> 8) + chr(0))
            self.socket_sndp.sendto(t, (self.broadcast_addr, 48321))
  def HeartBeat(self):
    if self.sndp_rx_active or self.sndp_tx_active:
      self.Sndp()
      return        # SNDP is required
    for i in range(10):
      try:	# receive the Rx status if any
        data = self.rx_udp_socket.recv(1024)
        if DEBUG > 1:
          self.PrintStatus(' gotRx ', data)
      except:
        break
      else:
        if data[0:2] == 'Sx':
          self.got_rx_udp_status = data
    if self.tx_udp_socket:
      for i in range(10):
        try:	# receive the Tx status if any
          data = self.tx_udp_socket.recv(1024)
          if DEBUG > 1:
            self.PrintStatus(' gotTx ', data)
        except:
          break
        else:
          if data[0:2] == 'Sx':
            self.got_tx_udp_status = data
    if self.want_rx_udp_status[16:] == self.got_rx_udp_status[16:]:   # The first part returns information from the hardware
      self.firmware_version = ord(self.got_rx_udp_status[2])       # Firmware version is returned here
      self.Rx4351.changed = 0
    else:
      if DEBUG > 1:
        self.PrintStatus('HaveRx', self.got_rx_udp_status[0:20])
        self.PrintStatus('sendRx', self.want_rx_udp_status[0:20])
      try:
        self.rx_udp_socket.send(self.want_rx_udp_status)
      except:
        #traceback.print_exc()
        pass
    if not self.tx_udp_socket:
      pass
    elif self.want_rx_udp_status[16:] == self.got_tx_udp_status[16:]:   # The first part returns information from the hardware
      self.Tx4351.changed = 0
      self.Tx9951_changed = 0
    else:
      if DEBUG > 1:
        self.PrintStatus('HaveTx', self.got_rx_udp_status[0:20])
        self.PrintStatus('sendTx', self.want_rx_udp_status[0:20])
      try:
        self.tx_udp_socket.send(self.want_rx_udp_status)
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
      self.scan_enable = 1
      self.scan_blocks = int(rate[0:-1])
      self.scan_samples = self.application.fft_size
      self.decim1 = 2
      self.decim2 = 3
      rate = 1152000 * self.scan_blocks
    else:
      self.scan_enable = 0
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
  def NewUdpStatus(self):
    # Start of 16 bytes sent to the hardware:
    s = "Sx"            # 0:2   Fixed string 
    s += chr(0)         # 2     Version number is returned here
    s += chr(0)         # 3
    s += chr(0) * 12    # 4:16
    # Start of 80 bytes of data sent to the hardware:
    s += chr( 6 - 1)						#  0    Variable decimation less one channel 0 first
    s += chr(12 - 1)			        	#  1    Variable decimation less one channel 0 second
    s += struct.pack("<L", self.rx_phase0)	#  2: 6 Channel zero Rx tune phase
    s += struct.pack("<L", self.rx_phase1)	#  6:10 Channel one Rx tune phase)
    s += chr(0x3 | self.scan_enable << 2 | self.Rx4351.changed << 3 |
            self.Tx4351.changed << 4 | self.Tx9951_changed << 5 |
            self.button_PTT << 6 | self.mode_is_cw << 7)		# 10    Flags
        # 0: enable samples on channel 0
        # 1: enable samples on channel 1
        # 2: enable scan on channel 1
        # 3: the receive adf4351 registers have changed
        # 4: the transmit adf4351 registers have changed
        # 5: the transmit ad9951 register changed
        # 6: the PTT button is down
        # 7: the mode is CWU or CWL
    s += chr(self.scan_blocks)						# 11    For scan, the number of frequency blocks
    s += struct.pack("<H", self.scan_samples)		# 12:14 For scan, the number of samples per block
    s += struct.pack("<L", self.scan_phase)			# 14:18 For scan, the tuning phase increment
    s += chr(self.decim1 - 1)				    	# 18    Variable decimation less one channel 1 first
    s += chr(self.decim2 - 1)		        		# 19    Variable decimation less one channel 1 second
    s += self.Rx4351.regs                           # 20:44 Receive adf4351; six 32-bit registers, 24 bytes
    s += self.Tx4351.regs                           # 44:68 Transmit adf4351; six 32-bit registers, 24 bytes
    s += self.ad9951_data                           # 68:74 Transmit ad9951: data length, instruction, 4 bytes of data
    DcI = int(self.DcI * 32767.0)
    DcQ = int(self.DcQ * 32767.0)
    s += struct.pack("<h", DcI)                # 74:76 Transmit DC correction for I channel
    s += struct.pack("<h", DcQ)                # 76:78 Transmit DC correction for Q channel
    s += chr(0) * (96 - len(s))     # Fixed length message 16 + 80
    self.want_rx_udp_status = s
  def NewAd9951(self, tx_freq):
    # Fpfd = Fref / 2 / R = Fvco / N
    # Fout = Fvco / 2**D and is twice the transmit frequency
    # Fref = 2R(2**d)Fout / N
    # Fout = Fref * N / 2 / R / 2**D
    adf = self.Tx4351
    freq = 2.0 * adf.r_counter * (2 ** adf.rf_divider) / adf.int_value * (tx_freq * 2.0)
    phase = int(freq / self.conf.tx_clock80 * 2.0**32 + 0.5)
    try:
      self.ad9951_data = chr(40) + struct.pack("<L", phase ) + chr(4)
    except struct.error:
      self.ad9951_data = chr(0) * 6
    self.ad9951_freq = float(phase) * self.conf.tx_clock80 / 2 ** 32
    ##adf.frequency = 0.5 * self.ad9951_freq * adf.int_value / 2.0 / adf.r_counter / (2 ** adf.rf_divider)
    self.Tx9951_changed = 1
  def NewAdf4351(self, adf, vfo_freq):
    # Set the adf4351 to the nearest integer-mode frequency
    Fpfd = adf.clock / 2.0 / adf.r_counter
    if adf.receiver:
      vfo_freq += Fpfd * self.vfo_test / 8	# test the VFO at an offset from the center
    vfo = vfo_freq * 2      # Local oscillator runs at 2X frequency
    for div in range(0, 7):
      Fvco = vfo * 2 ** div
      if 2200E6 <= Fvco < 4400E6:
        adf.rf_divider = div
        adf.int_value = int(vfo * 2 ** div / Fpfd + 0.5)
        break
    else:
      if vfo < 500e6:
        adf.rf_divider = 6
        adf.int_value = int(2200E6 / Fpfd)
      else:
        adf.rf_divider = 0
        adf.int_value = int(4400E6 / Fpfd)
    adf.frequency = 0.5 * Fpfd * adf.int_value / 2 ** div
    if DEBUG:
      print ("int, div, Fvco, ADF4351", adf.int_value, div, int(vfo * 2 ** div / 1e6), adf.frequency)
      print ("New adf4351_freq", adf.frequency)
    # Number of bits for each field:
    # intNmode              1
    # aux_rf_out            3
    # rf_divider            3
    # band_sel_clock_div    8
    # r_counter             10  Fpfd = Fref / 2 / r_counter
    # int_value             16  Fvco = Fpfd * (int_value + frac_value / modulus)
    # frac_value            12
    # modulus               12
    reg = 0b00000000000000000000000000000000    # Register 0
    reg = reg | adf.int_value << 15 | adf.frac_value << 3
    s  = struct.pack("<L", reg)
    reg = 0b00001000000000001000000000000001    # Register 1
    reg = reg | adf.modulus << 3
    s += struct.pack("<L", reg)
    reg = 0b00000001000000000001111001000010    # Register 2
    reg = reg | adf.r_counter << 14 | adf.int_mode << 8 | adf.int_mode << 7
    s += struct.pack("<L", reg)
    reg = 0b00000000000001000000000000000011    # Register 3
    reg = reg | adf.int_mode << 22 | adf.int_mode << 21 
    s += struct.pack("<L", reg)
    reg = 0b00000000100000000000010000111100    # Register 4
    reg = reg | adf.rf_divider << 20 | adf.band_sel_clock_div << 12 | adf.aux_rf_out << 6
    s += struct.pack("<L", reg)
    reg = 0b00000000010110000000000000000101    # Register 5
    s += struct.pack("<L", reg)
    adf.regs = s
    adf.changed = 1
  def TestVfoPlus(self, event):
    self.vfo_test += 1
    self.Rx4351.frequency = 1
    self.ChangeFrequency(self.tx_frequency, self.vfo_frequency)
  def TestVfoMinus(self, event):
    self.vfo_test -= 1
    self.Rx4351.frequency = 1
    self.ChangeFrequency(self.tx_frequency, self.vfo_frequency)
