import sys

settings_file_path = "../quisk_settings.json"

if sys.platform == "win32":
  digital_output_name = 'CABLE-A Input'
elif 0:
  digital_input_name = 'pulse'
  digital_output_name ='' 
else:
  digital_output_name = 'hw:Loopback,0'

name_of_sound_play = ''
microphone_name = ''
