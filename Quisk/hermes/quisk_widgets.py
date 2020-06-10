# Please do not change this widgets module for Quisk.  Instead copy
# it to your own quisk_widgets.py and make changes there.
#
# This module is used to add extra widgets to the QUISK screen.

from __future__ import print_function

import wx

class BottomWidgets:	# Add extra widgets to the bottom of the screen
  def __init__(self, app, hardware, conf, frame, gbs, vertBox):
    self.config = conf
    self.hardware = hardware
    self.application = app
    self.start_row = app.widget_row			# The first available row
    self.start_col = app.button_start_col	# The start of the button columns
    if hardware.hermes_board_id == 0x06:		# Hermes-Lite
      self.Widgets_0x06(app, hardware, conf, frame, gbs, vertBox)
    else:
      self.Widgets_dflt(app, hardware, conf, frame, gbs, vertBox)
  def Widgets_0x06(self, app, hardware, conf, frame, gbs, vertBox):
    b = app.QuiskCheckbutton(frame, self.OnAGC, 'RfAgc')
    gbs.Add(b, (self.start_row, self.start_col), (1, 2), flag=wx.EXPAND)
    init = 10
    sl = app.SliderBoxHH(frame, 'RfLna %d dB', init, -12, 48, self.OnLNA, True)
    hardware.ChangeLNA(init)
    gbs.Add(sl, (self.start_row, self.start_col + 2), (1, 8), flag=wx.EXPAND)
    self.num_rows_added = 1
  def Widgets_dflt(self, app, hardware, conf, frame, gbs, vertBox):
    pass
  def OnAGC(self, event):
    btn = event.GetEventObject()
    value = btn.GetValue()
    self.hardware.ChangeAGC(value)
  def OnLNA(self, event):
    sl = event.GetEventObject()
    value = sl.GetValue()
    self.hardware.ChangeLNA(value)
