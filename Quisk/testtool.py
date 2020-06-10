#! /usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division


import sys, os
import threading
import wx, wx.lib.stattext, wx.lib.colourdb, wx.html
import math, cmath, time, traceback, string, pickle
#from types import *
#import configure
from quisk_widgets import *
import time
#sys.path.append('./libso')
#print(sys.path)
import configure
from filters import Filters
import _quisk as QS

global DEBUG
global button_bezel
DEBUG = 1
button_bezel = 3 #needed by quisk_widgets.py when makewidgetglobals() fails
##ConfigPath = ""
##sound_capt = "hw:1,0"
##sound_play= "pulse"
##data_poll_usec = 5000
##latency_millisecs = 150
##microphone_name = ""
##tx_ip = ""
##tx_audio_port = 0
###sample_rate = 96000
##mic_channel_I = 0
##mic_channel_Q = 0
##mic_play_chan_I = 0
##mic_play_chan_Q = 1
##channel_i = 0
##channel_q = 1
##mic_out_volume = 0.7
##name_of_mic_play = ""
##mic_playback_rate = 48000
##key_method = "/dev/ttyS0"
##key_method = ""
##fail= 0


# Command line parsing: be able to specify the config file.
from optparse import OptionParser
parser = OptionParser()
parser.add_option('-c', '--config', dest='config_file_path',
		help='Specify the configuration file path')
parser.add_option('', '--config2', dest='config_file_path2', default='',
		help='Specify a second configuration file to read after the first')
parser.add_option('-a', '--ask', action="store_true", dest='AskMe', default=False,
		help='Ask which radio to use when starting')
parser.add_option('', '--local', dest='local_option', default='',
		help='Specify a custom option that you have programmed yourself')
argv_options = parser.parse_args()[0]
ConfigPath = argv_options.config_file_path	# Get config file path
ConfigPath2 = argv_options.config_file_path2
DefaultConfigDir = os.path.expanduser('~')
if not ConfigPath:
    ConfigPath = os.path.join(DefaultConfigDir, ".quisk_conf.py")


##############################################################################################
class A(object):
    def __init__(self):
        self.rate_min =-1
        self.rate_max =-1
        self.sample_rate =-1
        self.chan_min =-1
        self.chan_max =-1
        self.msg1 ="No Msg"
        self.unused =-1
        self.err_msg ="No Msg"
        self.read_error =-1
        self.write_error =-1
        self.underrun_error =-1
        self.latencyCapt =-1
        self.latencyPlay =-1
        self.interupts =-1
        self.fft_error =-1
        self.mic_max_display =-1
        self.data_poll_usec =-1
    def myprint(self, title):
        print("************************************")
        print("%s" %title)
        for attr, value in self.__dict__.iteritems():
          print( "%s: %s" %(attr, value))
        print("************************************")  

class SoundThread(threading.Thread): #vna thread but is the exact same as the quisk thread
  """Create a second (non-GUI) thread to read samples."""
  def __init__(self):
    self.do_init = 1
    self.a = A()
    threading.Thread.__init__(self)
    self.doQuit = threading.Event()
    self.doQuit.clear()
  def run(self):
    """Read, process, play sound; then notify the GUI thread to check for FFT data."""
    if self.do_init:	# Open sound using this thread
      self.do_init = 0
      QS.start_sound()
      #wx.CallAfter(application.PostStartup)
      (self.a.rate_min, self.a.rate_max, self.a.sample_rate, self.a.chan_min, self.a.chan_max,
         self.a.msg1, self.a.unused, self.a.err_msg,
          self.a.read_error,  self.a.write_error, self.a.underrun_error,
          self.a.latencyCapt, self.a.latencyPlay, self.a.interupts, self.a.fft_error, self.a.mic_max_display,
          self.a.data_poll_usec
      ) = QS.get_state()
      self.a.myprint("SoundThread Start_sound State:")
    while not self.doQuit.isSet():
      #print("Read_sound() START")
      QS.read_sound()  
      wx.CallAfter(application.OnReadSound)
    QS.close_sound()
  def stop(self):
    """Set a flag to indicate that the sound thread should end."""
    self.doQuit.set()
    
###########################################################################################

##class HelpScreen(wx.html.HtmlWindow):
##  """Create the screen for the Help button."""
##  def __init__(self, parent, width, height):
##    wx.html.HtmlWindow.__init__(self, parent, -1, size=(width, height))
##    if "gtk2" in wx.PlatformInfo:
##      self.SetStandardFonts()
##    self.SetFonts("", "", [10, 12, 14, 16, 18, 20, 22])
##    # read in text from file help.html in the directory of this module
##    self.LoadFile('help_vna.html')
##  def OnLinkClicked(self, link):
##    webbrowser.open(link.GetHref(), new=2)    


class GraphDisplay(wx.Window): ##JMH Taken from QUISK
  """Display the FFT graph within the graph screen."""
  def __init__(self, parent, x, y, graph_width, height, chary):
    wx.Window.__init__(self, parent,
       pos = (x, y),
       size = (graph_width, height),
       style = wx.NO_BORDER)
    self.parent = parent
    self.chary = chary
    self.graph_width = graph_width
    self.display_text = ""
    self.line = [(0, 0), (1,1)]		# initial fake graph data
    self.SetBackgroundColour(conf.color_graph)
    self.Bind(wx.EVT_PAINT, self.OnPaint)
    self.Bind(wx.EVT_LEFT_DOWN, parent.OnLeftDown)
    self.Bind(wx.EVT_RIGHT_DOWN, parent.OnRightDown)
    self.Bind(wx.EVT_LEFT_UP, parent.OnLeftUp)
    self.Bind(wx.EVT_MOTION, parent.OnMotion)
    self.Bind(wx.EVT_MOUSEWHEEL, parent.OnWheel)
    self.tune_tx = graph_width // 2	# Current X position of the Tx tuning line
    self.tune_rx = 0				# Current X position of Rx tuning line or zero
    self.scale = 20				# pixels per 10 dB
    self.peak_hold = 9999		# time constant for holding peak value
    self.height = 10
    self.y_min = 1000
    self.y_max = 0
    self.max_height = application.screen_height
    self.backgroundPen = wx.Pen(self.GetBackgroundColour(), 1)
    self.tuningPenTx = wx.Pen(conf.color_txline, 1)
    self.tuningPenRx = wx.Pen(conf.color_rxline, 1)
    self.backgroundBrush = wx.Brush(self.GetBackgroundColour())
    self.filterBrush = wx.Brush(conf.color_bandwidth, wx.SOLID)#wx.Brush(conf.color_bandwidth, wx.SOLID)
    self.horizPen = wx.Pen(conf.color_gl, 1, wx.SOLID)
    self.font = wx.Font(conf.graph_msg_font_size, wx.FONTFAMILY_SWISS, wx.NORMAL,
          wx.FONTWEIGHT_NORMAL, False, conf.quisk_typeface)
    self.SetFont(self.font)
    if sys.platform == 'win32':
      self.Bind(wx.EVT_ENTER_WINDOW, self.OnEnter)
##    print("HHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHH")  
##    print(wxVersion)
##    print("HHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHH")
##    if wxVersion in ('2', '3'):
    self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
##    else:
##      self.SetBackgroundStyle(wx.BG_STYLE_PAINT)
  def OnEnter(self, event):
    if not application.w_phase:
      self.SetFocus()	# Set focus so we get mouse wheel events
  def OnPaint(self, event):
    #print 'GraphDisplay', self.GetUpdateRegion().GetBox()
    dc = wx.AutoBufferedPaintDC(self)
    dc.Clear()
    # Draw the tuning line and filter display to the screen.
    # If self.tune_rx is zero, draw the Rx filter at the Tx tuning line. There is no separate Rx display.
    # Otherwise draw both an Rx and Tx tuning display.
    self.DrawFilter(dc)
    dc.SetPen(wx.Pen(conf.color_graphline, 1))
    dc.DrawLines(self.line)
    dc.SetPen(self.horizPen)
    for y in self.parent.y_ticks:
      dc.DrawLine(0, y, self.graph_width, y)	# y line
    if self.display_text:
      dc.SetFont(self.font)
      dc.SetTextBackground(conf.color_graph_msg_bg)
      dc.SetTextForeground(conf.color_graph_msg_fg)
      dc.SetBackgroundMode(wx.SOLID)
      dc.DrawText(self.display_text, 0, 0)
  def DrawFilter(self, dc):
    dc.SetPen(wx.TRANSPARENT_PEN)
    dc.SetLogicalFunction(wx.COPY)
    scale = 1.0 / self.parent.zoom / self.parent.sample_rate * self.graph_width
    dc.SetBrush(self.filterBrush)
    if self.tune_rx:
      x, w, rit = self.parent.GetFilterDisplayXWR(rx_filters=False)
      dc.DrawRectangle(self.tune_tx + x, 0, w, self.height)
      x, w, rit = self.parent.GetFilterDisplayXWR(rx_filters=True)
      dc.DrawRectangle(self.tune_rx + rit + x, 0, w, self.height)
      dc.SetPen(self.tuningPenRx)
      dc.DrawLine(self.tune_rx, 0, self.tune_rx, self.height)
    else:
      x, w, rit = self.parent.GetFilterDisplayXWR(rx_filters=True)
      dc.DrawRectangle(self.tune_tx + rit + x, 0, w, self.height)
    dc.SetPen(self.tuningPenTx)
    dc.DrawLine(self.tune_tx, 0, self.tune_tx, self.height)
    return rit
  def SetHeight(self, height):
    self.height = height
    self.SetSize((self.graph_width, height))
  def OnGraphData(self, data):
    x = 0
    for y in data:	# y is in dB, -130 to 0
      y = self.zeroDB - int(y * self.scale / 10.0 + 0.5)
      try:
        y0 = self.line[x][1]
      except IndexError:
        self.line.append([x, y])
      else:
        if y > y0:
          y = min(y, y0 + self.peak_hold)
        self.line[x] = [x, y]
      x = x + 1
    self.Refresh()
  def SetTuningLine(self, tune_tx, tune_rx):
    dc = wx.ClientDC(self)
    rit = self.parent.GetFilterDisplayRit() #JMH 20190803 commented out
    # Erase the old display
    dc.SetPen(self.backgroundPen)
    if self.tune_rx:
      dc.DrawLine(self.tune_rx, 0, self.tune_rx, self.height)
    dc.DrawLine(self.tune_tx, 0, self.tune_tx, self.height)
    # Draw a new display
    if self.tune_rx:
      dc.SetPen(self.tuningPenRx)
      dc.DrawLine(tune_rx, 0, tune_rx, self.height)
    dc.SetPen(self.tuningPenTx)
    dc.DrawLine(tune_tx, 0, tune_tx, self.height)
    self.tune_tx = tune_tx
    self.tune_rx = tune_rx
    
class GraphScreen(wx.Window):
  """Display the graph screen X and Y axis, and create a graph display."""
##  def __init__(self, parent, data_width, graph_width, fltr_disp, in_splitter=0):  
  def __init__(self, parent, data_width, graph_width, fltr_disp, in_splitter=0):
    wx.Window.__init__(self, parent, pos = (0, 0))
    self.fltr_disp = fltr_disp #JMH not used but added to support old class definition
    self.in_splitter = in_splitter	# Are we in the top of a splitter window? JMH Not used in the testtool app
    self.split_unavailable = False		# Are we a multi receive graph or waterfall window?
    if in_splitter:
      self.y_scale = conf.waterfall_graph_y_scale
      self.y_zero = conf.waterfall_graph_y_zero
    else:
      self.y_scale = conf.graph_y_scale
      self.y_zero = conf.graph_y_zero
    self.stopRndfeq = 0 #JMH 20181226 added to support "auto 0 beat" feature
    self.y_ticks = []
    self.VFO = 0
    self.filter_mode = 'AM'
    self.filter_bandwidth = 0
    self.filter_center = 0
    self.ritFreq = 0				# receive incremental tuning frequency offset
    self.mouse_x = 0
    self.WheelMod = conf.mouse_wheelmod		# Round frequency when using mouse wheel
    self.txFreq = 0
    self.sample_rate = application.sample_rate
    self.zoom = 1.0
    self.zoom_deltaf = 0
    self.data_width = data_width
    self.graph_width = graph_width
    self.doResize = False
    self.pen_tick = wx.Pen(conf.color_graphticks, 1)
    self.pen_label = wx.Pen(conf.color_graphlabels, 1)
    self.font = wx.Font(conf.graph_font_size, wx.FONTFAMILY_SWISS, wx.NORMAL,
          wx.FONTWEIGHT_NORMAL, False, conf.quisk_typeface)
    self.SetFont(self.font)
    w = self.GetCharWidth() * 14 // 10
    h = self.GetCharHeight()
    self.charx = w
    self.chary = h
    self.tick = max(2, h * 3 // 10)
    self.originX = w * 5
    self.offsetY = h + self.tick
    self.width = self.originX + self.graph_width + self.tick + self.charx * 2
    self.height = (application.screen_height * 3 // 10)
    self.x0 = self.originX + self.graph_width // 2		# center of graph
    self.tuningX = self.x0
    self.originY = 10
    self.zeroDB = 10	# y location of zero dB; may be above the top of the graph
    self.scale = 10
    self.mouse_is_rx = False
    self.SetSize((self.width, self.height))
    self.SetSizeHints(self.width, 1, self.width)
    self.SetBackgroundColour(conf.color_graph)
    self.backgroundBrush = wx.Brush(conf.color_graph)
    self.Bind(wx.EVT_SIZE, self.OnSize)
    self.Bind(wx.EVT_PAINT, self.OnPaint)
    self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
    self.Bind(wx.EVT_RIGHT_DOWN, self.OnRightDown)
    self.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
    self.Bind(wx.EVT_MOTION, self.OnMotion)
    self.Bind(wx.EVT_MOUSEWHEEL, self.OnWheel)
    self.MakeDisplay()
  def MakeDisplay(self):
    self.display = GraphDisplay(self, self.originX, 0, self.graph_width, 5, self.chary)
    self.display.zeroDB = self.zeroDB
  def SetDisplayMsg(self, text=''):
    self.display.display_text = text
    self.display.Refresh()
  def ScrollMsg(self, chars):	# Add characters to a scrolling message
    self.display.display_text = self.display.display_text + chars
    self.display.display_text = self.display.display_text[-50:]
    self.display.Refresh()
  def OnPaint(self, event):
    dc = wx.PaintDC(self)
    dc.SetBackground(self.backgroundBrush)
    dc.Clear()
    dc.SetFont(self.font)
    dc.SetTextForeground(conf.color_graphlabels)
    self.MakeYTicks(dc)
    self.MakeXTicks(dc)
  def OnIdle(self, event):
    if self.doResize:
      self.ResizeGraph()
  def OnSize(self, event):
    self.doResize = True
    event.Skip()
  def ResizeGraph(self):
    """Change the height of the graph.

    Changing the width interactively is not allowed because the FFT size is fixed.
    Call after changing the zero or scale to recalculate the X and Y axis marks.
    """
    w, h = self.GetClientSize()
    self.height = h - (self.chary)		# Leave space for X scale
    self.originY = self.height - self.offsetY
    if self.originY < 0:
      self.originY = 0
    self.MakeYScale()
    self.display.SetHeight(self.originY)
    self.display.scale = self.scale
    self.doResize = False
    self.Refresh()
  def ChangeYscale(self, y_scale):
    self.y_scale = y_scale
    self.doResize = True
  def ChangeYzero(self, y_zero):
    self.y_zero = y_zero
    self.doResize = True
  def ChangeZoom(self, zoom, deltaf):
    self.zoom = zoom
    self.zoom_deltaf = deltaf
    self.doResize = True
  def MakeYScale(self):
    chary = self.chary
    scale = (self.originY - chary)  * 10 // (self.y_scale + 20)	# Number of pixels per 10 dB
    scale = max(1, scale)
    q = (self.originY - chary ) // scale // 2
    zeroDB = chary + q * scale - self.y_zero * scale // 10
    if zeroDB > chary:
      zeroDB = chary
    self.scale = scale
    self.zeroDB = zeroDB
    self.display.zeroDB = self.zeroDB
    QS.record_graph(self.originX, self.zeroDB, self.scale)
  def MakeYTicks(self, dc):
    chary = self.chary
    x1 = self.originX - self.tick * 3	# left of tick mark
    x2 = self.originX - 1		# x location of y axis
    x3 = self.originX + self.graph_width	# end of graph data
    dc.SetPen(self.pen_tick)
    dc.DrawLine(x2, 0, x2, self.originY + 1)	# y axis
    y = self.zeroDB
    del self.y_ticks[:]
    y_old = y
    for i in range(0, -99999, -10):
      if y >= chary // 2:
        dc.SetPen(self.pen_tick)
        dc.DrawLine(x1, y, x2, y)	# y tick
        self.y_ticks.append(y)
        t = repr(i)
        w, h = dc.GetTextExtent(t)
        # draw text on Y axis
        if y - y_old > h:
          if y + h // 2 <= self.originY:	
            dc.DrawText(repr(i), x1 - w, y - h // 2)
          elif h < self.scale:
            dc.DrawText(repr(i), x1 - w, self.originY - h)
          y_old = y
      y = y + self.scale
      if y >= self.originY - 3:
        break
  def MakeXTicks(self, dc):
    
    sample_rate = int(self.sample_rate * self.zoom)
    VFO = self.VFO + self.zoom_deltaf
    originY = self.originY
    x3 = self.originX + self.graph_width	# end of fft data
    charx , z = dc.GetTextExtent('-30000XX')
    tick0 = self.tick
    tick1 = tick0 * 2
    tick2 = tick0 * 3
    # Draw the X axis
    dc.SetPen(self.pen_tick)
    x = self.originX
    f = float(x - self.x0) * sample_rate / self.data_width
    c = None
    y = originY + 1
    for freq, color in conf.BandPlan:
      freq -= VFO
      if f < freq:
        xend = int(self.x0 + float(freq) * self.data_width / sample_rate + 0.5)
        if c is not None:
          dc.SetPen(wx.TRANSPARENT_PEN)
          dc.SetBrush(wx.Brush(c))
          dc.DrawRectangle(x, y, min(x3, xend) - x, tick0)  # x axis
        if xend >= x3:
          break
        x = xend
        f = freq
      c = color
    # check the width of the frequency label versus frequency span
    df = charx * sample_rate // self.data_width
    if VFO >= 10E9:     # Leave room for big labels
      df *= 1.33
    elif VFO >= 1E9:
      df *= 1.17
    # tfreq: tick frequency for labels in Hertz
    # stick: small tick in Hertz
    # mtick: medium tick
    # ltick: large tick
    s2 = 1000
    tfreq = None
    while tfreq is None:
      if df < s2:
        tfreq = s2
        stick = s2 // 10
        mtick = s2 // 2
        ltick = tfreq
      elif df < s2 * 2:
        tfreq = s2 * 2
        stick = s2 // 10
        mtick = s2 // 2
        ltick = s2
      elif df < s2 * 5:
        tfreq = s2 * 5
        stick = s2 // 2
        mtick = s2
        ltick = tfreq
      s2 *= 10
    # Draw the X axis ticks and frequency in kHz
    dc.SetPen(self.pen_tick)
    freq1 = VFO - sample_rate // 2
    freq1 = (freq1 // stick) * stick
    freq2 = freq1 + sample_rate + stick + 1
    y_end = 0
    #print(self.tick, stick, VFO, sample_rate , self.data_width, self.VFO, self.zoom_deltaf )
    for f in range (freq1, freq2, stick):
      x = self.x0 + int(float(f - VFO) / sample_rate * self.data_width)
      #print(x, originY, x, originY + tick0 )
      if self.originX <= x <= x3:
        if f % ltick == 0:		# large tick
          dc.DrawLine(x, originY, x, originY + tick2)
        elif f % mtick == 0:	# medium tick
          dc.DrawLine(x, originY, x, originY + tick1)
        else:					# small tick
          dc.DrawLine(x, originY, x, originY + tick0)
        if f % tfreq == 0:		# place frequency label
          t = str(f//1000)
          w, h = dc.GetTextExtent(t)
          dc.DrawText(t, x - w // 2, originY + tick2)
          y_end = originY + tick2 + h
    if y_end:		# mark the center of the display
      dc.DrawLine(self.x0, y_end, self.x0, application.screen_height)
     
  def OnGraphData(self, data):
    i1 = (self.data_width - self.graph_width) // 2
    i2 = i1 + self.graph_width
    self.display.OnGraphData(data[i1:i2])
  def SetVFO(self, vfo):
    self.VFO = vfo
    self.doResize = True
  def SetTxFreq(self, tx_freq, rx_freq):
    sample_rate = int(self.sample_rate * self.zoom)
    self.txFreq = tx_freq
    tx_x = self.x0 + int(float(tx_freq - self.zoom_deltaf) / sample_rate * self.data_width)
    self.tuningX = tx_x
    rx_x = self.x0 + int(float(rx_freq - self.zoom_deltaf) / sample_rate * self.data_width)
    if abs(tx_x - rx_x) < 2:		# Do not display Rx line for small frequency offset
      self.display.SetTuningLine(tx_x - self.originX, 0)
    else:
      self.display.SetTuningLine(tx_x - self.originX, rx_x - self.originX)
  def GetFilterDisplayXWR(self, rx_filters):
    mode = self.filter_mode
    rit = self.ritFreq
    if rx_filters:	# return Rx filter
      bandwidth = self.filter_bandwidth
      center = self.filter_center
      #print(mode, rit, bandwidth, center, "RX" ) # JMH 20190810 for this application, this is the side that is used
    else:	# return Tx filter
      bandwidth, center = get_filter_tx(mode)
      #print(mode, rit, bandwidth, center, "TX" )
    x = center - bandwidth // 2
    scale = 1.0 / self.zoom / self.sample_rate * self.data_width
    x = int(x * scale + 0.5)
    bandwidth = int(bandwidth * scale + 0.5)
    if bandwidth < 2:
      bandwidth = 1
    rit = int(rit * scale + 0.5)
    #print(mode, x, bandwidth, rit, center )
    return x, bandwidth, rit		# Starting x, bandwidth and RIT frequency
  def GetFilterDisplayRit(self):
    rit = self.ritFreq
    scale = 1.0 / self.zoom / self.sample_rate * self.data_width
    rit = int(rit * scale + 0.5)
    return rit
  def GetMousePosition(self, event):
    """For mouse clicks in our display, translate to our screen coordinates."""
    mouse_x, mouse_y = event.GetPosition()
    win = event.GetEventObject()
    if win is not self:
      x, y = win.GetPosition().Get()
      mouse_x += x
      mouse_y += y
    return mouse_x, mouse_y
  def FreqRound(self, tune, vfo):
    if conf.freq_spacing and not conf.freq_round_ssb:
      freq = tune + vfo
      n = int(freq) - conf.freq_base
      if n >= 0:
        n = (n + conf.freq_spacing // 2) // conf.freq_spacing
      else:
        n = - ( - n + conf.freq_spacing // 2) // conf.freq_spacing
      freq = conf.freq_base + n * conf.freq_spacing
      return freq - vfo
    else:
      return tune
  def OnRightDown(self, event):
    sample_rate = int(self.sample_rate * self.zoom)
    VFO = self.VFO + self.zoom_deltaf
    mouse_x, mouse_y = self.GetMousePosition(event)
    freq = float(mouse_x - self.x0) * sample_rate / self.data_width
    freq = int(freq)
    if VFO > 0:
      vfo = VFO + freq - self.zoom_deltaf
      if sample_rate > 40000:
        vfo = (vfo + 5000) // 10000 * 10000	# round to even number
      elif sample_rate > 5000:
        vfo = (vfo + 500) // 1000 * 1000
      else:
        vfo = (vfo + 50) // 100 * 100
      tune = freq + VFO - vfo
      tune = self.FreqRound(tune, vfo)
      self.ChangeHwFrequency(tune, vfo, 'MouseBtn3', event=event)
  def OnLeftDown(self, event):
    self.VFO = application.VFO  
    sample_rate = int(self.sample_rate * self.zoom)
    mouse_x, mouse_y = self.GetMousePosition(event)
    if mouse_x <= self.originX:		# click left of Y axis
      print("Bad Mouse Click LEFT")
      return
    if mouse_x >= self.originX + self.graph_width:	# click past FFT data
      print("Bad Mouse Click RIGHT")
      return
    shift = wx.GetKeyState(wx.WXK_SHIFT)
    if shift:
      mouse_x -= self.filter_center * self.data_width / sample_rate
    self.mouse_x = mouse_x
    x = mouse_x - self.originX
    if self.split_unavailable:
      self.mouse_is_rx = False

    if mouse_y < self.originY:		# click above X axis
      freq = float(mouse_x - self.x0) * sample_rate / self.data_width + self.zoom_deltaf
      freq = int(freq)
      #print("X: %d; Mouse_x: %d; origin_x: %d; freq: %d;  mouse_is_rx %d" %(x, mouse_x, self.originX, freq, self.mouse_is_rx))
      if self.mouse_is_rx:
        application.rxFreq = freq
        application.screen.SetTxFreq(self.txFreq, freq)
        QS.set_tune(freq + application.ritFreq, self.txFreq)
      else:
        rnd = conf.freq_round_ssb
        if rnd and not shift:
          if application.mode in ('LSB', 'USB', 'AM', 'FM', 'FDV-U', 'FDV-L'):
            freq = (freq + rnd//2) // rnd * rnd
        else:
          #print("^^^^^^^^^^^^^^^^^^^^^^^^^")  #JMH 20190810 this is the path that the program takes
          freq = self.FreqRound(freq, self.VFO)#JMH 20190810 I added the "application.ritFreq" term
        self.ChangeHwFrequency(freq, self.VFO, 'MouseBtn1', event=event)
    else:
        return
    self.CaptureMouse()
    #Start Auto Zero-beat  JMH ADDED 20190813
    ##################################################################
    time.sleep(2.2)
    ZeroFreq =int(round(QS.measure_frequency(-1)))
    count = 0 
    loop = 1
    while loop:
        ZFold = ZeroFreq
        count += 1
        time.sleep(0.2)
        ZeroFreq = int(round(QS.measure_frequency(-1)))
        if (count ==150) or (ZeroFreq== ZFold): loop = 0
        print("ZeroFreq: %d; ZFold: %d"%(ZeroFreq+self.VFO, ZFold+self.VFO))
        
    
    self.ChangeHwFrequency(ZeroFreq, self.VFO, 'AutoZero', event) #'MouseBtn1' +application.ritFreq
    return        
    #End Auto Zero-beat  JMH ADDED 20181226
    #################################################################
    self.CaptureMouse()
  def OnLeftUp(self, event):
    if self.stopRndfeq == 1: #JMH 20181226 added to support "auto 0 beat" feature
##      print("OnLeftUP C")
      self.stopRndfeq =0
      return
    if self.HasCapture():
      self.ReleaseMouse()
      freq = self.FreqRound(self.txFreq, self.VFO)
      if freq != self.txFreq:
        self.ChangeHwFrequency(freq, self.VFO, 'MouseMotion', event=event)
  def OnMotion(self, event):
    self.VFO = application.VFO  
    sample_rate = int(self.sample_rate * self.zoom)
    if event.Dragging() and event.LeftIsDown():
      mouse_x, mouse_y = self.GetMousePosition(event)
      if wx.GetKeyState(wx.WXK_SHIFT):
        mouse_x -= self.filter_center * self.data_width / sample_rate
      if conf.mouse_tune_method:		# Mouse motion changes the VFO frequency
        x = (mouse_x - self.mouse_x)	# Thanks to VK6JBL
        self.mouse_x = mouse_x
        freq = float(x) * sample_rate / self.data_width
        freq = int(freq)
        self.ChangeHwFrequency(self.txFreq, self.VFO - freq, 'MouseMotion', event=event)
      else:		# Mouse motion changes the tuning frequency
        # Frequency changes more rapidly for higher mouse Y position
        speed = max(10, self.originY - mouse_y) / float(self.originY + 1)
        x = (mouse_x - self.mouse_x)
        self.mouse_x = mouse_x
        freq = speed * x * sample_rate / self.data_width
        freq = int(freq)
        if self.mouse_is_rx:	# Mouse motion changes the receive frequency
          application.rxFreq += freq
          application.screen.SetTxFreq(self.txFreq, application.rxFreq)
          QS.set_tune(application.rxFreq + application.ritFreq, self.txFreq)
        else:					# Mouse motion changes the transmit frequency
          self.ChangeHwFrequency(self.txFreq + freq, self.VFO, 'MouseMotion', event=event)
  def OnWheel(self, event):
    self.VFO = application.VFO  
    if conf.freq_spacing:
      wm = conf.freq_spacing
    else:
      wm = self.WheelMod		# Round frequency when using mouse wheel
    mouse_x, mouse_y = self.GetMousePosition(event)
    x = mouse_x - self.originX
    if self.split_unavailable:
      self.mouse_is_rx = False
    else:
      self.mouse_is_rx = False
    if self.mouse_is_rx:
      #print("mouse_is_rx") #JMH 20190809 this path is NOT taken on mouse wheel event
      freq = application.rxFreq + self.VFO + wm * event.GetWheelRotation() // event.GetWheelDelta()
      if conf.freq_spacing:
        freq = self.FreqRound(freq, 0)
      elif freq >= 0:
        freq = freq // wm * wm
      else:		# freq can be negative when the VFO is zero
        freq = - (- freq // wm * wm)
      tune = freq - self.VFO
      application.rxFreq = tune
      application.screen.SetTxFreq(self.txFreq, tune)
      QS.set_tune(tune + application.ritFreq, self.txFreq)
    else:
      #print("!mouse_is_rx")  #JMH 20190809 this path IS TAKEN on mouse wheel event
      whlrot = event.GetWheelRotation()
      wdelta = event.GetWheelDelta()
      frqchng = (wm * whlrot // wdelta)
      freqi = application.txFreq + application.VFO
      freq = frqchng + freqi
      if conf.freq_spacing:
        #print('path 1') #route taken 
        freq = freq #self.FreqRound(freq, 0) #JMH 20190809 this function would not allow positive mouse changes to pass through
      elif freq >= 0:
        #print('path 2') #route NOT taken  
        freq = freq // wm * wm
      else:		# freq can be negative when the VFO is zero
        #print('path 3') #route NOT taken 
        freq = - (- freq // wm * wm)
      tune = freq - application.VFO
      #print("New Mouse Wheel Tune: %d; Freqi: %d; wm: %d; whlrot: %d; wdelta: %d; frqchng: %d" %(tune, freqi, wm, whlrot, wdelta, frqchng)) 
      self.ChangeHwFrequency(tune, self.VFO, 'MouseWheel', event=event)
  def ChangeHwFrequency(self, tune, vfo, source='', band='', event=None):
    application.ChangeHwFrequency(tune, vfo, source, band, event)
  def PeakHold(self, name):
    if name == 'GraphP1':
      self.display.peak_hold = int(self.display.scale * conf.graph_peak_hold_1)
    elif name == 'GraphP2':
      self.display.peak_hold = int(self.display.scale * conf.graph_peak_hold_2)
    else:
      self.display.peak_hold = 9999
    if self.display.peak_hold < 1:
      self.display.peak_hold = 1


class QMainFrame(wx.Frame):
  """Create the main top-level window."""
  def __init__(self, width, height):
    fp = open('__init__.py')		# Read in the title
    self.title = fp.readline().strip()
    fp.close()
    self.title = ' Quisk Diagnostic Debug Tool '
    wx.Frame.__init__(self, None, -1, self.title, wx.DefaultPosition,
        (width, height), wx.DEFAULT_FRAME_STYLE, 'MainFrame')
    self.SetBackgroundColour(conf.color_bg)
    self.Bind(wx.EVT_CLOSE, self.OnBtnClose)
  def OnBtnClose(self, event):
    application.OnBtnClose(event)
    self.Destroy()
  def SetConfigText(self, text):
    if len(text) > 100:
      text = text[0:80] + '|||' + text[-17:]
    self.SetTitle("Radio %s   %s   %s" % ("KW4KD", self.title, text))  

class Spacer(wx.Window):
  """Create a bar between the graph screen and the controls"""
  def __init__(self, parent):
    wx.Window.__init__(self, parent, pos = (0, 0),
       size=(-1, 6), style = wx.NO_BORDER)
    self.Bind(wx.EVT_PAINT, self.OnPaint)
    r, g, b = parent.GetBackgroundColour().Get(False)
    dark = (r * 7 // 10, g * 7 // 10, b * 7 // 10)
    light = (r + (255 - r) * 5 // 10, g + (255 - g) * 5 // 10, b + (255 - b) * 5 // 10)
    self.dark_pen = wx.Pen(dark, 1, wx.SOLID)
    self.light_pen = wx.Pen(light, 1, wx.SOLID)
    self.width = application.screen_width
  def OnPaint(self, event):
    dc = wx.PaintDC(self)
    w = self.width
    dc.SetPen(self.dark_pen)
    dc.DrawLine(0, 0, w, 0)
    dc.DrawLine(0, 1, w, 1)
    dc.DrawLine(0, 2, w, 2)
    dc.SetPen(self.light_pen)
    dc.DrawLine(0, 3, w, 3)
    dc.DrawLine(0, 4, w, 4)
    dc.DrawLine(0, 5, w, 5)
    

class App(wx.App):
  """Class representing the application."""
  StateNames = ['transmission_open', 'transmission_short', 'reflection_open', 'reflection_short', 'reflection_load', 'calibrate_time',
    'calibrate_version']
  def __init__(self):
    global application
    application = self
    self.bottom_widgets = None
    self.is_vna_program = None
    if sys.stdout.isatty():
      wx.App.__init__(self, redirect=False)
    else:
      wx.App.__init__(self, redirect=True)
  def OnInit(self):
    """Perform most initialization of the app here (called by wxPython on startup)."""
    wx.lib.colourdb.updateColourDB()	# Add additional color names
    import quisk_widgets		# quisk_widgets needs the application object
    quisk_widgets.application = self
    del quisk_widgets
    global conf		# conf is the module for all configuration data
    import quisk_conf_defaults as conf
    setattr(conf, 'config_file_path', ConfigPath)
    setattr(conf, 'DefaultConfigDir', DefaultConfigDir)
    if os.path.isfile(ConfigPath):	# See if the user has a config file
      setattr(conf, 'config_file_exists', True)
      d = {}
      d.update(conf.__dict__)		# make items from conf available
      exec(compile(open(ConfigPath).read(), ConfigPath, 'exec'), d)		# execute the user's config file
      for k, v in d.items():          # add user's config items to conf
          if k[0] != '_':				# omit items starting with '_'
              setattr(conf, k, v)
          print("%s: %s" %(k, v))
      print("__________________________________________________________________________________")  
    else:
      setattr(conf, 'config_file_exists', False)
    for k in ('sym_stat_mem', 'sym_stat_fav', 'sym_stat_dx',
        'btn_text_range_dn', 'btn_text_range_up', 'btn_text_play', 'btn_text_rec', 'btn_text_file_rec', 
		'btn_text_file_play', 'btn_text_fav_add',
        'btn_text_fav_recall', 'btn_text_mem_add', 'btn_text_mem_next', 'btn_text_mem_del'):
      if conf.use_unicode_symbols:
        setattr(conf, 'X' + k, getattr(conf, 'U' + k))
      else:
        setattr(conf, 'X' + k, getattr(conf, 'T' + k))
    QS.set_params(quisk_is_vna=0)	# We are not the VNA program          JMH 20190813 taken from QUISK4.1.41
    self.local_conf = configure.Configuration(self, argv_options.AskMe)
    self.local_conf.UpdateConf()
    if conf.invertSpectrum:
      QS.invert_spectrum(1)
    # Check for PulseAudio names and substitute the actual device name for abbreviations
    self.pulse_in_use = False
    if sys.platform != 'win32' and conf.show_pulse_audio_devices:
      self.pa_dev_capt, self.pa_dev_play = QS.pa_sound_devices()
      for key in ("name_of_sound_play", "name_of_mic_play", "digital_output_name", "digital_rx1_name", "sample_playback_name"):
        value = getattr(conf, key)		# playback devices
        if value[0:6] == "pulse:":
          self.pulse_in_use = True
          for n0, n1, n2 in self.pa_dev_play:
            for n in (n0, n1, n2):
              if value[6:] in n:
                setattr(conf, key, "pulse:" + n0)
      for key in ("name_of_sound_capt", "microphone_name", "digital_input_name"):
        value = getattr(conf, key)		# capture devices
        if value[0:6] == "pulse:":
          self.pulse_in_use = True
          for n0, n1, n2 in self.pa_dev_capt:
            for n in (n0, n1, n2):
              if value[6:] in n:
                setattr(conf, key, "pulse:" + n0)

    # Open hardware file
    print("########################### Open hardware file ##################################")
    self.bandAmplPhase = conf.bandAmplPhase
    self.modeFilter = {			# the filter button index in use for each mode
      'CW'  : 3,
      'SSB' : 3,
      'AM'  : 3,
      'FM'  : 3,
      'DGT' : 1,
      'FDV' : 2,
      'IMD' : 3,                        # JMH ADDED 20180430
      '0BtSig' : 1,
      conf.add_extern_demod : 3,
      }
    global Hardware
    if self.local_conf.GetHardware():
      pass
    else:
      if hasattr(conf, "Hardware"):	# Hardware defined in config file
        self.Hardware = conf.Hardware(self, conf)
        hname =  ConfigPath
      else:
        self.Hardware = conf.quisk_hardware.Hardware(self, conf)
        hname =  conf.quisk_hardware.__file__
      if hname[-3:] == 'pyc':
        hname = hname[0:-1]
      setattr(conf, 'hardware_file_name',  hname)
      if conf.quisk_widgets:
        hname =  conf.quisk_widgets.__file__
        if hname[-3:] == 'pyc':
          hname = hname[0:-1]
        setattr(conf, 'widgets_file_name',  hname)
      else:
        setattr(conf, 'widgets_file_name',  '')
    Hardware = self.Hardware
    for attr, value in Hardware.__dict__.iteritems():
        print("%s: %s" %(attr, value))     
    print("########################### hardware file Opened ##################################") 
    self.makeButtons = 1 #0= nobuttons; 1= make buttons JMH 20190812
    ######################################################################
    if(self.makeButtons): self.WidgetGlobals = MakeWidgetGlobals()
    ###################################################################### 

    self.a = A()
    self.ritFreq = -750 #Hz
    self.txFreq = 0
    self.VFO = 7060000
    self.lastBand = 'Audio'
    self.mode ="CWU"
    self.w_phase = None 
    self.zoom = 1.0
    self.ZeroFreq = 0
    self.filter_bandwidth = 1000
    self.dataFailCnt =0
    self.baddata = 0
    self.Mflpcnt = 0
    self.zoom_deltaf = 0
    self.multirx_index = 0
    self.BtnRfGain = None
    # Open hardware file
    self.firmware_version = None
    # Initialization
    x, y, self.screen_width, self.screen_height = wx.Display().GetGeometry()
    self.Bind(wx.EVT_QUERY_END_SESSION, self.OnEndSession)
    self.sample_rate = conf.sample_rate #96000 #48000
    self.timer = time.time()		# A seconds clock
    self.time0 = 0			# timer to display fields
    self.clip_time0 = 0			# timer to display a CLIP message on ADC overflow
    self.heart_time0 = self.timer	# timer to call HeartBeat at intervals
    self.running = False
    self.startup = True
    self.save_data = []
    self.frequency = 0
    self.main_frame = frame = QMainFrame(x, y)
    self.SetTopWindow(frame)
    # Find the data width, the width of returned graph data.
    width = self.screen_width * conf.graph_width
    width = int(width)
    self.data_width = width
    if hasattr(Hardware, 'pre_open'):       # pre_open() is called before open()
      Hardware.pre_open()
    # correct_delta is the spacing of correction points in Hertz
    self.correct_width = self.data_width	# number of data points in the correct arrays
    self.correct_delta = 1
    h = 0 #handle for QS.record_app
    fft_mult = 3
    rx_data_width = 1008
    self.fft_size = self.data_width * fft_mult
    QS.set_enable_bandscope(0)
    self.graph_width = 1120
    self.timeVOX = 500
    average_count = 4

    # Make all the screens and hide all but one
    self.graph = GraphScreen(frame, self.data_width, self.data_width, self.correct_width, self.correct_delta)
    self.screen = self.graph
    width = self.graph.width
    # Make a vertical box to hold all the screens and the bottom rows
    vertBox = self.vertBox = wx.BoxSizer(wx.VERTICAL)
    frame.SetSizer(vertBox)
    # Add the screens
    vertBox.Add(self.graph, 1, wx.EXPAND) 
    vertBox.Add(Spacer(frame), 0, wx.EXPAND)
    # Add the sizer for the buttons
    szr1 = wx.BoxSizer(wx.HORIZONTAL)
    vertBox.Add(szr1, 0, wx.EXPAND, 0)
    ######################################################################
    # Make the buttons in row 1
    if(self.makeButtons):
        self.buttons1 = buttons1 = []
        self.screen_name = "Test Tool"
        b = RadioButtonGroup(frame, self.OnBtnScreen, ('  Button 1  ', '  Button 2  ', '  Button 3  '), self.screen_name)
        buttons1 += b.buttons
        self.btn_run = b = QuiskCheckbutton(frame, self.OnBtnRun, 'ZeroBt')
        buttons1.append(b)
        self.btn_calibrate = b = QuiskPushbutton(frame, self.OnBtnCal, '  Button 4 ')
        buttons1.append(b)
        width = 0
        for b in buttons1:
          w, height = b.GetMinSize()
          if width < w:
            width = w
    ######################################################################

    w, height = (10,24) 
    for i in range(24, 8, -2):
        font = wx.Font(i, wx.FONTFAMILY_SWISS, wx.NORMAL, wx.FONTWEIGHT_NORMAL, False, conf.quisk_typeface)
        frame.SetFont(font)
        w, h = frame.GetTextExtent('Start   ')
        if h < height * 9 // 10:
            break
    e = wx.TextCtrl(frame, -1, '1', style=wx.TE_PROCESS_ENTER)
    e.SetFont(font)
    tw, z = e.GetTextExtent("xx30.333xxxXXXx")
    e.SetMinSize((tw, height))
    e.SetBackgroundColour(conf.color_entry)
    self.freq_start_ctrl = e
    frame.Bind(wx.EVT_TEXT_ENTER, self.OnNewFreq, source=e)
    frame.Bind(wx.EVT_TEXT, self.OnNewFreq, source=e)
    e = wx.TextCtrl(frame, -1, '--------', style=wx.TE_PROCESS_ENTER)
    e.SetFont(font)
    e.SetMinSize((tw, height))
    e.SetBackgroundColour(conf.color_entry)
    self.freq_stop_ctrl = e
    frame.Bind(wx.EVT_TEXT_ENTER, self.OnNewFreq, source=e)
    frame.Bind(wx.EVT_TEXT, self.OnNewFreq, source=e)
    gap = max(2, height // 16)
    
    ######################################################################
    if(self.makeButtons):
        szr1.Add(buttons1[0], 0, wx.RIGHT|wx.LEFT, gap) #Transmission Button
        szr1.Add(buttons1[1], 0, wx.RIGHT, gap) #Reflection Button
        szr1.Add(buttons1[2], 0, wx.RIGHT, gap) #Help Button
        szr1.Add(buttons1[3], 0, wx.RIGHT|wx.LEFT, gap) #Run Button
        szr1.Add(buttons1[4], 0, wx.RIGHT|wx.LEFT, gap) #Calibrate Button
    ######################################################################

    szr1.Add(self.freq_start_ctrl, 0, wx.RIGHT, gap)
    szr1.Add(self.freq_stop_ctrl, 0, wx.RIGHT, gap)
    self.statusbar = self.main_frame.CreateStatusBar()
    # Set top window size
    self.main_frame.SetClientSize(wx.Size(self.graph.width, (self.screen_height * 5 // 10)))
    w, h = self.main_frame.GetSize().Get()
    self.main_frame.SetSizeHints(w, 1, w)
    self.add_version = False
    # Open the hardware.  This must be called before open_sound().
    self.config_text = "NO hardware response"# Hardware.open()
    self.status_error = "possible error messages"	# possible error messages
    self.main_frame.SetConfigText(self.config_text)
#************************** JMH 20190809 the following taken from quisk *****************************************
    if conf.use_rx_udp and conf.use_rx_udp != 10:
      self.add_version = True		# Add firmware version to config text
    else:
      self.add_version = False
    if conf.use_rx_udp == 10:		# Hermes UDP protocol
      if conf.tx_ip == '':
        conf.tx_ip = Hardware.hermes_ip
      elif conf.tx_ip == 'disable':
        conf.tx_ip = ''
      if conf.tx_audio_port == 0:
        conf.tx_audio_port = conf.rx_udp_port
    elif conf.use_rx_udp:
      conf.rx_udp_decimation = 8 * 8 * 8
      if conf.tx_ip == '':
        conf.tx_ip = conf.rx_udp_ip
      elif conf.tx_ip == 'disable':
        conf.tx_ip = ''
      if conf.tx_audio_port == 0:
        conf.tx_audio_port = conf.rx_udp_port + 2
    # Open the hardware.  This must be called before open_sound().
    print("++++++++++++++++++++ Hardware.open()++++++++++++++++++++++")
    self.config_text = Hardware.open()
    print(" config_text: %s" % self.config_text)
    
    self.main_frame.SetConfigText(self.config_text)  
    print("conf.key_method: %s"% conf.key_method)  
    ##### JMH 20190810 setup mode & filter ######
        #Configure & Install Filter
    self.OnChangeMode() # automatically calls self.OnChangeFilter()
    # FFT size must equal the data_width so that all data points are returned!
    #(args, "OOiiiiik", &pyApp, &quisk_pyConfig, &data_width, &graph_width, &fft_size, &multirx_data_width, &rate, &handle)
    QS.record_app(self, conf, self.data_width, self.graph_width, self.fft_size, rx_data_width, self.sample_rate, h)
    print ('QS.record_app() Settings:')
    print ('data_width: %d, FFT size: %d, FFT mult: %d, average_count: %d, rate: %d, Refresh: %.2f Hz' % (
        self.data_width, self.fft_size, self.fft_size / self.data_width, average_count, self.sample_rate,
        float(self.sample_rate) / self.fft_size / average_count))
    QS.record_graph(0, 0, 1.0)
    QS.set_tx_audio(vox_level=20, vox_time=self.timeVOX)

    if QS.open_key(conf.key_method):
      print('open_key failed for name "%s"' % conf.key_method)
    if hasattr(conf, 'mixer_settings'):
      for dev, numid, value in conf.mixer_settings:
        print(dev, numid, value)
        err_msg = QS.mixer_set(dev, numid, value)
        if err_msg:
          print("Mixer", err_msg)
    QS.capt_channels (conf.channel_i, conf.channel_q)
    print( "conf.channel_i: %s"% conf.channel_i)
    print( "conf.channel_q: %s"% conf.channel_q)
    QS.play_channels (conf.channel_i, conf.channel_q)
    QS.micplay_channels (conf.mic_play_chan_I, conf.mic_play_chan_Q)
    print( "conf.mic_play_chan_I: %s"% conf.mic_play_chan_I)
    print( "conf.mic_play_chan_Q: %s"% conf.mic_play_chan_Q)
    # Note: Subsequent calls to set channels must not name a higher channel number.
    #       Normally, these calls are only used to reverse the channels.
    print("++++++++++++++++++++ QS.open_sound()++++++++++++++++++++++")
    QS.open_sound(conf.name_of_sound_capt, conf.name_of_sound_play, 0,
                conf.data_poll_usec, conf.latency_millisecs,
                conf.microphone_name, conf.tx_ip, conf.tx_audio_port,
                conf.sample_rate, conf.mic_channel_I, conf.mic_channel_Q,
				conf.mic_out_volume, conf.name_of_mic_play, conf.mic_playback_rate)
    print( "sound_capt: %s" % conf.name_of_sound_capt)
    print( "sound_play: %s"% conf.name_of_sound_play)
    print( "data_poll_usec: %d"% conf.data_poll_usec)
    print( "latency_millisecs: %d"% conf.latency_millisecs)
    print( "microphone_name: %s"% conf.microphone_name)
    print( "tx_ip: %s"% conf.tx_ip)
    print( "tx_audio_port: %s"% conf.tx_audio_port)
    print( "mic_sample_rate: %d"% conf.sample_rate)
    print( "mic_channel_I: %s"% conf.mic_channel_I)
    print( "mic_channel_Q: %s"% conf.mic_channel_Q)
    print( "mic_out_volume: %s"% conf.mic_out_volume)
    print( "name_of_mic_play: %s"% conf.name_of_mic_play)
    print( "mic_playback_rate: %d"% conf.mic_playback_rate)
    print( "$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$")
    for use, name, rate, latency, errors in QS.sound_errors():
      print("use: %s; name: %s; rate: %d; latncy: %d; err: %d" %(use, name, rate, latency, errors))
      # use: I/Q Rx Sample Input; name: portaudio:(hw:1,0); rate: 96000; latncy: 0; err: 0
      # use: Radio Sound Output; name: pulse; rate: 96000; latncy: 0; err: 0
    print( "$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$")
    (rate_min, rate_max, sample_rate, chan_min, chan_max,
         msg1, unused, err_msg,
          read_error,  write_error, underrun_error,
          latencyCapt, latencyPlay, interupts, fft_error, mic_max_display,
          data_poll_usec
     ) = QS.get_state()
    print( "err_msg : %s" %  err_msg)
    tune, vfo = Hardware.ReturnFrequency()	# Request initial frequency
    if tune is None or vfo is None:		# Set last-used frequency
      tune = -12500
      #self.vfo = 7060000
      source = 'FreqEntry'
      band = '40'
      event=None
      #tune, vfo = Hardware.ChangeFrequency(vfo + tune, vfo, source, band, event) #this function is found in "hardware_usb.py"
      self.ChangeHwFrequency(tune, self.VFO, source, band, event) 
    else:			# Set requested frequency
      self.BandFromFreq(tune)
      self.ChangeDisplayFrequency(tune - vfo, vfo)
    # Record filter rate for the filter screen
    fltrSmplRate = QS.get_filter_rate(-1, -1)
    print("QS Filter Sample Rate: %d" %fltrSmplRate)
    #if info[8]:		# error message
    #  self.sound_error = 1
    #  self.config_screen.err_msg = info[8]
    #  print info[8]

#************************** JMH 20190809 End of code taken from quisk *****************************************

      
    # Note: Subsequent calls to set channels must not name a higher channel number.
    #       Normally, these calls are only used to reverse the channels.
##    print("QS.open_sound sample_rate: %d" %sample_rate)

    self.audio_volume = .50 	# audio_volume is 0 to 1.000
    QS.set_volume(self.audio_volume)
    self.OnChangeMode(None) #Set radio to operate in CW/Upper-SideBand Mode
    self.Bind(wx.EVT_IDLE, self.graph.OnIdle)
    frame.Show()
    self.EnableButtons()
    QS.set_fdx(1)
    self.sound_thread = SoundThread()
    self.sound_thread.start()
    return True
# JMH 20200403 taken from QUISKKW4KD
  def BandFromFreq(self, frequency):	# Change to a new band based on the frequency
    try:
      f1, f2 = conf.BandEdge[self.lastBand]
      if f1 <= frequency <= f2:
        return						# We are within the current band
    except KeyError:
      f1 = f2 = -1
    # Frequency is not within the current band.  Save the current band data.
    if f1 <= self.VFO + self.txFreq <= f2:
      self.bandState[self.lastBand] = (self.VFO, self.txFreq, self.mode)
    # Change to the correct band based on frequency.
##    for band, (f1, f2) in conf.BandEdge.items():
##      if f1 <= frequency <= f2:
##        self.lastBand = band
##        self.bandBtnGroup.SetLabel(band, do_cmd=False)
##        try:
##          vfo, tune, mode = self.bandState[band]
##        except KeyError:
##          vfo, tune, mode = (0, 0, 'LSB')
##        self.OnBtnMode(None, mode)
##        self.ChangeBand(band)
##        break


# JMH 20190809 taken from QUISK
  def ChangeDisplayFrequency(self, tune, vfo):
      'Change the frequency displayed by Quisk'
      change = 0
      if tune != self.txFreq:
          change = 1
          self.txFreq = tune
          self.rxFreq = self.txFreq
          self.screen.SetTxFreq(self.txFreq, self.rxFreq) #map/draw the tx & rx lines to the graph
          self.freq_start_ctrl.SetValue(str(vfo+self.txFreq))
          try:
              Hardware.ChangeTXFreq(vfo+self.txFreq) # 20180226 JMH added to suppport TX Si5351 Tx freq clock
          except:
              pass
          print("QS.set_tune(rx: %d, tx: %d)" %(self.rxFreq + self.ritFreq, self.txFreq))
          QS.set_tune(self.rxFreq + self.ritFreq, self.txFreq) #JMH This sets the RX & TX frequencies that the SDR (fft) is working at relative to the radios mux frequency 
          #QS.set_tune(self.txFreq, self.txFreq)
      
      if vfo != self.VFO:
          change = 1
          self.VFO = vfo
      if self.w_phase:		# Phase adjustment screen can not change its VFO
          self.w_phase.Destroy()
          self.w_phase = None
          ampl, phase = (0.0, 0.0) #self.GetAmplPhase(0) #JMH 20190809 simplified for this application
          QS.set_ampl_phase(ampl, phase, 0)
          ampl, phase = (0.0, 0.0) #self.GetAmplPhase(1) #JMH 20190809 simplified for this application
          QS.set_ampl_phase(ampl, phase, 1)
      return change
  def ChangeHwFrequency(self, tune, vfo, source='', band='', event=None):
      """Change the VFO and tuning frequencies, and notify the hardware.
        tune:   the new tuning frequency in +- sample_rate/2;
        vfo:    the new vfo frequency in Hertz; this is the RF frequency at zero Hz audio
        source: a string indicating the source or widget requesting the change;
        band:   if source is "BtnBand", the band requested;
        event:  for a widget, the event (used to access control/shift key state).

        Try to update the hardware by calling Hardware.ChangeFrequency().
        The hardware will reply with the updated frequencies which may be different
        from those requested; use and display the returned tune and vfo.
      """
        
      #print("ChangeHwFrequency Tune:",tune, " VFO:",vfo, "Source: ", source) #JMH Test
      tune, vfo = Hardware.ChangeFrequency(vfo + tune, vfo, source, band, event) #this function is found in "hardware_usb.py"
      self.ChangeDisplayFrequency(tune - vfo, vfo)
      self.screen.VFO = vfo #JMH 20190813 added to sync all vfo references
  
  def MakeFilterCoef(self, rate, N, bw, center):
      """Make an I/Q filter with rectangular passband."""
      lowpass = bw * 24000 // rate // 2
      if lowpass in Filters:
          filtD = Filters[lowpass]
          #print ("Custom filter key %d rate %d bandwidth %d size %d" % (lowpass, rate, bw, len(filtD)))
      else:
          #print ("Window filter key %d rate %d bandwidth %d" % (lowpass, rate, bw))
          if N is None:
            shape = 1.5       # Shape factor at 88 dB
            trans = (bw / 2.0 / rate) * (shape - 1.0)     # 88 dB atten
            N = int(4.0 / trans)
            if N > 1000:
              N = 1000
            N = (N // 2) * 2 + 1
          K = bw * N / rate
          filtD = []
          pi = math.pi
          sin = math.sin
          cos = math.cos
          for k in range(-N//2, N//2 + 1):
            # Make a lowpass filter
            if k == 0:
              z = float(K) / N
            else:
              z = 1.0 / N * sin(pi * k * K / N) / sin(pi * k / N)
            # Apply a windowing function
            if 1:	# Blackman window
              w = 0.42 + 0.5 * cos(2. * pi * k / N) + 0.08 * cos(4. * pi * k / N)
            elif 0:	# Hamming
              w = 0.54 + 0.46 * cos(2. * pi * k / N)
            elif 0:	# Hanning
              w = 0.5 + 0.5 * cos(2. * pi * k / N)
            else:
              w = 1
            z *= w
            filtD.append(z)
      if center:
          # Make a bandpass filter by tuning the low pass filter to new center frequency.
          # Make two quadrature filters.
          filtI = []
          filtQ = []
          tune = -1j * 2.0 * math.pi * center / rate;
          NN = len(filtD)
          D = (NN - 1.0) / 2.0;
          for i in range(NN):
            z = 2.0 * cmath.exp(tune * (i - D)) * filtD[i]
            filtI.append(z.real)
            filtQ.append(z.imag)
          return filtI, filtQ
      return filtD, filtD
    
  def OnChangeMode(self, event=None):
    mode = self.mode
    if mode == 'CWL':
      bws =  conf.FilterBwCW
      print("QS.set_rx_mode(0)") 
      QS.set_rx_mode(0)
      #self.SetRit(conf.cwTone)
      index = 0
      style = 'AM'
      offset = 0
    elif mode == 'CWU':
      bws = conf.FilterBwCW
      print("QS.set_rx_mode(1)") 
      QS.set_rx_mode(1)
      #self.SetRit(-conf.cwTone)
      index = 1
      style = 'AM'
      offset = 0
    elif mode == 'LSB':
      QS.set_rx_mode(2)
      #self.SetRit(0)  
      bws = conf.FilterBwSSB
      index = 2
      style = 'LSB'
      offset = 300
    elif mode == 'USB':
      bws = conf.FilterBwSSB
      QS.set_rx_mode(3)
      #self.SetRit(0)
      index = 3
      style = 'USB'
      offset = 300
    elif mode == 'AM':
      bws = conf.FilterBwAM
      QS.set_rx_mode(4)
      #self.SetRit(0)
      index = 4
      style = 'AM'
      offset = 0
    elif mode == 'FM':
      bws = conf.FilterBwFM
      QS.set_rx_mode(5)
      #self.SetRit(0)
      index = 5
      style = 'AM'
      offset = 0
    elif mode == 'DGT-U':
      bws = conf.FilterBwDGT
      QS.set_rx_mode(7)
      index = 7
      style = 'USB'
      offset = 300
    elif mode == 'DGT-L':
      bws = conf.FilterBwDGT
      QS.set_rx_mode(8)
      index = 8
      style = 'LSB'
      offset = 300
    elif mode == 'DGT-IQ':
      bws = conf.FilterBwDGT
      index = 9
      style = 'AM'
      offset = 0
    elif mode == 'DGT-FM':
      bws = conf.FilterBwDGT
      QS.set_rx_mode(13)
      index = 13
      style = 'AM'
      offset = 0
    else:
      self.mode = 'USB'
      bws = conf.FilterBwSSB
      QS.set_rx_mode(3)
      #self.SetRit(0)
      index = 3
      style = 'USB'
      offset = 300
    self.mode_index = index
    #QS.set_multirx_mode(self.multirx_index, index)
    QS.set_sidetone(0, 0, self.ritFreq, conf.keyupDelay) #JMH 20190813 need this to get the qs.measure_freq to work correctly
    self.filter_bandwidth = bws[2]
    self.filter_style = style
    self.filter_offset = offset
    self.OnChangeFilter()

  def OnChangeFilter(self, event=None):
    mode = self.mode
    if mode in ("CWL", "CWU"):
      center = max(conf.cwTone, self.filter_bandwidth // 2)
      frate = 48000 / 8;
    elif mode in ('LSB', 'USB'):
      center = 300 + self.filter_bandwidth // 2
      frate = 48000 / 4;
    elif mode == 'AM':
      center = 0
      frate = 48000 / 2;
    elif mode in ('FM', 'DGT-FM'):
      center = 0
      frate = 48000 / 2;
    elif mode in ('DGT-U', 'DGT-L'):
      center = 300 + self.filter_bandwidth / 2
      frate = 48000;
    elif mode == 'DGT-IQ':
      center = 0
      frate = 48000;
    else:
      center = 0
      frate = 48000;

    #frate = QS.get_filter_rate(Mode2Index.get(mode, 3), self.filter_bandwidth ) #
    #frate = QS.get_filter_rate(1, self.filter_bandwidth )  #For CW Mode2Index.get(mode, 3) always = 1
    bw = min(self.filter_bandwidth, frate // 2)
    lower_edge = self.ritFreq  - bw // 2   #center - self.filter_bandwidth // 2  
    print("bw %d; filter_bandwith %d; frate %d; lower_edge: %d " %(bw, self.filter_bandwidth, frate, lower_edge))
    self.filter_bandwidth = bw 
    self.filter_I, self.filter_Q = application.MakeFilterCoef(frate, None, self.filter_bandwidth, center)
#    if self.is_playing:
    QS.set_filters(self.filter_I, self.filter_Q, self.filter_bandwidth, lower_edge, 0)	# filter for receiver that is playing sound
##    if self.multirx_index == 0:
##    QS.set_filters(self.filter_I, self.filter_Q, self.filter_bandwidth, lower_edge, 1)	# filter for digital mode output to sound device
    #center = self.GetFilterCenter(mode, bw)
    self.graph.filter_mode = mode
    self.graph.filter_bandwidth = bw
    self.graph.filter_center = center
    self.graph.ritFreq = self.ritFreq
    
  def OnExit(self):
    QS.close_rx_udp()
    return 0
  def SaveState(self):
    if self.init_path:		# save current program state
      d = {}
      for n in self.StateNames:
        d[n] = getattr(self, n)
      try:
        fp = open(self.init_path, "wb")
        pickle.dump(d, fp)
        fp.close()
      except:
        pass #traceback.print_exc()
  def OnEndSession(self, event):
    event.Skip()
    self.OnBtnClose(event)
  def OnBtnClose(self, event):
    time.sleep(0.5)
    if self.sound_thread:
      self.sound_thread.stop()
    for i in range(0, 20):
      if threading.activeCount() == 1:
        break
      time.sleep(0.1)
    Hardware.close()
  def OnBtnBand(self, event):
      pass

  def Calibrate(self):
      pass
##    self.graph.calibrate_tmp = [0] * self.correct_width
##    self.graph.calibrate_count = 0
##    self.graph.SetMode("Calibrate")
##    self.NewFreq(0, self.max_freq)
##    if self.has_SetVNA:
##      Hardware.SetVNA(key_down=1)
##    self.running = True
##    self.startup = True
  def OnBtnCal(self, event):
      pass
##    if self.has_SetVNA:
##      Hardware.SetVNA(key_down=0, vna_start=0, vna_stop=self.max_freq, vna_count=self.correct_width)
##    dlg = CalibrateDialog(self)
##    dlg.ShowModal()
##    dlg.Destroy()
##    if application.has_SetVNA:
##      Hardware.SetVNA(key_down=0, vna_count=self.data_width)
  def OnBtnScreen(self, event):
      pass
##    btn = event.GetEventObject()
##    self.screen_name = btn.GetLabel().strip()
##    if self.screen_name == 'Help':
##      self.help_screen.Show()
##      self.graph.Hide()
##    else:
##      self.help_screen.Hide()
##      self.graph.Show()
##      self.graph.SetMode(self.screen_name)
##    self.vertBox.Layout()
##    self.EnableButtons()
  def OnBtnRun(self, event):
      btn = event.GetEventObject()
##    run = btn.GetValue()
##    if run:
##      for b in self.buttons1:
##        if b != btn:
##          b.Enable(False)
##    else:
##      for b in self.buttons1:
##        b.Enable(True)
##    self.graph.SetMode(self.screen_name)
##    if not self.running and not self.OnNewFreq():
##      return
##    if self.has_SetVNA:
##      if run:
##        self.running = True
##        self.startup = True
##        Hardware.SetVNA(key_down=1)
##      else:
##        self.running = False
##        Hardware.SetVNA(key_down=0)
      vfo = Hardware.ReturnVfoFloat()
      if vfo is None:
        vfo = self.VFO
      vfo += Hardware.transverter_offset
##      ZeroOld = 0
##      ZeroFreq = int(round(QS.measure_frequency(-1)))
##      
##      while ZeroFreq==0 or ZeroFreq != ZeroOld :
##        ZeroOld = ZeroFreq  
##        QS.measure_frequency(2)
##        time.sleep(0.1)
##        ZeroFreq =int(round(QS.measure_frequency(-1)))
##        tune = ZeroFreq+ vfo
      #QS.measure_frequency(0)
      ZeroFreq =self.ZeroFreq
      tune = ZeroFreq+ self.VFO
      txfreq = self.VFO+self.txFreq
      delta = tune-txfreq
      print( '0Beat Freq: %d' %tune ) #JMH ADDED 20180430; Test
      self.ChangeDisplayFrequency((ZeroFreq), vfo) #this method factors in RIT; so should not need submit with RIT added
      mode = self.mode
      Hardware.ChangeMode(mode)
      return

      
  def EnableButtons(self):
      if(self.makeButtons):
          for b in self.buttons1: # start by disabling all buttons
              b.Enable(0)
          self.btn_run.Enable(1)
          #self.btn_calibrate.Enable(0)
          
      pass
  def ShowFreq(self, freq, index):
    self.frequency = freq
##    if hasattr(Hardware, 'ChangeFilterFrequency'):
##      Hardware.ChangeFilterFrequency(freq)
    self.graph_freq = freq
    self.graph_index = index
    self.WriteFields()
  def OnNewFreq(self, event=None):
      pass

  def NewFreq(self, start, stop):
      pass
##    self.transmission_cal = text
  def WriteFields(self):
    index = self.graph_index
    if index < 0:
      index = 0
    elif index >= self.data_width:
      index = self.data_width - 1
    freq = "Freq %.6f" % (self.frequency * 1E-6)
    #mode = self.graph.mode
    mode = 'Transmission'
    if self.status_error:
      text = self.status_error
    elif not self.graph.data_mag:
      if mode == 'Transmission':
        text = u"   %s    %s" % (self.transmission_cal, freq)
      elif mode == 'Reflection':
        text = u"   %s    %s" % (self.reflection_cal, freq)
      else:
        text = ''
    elif mode == 'Calibrate':
      db = self.graph.data_mag[index]
      phase = self.graph.data_phase[index]
      text = u"  %s     Calibrate   %.2f dB   %.1f\u00B0" % (freq, db, phase)
    elif mode == 'Transmission':
      db = self.graph.data_mag[index]
      phase = self.graph.data_phase[index]
      text = u"   %s    %s     Transmission   %.2f dB   %.1f\u00B0" % (self.transmission_cal, freq, db, phase)
    elif mode == 'Reflection':
      db = self.graph.data_mag[index]
      phase = self.graph.data_phase[index]
      aref = abs(self.graph.data_reflect[index])
      swr = (1.0 + aref) / (1.0 - aref)
      if not 0.999 <= swr <= 99:
        swr = 99.0
      text = u"   %s    %s     Reflect  ( %.2f dB   %.1f\u00B0 )  SWR %.1f" % (self.reflection_cal, freq, db, phase, swr)
      Z = self.graph.data_impedance[index]
      mag = abs(Z)
      phase = cmath.phase(Z) * 360. / (2.0 * math.pi)
      freq = self.graph.data_freq[index]
      z_real = Z.real
      z_imag = Z.imag
      if z_imag < 0:
        text += u"     Z \u03A9 ( %.1f - %.1fJ ) = ( %.1f  %.1f\u00B0 )" % (z_real, abs(z_imag), mag, phase)
      else:
        text += u"     Z \u03A9 ( %.1f + %.1fJ ) = ( %.1f  %.1f\u00B0 )" % (z_real, z_imag, mag, phase)
      if z_imag >= 0.5:
        L = z_imag / (2.0 * math.pi * freq) * 1e9
        Xp = (z_imag ** 2 + z_real ** 2) / z_imag
        Lp = Xp / (2.0 * math.pi * freq) * 1e9
        text += '     L %.0f nH' % L
        if z_real > 0.01:
          Rp = (z_imag ** 2 + z_real ** 2) / z_real
          text += "  ( %.1f || %.0f nH )" % (Rp, Lp)
      elif z_imag < -0.5:
        C = -1.0 / (2.0 * math.pi * freq * z_imag) * 1e9
        Xp = (z_imag ** 2 + z_real ** 2) / z_imag
        Cp = -1.0 / (2.0 * math.pi * freq * Xp) * 1e9
        text += '     C %.3f nF' % C
        if z_real > 0.01:
          Rp = (z_imag ** 2 + z_real ** 2) / z_real
          text += "  ( %.1f || %.3f nF )" % (Rp, Cp)
    self.statusbar.SetStatusText(text)
  def PostStartup(self):	# called once after sound attempts to start
    pass #VNA code
  def OnReadSound(self):	# called at frequent intervals
    self.timer = time.time()
    data = QS.get_graph(1, self.zoom, float(self.zoom_deltaf))	# get FFT data
    baddata = 0
    if data:
        self.dataFailCnt += 1
        self.baddata = 0
        if (self.Mflpcnt ==0):
            self.ZeroFreq =  int(round(QS.measure_frequency(-1)))#QS.measure_frequency(2)
            vfo = Hardware.ReturnVfoFloat()
            if vfo is None:
              vfo = self.VFO
            vfo += Hardware.transverter_offset
            t = '%10d' % (self.ZeroFreq + vfo)#t = '%13.2f' % (self.ZeroFreq + vfo)
            t = t[0:4] + ' ' + t[4:7] + ' ' + t[7:] + ' Hz'
            txfreq = self.VFO+self.txFreq
            #print("%s" %t)
            self.freq_stop_ctrl.SetValue(t)
            self.Mflpcnt =1
        self.screen.OnGraphData(data)			# Send message to draw new data
    else:
        self.dataFailCnt += 1
        self.baddata +=1
        
    if(self.dataFailCnt == 1000):
        self.dataFailCnt = 0
        (self.a.rate_min, self.a.rate_max, self.a.sample_rate, self.a.chan_min, self.a.chan_max,
              self.a.msg1, self.a.unused, self.a.err_msg,
              self.a.read_error,  self.a.write_error, self.a.underrun_error,
              self.a.latencyCapt, self.a.latencyPlay, self.a.interupts, self.a.fft_error, self.a.mic_max_display,
              self.a.data_poll_usec
        ) = QS.get_state()
        if (self.baddata > 100): self.a.myprint("No Data QS.sound State:")
        else: self.a.myprint("QS.sound State:") 
        print("QS.sound_error cnts:")
        a = QS.sound_errors()
        
        for Dev, Loc, rate, latncy, cnt in a:
            #'I/Q Rx Sample Input', 'hw:1,0', 48000, 0, 18162) Typical output
            print("\tDev: %s; loc: %s; rate: %d; latncy: %d; ErrCnt: %d"  %(Dev, Loc, rate, latncy, cnt))
        #print("#########################################################################") 
    if self.timer - self.heart_time0 > 0.10:		
        self.heart_time0 = self.timer
        Hardware.HeartBeat()                            # call hardware to perform background tasks

        if not (self.Mflpcnt ==0):
            self.Mflpcnt +=1
        if(self.Mflpcnt == 2):
            self.Mflpcnt = 0
            QS.measure_frequency(1)                     #set/reset the measure freq to assure we're using the correct mode
        if self.add_version and Hardware.GetFirmwareVersion() is not None:
            self.add_version = False
            self.config_text = "%s, firmware version 1.%d" % (self.config_text, Hardware.GetFirmwareVersion())
            self.main_frame.SetConfigText(self.config_text)     
   
    
def main():
  """If quisk is installed as a package, you can run it with quisk.main()."""
  App()
  application.MainLoop()

if __name__ == '__main__':
  main()

