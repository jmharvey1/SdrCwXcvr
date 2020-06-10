# This is the config file from my shack, which controls various hardware.
# The files to control my 2010 transceiver and for the improved version HiQSDR
# are in the package directory HiQSDR.

favorites_file_path = "../quisk_favorites.txt"
settings_file_path  = "../quisk_settings.json"

n2adr_sound_usb_mic = 'alsa:USB Sound Device'
microphone_name = n2adr_sound_usb_mic
mixer_settings = [		# These are for CM106 like sound device
    (microphone_name, 16, 1),		# PCM capture from line
    (microphone_name, 14, 0),		# PCM capture switch
    (microphone_name, 11, 1),		# line capture switch
    (microphone_name, 12, 0.70),	# line capture volume
    (microphone_name,  3, 0),		# mic playback switch
    (microphone_name,  9, 0),		# mic capture switch
  ]
