# Please do not change this hardware control module.
# It provides support for the SDR-IQ by RfSpace.

from __future__ import print_function

import _quisk as QS
try:
  import sdriq
except ImportError:
  from sdriqpkg import sdriq

from quisk_hardware_model import Hardware as BaseHardware

class Hardware(BaseHardware):
  decimations = [1250, 600, 500, 360]
  def __init__(self, app, conf):
    BaseHardware.__init__(self, app, conf)
    self.clock = conf.sdriq_clock
    self.rf_gain_labels = ('RF +30', 'RF +20', 'RF +10', 'RF 0 dB')
    if conf.fft_size_multiplier == 0:
      conf.fft_size_multiplier = 3		# Set size needed by VarDecim
  def open(self):
    return sdriq.open_samples()		# Return a config message
  def close(self):
    sdriq.close_samples()
  def OnButtonRfGain(self, event):
    """Set the SDR-IQ preamp gain and attenuator state.

    sdriq.gain_sdriq(gstate, gain)
    gstate == 0:  Gain must be 0, -10, -20, or -30
    gstate == 1:  Attenuator is on  and gain is 0 to 127 (7 bits)
    gstate == 2:  Attenuator is off and gain is 0 to 127 (7 bits)
    gain for 34, 24, 14, 4 db is 127, 39, 12, 4.
    """
    btn = event.GetEventObject()
    n = btn.index
    if n == 0:
      sdriq.gain_sdriq(2, 127)
    elif n == 1:
      sdriq.gain_sdriq(2, 39)
    elif n == 2:
      sdriq.gain_sdriq(2, 12)
    elif n == 3:
      sdriq.gain_sdriq(1, 12)
    else:
      print ('Unknown RfGain')
  def ChangeFrequency(self, tune, vfo, source='', band='', event=None):
    if vfo:
      sdriq.freq_sdriq(vfo - self.transverter_offset)
    return tune, vfo
  def ChangeBand(self, band):
    # band is a string: "60", "40", "WWV", etc.
    BaseHardware.ChangeBand(self, band)
    btn = self.application.BtnRfGain
    if btn:
      if band in ('160', '80', '60', '40'):
        btn.SetLabel('RF +10', True)
      elif band in ('20',):
        btn.SetLabel('RF +20', True)
      else:
        btn.SetLabel('RF +20', True)
  def VarDecimGetChoices(self):		# return text labels for the control
    l = []		# a list of sample rates
    for dec in self.decimations:
      l.append(str(int(float(self.clock) / dec / 1e3 + 0.5)))
    return l
  def VarDecimGetLabel(self):		# return a text label for the control
    return "Sample rate ksps"
  def VarDecimGetIndex(self):		# return the current index
    return self.index
  def VarDecimSet(self, index=None):		# set decimation, return sample rate
    if index is None:		# initial call to set decimation before the call to open()
      rate = self.application.vardecim_set		# May be None or from different hardware
      try:
        dec = int(float(self.clock / rate + 0.5))
        self.index = self.decimations.index(dec)
      except:
        try:
          self.index = self.decimations.index(self.conf.sdriq_decimation)
        except:
          self.index = 0
    else:
      self.index = index
    dec = self.decimations[self.index]
    sdriq.set_decimation(dec)
    return int(float(self.clock) / dec + 0.5)
