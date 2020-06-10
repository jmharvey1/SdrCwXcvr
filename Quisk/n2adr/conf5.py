import sys

settings_file_path = "../quisk_settings.json"

#hamlib_port = 4575		# Standard port for Quisk control.  Set the port in Hamlib to 4575 too.
hamlib_port = 4532		# Default port for rig 2.  Use this if you can not set the Hamlib port.
if sys.platform == "win32":
  pass
elif 0:
  digital_input_name = 'pulse'
  digital_output_name ='' 
else:
  digital_input_name = 'hw:Loopback,0'
  digital_output_name = digital_input_name

