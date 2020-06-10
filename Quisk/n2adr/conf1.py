from n2adr.quisk_conf import n2adr_sound_pc_capt, n2adr_sound_pc_play, n2adr_sound_usb_play, n2adr_sound_usb_mic, favorites_file_path

settings_file_path = "../quisk_settings.json"

name_of_sound_play = n2adr_sound_usb_play
microphone_name = n2adr_sound_usb_mic
digital_input_name = ""
digital_output_name = ""

use_rx_udp = 1				# Get ADC samples from UDP
rx_udp_ip = "192.168.1.196"		# Sample source IP address
rx_udp_port = 0xBC77			# Sample source UDP port
graph_width = 0.80
