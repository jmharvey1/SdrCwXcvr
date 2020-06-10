# This is a sample quisk_conf.py configuration file for a SoftRock Rx/Tx Ensemble or
# other SoftRock that has both transmit and receive capability.  You need two sound
# cards, a high quality card to capture radio samples and play microphone sound; and
# a lower quality card to play radio sound and capture the microphone.

# Please do not change this sample file.
# Instead copy it to your own config file and make changes there.
# See quisk_conf_defaults.py for more information.

from softrock import hardware_usb as quisk_hardware
from softrock import widgets_tx   as quisk_widgets

# In Linux, ALSA soundcards have these names.  The "hw" devices are the raw
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

softrock_model = "RxTxEnsemble"
#si570_direct_control = True
#si570_i2c_address = 0x70

# If you have a SoftRock with a key jack, and you want to monitor the hardware key state for
# CW operation, enter a key poll time in milliseconds and a semi-break-in hang time in seconds.
# Do not press the PTT button.  CW has its own timer to control transmit.
#key_poll_msec = 5
#key_hang_time = 0.7

# Radio samples and audio:
#sample_rate = 96000					# ADC hardware sample rate
#name_of_sound_capt = "hw:0"			# Name of soundcard capture device for radio samples.
playback_rate = 48000					# radio sound playback rate
#name_of_sound_play = "hw:1"			# Name of soundcard playback device for radio audio.  Must be 48 ksps.

# Microphone:
#microphone_name = name_of_sound_play	# Name of microphone capture device
#name_of_mic_play = name_of_sound_capt	# Name of play device if CW or mic I/Q is sent to a sound card
mic_playback_rate = sample_rate			# Playback rate for microphone
#mic_out_volume = 0.6					# Transmit sound output volume (after all processing) as a fraction 0.0 to 1.0

repeater_delay = 0.25					# delay for changing repeater frequency in seconds
