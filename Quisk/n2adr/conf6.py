# This is a second config file to test the softrock radios.

from n2adr.quisk_conf import n2adr_sound_pc_capt, n2adr_sound_pc_play, n2adr_sound_usb_play, n2adr_sound_usb_mic
from n2adr.quisk_conf import latency_millisecs, data_poll_usec, favorites_file_path
from n2adr.quisk_conf import mixer_settings

settings_file_path = "../quisk_settings.json"

name_of_sound_capt = n2adr_sound_pc_capt
name_of_sound_play = n2adr_sound_usb_play

default_screen = 'WFall'
waterfall_y_scale = 80
waterfall_y_zero  = 40
waterfall_graph_y_scale = 40
waterfall_graph_y_zero = 90
waterfall_graph_size = 160
display_fraction = 1.00

sample_rate = 48000	
playback_rate = 48000
key_poll_msec = 5

do_repeater_offset = True
#bandTransverterOffset = {'40' : 300000}

# Microphone capture and playback:
microphone_name = n2adr_sound_usb_mic
name_of_mic_play = n2adr_sound_pc_play
mic_playback_rate = sample_rate
mic_out_volume = 0.6
