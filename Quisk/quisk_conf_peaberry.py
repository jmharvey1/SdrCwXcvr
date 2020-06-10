from softrock import hardware_usb_new as quisk_hardware
from softrock import widgets_tx as quisk_widgets

si570_direct_control = True
si570_xtal_freq = 114211833

sample_rate = 48000
playback_rate = 48000
name_of_sound_capt = "hw:1,0"
name_of_sound_play = "plughw:0,0"
channel_i = 0
channel_q = 1

usb_vendor_id = 0x16c0
usb_product_id = 0x05dc
