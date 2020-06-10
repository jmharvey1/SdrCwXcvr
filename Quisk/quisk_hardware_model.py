# Please do not change this hardware control module for Quisk.
# It is a basic module providing almost no features.  You should
# still use it a a base class for your own hardware modules.

# If you want to use a hardware module different from the default
# module quisk_hardware_model, then specify it in your quisk_conf.py:
#     import quisk_hardware_myhardware as quisk_hardware
# or if it is in the n2adr (or other) package:
#     from n2adr import quisk_hardware

# A custom hardware module should subclass this module; start it with:
#    from quisk_hardware_model import Hardware as BaseHardware
#    class Hardware(BaseHardware):
#      def __init__(self, app, conf):
#        BaseHardware.__init__(self, app, conf)
#          ###   your module starts here

# Alternatively, you can define a class named "Hardware" in your config file,
# and that class will be used instead of a hardware file.  This is recommended
# only for simple hardware needs.  The class should start the same as above.

class Hardware:
  def __init__(self, app, conf):
    self.application = app			# Application instance (to provide attributes)
    self.conf = conf				# Config file module
    self.rf_gain_labels = ()		# Do not add the Rf Gain button
    self.correct_smeter = conf.correct_smeter		# Default correction for S-meter
    self.use_sidetone = conf.use_sidetone           # Copy from the config file
    self.transverter_offset = 0		# Calculate the transverter offset in Hertz for each band
  def open(self):			# Called once to open the Hardware
    # Return an informative message for the config screen
    t = "Capture from sound card %s." % self.conf.name_of_sound_capt
    return t
  def close(self):			# Called once to close the Hardware
    pass
  def ChangeFrequency(self, tune, vfo, source='', band='', event=None):
    # Change and return the tuning and VFO frequency in Hertz.  The VFO frequency is the
    # frequency in the center of the display; that is, the RF frequency corresponding to an
    # audio frequency of zero Hertz.  The tuning frequency is the RF frequency indicated by
    # the tuning line on the display, and is equivalent to the transmit frequency.  The quisk
    # receive frequency is the tuning frequency plus the RIT (receive incremental tuning).
    # If your hardware will not change to the requested frequencies, return different
    # frequencies.
    # The source is a string indicating the source of the change:
    #   BtnBand       A band button
    #   BtnUpDown     The band Up/Down buttons
    #   FreqEntry     The user entered a frequency in the box
    #   MouseBtn1     Left mouse button press
    #   MouseBtn3     Right mouse button press
    #   MouseMotion   The user is dragging with the left button
    #   MouseWheel    The mouse wheel up/down
    #   NewDecim      The decimation changed
    # For "BtnBand", the string band is in the band argument.
    # For the mouse events, the handler event is in the event argument.
    return tune, vfo
  def ReturnFrequency(self):
    # Return the current tuning and VFO frequency.  If neither have changed,
    # you can return (None, None).  This is called at about 10 Hz by the main.
    # return (tune, vfo)	# return changed frequencies
    return None, None		# frequencies have not changed
  def ReturnVfoFloat(self):
    # Return the accurate VFO frequency as a floating point number.
    # You can return None to indicate that the integer VFO frequency is valid.
    return None
  def ChangeMode(self, mode):		# Change the tx/rx mode
    # mode is a string: "USB", "AM", etc.
    pass
  def ChangeBand(self, band):
    # band is a string: "60", "40", "WWV", etc.
    try:
      self.transverter_offset = self.conf.bandTransverterOffset[band]
    except:
      self.transverter_offset = 0
  def OnBtnFDX(self, is_fdx):   # Status of FDX button, 0 or 1
    pass
  def HeartBeat(self):	# Called at about 10 Hz by the main
    pass
  # The "VarDecim" methods are used to change the hardware decimation rate.
  # If VarDecimGetChoices() returns any False value, no other methods are called.
  def VarDecimGetChoices(self):	# Return a list/tuple of strings for the decimation control.
    return False	# Return a False value for no decimation changes possible.
  def VarDecimGetLabel(self):	# Return a text label for the decimation control.
    return ''
  def VarDecimGetIndex(self):	# Return the index 0, 1, ... of the current decimation.
    return 0		# This is called before open() to initialize the control.
  def VarDecimSet(self, index=None):	# Called when the control is operated.
    # Change the decimation here, and return the sample rate.  The index is 0, 1, 2, ....
    # Called with index == None before open() to set the initial sample rate.
    # Note:  The last used value is available as self.application.vardecim_set if
    #        the persistent state option is True.  If the value is unavailable for
    #        any reason, self.application.vardecim_set is None.
    return 48000
  def VarDecimRange(self):  # Return the lowest and highest sample rate.
    return (48000, 960000)

