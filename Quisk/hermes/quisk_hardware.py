# This is a sample hardware file for UDP control using the Hermes-Metis protocol.  Use this for
# the HermesLite project.  It can also be used for the HPSDR, but since I don't have one, I
# can't test it.

from __future__ import print_function

import socket, traceback, time, math
import _quisk as QS

from quisk_hardware_model import Hardware as BaseHardware

DEBUG = 0

class Hardware(BaseHardware):
  var_rates = ['48', '96', '192', '384']
  def __init__(self, app, conf):
    BaseHardware.__init__(self, app, conf)
    self.var_index = 0
    self.hermes_ip = ""
    self.hermes_board_id = -1
    self.mode = None
    self.band = None
    self.vfo_frequency = 0
    self.tx_frequency = 0
    self.vna_count = 0
    self.vna_started = False
    self.repeater_freq = None		# original repeater output frequency
    try:
      self.repeater_delay = conf.repeater_delay		# delay for changing repeater frequency in seconds
    except:
      self.repeater_delay = 0.25
    self.repeater_time0 = 0			# time of repeater change in frequency
    # Create the proper broadcast address for rx_udp_ip.
    if False and self.conf.rx_udp_ip:
      nm = self.conf.rx_udp_ip_netmask.split('.')
      ip = self.conf.rx_udp_ip.split('.')
      nm = map(int, nm)
      ip = map(int, ip)
      bc = ''
      for i in range(4):
        x = (ip[i] | ~ nm[i]) & 0xFF
        bc = bc + str(x) + '.'
      self.broadcast_addr = bc[:-1]
    else:
      self.broadcast_addr = '255.255.255.255'
    # This socket is used for the Metis Discover protocol
    self.discover_request = chr(0xEF) + chr(0xFE) + chr(0x02) + chr(0) * 60
    self.socket_discover = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    self.socket_discover.setblocking(0)
    self.socket_discover.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    # This is the control data to send to the Hermes using the Metis protocol
    # Duplex must be on or else the first Rx frequency is locked to the Tx frequency
    self.pc2hermes = bytearray(17 * 4)		# Control bytes not including C0.  Python initializes this to zero.
    self.pc2hermes[3] = 0x04	# C0 index == 0, C4[5:3]: number of receivers 0b000 -> one receiver; C4[2] duplex on
    for c0 in range(1, 9):		# Set all frequencies to 7012352, 0x006B0000
      self.SetControlByte(c0, 2, 0x6B)
    QS.pc_to_hermes(self.pc2hermes)
  def pre_open(self):
    st = "No capture device found."
    port = self.conf.rx_udp_port
    for i in range(5):
      if DEBUG: print ('Send discover')
      try:
        self.socket_discover.sendto(self.discover_request, (self.broadcast_addr, port))
        time.sleep(0.05)
        data, addr = self.socket_discover.recvfrom(1500)
      except:
        if DEBUG > 1: traceback.print_exc()
      else:
        if len(data) > 32 and data[0] == chr(0xEF) and data[1] == chr(0xFE):
          data = map(ord, data)
          ver = self.conf.hermes_code_version
          bid = self.conf.hermes_board_id
          if ver >= 0 and data[9] != ver:
            pass
          elif bid >= 0 and data[10] != bid:
            pass
          else:
            st = 'Capture from Hermes device: Mac %2x:%2x:%2x:%2x:%2x:%2x, Version %d, ID %d' % tuple(data[3:11])
            self.hermes_ip = addr[0]
            self.hermes_board_id = data[10]
            if DEBUG: print (st)
            adr = self.conf.rx_udp_ip
            if adr and adr != addr[0]:		# Specified IP address
              if DEBUG: print("Change IP address from %s to %s" % (addr[0], adr))
              ip = adr.split('.')
              ip = map(int, ip)
              cmd = (chr(0xEF) + chr(0xFE) + chr(0x03) + 
                  chr(data[3]) + chr(data[4]) + chr(data[5]) + chr(data[6]) + chr(data[7]) + chr(data[8]) +
                  chr(ip[0]) + chr(ip[1]) + chr(ip[2]) + chr(ip[3]) + chr(0) * 60)
              self.socket_discover.sendto(cmd, (self.broadcast_addr, port))
              time.sleep(0.1)
              self.socket_discover.sendto(cmd, (self.broadcast_addr, port))
              # Note: There is no response, contrary to the documentation
              self.hermes_ip = adr
              if False:
                try:
                  data, addr = self.socket_discover.recvfrom(1500)
                except:
                  if DEBUG: traceback.print_exc()
                else:
                  print(repr(data), addr)
                  ##self.hermes_ip = adr
                time.sleep(1.0)
            st += ', IP %s' % self.hermes_ip
            # Open a socket for communication with the hardware
            msg = QS.open_rx_udp(self.hermes_ip, port)
            if msg[0:8] != "Capture ":
              st = msg		# Error
            break
      time.sleep(0.05)
    self.socket_discover.close()
    self.config_text = st
  def open(self):
    return self.config_text
  def GetControlByte(self, C0_index, byte_index):
    # Get the control byte at C0 index and byte index.  The bytes are C0, C1, C2, C3, C4.
    # The C0 index is 0 to 16 inclusive.  The byte index is 1 to 4.  The byte index of C2 is 2.
    # microphone.c does not send all C0 0 to 16.
    return self.pc2hermes[C0_index * 4 + byte_index - 1]
  def SetControlByte(self, C0_index, byte_index, value):		# Set the control byte as above.
    self.pc2hermes[C0_index * 4 + byte_index - 1] = value
    QS.pc_to_hermes(self.pc2hermes)
    if DEBUG: print ("SetControlByte C0_index %d byte_index %d to 0x%X" % (C0_index, byte_index, value))
  def ChangeFrequency(self, tx_freq, vfo_freq, source='', band='', event=None):
    if tx_freq and tx_freq > 0:
      self.tx_frequency = tx_freq
      tx = int(tx_freq - self.transverter_offset)
      self.pc2hermes[ 4] = tx >> 24 & 0xff		# C0 index == 1, C1, C2, C3, C4: Tx freq, MSB in C1
      self.pc2hermes[ 5] = tx >> 16 & 0xff
      self.pc2hermes[ 6] = tx >>  8 & 0xff
      self.pc2hermes[ 7] = tx       & 0xff
    if self.vfo_frequency != vfo_freq:
      self.vfo_frequency = vfo_freq
      vfo = int(vfo_freq - self.transverter_offset)
      self.pc2hermes[ 8] = vfo >> 24 & 0xff		# C0 index == 2, C1, C2, C3, C4: Rx freq, MSB in C1
      self.pc2hermes[ 9] = vfo >> 16 & 0xff
      self.pc2hermes[10] = vfo >>  8 & 0xff
      self.pc2hermes[11] = vfo       & 0xff
    if DEBUG > 1: print("Change freq Tx", tx_freq, "Rx", vfo_freq)
    QS.pc_to_hermes(self.pc2hermes)
    return tx_freq, vfo_freq
  def Freq2Phase(self, freq=None):		# Return the phase increment as calculated by the FPGA
    # This code attempts to duplicate the calculation of phase increment in the FPGA code.
    clock = ((int(self.conf.rx_udp_clock) + 24000) / 48000) * 48000		# this assumes the nominal clock is a multiple of 48kHz
    M2 = 2 ** 57 / clock
    M3 = 2 ** 24
    if freq is None:
      freqcomp = int(self.vfo_frequency - self.transverter_offset) * M2 + M3
    else:
      freqcomp = int(freq) * M2 + M3
    phase = (freqcomp / 2 ** 25) & 0xFFFFFFFF
    return phase
  def ReturnVfoFloat(self, freq=None):	# Return the accurate VFO as a float
    phase = self.Freq2Phase(freq)
    freq = float(phase) * self.conf.rx_udp_clock / 2.0**32
    return freq
  def ReturnFrequency(self):	# Return the current tuning and VFO frequency
    return None, None			# frequencies have not changed
  def RepeaterOffset(self, offset=None):	# Change frequency for repeater offset during Tx
    if offset is None:		# Return True if frequency change is complete
      if time.time() > self.repeater_time0 + self.repeater_delay:
        return True
    elif offset == 0:			# Change back to the original frequency
      if self.repeater_freq is not None:
        self.repeater_time0 = time.time()
        self.ChangeFrequency(self.repeater_freq, self.vfo_frequency, 'repeater')
        self.repeater_freq = None
    else:			# Shift to repeater input frequency
      self.repeater_freq = self.tx_frequency
      offset = int(offset * 1000)	# Convert kHz to Hz
      self.repeater_time0 = time.time()
      self.ChangeFrequency(self.tx_frequency + offset, self.vfo_frequency, 'repeater')
    return False
  def ChangeBand(self, band):
    # band is a string: "60", "40", "WWV", etc.
    BaseHardware.ChangeBand(self, band)
    self.band = band
    J16 = self.conf.Hermes_BandDict.get(band, 0)
    self.SetControlByte(0, 2, J16 << 1)		# C0 index == 0, C2[7:1]: user output
    self.SetTxLevel()
  def ChangeMode(self, mode):
    # mode is a string: "USB", "AM", etc.
    BaseHardware.ChangeMode(self, mode)
    self.mode = mode
    self.SetTxLevel()
  def OnButtonPTT(self, event):
    btn = event.GetEventObject()
    if btn.GetValue():
      QS.set_PTT(1)
    else:
      QS.set_PTT(0)
  def OnSpot(self, level):
    # level is -1 for Spot button Off; else the Spot level 0 to 1000.
    pass
  def VarDecimGetChoices(self):		# return text labels for the control
    return self.var_rates
  def VarDecimGetLabel(self):		# return a text label for the control
    return "Sample rate ksps"
  def VarDecimGetIndex(self):		# return the current index
    return self.var_index
  def VarDecimSet(self, index=None):		# set decimation, return sample rate
    if index is None:		# initial call to set rate before the call to open()
      rate = self.application.vardecim_set		# May be None or from different hardware
    else:
      rate = int(self.var_rates[index]) * 1000
    if rate == 48000:
      self.var_index = 0
    elif rate == 96000:
      self.var_index = 1
    elif rate == 192000:
      self.var_index = 2
    elif rate == 384000:
      self.var_index = 3
    else:
      self.var_index = 0
      rate = 48000
    self.pc2hermes[0] = self.var_index		# C0 index == 0, C1[1:0]: rate
    QS.pc_to_hermes(self.pc2hermes)
    if DEBUG: print ("Change sample rate to", rate)
    return rate
  def VarDecimRange(self):
    return (48000, 384000)
  def ChangeAGC(self, value):
    if value:
      self.pc2hermes[2] |= 0x10		# C0 index == 0, C3[4]: AGC enable
    else:
      self.pc2hermes[2] &= ~0x10
    QS.pc_to_hermes(self.pc2hermes)
    if DEBUG: print ("Change AGC to", value)
  def ChangeLNA(self, value):
    # value is -12 to +48
    if value < 20:
      self.pc2hermes[2] |= 0x08			# C0 index == 0, C3[3]: LNA +32 dB disable == 1
      value = 19 - value
    else:
      self.pc2hermes[2] &= ~0x08		# C0 index == 0, C3[3]: LNA +32 dB enable == 0
      value = 51 - value
    self.pc2hermes[4 * 10 + 3] = value			# C0 index == 0x1010, C4[4:0] LNA 0-32 dB gain
    QS.pc_to_hermes(self.pc2hermes)
    if DEBUG: print ("Change LNA to", value)
  def SetTxLevel(self):
    try:
      tx_level = self.conf.tx_level[self.band]
    except KeyError:
      tx_level = self.conf.tx_level.get(None, 127)	# The default
    if self.mode[0:3] in ('DGT', 'FDV'):			# Digital modes; change power by a percentage
      reduc = self.application.digital_tx_level
    else:
      reduc = self.application.tx_level
    level = 1.0 + tx_level * 0.0326
    level *= math.sqrt(reduc / 100.0)      # Convert from a power to an amplitude
    tx_level = int((level - 1.0) / 0.0326 + 0.5)
    if tx_level < 0:
      tx_level = 0
    elif tx_level > 255:
      tx_level = 255
    self.pc2hermes[4 * 9] = tx_level			# C0 index == 0x1001, C1[7:0] Tx level
    QS.pc_to_hermes(self.pc2hermes)
    if DEBUG: print("Change tx_level to", tx_level)
  def MultiRxCount(self, count):	# count == number of additional receivers besides the Tx/Rx receiver: 1, 2, 3
    # C0 index == 0, C4[5:3]: number of receivers 0b000 -> one receiver; C4[2] duplex on
    self.pc2hermes[3] = 0x04 | count << 3
    QS.pc_to_hermes(self.pc2hermes)
    if DEBUG: print("Change MultiRx count to", count)
  def MultiRxFrequency(self, index, vfo):	# index of multi rx receiver: 0, 1, 2, ...
    if DEBUG: print("Change MultiRx %d frequency to %d" % (index, vfo))
    index = index * 4 + 12		# index does not include first Tx/Rx receiver in C0 index == 1, 2
    self.pc2hermes[index    ] = vfo >> 24 & 0xff
    self.pc2hermes[index + 1] = vfo >> 16 & 0xff		# C1, C2, C3, C4: Rx freq, MSB in C1
    self.pc2hermes[index + 2] = vfo >>  8 & 0xff
    self.pc2hermes[index + 3] = vfo       & 0xff
    QS.pc_to_hermes(self.pc2hermes)
  def SetVNA(self, key_down=None, vna_start=None, vna_stop=None, vna_count=None, do_tx=False):
    if vna_count is not None:	# must be called first
      self.vna_count = vna_count
      if not self.vna_started:
        self.pc2hermes[4 * 9] = 63	# C0 index == 0x1001, C1[7:0] Tx level
        self.ChangeLNA(2)	# Preamp and Rx gain
    if vna_start is None:
      start = 0
      stop = 0
    else:	# Set the start and stop frequencies and the frequency change for each point
      # vna_start and vna_stop must be specified together
      self.pc2hermes[ 4] = vna_start >> 24 & 0xff	# C0 index == 1, C1, C2, C3, C4: Tx freq, MSB in C1
      self.pc2hermes[ 5] = vna_start >> 16 & 0xff	# used for vna starting frequency
      self.pc2hermes[ 6] = vna_start >>  8 & 0xff
      self.pc2hermes[ 7] = vna_start       & 0xff
      N = self.vna_count - 1
      ph_start = self.Freq2Phase(vna_start)	# Calculate using phases
      ph_stop = self.Freq2Phase(vna_stop)
      delta = (ph_stop - ph_start + N // 2) // N
      delta = int(float(delta) * self.conf.rx_udp_clock / 2.0**32 + 0.5)
      self.pc2hermes[ 8] = delta >> 24 & 0xff		# C0 index == 2, C1, C2, C3, C4: Rx freq, MSB in C1
      self.pc2hermes[ 9] = delta >> 16 & 0xff		# used for the frequency to add for each point
      self.pc2hermes[10] = delta >>  8 & 0xff
      self.pc2hermes[11] = delta       & 0xff
      self.pc2hermes[4 * 9 + 2] = (self.vna_count >> 8) & 0xff	# C0 index == 0x1001, C3
      self.pc2hermes[4 * 9 + 3] = self.vna_count & 0xff		# C0 index == 0x1001, C4
      QS.pc_to_hermes(self.pc2hermes)
      start = self.ReturnVfoFloat(vna_start)
      phase = ph_start + self.Freq2Phase(delta) * N
      stop = float(phase) * self.conf.rx_udp_clock / 2.0**32
      start = int(start + 0.5)
      stop = int(stop + 0.5)
      if DEBUG: print ("Change VNA start", vna_start, start, "stop", vna_stop, stop)
    if key_down is None:
      pass
    elif key_down:
      if not self.vna_started:
        self.vna_started = True
        self.SetControlByte(9, 2, 0x80)		# turn on VNA mode
      QS.set_PTT(1)
    else:
      QS.set_PTT(0)
    return start, stop	# Return actual frequencies after all phase rounding
