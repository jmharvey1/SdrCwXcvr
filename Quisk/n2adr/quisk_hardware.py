# This is the hardware file from my shack, which controls various hardware.
# The files to control my 2010 transceiver and for the improved version HiQSDR
# are in the package directory HiQSDR.

from hiqsdr.quisk_hardware import Hardware as BaseHw
from n2adr import station_hardware

class Hardware(BaseHw):
  def __init__(self, app, conf):
    BaseHw.__init__(self, app, conf)
    self.GUI = None
    self.vfo_frequency = 0		# current vfo frequency
    self.rf_gain_labels = ('RF 0 dB', 'RF +16')
    self.rf_gain = 0	# Preamp or attenuation in dB; changed via app.Hardware
    # Other hardware
    self.anttuner = station_hardware.AntennaTuner(app, conf)	# Control the antenna tuner
    #self.lpfilter = station_hardware.LowPassFilter(app, conf)	# Control LP filter box
    #self.hpfilter = station_hardware.HighPassFilter(app, conf)	# Control HP filter box
    self.controlbox = station_hardware.ControlBox(app, conf)	# Control my Station Control Box
    self.v2filter = station_hardware.FilterBoxV2(app, conf)	# Control V2 filter box
  def open(self):
    if False:
      from n2adr.station_hardware import StationControlGUI
      self.GUI = StationControlGUI(self.application.main_frame, self, self.application, self.conf)
      self.GUI.Show()
    self.anttuner.open()
    return BaseHw.open(self)
  def close(self):
    self.anttuner.close()
    self.controlbox.close()
    return BaseHw.close(self)
  def ChangeFilterFrequency(self, tx_freq):
    if tx_freq and tx_freq > 0:
      if self.GUI:
        self.GUI.SetTxFreq(tx_freq)
      else:
        self.anttuner.SetTxFreq(tx_freq)
        self.v2filter.SetTxFreq(tx_freq)
  def ChangeFrequency(self, tx_freq, vfo_freq, source='', band='', event=None):
    if source == 'MouseBtn1' and self.application.mode in ('LSB', 'USB', 'AM', 'FM', 'FDV-U', 'FDV-L'):
      tx_freq = (tx_freq + 500) // 1000 * 1000
    self.ChangeFilterFrequency(tx_freq)
    return BaseHw.ChangeFrequency(self, tx_freq, vfo_freq, source, band, event)
  def ChangeBand(self, band):
    # band is a string: "60", "40", "WWV", etc.
    self.anttuner.ChangeBand(band)
    #self.lpfilter.ChangeBand(band)
    #self.hpfilter.ChangeBand(band)
    self.v2filter.ChangeBand(band)
    ret = BaseHw.ChangeBand(self, band)
    self.CorrectSmeter()
    return ret
  def HeartBeat(self):	# Called at about 10 Hz by the main
    self.anttuner.HeartBeat()
    #self.lpfilter.HeartBeat()
    #self.hpfilter.HeartBeat()
    self.v2filter.HeartBeat()
    self.controlbox.HeartBeat()
    return BaseHw.HeartBeat(self)
  def OnSpot(self, level):
    # level is -1 for Spot button Off; else the Spot level 0 to 1000.
    self.anttuner.OnSpot(level)
    return BaseHw.OnSpot(self, level)
  def OnButtonRfGain(self, event):
    #self.hpfilter.OnButtonRfGain(event)
    self.v2filter.OnButtonRfGain(event)
    self.CorrectSmeter()
  def CorrectSmeter(self):	# S-meter correction can change with band or RF gain
    if self.band == '40':				# Basic S-meter correction by band
      self.correct_smeter = 20.5
    else:
      self.correct_smeter = 20.5
    self.correct_smeter -= self.rf_gain / 6.0		# Correct S-meter for RF gain
    self.application.waterfall.ChangeRfGain(self.rf_gain)	# Waterfall colors are constant
  def OnButtonPTT(self, event):
    self.controlbox.OnButtonPTT(event)
    return BaseHw.OnButtonPTT(self, event)
