# Please do not change this widgets module for Quisk.  Instead copy
# it to your own quisk_widgets.py and make changes there.
#
# This module is used to add extra widgets to the QUISK screen.

import wx
import _quisk as QS
import math

class BottomWidgets:	# Add extra widgets to the bottom of the screen
  def __init__(self, app, hardware, conf, frame, gbs, vertBox):
    self.hardware = hardware
    #self.info_text = app.QuiskText(frame, 'Info', app.button_height)
    #gbs.Add(self.info_text, (4, 0), (1, 27), flag=wx.EXPAND)

