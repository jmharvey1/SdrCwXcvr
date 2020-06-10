# This is a sample config file for the Hermes-Lite.  Do not modify this file.

from hermes import quisk_hardware
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
tx_level = {None:255, '60':255}		# Adjust your power for each band

# Control the J16 connector according to the band.  J16 is C0 index 0, C2[7:1].  If the band is not here, the default is 0x00.
# This value is written to bits C2[7:1].  That is, it is left shifted by one bit and written to byte C2.
Hermes_BandDict = {'160':0b0000001, '80':0b0000010, '60':0b0000100, '40':0b0001000, '30':0b0010000, '20':0b0100000, '15':0b1000000}
