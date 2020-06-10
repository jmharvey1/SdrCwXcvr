# This is a sample quisk_conf.py configuration file for a SoftRock Rx Ensemble II or
# other SoftRock that has receive only capability.  No Tx.  The single sound card
# is used for radio sample capture, and playing radio sound.  Of course, if you have
# two sound cards, you can play radio sound on the other one, preferably at 48000 sps.

# Please do not change this sample file.
# Instead copy it to your own config file and make changes there.
# See quisk_conf_defaults.py for more information.

from softrock import hardware_usb as quisk_hardware
from softrock import widgets_tx   as quisk_widgets

del quisk_hardware.Hardware.OnSpot			# Remove this transmit feature
del quisk_hardware.Hardware.OnButtonPTT		# Remove this transmit feature

# In ALSA, soundcards have these names.  The "hw" devices are the raw
# hardware devices, and should be used for soundcard capture.
#name_of_sound_capt = "hw:0"
#name_of_sound_capt = "hw:1"
#name_of_sound_capt = "plughw"
#name_of_sound_capt = "plughw:1"
#name_of_sound_capt = "default"

# Pulseaudio support added by Philip G. Lee.  Many thanks!
# For PulseAudio support, use the name "pulse" and connect the streams
# to your hardware devices using a program like pavucontrol
#name_of_sound_capt = "pulse"

softrock_model = "RxEnsemble2"
#si570_direct_control = False
#si570_i2c_address = 0x70

#sample_rate = 48000							# ADC hardware sample rate in Hertz
#name_of_sound_capt = "hw:0"					# Name of soundcard capture hardware device.
#name_of_sound_play = name_of_sound_capt		# Use the same device for radio sound play back
# There are no microphone devices.

