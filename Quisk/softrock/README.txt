This directory has config, hardware and widget files for several models
of SoftRock.  An alternative is to use the VK6JBL hardware file.
It controls the SoftRock using the usbsoftrock program.

If your SoftRock has a fixed frequency crystal, use config_fixed, and
enter the crystal frequency divided by four as fixed_vfo_freq.

Recent SoftRock hardware is controlled by USB.  Our USB access is provided by
Python's pyusb module version 1.0, and that is based on libusb.  Check
the config screen for error messages.  If you get "USB device not found" then
the SoftRock is not connected to USB, or the vendor or product ID's are not correct.
If you get "No permission", then you don't have permission to access libusb.  Quisk
will probably run as root, but running as root is a bad idea.  Instead try adding this:

SUBSYSTEM=="usb", ATTR{idVendor}=="16c0" , ATTR{idProduct}=="05dc", MODE="0666", GROUP="dialout"

to a file /etc/udev/local.rules and re-booting.  This works on my Debian system. 
Take a look at libusb.txt; or ask Google.  If your SoftRock model is not listed,
try the closest model.  I don't have every SoftRock available to test, but I will
try to help if you send me an email.  Please provide your firmware version, which
is shown on the config screen.

On both Debian and Windows, if I unplug my RxTx Ensemble and plug it in again, it is
not recognized.  The vendor and product ID's are both zero.  I guess the workaround
is to leave it plugged in.

If your SoftRock has an Si570 chip and is USB controlled, it may require calibration
and initialization.  I use the CFGSR program by Fred, PE0FKO.

If you have an RxTx Ensemble, and you want to monitor the key status for CW operation,
set key_poll_msec in your configuration file.  Note that Quisk does not have an internal
keyer.  Connect a straight key or your external keyer to the tip of the paddle connector.
The Quisk CW sidetone does not work well due to the time lag in the audio system.  Please use a
keyer with its own sidetone.  Quisk uses semi break-in for SoftRock hardware.  You can specify
the hang time in seconds in your config file with key_hang_time.  So you need:
    key_poll_msec = 5
    key_hang_time = 0.7
