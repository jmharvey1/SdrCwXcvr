# These are the configuration parameters for receiving the
# 10.7 MHz IF output of the AOR AR8600 receiver with the
# SDR-IQ by RfSpace.  This results in a 100 kHz to 3 GHz
# wide range receiver with pan adapter.

# Please do not change this sample file.
# Instead copy it to your own .quisk_conf.py and make changes there.
# See quisk_conf_defaults.py for more information.

# Use this hardware module to control the AR8600 and SDR-IQ
import quisk_hardware_sdr8600 as quisk_hardware

# Start in FM mode
default_mode = 'FM'

use_sdriq = 1					# Use the SDR-IQ
#sdriq_name = "/dev/ft2450"		# Name of the SDR-IQ device to open
sdriq_name = "/dev/ttyUSB2"		# Name of the SDR-IQ device to open
sdriq_clock = 66666667.0		# actual sample rate (66666667 nominal)
sdriq_decimation = 1250			# Must be 360, 500, 600, or 1250
sample_rate = int(float(sdriq_clock) / sdriq_decimation + 0.5)	# Don't change this
name_of_sound_capt = ""			# We do not capture from the soundcard
name_of_sound_play = "hw:0"		# Play back on this soundcard
# Note: For the SDR-IQ, playback is stereo at 48000 Hertz.
channel_i = 0					# Soundcard index of left channel
channel_q = 1					# Soundcard index of right channel
display_fraction = 0.85			# The edges of the full bandwidth are not valid

