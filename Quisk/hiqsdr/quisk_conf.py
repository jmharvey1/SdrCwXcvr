# This is a sample config file for the N2ADR 2010 transceiver hardware and for the
# improved version HiQSDR.  If you use the HiQSDR you should upgrade your firmware
# to version 1.1.

from hiqsdr import quisk_hardware

add_imd_button = 1
add_fdx_button = 1
latency_millisecs = 50
# tx_level = {None:120, '60':52}	#  Use this to change your transmit level.

#use_rx_udp = 1					# Use this for the N2ADR 2010 hardware
use_rx_udp = 2					# Use this for the HiQSDR
rx_udp_ip = "192.168.2.196"		# Sample source IP address
rx_udp_port = 0xBC77			# Sample source UDP port
rx_udp_clock = 122880000  		# ADC sample rate in Hertz
rx_udp_decimation = 8 * 8 * 8	# Decimation from clock to UDP sample rate
sample_rate = int(float(rx_udp_clock) / rx_udp_decimation + 0.5)	# Don't change this
name_of_sound_capt = ""			# We do not capture from the soundcard
name_of_sound_play = "hw:0"
data_poll_usec = 10000
playback_rate = 48000

microphone_name = "hw:1"
tx_ip = rx_udp_ip
key_method = ""		# Use internal method
tx_audio_port = 0xBC79
mic_out_volume = 1.0

