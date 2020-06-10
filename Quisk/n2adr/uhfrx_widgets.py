# Please do not change this widgets module for Quisk.  Instead copy
# it to your own quisk_widgets.py and make changes there.
#
# This module is used to add extra widgets to the QUISK screen.

from __future__ import print_function

import wx, time
import _quisk as QS

class BottomWidgets:	# Add extra widgets to the bottom of the screen
  def __init__(self, app, hardware, conf, frame, gbs, vertBox):
    self.config = conf
    self.hardware = hardware
    self.application = app
    self.correct_screen = None
    row = 4			# The next available row
    b = app.QuiskPushbutton(frame, hardware.TestVfoPlus, 'Adf+')
    bw, bh = b.GetMinSize()
    gbs.Add(b, (row, 0), flag=wx.EXPAND)
    b = app.QuiskPushbutton(frame, hardware.TestVfoMinus, 'Adf-')
    gbs.Add(b, (row, 1), flag=wx.EXPAND)
    b = app.QuiskPushbutton(frame, self.OnBtnCorrect, 'Corr')
    gbs.Add(b, (row, 2), flag=wx.EXPAND)
    self.status_label = app.QuiskText(frame, 'Ready', bh)
    gbs.Add(self.status_label, (row, 3), (1, 24), flag=wx.EXPAND)
  def UpdateText(self, text):
    self.status_label.SetLabel(text)
  def OnBtnCorrect(self, event):
    if self.correct_screen:
      self.correct_screen.Raise()
    else:
      self.correct_screen = QCorrect(self, self.application.width)

class QCorrect(wx.Frame):
  """Create a window with DC adjustment controls"""
  f_DcI = "DC adjustment for In-Phase %.6f"
  f_DcQ = "DC adjustment for Quadrature %.6f"
  def __init__(self, parent, width):
    self.parent = parent
    self.application = parent.application
    self.config = parent.config
    self.hardware = parent.hardware
    t = "DC Null Adjustment"
    wx.Frame.__init__(self, self.application.main_frame, -1, t, pos=(50, 100), style=wx.CAPTION)
    panel = wx.Panel(self)
    self.MakeControls(panel, width)
    self.Show()
  def MakeControls(self, panel, width):		# Make controls for DC adjustment
    self.old_DcI = self.DcI = self.hardware.DcI
    self.old_DcQ = self.DcQ = self.hardware.DcQ
    self.hardware.NewUdpCorrect(self.DcI, self.DcQ)
    sl_max = width * 4 // 10		# maximum +/- value for slider
    self.dc_scale = float(0.3) / sl_max
    font = wx.Font(self.config.default_font_size, wx.FONTFAMILY_SWISS, wx.NORMAL,
          wx.FONTWEIGHT_NORMAL, face=self.config.quisk_typeface)
    chary = self.GetCharHeight()
    y = chary * 3 // 10
    self.t_DcI = wx.StaticText(panel, -1, self.f_DcI % self.old_DcI, pos=(0, y))
    self.t_DcI.SetFont(font)
    y += self.t_DcI.GetSizeTuple()[1]
    self.DcI1 = wx.Slider(panel, -1, 0, -sl_max, sl_max,
      pos=(0, y), size=(width, -1))
    y += self.DcI1.GetSizeTuple()[1]
    self.DcI2 = wx.Slider(panel, -1, 0, -sl_max, sl_max,
      pos=(0, y), size=(width, -1))
    y += self.DcI2.GetSizeTuple()[1]
    self.PositionDcI(self.old_DcI)
    self.t_DcQ = wx.StaticText(panel, -1, self.f_DcQ % self.old_DcQ, pos=(0, y))
    self.t_DcQ.SetFont(font)
    y += self.t_DcQ.GetSizeTuple()[1]
    self.DcQ1 = wx.Slider(panel, -1, 0, -sl_max, sl_max,
      pos=(0, y), size=(width, -1))
    y += self.DcQ1.GetSizeTuple()[1]
    self.DcQ2 = wx.Slider(panel, -1, 0, -sl_max, sl_max,
      pos=(0, y), size=(width, -1))
    y += self.DcQ2.GetSizeTuple()[1]
    sv = self.application.QuiskPushbutton(panel, self.OnBtnSave, 'Save')
    cn = self.application.QuiskPushbutton(panel, self.OnBtnCancel, 'Cancel')
    w, h = cn.GetSizeTuple()
    sv.SetSize((w, h))
    y += h // 4
    x = (width - w * 3) // 4
    sv.SetPosition((x, y))
    cn.SetPosition((x*3 + w*2, y))
    sv.SetBackgroundColour('light blue')
    cn.SetBackgroundColour('light blue')
    y += h
    y += h // 4
    self.DcI1.SetBackgroundColour('aquamarine')
    self.DcI2.SetBackgroundColour('orange')
    self.DcQ1.SetBackgroundColour('aquamarine')
    self.DcQ2.SetBackgroundColour('orange')
    self.PositionDcQ(self.old_DcQ)
    self.SetClientSizeWH(width, y)
    self.DcI1.Bind(wx.EVT_SCROLL, self.OnChange)
    self.DcI2.Bind(wx.EVT_SCROLL, self.OnFineDcI)
    self.DcQ1.Bind(wx.EVT_SCROLL, self.OnChange)
    self.DcQ2.Bind(wx.EVT_SCROLL, self.OnFineDcQ)
  def PositionDcI(self, dc):	# set pos1, pos2 for I
    pos2 = round(dc / self.dc_scale)
    remain = dc - pos2 * self.dc_scale
    pos1 = round(remain / self.dc_scale * 50.0)
    self.DcI1.SetValue(pos1)
    self.DcI2.SetValue(pos2)
  def PositionDcQ(self, dc):	# set pos1, pos2 for Q
    pos2 = round(dc / self.dc_scale)
    remain = dc - pos2 * self.dc_scale
    pos1 = round(remain / self.dc_scale * 50.0)
    self.DcQ1.SetValue(pos1)
    self.DcQ2.SetValue(pos2)
  def OnChange(self, event):
    dc = self.dc_scale * self.DcI1.GetValue() / 50.0 + self.dc_scale * self.DcI2.GetValue()
    if abs(dc) < self.dc_scale * 3.0 / 50.0:
      dc = 0.0
    self.t_DcI.SetLabel(self.f_DcI % dc)
    self.DcI = dc
    dc = self.dc_scale * self.DcQ1.GetValue() / 50.0 + self.dc_scale * self.DcQ2.GetValue()
    if abs(dc) < self.dc_scale * 3.0 / 50.0:
      dc = 0.0
    self.t_DcQ.SetLabel(self.f_DcQ % dc)
    self.DcQ = dc
    self.hardware.NewUdpCorrect(self.DcI, self.DcQ)
  def OnFineDcI(self, event):		# re-center the fine slider when the coarse slider is adjusted
    dc = self.dc_scale * self.DcI1.GetValue() / 50.0 + self.dc_scale * self.DcI2.GetValue()
    self.PositionDcI(dc)
    self.OnChange(event)
  def OnFineDcQ(self, event):	# re-center the fine slider when the coarse slider is adjusted
    dc = self.dc_scale * self.DcQ1.GetValue() / 50.0 + self.dc_scale * self.DcQ2.GetValue()
    self.PositionDcQ(dc)
    self.OnChange(event)
  def OnBtnSave(self, event):
    self.config.CorrectTxDc[self.hardware.band] = (self.hardware.tx_frequency * 1E-6, self.DcI, self.DcQ)
    self.hardware.PrintUdpCorrect()
    self.parent.correct_screen = None
    self.Destroy()
  def OnBtnCancel(self, event=None):
    self.hardware.NewUdpCorrect(self.old_DcI, self.old_DcQ)
    self.parent.correct_screen = None
    self.Destroy()

