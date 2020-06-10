# Instead copy it to your own .quisk_conf.py and make changes there.
# See quisk_conf_defaults.py for more information.

# The default hardware module was already imported.  Import a different one here.
#import quisk_hardware_fixed as quisk_hardware
import quisk_hardware as quisk_hardware
#from softrock import hardware_usb as quisk_hardware
from softrock import widgets_tx   as quisk_widgets

# In ALSA, soundcards have these names.  The "hw" devices are the raw
# hardware devices, and should be used for soundcard capture.
#name_of_sound_capt = "hw:0"		#JMH 2019 - internal sound card - work but not stereo/I-Q input; msg1: Available formats: *S32 S16 
name_of_sound_capt = "hw:1,0"		#JMH 2019 - external sound card; JMH the one that I use; msg1: Available formats: *S24_3LE S16 
#name_of_sound_capt = "plughw"       #JMH 2019 - internal sound card - work but not stereo/I-Q input; msg1: Available formats: *S32 U32 S24 U24 S24_3LE S16 U16  
#name_of_sound_capt = "plughw:1"    ##JMH 2019 - This Works as well as the "hw:1,0" method; msg1: Available formats: *S32 U32 S24 U24 S24_3LE S16 U16 
#name_of_sound_capt = "default"      #JMH 2019 - Used external sound card but not stereo/I-Q & samplerate was 48000 ; msg1: Available formats: *S32 S24 S24_3LE S16 
#name_of_sound_capt = "pulse:tunnel.raspberrypi.local.alsa_input.usb-VIA_Technologies_Inc._VIA_USB_Dongle-00.analog-stereo"
#name_of_sound_capt = "pulse:alsa_input.usb-VIA_Technologies_Inc._VIA_USB_Dongle-00.analog-stereo"   #JMH 2019 - works but same as "name_of_sound_capt = "pulse""
#name_of_sound_capt = "pulse"  #JMH 2019 - works but is not IQ/stero input and sample rate is 48000 regardless of quisk declared samplerate; msg1: ""
#name_of_sound_capt="portaudio:(hw:1,0)" #JMH 2019 - This Works as well as the "hw:1,0"; method msg1: PortAudio device VIA USB Dongle: Audio (hw:1,0)



#name_of_sound_play = "hw:1,0"
#name_of_sound_play = "pcm.jack" #JMH added 20170408
name_of_sound_play = "pulse" #JMH added 20170408 - this is the one i use on linux mint while also running FLDIGI
#name_of_sound_play="portaudio:(hw:0,0)" JMH 20190806 quisk will work, but it would not create/register an entry on the PulseAudio Volume control so could not link the output of quisk to fldigi

softrock_model = "KW4KD"				# Fixed frequency SoftRock
sample_rate = 96000#48000#  			# ADC hardware sample rate in Hertz

channel_i = 0						# Soundcard index of in-phase channel:  0, 1, 2, ...
channel_q = 1						# Soundcard index of quadrature channel:  0, 1, 2, ...
# Thanks to Franco Spinelli for this fix:
## channel_delay		Rx channel delay, integer
# The H101 hardware using the PCM2904 chip has a one-sample delay between
# channels, which must be fixed in software.  If you have this problem,
# change channel_delay to either channel_i or channel_q.  Use -1 for no delay.
#channel_delay = -1  # Default - See quisk_conf_defaults.py
#channel_delay = 0
#channel_delay = 1

sdriq_clock = 66666667.0		# Not really needed for SdriqHardware but included here to keep 
					# ./sdriqpkg/quisk_hardware.py happy 

# This is a list of mixer settings.  It only works for Linux; it has no effect in Windows.
# Use "amixer -c 1 contents" to get a list of mixer controls and their numid's for
# card 1 (or "-c 0" for card 0).  Then make a list of (device_name, numid, value)
# for each control you need to set.  For a decimal fraction, use a Python float; for example,
# use "1.0", not the integer "1".
### Enermax AP001 24-bit 96KHz USB settings @ 96KHz
channel_i = 0						# Soundcard index of in-phase channel:  0, 1, 2, ...
channel_q = 1
channel_delay = 1
mixer_settings = [
("hw:1", 4, 0),     #numid=4,iface=MIXER,name='Mic Playback Switch'
                    #  ; type=BOOLEAN,access=rw------,values=1
                    #  : values 0= mute;  1 = not muted
#("hw:1", 5, 0),     #numid=5,iface=MIXER,name='Mic Playback Volume'
                    #  ; type=INTEGER,access=rw---R--,values=1,min=0,max=20,step=0
                    #  : values=0
                    #  | dBminmax-min=0.00dB,max=30.00dB
("hw:1", 8, 1),     #numid=8,iface=MIXER,name='Mic Capture Switch'
                    #  ; type=BOOLEAN,access=rw------,values=1
                    #  : values 0= mute;  1 = not muted
("hw:1", 9, 4),     #numid=9,iface=MIXER,name='Mic Capture Volume'          ##JMH use this value to set the QUISK Smeter reading while connected to a dummy load
                    #  ; type=INTEGER,access=rw---R--,values=2,min=0,max=20,step=0
                    #  : values=0,0
                    #  | dBminmax-min=0.00dB,max=30.00dB
("hw:1", 3, 0),     #numid=3,iface=MIXER,name='Auto Gain Control'
                    #  ; type=BOOLEAN,access=rw------,values=1
                    #  : values 0= off;  1 = on
("hw:1", 6, 1),     #numid=6,iface=MIXER,name='Speaker Playback Switch'
                    #  ; type=BOOLEAN,access=rw------,values=1
                    #  : values 0= mute;  1 = not muted
("hw:1", 7, 40)     #numid=7,iface=MIXER,name='Speaker Playback Volume'
                    #  ; type=INTEGER,access=rw---R--,values=2,min=0,max=50,step=0
                    #  : values=0,0
                    #  | dBminmax-min=-50.00dB,max=0.00dB
]

###SD-AUD20101 "SYBA"
##mixer_settings = [
##("hw:1", 3, 1),		#numid=3,iface=MIXER,name='Mic Playback Switch'
##			#  ; type=BOOLEAN,access=rw------,values=1
##			#  : values=on
##("hw:1", 4, 37),	#numid=4,iface=MIXER,name='Mic Playback Volume'
##			#  ; type=INTEGER,access=rw---R--,values=2,min=0,max=37,step=0
##			#  : values=37,37
##			#  | dBminmax-min=-15.00dB,max=22.00dB
##("hw:1", 7, 1),		#numid=7,iface=MIXER,name='Mic Capture Switch'
##			#  ; type=BOOLEAN,access=rw------,values=1
##			#  : values=on
##("hw:1", 8, 0),		#numid=8,iface=MIXER,name='Mic Capture Volume'
##			#  ; type=INTEGER,access=rw---R--,values=2,min=0,max=30,step=0
##			#  : values=0,0
##			#  | dBminmax-min=0.00dB,max=30.00dB
##("hw:1", 5, 1),		#numid=5,iface=MIXER,name='Speaker Playback Switch'
##			#  ; type=BOOLEAN,access=rw------,values=1
##			#  : values=on
##("hw:1", 6, 45)	#numid=6,iface=MIXER,name='Speaker Playback Volume'
##			#  ; type=INTEGER,access=rw---R--,values=2,min=0,max=45,step=0
##			#  : values=45,45
##			#  | dBminmax-min=-45.00dB,max=0.00dB
##]


###USB Type CM106
##mixer_settings = [
##("hw:1", 16, 1),   #numid=16,iface=MIXER,name='PCM Capture Source'
##                    #; type=ENUMERATED,access=rw------,values=1,items=4
##                    #; Item #0 'Mic'
##                    #; Item #1 'Line'
##                    #  ; Item #2 'IEC958 In'
##                    #; Item #3 'Mixer'
##                    #  : values=0
##("hw:1", 14, 1),   #numid=14,iface=MIXER,name='PCM Capture Switch'
##                      #; type=BOOLEAN,access=rw------,values=1
##                    #  : values=on
##("hw:1", 5, 1),    #numid=5,iface=MIXER,name='Line Playback Switch'
##                    #  ; type=BOOLEAN,access=rw------,values=1
##                    #  : values=on
##("hw:1", 11, 1),   #numid=11,iface=MIXER,name='Line Capture Switch'
##                    #  ; type=BOOLEAN,access=rw------,values=1
##                    #  : values=off
##("hw:1", 3, 1),    #numid=3,iface=MIXER,name='Mic Playback Switch'
##                    #  ; type=BOOLEAN,access=rw------,values=1
##                    #  : values=on
##("hw:1", 9, 1),    #numid=9,iface=MIXER,name='Mic Capture Switch'
##                    #  ; type=BOOLEAN,access=rw------,values=1
##                    #  : values=on
##("hw:1", 13, 1),  #numid=13,iface=MIXER,name='IEC958 In Capture Switch'
##                    #  ; type=BOOLEAN,access=rw------,values=1
##                    # : values=on
##("hw:1", 7, 1)    #numid=7,iface=MIXER,name='Speaker Playback Switch'
##                    #  ; type=BOOLEAN,access=rw------,values=1
##                    #  : values=on
##]

################ Options
## max_record_minutes       Max minutes record time, number
# Quisk has record and playback buttons to save radio sound.  If there is no more room for
# sound, the old sound is discarded and the most recent sound is retained.  This controls
# the maximum time of sound storage in minutes for this recorded audio, and also the record
# time for the Tx Audio test screen.  If you want to transmit recorded sound, then mic_sample_rate
# must equal playback_rate and both must be 48000.
max_record_minutes = 15.00
file_name_audio = "/home/jim/tmp/qaudio.wav"

## split_rxtx           Split-mode audio, integer choice
# Quisk can operate in Split mode and can receive both the Tx and Rx frequency signals.  This option
# controls where the sound goes.  You may need to reverse 1 or 2 depending on your wiring.
#split_rxtx = 1		# Play both, the higher frequency on real
split_rxtx = 2		# Play both, the lower frequency on real
#split_rxtx = 3		# Play receive only
#split_rxtx = 4		# Play transmit only

# Quisk can save radio sound and samples to files, and can play recorded sound.  There is a button on the
# Config/Config screen to set the file names.  You can set the initial names with these variables:
file_name_audio = ""
#file_name_audio = "/home/jim/tmp/qaudio.wav"

# This is the CW tone frequency in Hertz.
cwTone = 750

## freq_spacing         Frequency rounding spacing, integer
# If freq_spacing is not zero, frequencies are rounded to the freq_base plus the
# freq_spacing; frequency = freq_base + N * freq_spacing.  This is useful at
# VHF and higher when Quisk is used with a transverter.
freq_spacing = 25

################ Remote
# DX cluster telent login data, thanks to DJ4CM.  Must have station_display_lines > 0.
## dxClHost             Dx cluster host name, text
# The Dx cluster options log into a Dx cluster server, and put station information
# on the station window under the graph and waterfall screens.
# dxClHost is the telnet host name.
#dxClHost = 'w3lpl.net'  #set port number to = 7373
#dxClHost = 'dxc.wc2l.com' #set port number to = 0; use skimmer filter to restrict spotter stations
#dxClHost = 'dxc-us.ab5k.net' 
#dxClHost = 'dxc.ab5k.net'
#dxClHost = 'dx.k3lr.com' #set port number to = 0; that connects but did not return any results
#dxClHost = 'dxc.nc7j.com'  #set port number to = 23; use skimmer filter to restrict spotter stations
dxClHost = 'w4ax.com'   #set port number to = 44000; Station is located at Ball Ground Ga; 72 miles S.E. of Hixson, TN; monitors 20, 30, 40 mtrs
dxClPort = 44000
#dxClHost = 'mackmc.dnsalias.com'#set port number to = 23; Station is located at Alpharetta, GA (EM74uc); 89 miles S.E. of Hixson, TN; have not been able to get this one work
#dxClHost = 'kq8m.no-ip.org' # use port setting 3607 See Web Site http://www.kq8m.com/gpage2.html; use port 7300 and use filter without spotter state restriction
#dxClHost = 'k4zr.no-ip.org'
#dxClHost = 'DXSPOTS.COM' # See Web Site http://www.dxspots.com/ filter does not work, may be using a different set of commands

## dxClPort             Dx cluster port number, integer
# The Dx cluster options log into a Dx cluster server, and put station information
# on the station window under the graph and waterfall screens.
# dxClPort is the telnet port number.
#dxClPort = 7373
#dxClPort = 7300
#dxClPort = 23
#dxClPort = 0

#Configure Optional 2nd Dx cluster telnet session
dxClHost2 = 'dxc.wc2l.com'
dxClPort2 = 0
dxClFltrCmd2 = 'Set Dx Filter (skimmer and unique > 1 and SpotterState=[TN, NC, SC, GA, AL] and band=[80, 40, 30, 20] and comment like *CW*)'

## user_call_sign       Call sign for Dx cluster, text
# The Dx cluster options log into a Dx cluster server, and put station information
# on the station window under the graph and waterfall screens.
# user_call_sign is your call sign which may be needed for login.
user_call_sign = 'KW4KD' # Set Dx Filter skimmer and unique > 2'

## dxClPassword         Password for Dx cluster, text
# The Dx cluster options log into a Dx cluster server, and put station information
# on the station window under the graph and waterfall screens.
# dxClPassword  is the telnet password for the server.
#dxClPassword = 'getsomedx'
dxClPassword = ''

#dxClFltrCmd = 'Set Dx Filter (skimmer and unique > 2 AND spottercont=na)'
#dxClFltrCmd = 'Set Dx Filter (skimmer and unique > 1 and SpotterState=[TN, NC, SC, GA, AL] and band=[80, 40, 30, 20] and comment=*CW*)'
#dxClFltrCmd = 'Set Dx Filter (skimmer and band=[80, 40, 30, 20] and comment=*CW*)'
dxClFltrCmd = 'sh/dx 10m' ##'ValidationLevel=0'
## dxClExpireTime       Dx cluster expire minutes, integer
# The Dx cluster options log into a Dx cluster server, and put station information
# on the station window under the graph and waterfall screens.
# dxClExpireTime is the time in minutes until DX Cluster entries are removed.
dxClExpireTime = 1
#data_poll_usec = 500
# Next two entries support external manual CW keying
key_poll_msec = 5  
key_hang_time = 0.7
# SSmicro USB Ids
usb_vendor_id = 0x2341
usb_product_id =0x8037 

#waterfall_palette = 'B'
waterfall_palette = 'C'
InitTalk = False
HrdwrTalk = False
TelnetTalk = False



