from __future__ import absolute_import
from __future__ import division
#  ** This is the file quisk_conf_defaults.py which contains defaults for Quisk. **
#  
# Please do not change this configuration file quisk_conf_defaults.py.
# Instead copy one of the other quisk_conf_*.py files to your own
# configuration file and make changes there.
#
# For Linux, your standard configuration file name is .quisk_conf.py in your home directory.
#
# For Windows, your standard comfiguration file name is quisk_conf.py in your Documents folder.
#
# You can specify a different configuration file with the -c or --config command line argument.
#
# Check the config screen to make sure that the correct configuration file is in use.
#
#
# PLEASE DO **NOT** COPY THIS FILE AND USE IT AS A START FOR YOUR CONFIGURATION FILE!
# YOUR CONFIGURATION FILE SHOULD ONLY HAVE LINES THAT DIFFER FROM THIS FILE.  QUISK
# IMPORTS THIS FILE FIRST, AND THEN YOUR CONFIG FILE OVERWRITES A FEW ITEMS SUCH AS
# SOUND CARD NAMES.
#
# Quisk imports quisk_conf_defaults.py to set its configuration.
# If you have a configuration file, it then overwrites the defaults
# with your parameters.
#
# Quisk uses a hardware file to control your transceiver and optionally other station hardware.
# Your config file specifies the hardware file to use.  Quisk comes with several hardware
# files, and you can write your own hardware file in Python to do anything you want.
#
# Quisk has a custom decimation scheme for each sample rate.  The allowable sample rates
# are the four SDR-IQ rates plus 24, 48, 96, 192, 240, 384, 480, and 960 ksps.  Other rates
# can be added.

import sys
import wx

# Import the default Hardware module.  You can import a different module in
# your configuration file.
import quisk_hardware_model as quisk_hardware

# Module for additional widgets (advanced usage).  See n2adr/quisk_widgets.py for an example.
# import n2adr.quisk_widgets as quisk_widgets
quisk_widgets = None




################ Receivers SoftRock USB, Devices controlled by USB that capture samples from a sound card, and (for Tx) play samples to a sound card
## hardware_file_name		Hardware file path, rfile
# This is the file that contains the control logic for each radio.
#hardware_file_name = 'softrock/hardware_usb.py'

## widgets_file_name			Widget file path, rfile
# This optional file adds additional controls for the radio.
#widgets_file_name = 'softrock/widgets_tx.py'

use_sdriq = 0						# Get ADC samples from SDR-IQ is not used
use_rx_udp = 0						# Get ADC samples from UDP is not used
use_soapy = 0						# Get ADC samples from SoapySDR is not used
sample_rate = 48000					# name_of_sound_capt hardware sample rate in Hertz
if sys.platform == "win32":
  name_of_sound_capt = "Primary"
  name_of_sound_play = "Primary"
elif sys.platform == "darwin":
  name_of_sound_capt = "pulse"
  name_of_sound_play = "pulse"
else:
  name_of_sound_capt = "hw:0"		# Name of soundcard capture hardware device.
  name_of_sound_play = "hw:0"
channel_i = 0						# Soundcard index of in-phase channel:  0, 1, 2, ...
channel_q = 1						# Soundcard index of quadrature channel:  0, 1, 2, ...

## usb_vendor_id			Vendor ID for USB control, integer
# USB devices have a vendor ID and a product ID.
usb_vendor_id = 0x16c0

## usb_product_id			Product ID for USB control, integer
# USB devices have a vendor ID and a product ID.
usb_product_id = 0x05dc

# I2C-address of the Si570 in the softrock;  Thanks to Joachim Schneider, DB6QS
## si570_i2c_address		I2C address, integer
# I2C-address of the Si570 in the softrock.
si570_i2c_address = 0x55
#si570_i2c_address = 0x70

# Thanks to Ethan Blanton, KB8OJH, for this patch for the Si570 (many SoftRock's):
## si570_direct_control		Use Si570 direct control, boolean
# If you are using a DG8SAQ interface to set a Si570 clock directly, set
# this to True.  Complex controllers which have their own internal
# crystal calibration do not require this.
si570_direct_control = False
#si570_direct_control = True

## si570_xtal_freq			Si570 crystal frequency, integer
# This is the Si570 startup frequency in Hz.  114.285MHz is the typical
# value from the data sheet; you can use 'usbsoftrock calibrate' to find
# the value for your device.
si570_xtal_freq = 114285000

## key_poll_msec			Key poll time msec, integer
# Softrock hardware must be polled to get the key up/down state.  This is the time between
# polls in milliseconds.  Use zero to turn off the poll if your SoftRock does not have a key
# jack or USB key control.
key_poll_msec = 0
#key_poll_msec = 5

## key_hang_time			Key hang time secs, number
# Softrock transmit hardware uses semi break-in for CW operation.  This is the time in
# seconds before changing back to receive.
key_hang_time = 0.7

## repeater_delay			Repeater delay secs, number
# The fixed delay for changing the repeater Rx/Tx frequency in seconds.
repeater_delay = 0.25

## rx_max_amplitude_correct		Max ampl correct, number
# If you get your I/Q samples from a sound card, you will need to correct the
# amplitude and phase for inaccuracies in the analog hardware.  The correction is
# entered using the controls from the "Rx Phase" button on the config screen.
# You must enter a positive number.  This controls the range of the control.
rx_max_amplitude_correct = 0.2

## rx_max_phase_correct			Max phase correct, number
# If you get your I/Q samples from a sound card, you will need to correct the
# amplitude and phase for inaccuracies in the analog hardware.  The correction is
# entered using the controls from the "Rx Phase" button on the config screen.
# You must enter a positive number.  This controls the range of the control in degrees.
rx_max_phase_correct = 10.0

## mic_out_volume		Tx audio level, number
# The level of the Tx audio sent to the sound card after all processing as a fraction 0.0 to 0.7.
# The level is limited to 0.7 to allow headroom for amplitude and phase adjustments.
mic_out_volume = 0.7

# The bandAmplPhase dictionary gives the amplitude and phase corrections for
# sound card data.  The format is a dictionary with key "band", giving a dictionary
# with key "rx" or "tx", giving a list of tuples (VFO, tune, amplitude, phase).  
#
# If you use Quisk as a panadapter, the corrections will not depend on the band.
# In that case create a band "panadapter" in your config file, and all corrections
# will be read/written to that band.
bandAmplPhase = {}				# Empty dictionary to start
#bandAmplPhase = {'panadapter':{}}		# Create "panadapter" band for all corrections




################ Receivers SoftRock Fixed, Fixed frequency devices that capture samples from a sound card, and (for Tx) play samples to a sound card
## hardware_file_name		Hardware file path, rfile
# This is the file that contains the control logic for each radio.
#hardware_file_name = 'quisk_hardware_fixed.py'

## widgets_file_name			Widget file path, rfile
# This optional file adds additional controls for the radio.
#widgets_file_name = ''

## fixed_vfo_freq			Fixed VFO frequency, integer
# The fixed VFO frequency.  That is, the frequency in the center of the screen.
fixed_vfo_freq = 7056000

## rx_max_amplitude_correct		Max ampl correct, number
# If you get your I/Q samples from a sound card, you will need to correct the
# amplitude and phase for inaccuracies in the analog hardware.  The correction is
# entered using the controls from the "Rx Phase" button on the config screen.
# No correction is 1.00.  This controls the range of the control.
rx_max_amplitude_correct = 0.2

## rx_max_phase_correct			Max phase correct, number
# If you get your I/Q samples from a sound card, you will need to correct the
# amplitude and phase for inaccuracies in the analog hardware.  The correction is
# entered using the controls from the "Rx Phase" button on the config screen.
# No correction is 0.00.  This controls the range of the control in degrees.
rx_max_phase_correct = 10.0

## mic_out_volume		Tx audio level, number
# The level of the Tx audio sent to the sound card after all processing as a fraction 0.0 to 0.7.
# The level is limited to 0.7 to allow headroom for amplitude and phase adjustments.
mic_out_volume = 0.7

# The bandAmplPhase dictionary gives the amplitude and phase corrections for
# sound card data.  The format is a dictionary with key "band", giving a dictionary
# with key "rx" or "tx", giving a list of tuples (VFO, tune, amplitude, phase).  
#
# If you use Quisk as a panadapter, the corrections will not depend on the band.
# In that case create a band "panadapter" in your config file, and all corrections
# will be read/written to that band.
bandAmplPhase = {}				# Empty dictionary to start
#bandAmplPhase = {'panadapter':{}}		# Create "panadapter" band for all corrections



################ Receivers HiQSDR, The original N2ADR hardware and the improved HiQSDR using UDP
## hardware_file_name		Hardware file path, rfile
# This is the file that contains the control logic for each radio.
#hardware_file_name = 'hiqsdr/quisk_hardware.py'

## widgets_file_name			Widget file path, rfile
# This optional file adds additional controls for the radio.
#widgets_file_name = ''

# For the N2ADR 2010 transceiver described in QEX, and for the improved version HiQSDR,
# see the sample config file in the hiqsdr package directory, and set these:

## use_rx_udp			Hardware type, integer choice
# This is the type of UDP hardware.  Use 1 for the original hardware by N2ADR.
# Use 2 for the HiQSDR.
#use_rx_udp = 2
#use_rx_udp = 1
#use_rx_udp = 17

## tx_level		Tx Level, dict
# tx_level sets the transmit level 0 to 255 for each band.  The None band is the default.
# The config screen has a slider 0 to 100% so you can reduce the transmit power.  The sliders
# only appear if your hardware defines the method SetTxLevel().  The hardware only supports a
# power adjustment range of 20 dB, so zero is still a small amount of power.
tx_level = {
	None:120, '60':110}

## digital_tx_level			Digital Tx power %, integer
# Digital modes reduce power by the percentage on the config screen.
# This is the maximum value of the slider.
digital_tx_level = 20

## HiQSDR_BandDict		IO Bus, dict
# If you use the HiQSDR hardware, set these:
# The HiQSDR_BandDict sets the preselect (4 bits) on the X1 connector.
HiQSDR_BandDict = {
	'160':1, '80':2, '40':3, '30':4, '20':5, '15':6, '17':7,
	'12':8, '10':9, '6':10, '500k':11, '137k':12 }

## cw_delay                 CW Delay, integer
# This is the delay for CW from 0 to 255.
cw_delay = 0

## rx_udp_ip				IP address, text
# This is the IP address of your hardware.
# For FPGA firmware version 1.4 and newer, and if enabled, the hardware is set to the IP address you enter here.
# For older firmware, the IP address is programmed into the FPGA, and you must enter that address.
rx_udp_ip = "192.168.2.196"
#rx_udp_ip = "192.168.1.196"

## rx_udp_port				Hardware UDP port, integer
# This is the base UDP port number of your hardware.
rx_udp_port = 0xBC77

## rx_udp_ip_netmask		Network netmask, text
# This is the netmask for the network.
rx_udp_ip_netmask = '255.255.255.0'

## tx_ip					Transmit IP, text
# Leave this blank to use the same IP address as the receive hardware.  Otherwise, enter "disable"
# to disable sending transmit I/Q samples, or enter the actual IP address.  You must enter "disable"
# if you have multiple hardwares on the network, and only one should transmit.
tx_ip = ""
#tx_ip = "disable"
#tx_ip = "192.168.1.201"

## tx_audio_port			Tx audio UDP port, integer
# This is the UDP port for transmit audio I/Q samples.  Enter zero to calculate this from the
# base hardware port.  Otherwise enter the special custom port.
tx_audio_port = 0

## rx_udp_clock				Clock frequency Hertz, integer
# This is the clock frequency of the hardware in Hertz.
rx_udp_clock = 122880000

## sndp_active				Enable setting IP, boolean
# If possible, set the IP address to the address entered.
# For FPGA firmware version 1.4 and newer, the hardware is set to the IP address you enter here.
# For older firmware, the IP address is programmed into the FPGA, and you must enter that address.
sndp_active = True
#sndp_active = False





################ Receivers Hermes, The Hermes-Lite Project and possibly other hardware with the Hermes FPGA code.
## hardware_file_name		Hardware file path, rfile
# This is the file that contains the control logic for each radio.
#hardware_file_name = 'hermes/quisk_hardware.py'

## widgets_file_name			Widget file path, rfile
# This optional file adds additional controls for the radio.
#widgets_file_name = 'hermes/quisk_widgets.py'

# Quisk has support for the Hermes-Lite project.  This support will be extended to the original Hermes.
# Use the file hermes/quisk_conf.py as a model config file.  The Hermes can obtain its IP address from
# DHCP.  Set rx_udp_ip to the null string in this case.  Or use rx_udp_ip to specify an IP address, but
# be sure it is unique and not in use by a DHCP server. The tx_ip and tx_audio_port are not used.
# Note: Setting the IP fails for the Hermes-Lite.
# You can set these options:

## use_rx_udp			Hardware type, integer choice
# This is the type of UDP hardware.  Use 10 for the Hermes protocol.
#use_rx_udp = 10

## rx_udp_ip				IP change, text
# This item should be left blank. It is used to change the IP address of the hardware to a different
# IP once the hardware is found. Not all Hermes firmware supports changing the IP address.
#rx_udp_ip = ""

## rx_udp_port				Hardware UDP port, integer
# This is the UDP port number of your hardware.
#rx_udp_port = 1024

## rx_udp_ip_netmask		Network netmask, text
# This is the netmask for the network.
#rx_udp_ip_netmask = '255.255.255.0'

## tx_ip					Transmit IP, text
# Leave this blank to use the same IP address as the receive hardware.  Otherwise, enter "disable"
# to disable sending transmit I/Q samples, or enter the actual IP address.  You must enter "disable"
# if you have multiple hardwares on the network, and only one should transmit. This item is normally blank.
tx_ip = ""
#tx_ip = "disable"

## tx_audio_port			Tx audio UDP port, integer
# This is the UDP port for transmit audio I/Q samples.  Enter zero to calculate this from the
# base hardware port.  Otherwise enter the special custom port.
tx_audio_port = 0

## rx_udp_clock				Clock frequency Hertz, integer
# This is the clock frequency of the hardware in Hertz.  For HermesLite ver2 use 76800000.
#rx_udp_clock = 73728000
#rx_udp_clock = 61440000
#rx_udp_clock = 76800000

## tx_level		Tx Level, dict
# tx_level sets the transmit level 0 to 255 for each band.  The None band is the default.
# The config screen has a slider 0 to 100% so you can reduce the transmit power.  The sliders
# only appear if your hardware defines the method SetTxLevel().  The hardware only supports a
# limited adjustment range, so zero is still a small amount of power.
tx_level = {
	None:120, '60':110}

## digital_tx_level			Digital Tx power %, integer
# Digital modes reduce power by the percentage on the config screen.
# This is the maximum value of the slider.
#digital_tx_level = 20


## hermes_code_version		Hermes code version, integer
# There can be multiple Hermes devices on a network, but Quisk can only use one of these.  If you have multiple
# hermes devices, you can use this to specify a unique device.  Or use -1 to accept any board.
hermes_code_version = -1

## hermes_board_id			Hermes board ID, integer
# There can be multiple Hermes devices on a network, but Quisk can only use one of these.  If you have multiple
# hermes devices, you can use this to specify a unique device.  Or use -1 to accept any board.
hermes_board_id = -1

## hermes_LNA_dB			Initial LNA dB, integer
# The initial value for the low noise Rx amplifier gain in dB.
hermes_LNA_dB = 20

## hermes_lowpwr_tr_enable		Disable T/R in low power, boolean
# This option only applies to the Hermes Lite 2.
# Normally, the T/R relay and external PTT output switch on and off when keying the transmitter.
# But if you set this option, and if you are in low power mode (final amp off) then the T/R relay
# remains in receive mode.  This is useful for VNA operation as you can use the low power Tx output
# as the generator and the normal connector as the detector.
# Changes are immediate (no need to restart).
hermes_lowpwr_tr_enable = False
#hermes_lowpwr_tr_enable = True

## hermes_bias_adjust			Enable bias adjust, boolean
# This option only applies to the Hermes Lite 2.
# Below are controls that adjust the bias on the power output transistors.  Before you enable adjustment,
# make sure you know the correct drain current and how to monitor the current.
# Then set this to True.  When you are finished, set it back to False.  The bias adjustment
# is stored in the hardware only when the "Write" button is pressed.
# Changes are immediate (no need to restart).
hermes_bias_adjust = False
#hermes_bias_adjust = True

## hermes_power_amp			Enable power amp, boolean
# This option only applies to the Hermes Lite 2.
# When True, the power amp is turned on.  Otherwise, the low power output is used.
# Changes are immediate (no need to restart).
hermes_power_amp = False
#hermes_power_amp = True

## power_meter_calib_name		Power meter calibration, text choice
# This is the calibration table used to convert the power sensor voltage measured by the ADC to the transmit power display.
# It is a table of ADC codes and the corresponding measured power level.  If you have a power meter, you can create your own
# table by selecting "New". Then enter ten or more power measurements from low to full power.
# For the Hermes-Lite version E3 filter board, use the built-in table "HL2FilterE3".
# Changes are immediate (no need to restart).
power_meter_calib_name = 'HL2FilterE3'

## hermes_disable_sync			Disable Power Supply Sync, boolean
# This option only applies to the Hermes Lite 2.
# When True, the FPGA will not generate a switching frequency for the power supply to
# move the harmonics out of amateur bands.
# Changes are immediate (no need to restart).
hermes_disable_sync = False
#hermes_disable_sync = True

# These are known power meter calibration tables. This table is not present in the JSON settings file.
power_meter_std_calibrations = {}
power_meter_std_calibrations['HL2FilterE3'] = [[ 0, 0.0 ], [ 25.865384615384617, 0.0025502539351328003 ], [ 101.02453987730061, 0.012752044999999998 ], 
          [ 265.2901234567901, 0.050600930690879994 ], [ 647.9155844155844, 0.21645831264800003 ], [ 1196.5935483870967, 0.66548046472992 ], 
          [ 1603.7032258064517, 1.1557229391679997 ], [ 2012.3271604938273, 1.811892166688 ], [ 2616.7727272727275, 3.0085848760319993 ], 
          [ 3173.818181818182, 4.3927428485119995 ], [ 3382.7922077922076, 4.9791328857920005 ], [ 3721.0714285714284, 6.024750791808321 ], 
          [ 4093.1785714285716, 7.28994845808807 ], [ 4502.496428571429, 8.820837634286566 ], [ 4952.746071428572, 10.673213537486745 ] ]
#power_meter_std_calibrations['HL2FilterE1'] = [[0, 0.0], [9.07, 0.002], [54.98, 0.014], [148.6, 0.057],
#          [328.0, 0.208], [611.1, 0.646], [807.0, 1.098], [982.1, 1.6], [1223.3, 2.471], [1517.7, 3.738], [1758.7, 5.02]]

## Hermes_BandDict		Rx IO Bus, dict
# The Hermes_BandDict sets the 7 bits on the J16 connector for Rx.
Hermes_BandDict = {
	'160':0b0000001, '80':0b1000010, '60':0b1000100, '40':0b1000100, '30':0b1001000, '20':0b1001000, '17':0b1010000,
	 '15':0b1010000, '12':0b1100000, '10':0b1100000}

## Hermes_BandDictTx		Tx IO Bus, dict
# The Hermes_BandDictTx sets the 7 bits on the J16 connector for Tx if enabled.
Hermes_BandDictTx = {'160':0, '80':0, '60':0, '40':0, '30':0, '20':0, '17':0, '15':0, '12':0, '10':0}

## Hermes_BandDictEnTx		Enable Tx Filt, boolean
# Enable the separate Rx and Tx settings for the J16 connector.
Hermes_BandDictEnTx = False
#Hermes_BandDictEnTx = True

## AlexHPF                      Alex High Pass Filters, list
# This is a list of frequencies and high pass filter settings.
AlexHPF = [
    ['3.0', '4.5', 0, 0], ['6.5', '8.5', 0, 0]] + [['', '', 0, 0]] * 6
## AlexLPF                      Alex Low Pass Filters, list
# This is a list of frequencies and low pass filter settings.
AlexLPF = [
    ['3.0', '4.5', 0, 0], ['6.5', '8.5', 0, 0]] + [['', '', 0, 0]] * 6

## AlexHPF_TxEn                    Alex HPF Tx Enable, boolean
AlexHPF_TxEn = False
#AlexHPF_TxEn = True

## AlexLPF_TxEn                    Alex LPF Tx Enable, boolean
AlexLPF_TxEn = False
#AlexLPF_TxEn = True


################ Receivers Red Pitaya, The Red Pitaya Project by Pavel Demin.  This uses the Hermes FPGA code.
## hardware_file_name		Hardware file path, rfile
# This is the file that contains the control logic for each radio.
#hardware_file_name = 'hermes/quisk_hardware.py'

## widgets_file_name			Widget file path, rfile
# This optional file adds additional controls for the radio.
#widgets_file_name = ''

## use_rx_udp			Hardware type, integer choice
# This is the type of UDP hardware.  Use 10 for the Hermes protocol.
#use_rx_udp = 10

## rx_udp_ip				IP change, text
# This item should be left blank. It is used to change the IP address of the hardware to a different
# IP once the hardware is found. Not all Hermes firmware supports changing the IP address.
#rx_udp_ip = ""

## rx_udp_port				Hardware UDP port, integer
# This is the UDP port number of your hardware.
#rx_udp_port = 1024

## rx_udp_ip_netmask		Network netmask, text
# This is the netmask for the network.
#rx_udp_ip_netmask = '255.255.255.0'

## tx_ip					Transmit IP, text
# Leave this blank to use the same IP address as the receive hardware.  Otherwise, enter "disable"
# to disable sending transmit I/Q samples, or enter the actual IP address.  You must enter "disable"
# if you have multiple hardwares on the network, and only one should transmit. This item is normally blank.
tx_ip = ""
#tx_ip = "disable"

## tx_audio_port			Tx audio UDP port, integer
# This is the UDP port for transmit audio I/Q samples.  Enter zero to calculate this from the
# base hardware port.  Otherwise enter the special custom port.
tx_audio_port = 0

## rx_udp_clock				Clock frequency Hertz, integer
# This is the clock frequency of the hardware in Hertz.
#rx_udp_clock = 125000000

## tx_level		Tx Level, dict
# tx_level sets the transmit level 0 to 255 for each band.  The None band is the default.
# The config screen has a slider 0 to 100% so you can reduce the transmit power.  The sliders
# only appear if your hardware defines the method SetTxLevel().  The hardware only supports a
# limited adjustment range, so zero is still a small amount of power.
tx_level = {
	None:120, '60':110}

## digital_tx_level			Digital Tx power %, integer
# Digital modes reduce power by the percentage on the config screen.
# This is the maximum value of the slider.
#digital_tx_level = 20

## hermes_code_version		Hermes code version, integer
# There can be multiple Hermes devices on a network, but Quisk can only use one of these.  If you have multiple
# hermes devices, you can use this to specify a unique device.  Or use -1 to accept any board.
hermes_code_version = -1

## hermes_board_id			Hermes board ID, integer
# There can be multiple Hermes devices on a network, but Quisk can only use one of these.  If you have multiple
# hermes devices, you can use this to specify a unique device.  Or use -1 to accept any board.
hermes_board_id = -1

## hermes_LNA_dB			Initial LNA dB, integer
# The initial value for the low noise Rx amplifier gain in dB.
hermes_LNA_dB = 20

## Hermes_BandDict		Hermes Bus, dict
# The Hermes_BandDict sets the 7 bits on the J16 connector.
Hermes_BandDict = {
	'160':0b0000001, '80':0b0000010, '60':0b0000100, '40':0b0001000, '30':0b0010000, '20':0b0100000, '15':0b1000000}

## Hermes_BandDictTx		Tx IO Bus, dict
# The Hermes_BandDictTx sets the 7 bits on the J16 connector for Tx if enabled.
Hermes_BandDictTx = {'160':0, '80':0, '60':0, '40':0, '30':0, '20':0, '17':0, '15':0, '12':0, '10':0}

## Hermes_BandDictEnTx		Enable Tx Filt, boolean
# Enable the separate Rx and Tx settings for the J16 connector.
Hermes_BandDictEnTx = False
#Hermes_BandDictEnTx = True

## AlexHPF                      Alex High Pass Filters, list
# This is a list of frequencies and high pass filter settings.
AlexHPF = [
    ['3.0', '4.5', 0, 0], ['6.5', '8.5', 0, 0]] + [['', '', 0, 0]] * 6

## AlexLPF                      Alex Low Pass Filters, list
# This is a list of frequencies and low pass filter settings.
AlexLPF = [
    ['3.0', '4.5', 0, 0], ['6.5', '8.5', 0, 0]] + [['', '', 0, 0]] * 6

## AlexHPF_TxEn                    Alex HPF Tx Enable, boolean
AlexHPF_TxEn = False
#AlexHPF_TxEn = True

## AlexLPF_TxEn                    Alex LPF Tx Enable, boolean
AlexLPF_TxEn = False
#AlexLPF_TxEn = True


################ Receivers SoapySDR, The SoapySDR interface to multiple hardware SDRs.
## hardware_file_name		Hardware file path, rfile
# This is the file that contains the control logic for each radio.
#hardware_file_name = 'soapypkg/quisk_hardware.py'

## widgets_file_name			Widget file path, rfile
# This optional file adds additional controls for the radio.
#widgets_file_name = ''

## use_soapy	Use SoapySDR, integer
# Enter 1 to turn on SoapySDR.
#use_soapy = 1

# Further items are present in the radio dictionary with names soapy_*


################ Receivers SdrIQ, The SDR-IQ receiver by RfSpace
## hardware_file_name		Hardware file path, rfile
# This is the file that contains the control logic for each radio.
#hardware_file_name = 'sdriqpkg/quisk_hardware.py'

## widgets_file_name			Widget file path, rfile
# This optional file adds additional controls for the radio.
#widgets_file_name = ''

#
# For the SDR-IQ the soundcard is not used for capture.


## use_sdriq			Hardware by RF-Space, integer choice
# This is the type of hardware.  For the SdrIQ, use_sdriq is 1.
#use_sdriq = 1

## sdriq_name			Serial port, text
# The name of the SDR-IQ serial port to open.
#sdriq_name = "/dev/ft2450"
#sdriq_name = "/dev/ttyUSB2"
#sdriq_name = "COM6"

## sdriq_clock			Clock frequency Hertz, number
# This is the clock frequency of the hardware in Hertz.
#sdriq_clock = 66666667.0

## sdriq_decimation		Decimation, integer choice
# This is the decimation from the SDR-IQ clock.  Decimation by 1250, 600, 500, 360 results in a
# sample rate of 53333, 111111, 133333, 185185 samples per second.
#sdriq_decimation = 1250
#sdriq_decimation = 600
#sdriq_decimation = 500
#sdriq_decimation = 360



################ Receivers Odyssey,   The Odyssey project using a UDP protocol similar to the HiQSDR
## hardware_file_name		Hardware file path, rfile
# This is the file that contains the control logic for each radio.
#hardware_file_name = 'hiqsdr/quisk_hardware.py'

## widgets_file_name			Widget file path, rfile
# This optional file adds additional controls for the radio.
#widgets_file_name = ''

## use_rx_udp			Hardware type, integer choice
# This is the type of UDP hardware.  The Odyssey uses type 2.
#use_rx_udp = 2

## tx_level		Tx Level, dict
# tx_level sets the transmit level 0 to 255 for each band.  The None band is the default.
# The config screen has a slider 0 to 100% so you can reduce the transmit power.  The sliders
# only appear if your hardware defines the method SetTxLevel().  The hardware only supports a
# power adjustment range of 20 dB, so zero is still a small amount of power.
tx_level = {
	None:120, '60':110}

## digital_tx_level			Digital Tx power %, integer
# Digital modes reduce power by the percentage on the config screen.
# This is the maximum value of the slider.
digital_tx_level = 20

## HiQSDR_BandDict		IO Bus, dict
# This sets the preselect (4 bits) on the X1 connector.
HiQSDR_BandDict = {
	'160':1, '80':2, '40':3, '30':4, '20':5, '15':6, '17':7,
	'12':8, '10':9, '6':10, '500k':11, '137k':12 }

## cw_delay                 CW Delay, integer
# This is the delay for CW from 0 to 255.
cw_delay = 0

## rx_udp_ip				IP address, text
# This is the IP address of your hardware.
# For FPGA firmware version 1.4 and newer, and if enabled, the hardware is set to the IP address you enter here.
# For older firmware, the IP address is programmed into the FPGA, and you must enter that address.
rx_udp_ip = "192.168.2.160"
#rx_udp_ip = "192.168.1.196"

## rx_udp_port				Hardware UDP port, integer
# This is the UDP port number of your hardware.
rx_udp_port = 48247

## rx_udp_ip_netmask		Network netmask, text
# This is the netmask for the network.
rx_udp_ip_netmask = '255.255.255.0'

## tx_ip					Transmit IP, text
# Leave this blank to use the same IP address as the receive hardware.  Otherwise, enter "disable"
# to disable sending transmit I/Q samples, or enter the actual IP address.  You must enter "disable"
# if you have multiple hardwares on the network, and only one should transmit.
tx_ip = ""
#tx_ip = "disable"
#tx_ip = "192.168.1.201"

## tx_audio_port			Tx audio UDP port, integer
# This is the UDP port for transmit audio I/Q samples.  Enter zero to calculate this from the
# base hardware port.  Otherwise enter the special custom port.
tx_audio_port = 0

## rx_udp_clock				Clock frequency Hertz, integer
# This is the clock frequency of the hardware in Hertz.
rx_udp_clock = 122880000

## sndp_active				Enable setting IP, boolean
# If possible, set the IP address to the address entered.
# For FPGA firmware version 1.4 and newer, the hardware is set to the IP address you enter here.
# For older firmware, the IP address is programmed into the FPGA, and you must enter that address.
sndp_active = True
#sndp_active = False

## radio_sound_ip			IP sound play, text
# This option sends radio playback sound to a UDP device.  Some SDR hardware devices have an
# audio codec that can play radio sound with less latency than a soundcard.  The sample rate
# is the same as the soundcard sample rate, but probably you will want 48000 sps.  The UDP
# data consists of two bytes of zero, followed by the specified number of samples.  Each
# sample consists of two bytes (a short) of I data and two bytes of Q data in little-endian order.
# For radio_sound_nsamples = 360, the total number of UDP data bytes is 1442.
#radio_sound_ip = "192.168.2.160"

## radio_sound_port			UDP port play, integer
# The UDP port of the radio sound play device.
#radio_sound_port = 48250

## radio_sound_nsamples		Num play samples, integer
# The number of play samples per UDP block.
#radio_sound_nsamples = 360

## radio_sound_mic_ip		IP microphone, text
# This option receives microphone samples from a UDP device.  The UDP
# data consists of two bytes of zero, followed by the specified number of samples.  Each
# sample consists of two bytes (a short) of monophonic microphone data in little-endian order.
# For radio_sound_mic_nsamples = 720, the total number of UDP data bytes is 1442.
#radio_sound_mic_ip = "192.168.2.160"

## radio_sound_mic_port		UDP port mic, integer
# The UDP port of the microphone device.
#radio_sound_mic_port = 48251

## radio_sound_mic_nsamples		Num mic samples, integer
# The number of mic samples per UDP block.
#radio_sound_mic_nsamples = 720

## radio_sound_mic_boost	Mic boost, boolean
# Use False for no microphone boost, or True for +20 dB boost.
#radio_sound_mic_boost = False
#radio_sound_mic_boost = True


################ Receivers Odyssey2,   The Odyssey-2 project using the HPSDR Hermes protocol
## hardware_file_name		Hardware file path, rfile
# This is the file that contains the control logic for each radio.
#hardware_file_name = 'hermes/quisk_hardware.py'

## widgets_file_name			Widget file path, rfile
# This optional file adds additional controls for the radio.
#widgets_file_name = 'hermes/quisk_widgets.py'

# Use the file hermes/quisk_conf.py as a model config file.  The Hermes can obtain its IP address from
# DHCP.  Set rx_udp_ip to the null string in this case.  Or use rx_udp_ip to specify an IP address, but
# be sure it is unique and not in use by a DHCP server.
# You can set these options:

## use_rx_udp			Hardware type, integer choice
# This is the type of UDP hardware.  Use 10 for the Hermes protocol.
#use_rx_udp = 10

## rx_udp_ip				IP change, text
# This item should be left blank. It is used to change the IP address of the hardware to a different
# IP once the hardware is found. Not all Hermes firmware supports changing the IP address.
#rx_udp_ip = ""

## rx_udp_port				Hardware UDP port, integer
# This is the UDP port number of your hardware.
#rx_udp_port = 1024

## rx_udp_ip_netmask		Network netmask, text
# This is the netmask for the network.
#rx_udp_ip_netmask = '255.255.255.0'

## tx_ip					Transmit IP, text
# Leave this blank to use the same IP address as the receive hardware.  Otherwise, enter "disable"
# to disable sending transmit I/Q samples, or enter the actual IP address.  You must enter "disable"
# if you have multiple hardwares on the network, and only one should transmit. This item is normally blank.
tx_ip = ""
#tx_ip = "disable"

## tx_audio_port			Tx audio UDP port, integer
# This is the UDP port for transmit audio I/Q samples.  Enter zero to calculate this from the
# base hardware port.  Otherwise enter the special custom port.
tx_audio_port = 0

## rx_udp_clock				Clock frequency Hertz, integer
# This is the clock frequency of the hardware in Hertz.  For Odyssey use 122880000.
#rx_udp_clock = 122880000

## tx_level		Tx Level, dict
# tx_level sets the transmit level 0 to 255 for each band.  The None band is the default.
# The config screen has a slider 0 to 100% so you can reduce the transmit power.  The sliders
# only appear if your hardware defines the method SetTxLevel().  The hardware only supports a
# limited adjustment range, so zero is still a small amount of power.
tx_level = {
	None:120, '60':110}

## digital_tx_level			Digital Tx power %, integer
# Digital modes reduce power by the percentage on the config screen.
# This is the maximum value of the slider.
#digital_tx_level = 20


## hermes_code_version		Hermes code version, integer
# There can be multiple Hermes devices on a network, but Quisk can only use one of these.  If you have multiple
# Hermes devices, you can use this to specify a unique device.  Or use -1 to accept any board.
hermes_code_version = -1

## hermes_board_id			Hermes board ID, integer
# There can be multiple Hermes devices on a network, but Quisk can only use one of these.  If you have multiple
# Hermes devices, you can use this to specify a unique device.  Or use -1 to accept any board.
hermes_board_id = -1

## hermes_LNA_dB			Initial LNA dB, integer
# The initial value for the low noise Rx amplifier gain in dB.
hermes_LNA_dB = 20

## Hermes_BandDict		Hermes Bus, dict
# The Hermes_BandDict sets the 7 bits on the J16 connector.
Hermes_BandDict = {
	'160':0b0000001, '80':0b0000010, '60':0b0000100, '40':0b0001000, '30':0b0010000, '20':0b0100000, '15':0b1000000}

## Hermes_BandDictTx		Tx IO Bus, dict
# The Hermes_BandDictTx sets the 7 bits on the J16 connector for Tx if enabled.
Hermes_BandDictTx = {'160':0, '80':0, '60':0, '40':0, '30':0, '20':0, '17':0, '15':0, '12':0, '10':0}

## Hermes_BandDictEnTx		Enable Tx Filt, boolean
# Enable the separate Rx and Tx settings for the J16 connector.
Hermes_BandDictEnTx = False
#Hermes_BandDictEnTx = True

## AlexHPF                      Alex High Pass Filters, list
# This is a list of frequencies and high pass filter settings.
AlexHPF = [
    ['3.0', '4.5', 0, 0], ['6.5', '8.5', 0, 0]] + [['', '', 0, 0]] * 6

## AlexLPF                      Alex Low Pass Filters, list
# This is a list of frequencies and low pass filter settings.
AlexLPF = [
    ['3.0', '4.5', 0, 0], ['6.5', '8.5', 0, 0]] + [['', '', 0, 0]] * 6

## AlexHPF_TxEn                    Alex HPF Tx Enable, boolean
AlexHPF_TxEn = False
#AlexHPF_TxEn = True

## AlexLPF_TxEn                    Alex LPF Tx Enable, boolean
AlexLPF_TxEn = False
#AlexLPF_TxEn = True


################ Receivers Afedri,   The Afedri SDR receiver with the Ethernet interface.
## hardware_file_name		Hardware file path, rfile
# This is the file that contains the control logic for each radio.
#hardware_file_name = 'afedrinet/quisk_hardware.py'

## widgets_file_name			Widget file path, rfile
# This optional file adds additional controls for the radio.
#widgets_file_name = ''

## rx_udp_ip				IP address, text
# This is the IP address of your hardware. Enter 0.0.0.0 to search for the address.
#rx_udp_ip = "0.0.0.0"
#rx_udp_ip = "192.168.0.200"
#rx_udp_ip = "192.168.1.196"

## rx_udp_port				Hardware UDP port, integer
# This is the base UDP port number of your hardware.
#rx_udp_port = 50000

## rx_udp_ip_netmask		Network netmask, text
# This is the netmask for the network.
#rx_udp_ip_netmask = '255.255.255.0'

## rx_udp_clock				Clock frequency Hertz, integer
# This is the clock frequency of the hardware in Hertz.
#rx_udp_clock = 80000000

## default_rf_gain			Default RF gain, integer
# This is the RF gain when starting.
#default_rf_gain = 11


################ Sound Devices.  Quisk recognizes eight sound capture and playback devices.
# Playback devices:
#    name_of_sound_play      Play radio sound on speakers or headphones
#        playback_rate            The sample rate, normally 48000, 96000 or 192000
#    name_of_mic_play        For sound card modes (like SoftRock), play I/Q transmit audio
#        mic_playback_rate        The sample rate
#        mic_play_chan_I          Channel number 0, 1, ... for I samples
#        mic_play_chan_Q          Channel number 0, 1, ... for Q samples
#        tx_channel_delay         Channel number for delay, or -1
#    digital_output_name     Output monophonic digital samples to another program
#    sample_playback_name    Output digital I/Q samples to another program
#    digital_rx1_name     Output monophonic digital samples from Rx1 to another program
# Capture devices:
#    microphone_name         The monophonic microphone source
#        mic_sample_rate          The sample rate; must be 48000
#        mic_channel_I            The channel number for samples
#        mic_channel_Q            Not used.
#    name_of_sound_capt      For sound card modes (like SoftRock), capture I/Q samples
#        sample_rate              The sample rate
#        channel_i                Channel number 0, 1, ... for I samples
#        channel_q                Channel number 0, 1, ... for Q samples
#        channel_delay            Channel number for delay, or -1
#    digital_input_name      Receive monophonic digital samples from another program
#
# Unused devices have the null string "" as the name.  For example, name_of_sound_play="" for a panadapter.
#
# On Linux, Quisk can access your sound card through ALSA, PortAudio or PulseAudio.
# On Windows, Quisk uses DirectX for sound card access.

## channel_i		Sample channel I, integer
# Soundcard index of in-phase channel:  0, 1, 2, ...
channel_i = 0
#channel_i = 1

## channel_q		Sample channel Q, integer
# Soundcard index of quadrature channel:  0, 1, 2, ...
channel_q = 1
#channel_q = 0

# Thanks to Franco Spinelli for this fix:
## channel_delay		Rx channel delay, integer
# The H101 hardware using the PCM2904 chip has a one-sample delay between
# channels, which must be fixed in software.  If you have this problem,
# change channel_delay to either channel_i or channel_q.  Use -1 for no delay.
channel_delay = -1
#channel_delay = 0
#channel_delay = 1

## tx_channel_delay		Tx channel delay, integer
# This is for mic playback (SoftRock transmit)
tx_channel_delay = -1
#tx_channel_delay = 0
#tx_channel_delay = 1

## playback_rate		Playback rate, integer choice
# This is the received radio sound playback rate.  The default will
# be 48 kHz for the SDR-IQ and UDP port samples, and sample_rate for sound
# card capture.  Set it yourself for other rates or hardware.
# The playback_rate must be 24000, 48000, 96000 or 192000.
# The preferred rate is 48000 for use with digital modes and transmit of recorded audio.
#playback_rate =  48000
#playback_rate =  24000
#playback_rate =  96000
#playback_rate = 192000

## lin_sample_playback_name		Sample playback name, text
# This option sends the raw I/Q samples to another program using a loopback device (Linux) or
# a Virtual Audio Cable (Windows).  The sample rate is the same as the hardware sample rate.
# Read the samples from the loopback device with another program.
lin_sample_playback_name = ""
#lin_sample_playback_name = "hw:Loopback,0"

## win_sample_playback_name		Sample playback name, text
# This option sends the raw I/Q samples to another program using a loopback device (Linux) or
# a Virtual Audio Cable (Windows).  The sample rate is the same as the hardware sample rate.
# Read the samples from the loopback device with another program.
win_sample_playback_name = ""
#win_sample_playback_name = "COM6"

sample_playback_name = ""

# When you use the microphone input, the mic_channel_I and Q are the two capture
# microphone channels.  Quisk uses a monophonic mic, so audio is taken from the I
# channel, and the Q channel is (currently) ignored.  It is OK to set the same
# channel number for both, and this is necessary for a USB mono mic.  The mic sample rate
# should be 48000 to enable digital modes and the sound recorder to work, but 8000 can be used.
# Mic samples can be sent to an Ethernet device (use tx_ip and name_of_mic_play = "")
# or to a sound card (use name_of_mic_play="hw:1" or other device).
#
# If mic samples are sent to a sound card for Tx, the samples are tuned to the audio
# transmit frequency, and are set to zero unless the key is down.  You must set both
# microphone_name and name_of_mic_play even for CW.  For softrock hardware, you usually
# capture radio samples and play Tx audio on one soundcard; and capture the mic and play radio
# sound on the other sound card at 48000 sps.  For example:
#   name_of_sound_capt = "hw:0"				# high quality sound card at 48, 96, or 192 ksps
#   name_of_sound_play = "hw:1"				# lower quality sound card at 48 ksps
#   microphone_name    = name_of_sound_play
#   name_of_mic_play   = name_of_sound_capt

## lin_name_of_sound_play	Play radio sound, text
# Name of device to play demodulated radio audio.
lin_name_of_sound_play = "hw:0"

## win_name_of_sound_play	Play radio sound, text
# Name of device to play demodulated radio audio.
win_name_of_sound_play = "Primary"

## lin_name_of_sound_capt	Capture audio samples, text
# Name of device to capture samples from an audio device.
lin_name_of_sound_capt = "hw:0"

## win_name_of_sound_capt	Capture audio samples, text
# Name of device to capture samples from an audio device.
win_name_of_sound_capt = "Primary"

## sample_rate		Sample rate, integer
# The sample rate when capturing samples from a sound card.
#sample_rate =  48000
#sample_rate =  96000
#sample_rate = 192000

# Microphone capture:
## lin_microphone_name		Microphone name, text
# Name of microphone capture device (or "hw:1")
lin_microphone_name = ""

## win_microphone_name		Microphone name, text
# Name of microphone capture device (or "hw:1")
win_microphone_name = ""

microphone_name = ''

## mic_sample_rate		Mic sample rate, integer choice
# Microphone capture sample rate in Hertz, should be 48000, can be 8000
mic_sample_rate = 48000
#mic_sample_rate = 8000

## mic_channel_I		Mic channel I, integer
# Soundcard index of mic capture audio channel
mic_channel_I = 0

## mic_channel_Q		Mic channel Q, integer
# Soundcard index of ignored capture channel
mic_channel_Q = 0

## lin_name_of_mic_play		Mic play name, text
# Tx audio samples sent to soundcard (SoftRock).
# Name of play device if Tx audio I/Q is sent to a sound card.
lin_name_of_mic_play = ""

## win_name_of_mic_play		Mic play name, text
# Tx audio samples sent to soundcard (SoftRock).
# Name of play device if Tx audio I/Q is sent to a sound card.
win_name_of_mic_play = ""

name_of_mic_play = ""

## mic_playback_rate		Mic playback rate, integer
# Playback rate must be a multiple 1, 2, ... of mic_sample_rate
mic_playback_rate = 48000
#mic_playback_rate =  24000
#mic_playback_rate =  96000
#mic_playback_rate = 192000

## mic_play_chan_I		Mic play channel I, integer
# Soundcard index of Tx audio I play channel
mic_play_chan_I = 0
#mic_play_chan_I = 1

## mic_play_chan_Q		Mic play channel Q, integer
# Soundcard index of Tx audio Q play channel
mic_play_chan_Q = 1
#mic_play_chan_Q = 0

## lin_digital_input_name		Digital input name, text
# Input audio from an external program for use with digital modes.  The input must be
# stereo at 48000 sps, and you must set mic_sample_rate to 48000 also.
lin_digital_input_name = ""

## win_digital_input_name		Digital input name, text
# Input audio from an external program for use with digital modes.  The input must be
# stereo at 48000 sps, and you must set mic_sample_rate to 48000 also.
win_digital_input_name = ""

digital_input_name = ""

## lin_digital_output_name		Digital output name, text
# Output audio to an external program for use with digital modes.  The output is
# stereo at the same sample rate as the radio sound playback.
lin_digital_output_name = ""

## win_digital_output_name		Digital output name, text
# Output audio to an external program for use with digital modes.  The output is
# stereo at the same sample rate as the radio sound playback.
win_digital_output_name = ""

digital_output_name = ""

## lin_digital_rx1_name		Digital sub-receiver 1 output name, text
# Output audio to an external program for use with digital modes.
lin_digital_rx1_name = ""

## win_digital_rx1_name		Digital sub-receiver 1 output name, text
# Output audio to an external program for use with digital modes.
win_digital_rx1_name = ""

digital_rx1_name = ""

## digital_output_level		Digital output level, number
# This is the volume control 0.0 to 1.0 for digital playback to fldigi, etc.
# Changes are immediate (no need to restart).
digital_output_level = 0.7

# Sound card names:
#
# In PortAudio, soundcards have an index number 0, 1, 2, ... and a name.
# The name can be something like "HDA NVidia: AD198x Analog (hw:0,0)" or
# "surround41".  In Quisk, all PortAudio device names start with "portaudio".
# A device name like "portaudio#6" directly specifies the index.  A name like
# "portaudio:text" means to search for "text" in all available devices.  And
# there is a default device "portaudiodefault".  So these portaudio names are useful:
#name_of_sound_capt = "portaudio:(hw:0,0)"		# First sound card
#name_of_sound_capt = "portaudio:(hw:1,0)"		# Second sound card, etc.
#name_of_sound_capt = "portaudio#1"				# Directly specified index
#name_of_sound_capt = "portaudiodefault"		# May give poor performance on capture
#
# In ALSA, soundcards have these names.  The "hw" devices are the raw
# hardware devices, and should be used for soundcard capture.
#name_of_sound_capt = "hw:0"					# First sound card
#name_of_sound_capt = "hw:1"					# Second sound card, etc.
#name_of_sound_capt = "plughw"
#name_of_sound_capt = "plughw:1"
#name_of_sound_capt = "default"
#
# It is usually best to use ALSA names because they provide minimum latency.  But
# you may need to use PulseAudio to connect to other programs such as wsjt-x.
#
# Pulseaudio support was added by Philip G. Lee.  Many thanks!
# More pulse audio support was added by Eric Thornton, KM4DSJ.  Many thanks!
#
# For PulseAudio devices, use the name "pulse:name" and connect the streams
# to your hardware devices using a PulseAudio control program.  The name "pulse"
# alone refers to the "default" device.  The PulseAudio names are quite long;
# for example "alsa_output.pci-0000_00_1b.0.analog-stereo".  Look on the screen
# Config/Sound to see the device names.  There is a description, a PulseAudio name,
# and for ALSA devices, the ALSA name.  An example is:
#
#   CM106 Like Sound Device Analog Stereo
#      alsa_output.usb-0d8c_USB_Sound_Device-00-Device.analog-stereo
#      USB Sound Device USB Audio (hw:1,0)
#
#  Instead of the long PulseAudio name, you can enter a substring of any of
#  these three strings.
#
# Use the default pulse device for radio sound:
#name_of_sound_play = "pulse"
# Use a PulseAudio name for radio sound:
#name_of_sound_play = "pulse:alsa_output.usb-0d8c_USB_Sound_Device-00-Device.analog-stereo"
# Abbreviate the PulseAudio name:
#name_of_sound_play = "pulse:alsa_output.usb"
# Another abbreviation:
#name_of_sound_play = "pulse:CM106"
#
# This controls whether the PulseAudio devices are shown in the device list.
# If you don't have PulseAudio, you must set this to False.  Thanks to Simon, S54MI.

## lin_latency_millisecs		Play latency msec, integer
# Play latency determines how many samples are in the radio sound play buffer.
# A larger number makes it less likely that you will run out of samples to play,
# but increases latency.  It is OK to suffer a certain number of play buffer 
# underruns in order to get lower latency.
lin_latency_millisecs = 150
#lin_latency_millisecs =  50
#lin_latency_millisecs = 100
#lin_latency_millisecs = 250

## win_latency_millisecs		Play latency msec, integer
# Play latency determines how many samples are in the radio sound play buffer.
# A larger number makes it less likely that you will run out of samples to play,
# but increases latency.  It is OK to suffer a certain number of play buffer 
# underruns in order to get lower latency.
win_latency_millisecs = 150
#win_latency_millisecs =  50
#win_latency_millisecs = 100
#win_latency_millisecs = 250

latency_millisecs = 150

# If False, no list of PulseAudio devices is available.
# show_pulse_audio_devices		Show PulseAudio, boolean
# This controls whether PulseAudio devices are shown in the list of sound devices.
show_pulse_audio_devices = True
#show_pulse_audio_devices = False



################ Options
## max_record_minutes       Max minutes record time, number
# Quisk has record and playback buttons to save radio sound.  If there is no more room for
# sound, the old sound is discarded and the most recent sound is retained.  This controls
# the maximum time of sound storage in minutes for this recorded audio, and also the record
# time for the Tx Audio test screen.  If you want to transmit recorded sound, then mic_sample_rate
# must equal playback_rate and both must be 48000.
max_record_minutes = 1.00

# Quisk can save radio sound and samples to files, and can play recorded sound.  There is a button on the
# Config/Config screen to set the file names.  You can set the initial names with these variables:
file_name_audio = ""
#file_name_audio = "/home/jim/tmp/qaudio.wav"

file_name_samples = ""
#file_name_samples = "C:/tmp/qsamples.wav"
# The file for playback must be 48 ksps, 16-bit, one channel (monophonic); the same as the mic input.  When
# you play a file, the PTT button (if any) is pushed.  There is a control to repeat the playback.  This
# feature is intended to transmit a "CQ CQ" message, for example, during a contest.
file_name_playback = ""
#file_name_playback = "/home/jim/sounds/cqcq_contest.wav"

## do_repeater_offset       Use repeater offset, boolean
# Quisk can implement the frequency shift needed for repeaters.  If the repeater frequency
# is on the favorites screen, and you tune close (500 Hz) to that frequency, and there
# is an entry in the "offset" column, and the mode is FM, and do_repeater_offset is True,
# then Quisk will shift the Tx frequency by the offset when transmitting.  Your hardware
# file must define the method RepeaterOffset(self, offset=None).
do_repeater_offset = False
#do_repeater_offset = True

## correct_smeter       S-meter correction in S units, number
# This converts from dB to S-units for the S-meter (it is in S-units).
correct_smeter = 15.5
#correct_smeter = 7.7
#correct_smeter = 21.6

## agc_max_gain     Maximum AGC gain, number
# There is a button to turn AGC on or off,
# but AGC still limits the peak amplitude to avoid clipping even if it is off.
# Right click the AGC button to show the adjustment slider.  If the slider is at maximum,
# all signals will have the same (maximum) amplitude.  For lower values, weak signals
# will be somewhat less loud than strong signals; that is, some variation in signal
# amplitude remains.
# agc_max_gain controls the maximum AGC gain and thus the scale of the AGC slider control.  If
# it is too high, all signals reach the same amplitude at much less than 100% slider.
# If it is too low, then all signals fail to have the same amplitude even at 100%.  But
# the value is not critical, because you can adjust the slider a bit more.
agc_max_gain = 15000.0
#agc_max_gain = 10000.0
#agc_max_gain = 20000.0

## agc_release_time         AGC release time in seconds, number
# This is the AGC release time in seconds.  It must be greater than zero.  It is the time
# constant for gain recovery after a strong signal disappears.
agc_release_time = 1.0
#agc_release_time = 2.0
#agc_release_time = 0.5

## freq_spacing         Frequency rounding spacing, integer
# If freq_spacing is not zero, frequencies are rounded to the freq_base plus the
# freq_spacing; frequency = freq_base + N * freq_spacing.  This is useful at
# VHF and higher when Quisk is used with a transverter.
# This option is incompatible with "Frequency round for SSB".
freq_spacing = 0
#freq_spacing = 25000
#freq_spacing = 15000

## freq_round_ssb       Frequency round for SSB, integer
# If freq_round_ssb is not zero, when the left mouse button is clicked
# the frequency is rounded for voice modes but not for CW.  Mouse wheel etc. are unaffected.
# This is useful for HF when many SSB, AM etc. stations are at multiples of 500 or 1000 Hertz.
# This option is incompatible with "Frequency rounding spacing".
freq_round_ssb = 0
#freq_round_ssb = 1000

## freq_base            Frequency rounding base, integer
# If freq_spacing is not zero, frequencies are rounded to the freq_base plus the
# freq_spacing; frequency = freq_base + N * freq_spacing.  This is useful at
# VHF and higher when Quisk is used with a transverter.
# This option is incompatible with "Frequency round for SSB".
freq_base = 0
#freq_base = 12500

## cwTone               CW tone frequency in Hertz, integer
# This is the CW tone frequency in Hertz.
cwTone = 600
#cwTone = 400
#cwTone = 800

## invertSpectrum       Invert the RF spectrum, integer choice
# If your mixing scheme inverts the RF spectrum, set this option to un-invert it.
invertSpectrum = 0      # Do not invert
#invertSpectrum = 1     # Invert spectrum

# This is a list of mixer settings.  It only works for Linux; it has no effect in Windows.
# Use "amixer -c 1 contents" to get a list of mixer controls and their numid's for
# card 1 (or "-c 0" for card 0).  Then make a list of (device_name, numid, value)
# for each control you need to set.  For a decimal fraction, use a Python float; for example,
# use "1.0", not the integer "1".
#mixer_settings = [
#  ("hw:1", 2, 0.80),	# numid of microphone volume control, volume 0.0 to 1.0;
#  ("hw:1", 1, 1)		# numid of capture on/off control, turn on with 1;
#  ]

## modulation_index     FM modulation index, number
# For FM transmit, this is the modulation index.
modulation_index = 1.67

## pulse_audio_verbose_output		Debug PortAudio, integer choice
# Use 1 to turn on PulseAudio debug and status messages.  This allows for debugging of both devices and performance.
pulse_audio_verbose_output = 0
#pulse_audio_verbose_output = 1

## favorites_file_path	Path to favorites file, text
# The quisk config screen has a "favorites" tab where you can enter the frequencies and modes of
# stations.  The data is stored in this file.  If this is blank, the default is the file
# quisk_favorites.txt in the directory where your config file is located.
favorites_file_path = ''

## reverse_tx_sideband		Reverse Tx sideband, integer
# Set to 1 if you want to reverse the sideband when transmitting.
# For example, to receive on LSB but transmit on USB. This may be necessary for satellite operation
# depending on the mixing scheme.
# Changes are immediate (no need to restart).
reverse_tx_sideband = 0
#reverse_tx_sideband = 1

## dc_remove_bw			DC remove bandwidth, integer
# This is the 3 dB bandwidth of the filter centered at zero Hertz that is used to remove DC bias.
# Choose a bandwidth that suppresses DC and low frequency noise.
# Enter 1 to select a different filter based on block removal.
# Enter zero to disable the filter.
# Changes are immediate (no need to restart).
#dc_remove_bw =  0
#dc_remove_bw =  1
#dc_remove_bw =  20
#dc_remove_bw =  50
dc_remove_bw = 100
#dc_remove_bw = 200
#dc_remove_bw = 400




################ Remote
# DX cluster telent login data, thanks to DJ4CM.  Must have station_display_lines > 0.
## dxClHost             Dx cluster host name, text
# The Dx cluster options log into a Dx cluster server, and put station information
# on the station window under the graph and waterfall screens.
# dxClHost is the telnet host name.
dxClHost = ''
#dxClHost = 'example.host.net'

## dxClPort             Dx cluster port number, integer
# The Dx cluster options log into a Dx cluster server, and put station information
# on the station window under the graph and waterfall screens.
# dxClPort is the telnet port number.
dxClPort = 7373

## user_call_sign       Call sign for Dx cluster, text
# The Dx cluster options log into a Dx cluster server, and put station information
# on the station window under the graph and waterfall screens.
# user_call_sign is your call sign which may be needed for login.
user_call_sign = ''

## dxClPassword         Password for Dx cluster, text
# The Dx cluster options log into a Dx cluster server, and put station information
# on the station window under the graph and waterfall screens.
# dxClPassword  is the telnet password for the server.
dxClPassword = ''
#dxClPassword = 'getsomedx'

## dxClExpireTime       Dx cluster expire minutes, integer
# The Dx cluster options log into a Dx cluster server, and put station information
# on the station window under the graph and waterfall screens.
# dxClExpireTime is the time in minutes until DX Cluster entries are removed.
dxClExpireTime = 20

## IQ_Server_IP         Pulse server IP address, text
#IP Adddress for remote PulseAudio IQ server.
IQ_Server_IP = ""

## hamlib_ip            IP address for Hamlib Rig 2, text
# You can control Quisk from Hamlib.  Set the Hamlib rig to 2 and the device for rig 2 to
# localhost:4575.  Or choose a different name and port here.  Set the same name and port
# in the controlling program.
# hamlib_ip is the IP name or address.
hamlib_ip = "localhost"

## hamlib_port          IP port for Hamlib, integer
# You can control Quisk from Hamlib. For direct control, set the external program to rig 2
# "Hamlib NET rigctl", and set the Quisk hamlib port to 4532. To use the rigctld program to control
# Quisk, set the Quisk hamlib port to 4575. To turn off Hamlib control, set the Quisk port to zero.
#hamlib_port = 4575
hamlib_port = 4532
#hamlib_port = 0

## digital_xmlrpc_url   URL for control by XML-RPC, text
# This option is used by the digital modes that send audio to an external
# program, and receive audio to transmit.  Set Fldigi to upper sideband, XML-RPC control.
digital_xmlrpc_url = "http://localhost:7362"
#digital_xmlrpc_url = ""

## lin_hamlib_com1_name		CAT serial port name, text
# Enter a name to create a serial port so that an external program like N1MM+ or WSJT-X can
# control Quisk.  Then enter that name into the other program and specify a radio of type "Flex".  This is addition to the
# "Hamlib NET rigctl" mechanism which is based on a network connection. Leave this blank
# to turn off the serial port. The port settings are 9600 baud, 8 bits of data, no parity and one stop bit,
# although other settings are OK too.
# On Linux, the serial port names are of the form "/tmp/QuiskTTYx"
# where "x" is 0, 1, 2, etc. Quisk will create the serial port when it starts.
lin_hamlib_com1_name = ""
#lin_hamlib_com1_name = "/tmp/QuiskTTY0"

## lin_hamlib_com2_name     CAT serial-2 name, text
# This is a second serial port for external control of Quisk. Use a different serial port name.
lin_hamlib_com2_name = ""
#lin_hamlib_com2_name = "/tmp/QuiskTTY1"

## win_hamlib_com1_name		CAT serial port name, text
# Enter the name of the serial port that Quisk uses to connect to an external program like N1MM+ or WSJT-X.
# You must first create a pair of virtual serial ports with a program like vspMgr or HHD Software.
# Then enter the second name into the other program and specify a radio of type "Flex".  This control method is in addition to the
# "Hamlib NET rigctl" mechanism which is based on a network connection. Leave this blank
# to turn off the serial port. The port settings are 9600 baud, 8 bits of data, no parity and one stop bit.
win_hamlib_com1_name = ""
#win_hamlib_com1_name = "COM5"
#win_hamlib_com1_name = "COM6"

## win_hamlib_com2_name     CAT serial-2 name, text
# This is a second serial port for external control of Quisk. Use a different serial port pair.
win_hamlib_com2_name = ""
#win_hamlib_com2_name = "COM15"
#win_hamlib_com2_name = "COM16"


hamlib_com1_name = ""
hamlib_com2_name = ""


################ Keys
## hot_key_ptt1		PTT Key 1, keycode
# Set a keyboard shortcut that will press the PTT button.
# For a regular key, use the ord() of the key.  For example, ord('a') or ord('b').  For the space bar
# use ord(' ').  Then restart Quisk.
# If you do not want a hot key, set this to None.
# Do not choose a key that interferes with other features
# on your system such as system menus.
hot_key_ptt1 = None
#hot_key_ptt1 = ord(' ')
#hot_key_ptt1 = ord('z')
#hot_key_ptt1 = ord('a')
#hot_key_ptt1 = wx.WXK_F5

## hot_key_ptt2		PTT Key 2, keycode
# If the Control or Shift key must be pressed too, set that key modifier here.
# Otherwise, set NORMAL here.
# For example, if you want control-A, set CTRL in "PTT Key 2", and ord('a') in "PTT Key 1".
hot_key_ptt2 = wx.ACCEL_NORMAL
#hot_key_ptt2 = wx.ACCEL_CTRL
#hot_key_ptt2 = wx.ACCEL_SHIFT
#hot_key_ptt2 = wx.ACCEL_CTRL | wx.ACCEL_SHIFT
#hot_key_ptt2 = wx.ACCEL_ALT

## hot_key_ptt_toggle	PTT Key Toggle, boolean
# Set to True if you want PTT to remain on when you release the key.  A second key press will
# then release PTT.  This is toggle mode.  If False, you must keep pressing the key, and releasing
# it will release PTT.
# Changes are immediate (no need to restart).
hot_key_ptt_toggle = False
#hot_key_ptt_toggle = True

## hot_key_ptt_if_hidden	PTT Key if Hidden, boolean
# Set to True if you want PTT to be active when the Quisk window is not visible.
# Otherwise, the Quisk window must be active and on top.
hot_key_ptt_if_hidden = False
#hot_key_ptt_if_hidden = True




################ Windows
# Station info display configuration, thanks to DJ4CM.  This displays a window of station names
# below the graph frequency (X axis).

## station_display_lines		Number of station lines, integer
# The number of station info display lines below the graph X axis.
station_display_lines = 1
#station_display_lines = 0
#station_display_lines = 3

## display_fraction				Display fraction, number
# This is the fraction of spectrum to display from zero to one.  It causes the edges
# of the display to be suppressed.  For example, 0.85 displays the central 85% of the spectrum.
display_fraction = 1.00

## default_screen				Startup screen, text choice
# Select the default screen when Quisk starts.
default_screen = 'Graph'
#default_screen = 'WFall'
#default_screen = 'Config'

## graph_width					Startup graph width, number
# The width of the graph data as a fraction of the total screen size.  This
# controls the width of the Quisk window, but
# will be adjusted by Quisk to accommodate preferred FFT sizes.
# It can not be made too small because
# of the space needed for all the buttons.
graph_width = 0.8

## window_width					Window width pixels, integer
# The use of startup graph width provides an optimal size for PC screens.  But when running
# full screen, for example, on a tablet screen or a dedicated display, greater control
# is required.  These options exactly set the Quisk window geometry.  When window pixel width
# is used, graph width is ignored.  You may need to reduce button_font_size.  Use -1
# to ignore this feature, and use graph width.
window_width = -1
#window_width = 640

## window_height				Window height pixels, integer
# The use of startup graph width provides an optimal size for PC screens.  But when running
# full screen, for example, on a tablet screen or a dedicated display, greater control
# is required.  These options exactly set the Quisk window geometry.  When window pixel width
# is used, graph width is ignored.  You may need to reduce button_font_size.  Use -1
# to ignore this feature, and use graph width.
window_height = -1
#window_height = 480

## window_posX					Window X position, integer
# The use of startup graph width provides an optimal size for PC screens.  But when running
# full screen, for example, on a tablet screen or a dedicated display, greater control
# is required.  These options exactly set the Quisk window geometry.  When window pixel width
# is used, graph width is ignored.  You may need to reduce button_font_size.  Use -1
# to ignore this feature, and use graph width.
window_posX = -1
#window_posX = 0

## window_posY					Window Y position, integer
# The use of startup graph width provides an optimal size for PC screens.  But when running
# full screen, for example, on a tablet screen or a dedicated display, greater control
# is required.  These options exactly set the Quisk window geometry.  When window pixel width
# is used, graph width is ignored.  You may need to reduce button_font_size.  Use -1
# to ignore this feature, and use graph width.
window_posY = -1
#window_posY = 0

## button_layout				Button layout, text choice
# This option controls how many buttons are displayed on the screen.  The large screen
# layout is meant for a PC.  The small screen layout is meant for small touch screens, and
# small screens used in embedded systems.
button_layout = 'Large screen'
#button_layout = 'Small screen'


# These are the initial values for the Y-scale and Y-zero sliders for each screen.
# The sliders go from zero to 160.
graph_y_scale = 100
graph_y_zero  = 0
waterfall_y_scale = 80		# Initial value; new values are saved for each band
waterfall_y_zero  = 40		# Initial value; new values are saved for each band
waterfall_graph_y_scale = 100
waterfall_graph_y_zero = 60
scope_y_scale = 80
scope_y_zero  = 0			# Currently doesn't do anything
filter_y_scale = 90
filter_y_zero  = 0

# Select the way the waterfall screen scrolls:
# waterfall_scroll_mode = 0	#  scroll at a constant rate.
waterfall_scroll_mode = 1	# scroll faster at the top so that a new signal appears sooner.

# Select the initial size in pixels (minimum 1) of the graph at the top of the waterfall.
waterfall_graph_size = 80

# Quisk saves radio settings in a settings file.  The default directory is the same as the config
# file, and the file name is quisk_settings.json.  You can set a different name here.  If you dual
# boot Windows and Linux, you can set the same path in your Windows and Linux config files, so that
# settings are shared.  Even if Windows and Linux settings are shared, the sound device names and a
# few other settings are kept separate.
settings_file_path = ''
#settings_file_path = /path/to/my/file/quisk_settings.json




################ Timing

## lin_data_poll_usec			Hardware poll usecs, integer
# Quisk polls the hardware for samples at intervals.  This is the poll time in microseconds.
# A lower time reduces latency. A higher time is less taxing on the hardware.
#lin_data_poll_usec =  5000
#lin_data_poll_usec = 10000
#lin_data_poll_usec = 15000
#lin_data_poll_usec = 20000

## win_data_poll_usec			Hardware poll usecs, integer
# Quisk polls the hardware for samples at intervals.  This is the poll time in microseconds.
# A lower time reduces latency. A higher time is less taxing on the hardware.
#win_data_poll_usec = 15000
#win_data_poll_usec =  5000
#win_data_poll_usec = 10000
#win_data_poll_usec = 20000

if sys.platform == "win32":
  data_poll_usec = 20000	# poll time in microseconds
else:
  data_poll_usec = 5000		# poll time in microseconds

## keyupDelay			Keyup delay msecs, integer
# For the Hermes protocol including the Hermes-Lite2, this is the key-up hang time,
# the time in milliseconds 0 to 1023 to hold the T/R relay after the CW key goes up
# or the PTT button goes up. For all
# hardware, it adds a silent period to the audio after key up.
# A large key up delay may be needed to accomodate
# antenna switching or other requirements of your hardware.
# Changes are immediate (no need to restart).
keyupDelay = 23

## fft_size_multiplier		FFT size multiplier, integer
# The fft_size is the width of the data on the screen (about 800 to
# 1200 pixels) times the fft_size_multiplier.  Multiple FFTs are averaged
# together to achieve your graph refresh rate.  If fft_size_multiplier is
# too small you will get many fft errors.  You can specify fft_size_multiplier,
# or enter a large number (use 9999) to maximize it, or enter zero to let
# quisk calculate it for you.
# Your fft_size_multiplier should have many small factors.  Avoid 7 and 13, and
# use 8 or 12 instead.
# If your hardware can change the decimation, there are further compilcations.
# The FFT size is fixed, and only the average count can change to adjust the
# refresh rate.
fft_size_multiplier = 0

## graph_refresh			Graph refresh Hertz, integer
# The graph_refresh is the frequency at which the graph is updated,
# and should be about 5 to 10 Hertz.  Higher rates require more processor power.
graph_refresh = 7





################ Controls

## graph_peak_hold_1			Graph peak hold 1, number
# This controls the speed of the graph peak hold for the two settings
# of the Graph button.  Lower numbers give a longer time constant.
graph_peak_hold_1 = 0.25

## graph_peak_hold_2			Graph peak hold 2, number
# This controls the speed of the graph peak hold for the two settings
# of the Graph button.  Lower numbers give a longer time constant.
graph_peak_hold_2 = 0.10


## use_sidetone				Use sidetone, integer choice
# This controls whether Quisk will display a sidetone volume control "Sto",
# and whether Quisk will gererate a CW sidetone.
use_sidetone = 0
#use_sidetone = 1

## add_imd_button			Add IMD button, integer choice
# If you want Quisk to add a button to generate a 2-tone IMD test signal,
# set this to 1.
add_imd_button = 0
#add_imd_button = 1

## add_extern_demod			Add ext demod button, text
# If you want to write your own I/Q filter and demodulation module, set
# this to the name of the button to add, and change extdemod.c.
add_extern_demod = ""
#add_extern_demod = "WFM"

## add_fdx_button			Add FDX button, integer choice
# If you want Quisk to add a full duplex button (transmit and receive at the
# same time), set this to 1.
add_fdx_button = 0
#add_fdx_button = 1

## add_freedv_button		Add FreeDv button, integer choice
# These buttons add up to two additional mode buttons after CW, USB, etc.
# Set this to add the FDV mode button for digital voice:
add_freedv_button = 1
#add_freedv_button = 0

## freedv_tx_msg			FreeDv Tx message, text
# For freedv, this is the text message to send.
freedv_tx_msg = ''
#freedv_tx_msg = 'N2XXX Jim, New Jersey, USA \n'


# This is the list of FreeDV modes and their index number.  The starting mode is the first listed.
freedv_modes = (('Mode 1600', 0), ('Mode 700', 1), ('Mode 700B', 2),
		# ('Mode 2400A', 3), ('Mode 2400B', 4), ('Mode 800XA', 5),
		('Mode 700C', 6), ('Mode 700D', 7), ('Future8', 8), ('Future9', 9))

# These are the filter bandwidths for each mode.  Quisk has built-in optimized filters
# for these values, but you can change them if you want.
FilterBwCW	= (200, 400, 600, 1000, 1500, 3000)
FilterBwSSB	= (2000, 2200, 2500, 2800, 3000, 3300)
FilterBwAM	= (4000, 5000, 6000, 8000, 10000, 9000)
FilterBwFM	= (8000, 10000, 12000, 16000, 18000, 20000)
FilterBwIMD	= FilterBwSSB
FilterBwDGT	= (200, 400, 1500, 3200, 4800, 10000)
FilterBwEXT	= (8000, 10000, 12000, 15000, 17000, 20000)
FilterBwFDV	= (1500, 2000, 3000, '', '', '')

# If your hardware file defines the method OnButtonPTT(self, event), then Quisk will
# display a PTT button you can press.  The method must switch your hardware to
# transmit somehow, for example, by setting a serial port pin to high.

## spot_button_keys_tx			Key Tx on Spot, boolean
# If you want the Spot button to key the transmitter immediately when you press it, set this option.
# Your hardware must have a working PTT button for this to work.
spot_button_keys_tx = True
#spot_button_keys_tx = False



# Thanks to Christof, DJ4CM, for button fonts.
################ Fonts

## button_font_size				Button font size, integer
# If the Quisk screen is too wide or the buttons are too crowded, perhaps due to a low screen
# resolution, you can reduce the font sizes.
button_font_size = 10
#button_font_size = 9
#button_font_size = 8

## default_font_size			Default font size, integer
# These control the font size on the named screen.
default_font_size = 12

## status_font_size				Status font size, integer
# These control the font size on the named screen.
status_font_size = 14

## config_font_size				Config font size, integer
# These control the font size on the named screen.
config_font_size = 14

## graph_font_size				Graph font size, integer
# These control the font size on the named screen.
graph_font_size = 10

## graph_msg_font_size			Graph message font size, integer
# These control the font size on the named screen.
graph_msg_font_size = 14

## favorites_font_size			Favorites font size, integer
# These control the font size on the named screen.
favorites_font_size = 14

## lin_quisk_typeface				Typeface, text
# This controls the typeface used in fonts.  The objective is to choose an available font that
# offers good support for the Unicode characters used on buttons and windows.
#lin_quisk_typeface = ''

## win_quisk_typeface				Typeface, text
# This controls the typeface used in fonts.  The objective is to choose an available font that
# offers good support for the Unicode characters used on buttons and windows.
#win_quisk_typeface = 'Lucida Sans Unicode'
#win_quisk_typeface = 'Arial Unicode MS'

if sys.platform == "win32":
  quisk_typeface = 'Lucida Sans Unicode'
  #quisk_typeface = 'Arial Unicode MS'
else:
  quisk_typeface = ''

## use_unicode_symbols				Use Unicode symbols, boolean
# This controls whether the "U" unicode symbols or the "T" text symbols are used on buttons and windows.
# You can change the "U" and "T" symbols to anything you want in your config file.
use_unicode_symbols = True
#use_unicode_symbols = False

# These are the Unicode symbols used in the station window.  Thanks to Christof, DJ4CM.
Usym_stat_fav = unichr(0x2605)	# Symbol for favorites, a star
Usym_stat_mem = unichr(0x24C2)	# Symbol for memory stations, an "M" in a circle
#Usym_stat_dx = unichr(0x2691)	# Symbol for DX Cluster stations, a flag
Usym_stat_dx = unichr(0x25B2)	# Symbol for DX Cluster stations, a Delta
# These are the text symbols used in the station window.
Tsym_stat_fav = 'F'
Tsym_stat_mem = 'M'
Tsym_stat_dx = 'Dx'
#
# These are the Unicode symbols to display on buttons.  Thanks to Christof, DJ4CM.
Ubtn_text_range_dn = unichr(0x2B07)						# Down band, left arrow
Ubtn_text_range_up = unichr(0x2B06)						# Up band, right arrow
Ubtn_text_play = unichr(0x25BA)							# Play button
Ubtn_text_rec = unichr(0x25CF)							# Record button, a filled dot
Ubtn_text_file_rec = "File " + unichr(0x25CF)           # Record to file
Ubtn_text_file_play = "File " + unichr(0x25BA)          # Play from file
Ubtn_text_fav_add    = unichr(0x2605) + unichr(0x2191)  # Add to favorites
Ubtn_text_fav_recall = unichr(0x2605) + unichr(0x2193)  # Jump to favorites screen
Ubtn_text_mem_add  = unichr(0x24C2) + unichr(0x2191)    # Add to memory
Ubtn_text_mem_next = unichr(0x24C2) + unichr(0x27B2)    # Next memory
Ubtn_text_mem_del  = unichr(0x24C2) + unichr(0x2613)    # Delete from memory
# These are the text symbols to display on buttons.
Tbtn_text_range_dn = "Dn"
Tbtn_text_range_up = "Up"
Tbtn_text_play = "Tmp Play"
Tbtn_text_rec = "Tmp Rec"
Tbtn_text_file_rec = "File Rec"
Tbtn_text_file_play = "File Play"
Tbtn_text_fav_add    = ">Fav"
Tbtn_text_fav_recall = "Fav"
Tbtn_text_mem_add  = "Save"
Tbtn_text_mem_next = "Next"
Tbtn_text_mem_del  = "Del"

## decorate_buttons				Decorate buttons, boolean
# This controls whether to add the button decorations that mark cycle and adjust buttons.
decorate_buttons = True
#decorate_buttons = False

btn_text_cycle = unichr(0x21B7)			# Character to display on multi-push buttons
btn_text_cycle_small = unichr(0x2193)	# Smaller version when there is little space
btn_text_switch = unichr(0x21C4)		# Character to switch left-right

## color_scheme				Color scheme, text choice
# This controls the color scheme used by Quisk.  The default color scheme is A, and you can change this scheme
# in your config file.  Other color schemes are available here.
color_scheme = 'A'
#color_scheme = 'B'
#color_scheme = 'C'

## waterfall_palette			Waterfall colors, text choice
# This controls the colors used in the waterfall.  The default color scheme is A, and you can change this scheme
# in your config file.  Other color schemes are available here.
waterfall_palette = 'A'
#waterfall_palette = 'B'
#waterfall_palette = 'C'




################ Colors
# Thanks to Steve Murphy, KB8RWQ for the patch adding additional color control.
# Thanks to Christof, DJ4CM for the patch adding additional color control. 
# Define colors used by all widgets in wxPython colour format.
# This is the default color scheme, color scheme A.  You can change these colors in your config file:
color_bg			= 'light steel blue'	# Lower screen background
color_bg_txt		= 'black'             	# Lower screen text color
color_graph			= 'lemonchiffon1'		# Graph background
color_config2		= 'lemonchiffon3'		# color in tab row of config screen
color_gl			= 'grey'				# Lines on the graph
color_graphticks	= 'black'				# Graph ticks
color_graphline		= '#005500'				# graph data line color
color_graphlabels	= '#555555'				# graph label color
color_btn			= 'steelblue2'			# button color
color_check_btn		= 'yellow2'				# color of a check button when it is checked
color_cycle_btn		= 'goldenrod3'			# color of a cycle button when it is checked
color_adjust_btn	= 'orange3'				# color of an adjustable button when it is checked
color_test			= 'hot pink'			# color of a button used for test (turn off for tx)
color_freq			= 'lightcyan1'			# background color of frequency and s-meter
color_freq_txt      = 'black'               # text color of frequency display
color_entry			= color_freq			# frequency entry box
color_entry_txt     = 'black'		        # text color of entry box
color_enable		= 'black'				# text color for an enabled button
color_disable		= 'white'				# text color for a disabled button
color_popchoice		= 'maroon'				# text color for button that pops up a row of buttons
color_bandwidth		= 'lemonchiffon3'		# color for bandwidth display; thanks to WB4JFI
color_txline		= 'red'					# vertical line color for tx in graph
color_rxline		= 'green'				# vertical line color for rx in graph
color_graph_msg_fg	= 'black'				# text messages on the graph screen
color_graph_msg_bg	= 'lemonchiffon2'		# background of text messages on the graph screen

# This color scheme B, a dark color scheme designed by Steve Murphy, KB8RWQ.
# Additional colors added by N2ADR.
color_scheme_B = {
'color_bg'			: '#111111',
'color_bg_txt'		: 'white',
'color_graph'		: '#111111',
'color_config2'		: '#111111',
'color_gl'			: '#555555',
'color_graphticks'	: '#DDDDDD',
'color_graphline'	: '#00AA00',
'color_graphlabels'	: '#FFFFFF',
'color_btn'			: '#666666',
'color_check_btn'	: '#996699',
'color_cycle_btn'	: '#666699',
'color_adjust_btn'	: '#669999',
'color_test'		: 'hot pink',
'color_freq'		: '#333333',
'color_freq_txt'	: 'white',
'color_entry'		: '#333333',
'color_entry_txt'	: 'white',
'color_enable'		: 'white',
'color_disable'		: 'black',
'color_popchoice'	: 'maroon',
'color_bandwidth'	: '#333333',
'color_txline'		: 'red',
'color_rxline'		: 'green',
'color_graph_msg_fg'		: 'white',
'color_graph_msg_bg'		: '#111111',
}

# This is color scheme C:
#######################################################################################
#
#   Color scheme designed by Sergio, IK8HTM.  04/06/2016
#   '#red red green green blue blue' x00 to xFF
#	'#FFFFFF' = white
#   	'#000000' = black
#
#######################################################################################
color_scheme_C = {
'color_bg'			: '#123456',
'color_bg_txt'		: '#FFFFFF',
'color_graph'		: 'lightcyan3',
'color_config2'		: '#0000FF',
'color_gl'			: '#555555',
'color_graphticks'	: '#DDDDDD',
'color_graphline'	: '#00AA00',
'color_graphlabels'	: '#000000',
'color_btn'			: '#223344',
'color_check_btn'	: '#A07315',
'color_cycle_btn'	: '#0031C4',
'color_adjust_btn'	: '#669999',
'color_test'		: '#E73EE7',
'color_freq'		: '#333333',
'color_freq_txt'	: '#FEF80A',
'color_entry'		: '#333333',
'color_entry_txt'	: '#FEF80A',
'color_enable'		: '#FFFFFF',
'color_disable'		: '#000000',
'color_popchoice'	: '#D76B00',
'color_bandwidth'	: 'lemonchiffon1',
'color_txline'		: '#FF0000',
'color_rxline'		: '#3CC918',
'color_graph_msg_fg'	: '#000000',
'color_graph_msg_bg'	: 'lemonchiffon2',
}
#############################################################################################


# These are the palettes for the waterfall.  The one used is named waterfallPallette,
# so to use a different one, overwrite this name in your configuration file.
waterfallPalette = (
     (  0,   0,   0,   0),
     ( 36,  85,   0, 255),
     ( 73, 153,   0, 255),
     (109, 255,   0, 128),
     (146, 255, 119,   0),
     (182,  85, 255, 100),
     (219, 255, 255,   0),
     (255, 255, 255, 255)
      )
digipanWaterfallPalette = (
     (  0,   0,   0,   0),
     ( 32,   0,   0,  62),
     ( 64,   0,   0, 126),
     ( 96, 145, 142,  96),
     (128, 181, 184,  48),
     (160, 223, 226, 105),
     (192, 254, 254,   4),
     (255, 255,  58,   0)
      )

waterfallPaletteB = (	# from David Fainitski
(0, 0, 0, 0),
(13, 0, 14, 14),
(26, 0, 40, 40),
(39, 0, 73, 73),
(43, 0, 94, 94),
(56, 0, 115, 121),
(69, 0, 87, 190),
(72, 0, 110, 252),
(85, 0, 166, 252),
(98, 0, 216, 252),
(112, 0, 247, 234),
(125, 2, 255, 124),
(138, 5, 255, 64),
(151, 154, 255, 0),
(164, 219, 255, 0),
(177, 247, 250, 0),
(190, 254, 233, 0),
(214, 254, 185, 0),
(227, 255, 125, 0),
(241, 255, 59, 0),
(255, 255, 0, 0)
) 

waterfallPaletteC = (	# from David Fainitski
(0, 0, 0, 0),
(32, 0, 25, 25),
(64, 6, 58, 41),
(96, 16, 78, 43),
(128, 29, 120, 41),
(160, 51, 144, 35),
(192, 116, 141, 43),
(224, 195, 198, 35),
(255, 245, 99, 3)
) 

# This is the data used to draw colored lines on the frequency X axis to
# indicate CW and Phone sub-bands.  You can make it anything you want.
# These are the colors used for sub-bands:
CW		= '#FF4444'		# General class CW
eCW		= '#FF8888'		# Extra class CW
Phone	= '#4444FF'		# General class phone
ePhone	= '#8888FF'		# Extra class phone
# ARRL band plan special frequencies
Data	= '#FF9900'
DxData	= '#CC6600'
RTTY	= '#FF9900'
SSTV	= '#FFFF00'
AM		= '#00FF00'
Packet	= '#00FFFF'
Beacons	= '#66FF66'
Satellite	= '#22AA88'
Repeater	= '#AA00FF'	# Repeater outputs
RepInput	= '#AA88FF'	# Repeater inputs
Simplex	= '#00FF44'
Special	= 'hot pink'
Other	= '#888888'
# Colors start at the indicated frequency and continue until the
# next frequency.  The special color "None" turns off color.
#




################ Bands
# Band plans vary by country, so they can be changed here.
# To change BandPlan in your config file, first remove any frequencies in the range
# you want to change; then add your frequencies; and then sort the list.  Or you could just
# replace the whole list.
# These are the suppressed carrier frequencies for 60 meters
freq60 = (5330500, 5346500, 5357000, 5371500, 5403500)
# Band plan
BandPlan = [
  # Test display of colors
  #[      0, CW], [  50000, eCW], [ 100000, Phone], [ 150000, ePhone], [ 200000, Data], [ 250000, DxData], [ 300000, RTTY], [ 350000, SSTV],
  #[ 400000, AM], [ 450000, Packet], [ 500000, Beacons], [ 550000, Satellite], [ 600000, Repeater], [ 650000, RepInput], [ 700000, Simplex],
  #[ 750000, Other], [ 800000, Special], [ 850000, None],
  # 137k
  [  130000, Data],
  [  150000, None],
  # 500k
  [  490000, Data],
  [  510000, None],
  # 160 meters
  [ 1800000, Data],
  [ 1809000, Other],
  [ 1811000, CW],
  [ 1843000, Phone],
  [ 1908000, Other],
  [ 1912000, Phone],
  [ 1995000, Other],
  [ 2000000, None],
  # 80 meters
  [ 3500000, eCW],
  [ 3525000, CW],
  [ 3570000, Data],
  [ 3589000, DxData],
  [ 3591000, Data],
  [ 3600000, ePhone],
  [ 3790000, Other],
  [ 3800000, Phone],
  [ 3844000, SSTV],
  [ 3846000, Phone],
  [ 3880000, AM],
  [ 3890000, Phone],
  [ 4000000, None],
  # 60 meters
  [ freq60[0], Phone],
  [ freq60[0] + 2800, None],
  [ freq60[1], Phone],
  [ freq60[1] + 2800, None],
  [ freq60[2], Phone],
  [ freq60[2] + 2800, None],
  [ freq60[3], Phone],
  [ freq60[3] + 2800, None],
  [ freq60[4], Phone],
  [ freq60[4] + 2800, None],
  # 40 meters
  [ 7000000, eCW],
  [ 7025000, CW],
  [ 7039000, DxData],
  [ 7041000, CW],
  [ 7080000, Data],
  [ 7125000, ePhone],
  [ 7170000, SSTV],
  [ 7172000, ePhone],
  [ 7175000, Phone],
  [ 7285000, AM],
  [ 7295000, Phone],
  [ 7300000, None],
  # 30 meters
  [10100000, CW],
  [10130000, RTTY],
  [10140000, Packet],
  [10150000, None],
  # 20 meters
  [14000000, eCW],
  [14025000, CW],
  [14070000, RTTY],
  [14095000, Packet],
  [14099500, Other],
  [14100500, Packet],
  [14112000, CW],
  [14150000, ePhone],
  [14225000, Phone],
  [14229000, SSTV],
  [14231000, Phone],
  [14281000, AM],
  [14291000, Phone],
  [14350000, None],
  # 17 meters
  [18068000, CW],
  [18100000, RTTY],
  [18105000, Packet],
  [18110000, Phone],
  [18168000, None],
  # 15 meters
  [21000000, eCW],
  [21025000, CW],
  [21070000, RTTY],
  [21110000, CW],
  [21200000, ePhone],
  [21275000, Phone],
  [21339000, SSTV],
  [21341000, Phone],
  [21450000, None],
  # 12 meters
  [24890000, CW],
  [24920000, RTTY],
  [24925000, Packet],
  [24930000, Phone],
  [24990000, None],
  # 10 meters
  [28000000, CW],
  [28070000, RTTY],
  [28150000, CW],
  [28200000, Beacons],
  [28300000, Phone],
  [28679000, SSTV],
  [28681000, Phone],
  [29000000, AM],
  [29200000, Phone],
  [29300000, Satellite],
  [29520000, Repeater],
  [29590000, Simplex],
  [29610000, Repeater],
  [29700000, None],
  # 6 meters
  [50000000, Beacons],
  [50100000, Phone],
  [54000000, None],
  # 4 meters
  [70000000, Phone],
  [70500000, None],
  # 2 meters
  [144000000, CW],
  [144200000, Phone],
  [144275000, Beacons],
  [144300000, Satellite],
  [144380000, Special],
  [144400000, Satellite],
  [144500000, RepInput],
  [144900000, Other],
  [145100000, Repeater],
  [145500000, Other],
  [145800000, Satellite],
  [146010000, RepInput],
  [146400000, Simplex],
  [146510000, Special],     # Simplex calling frequency
  [146530000, Simplex],
  [146610000, Repeater],
  [147420000, Simplex],
  [147600000, RepInput],
  [148000000, None],
  # 1.25 meters
  [222000000, Phone],
  [222250000, RepInput],
  [223400000, Simplex],
  [223520000, Data],
  [223640000, Repeater],
  [225000000, None],
  #70 centimeters
  [420000000, SSTV],
  [432000000, Satellite],
  [432070000, Phone],
  [432300000, Beacons],
  [432400000, Phone],
  [433000000, Repeater],
  [435000000, Satellite],
  [438000000, Repeater],
  [445900000, Simplex],
  [445990000, Special],     # Simplex calling frequency
  [446010000, Simplex],
  [446100000, Repeater],
  [450000000, None],
  # 33 centimeters
  [902000000, Other],
  [928000000, None],
  # 23 centimeters
  [1240000000, Other],
  [1300000000, None],
  # 13 centimeters
  [2300000000, Other],
  [2450000000, None],
  # 9 centimeters
  [3300000000, Other],
  [3500000000, None],
  # 5 centimeters
  [5650000000, Other],
  [5925000000, None],
  # 3 centimeters
  [10000000000, Other],
  [10500000000, None],
  ]

## BandEdge 	Band Edge, dict
# For each band, this dictionary gives the lower and upper band edges.  Frequencies
# outside these limits will not be remembered as the last frequency in the band.
BandEdge = {
	'137k':( 136000,   138000),	'500k':( 400000,   600000),
	'160':( 1800000,  2000000),	'80' :( 3500000,  4000000),
	'60' :( 5300000,  5430000),	'40' :( 7000000,  7300000),
	'30' :(10100000, 10150000),	'20' :(14000000, 14350000),	
	'17' :(18068000, 18168000), '15' :(21000000, 21450000),
	'12' :(24890000, 24990000),	'10' :(28000000, 29700000),
	'6'     :(  50000000,   54000000),
	'4'     :(  70000000,   70500000),
	'2'     :( 144000000,  148000000),
    '1.25'  :( 222000000,  225000000),
    '70cm'  :( 420000000,  450000000),
    '33cm'  :( 902000000,  928000000),
    '23cm'  :(1240000000, 1300000000),
    '13cm'  :(2300000000, 2450000000),
    '9cm'   :(3300000000, 3500000000),
    '5cm'   :(5650000000, 5925000000),
    '3cm'  :(10000000000,10500000000),
	}

# For the Time band, this is the center frequency, tuning frequency and mode:
bandTime = [
	( 2500000-10000, 10000, 'AM'),
	( 3330000-10000, 10000, 'AM'),
	( 5000000-10000, 10000, 'AM'),
	( 7335000-10000, 10000, 'AM'),
	(10000000-10000, 10000, 'AM'),
	(14670000-10000, 10000, 'AM'),
	(15000000-10000, 10000, 'AM'),
	(20000000-10000, 10000, 'AM'),
	]

## bandLabels		Band Buttons, list
# This is the list of band buttons that Quisk displays, and it should have
# a length of 14 or less.  Empty buttons can have a null string "" label.
# Note that the 60 meter band and the Time band have buttons that support
# multiple presses.
bandLabels = [
	'Audio', '160', '80', ('60',) * 5, '40', '30', '20', '17',
	'15', '12', '10', ('Time',) * len(bandTime)]

# This is a dictionary of shortcut keys for each band. If you do not want a shortcut, use ''. The shortcut
# character will be underlined in the label if present.
bandShortcuts = {'Audio':'', '160':'1', '80':'8', '60':'6', '40':'4', '30':'3', '20':'2', '17':'7',
	'15':'5', '12':'1', '10':'0', 'Time':'e', '6':'6', '4':'4', '2':'2', '1.25':'5', '70cm':'7',
	'33cm':'3', '23cm':'', '13cm':'', '9cm':'', '5cm':'', '3cm':''}

## bandTransverterOffset	Transverter Offset, dict
# If you use a transverter, you need to tune your hardware to a frequency lower than
# the frequency displayed by Quisk.  For example, if you have a 2 meter transverter,
# you may need to tune your hardware from 28 to 30 MHz to receive 144 to 146 MHz.
# Enter the transverter offset in Hertz in this dictionary.  For this to work, your
# hardware must support it.  Currently, the HiQSDR, SDR-IQ and SoftRock are supported.
bandTransverterOffset = {
#    '2': 144000000 - 28000000
}




################ Obsolete
filter_display = 1	# Display the filter bandwidth on the graph screen; 0 or 1; thanks to WB4JFI
# For each band, this dictionary gives the initial center frequency, tuning
# frequency as an offset from the center frequency, and the mode.  This is
# no longer too useful because the persistent_state feature saves and then
# overwrites these values anyway.
bandState = {'Audio':(0, 0, 'LSB'),
      '160':( 1890000, -10000, 'LSB'), '80' :( 3660000, -10000, 'LSB'),
      '60' :( 5370000,   1500, 'USB'), '40' :( 7180000, -5000, 'LSB'),  '30':(10120000, -10000, 'CWL'),
      'Time':( 5000000, 0, 'AM')}
for band in BandEdge:
  f1, f2 = BandEdge[band]
  if f1 > 13500000:
    f = (f1 + f2) // 2
    f = (f + 5000) // 10000
    f *= 10000
    bandState[band] = (f, 10000, 'USB')
# Select the method to test the state of the key; see is_key_down.c
key_method = ""					# No keying, or internal method
# key_method = "/dev/parport0"	# Use the named parallel port
# key_method = "/dev/ttyS0"	# Use the named serial port
# key_method = "192.168.1.44"	# Use UDP from this address
#
# Quisk can save its current state in a file on exit, and restore it when you restart.
# State includes band, frequency and mode, but not every item of state (not screen).
# The file is .quisk_init.pkl in the same directory as your config file.  If this file
# becomes corrupted, just delete it and it will be reconstructed.
#persistent_state = False
persistent_state = True
# Select the default mode when Quisk starts (overruled by persistent_state):
# default_mode = 'FM'
default_mode = 'USB'
# If you use a soundcard with Ethernet control of the VFO, set these parameters:
rx_ip = ""							# Receiver IP address for VFO control
# This determines what happens when you tune by dragging the mouse.  The correct
# choice depends on how your hardware performs tuning.  You may want to use a
# custom hardware file with a custom ChangeFrequency() method too.
mouse_tune_method = 0	# The Quisk tune frequency changes and the VFO frequency is unchanged.
#mouse_tune_method = 1	# The Quisk tune frequency is unchanged and the VFO changes.
# configurable mouse wheel thanks to DG7MGY
mouse_wheelmod = 50		# Round frequency when using mouse wheel (50 Hz)
