# Please do not change this hardware control module for Quisk.
# This hardware module is for receivers with a fixed VFO, such as
# the SoftRock.  Change your VFO frequency below.

# If you want to use this hardware module, specify it in quisk_conf.py.
# import quisk_hardware_fixed as quisk_hardware
# See quisk_hardware_model.py for documentation.

from quisk_hardware_model import Hardware as BaseHardware

class Hardware(BaseHardware):
  def __init__(self, app, conf):
    BaseHardware.__init__(self, app, conf)
    self.vfo = self.conf.fixed_vfo_freq		# Fixed VFO frequency in Hertz
    self.tune = self.vfo + 10000		# Current tuning frequency in Hertz
  def ChangeFrequency(self, tune, vfo, source='', band='', event=None):
    # Change and return the tuning and VFO frequency.  See quisk_hardware_model.py.
    self.tune = tune
    return tune, self.vfo
  def ReturnFrequency(self):
    # Return the current tuning and VFO frequency.  See quisk_hardware_model.py.
    return self.tune, self.vfo

