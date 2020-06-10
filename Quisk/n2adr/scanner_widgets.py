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
    row = 4			# The next available row
    b = app.QuiskPushbutton(frame, None, 'Tune')
    bw, bh = b.GetMinSize()
    b.Enable(0)
    gbs.Add(b, (row, 0), (1, 2), flag=wx.EXPAND)
    b = app.QuiskPushbutton(frame, None, '')
    gbs.Add(b, (row, 2), (1, 2), flag=wx.EXPAND)
    b = app.QuiskPushbutton(frame, None, '')
    gbs.Add(b, (row, 4), (1, 2), flag=wx.EXPAND)
    b = self.btnScanner = app.QuiskCheckbutton(frame, self.OnBtnScanner, text='Scanner', use_right=True)
    self.scan_timer = wx.Timer(b)	# timed events for the scanner
    b.Bind(wx.EVT_TIMER, self.OnTimerEvent)
    gbs.Add(b, (row, 6), (1, 2), flag=wx.EXPAND)
    b = self.btnNext = app.QuiskPushbutton(frame, self.OnBtnNext, 'Next', True)
    gbs.Add(b, (row, 8), (1, 2), flag=wx.EXPAND)
    b = app.QuiskCheckbutton(frame, self.OnBtnRptr, text='Rptr')
    b.SetValue(True, True)
    gbs.Add(b, (row, 10), (1, 2), flag=wx.EXPAND)
    self.swr_label = app.QuiskText(frame, 'Watts 000   SWR 10.1  Zh Ind 22 Cap 33   Freq 28100 (7777)', bh)
    gbs.Add(self.swr_label, (row, 15), (1, 12), flag=wx.EXPAND)
#  Example of a horizontal slider:
#    lab = wx.StaticText(frame, -1, 'Preamp', style=wx.ALIGN_CENTER)
#    gbs.Add(lab, (5,0), flag=wx.EXPAND)
#    sl = wx.Slider(frame, -1, 1024, 0, 2048)	# parent, -1, initial, min, max
#    gbs.Add(sl, (5,1), (1, 5), flag=wx.EXPAND)
#    sl.Bind(wx.EVT_SCROLL, self.OnPreamp)
#  def OnPreamp(self, event):
#    print event.GetPosition()
  def UpdateText(self, text):
    self.swr_label.SetLabel(text)
  def OnBtnRptr(self, event):
    btn = event.GetEventObject()
    if btn.GetValue():
      self.config.freq_spacing = 5000
    else:
      self.config.freq_spacing = 0
  def OnBtnNext(self, event):
    self.direction = self.btnNext.direction			# +1 for left -> go up; -1 for down
    self.keep_going = wx.GetKeyState(wx.WXK_SHIFT)	# if Shift is down, move to next band
    self.scanner = False
    if self.keep_going:
      if not self.ScanScreen(event):
        self.MoveVfo(event)
        self.scan_timer.Start(500)
    else:
      self.ScanScreen(event)
  def ScanScreen(self, event):	# Look for signals on the current screen
    lst = self.hardware.rpt_freq_list
    app = self.application
    vfo = app.VFO
    tx_freq = vfo + app.txFreq
    sample_rate = app.sample_rate
    limit = int(sample_rate / 2.0 * self.config.display_fraction * 0.95)	# edge of screen
    self.scan_n1 = None
    self.scan_n = None
    for n in range(len(lst)):
      if lst[n] > vfo - limit and self.scan_n1 is None:
        self.scan_n1 = n	# inclusive
      if lst[n] >= tx_freq and self.scan_n is None:
        self.scan_n = n
      if lst[n] > vfo + limit:
        break
      self.scan_n2 = n	# inclusive
    if self.scan_n is None:
      self.scan_n = self.scan_n1
    if self.direction > 0:	# left click; go up
      seq = range(self.scan_n + 1, self.scan_n2 + 1)
      if not self.keep_going:
        seq += range(self.scan_n1, self.scan_n)
    else:					# right click; go down
      seq = range(self.scan_n - 1, self.scan_n1 - 1, -1)
      if not self.keep_going:
        seq += range(self.scan_n2, self.scan_n, -1)
    for n in seq:
      freq = lst[n]
      if not QS.get_squelch(freq - vfo):
        app.ChangeHwFrequency(freq - vfo, vfo, 'Repeater', event)
        return True		# frequency was changed
    return False	# frequency was not changed
  def MoveVfo(self, event):		# Move the VFO to look for further signals
    lst = self.hardware.rpt_freq_list
    app = self.application
    vfo = app.VFO
    tx_freq = vfo + app.txFreq
    sample_rate = app.sample_rate
    if self.direction > 0:	# left click; go up
      n = self.scan_n2 + 1
      if n >= len(lst):
        n = 0
      freq = lst[n]
      vfo = freq + sample_rate * 4 / 10
      app.ChangeHwFrequency(freq - vfo, vfo, 'Repeater', event)
    else:					# right click; go down
      n = self.scan_n1 - 1
      if n < 0:
        n = len(lst) - 1
      freq = lst[n]
      vfo = freq - sample_rate * 4 / 10
      app.ChangeHwFrequency(freq - vfo, vfo, 'Repeater', event)
  def OnBtnScanner(self, event):
    self.direction = self.btnScanner.direction		# +1 for left -> go up; -1 for down
    self.keep_going = wx.GetKeyState(wx.WXK_SHIFT)	# if Shift is down, move to next band
    self.scanner = True
    if self.btnScanner.GetValue():
      self.btnNext.Enable(0)
      if self.keep_going:
        if not self.ScanScreen(event):
          self.MoveVfo(event)
      else:
        self.ScanScreen(event)
      self.scan_timer.Start(500)
    else:
      self.btnNext.Enable(1)
      self.scan_timer.Stop()
  def OnTimerEvent(self, event):
    if QS.get_squelch(self.application.txFreq):
      if self.keep_going:
        if not self.ScanScreen(event):
          self.MoveVfo(event)
      else:
        self.ScanScreen(event)
    elif not self.scanner:
      self.scan_timer.Stop()
