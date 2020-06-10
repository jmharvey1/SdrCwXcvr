# This is a sample config file for the Hermes-Lite.  Do not modify this file.
# This example file uses the lower bits of J16 for the band, and the highest bit for a Spot indicator.

from hermes.quisk_hardware import Hardware as BaseHardware	# We have our own hardware file defined below
from hermes import quisk_widgets

use_rx_udp = 10					# Use this for Hermes-Lite
rx_udp_clock = 73728000			# The clock is 73.728 or 61.440 megahertz.  Adjust slightly for actual frequency.
rx_udp_ip = ""					# Sample source IP address "" for DHCP
rx_udp_port = 1024				# Sample source UDP port; must be 1024
data_poll_usec = 10000		    # poll time in microseconds

use_sidetone = 1				# Use the Quisk sidetone for CW

sample_rate = 96000
name_of_sound_capt = ""			# We do not capture from the soundcard

name_of_sound_play = 'hw:1'		# Play radio sound here.  Linux.
microphone_name = 'hw:1'		# The microphone is here.

#name_of_sound_play = 'Primary'	# Play radio sound here. Windows.
#microphone_name = 'Primary'	# The microphone is here.

graph_y_scale = 100
graph_y_zero  = 100
playback_rate = 48000
add_imd_button = 1
add_fdx_button = 1
tx_level = {None:255, '60':110}		# Adjust your power for each band

# Control the J16 connector according to the band.  J16 is C0 index 0, C2[7:1].  If the band is not here, the default is 0x00.
# This value is written to bits C2[7:1].  That is, it is left shifted by one bit and written to byte C2.
Hermes_BandDict = {'160':0b0000001, '80':0b0000010, '60':0b0000011, '40':0b0000100, '30':0b0000101, '20':0b0000110, '15':0b0000111}


# Define the Hardware class in this config file instead of a separate file.

class Hardware(BaseHardware):
  def __init__(self, app, conf):
    BaseHardware.__init__(self, app, conf)
    self.usingSpot = False		# Use bit C2[7] as the Spot indicator
  def ChangeBand(self, band):
    # band is a string: "60", "40", "WWV", etc.
    # The call to BaseHardware will set C2 according to the Hermes_BandDict{}
    ret = BaseHardware.ChangeBand(self, band)
    if self.usingSpot:
      byte = self.GetControlByte(0, 2)		# C0 index == 0, C2: user output
      byte |= 0b10000000
      self.SetControlByte(0, 2, byte)
    return ret
  def OnSpot(self, level):
    # level is -1 for Spot button Off; else the Spot level 0 to 1000.
    ret = BaseHardware.OnSpot(self, level)
    if level >= 0 and not self.usingSpot:		# Spot was turned on
      byte = self.GetControlByte(0, 2)
      byte |= 0b10000000
      self.SetControlByte(0, 2, byte)
      self.usingSpot = True
    elif level < 0 and self.usingSpot:			# Spot was turned off
      byte = self.GetControlByte(0, 2)
      byte &= 0b01111111
      self.SetControlByte(0, 2, byte)
      self.usingSpot = False
    return ret
