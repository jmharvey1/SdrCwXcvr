# These are the configuration parameters for Quisk using the
# SDR-IQ by RfSpace as the capture device.

# Please do not change this sample file.
# Instead copy it to your own .quisk_conf.py and make changes there.
# See quisk_conf_defaults.py for more information.

from sdriqpkg import quisk_hardware		# Use different hardware file

# In ALSA, soundcards have these names:
#name_of_sound_play = "hw:0"
#name_of_sound_play = "hw:1"
#name_of_sound_play = "plughw"
#name_of_sound_play = "plughw:1"
#name_of_sound_play = "default"

# Pulseaudio support added by Philip G. Lee.  Many thanks!
# For PulseAudio support, use the name "pulse" and connect the streams
# to your hardware devices using a program like pavucontrol
#name_of_sound_capt = "pulse"

use_sdriq = 1					# Use the SDR-IQ
#sdriq_name = "/dev/ft2450"		# Name of the SDR-IQ device to open
sdriq_name = "/dev/ttyUSB2"		# Name of the SDR-IQ device to open
sdriq_clock = 66666667.0		# actual sample rate (66666667 nominal)
sdriq_decimation = 1250			# Must be 360, 500, 600, or 1250
sample_rate = int(float(sdriq_clock) / sdriq_decimation + 0.5)	# Don't change this
name_of_sound_capt = ""			# We do not capture from the soundcard
name_of_sound_play = "hw:0"		# Play back on this soundcard
playback_rate = 48000			# Radio sound play rate
channel_i = 0					# Soundcard index of left channel
channel_q = 1					# Soundcard index of right channel
display_fraction = 0.85			# The edges of the full bandwidth are not valid

