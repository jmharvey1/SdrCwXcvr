#! /usr/bin/python

# All QUISK software is Copyright (C) 2006-2016 by James C. Ahlstrom.
# This free software is licensed for use under the GNU General Public
# License (GPL), see http://www.opensource.org.
# Note that there is NO WARRANTY AT ALL.  USE AT YOUR OWN RISK!!

"""The main program for Quisk VNA, a vector network analyzer.

Usage:  python quisk_vns.py [-c | --config config_file_path]
This can also be installed as a package and run as quisk_vna.main().
"""

from __future__ import print_function

import sys, os
os.chdir(os.path.normpath(os.path.dirname(__file__)))
if sys.path[0] != "'.'":		# Make sure the current working directory is on path
  sys.path.insert(0, '.')

import wx, wx.html, wx.lib.buttons, wx.lib.stattext, wx.lib.colourdb
import math, cmath, time, traceback, string, pickle
import threading, webbrowser
import _quisk as QS
from types import *
from quisk_widgets import *
import configure

DEBUG = 0

# Command line parsing: be able to specify the config file.
from optparse import OptionParser
parser = OptionParser()
parser.add_option('-c', '--config', dest='config_file_path',
		help='Specify the configuration file path')
parser.add_option('', '--config2', dest='config_file_path2', default='',
		help='Specify a second configuration file to read after the first')
parser.add_option('-a', '--ask', action="store_true", dest='AskMe', default=False,
		help='Ask which radio to use when starting')
argv_options = parser.parse_args()[0]
ConfigPath = argv_options.config_file_path	# Get config file path
ConfigPath2 = argv_options.config_file_path2
if sys.platform == 'win32':
  path = os.getenv('HOMEDRIVE', '') + os.getenv('HOMEPATH', '')
  for dir in ("Documents", "My Documents", "Eigene Dateien", "Documenti", "Mine Dokumenter"):
    config_dir = os.path.join(path, dir)
    if os.path.isdir(config_dir):
      break
  else:
    config_dir = os.path.join(path, "My Documents")
  try:
    import _winreg
    key = _winreg.OpenKey(_winreg.HKEY_CURRENT_USER,
       r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders")
    val = _winreg.QueryValueEx(key, "Personal")
    val = _winreg.ExpandEnvironmentStrings(val[0])
    _winreg.CloseKey(key)
    if os.path.isdir(val):
      DefaultConfigDir = val
    else:
      DefaultConfigDir = config_dir
  except:
    traceback.print_exc()
    DefaultConfigDir = config_dir
  if not ConfigPath:
    ConfigPath = os.path.join(DefaultConfigDir, "quisk_conf.py")
    if not os.path.isfile(ConfigPath):
      path = os.path.join(config_dir, "quisk_conf.py")
      if os.path.isfile(path):
        ConfigPath = path
  del config_dir
else:
  DefaultConfigDir = os.path.expanduser('~')
  if not ConfigPath:
    ConfigPath = os.path.join(DefaultConfigDir, ".quisk_conf.py")


if not ConfigPath:	# Use default path
  if sys.platform == 'win32':
    path = os.getenv('HOMEDRIVE', '') + os.getenv('HOMEPATH', '')
    for dir in ("Documents", "My Documents", "Eigene Dateien", "Documenti"):
      ConfigPath = os.path.join(path, dir)
      if os.path.isdir(ConfigPath):
        break
    else:
      ConfigPath = os.path.join(path, "My Documents")
    ConfigPath = os.path.join(ConfigPath, "quisk_conf.py")
    if not os.path.isfile(ConfigPath):	# See if the user has a config file
      try:
        import shutil	# Try to create an initial default config file
        shutil.copyfile('quisk_conf_win.py', ConfigPath)
      except:
        pass
  else:
    ConfigPath = os.path.expanduser('~/.quisk_conf.py')

class SoundThread(threading.Thread):
  """Create a second (non-GUI) thread to read samples."""
  def __init__(self):
    self.do_init = 1
    threading.Thread.__init__(self)
    self.doQuit = threading.Event()
    self.doQuit.clear()
  def run(self):
    """Read, process, play sound; then notify the GUI thread to check for FFT data."""
    if self.do_init:	# Open sound using this thread
      self.do_init = 0
      QS.start_sound()
      wx.CallAfter(application.PostStartup)
    while not self.doQuit.isSet():
      QS.read_sound()
      wx.CallAfter(application.OnReadSound)
    QS.close_sound()
  def stop(self):
    """Set a flag to indicate that the sound thread should end."""
    self.doQuit.set()

class GraphDisplay(wx.Window):
  """Display the graph within the graph screen."""
  def __init__(self, parent, x, y, graph_width, height, chary):
    wx.Window.__init__(self, parent,
       pos = (x, y),
       size = (graph_width, height),
       style = wx.NO_BORDER)
    self.parent = parent
    self.chary = chary
    self.graph_width = graph_width
    self.line_mag = []
    self.line_phase = []
    self.line_swr = []
    self.display_text = ""
    self.SetBackgroundColour(conf.color_graph)
    self.Bind(wx.EVT_PAINT, self.OnPaint)
    self.Bind(wx.EVT_LEFT_DOWN, parent.OnLeftDown)
    self.Bind(wx.EVT_LEFT_UP, parent.OnLeftUp)
    self.Bind(wx.EVT_MOTION, parent.OnMotion)
    self.Bind(wx.EVT_MOUSEWHEEL, parent.OnWheel)
    self.tune_tx = graph_width / 2	# Current X position of the Tx tuning line
    self.height = 10
    self.y_min = 1000
    self.y_max = 0
    self.y_ticks = []
    self.max_height = application.screen_height
    self.tuningPenTx = wx.Pen('Red', 1)
    self.magnPen = wx.Pen('Black', 1)
    self.phasePen = wx.Pen((0, 180, 0), 1)
    self.swrPen = wx.Pen('Blue', 1)
    self.backgroundPen = wx.Pen(self.GetBackgroundColour(), 1)
    self.horizPen = wx.Pen(conf.color_gl, 1, wx.SOLID)
    self.font = wx.Font(24, wx.FONTFAMILY_SWISS, wx.NORMAL,
          wx.FONTWEIGHT_NORMAL, face=conf.quisk_typeface)
    if sys.platform == 'win32':
      self.Bind(wx.EVT_ENTER_WINDOW, self.OnEnter)
  def OnEnter(self, event):
    self.SetFocus()	# Set focus so we get mouse wheel events
  def OnPaint(self, event):
    dc = wx.PaintDC(self)
    x = self.tune_tx
    dc.SetPen(self.tuningPenTx)
    dc.DrawLine(x, 0, x, self.max_height)
    dc.SetPen(self.horizPen)
    for y in self.y_ticks:
      dc.DrawLine(0, y, self.graph_width, y)
    # Magnitude
    t = 'Magnitude, '
    x = self.chary
    y = self.height - self.chary
    dc.SetTextForeground(self.magnPen.GetColour())
    dc.DrawText(t, x, y)
    w, h = dc.GetTextExtent(t)
    x += w + self.chary
    # Phase
    t = 'Phase, '
    dc.SetTextForeground(self.phasePen.GetColour())
    dc.DrawText(t, x, y)
    w, h = dc.GetTextExtent(t)
    x += w + self.chary
    # SWR
    t = 'SWR'
    dc.SetTextForeground(self.swrPen.GetColour())
    dc.DrawText(t, x, y)
    w, h = dc.GetTextExtent(t)
    x += w + self.chary
    # Draw graph
    if self.line_phase:		# Phase line
      # Try to avoid drawing vertical lines when the phase goes from +180 to -180
      dc.SetPen(self.phasePen)
      top = self.y_ticks[0]
      high = self.y_ticks[1]
      low = self.y_ticks[-2]
      bottom = self.y_ticks[-1]
      old_phase = self.line_phase[0]
      line = [(0, old_phase)]
      for x in range(1, self.graph_width):
        phase = self.line_phase[x]
        if phase < high and old_phase > low:
          line.append((x-1, bottom))
          dc.DrawLines(line)
          line = [(x, top), (x, phase)]
        elif phase > low and old_phase < high:
          line.append((x-1, top))
          dc.DrawLines(line)
          line = [(x, bottom), (x, phase)]
        else:
          line.append((x, phase))
        old_phase = phase
      dc.DrawLines(line)
    if self.line_mag:		# Magnitude line
      dc.SetPen(self.magnPen)
      dc.DrawLines(self.line_mag)
    if self.line_swr:		# SWR line
      dc.SetPen(self.swrPen)
      dc.DrawLines(self.line_swr)
    if self.display_text:
      dc.SetFont(self.font)
      dc.SetTextBackground(conf.color_graph)
      dc.SetTextForeground('red')
      dc.SetBackgroundMode(wx.SOLID)
      dc.DrawText(self.display_text, 10, 50)
  def SetHeight(self, height):
    self.height = height
    self.SetSize((self.graph_width, height))
  def SetTuningLine(self, tune_tx):
    dc = wx.ClientDC(self)
    dc.SetPen(self.backgroundPen)
    dc.DrawLine(self.tune_tx, 0, self.tune_tx, self.max_height)
    dc.SetPen(self.tuningPenTx)
    dc.DrawLine(tune_tx, 0, tune_tx, self.max_height)
    self.tune_tx = tune_tx
    self.Refresh()

class GraphScreen(wx.Window):
  """Display the graph screen X and Y axis, and create a graph display."""
  def __init__(self, parent, data_width, graph_width, correct_width, correct_delta, in_splitter=0):
    wx.Window.__init__(self, parent, pos = (0, 0))
    self.in_splitter = in_splitter	# Are we in the top of a splitter window?
    self.data_width = data_width
    self.graph_width = graph_width
    self.correct_width = correct_width
    self.correct_delta = correct_delta
    self.started = False
    self.doResize = False
    self.pen_tick = wx.Pen("Black", 1, wx.SOLID)
    self.font = wx.Font(10, wx.FONTFAMILY_SWISS, wx.NORMAL, wx.FONTWEIGHT_NORMAL, face=conf.quisk_typeface)
    self.SetFont(self.font)
    w = self.GetCharWidth() * 14 / 10
    h = self.GetCharHeight()
    self.freq_start = 1000000
    self.freq_stop  = 2000000
    self.charx = w
    self.chary = h
    self.mode = ''
    self.data_mag = []
    self.data_phase = []
    self.data_impedance = []
    self.data_reflect = []
    self.data_freq = [0] * data_width
    self.tick = max(2, h * 3 / 10)
    self.originX = w * 5
    self.offsetY = h + self.tick
    self.width = self.originX * 2 + self.graph_width + self.tick
    self.height = application.screen_height * 3 / 10
    self.x0 = self.originX + self.graph_width / 2		# center of graph
    self.originY = 10
    self.num_ticks = 8	# number of Y lines above the X axis
    self.dy_ticks = 10
    # The pixel = slope * value + zero_pixel
    # The value = (pixel - zero_pixel) / slope
    self.leftZero = 10		# y location of left zero value
    self.rightZero = 10		# y location of right zero value
    self.leftSlope = 10		# slope of left scale times 360
    self.rightSlope = 10	# slope of right scale times 360
    self.SetSize((self.width, self.height))
    self.SetSizeHints(self.width, 1, self.width)
    self.SetBackgroundColour(conf.color_graph)
    self.Bind(wx.EVT_SIZE, self.OnSize)
    self.Bind(wx.EVT_PAINT, self.OnPaint)
    self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
    self.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
    self.Bind(wx.EVT_MOTION, self.OnMotion)
    self.Bind(wx.EVT_MOUSEWHEEL, self.OnWheel)
    self.display = GraphDisplay(self, self.originX, 0, self.graph_width, 5, self.chary)
  def OnPaint(self, event):
    dc = wx.PaintDC(self)
    if self.started and not self.in_splitter:
      dc.SetFont(self.font)
      self.MakeYTicks(dc)
      self.MakeXTicks(dc)
  def OnIdle(self, event):
    if self.doResize:
      self.ResizeGraph()
  def OnSize(self, event):
    self.doResize = True
    self.ClearGraph()
    event.Skip()
  def ResizeGraph(self):
    """Change the height of the graph.

    Changing the width interactively is not allowed.
    Call after changing the zero or scale to recalculate the X and Y axis marks.
    """
    w, h = self.GetClientSize()
    if self.in_splitter:	# Splitter window has no X axis scale
      self.height = h
      self.originY = h
    else:
      self.height = h - self.chary		# Leave space for X scale
      self.originY = self.height - self.offsetY
    self.MakeYScale()
    self.display.SetHeight(self.originY)
    self.doResize = False
    self.started = True
    self.Refresh()
  def MakeYScale(self):
    chary = self.chary
    dy = self.dy_ticks = (self.originY - chary * 2) / self.num_ticks   # pixels per tick
    ytot = dy * self.num_ticks
    # Voltage dB scale
    dbs = 80	# Number of dB to display
    self.leftZero = self.originY - ytot - chary
    self.leftSlope = - ytot * 360 / dbs		# pixels per dB times 360
    # Phase scale
    self.rightSlope = - ytot			# pixels per degree times 360
    self.rightZero = self.originY - ytot / 2 - chary
    # SWR scale
    swrs = 9		# display range 1.0 to swrs
    self.swrSlope = - ytot * 360 / (swrs - 1)	# pixels per SWR unit times 360
    self.swrZero = self.originY - self.swrSlope / 360 - chary
  def MakeYTicks(self, dc):
    charx = self.charx
    chary = self.chary
    x1 = self.originX - self.tick * 3	# left of tick mark
    x2 = self.originX - 1		# x location of left y axis
    x3 = self.originX + self.graph_width	# end of graph data
    x4 = x3 + 1				# right y axis
    x5 = x3 + self.tick * 3		# right tick mark
    dc.SetPen(self.pen_tick)
    dc.DrawLine(x2, 0, x2, self.originY + 1)	# y axis
    dc.DrawLine(x4, 0, x4, self.originY + 1)	# y axis
    del self.display.y_ticks[:]
    y = self.leftZero
    dc.SetTextForeground(self.display.magnPen.GetColour())
    for i in range(self.num_ticks + 1):
      # Create the dB scale
      val = (y - self.leftZero) * 360 / self.leftSlope
      t = str(val)
      dc.DrawLine(x1, y, x2, y)
      self.display.y_ticks.append(y)
      w, h = dc.GetTextExtent(t)
      dc.DrawText(t, x1 - w, y - h / 2)
      y += self.dy_ticks
    y = self.leftZero
    dc.SetTextForeground(self.display.phasePen.GetColour())
    for i in range(self.num_ticks + 1):
      # Create the scale on the right
      val = (y - self.rightZero) * 360 / self.rightSlope
      t = str(val)
      dc.DrawLine(x4, y, x5, y)
      w, h = dc.GetTextExtent(t)
      dc.DrawText(t, self.width - w - charx, y - h / 2 + 3)	# right text
      y += self.dy_ticks
    # Create the SWR scale
    if self.mode == 'Reflection':
      y = self.leftZero
      dc.SetTextForeground(self.display.swrPen.GetColour())
      for i in range(self.num_ticks + 1):
        val = (y - self.swrZero) * 360 / self.swrSlope
        t = str(val)
        w, h = dc.GetTextExtent(t)
        dc.DrawText(t, w/2, y - h / 2)
        y += self.dy_ticks
  def MakeXTicks(self, dc):
    originY = self.originY
    x3 = self.originX + self.graph_width	# end of fft data
    charx , z = dc.GetTextExtent('-30000XX')
    tick0 = self.tick
    tick1 = tick0 * 2
    tick2 = tick0 * 3
    dc.SetTextForeground(self.display.magnPen.GetColour())
    # Draw the X axis
    dc.SetPen(self.pen_tick)
    dc.DrawLine(self.originX, originY, x3, originY)
    sample_rate = int(self.freq_stop - self.freq_start)
    if sample_rate < 12000:
      return
    VFO = int((self.freq_start + self.freq_stop) / 2)
    # Draw the band plan colors below the X axis
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
    stick =  1000		# small tick in Hertz
    mtick =  5000		# medium tick
    ltick = 10000		# large tick
    # check the width of the frequency label versus frequency span
    df = float(charx) * sample_rate / self.data_width	# max label freq in Hertz
    df *= 2.0
    df = math.log10(df)
    expn = int(df)
    mant = df - expn
    if mant < 0.3:	# label every 10
      tfreq = 10 ** expn
      ltick = tfreq
      mtick = ltick / 2
      stick = ltick / 10
    elif mant < 0.69:	# label every 20
      tfreq = 2 * 10 ** expn
      ltick = tfreq / 2
      mtick = ltick / 2
      stick = ltick / 10
    else:		# label every 50
      tfreq = 5 * 10 ** expn
      ltick = tfreq
      mtick = ltick / 5
      stick = ltick / 10
    # Draw the X axis ticks and frequency in kHz
    dc.SetPen(self.pen_tick)
    freq1 = VFO - sample_rate / 2
    freq1 = (freq1 / stick) * stick
    freq2 = freq1 + sample_rate + stick + 1
    y_end = 0
    for f in range (freq1, freq2, stick):
      x = self.x0 + int(float(f - VFO) / sample_rate * self.data_width)
      if self.originX <= x <= x3:
        if f % ltick is 0:		# large tick
          dc.DrawLine(x, originY, x, originY + tick2)
        elif f % mtick is 0:	# medium tick
          dc.DrawLine(x, originY, x, originY + tick1)
        else:					# small tick
          dc.DrawLine(x, originY, x, originY + tick0)
        if f % tfreq is 0:		# place frequency label
          t = str(f/1000)
          w, h = dc.GetTextExtent(t)
          dc.DrawText(t, x - w / 2, originY + tick2)
          y_end = originY + tick2 + h
    if y_end:		# mark the center of the display
      dc.DrawLine(self.x0, y_end, self.x0, application.screen_height)
  def ClearGraph(self):
    del self.display.line_mag[:]
    del self.display.line_phase[:]
    del self.display.line_swr[:]
    del self.data_mag[:]
    del self.data_phase[:]
    del self.data_impedance[:]
    del self.data_reflect[:]
    self.display.Refresh()
  def SetDisplayMsg(self, text=''):
    self.display.display_text = text
    self.display.Refresh()
  def SetMode(self, mode):
    self.mode = mode
  def OnGraphData(self, volts):
    # SWR = (1 + rho) / (1 - rho)
    # Create graph lines
    mode = self.mode
    del self.display.line_mag[:]
    del self.display.line_phase[:]
    del self.display.line_swr[:]
    del self.data_mag[:]
    del self.data_phase[:]
    del self.data_impedance[:]
    del self.data_reflect[:]
    if mode == 'Calibrate':
      for x in range(application.correct_width):
        self.calibrate_tmp[x] += volts[x]
      self.calibrate_count += 1
      for x in range(self.graph_width):
        self.data_impedance.append(50)
        self.data_reflect.append(0)
        i = x * self.correct_width / self.data_width
        magn = abs(volts[i])
        phase = cmath.phase(volts[i]) * 360. / (2.0 * math.pi)
        if magn < 1e-6:
          db = -120.0
        else:
          db = 20.0 * math.log10(magn)
        self.data_mag.append(db)
        y = self.leftZero - int( - db * self.leftSlope / 360.0 + 0.5)
        self.display.line_mag.append((x, y))
        self.data_phase.append(phase)
        y = self.rightZero - int( - phase * self.rightSlope / 360.0 + 0.5)
        y = int(y)
        self.display.line_phase.append(y)
    elif mode == 'Reflection':
      for x in range(self.graph_width):
        delta = self.correct_delta
        # Find the frequency for this pixel
        freq = self.data_freq[x]
        # Find the corresponding index into the correction array
        i = int(freq / delta)
        if i > self.correct_width - 2:
          i = self.correct_width - 2
        dd = float(freq - i * delta) / delta	# fractional part of next index for linear interpolation
        Vx = volts[x]
        # linear interpolation
        if application.reflection_short is not None and application.reflection_open is not None and application.reflection_load is not None:
          Vs = application.reflection_short[i] + (application.reflection_short[i+1] - application.reflection_short[i]) * dd
          Vo = application.reflection_open[i] + (application.reflection_open[i+1] - application.reflection_open[i]) * dd
          Vl = application.reflection_load[i] + (application.reflection_load[i+1] - application.reflection_load[i]) * dd
          S11 = Vl
          VVop = Vo - S11
          VVsh = Vs - S11
          try:
            S12S21 = 2.0 * VVop * VVsh / (VVsh - VVop)
            S22 = (VVop + VVsh) / (VVop - VVsh)
            reflect = (Vx - S11) / (S12S21 + S22 * (Vx - S11))
            Z = 50.0 * (1.0 + reflect) / (1.0 - reflect)
          except:
            Z = 50E3
            reflect = (Z - 50) / (Z + 50)
          #print ('Vs Vo Vl', abs(Vs), abs(Vo), abs(Vl), 'S22', abs(S22), 'S1221', abs(S12S21))
        else:
          if application.reflection_open is not None:
            correct = application.reflection_open[i] + (application.reflection_open[i+1] - application.reflection_open[i]) * dd
            if application.reflection_short is not None:
              correct = (correct - (application.reflection_short[i] + (application.reflection_short[i+1] - application.reflection_short[i]) * dd)) / 2.0
          else:		# Use Short
            correct = - (application.reflection_short[i] + (application.reflection_short[i+1] - application.reflection_short[i]) * dd)
          try:
            reflect = volts[x] / correct
            Z = 50.0 * (1.0 + reflect) / (1.0 - reflect)
          except:
            Z = 50E3
            reflect = (Z - 50) / (Z + 50)
        self.data_reflect.append(reflect)
        self.data_impedance.append(Z)
        magn = abs(reflect)
        swr = (1.0 + magn) / (1.0 - magn)
        if not 0.999 <= swr <= 99:
          swr = 99.0
        if magn < 1e-6:
          db = -120.0
        else:
          db = 20.0 * math.log10(magn)
        self.data_mag.append(db)
        y = self.leftZero - int( - db * self.leftSlope / 360.0 + 0.5)
        self.display.line_mag.append((x, y))
        phase = cmath.phase(reflect) * 360. / (2.0 * math.pi)
        self.data_phase.append(phase)
        y = self.rightZero - int( - phase * self.rightSlope / 360.0 + 0.5)
        y = int(y)
        self.display.line_phase.append(y)
        y = self.swrZero - int( - swr * self.swrSlope / 360.0 + 0.5)
        self.display.line_swr.append((x,y))
    else:	# Mode is transmission
      for x in range(self.graph_width):
        delta = self.correct_delta
        # Find the frequency for this pixel
        freq = self.data_freq[x]
        # Find the corresponding index into the correction array
        i = int(freq / delta)
        if i > self.correct_width - 2:
          i = self.correct_width - 2
        dd = float(freq - i * delta) / delta	# fractional part of next index for linear interpolation
        trans = volts[x]
        if application.transmission_open is not None:
          trans -= application.transmission_open[i] + (application.transmission_open[i+1] - application.transmission_open[i]) * dd
        trans /= application.transmission_short[i] + (application.transmission_short[i+1] - application.transmission_short[i]) * dd
        self.data_reflect.append(trans)
        self.data_impedance.append(50)
        magn = abs(trans)
        if magn < 1e-6:
          db = -120.0
        else:
          db = 20.0 * math.log10(magn)
        self.data_mag.append(db)
        y = self.leftZero - int( - db * self.leftSlope / 360.0 + 0.5)
        self.display.line_mag.append((x, y))
        phase = cmath.phase(trans) * 360. / (2.0 * math.pi)
        self.data_phase.append(phase)
        y = self.rightZero - int( - phase * self.rightSlope / 360.0 + 0.5)
        y = int(y)
        self.display.line_phase.append(y)
    self.display.Refresh()
  def NewFreq(self, start, stop):
    if self.freq_start != start or self.freq_stop != stop:
      self.ClearGraph()
    self.freq_start = start
    self.freq_stop = stop
    for i in range(self.data_width):	# The frequency in Hertz for every graph pixel
      self.data_freq[i] = int(start + float(stop - start) * i / (self.data_width - 1) + 0.5)
    self.SetTxFreq(index=self.display.tune_tx)
    self.doResize = True
  def SetTxFreq(self, freq=None, index=None):
    if index is None:
      index = int(float(freq - self.freq_start) * (self.data_width - 1) / (self.freq_stop - self.freq_start) + 0.5)
    if index < 0:
      index = 0
    elif index >= self.data_width:
      index = self.data_width - 1
    if freq is None:
      freq = self.data_freq[index]
    self.display.SetTuningLine(index)
    application.ShowFreq(freq, index)
  def GetMousePosition(self, event):
    """For mouse clicks in our display, translate to our screen coordinates."""
    mouse_x, mouse_y = event.GetPositionTuple()
    win = event.GetEventObject()
    if win is not self:
      x, y = win.GetPositionTuple()
      mouse_x += x
      mouse_y += y
    return mouse_x, mouse_y
  def OnLeftDown(self, event):
    mouse_x, mouse_y = self.GetMousePosition(event)
    self.SetTxFreq(index=mouse_x - self.originX)
    self.CaptureMouse()
  def OnLeftUp(self, event):
    if self.HasCapture():
      self.ReleaseMouse()
  def OnMotion(self, event):
    if event.Dragging() and event.LeftIsDown():
      mouse_x, mouse_y = self.GetMousePosition(event)
      self.SetTxFreq(index=mouse_x - self.originX)
  def OnWheel(self, event):
    tune = self.display.tune_tx + event.GetWheelRotation() / event.GetWheelDelta()
    self.SetTxFreq(index=tune)

class HelpScreen(wx.html.HtmlWindow):
  """Create the screen for the Help button."""
  def __init__(self, parent, width, height):
    wx.html.HtmlWindow.__init__(self, parent, -1, size=(width, height))
    if "gtk2" in wx.PlatformInfo:
      self.SetStandardFonts()
    self.SetFonts("", "", [10, 12, 14, 16, 18, 20, 22])
    # read in text from file help.html in the directory of this module
    self.LoadFile('help_vna.html')
  def OnLinkClicked(self, link):
    webbrowser.open(link.GetHref(), new=2)

class QMainFrame(wx.Frame):
  """Create the main top-level window."""
  def __init__(self, width, height):
    fp = open('__init__.py')		# Read in the title
    self.title = fp.readline().strip()
    fp.close()
    self.title = 'Quisk Vector Network Analyzer ' + self.title[7:]
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
    self.SetTitle("Radio %s   %s   %s" % (configure.Settings[1], self.title, text))

class Spacer(wx.Window):
  """Create a bar between the graph screen and the controls"""
  def __init__(self, parent):
    wx.Window.__init__(self, parent, pos = (0, 0),
       size=(-1, 6), style = wx.NO_BORDER)
    self.Bind(wx.EVT_PAINT, self.OnPaint)
    r, g, b = parent.GetBackgroundColour().Get()
    dark = (r * 7 / 10, g * 7 / 10, b * 7 / 10)
    light = (r + (255 - r) * 5 / 10, g + (255 - g) * 5 / 10, b + (255 - b) * 5 / 10)
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

class CalibrateDialog(wx.Dialog):
  def __init__(self, app):
    self.app = app
    self.correct_open = None
    self.correct_short = None
    self.correct_load = None
    w, h = app.main_frame.GetSizeTuple()
    width = w / 2
    if app.screen_name == "Reflection":
      title = "Calibrate for Reflection Mode"
      t = ''
      if app.reflection_short is not None:
        t += "Short"
      if app.reflection_open is not None:
        t += "Open"
      if app.reflection_load is not None:
        t += "Load"
      if t:
        t = "Reflection mode calibration is %s from %s" % (t, app.calibrate_time)
      else:
        t = "Reflection mode is Uncalibrated"
    else:
      title = "Calibrate for Transmission Mode"
      t = ''
      if app.transmission_short is not None:
        t += "Short"
      if app.transmission_open is not None:
        t += "Open"
      if t:
        t = "Transmission mode calibration is %s from %s" % (t, app.calibrate_time)
      else:
        t = "Transmission mode is Uncalibrated"
    wx.Dialog.__init__(self, None, -1, title, size=(width, h))
    tab = self.GetCharHeight() * 2
    y = tab
    txt = wx.StaticText(self, -1, t, pos=(tab, y))
    z, chary = txt.GetSizeTuple()
    y += chary * 3 / 2
    if app.screen_name == "Reflection":
      t = "To calibrate the VNA for reflection mode, connect the standard Short, Open and Load connectors to the unknown port, and press the button."
      t += "  Reflection mode requires at least an Open or Short calibration, but using all three is highly recommended."
    else:
      t = "To calibrate the VNA for transmission mode, connect the cables together for Short, or leave them unconnected for Open, and press the button."
      t += "  The Short calibration is required, but the Open calibration is optional."
    t += "  The calibration will be saved for use the next time the program starts."
    txt = wx.StaticText(self, -1, t, pos=(tab, y))
    txt.Wrap(width - tab * 2)
    w, h = txt.GetSizeTuple()
    y += h + chary
    # Calibrate buttons
    t1 = wx.StaticText(self, -1, "Connect the Short connector and press", pos=(tab, y))
    tw, th = t1.GetSizeTuple()
    bx = tab + tw + tab / 2
    b1 = wx.lib.buttons.GenButton(self, -1, '  Short  ')
    self.Bind(wx.EVT_BUTTON, self.OnBtnShort, b1)
    bw, bh = b1.GetSizeTuple()
    by = y + (th - bh) / 2
    b1.MoveXY(bx, by)
    self.txt_short = wx.StaticText(self, -1, "Not done", pos=(bx + bw + tab / 2, y))
    y = by + bh * 15 / 10
    by = y + (th - bh) / 2
    t2 = wx.StaticText(self, -1, "Connect the Open connector and press", pos=(tab, y), size = (tw, th))
    b2 = wx.lib.buttons.GenButton(self, -1, 'Open', pos = (bx, by), size = (bw, bh))
    self.Bind(wx.EVT_BUTTON, self.OnBtnOpen, b2)
    self.txt_open = wx.StaticText(self, -1, "Not done", pos=(bx + bw + tab / 2, y))
    y = by + bh * 15 / 10
    by = y + (th - bh) / 2
    if app.screen_name == "Reflection":
      t3 = wx.StaticText(self, -1, "Connect the Load connector and press", pos=(tab, y), size = (tw, th))
      b3 = wx.lib.buttons.GenButton(self, -1, 'Load', pos = (bx, by), size = (bw, bh))
      self.Bind(wx.EVT_BUTTON, self.OnBtnLoad, b3)
      self.txt_load = wx.StaticText(self, -1, "Not done", pos=(bx + bw + tab / 2, y))
      y = by + bh * 15 / 10
    # Calibrate buttons
    b1 = wx.lib.buttons.GenButton(self, -1, '  Calibrate  ')
    b1.Enable(False)
    w, h = b1.GetSizeTuple()
    b2 = wx.lib.buttons.GenButton(self, -1, 'Cancel', size=(w, h))
    self.Bind(wx.EVT_BUTTON, self.OnBtnCalibrate, b1)
    self.Bind(wx.EVT_BUTTON, self.OnBtnCancel, b2)
    ww = (width - w * 2 - 40) / 3
    b1.MoveXY(ww, y)
    b2.MoveXY(width - w - ww, y)
    y += h * 3 / 2
    self.SetClientSizeWH(width, y)
    self.btns = [b1, b2]
    # timer for calibrate buttons
    self.calibrate_timer = wx.Timer(self)
    self.Bind(wx.EVT_TIMER, self.OnCalibrateTimer, self.calibrate_timer)
  def OnBtnCalibrate(self, event):
    app = self.app
    if app.screen_name == "Reflection":
      app.reflection_short = self.correct_short
      app.reflection_open = self.correct_open
      app.reflection_load = self.correct_load
    elif app.screen_name == "Transmission":
      app.transmission_short = self.correct_short
      app.transmission_open = self.correct_open
    app.calibrate_time = time.asctime()
    app.EnableButtons()
    app.SetCalText()
    app.SaveState()
    self.EndModal(4)
  def OnBtnCancel(self, event):
    self.EndModal(5)
  def Calibrate(self):
    for b in self.btns:
      b.Enable(False)
    self.app.Calibrate()
    self.calibrate_timer.Start(3000, oneShot=True)
  def OnBtnShort(self, event):
    self.txt_short.SetLabel("Wait")
    self.mode = "Short"
    self.Calibrate()
  def OnBtnOpen(self, event):
    self.txt_open.SetLabel("Wait")
    self.mode = "Open"
    self.Calibrate()
  def OnBtnLoad(self, event):
    self.txt_load.SetLabel("Wait")
    self.mode = "Load"
    self.Calibrate()
  def OnCalibrateTimer(self, event):
    self.app.running = False
    if self.app.has_SetVNA:
      Hardware.SetVNA(key_down=0)
    for b in self.btns:
      b.Enable(True)
    data = self.app.graph.calibrate_tmp
    count = self.app.graph.calibrate_count
    if count == 0:
      if self.mode == "Short":
        self.txt_short.SetLabel("Not done")
      elif self.mode == "Open":
        self.txt_open.SetLabel("Not done")
      elif self.mode == "Load":
        self.txt_load.SetLabel("Not done")
      return
    for i in range(application.correct_width):
      data[i] /= count
    if self.mode == "Short":
      self.txt_short.SetLabel("Done")
      self.correct_short = data
    elif self.mode == "Open":
      self.txt_open.SetLabel("Done")
      self.correct_open = data
    elif self.mode == "Load":
      self.txt_load.SetLabel("Done")
      self.correct_load = data

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
      if os.path.isfile(ConfigPath2):	# See if the user has a second config file
        exec(compile(open(ConfigPath2).read(), ConfigPath2, 'exec'), d)	# execute the user's second config file
      for k, v in d.items():		# add user's config items to conf
        if k[0] != '_':				# omit items starting with '_'
          setattr(conf, k, v)
    else:
      setattr(conf, 'config_file_exists', False)
    # Read in configuration from the selected radio
    if configure: self.local_conf = configure.Configuration(self, argv_options.AskMe)
    if configure: self.local_conf.UpdateConf()
    # Choose whether to use Unicode or text symbols
    for k in ('sym_stat_mem', 'sym_stat_fav', 'sym_stat_dx',
        'btn_text_range_dn', 'btn_text_range_up', 'btn_text_play', 'btn_text_rec', 'btn_text_file_rec', 
		'btn_text_file_play', 'btn_text_fav_add',
        'btn_text_fav_recall', 'btn_text_mem_add', 'btn_text_mem_next', 'btn_text_mem_del'):
      if conf.use_unicode_symbols:
        setattr(conf, 'X' + k, getattr(conf, 'U' + k))
      else:
        setattr(conf, 'X' + k, getattr(conf, 'T' + k))
    MakeWidgetGlobals()
    self.graph_freq = 7e6
    self.graph_index = 50
    self.transmission_open = None
    self.transmission_short = None
    self.reflection_open = None
    self.reflection_short = None
    self.reflection_load = None
    self.reflection_cal = "Cal x"
    self.transmission_cal = "Cal x"
    self.calibrate_time = time.asctime()
    self.calibrate_version = 1
    # Open hardware file
    self.firmware_version = None
    global Hardware
    if configure and self.local_conf.GetHardware():
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
    # Initialization
    if configure: self.local_conf.Initialize()
    # get the screen size
    x, y, self.screen_width, self.screen_height = wx.Display().GetGeometry()
    self.Bind(wx.EVT_QUERY_END_SESSION, self.OnEndSession)
    self.sample_rate = 48000
    self.timer = time.time()		# A seconds clock
    self.time0 = 0			# timer to display fields
    self.clip_time0 = 0			# timer to display a CLIP message on ADC overflow
    self.heart_time0 = self.timer	# timer to call HeartBeat at intervals
    self.running = False
    self.startup = True
    self.save_data = []
    self.frequency = 0
    self.main_frame = frame = QMainFrame(10, 10)
    self.SetTopWindow(frame)
    # Find the data width, the width of returned graph data.
    width = self.screen_width * conf.graph_width
    width = int(width)
    self.data_width = width
    # correct_delta is the spacing of correction points in Hertz
    if conf.use_rx_udp == 10:		# Hermes UDP protocol
      self.max_freq = 30000000		# maximum calculation frequency
      self.correct_width = self.data_width	# number of data points in the correct arrays
    else:
      self.max_freq = 60000000
      self.correct_width = self.max_freq // 15000 + 4
    if hasattr(Hardware, 'SetVNA'):
      self.has_SetVNA = True
      start, stop = Hardware.SetVNA(vna_start=0, vna_stop=self.max_freq, vna_count=self.correct_width)
      self.correct_delta = float(stop - start) / (self.correct_width - 1)
      Hardware.SetVNA(vna_count=self.data_width)
    else:
      self.has_SetVNA = False
      self.correct_delta = 1
    # Restore persistent program state
    self.init_path = os.path.join(os.path.dirname(ConfigPath), '.quisk_vna_init.pkl')
    try:
      fp = open(self.init_path, "rb")
      d = pickle.load(fp)
      fp.close()
      for k, v in d.items():
        if k in self.StateNames:
          setattr(self, k, v)
    except:
      pass #traceback.print_exc()
    # Record the basic application parameters
    if sys.platform == 'win32':
      h = self.main_frame.GetHandle()
    else:
      h = 0
    # FFT size must equal the data_width so that all data points are returned!
    QS.record_app(self, conf, self.data_width, self.data_width,
                 1, self.sample_rate, h)
    # Make all the screens and hide all but one
    self.graph = GraphScreen(frame, self.data_width, self.data_width, self.correct_width, self.correct_delta)
    self.screen = self.graph
    width = self.graph.width
    self.help_screen = HelpScreen(frame, width, self.screen_height / 10)
    self.help_screen.Hide()
    # Make a vertical box to hold all the screens and the bottom rows
    vertBox = self.vertBox = wx.BoxSizer(wx.VERTICAL)
    frame.SetSizer(vertBox)
    # Add the screens
    vertBox.Add(self.graph, 1)
    vertBox.Add(self.help_screen, 1)
    # Add the spacer
    vertBox.Add(Spacer(frame), 0, wx.EXPAND)
    # Add the sizer for the buttons
    szr1 = wx.BoxSizer(wx.HORIZONTAL)
    vertBox.Add(szr1, 0, wx.EXPAND, 0)
    # Make the buttons in row 1
    self.buttons1 = buttons1 = []
    self.screen_name = "Reflection"
    self.graph.SetMode(self.screen_name)
    b = RadioButtonGroup(frame, self.OnBtnScreen, ('  Transmission  ', 'Reflection', 'Help'), self.screen_name)
    buttons1 += b.buttons
    self.btn_run = b = QuiskCheckbutton(frame, self.OnBtnRun, 'Run')
    buttons1.append(b)
    self.btn_calibrate = b = QuiskPushbutton(frame, self.OnBtnCal, 'Calibrate..')
    buttons1.append(b)
    width = 0
    for b in buttons1:
      w, height = b.GetMinSize()
      if width < w:
        width = w
    for i in range(24, 8, -2):
      font = wx.Font(i, wx.FONTFAMILY_SWISS, wx.NORMAL, wx.FONTWEIGHT_NORMAL, face=conf.quisk_typeface)
      frame.SetFont(font)
      w, h = frame.GetTextExtent('Start   ')
      if h < height * 9 / 10:
        break
    for b in buttons1:
      b.SetMinSize((width, height))
    # Frequency entry start and stop
    t = wx.lib.stattext.GenStaticText(frame, -1, 'Start  ')
    t.SetFont(font)
    t.SetBackgroundColour(conf.color_bg)
    gap = max(2, height/8)
    freq0 = t
    e = wx.TextCtrl(frame, -1, '1', style=wx.TE_PROCESS_ENTER)
    e.SetFont(font)
    tw, z = e.GetTextExtent("xx30.333xxxxx")
    e.SetMinSize((tw, height))
    e.SetBackgroundColour(conf.color_entry)
    self.freq_start_ctrl = e
    frame.Bind(wx.EVT_TEXT_ENTER, self.OnNewFreq, source=e)
    frame.Bind(wx.EVT_TEXT, self.OnNewFreq, source=e)
    t = wx.lib.stattext.GenStaticText(frame, -1, 'Stop  ')
    t.SetFont(font)
    t.SetBackgroundColour(conf.color_bg)
    freq2 = t
    e = wx.TextCtrl(frame, -1, '30', style=wx.TE_PROCESS_ENTER)
    e.SetFont(font)
    e.SetMinSize((tw, height))
    e.SetBackgroundColour(conf.color_entry)
    self.freq_stop_ctrl = e
    frame.Bind(wx.EVT_TEXT_ENTER, self.OnNewFreq, source=e)
    frame.Bind(wx.EVT_TEXT, self.OnNewFreq, source=e)
    # Band buttons
    ilst = []
    slst = []
    for l in conf.BandEdge.keys():	# Sort keys
      if not (l in conf.bandLabels or l == '60'):
        continue
      try:
        ilst.append((int(l), conf.BandEdge[l]))
      except ValueError:	# item is a string, not an integer
        slst.append((l, conf.BandEdge[l]))
    ilst.sort()
    ilst.reverse()
    slst.sort()
    band = []
    width = 0
    for l in ilst + slst:
      b = QuiskPushbutton(frame, self.OnBtnBand, str(l[0]))
      b.bandEdge = l[1]
      band.append(b)
      w, h= b.GetMinSize()
      if width < w:
        width = w
    # make a list of all buttons
    self.buttons = buttons1 + band
    # Add button row to sizer
    gap = max(2, height / 8)
    gap2 = max(2, height / 4)
    szr1.Add(buttons1[0], 0, wx.RIGHT|wx.LEFT, gap)
    szr1.Add(buttons1[1], 0, wx.RIGHT, gap)
    szr1.Add(buttons1[2], 0, wx.RIGHT, gap)
    szr1.Add(buttons1[3], 0, wx.RIGHT|wx.LEFT, gap2)
    szr1.Add(buttons1[4], 0, wx.RIGHT|wx.LEFT, gap)
    szr1.Add(freq0, 0, wx.ALIGN_CENTER_VERTICAL)
    szr1.Add(self.freq_start_ctrl, 0, wx.RIGHT, gap)
    szr1.Add(freq2, 0, wx.ALIGN_CENTER_VERTICAL)
    szr1.Add(self.freq_stop_ctrl, 0, wx.RIGHT, gap)
    for x in band:
      szr1.Add(x, 1, wx.RIGHT, gap)
    self.statusbar = self.main_frame.CreateStatusBar()
    # Set top window size
    self.main_frame.SetClientSizeWH(self.graph.width, self.screen_height * 5 / 10)
    w, h = self.main_frame.GetSizeTuple()
    self.main_frame.SetSizeHints(w, 1, w)
    if hasattr(Hardware, 'pre_open'):       # pre_open() is called before open()
      Hardware.pre_open()
    if conf.use_rx_udp == 10:		# Hermes UDP protocol
      self.add_version = False
      conf.tx_ip = Hardware.hermes_ip
      conf.tx_audio_port = conf.rx_udp_port
    elif conf.use_rx_udp:
      self.add_version = True		# Add firmware version to config text
      conf.rx_udp_decimation = 8 * 8 * 8
      if not conf.tx_ip:
        conf.tx_ip = conf.rx_udp_ip
      if not conf.tx_audio_port:
        conf.tx_audio_port = conf.rx_udp_port + 2
    else:
      self.add_version = False
    # Open the hardware.  This must be called before open_sound().
    self.config_text = Hardware.open()
    self.status_error = "No hardware response"	# possible error messages
    if self.config_text:
      self.main_frame.SetConfigText(self.config_text)
      if conf.use_rx_udp == 10:		# Hermes UDP protocol
        if self.config_text[0:12] == "Capture from":
          self.status_error = ''
    else:
      self.config_text = "Missing config_text"
    # Note: Subsequent calls to set channels must not name a higher channel number.
    #       Normally, these calls are only used to reverse the channels.
    QS.open_sound(conf.name_of_sound_capt, '', self.sample_rate,
                conf.data_poll_usec, conf.latency_millisecs,
                '', conf.tx_ip, conf.tx_audio_port,
                48000, 0, 0, 1.0, '', 48000)
    self.Bind(wx.EVT_IDLE, self.graph.OnIdle)
    frame.Show()
    self.NewFreq(1000000, 30000000)
    self.SetCalText()
    self.WriteFields()
    self.EnableButtons()
    QS.set_fdx(1)
    QS.set_rx_mode(0)
    self.sound_thread = SoundThread()
    self.sound_thread.start()
    return True
  def OnExit(self):
    QS.close_rx_udp()
    ##self.local_conf.SaveState()	# to save default radio selection
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
    if self.has_SetVNA:
      Hardware.SetVNA(key_down=0, do_tx=True)
    time.sleep(0.5)
    if self.sound_thread:
      self.sound_thread.stop()
    for i in range(0, 20):
      if threading.activeCount() == 1:
        break
      time.sleep(0.1)
    Hardware.close()
  def OnBtnBand(self, event):
    btn = event.GetEventObject()
    start, stop = btn.bandEdge
    start = float(start) * 1e-6
    stop = float(stop) * 1e-6
    self.freq_start_ctrl.SetValue(str(start))
    self.freq_stop_ctrl.SetValue(str(stop))
  def Calibrate(self):
    self.graph.calibrate_tmp = [0] * self.correct_width
    self.graph.calibrate_count = 0
    self.graph.SetMode("Calibrate")
    self.NewFreq(0, self.max_freq)
    if self.has_SetVNA:
      Hardware.SetVNA(key_down=1)
    self.running = True
    self.startup = True
  def OnBtnCal(self, event):
    if self.has_SetVNA:
      Hardware.SetVNA(key_down=0, vna_start=0, vna_stop=self.max_freq, vna_count=self.correct_width)
    dlg = CalibrateDialog(self)
    dlg.ShowModal()
    dlg.Destroy()
    if application.has_SetVNA:
      Hardware.SetVNA(key_down=0, vna_count=self.data_width)
  def OnBtnScreen(self, event):
    btn = event.GetEventObject()
    self.screen_name = btn.GetLabel().strip()
    if self.screen_name == 'Help':
      self.help_screen.Show()
      self.graph.Hide()
    else:
      self.help_screen.Hide()
      self.graph.Show()
      self.graph.SetMode(self.screen_name)
    self.vertBox.Layout()
    self.EnableButtons()
  def OnBtnRun(self, event):
    btn = event.GetEventObject()
    run = btn.GetValue()
    if run:
      for b in self.buttons1:
        if b != btn:
          b.Enable(False)
    else:
      for b in self.buttons1:
        b.Enable(True)
    self.graph.SetMode(self.screen_name)
    if not self.OnNewFreq():
      return
    if self.has_SetVNA:
      if run:
        self.running = True
        self.startup = True
        Hardware.SetVNA(key_down=1)
      else:
        self.running = False
        Hardware.SetVNA(key_down=0)
  def EnableButtons(self):
    if self.screen_name == 'Transmission':
      if self.transmission_short is not None and len(self.transmission_short) == self.correct_width:
        self.btn_run.Enable(1)
      else:
        self.btn_run.Enable(0)
    elif self.screen_name == 'Reflection':
      if (self.reflection_short is not None or self.reflection_open is not None) and len(self.reflection_short) == self.correct_width:
        self.btn_run.Enable(1)
      else:
        self.btn_run.Enable(0)
    else:		# Help
      self.btn_run.Enable(0)
  def ShowFreq(self, freq, index):
    self.frequency = freq
    if hasattr(Hardware, 'ChangeFilterFrequency'):
      Hardware.ChangeFilterFrequency(freq)
    self.graph_freq = freq
    self.graph_index = index
    self.WriteFields()
  def OnNewFreq(self, event=None):
    if self.status_error and self.status_error[0:15] != "Error in Start ":
      return False
    try:
      start = self.freq_start_ctrl.GetValue()
      start = float(start) * 1e6
      stop = self.freq_stop_ctrl.GetValue()
      stop = float(stop) * 1e6
    except:
      self.status_error = "Error in Start or Stop freq"
      #traceback.print_exc()
      return False
    start = int(start + 0.5)
    stop = int(stop + 0.5)
    if start > stop:
      self.status_error = "Error in Start or Stop freq"
      return False
    if stop > self.max_freq:
      stop = self.max_freq
      self.freq_stop_ctrl.SetValue("%.6f" % (stop * 1.E-6))
    self.status_error = ''
    self.NewFreq(start, stop)
    return True
  def NewFreq(self, start, stop):
    if application.has_SetVNA:
      start, stop = Hardware.SetVNA(vna_start=start, vna_stop=stop)
    self.graph.NewFreq(start, stop)
  def SetCalText(self):
    text = ''
    if self.reflection_short is not None:
      text += "S"
    if self.reflection_open is not None:
      text += "O"
    if self.reflection_load is not None:
      text += "L"
    if text:
      text = "Cal " + text
    else:
      text = "Cal x"
    self.reflection_cal = text
    text = ''
    if self.transmission_short is not None:
      text += "S"
    if self.transmission_open is not None:
      text += "O"
    if text:
      text = "Cal " + text
    else:
      text = "Cal x"
    self.transmission_cal = text
  def WriteFields(self):
    index = self.graph_index
    if index < 0:
      index = 0
    elif index >= self.data_width:
      index = self.data_width - 1
    freq = "Freq %.6f" % (self.frequency * 1E-6)
    mode = self.graph.mode
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
    pass
  def OnReadSound(self):	# called at frequent intervals
    self.timer = time.time()
    dat = QS.get_graph(0, 1.0, 0)
    if dat and self.running:
      dat = list(dat)
      try:
        start = dat.index(0)
      except ValueError:
        self.save_data += dat
        return
      data = self.save_data + dat[0:start]
      self.save_data = dat[start+1:]
      if self.graph.mode == 'Calibrate':
        if len(data) != self.correct_width:
          if DEBUG: print('  bad calibrate array', len(data), self.correct_width)
          return
      else:
        if len(data) != self.data_width:
          if DEBUG: print('  bad data array', len(data), self.data_width)
          return
      for i in range(len(data)):
        data[i] /= 2147483647.0
      if self.startup:		# always skip the first block of data
        self.startup = False
      else:
        self.graph.OnGraphData(data)
    if QS.get_overrange() and self.running:
      self.clip_time0 = self.timer
      self.status_error = "      *** CLIP ***"
      self.graph.SetDisplayMsg("Clip")
    if self.clip_time0:
      if self.timer - self.clip_time0 > 1.0:
        self.clip_time0 = 0
        self.status_error = ''
        self.graph.SetDisplayMsg()
    if self.timer - self.heart_time0 > 0.10:		# call hardware to perform background tasks
      self.heart_time0 = self.timer
      Hardware.HeartBeat()
      if self.add_version and self.firmware_version is None:
        self.firmware_version = Hardware.GetFirmwareVersion()
        if self.firmware_version is not None:
          if self.firmware_version < 3:
            self.status_error = "Need firmware ver 3"
          else:
            self.status_error = ''
    # Set text fields
    if  self.timer - self.time0 > 0.5:
      self.time0 = self.timer
      #print "len %5d  re %9.6f  im %9.6f  mag %9.6f  phase %7.2f" % (len(data),
      #   volts.real, volts.imag, abs(volts), phase)
      #print "Z re %12.2f  im %12.2f  mag %12.2f  phase %7.2f" % (zzz.real, zzz.imag,
      #  abs(zzz), cmath.phase(zzz) * 360. / (2.0 * math.pi))
      self.WriteFields()

def main():
  """If quisk is installed as a package, you can run it with quisk.main()."""
  App()
  application.MainLoop()

if __name__ == '__main__':
  main()

