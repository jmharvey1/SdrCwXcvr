# This is a sample quisk_conf.py configuration file for Microsoft Windows.

# For Windows, your default config file name is "My Documents/quisk_conf.py",
# but you can use a different config file by using -c or --config.  Quisk creates
# an initial default config file if there is none.  To control Quisk, edit
# "My Documents/quisk_conf.py" using any text editor; for example WordPad (not Notepad).

# In Windows you can see what sound devices you have, and you can set the Primary
# Device for capture and playback by using Control Panel/Sounds and Audio Devices.
# If you have only one sound device, it should be set as "Primary".  If you have
# several, find the names by using Control Panel/Sounds and Audio Devices; for
# example, you may have "SoundMAX HD Audio" in the list for "Sound playback" and
# "Sound recording".  To specify this device for capture (recording) or playback,
# enter a unique part of its name using exact upper/lower case.  For example:
#       name_of_sound_capture = "SoundMAX"
#       name_of_sound_play = "SoundMAX"

# There are many possible options for your config file.  Copy the ones you want
# from the master file quisk_conf_defaults.py (but don't change the master file).
# The master config file is located in the site-packages/quisk folder for Python 2.7.

# This file is Python code and the comment character is "#".  To ignore a line,
# start it with "#".  To un-ignore a line, remove the "#".  Generally you must start
# lines in column one (the left edge) except for logic blocks.


sample_rate = 48000				# ADC hardware sample rate in Hertz
name_of_sound_capt = "Primary"			# Name of soundcard capture hardware device.
name_of_sound_play = "Primary"			# Use the same device for play back.
latency_millisecs = 150				# latency time in milliseconds

# Select the default screen when Quisk starts:
default_screen = 'Graph'
#default_screen = 'WFall'

# If you use hardware with a fixed VFO (crystal controlled SoftRock) un-comment the following:
# import quisk_hardware_fixed as quisk_hardware
# fixed_vfo_freq = 7056000

# If you use an SDR-IQ for capture, first install the SpectraView software
# that came with the SDR-IQ.  This will install the USB driver.  Then set these parameters:
# import quisk_hardware_sdriq as quisk_hardware		# Use different hardware file
# use_sdriq = 1						# Capture device is the SDR-IQ
# sdriq_name = "SDR-IQ"				# Name of the SDR-IQ device to open
# sdriq_clock = 66666667.0			# actual sample rate (66666667 nominal)
# sdriq_decimation = 500			# Must be 360, 500, 600, or 1250
# sample_rate = int(float(sdriq_clock) / sdriq_decimation + 0.5)	# Don't change this
# name_of_sound_capt = ""			# We do not capture from the soundcard
# playback_rate = 48000				# Radio sound play rate, default 48000
# display_fraction = 0.85			# The edges of the full bandwidth are not valid
