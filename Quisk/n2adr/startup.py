#! /usr/bin/python

# All QUISK software is Copyright (C) 2006-2011 by James C. Ahlstrom.
# This free software is licensed for use under the GNU General Public
# License (GPL), see http://www.opensource.org.
# Note that there is NO WARRANTY AT ALL.  USE AT YOUR OWN RISK!!

"Select the desired hardware, and start Quisk"

import sys, wx, subprocess, os

Choices = [
(' My Transceiver', 'n2adr/quisk_conf.py', ''),
(' VHF/UHF Receiver', 'n2adr/uhfrx_conf.py', ''),
(' Softrock Rx Ensemble', 'softrock/conf_rx_ensemble2.py', 'n2adr/conf2.py'),
(' Softrock Rx/Tx Ensemble', 'softrock/conf_rx_tx_ensemble.py', 'n2adr/conf6.py'),
(' Plain Sound Card, Rx only', 'n2adr/conf2.py', ''),
(' Test microphone sound', 'n2adr/conf4.py', ''),
(' SDR-IQ, receive only, antenna to RF input', 'quisk_conf_sdriq.py', 'n2adr/conf2.py'),
(' AOR AR8600 with IF to my hardware', 'n2adr/quisk_conf_8600.py', ''),
(' AOR AR8600 with IF to SDR-IQ', 'quisk_conf_sdr8600.py', 'n2adr/conf2.py'),
(' Fldigi with my transceiver', 'n2adr/quisk_conf.py', 'n2adr/conf5.py'),
(' Freedv.org Rx with my transceiver', 'n2adr/quisk_conf.py', 'n2adr/conf7.py'),
(' Hermes-Lite', 'hermes/quisk_conf.py', 'n2adr/conf3.py'),
(' Odyssey', 'odyssey/quisk_conf.py', 'n2adr/conf1.py'),
(' My Transceiver to Hermes-Lite', 'Quisk2Hermes', ''),
]

if sys.platform == 'win32':
  os.chdir('C:\\pub\\quisk')
  exe = "C:\\python27\\pythonw.exe"
else:
  os.chdir('/home/jim/pub/quisk')
  exe = "/usr/bin/python"

class ListBoxFrame(wx.Frame):
  def __init__(self):
    wx.Frame.__init__(self, None, -1, 'Select Hardware')
    font = wx.Font(14, wx.FONTFAMILY_SWISS, wx.NORMAL, wx.FONTWEIGHT_NORMAL)
    self.SetFont(font)
    charx = self.GetCharWidth()
    chary = self.GetCharHeight()
    width = 0
    height = chary * 2
    tlist = []
    for txt, conf1, conf2 in Choices:
      text = "%s, %s" % (txt, conf1)
      if conf2:
        text = "%s, %s" % (text, conf2)
      tlist.append(text)
      w, h = self.GetTextExtent(text)
      width = max(width, w)
      height += h
    width += 3 * chary
    lb = wx.ListBox(self, -1, (0, 0), (width, height), tlist, wx.LB_SINGLE)
    lb.SetSelection(0)
    lb.SetFont(font)
    lb.Bind(wx.EVT_LISTBOX_DCLICK, self.OnDClick, lb)
    lb.Bind(wx.EVT_KEY_DOWN, self.OnChar)
    self.SetClientSize((width, height))
  def OnDClick(self, event):
    lb = event.GetEventObject()
    index = lb.GetSelection()
    text, conf1, conf2 = Choices[index]
    if conf1 == "Quisk2Hermes":
      subprocess.Popen([exe, 'quisk.py', '-c', 'n2adr/quisk_conf.py', '--local', 'Q2H'])
      subprocess.Popen([exe, 'quisk.py', '-c', 'hermes/quisk_conf.py', '--config2', 'n2adr/conf3A.py', '--local', 'Q2H'])
    else:
      cmd = [exe, 'quisk.py', '-c', conf1]
      if conf2:
        cmd = cmd + ['--config2', conf2]
      subprocess.Popen(cmd)
    self.Destroy()
  def OnChar(self, event):
    if event.GetKeyCode() == 13:
      self.OnDClick(event)
    else:
      event.Skip()

class App(wx.App):
  def __init__(self):
    if sys.stdout.isatty():
      wx.App.__init__(self, redirect=False)
    else:
      wx.App.__init__(self, redirect=True)
  def OnInit(self):
    frame = ListBoxFrame()
    frame.Show()
    return True

app = App()
app.MainLoop()
