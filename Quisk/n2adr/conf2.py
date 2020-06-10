# This is a second config file that I use to test various hardware configurations.

from n2adr.quisk_conf import n2adr_sound_pc_capt, n2adr_sound_pc_play, n2adr_sound_usb_play, n2adr_sound_usb_mic
from n2adr.quisk_conf import latency_millisecs, data_poll_usec, favorites_file_path

settings_file_path = "../quisk_settings.json"

name_of_sound_play = n2adr_sound_usb_play
name_of_sound_capt = n2adr_sound_pc_capt

sdriq_name = "/dev/ttyUSB0"		# Name of the SDR-IQ device to open

default_screen = 'WFall'
waterfall_y_scale = 80
waterfall_y_zero  = 40
waterfall_graph_y_scale = 40
waterfall_graph_y_zero = 90
waterfall_graph_size = 160
display_fraction = 1.00			# The edges of the full bandwidth are not valid

