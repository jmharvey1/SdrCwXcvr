# These are Quisk widgets

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import sys, re
import wx, wx.lib.buttons, wx.lib.stattext
from types import *
# The main script will alter quisk_conf_defaults to include the user's config file.
import quisk_conf_defaults as conf
import _quisk as QS


wxVersion = wx.version()[0]

def EmptyBitmap(width, height):
##  if wxVersion in ('2', '3'):
    return wx.EmptyBitmap(width, height)
##  else:
##    return wx.Bitmap(width, height)

def MakeWidgetGlobals():
  global button_font, button_uline_font, button_bezel, button_width, button_height, button_text_width, button_text_height
  global _bitmap_menupop, _bitmap_sliderpop, _bitmap_cyclepop
  button_bezel = 3		# size of button bezel in pixels
  button_font = wx.Font(conf.button_font_size, wx.FONTFAMILY_SWISS, wx.NORMAL,
           wx.FONTWEIGHT_NORMAL, False, conf.quisk_typeface)
  button_uline_font = wx.Font(conf.button_font_size, wx.FONTFAMILY_SWISS, wx.NORMAL,
           wx.FONTWEIGHT_NORMAL, True, conf.quisk_typeface)
  dc = wx.MemoryDC()
  dc.SetFont(button_font)
  tmp_bm = EmptyBitmap(1, 1)		# Thanks to NS4Y
  dc.SelectObject(tmp_bm)
  button_text_width, button_text_height = dc.GetTextExtent('0')
  button_width = button_text_width + 2 + 2 * button_bezel # + 4 * int(self.useFocusInd)
  button_height = button_text_height + 2 + 2 * button_bezel # + 4 * int(self.useFocusInd)
  # Make a bitmap for the slider pop button
  height = button_text_height + 2	# button height less bezel
  width = height
  _bitmap_sliderpop = EmptyBitmap(height, height)
  dc.SelectObject(_bitmap_sliderpop)
  pen = wx.Pen(conf.color_enable, 1)
  dc.SetPen(pen)
  brush = wx.Brush(conf.color_btn)
  dc.SetBackground(brush)
  dc.Clear()
  w = width * 5 // 10
  w += w % 2
  bd = (width - 1 - w) // 2
  x1 = bd
  x2 = x1 + w
  y1 = 0
  y2 = height - y1 - 1
  dc.DrawLine(x1, y1, x2, y1)
  dc.DrawLine(x2, y1, x2, y2)
  dc.DrawLine(x2, y2, x1, y2)
  dc.DrawLine(x1, y2, x1, y1)
  x0 = (x2 + x1) // 2
  dc.DrawLine(x0, y1 + 3, x0, y2 - 2)
  y0 = height * 6 // 10
  dc.DrawLine(x0 - 2, y0, x0 + 3, y0)
  y0 -= 1
  color = pen.GetColour()
  r = color.Red()
  g = color.Green()
  b = color.Blue()
  f = 160
  r = min(r + f, 255)
  g = min(g + f, 255)
  b = min(b + f, 255)
  color = wx.Colour(r, g, b)
  dc.SetPen(wx.Pen(color, 1, wx.SOLID))
  dc.DrawLine(x0 - 2, y0, x0 + 3, y0)
  dc.SelectObject(wx.NullBitmap)
  # Make a bitmap for the menu pop button
  _bitmap_menupop = EmptyBitmap(height, height)
  dc.SelectObject(_bitmap_menupop)
  dc.SetBackground(brush)
  dc.Clear()
  dc.SetPen(wx.Pen(conf.color_enable, 1))
  dc.SetBrush(wx.Brush(conf.color_enable))
  x = 3
  for y in range(2, height - 3, 5):
    dc.DrawRectangle(x, y, 3, 3)
    dc.DrawLine(x + 5, y + 1, width - 3, y + 1)
  dc.SelectObject(wx.NullBitmap)
  # Make a bitmap for the cycle button
  _bitmap_cyclepop = EmptyBitmap(height, height)
  dc.SelectObject(_bitmap_cyclepop)
  dc.SetBackground(brush)
  dc.SetFont(button_font)
  dc.Clear()
  w, h = dc.GetTextExtent(conf.btn_text_cycle)
  dc.DrawText(conf.btn_text_cycle, (height - x) // 2, (height - y) // 2)
  dc.SelectObject(wx.NullBitmap)

def FreqFormatter(freq):	# Format the string or integer frequency by adding blanks
  freq = int(freq)
  if freq >= 0:
    t = str(freq)
    minus = ''
  else:
    t = str(-freq)
    minus = '- '
  l = len(t)
  if l > 9:
    txt = "%s%s %s %s %s" % (minus, t[0:-9], t[-9:-6], t[-6:-3], t[-3:])
  elif l > 6:
    txt = "%s%s %s %s" % (minus, t[0:-6], t[-6:-3], t[-3:])
  elif l > 3:
    txt = "%s%s %s" % (minus, t[0:-3], t[-3:])
  else:
    txt = minus + t
  return txt

class FrequencyDisplay(wx.lib.stattext.GenStaticText):
  """Create a frequency display widget."""
  def __init__(self, frame, width, height):
    wx.lib.stattext.GenStaticText.__init__(self, frame, -1, '3',
         style=wx.ALIGN_CENTER|wx.ST_NO_AUTORESIZE)
    border = 4
    for points in range(30, 6, -1):
      font = wx.Font(points, wx.FONTFAMILY_SWISS, wx.NORMAL, wx.FONTWEIGHT_NORMAL, False, conf.quisk_typeface)
      self.SetFont(font)
      w, h = self.GetTextExtent('333 444 555 Hz')
      if w < width and h < height - border * 2:
        break
    self.SetSizeHints(w, h, w * 5, h)
    self.height = h
    self.points = points
    border = self.border = (height - self.height) // 2
    self.height_and_border = h + border * 2
    self.SetBackgroundColour(conf.color_freq)
    self.SetForegroundColour(conf.color_freq_txt)
    self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)	# Click on a digit changes the frequency
    self.Bind(wx.EVT_LEFT_DCLICK, self.OnLeftDown)
    self.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
    self.Bind(wx.EVT_MOUSEWHEEL, self.OnWheel)
    if sys.platform == 'win32':
      self.Bind(wx.EVT_ENTER_WINDOW, self.OnEnter)
    self.timer = wx.Timer(self)                     # Holding a digit continuously changes the frequency
    self.Bind(wx.EVT_TIMER, self.OnTimer)
    self.repeat_time = 0                           # Repeat function is inactive
  def OnEnter(self, event):
    if not application.w_phase:
      self.SetFocus()	# Set focus so we get mouse wheel events
  def Clip(self, clip):
    """Change color to indicate clipping."""
    if clip:
      self.SetBackgroundColour('deep pink')
    else:
      self.SetBackgroundColour(conf.color_freq)
    self.Refresh()
  def Display(self, freq):
    """Set the frequency to be displayed."""
    txt = FreqFormatter(freq)
    self.SetLabel('%s Hz' % txt)
  def GetIndex(self, event):		# Determine which digit is being changed
    mouse_x, mouse_y = event.GetPosition()
    width, height = self.GetClientSize().Get()
    text = self.GetLabel()
    tw, th = self.GetTextExtent(text)
    edge = (width - tw) // 2
    digit = self.GetTextExtent('0')[0]
    blank = self.GetTextExtent(' ')[0]
    if mouse_x < edge - digit:
      return None
    x = width - edge - self.GetTextExtent(" Hz")[0] - mouse_x
    if x < 0:
      return None
    #print ('size', width, height, 'mouse', mouse_x, mouse_y, 'digit', digit, 'blank', blank)
    shift = 0
    while x > digit * 3:
      shift += 1
      x -= digit * 3 + blank
    if x < 0:
      return None
    return x // digit + shift * 3	# index of digit being changed
  def OnLeftDown(self, event):		# Click on a digit changes the frequency
    if self.repeat_time:
      self.timer.Stop()
      self.repeat_time = 0
    index = self.GetIndex(event)
    if index is not None:
      self.index = index
      mouse_x, mouse_y = event.GetPosition()
      width, height = self.GetClientSize().Get()
      if mouse_y < height // 2:
        self.increase = True
      else:
        self.increase = False
      self.ChangeFreq()
      self.repeat_time = 300		# first button push
      self.timer.Start(milliseconds=300, oneShot=True)
  def OnLeftUp(self, event):
    self.timer.Stop()
    self.repeat_time = 0
  def ChangeFreq(self):
    text = self.GetLabel()
    text = text.replace(' ', '')[:-2]
    text = text[:len(text)-self.index] + '0' * self.index
    if self.increase:
      freq = int(text) + 10 ** self.index
    else:
      freq = int(text) - 10 ** self.index
      if freq <= 0 and self.index > 0:
        freq = 10 ** (self.index - 1)
    #print ('X', x, 'N', n, text, 'freq', freq)
    application.ChangeRxTxFrequency(None, freq)
  def OnTimer(self, event):
    if self.repeat_time == 300:     # after first push, turn on repeats
      self.repeat_time = 150
    elif self.repeat_time > 20:
      self.repeat_time -= 5
    self.ChangeFreq()
    self.timer.Start(milliseconds=self.repeat_time, oneShot=True)
  def OnWheel(self, event):
    index = self.GetIndex(event)
    if index is not None:
      self.index = index
      if event.GetWheelRotation() > 0:
        self.increase = True
      else:
        self.increase = False
      self.ChangeFreq()

class SliderBoxH:
  """A horizontal control with a slider and text with a value.  The text must have a %d or %f if display is True."""
  def __init__(self, parent, text, init, themin, themax, handler, display, pos, width, scale=1):
    self.text = text
    self.handler = handler
    self.display = display
    self.scale = scale
    if display:		# Display the slider value
      t1 = self.text % (themin * scale)
      t2 = self.text % (themax * scale)
      if len(t1) > len(t2):		# set text size to the largest
        t = t1
      else:
        t = t2
    else:
      t = self.text
    if pos is None:
      self.text_ctrl = wx.StaticText(parent, -1, t, style=wx.ST_NO_AUTORESIZE)
      w2, h2 = self.text_ctrl.GetSize()
      self.text_ctrl.SetSizeHints(w2, -1, w2)
      self.slider = wx.Slider(parent, -1, init, themin, themax)
    else:	# Thanks to Stephen Hurd
      self.text_ctrl = wx.StaticText(parent, -1, t, pos=pos)
      w2, h2 = self.text_ctrl.GetSize()
      self.slider = wx.Slider(parent, -1, init, themin, themax)
      w3, h3 = self.slider.GetSize()
      p2 = pos[1]
      if h3 > h2:
        p2 -= (h3 - h2) / 2
      else:
        p2 += (h2 - h3) / 2
      self.slider.SetSize((width - w2, h3))
      self.slider.SetPosition((pos[0] + w2, p2))
    self.slider.Bind(wx.EVT_SCROLL, self.OnScroll)
    self.text_ctrl.SetForegroundColour(parent.GetForegroundColour())
    self.OnScroll()
  def OnScroll(self, event=None):
    if event:
      event.Skip()
      if self.handler:
        self.handler(event)
    if self.display:
      t = self.text % (self.slider.GetValue() * self.scale)
    else:
      t = self.text
    self.text_ctrl.SetLabel(t)
  def GetValue(self):
    return self.slider.GetValue()
  def SetValue(self, value):
    # Set slider visual position; does not call handler
    self.slider.SetValue(value)
    self.OnScroll()

class SliderBoxHH(SliderBoxH, wx.BoxSizer):
  """A horizontal control with a slider and text with a value.  The text must have a %d if display is True."""
  def __init__(self, parent, text, init, themin, themax, handler, display):
    wx.BoxSizer.__init__(self, wx.HORIZONTAL)
    SliderBoxH.__init__(self, parent, text, init, themin, themax, handler, display, None, None)
    #font = wx.Font(10, wx.FONTFAMILY_SWISS, wx.NORMAL, wx.FONTWEIGHT_NORMAL, False, conf.quisk_typeface)
    #self.text_ctrl.SetFont(font)
    self.Add(self.text_ctrl, 0, wx.ALIGN_CENTER)
    self.Add(self.slider, 1, wx.ALIGN_CENTER)

class SliderBoxV(wx.BoxSizer):
  """A vertical box containing a slider and a text heading"""
  # Note: A vertical wx slider has the max value at the bottom.  This is
  # reversed for this control.
  def __init__(self, parent, text, init, themax, handler, display=False, themin=0):
    wx.BoxSizer.__init__(self, wx.VERTICAL)
    self.slider = wx.Slider(parent, -1, init, themin, themax, style=wx.SL_VERTICAL|wx.SL_INVERSE)
    self.slider.Bind(wx.EVT_SCROLL, handler)
    sw, sh = self.slider.GetSize()
    self.text = text
    self.themin = themin
    self.themax = themax
    if display:		# Display the slider value when it is thumb'd
      self.text_ctrl = wx.StaticText(parent, -1, str(themax))
      self.text_ctrl.SetFont(button_font)
      w1, self.text_height = self.text_ctrl.GetSize()	# Measure size with max number
      self.text_ctrl.SetLabel(str(themin))
      w3, h3 = self.text_ctrl.GetSize()	# Measure size with min number
      self.text_ctrl.SetLabel(text)
      w2, h2 = self.text_ctrl.GetSize()	# Measure size with text
      self.width = max(w1, w2, w3, sw) + self.text_ctrl.GetCharWidth()
      self.text_ctrl.SetSizeHints(self.width, -1, self.width)
      self.slider.Bind(wx.EVT_SCROLL_THUMBTRACK, self.Change)
      self.slider.Bind(wx.EVT_SCROLL_THUMBRELEASE, self.ChangeDone)
    else:
      self.text_ctrl = wx.StaticText(parent, -1, text)
      self.text_ctrl.SetFont(button_font)
      w2, self.text_height = self.text_ctrl.GetSize()	# Measure size with text
      self.width = max(w2, sw) + self.text_ctrl.GetCharWidth()
      self.text_ctrl.SetSizeHints(self.width, -1, self.width)
    self.text_ctrl.SetForegroundColour(parent.GetForegroundColour())
    self.Add(self.text_ctrl, 0, wx.ALIGN_CENTER_VERTICAL)
    self.Add(self.slider, 1, wx.ALIGN_CENTER_VERTICAL)
  def Change(self, event):
    event.Skip()
    self.text_ctrl.SetLabel(str(self.slider.GetValue()))
  def ChangeDone(self, event):
    event.Skip()
    self.text_ctrl.SetLabel(self.text)
  def GetValue(self):
    return self.slider.GetValue()
  def SetValue(self, value):
    # Set slider visual position; does not call handler
    self.slider.SetValue(value)

class QuiskText1(wx.lib.stattext.GenStaticText):
  # Self-drawn text for QuiskText.
  def __init__(self, parent, size_text, height, style=0, fixed=False):
    wx.lib.stattext.GenStaticText.__init__(self, parent, -1, '',
                 pos = wx.DefaultPosition, size = wx.DefaultSize,
                 style = wx.ST_NO_AUTORESIZE|style,
                 name = "QuiskText1")
    self.fixed = fixed
    self.size_text = size_text
    self.pen = wx.Pen(conf.color_btn, 2)
    self.brush = wx.Brush(conf.color_freq)
    self.SetForegroundColour(conf.color_freq_txt)
    self.SetSizeHints(1, height, 9999, height)
  def _MeasureFont(self, dc, width, height):
    # Set decreasing point size until size_text fits in the space available
    for points in range(20, 6, -1):
      if self.fixed:
        font = wx.Font(points, wx.FONTFAMILY_MODERN, wx.NORMAL, wx.FONTWEIGHT_NORMAL, False, conf.quisk_typeface)
      else:
        font = wx.Font(points, wx.FONTFAMILY_SWISS, wx.NORMAL, wx.FONTWEIGHT_NORMAL, False, conf.quisk_typeface)
      dc.SetFont(font)
      w, h = dc.GetTextExtent(self.size_text)
      if w < width and h < height:
        break
    self.size_text = ''
    self.SetFont(font)
  def OnPaint(self, event):
    dc = wx.PaintDC(self)
    width, height = self.GetClientSize().Get()
    if not width or not height:
      return
    dc.SetPen(self.pen)
    dc.SetBrush(self.brush)
    dc.DrawRectangle(1, 1, width-1, height-1)
    label = self.GetLabel()
    if not label:
      return
    if self.size_text:
      self._MeasureFont(dc, width-2, height-2)
    else:
      dc.SetFont(self.GetFont())
    if self.IsEnabled():
      dc.SetTextForeground(self.GetForegroundColour())
    else:
      dc.SetTextForeground(wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT))
    style = self.GetWindowStyleFlag()
    w, h = dc.GetTextExtent(label)
    y = (height - h) // 2
    if y < 0:
      y = 0
    if style & wx.ALIGN_RIGHT:
      x = width - w - 4
    elif style & wx.ALIGN_CENTER:
      x = (width - w - 1)//2
    else:
      x = 3
    dc.DrawText(label, x, y)

class QuiskText(wx.BoxSizer):
  # A one-line text display left/right/center justified and vertically centered.
  # The height of the control is fixed as "height".  The width is expanded.
  # The font is chosen so size_text fits in the client area.
  def __init__(self, parent, size_text, height, style=0, fixed=False):
    wx.BoxSizer.__init__(self, wx.HORIZONTAL)
    self.TextCtrl = QuiskText1(parent, size_text, height, style, fixed)
    self.Add(self.TextCtrl, 1, flag=wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL)
  def SetLabel(self, label):
    self.TextCtrl.SetLabel(label)

# Start of our button classes.  They are compatible with wxPython GenButton
# buttons.  Use the usual methods for access:
# GetLabel(self), SetLabel(self, label):	Get and set the label
# Enable(self, flag), Disable(self), IsEnabled(self):	Enable / Disable
# GetValue(self), SetValue(self, value):	Get / Set check button state True / False
# SetIndex(self, index):	For cycle buttons, set the label from its index

class QuiskButtons:
  """Base class for special buttons."""
  def __init__(self):
    self.up_brush = wx.Brush(conf.color_btn)
    r, g, b = self.up_brush.GetColour().Get(False)
    r, g, b = min(255,r+32), min(255,g+32), min(255,b+32)
    self.down_brush = wx.Brush(wx.Colour(r, g, b))
    self.color_disable = conf.color_disable
  def InitButtons(self, text, text_color=None):
    if text_color:
      self.text_color = text_color
    else:
      self.text_color = conf.color_enable
    self.SetBezelWidth(button_bezel)
    self.SetBackgroundColour(conf.color_btn)
    self.SetUseFocusIndicator(False)
    self.decoration = None
    self.char_shortcut = ''
    self.SetFont(button_font)
    if text:
      w, h = self.GetTextExtent(text)
    else:
      w, h = self.GetTextExtent("OK")
      self.Disable()	# create a size for null text, but Disable()
    w += button_bezel * 2 + self.GetCharWidth()
    h = h * 12 // 10
    h += button_bezel * 2
    self.SetSizeHints(w-10, h, 999, h, 1, 1) #JMH 20190815 added the -10 to get the buttons to fit Alongside FLDIGI
  def DrawLabel(self, dc, width, height, dx=0, dy=0):	# Override to change Disable text color
      if self.up:	# Clear the background here
        dc.SetBrush(self.up_brush)
      else:
        dc.SetBrush(self.down_brush)
      dc.SetPen(wx.TRANSPARENT_PEN)
      bw = self.bezelWidth
      dc.DrawRectangle(bw, bw, width - bw * 2, height - bw * 2)
      dc.SetFont(self.GetFont())
      label = self.GetLabel()
      tw, th = dc.GetTextExtent(label)
      self.label_width = tw
      dx = dy = self.labelDelta
      slabel = re.split('('+unichr(0x25CF)+')', label)	# unicode symbol for record: a filled dot
      for part in slabel:		# This code makes the symbol red.  Thanks to Christof, DJ4CM.
        if self.IsEnabled():
          if part == unichr(0x25CF):
            dc.SetTextForeground('red')
          else:
            dc.SetTextForeground(self.text_color)
        else:
          dc.SetTextForeground(self.color_disable)
        if self.char_shortcut:
          scut = part.split(self.char_shortcut, 1)
          if len(scut) == 2:	# The shortcut character is present in the string
            dc.DrawText(scut[0], (width-tw)//2+dx, (height-th)//2+dy)
            dx += dc.GetTextExtent(scut[0])[0]
            dc.SetFont(button_uline_font)
            dc.DrawText(self.char_shortcut, (width-tw)//2+dx, (height-th)//2+dy)
            dx += dc.GetTextExtent(self.char_shortcut)[0]
            dc.SetFont(self.GetFont())
            dc.DrawText(scut[1], (width-tw)//2+dx, (height-th)//2+dy)
            dx += dc.GetTextExtent(scut[1])[0]
          else:
            dc.DrawText(part, (width-tw)//2+dx, (height-th)//2+dy)
        else:
          dc.DrawText(part, (width-tw)//2+dx, (height-th)//2+dy)
        dx += dc.GetTextExtent(part)[0]
      if self.decoration and conf.decorate_buttons:
        wd, ht = dc.GetTextExtent(self.decoration)
        dc.DrawText(self.decoration, width - wd * 15 // 10, (height - ht) // 2)
  def OnKeyDown(self, event):
    pass
  def OnKeyUp(self, event):
    pass
  def DrawGlyphCycle(self, dc, width, height):	# Add a cycle indicator to the label
    if not conf.decorate_buttons:
      return
    uch = conf.btn_text_cycle
    wd, ht = dc.GetTextExtent(uch)
    if wd * 2 + self.label_width > width:		# not enough space
      uch = conf.btn_text_cycle_small
      wd, ht = dc.GetTextExtent(uch)
      dc.DrawText(uch, width - wd, (height - ht) // 2)
    else:
      dc.DrawText(uch, width - wd * 15 // 10, (height - ht) // 2)
  def SetColorGray(self):
    self.SetBackgroundColour(wx.Colour(220, 220, 220))	# This sets the bezel colors
    self.SetBezelWidth(2)
    self.text_color = 'black'
    self.color_disable = 'white'
    self.up_brush = wx.Brush(wx.Colour(220, 220, 220))
    self.down_brush = wx.Brush(wx.Colour(240, 240, 240))

class QuiskBitmapButton(wx.lib.buttons.GenBitmapButton):
  def __init__(self, parent, command, bitmap, use_right=False):
    self.command = command
    self.bitmap = bitmap
    wx.lib.buttons.GenBitmapButton.__init__(self, parent, -1, bitmap)
    self.SetFont(button_font)
    self.SetBezelWidth(button_bezel)
    self.SetBackgroundColour(conf.color_btn)
    self.SetUseFocusIndicator(False)
    self.Bind(wx.EVT_BUTTON, self.OnButton)
    self.direction = 1
    if use_right:
      self.Bind(wx.EVT_RIGHT_DOWN, self.OnRightDown)
      self.Bind(wx.EVT_RIGHT_UP, self.OnRightUp)
  def DoGetBestSize(self):
    return self.bitmap.GetWidth() + button_bezel * 2, self.bitmap.GetHeight() + button_bezel * 2
  def OnButton(self, event):
    if self.command:
      self.command(event)
  def OnRightDown(self, event):
    if self.GetBitmapLabel() == _bitmap_cyclepop:
      self.OnLeftDown(event) 
  def OnRightUp(self, event):
    if self.GetBitmapLabel() == _bitmap_cyclepop:
      self.direction = -1
      self.OnLeftUp(event)
      self.direction = 1

class QuiskPushbutton(QuiskButtons, wx.lib.buttons.GenButton):
  """A plain push button widget."""
  def __init__(self, parent, command, text, use_right=False, text_color=None, style=0):
    QuiskButtons.__init__(self)
    wx.lib.buttons.GenButton.__init__(self, parent, -1, text, style=style)
    self.command = command
    self.Bind(wx.EVT_BUTTON, self.OnButton)
    self.InitButtons(text, text_color)
    self.direction = 1
    if use_right:
      self.Bind(wx.EVT_RIGHT_DOWN, self.OnRightDown)
      self.Bind(wx.EVT_RIGHT_UP, self.OnRightUp)
  def OnButton(self, event):
    if self.command:
      self.command(event)
  def OnRightDown(self, event):
    self.direction = -1
    self.OnLeftDown(event) 
  def OnRightUp(self, event):
    self.OnLeftUp(event)
    self.direction = 1
##  def SetValue(self, n, value):
##      print("SetValue: %d" %value)
      

class QuiskRepeatbutton(QuiskButtons, wx.lib.buttons.GenButton):
  """A push button that repeats when held down."""
  def __init__(self, parent, command, text, up_command=None, use_right=False):
    QuiskButtons.__init__(self)
    wx.lib.buttons.GenButton.__init__(self, parent, -1, text)
    self.command = command
    self.up_command = up_command
    self.timer = wx.Timer(self)
    self.Bind(wx.EVT_TIMER, self.OnTimer)
    self.Bind(wx.EVT_BUTTON, self.OnButton)
    self.InitButtons(text)
    self.repeat_state = 0		# repeater button inactive
    self.direction = 1
    if use_right:
      self.Bind(wx.EVT_RIGHT_DOWN, self.OnRightDown)
      self.Bind(wx.EVT_RIGHT_UP, self.OnRightUp)
  def SendCommand(self, command):
    if command:
      event = wx.PyEvent()
      event.SetEventObject(self)
      command(event)
  def OnLeftDown(self, event):
    if self.IsEnabled():
      self.shift = event.ShiftDown()
      self.control = event.ControlDown()
      self.SendCommand(self.command)
      self.repeat_state = 1		# first button push
      self.timer.Start(milliseconds=300, oneShot=True)
    wx.lib.buttons.GenButton.OnLeftDown(self, event)
  def OnLeftUp(self, event):
    if self.IsEnabled():
      self.SendCommand(self.up_command)
      self.repeat_state = 0
      self.timer.Stop()
    wx.lib.buttons.GenButton.OnLeftUp(self, event)
  def OnRightDown(self, event):
    if self.IsEnabled():
      self.shift = event.ShiftDown()
      self.control = event.ControlDown()
      self.direction = -1
      self.OnLeftDown(event) 
  def OnRightUp(self, event):
    if self.IsEnabled():
      self.OnLeftUp(event)
      self.direction = 1
  def OnTimer(self, event):
    if self.repeat_state == 1:	# after first push, turn on repeats
      self.timer.Start(milliseconds=150, oneShot=False)
      self.repeat_state = 2
    if self.repeat_state:		# send commands until button is released
      self.SendCommand(self.command)
  def OnButton(self, event):
    pass	# button command not used

class QuiskCheckbutton(QuiskButtons, wx.lib.buttons.GenToggleButton):
  """A button that pops up and down, and changes color with each push."""
  # Check button; get the checked state with self.GetValue()
  def __init__(self, parent, command, text, color=None, use_right=False):
    QuiskButtons.__init__(self)
    wx.lib.buttons.GenToggleButton.__init__(self, parent, -1, text)
    self.InitButtons(text)
    self.Bind(wx.EVT_BUTTON, self.OnButton)
    self.button_down = 0		# used for radio buttons
    self.command = command
    if color is None:
      self.down_brush = wx.Brush(conf.color_check_btn)
    else:
      self.down_brush = wx.Brush(color)
    self.direction = 1
    if use_right:
      self.Bind(wx.EVT_RIGHT_DOWN, self.OnRightDown)
      self.Bind(wx.EVT_RIGHT_UP, self.OnRightUp)
  def SetValue(self, value, do_cmd=False):
    wx.lib.buttons.GenToggleButton.SetValue(self, value)
    self.button_down = value
    if do_cmd and self.command:
      event = wx.PyEvent()
      event.SetEventObject(self)
      self.command(event)
  def OnButton(self, event):
    if self.command:
      self.command(event)
  def OnRightDown(self, event):
    self.direction = -1
    self.OnLeftDown(event) 
  def OnRightUp(self, event):
    self.OnLeftUp(event)
    self.direction = 1
  def Shortcut(self, event):
    self.SetValue(not self.GetValue(), True)

class QuiskBitField(wx.Window):
  """A control used to set/unset bits."""
  def __init__(self, parent, numbits, value, height, command):
    self.numbits = numbits
    self.value = value
    self.height = height
    self.command = command
    self.backgroundBrush = wx.Brush('white')
    self.pen = wx.Pen('light gray', 1)
    self.font = parent.GetFont()
    self.charx, self.chary = parent.GetTextExtent('1')
    self.linex = []	# x pixel of vertical lines
    self.bitx = []	# x pixel of character for bits
    space = self.space = max(2, self.charx * 2 // 10)
    width = 0
    for i in range(numbits - 1):
      width += space + self.charx + space
      self.linex.append(width)
    width = space
    for i in range(numbits):
      self.bitx.append(width)
      width += self.charx + space * 2
    wx.Window.__init__(self, parent, size=(width + 4, height), style=wx.BORDER_SUNKEN)
    self.Bind(wx.EVT_PAINT, self.OnPaint)
    self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
  def OnPaint(self, event):
    dc = wx.PaintDC(self)
    dc.SetBackground(self.backgroundBrush)
    dc.Clear()
    dc.SetFont(self.font)
    dc.SetPen(self.pen)
    for x in self.linex:
      dc.DrawLine(x, 0, x, self.height)
    for i in range(self.numbits):
      power = self.numbits - i - 1
      x = self.bitx[i]
      if self.value & (1 << power):
        dc.DrawText('1', x, 0)
  def OnLeftDown(self, event):
    mouse_x, mouse_y = event.GetPosition().Get()
    for index in range(len(self.linex)):
      if mouse_x < self.linex[index]:
        break
    else:
      index = self.numbits - 1
    power = self.numbits - index - 1
    mask = 1 << power
    if self.value & mask:
      self.value &= ~ mask
    else:
      self.value |= mask
    self.Refresh()
    if self.command:
      self.command(self)

class QFilterButtonWindow(wx.Frame):
  """Create a window with controls for the button"""
  def __init__(self, wrap, value):
    self.wrap = wrap
    l = self.valuelist = []
    bw = 10
    incr = 10
    for i in range(0, 101):
      l.append(bw)
      bw += incr
      if bw == 100:
        incr = 20
      elif bw == 500:
        incr = 50
      elif bw == 1000:
        incr = 100
      elif bw == 5000:
        incr = 500
      elif bw == 10000:
        incr = 1000
    x, y = wrap.GetPosition().Get()
    x, y = wrap.GetParent().ClientToScreen(wx.Point(x, y))
    w, h = wrap.GetSize()
    height = h * 10
    size = (w, height)
    if sys.platform == 'win32':
      pos = (x, y - height)
      t = 'Filter'
    else:
      pos = (x, y - height - h)
      t = ''
    wx.Frame.__init__(self, wrap.GetParent(), -1, t, pos, size,
      wx.FRAME_TOOL_WINDOW|wx.FRAME_FLOAT_ON_PARENT|wx.CLOSE_BOX|wx.CAPTION|wx.SYSTEM_MENU)
    self.SetBackgroundColour(conf.color_freq)
    self.Bind(wx.EVT_CLOSE, self.OnClose)
    try:
      index = self.valuelist.index(value)
    except ValueError:
      index = 0
      self.wrap.button.slider_value = self.valuelist[0]
    self.slider = wx.Slider(self, -1, index, 0, 100, (0, 0), (w//2, height), wx.SL_VERTICAL|wx.SL_INVERSE)
    self.slider.Bind(wx.EVT_SCROLL, self.OnSlider)
    self.SetTitle("%d" % self.valuelist[index])
    self.Show()
    self.slider.SetFocus()
  def OnSlider(self, event):
    index = self.slider.GetValue()
    value = self.valuelist[index]
    self.SetTitle("%d" % value)
    self.wrap.ChangeSlider(value)
    #self.wrap.SetLabel(str(value))
    #self.wrap.SetValue(True, True)
    #application.filterAdjBw1 = value
  def OnClose(self, event):
    self.wrap.adjust = None
    self.Destroy()

class QSliderButtonWindow(wx.Frame):
  """Create a window with controls for the button"""
  def __init__(self, button, value):
    self.button = button
    x, y = button.GetPosition().Get()
    x, y = button.GetParent().ClientToScreen(wx.Point(x, y))
    w, h = button.GetSize()
    height = h * 10
    size = (w, height)
    if sys.platform == 'win32':
      pos = (x, y - height)
    else:
      pos = (x, y - height - h)
    wx.Frame.__init__(self, button.GetParent(), -1, '', pos, size,
      wx.FRAME_TOOL_WINDOW|wx.FRAME_FLOAT_ON_PARENT|wx.CLOSE_BOX|wx.CAPTION|wx.SYSTEM_MENU)
    self.SetBackgroundColour(conf.color_freq)
    self.Bind(wx.EVT_CLOSE, self.OnClose)
    self.slider = wx.Slider(self, -1, value,
             self.button.slider_min, self.button.slider_max,
             (0, 0), (w//2, height), wx.SL_VERTICAL|wx.SL_INVERSE)
    self.slider.Bind(wx.EVT_SCROLL, self.OnSlider)
    if self.button.display:
      value = float(value) / self.button.slider_max
      self.SetTitle("%6.3f" % value)
    self.Show()
    self.slider.SetFocus()
  def OnSlider(self, event):
    value = self.slider.GetValue()
    if self.button.display:
      v = float(value) / self.button.slider_max
      self.SetTitle("%6.3f" % v)
    self.button.ChangeSlider(value)
  def OnClose(self, event):
    self.button.adjust = None
    self.Destroy()

# Dual slider widget for bias
class QDualSliderButtonWindow(wx.Frame):	# Thanks to Steve, KF7O
  """Create a window with controls for the button"""
  def __init__(self, button):
    self.button = button
    x, y = button.GetPosition().Get()
    x, y = button.GetParent().ClientToScreen(wx.Point(x, y))
    w, h = button.GetSize()
    w = w * 12 // 10
    height = h * 10
    size = (w, height)
    if sys.platform == 'win32':
      pos = (x, y - height)
    else:
      pos = (x, y - height - h)
    wx.Frame.__init__(self, button.GetParent(), -1, '', pos, size,
      wx.FRAME_TOOL_WINDOW|wx.FRAME_FLOAT_ON_PARENT|wx.CLOSE_BOX|wx.CAPTION|wx.SYSTEM_MENU)
    self.SetBackgroundColour(conf.color_freq)
    self.Bind(wx.EVT_CLOSE, self.OnClose)
    panel = wx.Panel(self, -1)
    panel.SetBackgroundColour(conf.color_freq)
    hbox = wx.BoxSizer(wx.HORIZONTAL)
    self.lslider = wx.Slider(panel, -1, self.button.lslider_value,
             self.button.slider_min, self.button.slider_max,
             (0, 0), (w//2, height), wx.SL_VERTICAL|wx.SL_INVERSE)
    self.lslider.Bind(wx.EVT_SCROLL, self.OnSlider)
    hbox.Add(self.lslider, flag=wx.LEFT)
    self.rslider = wx.Slider(panel, -1, self.button.rslider_value,
             self.button.slider_min, self.button.slider_max,
             (0, 0), (w//2, height), wx.SL_VERTICAL|wx.SL_INVERSE)
    self.rslider.Bind(wx.EVT_SCROLL, self.OnSlider)
    hbox.Add(self.rslider, flag=wx.RIGHT)
    panel.SetSizer(hbox)
    if self.button.display:
      self.SetTitle("%3d   %3d" % (self.button.lslider_value,self.button.rslider_value))
    self.Show()
    self.lslider.SetFocus()
  def OnSlider(self, event):
    lvalue = self.lslider.GetValue()
    rvalue = self.rslider.GetValue()
    self.button.ChangeSlider(lvalue,rvalue)
    if self.button.display:
      self.SetTitle("%3d    %3d" % (self.button.lslider_value,self.button.rslider_value))
  def OnClose(self, event):
    self.button.adjust = None
    self.Destroy()

class WrapControl(wx.BoxSizer):
  def __init__(self):
    wx.BoxSizer.__init__(self, wx.HORIZONTAL)
  def Enable(self, value=True):
    self.button.Enable(value)
  def SetLabel(self, text=None):
    if text is not None:
      self.button.SetLabel(text)
  def GetParent(self):
    return self.button.GetParent()
  def GetValue(self):
    return self.button.GetValue()
  def SetValue(self, value, do_cmd=False):
    self.button.SetValue(value, do_cmd)
  def GetLabel(self):
    return self.button.GetLabel()
  def __getattr__(self, name):
    return getattr(self.button, name)

class WrapPushButton(WrapControl):
  def __init__(self, button, control):
    self.button = button
    WrapControl.__init__(self)
    self.Add(button, 1, flag=wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL)
    b = QuiskPushbutton(button.GetParent(), control, conf.btn_text_switch)
    self.Add(b, 0, flag=wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL|wx.LEFT, border=2)

class WrapMenu(WrapControl):
  def __init__(self, button, menu, on_open=None):
    self.button = button
    self.menu = menu
    self.on_open = on_open
    WrapControl.__init__(self)
    self.Add(button, 1, flag=wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL)
    b = QuiskBitmapButton(button.GetParent(), self.OnPopButton, _bitmap_menupop)
    self.Add(b, 0, flag=wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL|wx.LEFT, border=2)
  def OnPopButton(self, event):
    if self.on_open:
      self.on_open(self.menu)
    pos = (5, 5)
    self.button.PopupMenu(self.menu, pos)

class WrapSlider(WrapControl):
  def __init__(self, button, command, slider_value=0, slider_min=0, slider_max=1000, display=False, wintype=''):
    self.adjust = None
    self.dual = False						# dual means separate slider values for on and off
    self.button = button
    self.main_command = button.command
    button.command = self.OnMainButton
    self.command = command
    button.slider_value = slider_value		# value for not dual
    button.slider_value_off = slider_value	# value for dual and button up
    button.slider_value_on = slider_value		# value for dual and button down
    self.slider_min = slider_min
    self.slider_max = slider_max
    self.display = display					# Display the value at the top
    self.wintype = wintype
    WrapControl.__init__(self)
    self.Add(button, 1, flag=wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL)
    b = QuiskBitmapButton(button.GetParent(), self.OnPopButton, _bitmap_sliderpop)
    self.Add(b, 0, flag=wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL|wx.LEFT, border=2)
  def SetDual(self, dual):		# dual means separate slider values for on and off
    self.dual = dual
    if self.adjust:
      self.adjust.Destroy()
      self.adjust = None
  def DeleteSliderWindow(self):
    if self.adjust:
      self.adjust.Destroy()
      self.adjust = None
  def OnPopButton(self, event):
    if self.adjust:
      self.adjust.Destroy()
      self.adjust = None
    else:
      if not self.dual:
        value = self.button.slider_value
      elif self.button.GetValue():
        value = self.button.slider_value_on
      else:
        value = self.button.slider_value_off
      if self.wintype == 'filter':
        self.adjust = QFilterButtonWindow(self, value)
      else:
        self.adjust = QSliderButtonWindow(self, value)
  def OnMainButton(self, event):
    if self.adjust:
      self.adjust.Destroy()
      self.adjust = None
    if self.main_command:
      self.main_command(event)
  def ChangeSlider(self, value):
    if not self.dual:
      self.button.slider_value = value
    elif self.button.GetValue():
      self.button.slider_value_on = value
    else:
      self.button.slider_value_off = value
    if self.wintype == 'filter':
      self.button.SetLabel(str(value))
      self.button.Refresh()
    if self.command:
      event = wx.PyEvent()
      event.SetEventObject(self.button)
      self.command(event)
  def SetSlider(self, value=None, value_off=None, value_on=None):
    if value is not None:
      self.button.slider_value = value
    if value_off is not None:
      self.button.slider_value_off = value_off
    if value_on is not None:
      self.button.slider_value_on = value_on

class WrapDualSlider(WrapControl):	# Thanks to Steve, KF7O
  def __init__(self, button, command, lslider_value=0, rslider_value=0, slider_min=0, slider_max=1000, display=0):
    self.adjust = None
    self.button = button
    self.main_command = button.command
    button.command = self.OnMainButton
    self.command = command
    button.lslider_value = lslider_value
    button.rslider_value = rslider_value     
    self.slider_min = slider_min
    self.slider_max = slider_max
    self.display = display                  # Display the value at the top
    WrapControl.__init__(self)
    self.Add(button, 1, flag=wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL)
    print("Size",self.button.GetSize())
    ## This is a hack to get _bitmap_sliderpop
    ## It would be better if _bitmap_sliderpop were not a global variable 
    ##but a first-class member in another module
    _bitmap_sliderpop = MakeWidgetGlobals.__globals__['_bitmap_sliderpop']
    b = QuiskBitmapButton(button.GetParent(), self.OnPopButton, _bitmap_sliderpop)
    self.Add(b, 0, flag=wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL|wx.LEFT, border=2)
  def OnPopButton(self, event):
    if self.adjust:
      self.adjust.Destroy()
      self.adjust = None
    else:
      self.adjust = QDualSliderButtonWindow(self)
  def OnMainButton(self, event):
    if self.adjust:
      self.adjust.Destroy()
      self.adjust = None
    if self.main_command:
      self.main_command(event)
  def ChangeSlider(self, lvalue, rvalue):
    self.button.lslider_value = lvalue
    self.button.rslider_value = rvalue
    if self.command:
      event = wx.PyEvent()
      event.SetEventObject(self.button)
      self.command(event)

class QuiskCycleCheckbutton(QuiskCheckbutton):
  """A button that cycles through its labels with each push.

  The button is up for labels[0], down for all other labels.  Change to the
  next label for each push.  If you call SetLabel(), the label must be in the list.
  The self.index is the index of the current label.
  """
  def __init__(self, parent, command, labels, color=None, is_radio=False):
    self.labels = list(labels)		# Be careful if you change this list
    self.index = 0		# index of selected label 0, 1, ...
    self.direction = 0	# 1 for up, -1 for down, 0 for no change to index
    self.is_radio = is_radio	# Is this a radio cycle button?
    if color is None:
      color = conf.color_cycle_btn
    QuiskCheckbutton.__init__(self, parent, command, labels[0], color)
    self.Bind(wx.EVT_RIGHT_DOWN, self.OnRightDown)
    self.Bind(wx.EVT_LEFT_DCLICK, self.OnLeftDclick)
  def SetLabel(self, label, do_cmd=False):
    self.index = self.labels.index(label)
    QuiskCheckbutton.SetLabel(self, label)
    QuiskCheckbutton.SetValue(self, self.index)
    if do_cmd and self.command:
      event = wx.PyEvent()
      event.SetEventObject(self)
      self.command(event)
  def SetIndex(self, index, do_cmd=False):
    self.index = index
    QuiskCheckbutton.SetLabel(self, self.labels[index])
    QuiskCheckbutton.SetValue(self, index)
    if do_cmd and self.command:
      event = wx.PyEvent()
      event.SetEventObject(self)
      self.command(event)
  def OnButton(self, event):
    if not self.is_radio or self.button_down:
      self.direction = 1
      self.index += 1
      if self.index >= len(self.labels):
        self.index = 0
      self.SetIndex(self.index)
    else:
      self.direction = 0
    if self.command:
      self.command(event)
  def OnRightDown(self, event):		# Move left in the list of labels
    if not self.is_radio or self.GetValue():
      self.index -= 1
      if self.index < 0:
        self.index = len(self.labels) - 1
      self.SetIndex(self.index)
      self.direction = -1
      if self.command:
        self.command(event)
  def OnLeftDclick(self, event):	# Left double-click: Set index zero
    if not self.is_radio or self.GetValue():
      self.index = 0
      self.SetIndex(self.index)
      self.direction = 1
      if self.command:
        self.command(event)
  def DrawLabel(self, dc, width, height, dx=0, dy=0):
    QuiskCheckbutton.DrawLabel(self, dc, width, height, dx, dy)
    self.DrawGlyphCycle(dc, width, height)
  def Shortcut(self, event):
    index = self.index + 1
    if index >= len(self.labels):
      index = 0
    self.SetIndex(index, True)

class RadioButtonGroup:
  """This class encapsulates a group of radio buttons.  This class is not a button!

  The "labels" is a list of labels for the toggle buttons.  An item
  of labels can be a list/tuple, and the corresponding button will
  be a cycle button.
  """
  def __init__(self, parent, command, labels, default, shortcuts=()):
    self.command = command
    self.buttons = []
    self.button = None
    self.shortcuts = list(shortcuts[:])
    self.last_shortcut = 0
    i = 0
    for text in labels:
      if type(text) in (ListType, TupleType):
        b = QuiskCycleCheckbutton(parent, self.OnButton, text, is_radio=True)
        if shortcuts:
          b.char_shortcut = shortcuts[i]
        for t in text:
          if t == default and self.button is None:
            b.SetLabel(t)
            self.button = b
      else:
        b = QuiskCheckbutton(parent, self.OnButton, text)
        if shortcuts:
          b.char_shortcut = shortcuts[i]
        if text == default and self.button is None:
          b.SetValue(True)
          self.button = b
      self.buttons.append(b)
      i += 1
  def ReplaceButton(self, index, button):	# introduce a specialized button
    b = self.buttons[index]
    b.Destroy()
    self.buttons[index] = button
    if isinstance(button, WrapSlider):
      button.main_command = self.OnButton
    elif isinstance(button, WrapMenu):
      button.button.command = self.OnButton
    else:
      button.command = self.OnButton
  def SetLabel(self, label, do_cmd=False):
    self.button = None
    for b in self.buttons:
      if self.button is not None:
        b.SetValue(False)
      elif isinstance(b, QuiskCycleCheckbutton):
        try:
          index = b.labels.index(label)
        except ValueError:
          b.SetValue(False)
          continue
        else:
          b.SetIndex(index)
          self.button = b
          b.SetValue(True)
      elif b.GetLabel() == label:
        b.SetValue(True)
        self.button = b
      else:
        b.SetValue(False)
    if do_cmd and self.command and self.button:
      event = wx.PyEvent()
      event.SetEventObject(self.button)
      self.command(event)
  def GetButtons(self):
    return self.buttons
  def OnButton(self, event):
    win = event.GetEventObject()
    for b in self.buttons:
      if b is win or (isinstance(b, WrapControl) and b.button is win):
        self.button = b
        b.SetValue(True)
      else:
        b.SetValue(False)
    if self.command:
      self.command(event)
  def GetLabel(self):
    if not self.button:
      return None
    return self.button.GetLabel()
  def GetSelectedButton(self):		# return the selected button
    return self.button
  def GetIndex(self):	# Careful.  Some buttons are complex.
    if not self.button:
      return None
    return self.buttons.index(self.button)
  def Shortcut(self, event):
    # Multiple buttons can have the same shortcut, so move to the next one.
    index = self.last_shortcut + 1
    length = len(self.shortcuts)
    if index >= length:
      index = 0
    for i in range(length):
      shortcut = self.shortcuts[index]
      if shortcut and wx.GetKeyState(ord(shortcut)):
        break
      index += 1
      if index >= length:
        index = 0
    else:
      return
    self.last_shortcut = index
    button = self.buttons[index]
    event = wx.PyEvent()
    event.SetEventObject(button)
    button.OnButton(event)

class _PopWindow(wx.PopupWindow):
  def __init__(self, parent, command, labels, default):
    wx.PopupWindow.__init__(self, parent)
    self.panel = wx.Panel(self)
    self.panel.SetBackgroundColour(conf.color_popchoice)
    self.RbGroup = RadioButtonGroup(self.panel, command, labels, default)
    x = 5
    y = 5
    for b in self.RbGroup.buttons:
      b.SetPosition((x, y))
      w, h = b.GetTextExtent(b.GetLabel())
      width = w + 2 + 2 * b.bezelWidth + 4 * int(b.useFocusInd)
      height = h + 2 + 2 * b.bezelWidth + 4 * int(b.useFocusInd)
      b.SetInitialSize((width, height))
      x += width + 5
    self.SetSize((x, height + 2 * y))
    self.panel.SetSize((x, height + 2 * y))

class RadioBtnPopup:
  """This class contains a button that pops up a row of radio buttons"""
  def __init__(self, parent, command, in_labels, default):
    self.parent = parent
    self.pop_command = command
    self.button_data = {}
    labels = []
    for item in in_labels:
      if type(item) in (ListType, TupleType):
        labels.append(item[0])
        self.button_data[item[0]] = [_bitmap_cyclepop, 0, len(item)]	# bitmap, index, max_index
      else:
        labels.append(item)
    self.RbDialog = _PopWindow(parent, self.OnGroupButton, labels, default)
    self.RbDialog.Hide()
    self.pop_control = wx.BoxSizer(wx.HORIZONTAL)
    self.first_button = QuiskPushbutton(parent, self.OnFirstButton, labels[0], text_color=conf.color_popchoice)
    self.first_button.decoration = unichr(0x21D2)
    self.second_button = QuiskBitmapButton(parent, self.OnSecondButton, _bitmap_menupop, use_right=True)
    self.pop_control.Add(self.first_button, 1, flag=wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL)
    self.pop_control.Add(self.second_button, 0, flag=wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL|wx.LEFT, border=2)
    self.pop_control.Show(self.second_button, False)
    self.adjust = None
    self.first_button.index = 0
  def GetPopControl(self):
    return self.pop_control
  def AddMenu(self, label, menu):
    self.button_data[label] = (_bitmap_menupop, menu)
    return self
  def AddSlider(self, label, command, slider_value=0, slider_min=0, slider_max=1000, display=False, wintype=''):
    self.button_data[label] = [_bitmap_sliderpop, command, slider_value, slider_min, slider_max, display, wintype]
  def OnFirstButton(self, event):
    if self.adjust:		# Destroy any slider window
      self.adjust.Destroy()
      self.adjust = None
    if self.RbDialog.IsShown():
      self.RbDialog.Hide()
      return
    dw, dh = self.RbDialog.GetSize().Get()
    bw, bh = self.first_button.GetSize().Get()
    bx, by = self.first_button.ClientToScreen(wx.Point(0, 0))
    self.RbDialog.Position(wx.Point(bx + bw * 8 // 10, by + bh // 2 - dh), wx.Size(1, 1))
    self.RbDialog.Show()
    self.RbDialog.SetFocus()
  def AddSecondButton(self, label):
    data = self.button_data.get(label, None)
    if data is None:
      self.pop_control.Show(self.second_button, False)
    else:
      self.second_button.SetBitmapLabel(data[0])
      self.pop_control.Show(self.second_button, True)
      if data[0] == _bitmap_cyclepop:
        self.first_button.index = data[1]
    self.pop_control.Layout()
  def OnSecondButton(self, event):
    label = self.first_button.GetLabel()
    data = self.button_data.get(label, None)
    if data is None:
      pass
    elif data[0] == _bitmap_menupop:
      self.first_button.PopupMenu(data[1], (5, 5))
    elif data[0] == _bitmap_sliderpop:
      if self.adjust:
        self.adjust.Destroy()
        self.adjust = None
      else:
        bitm, self.command, slider_value, self.slider_min, self.slider_max, self.display, self.wintype = data
        self.adjust = QSliderButtonWindow(self, slider_value)
        self.second_data = data
    elif data[0] == _bitmap_cyclepop:
      if self.second_button.direction >= 0:
        data[1] += 1
        if data[1] >= data[2]:
          data[1] = 0
      else:
        data[1] -= 1
        if data[1] < 0:
          data[1] = data[2] - 1
      self.first_button.index = data[1]
      self.first_button.direction = self.second_button.direction
      if self.pop_command:
        event = wx.PyEvent()
        event.SetEventObject(self.first_button)
        self.pop_command(event)
      self.first_button.direction = 1
  def OnGroupButton(self, event):
    btn = event.GetEventObject()
    label = btn.GetLabel()
    self.first_button.SetLabel(label)
    self.first_button.Refresh()
    self.RbDialog.Hide()
    self.AddSecondButton(label)
    if self.pop_command:
      event = wx.PyEvent()
      event.SetEventObject(self.first_button)
      self.pop_command(event)
  def Enable(self, label, enable):
    for b in self.RbDialog.RbGroup.buttons:
      if b.GetLabel() == label:
        b.Enable(enable)
        break
  def GetLabel(self):
    return self.first_button.GetLabel()
  def SetLabel(self, label, do_cmd=False):
    self.first_button.SetLabel(label)
    self.AddSecondButton(label)
    self.RbDialog.RbGroup.SetLabel(label, False)
    if do_cmd and self.pop_command:
      event = wx.PyEvent()
      event.SetEventObject(self.first_button)
      self.pop_command(event)
  def Refresh(self):
    pass
  def ChangeSlider(self, slider_value):
    self.second_data[2] = slider_value
    command = self.second_data[1]
    if command:
      event = wx.PyEvent()
      self.first_button.slider_value = slider_value
      event.SetEventObject(self.first_button)
      command(event)
  def GetPositionTuple(self):
    return self.first_button.GetPosition().Get()
  def GetParent(self):
    return self.parent
  def GetSize(self):
    return self.first_button.GetSize()

class FreqSetter(wx.TextCtrl):
  def __init__(self, parent, x, y, label, fmin, fmax, freq, command):
    self.pos = (x, y)
    self.label = label
    self.fmin = fmin
    self.fmax = fmax
    self.command = command
    self.font = wx.Font(16, wx.FONTFAMILY_SWISS, wx.NORMAL, wx.FONTWEIGHT_NORMAL, False, conf.quisk_typeface)
    t = wx.StaticText(parent, -1, label, pos=(x, y))
    t.SetFont(self.font)
    freq_w, freq_h = t.GetTextExtent(" 662 000 000")
    tw, th = t.GetSize().Get()
    x += tw + 20
    wx.TextCtrl.__init__(self, parent, size=(freq_w, freq_h), pos=(x, y),
      style=wx.TE_RIGHT|wx.TE_PROCESS_ENTER)
    self.SetFont(self.font)
    self.Bind(wx.EVT_TEXT, self.OnText)
    self.Bind(wx.EVT_TEXT_ENTER, self.OnEnter)
    w, h = self.GetSize().Get()
    x += w + 1
    self.butn = b = wx.SpinButton(parent, size=(freq_h, freq_h), pos=(x, y))
    w, h = b.GetSize().Get()
    self.end_pos = (x + w, y + h)
    b.Bind(wx.EVT_SPIN, self.OnSpin)	# The spin button frequencies are in kHz
    b.SetMin(fmin // 1000)
    b.SetMax(fmax // 1000)
    self.SetValue(freq)
  def OnText(self, event):
    self.SetBackgroundColour('pink')
  def OnEnter(self, event):
    text = wx.TextCtrl.GetValue(self)
    text = text.replace(' ', '')
    if '-' in text:
      return
    try:
      if '.' in text:
        freq = int(float(text) * 1000000 + 0.5)
      else:
        freq = int(text)
    except:
      return
    self.SetValue(freq)
    self.command(self)
  def OnSpin(self, event):
    freq = self.butn.GetValue() * 1000
    self.SetValue(freq)
    self.command(self)
  def SetValue(self, freq):
    if freq < self.fmin:
      freq = self.fmin
    elif freq > self.fmax:
      freq = self.fmax
    self.butn.SetValue(freq // 1000)
    txt = FreqFormatter(freq)
    wx.TextCtrl.SetValue(self, txt)
    self.SetBackgroundColour(conf.color_entry)
  def GetValue(self):
    value = wx.TextCtrl.GetValue(self)
    value = value.replace(' ', '')
    try:
      value = int(value)
    except:
      value = 7000
    return value
