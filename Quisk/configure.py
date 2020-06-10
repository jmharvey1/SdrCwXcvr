
from __future__ import print_function

import sys, wx, wx.lib, wx.combo, os, re, pickle, traceback, json
from wx.lib.scrolledpanel import ScrolledPanel
from types import *
# Quisk will alter quisk_conf_defaults to include the user's config file.
import quisk_conf_defaults as conf
import _quisk as QS

# Settings is [
#   0: radio_requested, a string radio name or "Ask me" or "ConfigFileRadio"
#   1: radio in use and last used, a string radio name or "ConfigFileRadio"
#   2: list of radio names
#   3: parallel list of radio dicts.  These are all the parameters for the corresponding radio.  In
#      general, they are a subset of all the parameters listed in self.sections and self.receiver_data[radio_name].
#   ]

# radio_dict is a dictionary of variable names and text values for each radio including radio ConfigFileRadio.
# Only variable names from the specified radio and all sections are included.

# local_conf is the single instance of class Configuration


class Configuration:
  def __init__(self, app, AskMe):	# Called first
    global application, local_conf, Settings, noname_enable, platform_ignore, platform_accept
    Settings = ["ConfigFileRadio", "ConfigFileRadio", [], []]
    application = app
    local_conf = self
    noname_enable = []
    if sys.platform == 'win32':
      platform_ignore = 'lin_'
      platform_accept = 'win_'
    else:
      platform_accept = 'lin_'
      platform_ignore = 'win_'
    self.sections = []
    self.receiver_data = []
    self.StatePath = conf.settings_file_path
    if not self.StatePath:
      self.StatePath = os.path.join(conf.DefaultConfigDir, "quisk_settings.json")
    self.ReadState()
    if AskMe or Settings[0] == "Ask me":
      choices = Settings[2] + ["ConfigFileRadio"]
      dlg = wx.SingleChoiceDialog(None, "", "Start Quisk with this Radio",
          choices, style=wx.DEFAULT_FRAME_STYLE|wx.OK|wx.CANCEL)
      try:
        n = choices.index(Settings[1])		# Set default to last used radio
      except:
        pass
      else:
        dlg.SetSelection(n)
      ok = dlg.ShowModal()
      if ok != wx.ID_OK:
        sys.exit(0)
      select = dlg.GetStringSelection()
      dlg.Destroy()
      if Settings[1] != select:
        Settings[1] = select
        self.settings_changed = True
    else:
      Settings[1] = Settings[0]
    if Settings[1] == "ConfigFileRadio":
      Settings[2].append("ConfigFileRadio")
      Settings[3].append({})
    self.ParseConfig()
  def UpdateConf(self):		# Called second to update the configuration for the selected radio
    if Settings[1] == "ConfigFileRadio":
      return
    radio_dict = self.GetRadioDict()
    radio_type = radio_dict['hardware_file_type']
    # Fill in required values
    if radio_type == "SdrIQ":
      radio_dict["use_sdriq"] = '1'
    else:
      radio_dict["use_sdriq"] = '0'
    if radio_type not in ("HiQSDR", "Hermes", "Red Pitaya", "Odyssey"):
      radio_dict["use_rx_udp"] = '0'
    # fill in conf from our configuration data; convert text items to Python objects
    errors = ''
    for k, v in radio_dict.items():
      if k == 'favorites_file_path':	# A null string is equivalent to "not entered"
        if not v.strip():
          continue
      try:
        fmt = self.format4name[k]
      except:
        errors = errors + "Ignore obsolete parameter %s\n" % k
        del radio_dict[k]
        self.settings_changed = True
        continue
      k4 = k[0:4]
      if k4 == platform_ignore:
        continue
      elif k4 == platform_accept:
        k = k[4:]
      fmt4 = fmt[0:4]
      if fmt4 not in ('dict', 'list'):
        i1 = v.find('#')
        if i1 > 0:
          v = v[0:i1]
      try:
        if fmt4 == 'text':	# Note: JSON returns Unicode strings !!!
          setattr(conf, k, str(v))
        elif fmt4 in ('dict', 'list'):
          setattr(conf, k, v)
        elif fmt4 == 'inte':
          setattr(conf, k, int(v, base=0))
        elif fmt4 == 'numb':
          setattr(conf, k, float(v))
        elif fmt4 == 'bool':
          if v == "True":
            setattr(conf, k, True)
          else:
            setattr(conf, k, False)
        elif fmt4 == 'rfil':
          pass
        else:
          print ("Unknown format for", k, fmt)
      except:
        errors = errors + "Failed to set %s to %s using format %s\n" % (k, v, fmt)
        #traceback.print_exc()
    if conf.color_scheme == 'B':
      conf.__dict__.update(conf.color_scheme_B)
    elif conf.color_scheme == 'C':
      conf.__dict__.update(conf.color_scheme_C)
    if errors:
      dlg = wx.MessageDialog(None, errors,
        'Update Settings', wx.OK|wx.ICON_ERROR)
      ret = dlg.ShowModal()
      dlg.Destroy()
  def NormPath(self, path):	# Convert between Unix and Window file paths
    if sys.platform == 'win32':
      path = path.replace('/', '\\')
    else:
      path = path.replace('\\', '/')
    return path
  def GetHardware(self):	# Called third to open the hardware file
    if Settings[1] == "ConfigFileRadio":
      return False
    path = self.GetRadioDict()["hardware_file_name"]
    path = self.NormPath(path)
    if not os.path.isfile(path):
      dlg = wx.MessageDialog(None,
        "Failure for hardware file %s!" % path,
        'Hardware File', wx.OK|wx.ICON_ERROR)
      ret = dlg.ShowModal()
      dlg.Destroy()
      path = 'quisk_hardware_model.py'
    dct = {}
    dct.update(conf.__dict__)		# make items from conf available
    if dct.has_key("Hardware"):
      del dct["Hardware"]
    if dct.has_key('quisk_hardware'):
      del dct["quisk_hardware"]
    exec(compile(open(path).read(), path, 'exec'), dct)
    if dct.has_key("Hardware"):
      application.Hardware = dct['Hardware'](application, conf)
      return True
    return False
  def Initialize(self):		# Called fourth to fill in our ConfigFileRadio radio from conf
    if Settings[1] == "ConfigFileRadio":
      radio_dict = self.GetRadioDict("ConfigFileRadio")
      typ = self.GuessType()
      radio_dict['hardware_file_type'] = typ
      all_data = []
      all_data = all_data + self.GetReceiverData(typ)
      for name, sdata in self.sections:
        all_data = all_data + sdata
      for data_name, text, fmt, help_text, values in all_data:
        data_name4 = data_name[0:4]
        if data_name4 == platform_ignore:
          continue
        elif data_name4 == platform_accept:
          conf_name = data_name[4:]
        else:
          conf_name = data_name
        try:
          if fmt in ("dict", "list"):
            radio_dict[data_name] = getattr(conf, conf_name)
          else:
            radio_dict[data_name] = str(getattr(conf, conf_name))
        except:
          if data_name == 'playback_rate':
            pass
          else:
            print ('No config file value for', data_name)
 
  def GetWidgets(self, app, hardware, conf, frame, gbs, vertBox):	# Called fifth
    if Settings[1] == "ConfigFileRadio":
      return False
    path = self.GetRadioDict()["widgets_file_name"]
    path = self.NormPath(path)
    if os.path.isfile(path):
      dct = {}
      dct.update(conf.__dict__)		# make items from conf available
      exec(compile(open(path).read(), path, 'exec'), dct)
      if dct.has_key("BottomWidgets"):
        app.bottom_widgets = dct['BottomWidgets'](app, hardware, conf, frame, gbs, vertBox)
    return True
  def OnPageChanging(self, event):
    index = event.GetSelection()
    if index >= self.radios_page_start:
      page = self.notebk.GetPage(index)
      page.MakePages()
  def AddPages(self, notebk, width):	# Called sixth to add pages Help, Radios, all radio names
    global win_width
    win_width = width
    self.notebk = notebk
    page = ConfigHelp(notebk)
    notebk.AddPage(page, "Help with Radios")
    self.radio_page = Radios(notebk)
    notebk.AddPage(self.radio_page, "Radios")
    self.radios_page_start = notebk.GetPageCount()
    if sys.platform == 'win32':		# On Windows, PAGE_CHANGING doesn't work
      notebk.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.OnPageChanging)
    else:
      notebk.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGING, self.OnPageChanging)
    for name in Settings[2]:
      page = RadioNotebook(notebk, name)
      if name == Settings[1]:
        notebk.AddPage(page, "*%s*" % name)
      else:
        notebk.AddPage(page, name)
  def GuessType(self):
    udp = conf.use_rx_udp
    if conf.use_sdriq:
      return 'SdrIQ'
    elif udp == 1:
      return 'HiQSDR'
    elif udp == 2:
      return 'HiQSDR'
    elif udp == 10:
      return 'Hermes'
    elif udp > 0:
      return 'HiQSDR'
    return 'SoftRock USB'
  def AddRadio(self, radio_name, typ):
    radio_dict = {}
    radio_dict['hardware_file_type'] = typ
    Settings[2].append(radio_name)
    Settings[3].append(radio_dict)
    for data_name, text, fmt, help_text, values in self.GetReceiverData(typ):
      radio_dict[data_name] = values[0]
    for name, data in self.sections:
      for data_name, text, fmt, help_text, values in data:
        radio_dict[data_name] = values[0]
    page = RadioNotebook(self.notebk, radio_name)
    page.MakePages()
    self.notebk.AddPage(page, radio_name)
    return True
  def RenameRadio(self, old, new):
    index = Settings[2].index(old)
    n = self.radios_page_start + index
    if old == Settings[1]:
      self.notebk.SetPageText(n, "*%s*" % new)
    else:
      self.notebk.SetPageText(n, new)
    Settings[2][index] = new
    self.notebk.GetPage(n).NewName(new)
    if old == "ConfigFileRadio":
      for ctrl in noname_enable:
        ctrl.Enable()
    return True
  def DeleteRadio(self, name):
    index = Settings[2].index(name)
    n = self.radios_page_start + index
    self.notebk.DeletePage(n)
    del Settings[2][index]
    del Settings[3][index]
    return True
  def GetRadioDict(self, radio_name=None):	# None radio_name means the current radio
    if radio_name:
      index = Settings[2].index(radio_name)
    else:	# index of radio in use
      index = Settings[2].index(Settings[1])
    return Settings[3][index]
  def GetSectionData(self, section_name):
    for sname, data in self.sections:
      if sname == section_name:
        return data
    return None
  def GetReceiverData(self, receiver_name):
    for rxname, data in self.receiver_data:
      if rxname == receiver_name:
        return data
    return None
  def GetReceiverDatum(self, receiver_name, item_name):
    for rxname, data in self.receiver_data:
      if rxname == receiver_name:
        for data_name, text, fmt, help_text, values in data:
          if item_name == data_name:
            return values[0]
        break
    return ''
  def ReceiverHasName(self, receiver_name, item_name):
    for rxname, data in self.receiver_data:
      if rxname == receiver_name:
        for data_name, text, fmt, help_text, values in data:
          if item_name == data_name:
            return True
        break
    return False
  def ReadState(self):
    self.settings_changed = False
    global Settings
    try:
      fp = open(self.StatePath, "rb")
    except:
      return
    try:
      Settings = json.load(fp)
    except:
      traceback.print_exc()
    fp.close()
    try:	# Do not save settings for radio ConfigFileRadio
      index = Settings[2].index("ConfigFileRadio")
    except ValueError:
      pass
    else:
      del Settings[2][index]
      del Settings[3][index]
    for sdict in Settings[3]:		# Python None is saved as "null"
      if sdict.has_key("tx_level"):
        if sdict["tx_level"].has_key("null"):
          v = sdict["tx_level"]["null"]
          sdict["tx_level"][None] = v
          del sdict["tx_level"]["null"]
  def SaveState(self):
    if not self.settings_changed:
      return
    try:
      fp = open(self.StatePath, "wb")
    except:
      traceback.print_exc()
      return
    json.dump(Settings, fp, indent=2)
    fp.close()
    self.settings_changed = False
  def ParseConfig(self):
    # ParseConfig() fills self.sections, self.receiver_data, and
    # self.format4name with the items that Configuration understands.
    # Dicts and lists are Python objects.  All other items are text, not Python objects.
    #
    # Sections start with 16 #, section name
    # self.sections is a list of [section_name, section_data]
    # section_data is a list of [data_name, text, fmt, help_text, values]

    # Receiver sections start with 16 #, "Receivers ", receiver name, explain
    # self.receiver_data is a list of [receiver_name, receiver_data]
    # receiver_data is a list of [data_name, text, fmt, help_text, values]

    # Variable names start with ## variable_name   variable_text, format
    #     The format is integer, number, text, boolean, integer choice, text choice, rfile
    #     Then some help text starting with "# "
    #     Then a list of possible value#explain with the default first
    #     Then a blank line to end.

    self.format4name = {}
    self.format4name['hardware_file_type'] = 'text'
    re_AeqB = re.compile("^#?(\w+)\s*=\s*([^#]+)#*(.*)")		# item values "a = b"
    section = None
    data_name = None
    fp = open("quisk_conf_defaults.py", "rb")
    for line in fp:
      line = line.strip()
      if not line:
        data_name = None
        continue
      if line[0:27] == '################ Receivers ':
        section = 'Receivers'
        args = line[27:].split(',', 1)
        rxname = args[0].strip()
        section_data = []
        self.receiver_data.append((rxname, section_data))
      elif line[0:17] == '################ ':
        args = line[17:].split(None, 2)
        section = args[0]
        if section in ('Keys', 'Colors', 'Obsolete'):
          section = None
          continue
        rxname = None
        section_data = []
        self.sections.append((section, section_data))
      if not section:
        continue
      if line[0:3] == '## ':		# item_name   item_text, format
        args = line[3:].split(None, 1)
        data_name = args[0]
        args = args[1].split(',', 1)
        dspl = args[0].strip()
        fmt = args[1].strip()
        value_list = []
        if self.format4name.has_key(data_name):
          if self.format4name[data_name] != fmt:
            print ("Inconsistent format for", data_name, self.format4name[data_name], fmt)
        else:
          self.format4name[data_name] = fmt
        section_data.append([data_name, dspl, fmt, '', value_list])
      if not data_name:
        continue
      mo = re_AeqB.match(line)
      if mo:
        if data_name != mo.group(1):
          print ("Parse error for", data_name)
          continue
        value = mo.group(2).strip()
        expln = mo.group(3).strip()
        if value[0] in ('"', "'"):
          value = value[1:-1]
        elif value == '{':		# item is a dictionary
          value = getattr(conf, data_name)
        elif value == '[':		# item is a list
          value = getattr(conf, data_name)
        if expln:
          value_list.append("%s # %s" % (value, expln))
        else:
          value_list.append(value)
      elif line[0:2] == '# ':
        section_data[-1][3] = section_data[-1][3] + line[2:] + ' '
    fp.close()

class ConfigHelp(wx.html.HtmlWindow):	# The "Help with Radios" first-level page
  """Create the help screen for the configuration tabs."""
  def __init__(self, parent):
    wx.html.HtmlWindow.__init__(self, parent, -1, size=(win_width, 100))
    if "gtk2" in wx.PlatformInfo:
      self.SetStandardFonts()
    self.SetFonts("", "", [10, 12, 14, 16, 18, 20, 22])
    # read in text from file help_conf.html in the directory of this module
    self.LoadFile('help_conf.html')

class RadioNotebook(wx.Notebook):	# The second-level notebook for each radio name
  def __init__(self, parent, radio_name):
    wx.Notebook.__init__(self, parent)
    font = wx.Font(conf.config_font_size, wx.FONTFAMILY_SWISS, wx.NORMAL,
          wx.FONTWEIGHT_NORMAL, face=conf.quisk_typeface)
    self.SetFont(font)
    self.radio_name = radio_name
    self.pages = []
  def MakePages(self):
    if self.pages:
      return
    radio_name = self.radio_name
    page = RadioHardware(self, radio_name)
    self.AddPage(page, "Hardware")
    self.pages.append(page)
    page = RadioSound(self, radio_name)
    self.AddPage(page, "Sound")
    self.pages.append(page)
    for section, names in local_conf.sections:
      if section in ('Sound', 'Bands'):		# There is a special page for these sections
        continue
      page = RadioSection(self, radio_name, section, names)
      self.AddPage(page, section)
      self.pages.append(page)
    page = RadioBands(self, radio_name)
    self.AddPage(page, "Bands")
    self.pages.append(page)
  def NewName(self, new_name):
    self.radio_name = new_name
    for page in self.pages:
      page.radio_name = new_name

class ComboCtrl(wx.combo.ComboCtrl):
  def __init__(self, parent, value, choices, no_edit=False):
    self.value = value
    self.choices = choices[:]
    self.handler = None
    self.height = parent.quisk_height
    if no_edit:
      wx.combo.ComboCtrl.__init__(self, parent, -1, style=wx.CB_READONLY)
    else:
      wx.combo.ComboCtrl.__init__(self, parent, -1, style=wx.TE_PROCESS_ENTER)
      self.GetTextCtrl().Bind(wx.EVT_KILL_FOCUS, self.OnKillFocus)
      self.Bind(wx.EVT_TEXT_ENTER, self.OnTextEnter)
    self.ctrl = ListBoxComboPopup(choices, parent.font)
    self.SetPopupControl(self.ctrl)
    self.SetText(value)
    self.SetSizes()
  def SetItems(self, lst):
    self.ctrl.SetItems(lst)
    self.choices = lst[:]
    self.SetSizes()
  def SetSizes(self):
    charx = self.GetCharWidth()
    wm = charx
    w, h = self.GetTextExtent(self.value)
    if wm < w:
      wm = w
    for ch in self.choices:
      w, h = self.GetTextExtent(ch)
      if wm < w:
        wm = w
    wm += charx * 5
    self.SetSizeHints(wm, self.height, 9999, self.height)
  def SetSelection(self, n):
    try:
      text = self.choices[n]
    except IndexError:
      self.SetText('')
      self.value = ''
    else:
      self.ctrl.SetSelection(n)
      self.SetText(text)
      self.value = text
  def OnTextEnter(self, event=None):
    if event:
      event.Skip()
    if self.value != self.GetValue():
      self.value = self.GetValue()
      if self.handler:
        ok = self.handler(self)
  def OnKillFocus(self, event):
    event.Skip()
    self.OnTextEnter(event)
  def OnListbox(self):
    self.OnTextEnter()

class ListBoxComboPopup(wx.ListBox, wx.combo.ComboPopup):
  def __init__(self, choices, font):
    wx.combo.ComboPopup.__init__(self)
    self.choices = choices
    self.font = font
    self.lbox = None
  def Create(self, parent):
    self.lbox = wx.ListBox(parent, choices=self.choices, style=wx.LB_SINGLE)
    self.lbox.SetFont(self.font)
    self.lbox.Bind(wx.EVT_MOTION, self.OnMotion)
    self.lbox.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
    return True
  def SetItems(self, lst):
    self.choices = lst[:]
    self.lbox.Set(self.choices)
  def SetSelection(self, n):
    self.lbox.SetSelection(n)
  def GetStringValue(self):
    try:
      return self.choices[self.lbox.GetSelection()]
    except IndexError:
      pass
    return ''
  def GetAdjustedSize(self, minWidth, prefHeight, maxHeight):
    chary = self.lbox.GetCharHeight()
    return (minWidth, chary * len(self.choices) * 15 / 10 + chary)
  def OnLeftDown(self, event):
    event.Skip()
    self.Dismiss()
    self.GetCombo().OnListbox()
  def OnMotion(self, event):
    event.Skip()
    item = self.lbox.HitTest(event.GetPosition())
    if item >= 0:
      self.lbox.SetSelection(item)
  def GetControl(self):
    return self.lbox

class BaseWindow(ScrolledPanel):
  def __init__(self, parent):
    ScrolledPanel.__init__(self, parent)
    self.font = wx.Font(conf.config_font_size, wx.FONTFAMILY_SWISS, wx.NORMAL,
          wx.FONTWEIGHT_NORMAL, face=conf.quisk_typeface)
    self.SetFont(self.font)
    self.row = 1
    self.charx = self.GetCharWidth()
    self.chary = self.GetCharHeight()
    self.quisk_height = self.chary * 14 / 10
    # GBS
    self.gbs = wx.GridBagSizer(2, 2)
    self.gbs.SetEmptyCellSize((self.charx, self.charx))
    self.SetSizer(self.gbs)
    self.gbs.Add((self.charx, self.charx), (0, 0))
  def MarkCols(self):
    for col in range(1, self.num_cols):
      c = wx.StaticText(self, -1, str(col % 10))
      self.gbs.Add(c, (self.row, col))
    self.row += 1
  def NextRow(self, row=None):
    if row is None:
      self.row += 1
    else:
      self.row = row
  def AddTextL(self, col, text, span=None):
    c = wx.StaticText(self, -1, text)
    if col < 0:
      pass
    elif span is None:
      self.gbs.Add(c, (self.row, col), flag=wx.ALIGN_CENTER_VERTICAL)
    else:
      self.gbs.Add(c, (self.row, col), span=(1, span), flag=wx.ALIGN_CENTER_VERTICAL)
    return c
  def AddTextCHelp(self, col, text, help_text, span=None):
    bsizer = wx.BoxSizer(wx.HORIZONTAL)
    txt = wx.StaticText(self, -1, text)
    bsizer.Add(txt, flag=wx.ALIGN_CENTER_VERTICAL)
    btn = wx.Button(self, -1, "..")
    btn.quisk_help_text = help_text
    btn.quisk_caption = text
    h = self.quisk_height + 2
    btn.SetSizeHints(h, h, h, h)
    btn.Bind(wx.EVT_BUTTON, self._BTnHelp)
    bsizer.Add(btn, flag=wx.ALIGN_CENTER_VERTICAL|wx.LEFT, border=self.charx)
    if col < 0:
      pass
    elif span is None:
      self.gbs.Add(bsizer, (self.row, col), flag = wx.ALIGN_CENTER)
    else:
      self.gbs.Add(bsizer, (self.row, col), span=(1, span), flag = wx.ALIGN_CENTER)
    return bsizer
  def AddBoxSizer(self, col, span):
    bsizer = wx.BoxSizer(wx.HORIZONTAL)
    self.gbs.Add(bsizer, (self.row, col), span=(1, span))
    return bsizer
  def AddColSpacer(self, col, width):		# add a width spacer to row 0
    self.gbs.Add((width * self.charx, 1), (0, col))		# width is in characters
  def AddRadioButton(self, col, text, span=None, start=False):
    if start:
      c = wx.RadioButton(self, -1, text, style=wx.RB_GROUP)
    else:
      c = wx.RadioButton(self, -1, text)
    if col < 0:
      pass
    elif span is None:
      self.gbs.Add(c, (self.row, col), flag=wx.ALIGN_CENTER_VERTICAL)
    else:
      self.gbs.Add(c, (self.row, col), span=(1, span), flag=wx.ALIGN_CENTER_VERTICAL)
    return c
  def AddCheckBox(self, col, text, handler=None):
    btn = wx.CheckBox(self, -1, text)
    h = self.quisk_height + 2
    btn.SetSizeHints(-1, h, -1, h)
    if col >= 0:
      self.gbs.Add(btn, (self.row, col))
    if self.radio_name == "ConfigFileRadio":
      btn.Enable(False)
      noname_enable.append(btn)
    if handler:
      btn.Bind(wx.EVT_CHECKBOX, handler)
    return btn
  def AddPushButton(self, col, text, border=0):
    #btn = wx.Button(self, -1, text, style=wx.BU_EXACTFIT)
    btn = wx.lib.buttons.GenButton(self, -1, text)
    btn.SetBezelWidth(2)
    btn.SetUseFocusIndicator(False)
    h = self.quisk_height + 2
    btn.SetSizeHints(-1, h, -1, h)
    if col >= 0:
      self.gbs.Add(btn, (self.row, col), flag=wx.RIGHT|wx.LEFT, border=border*self.charx)
    if self.radio_name == "ConfigFileRadio":
      btn.Enable(False)
      noname_enable.append(btn)
    return btn
  def AddPushButtonR(self, col, text, border=0):
    btn = self.AddPushButton(-1, text, border=0)
    if col >= 0:
      self.gbs.Add(btn, (self.row, col), flag=wx.ALIGN_RIGHT|wx.RIGHT|wx.LEFT, border=border*self.charx)
    return btn
  def AddComboCtrl(self, col, value, choices, right=False, no_edit=False, span=None, border=1):
    cb = ComboCtrl(self, value, choices, no_edit)
    if col < 0:
      pass
    elif span is None:
      self.gbs.Add(cb, (self.row, col), flag=wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL|wx.EXPAND|wx.RIGHT|wx.LEFT, border=border*self.charx)
    else:
      self.gbs.Add(cb, (self.row, col), span=(1, span), flag=wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL|wx.EXPAND|wx.RIGHT|wx.LEFT, border=border*self.charx)
    if self.radio_name == "ConfigFileRadio":
      cb.Enable(False)
      noname_enable.append(cb)
    return cb
  def AddComboCtrlTx(self, col, text, value, choices, right=False, no_edit=False):
    c = wx.StaticText(self, -1, text)
    if col >= 0:
      self.gbs.Add(c, (self.row, col))
      cb = self.AddComboCtrl(col + 1, value, choices, right, no_edit)
    else:
      cb = self.AddComboCtrl(col, value, choices, right, no_edit)
    return c, cb
  def AddTextComboHelp(self, col, text, value, choices, help_text, no_edit=False, border=2, span_text=1, span_combo=1):
    txt = wx.StaticText(self, -1, text)
    self.gbs.Add(txt, (self.row, col), span=(1, span_text), flag=wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, border=self.charx)
    col += span_text
    cb = self.AddComboCtrl(-1, value, choices, False, no_edit)
    if no_edit:
      l = len(value)
      for i in range(len(choices)):
        if value == choices[i][0:l]:
          cb.SetSelection(i)
          break
      else:
        print ("Failure to set value for", text, value, choices)
    self.gbs.Add(cb, (self.row, col), span=(1, span_combo),
       flag=wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL|wx.EXPAND|wx.RIGHT,
       border=self.charx*2/10)
    col += span_combo
    btn = wx.Button(self, -1, "..")
    btn.quisk_help_text = help_text
    btn.quisk_caption = text
    h = self.quisk_height + 2
    btn.SetSizeHints(h, h, h, h)
    self.gbs.Add(btn, (self.row, col), flag=wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, border=self.charx*border)
    btn.Bind(wx.EVT_BUTTON, self._BTnHelp)
    return txt, cb, btn
  def _BTnHelp(self, event):
    btn = event.GetEventObject()
    dlg = wx.MessageDialog(self, btn.quisk_help_text, btn.quisk_caption, style=wx.OK|wx.ICON_INFORMATION)
    dlg.ShowModal()
    dlg.Destroy()
  def OnChange(self, ctrl):
    value = ctrl.GetValue()
    self.OnChange2(ctrl, value)
  def OnChange2(self, ctrl, value):
    name = ctrl.quisk_data_name
    fmt4 = local_conf.format4name[name][0:4]
    if self.FormatOK(value, fmt4):
      radio_dict = local_conf.GetRadioDict(self.radio_name)
      radio_dict[name] = value
      local_conf.settings_changed = True
  def FormatOK(self, value, fmt4):		# Check formats integer and number
    i1 = value.find('#')
    try:
      if fmt4 == 'inte':
        if i1 > 0:
          v = int(value[0:i1], base=0)
        else:
          v = int(value, base=0)
      elif fmt4 == 'numb':
        if i1 > 0:
          v = float(value[0:i1])
        else:
          v = float(value)
    except:
      dlg = wx.MessageDialog(None,
        "Can not set item with format %s to value %s" % (fmt4, value),
        'Change to item', wx.OK|wx.ICON_ERROR)
      dlg.ShowModal()
      dlg.Destroy()
      return False
    else:
      return True
  def GetValue(self, name, radio_dict):
    try:
      value = radio_dict[name]
    except:
      pass
    else:
      return value
    # Value was not in radio_dict.  Get it from conf.  There are values for platform win_data_name and lin_data_name.
    # The win_ and lin_ names are not in conf.
    try:
      fmt = local_conf.format4name[name]
    except:
      fmt = ''		# not all items in conf are in section_data or receiver_data
    try:
      if fmt == 'dict':				# make a copy for this radio
        value = {}
        value.update(getattr(conf, name))
      elif fmt == 'list':			# make a copy for this radio
        value = getattr(conf, name)[:]
      else:
        value = str(getattr(conf, name))
    except:
      return ''
    else:
      return value

class Radios(BaseWindow):	# The "Radios" first-level page
  def __init__(self, parent):
    BaseWindow.__init__(self, parent)
    self.num_cols = 8
    self.radio_name = None
    self.cur_radio_text = self.AddTextL(1, 'xx', self.num_cols - 1)
    self.SetCurrentRadioText()
    self.NextRow()
    self.NextRow()
    item = self.AddTextL(1, "When Quisk starts, use the radio")
    self.start_radio = self.AddComboCtrl(2, 'big_radio_name', choices=[], no_edit=True)
    self.start_radio.handler = self.OnChoiceStartup
    self.NextRow()
    item = self.AddTextL(1, "Add a new radio with the general type")
    choices = []
    for name, data in local_conf.receiver_data:
      choices.append(name)
    self.add_type = self.AddComboCtrl(2, '', choices=choices, no_edit=True)
    self.add_type.SetSelection(0)
    item = self.AddTextL(3, "and name the new radio")
    self.add_name = self.AddComboCtrl(4, '', choices=["My Radio", "SR with XVtr", "SoftRock"])
    item = self.AddPushButton(5, "Add")
    self.Bind(wx.EVT_BUTTON, self.OnBtnAdd, item)
    self.NextRow()
    item = self.AddTextL(1, "Rename the radio named")
    self.rename_old = self.AddComboCtrl(2, 'big_radio_name', choices=[], no_edit=True)
    item = self.AddTextL(3, "to the new name")
    self.rename_new = self.AddComboCtrl(4, '', choices=["My Radio", "SR with XVtr", "SoftRock"])
    item = self.AddPushButton(5, "Rename")
    self.Bind(wx.EVT_BUTTON, self.OnBtnRename, item)
    self.NextRow()
    item = self.AddTextL(1, "Delete the radio named")
    self.delete_name = self.AddComboCtrl(2, 'big_radio_name', choices=[], no_edit=True)
    item = self.AddPushButton(3, "Delete")
    self.Bind(wx.EVT_BUTTON, self.OnBtnDelete, item)
    self.NextRow()
    item = self.AddTextL(1, "Restart Quisk with new settings")
    item = self.AddPushButton(2, "Restart Quisk", 1)
    self.Bind(wx.EVT_BUTTON, self.OnBtnRestart, item)
    if application.pulse_in_use:
      pass #item.Enable(False)	# Pulse requires a program exit to clean up
    self.NextRow()
    self.Fit()
    self.SetupScrolling()
    self.NewRadioNames()
  def SetCurrentRadioText(self):
    radio_dict = local_conf.GetRadioDict(self.radio_name)
    radio_type = radio_dict['hardware_file_type']
    if Settings[1] == "ConfigFileRadio":
      text = 'The current radio is ConfigFileRadio, so all settings come from the config file.  The hardware type is %s.' % radio_type
    else:
      text = "Quisk is running with settings from the radio %s.  The hardware type is %s." % (Settings[1], radio_type)
    self.cur_radio_text.SetLabel(text)
  def DuplicateName(self, name):
    if name in Settings[2] or name == "ConfigFileRadio":
      dlg = wx.MessageDialog(self, "The name already exists.  Please choose a different name.",
          'Quisk', wx.OK)
      dlg.ShowModal()
      dlg.Destroy()
      return True
    return False
  def OnBtnAdd(self, event):
    name = self.add_name.GetValue().strip()
    if not name or self.DuplicateName(name):
      return
    self.add_name.SetValue('')
    typ = self.add_type.GetValue().strip()
    if local_conf.AddRadio(name, typ):
      if Settings[0] != "Ask me":
        Settings[0] = name
      self.NewRadioNames()
      local_conf.settings_changed = True
  def OnBtnRename(self, event):
    old = self.rename_old.GetValue()
    new = self.rename_new.GetValue().strip()
    if not old or not new or self.DuplicateName(new):
      return
    self.rename_new.SetValue('')
    if local_conf.RenameRadio(old, new):
      if old == 'ConfigFileRadio' and Settings[1] == "ConfigFileRadio":
        Settings[1] = new
      elif Settings[1] == old:
        Settings[1] = new
      self.SetCurrentRadioText()
      if Settings[0] != "Ask me":
        Settings[0] = new
      self.NewRadioNames()
      local_conf.settings_changed = True
  def OnBtnDelete(self, event):
    name = self.delete_name.GetValue()
    if not name:
      return
    dlg = wx.MessageDialog(self,
        "Are you sure you want to permanently delete the radio %s?" % name,
        'Quisk', wx.OK|wx.CANCEL|wx.ICON_EXCLAMATION)
    ret = dlg.ShowModal()
    dlg.Destroy()
    if ret == wx.ID_OK and local_conf.DeleteRadio(name):
      self.NewRadioNames()
      local_conf.settings_changed = True
  def OnChoiceStartup(self, ctrl):
    choice = self.start_radio.GetValue()
    if Settings[0] != choice:
      Settings[0] = choice
      local_conf.settings_changed = True
  def NewRadioNames(self):		# Correct all choice lists for changed radio names
    choices = Settings[2][:]			# can rename any available radio
    self.rename_old.SetItems(choices)
    self.rename_old.SetSelection(0)
    if "ConfigFileRadio" in choices:
      choices.remove("ConfigFileRadio")
    if Settings[1] in choices:
      choices.remove(Settings[1])
    self.delete_name.SetItems(choices)	# can not delete ConfigFileRadio nor the current radio
    self.delete_name.SetSelection(0)
    choices = Settings[2] + ["Ask me"]
    if "ConfigFileRadio" not in choices:
      choices.append("ConfigFileRadio")
    self.start_radio.SetItems(choices)	# can start any radio, plus "Ask me" and "ConfigFileRadio"
    try:	# Set text in control
      index = choices.index(Settings[0])	# last used radio, or new or renamed radio
    except:
      num = len(Settings[2])
      if len == 0:
        index = 1
      elif num == 1:
        index = 0
      else:
        index = len(choices) - 2
      Settings[0] = choices[index]
    self.start_radio.SetSelection(index)
  def OnBtnRestart(self, event):
    application.startup_quisk = True
    application.main_frame.OnBtnClose(event)

class RadioSection(BaseWindow):		# The pages for each section in the second-level notebook for each radio
  def __init__(self, parent, radio_name, section, names):
    BaseWindow.__init__(self, parent)
    self.radio_name = radio_name
    self.names = names
    self.num_cols = 8
    #self.MarkCols()
    self.NextRow(3)
    col = 1
    radio_dict = local_conf.GetRadioDict(radio_name)
    for name, text, fmt, help_text, values in self.names:
      if name == 'favorites_file_path':
        self.favorites_path = radio_dict.get('favorites_file_path', '')
        row = self.row
        self.row = 1
        item, self.favorites_combo, btn = self.AddTextComboHelp(1, text, self.favorites_path, values, help_text, False, span_text=1, span_combo=4)
        self.favorites_combo.handler = self.OnButtonChangeFavorites
        item = self.AddPushButtonR(7, "Change..", border=0)
        item.Bind(wx.EVT_BUTTON, self.OnButtonChangeFavorites)
        self.row = row
      else:
        if fmt[0:4] in ('dict', 'list'):
          continue
        if name[0:4] == platform_ignore:
          continue
        value = self.GetValue(name, radio_dict)
        no_edit = "choice" in fmt or fmt == 'boolean'
        txt, cb, btn = self.AddTextComboHelp(col, text, value, values, help_text, no_edit)
        cb.handler = self.OnChange
        cb.quisk_data_name = name
        if col == 1:
          col = 4
        else:
          col = 1
          self.NextRow()
    self.AddColSpacer(2, 20)
    self.AddColSpacer(5, 20)
    self.Fit()
    self.SetupScrolling()
  def OnButtonChangeFavorites(self, event):
    if isinstance(event, ComboCtrl):
      path = event.GetValue()
    else:
      direc, fname = os.path.split(getattr(conf, 'favorites_file_in_use'))
      dlg = wx.FileDialog(None, "Choose Favorites File", direc, fname, "*.txt", wx.OPEN)
      if dlg.ShowModal() == wx.ID_OK:
        path = dlg.GetPath()
        self.favorites_combo.SetText(path)
        dlg.Destroy()
      else:
        dlg.Destroy()
        return
    path = path.strip()
    self.favorites_path = path
    local_conf.GetRadioDict(self.radio_name)["favorites_file_path"] = path
    local_conf.settings_changed = True

class RadioHardware(BaseWindow):		# The Hardware page in the second-level notebook for each radio
  def __init__(self, parent, radio_name):
    BaseWindow.__init__(self, parent)
    self.radio_name = radio_name
    self.num_cols = 8
    #self.MarkCols()
    radio_dict = local_conf.GetRadioDict(radio_name)
    radio_type = radio_dict['hardware_file_type']
    data_names = local_conf.GetReceiverData(radio_type)
    bsizer = self.AddBoxSizer(1, self.num_cols - 1)
    item = self.AddTextL(-1, "These are the hardware settings for a radio of type %s" % radio_type, self.num_cols-1)
    bsizer.Add(item)
    self.NextRow(7)
    col = 1
    border = 2
    for name, text, fmt, help_text, values in data_names:
      if name == 'hardware_file_name':
        self.hware_path = self.GetValue(name, radio_dict)
        row = self.row
        self.row = 3
        item, self.hware_combo, btn = self.AddTextComboHelp(1, text, self.hware_path, values, help_text, False, span_text=1, span_combo=4)
        self.hware_combo.handler = self.OnButtonChangeHardware
        item = self.AddPushButtonR(7, "Change..", border=0)
        item.Bind(wx.EVT_BUTTON, self.OnButtonChangeHardware)
        self.row = row
      elif name == 'widgets_file_name':
        self.widgets_path = self.GetValue(name, radio_dict)
        row = self.row
        self.row = 5
        item, self.widgets_combo, btn = self.AddTextComboHelp(1, text, self.widgets_path, values, help_text, False, span_text=1, span_combo=4)
        self.widgets_combo.handler = self.OnButtonChangeWidgets
        item = self.AddPushButtonR(7, "Change..", border=0)
        item.Bind(wx.EVT_BUTTON, self.OnButtonChangeWidgets)
        self.row = row
      elif fmt[0:4] in ('dict', 'list'):
        pass
      elif name[0:4] == platform_ignore:
        pass
      else:
        value = self.GetValue(name, radio_dict)
        no_edit = "choice" in fmt or fmt == 'boolean'
        txt, cb, btn = self.AddTextComboHelp(col, text, value, values, help_text, no_edit, border=border)
        cb.handler = self.OnChange
        cb.quisk_data_name = name
        if col == 1:
          col = 4
          border = 0
        else:
          col = 1
          border = 2
          self.NextRow()
    self.AddColSpacer(2, 20)
    self.AddColSpacer(5, 20)
    self.Fit()
    self.SetupScrolling()
  def OnButtonChangeHardware(self, event):
    if isinstance(event, ComboCtrl):
      path = event.GetValue()
    else:
      direc, fname = os.path.split(self.hware_path)
      dlg = wx.FileDialog(None, "Choose Hardware File", direc, fname, "*.py", wx.OPEN)
      if dlg.ShowModal() == wx.ID_OK:
        path = dlg.GetPath()
        self.hware_combo.SetText(path)
        dlg.Destroy()
      else:
        dlg.Destroy()
        return
    path = path.strip()
    self.hware_path = path
    local_conf.GetRadioDict(self.radio_name)["hardware_file_name"] = path
    local_conf.settings_changed = True
  def OnButtonChangeWidgets(self, event):
    if isinstance(event, ComboCtrl):
      path = event.GetValue()
    else:
      direc, fname = os.path.split(self.widgets_path)
      dlg = wx.FileDialog(None, "Choose Widgets File", direc, fname, "*.py", wx.OPEN)
      if dlg.ShowModal() == wx.ID_OK:
        path = dlg.GetPath()
        self.widgets_combo.SetText(path)
        dlg.Destroy()
      else:
        dlg.Destroy()
        return
    path = path.strip()
    self.widgets_path = path
    local_conf.GetRadioDict(self.radio_name)["widgets_file_name"] = path
    local_conf.settings_changed = True

class RadioSound(BaseWindow):		# The Sound page in the second-level notebook for each radio
  """Configure the available sound devices."""
  sound_names = (		# same order as grid labels
    ('playback_rate', '', '', '', 'name_of_sound_play'),
    ('mic_sample_rate', 'mic_channel_I', 'mic_channel_Q', '', 'microphone_name'),
    ('sample_rate', 'channel_i', 'channel_q', 'channel_delay', 'name_of_sound_capt'),
    ('mic_playback_rate', 'mic_play_chan_I', 'mic_play_chan_Q', 'tx_channel_delay', 'name_of_mic_play'),
    ('', '', '', '', 'digital_input_name'),
    ('', '', '', '', 'digital_output_name'),
    ('', '', '', '', 'sample_playback_name'),
    ('', '', '', '', 'digital_rx1_name'),
    )
  def __init__(self, parent, radio_name):
    BaseWindow.__init__(self, parent)
    self.radio_name = radio_name
    self.radio_dict = local_conf.GetRadioDict(self.radio_name)
    self.num_cols = 8
    thename = platform_accept + "latency_millisecs"
    for name, text, fmt, help_text, values in local_conf.GetSectionData('Sound'):
      if name == thename:
        value = self.GetValue(name, self.radio_dict)
        no_edit = "choice" in fmt or fmt == 'boolean'
        txt, cb, btn = self.AddTextComboHelp(1, text, value, values, help_text, no_edit)
        cb.handler = self.OnChange
        cb.quisk_data_name = name
        break
    self.NextRow()
    # Add the grid for the sound settings
    sizer = wx.GridBagSizer(2, 2)
    sizer.SetEmptyCellSize((self.charx, self.charx))
    self.gbs.Add(sizer, (self.row, 0), span=(1, self.num_cols))
    gbs = self.gbs
    self.gbs = sizer
    self.row = 1
    dev_capt, dev_play = QS.sound_devices()
    if sys.platform != 'win32':
      for i in range(len(dev_capt)):
        dev_capt[i] = "alsa:" + dev_capt[i]
      for i in range(len(dev_play)):
        dev_play[i] = "alsa:" + dev_play[i]
      show = self.GetValue('show_pulse_audio_devices', self.radio_dict)
      if show == 'True':
        dev_capt.append("pulse # Use the default pulse device")
        dev_play.append("pulse # Use the default pulse device")
        for n0, n1, n2 in application.pa_dev_capt:
          dev_capt.append("pulse:%s" % n0)
        for n0, n1, n2 in application.pa_dev_play:
          dev_play.append("pulse:%s" % n0)
    dev_capt.insert(0, '')
    dev_play.insert(0, '')
    self.AddTextCHelp(1, "Stream",
"Quisk uses a number of sound devices for both audio and digital data.  "
"Radio audio output is the sound going to the headphones or speakers.  "
"Microphone input is the monophonic microphone source.  Set the channel if the source is stereo.  "
"I/Q sample input is the sample source if it comes from a sound device, such as a SoftRock.  Otherwise, leave it blank.  "
"I/Q Tx output is the transmit sample source from a SoftRock.  Otherwise leave it blank.  "
"Digital input is the loopback sound device attached to a digital program such as FlDigi.  "
"Digital output is the loopback sound device to send Tx samples to a digital program such as FlDigi.  "
"I/Q sample output sends the received I/Q data to another program.  "
"Digital Rx1 Output is the loopback sound device to send sub-receiver 1 output to another program.")
    self.AddTextCHelp(2, "Rate",
"This is the sample rate for the device in Hertz." "Some devices have fixed rates that can not be changed.")
    self.AddTextCHelp(3, "Ch I", "This is the in-phase channel for devices with I/Q data, and the main channel for other devices.")
    self.AddTextCHelp(4, "Ch Q", "This is the quadrature channel for devices with I/Q data, and the second channel for other devices.")
    self.AddTextCHelp(5, "Delay", "Some older devices have a one sample channel delay between channels.  "
"This must be corrected for devices with I/Q data.  Enter the channel number to delay; either the I or Q channel number.  "
"For no delay, leave this blank.")
    self.AddTextCHelp(6, "Sound Device", "This is the name of the sound device.  For Windows, this is the DirectX name.  "
"For Linux you can use the Alsa device, the PortAudio device or the PulseAudio device.  "
"The Alsa device are recommended because they have lower latency.  See the documentation for more information.")
    self.NextRow()
    labels = ("Radio Audio Output", "Microphone Input", "I/Q Sample Input", "I/Q Tx Output", "Digital Input", "Digital Output", "I/Q Sample Output", "Digital Rx1 Output")
    choices = (("48000", "96000", "192000"), ("0", "1"), ("0", "1"), (" ", "0", "1"))
    r = 0
    if "SoftRock" in self.radio_dict['hardware_file_type']:		# Samples come from sound card
      softrock = True
    else:
      softrock = False
    for label in labels:
      self.AddTextL(1, label)
      # Add col 0
      value = self.ItemValue(r, 0)
      if value is None:
        value = ''
      data_name = self.sound_names[r][0]
      if r == 0:
        cb = self.AddComboCtrl(2, value, choices=("48000", "96000", "192000"), right=True)
      if r == 1:
        cb = self.AddComboCtrl(2, value, choices=("48000", "8000"), right=True, no_edit=True)
      if softrock:
        if r == 2:
          cb = self.AddComboCtrl(2, value, choices=("48000", "96000", "192000"), right=True)
        if r == 3:
          cb = self.AddComboCtrl(2, value, choices=("48000", "96000", "192000"), right=True)
      else:
        if r == 2:
          cb = self.AddComboCtrl(2, '', choices=("",), right=True)
          cb.Enable(False)
        if r == 3:
          cb = self.AddComboCtrl(2, '', choices=("",), right=True)
          cb.Enable(False)
      if r == 4:
        cb = self.AddComboCtrl(2, "48000", choices=("48000",), right=True, no_edit=True)
        cb.Enable(False)
      if r == 5:
        cb = self.AddComboCtrl(2, "48000", choices=("48000",), right=True, no_edit=True)
        cb.Enable(False)
      if r == 6:
        cb = self.AddComboCtrl(2, "48000", choices=("48000",), right=True, no_edit=True)
        cb.Enable(False)
      if r == 7:
        cb = self.AddComboCtrl(2, "48000", choices=("48000",), right=True, no_edit=True)
        cb.Enable(False)
      cb.handler = self.OnChange
      cb.quisk_data_name = data_name
      # Add col 1, 2, 3
      for col in range(1, 4):
        value = self.ItemValue(r, col)
        data_name = self.sound_names[r][col]
        if value is None:
          cb = self.AddComboCtrl(col + 2, ' ', choices=[], right=True)
          cb.Enable(False)
        else:
          cb = self.AddComboCtrl(col + 2, value, choices=choices[col], right=True)
        cb.handler = self.OnChange
        cb.quisk_data_name = self.sound_names[r][col]
      # Add col 4
      if not softrock and r in (2, 3):
        cb = self.AddComboCtrl(6, '', choices=[''])
        cb.Enable(False)
      elif "Output" in label:
        cb = self.AddComboCtrl(6, self.ItemValue(r, 4), choices=dev_play)
      else:
        cb = self.AddComboCtrl(6, self.ItemValue(r, 4), choices=dev_capt)
      cb.handler = self.OnChange
      cb.quisk_data_name = platform_accept + self.sound_names[r][4]
      self.NextRow()
      r += 1
    self.gbs = gbs
    self.Fit()
    self.SetupScrolling()
  def ItemValue(self, row, col):
    data_name = self.sound_names[row][col]
    if col == 4:		# Device names
      data_name = platform_accept + data_name
      value = self.GetValue(data_name, self.radio_dict)
      return value
    elif data_name:
      value = self.GetValue(data_name, self.radio_dict)
      if col == 3:		# Delay
        if value == "-1":
          value = ''
      return value
    return None
  def OnChange(self, ctrl):
    data_name = ctrl.quisk_data_name
    value = ctrl.GetValue()
    if data_name in ('channel_delay', 'tx_channel_delay'):
      value = value.strip()
      if not value:
        value = "-1"
    self.OnChange2(ctrl, value)

class RadioBands(BaseWindow):		# The Bands page in the second-level notebook for each radio
  def __init__(self, parent, radio_name):
    BaseWindow.__init__(self, parent)
    self.radio_name = radio_name
    radio_dict = local_conf.GetRadioDict(self.radio_name)
    radio_type = radio_dict['hardware_file_type']
    self.num_cols = 8
    #self.MarkCols()
    self.NextRow()
    self.AddTextCHelp(1, "Bands",
"This is a list of the bands that Quisk understands.  A check mark means that the band button is displayed.  A maximum of "
"14 bands may be displayed.")
    self.AddTextCHelp(2, "    Start MHz",
"This is the start of the band in megahertz.")
    self.AddTextCHelp(3, "    End MHz",
"This is the end of the band in megahertz.")
    heading_row = self.row
    self.NextRow()
    band_labels = radio_dict['bandLabels'][:]
    for i in range(len(band_labels)):
      if type(band_labels[i]) in (ListType, TupleType):
        band_labels[i] = band_labels[i][0]
    band_edge = radio_dict['BandEdge']
    # band_list is a list of all known bands
    band_list = band_edge.keys()
    if local_conf.ReceiverHasName(radio_type, 'tx_level'):
      tx_level = self.GetValue('tx_level', radio_dict)
      radio_dict['tx_level'] = tx_level     # Make sure the dictionary is in radio_dict
      for band in tx_level.keys():
        if band is None:	# Special band None means the default
          continue
        if band not in band_list:
          band_list.append(band)
    else:
      tx_level = None
    try:
      transverter_offset = radio_dict['bandTransverterOffset']
    except:
      transverter_offset = {}
      radio_dict['bandTransverterOffset'] = transverter_offset     # Make sure the dictionary is in radio_dict
    else:
      for band in transverter_offset.keys():
        if band not in band_list:
          band_list.append(band)
    try:
      hiqsdr_bus = radio_dict['HiQSDR_BandDict']
    except:
      hiqsdr_bus = None
    else:
      for band in hiqsdr_bus.keys():
        if band not in band_list:
          band_list.append(band)
    try:
      hermes_bus = radio_dict['Hermes_BandDict']
    except:
      hermes_bus = None
    else:
      for band in hermes_bus.keys():
        if band not in band_list:
          band_list.append(band)
    band_list.sort(self.SortCmp)
    self.band_checks = []
    # Add the Audio band
    cb = self.AddCheckBox(1, 'Audio', self.OnChangeBands)
    self.band_checks.append(cb)
    if 'Audio' in band_labels:
      cb.SetValue(True)
    self.NextRow()
    start_row = self.row
    # Add check box, start, end
    for band in band_list:
      cb = self.AddCheckBox(1, band, self.OnChangeBands)
      self.band_checks.append(cb)
      if band in band_labels:
        cb.SetValue(True)
      try:
        start, end = band_edge[band]
        start = str(start * 1E-6)
        end = str(end * 1E-6)
      except:
        start = ''
        end = ''
      cb = self.AddComboCtrl(2, start, choices=(start, ), right=True)
      cb.handler = self.OnChangeBandStart
      cb.quisk_band = band
      cb = self.AddComboCtrl(3, end, choices=(end, ), right=True)
      cb.handler = self.OnChangeBandEnd
      cb.quisk_band = band
      self.NextRow()
    col = 3
    # Add tx_level
    if tx_level is not None:
      col += 1
      self.row = heading_row
      self.AddTextCHelp(col, "    Tx Level",
"This is the transmit level for each band.  The level is a number from zero to 255.  Changes are immediate.")
      self.row = start_row
      for band in band_list:
        try:
          level = tx_level[band]
          level = str(level)
        except:
          try:
            level = tx_level[None]
            tx_level[band] = level      # Fill in tx_level for each band
            level = str(level)
          except:
            tx_level[band] = 0
            level = '0'
        cb = self.AddComboCtrl(col, level, choices=(level, ), right=True)
        cb.handler = self.OnChangeDict
        cb.quisk_data_name = 'tx_level'
        cb.quisk_band = band
        self.NextRow()
    # Add transverter offset
    if type(transverter_offset) is DictType:
      col += 1
      self.row = heading_row
      self.AddTextCHelp(col, "    Transverter Offset",
"If you use a transverter, you need to tune your hardware to a frequency lower than\
 the frequency displayed by Quisk.  For example, if you have a 2 meter transverter,\
 you may need to tune your hardware from 28 to 30 MHz to receive 144 to 146 MHz.\
 Enter the transverter offset in Hertz.  For this to work, your\
 hardware must support it.  Currently, the HiQSDR, SDR-IQ and SoftRock are supported.")
      self.row = start_row
      for band in band_list:
        try:
          offset = transverter_offset[band]
        except:
          offset = ''
        else:
          offset = str(offset)
        cb = self.AddComboCtrl(col, offset, choices=(offset, ), right=True)
        cb.handler = self.OnChangeDictBlank
        cb.quisk_data_name = 'bandTransverterOffset'
        cb.quisk_band = band
        self.NextRow()
    # Add hiqsdr_bus
    if hiqsdr_bus is not None:
      col += 1
      self.row = heading_row
      self.AddTextCHelp(col, "    IO Bus",
"This is the value to set on the IO bus for each band.  It may be used to select filters.")
      self.row = start_row
      for band in band_list:
        try:
          bus = hiqsdr_bus[band]
        except:
          bus = ''
          bus_choice = ('11', )
        else:
          bus = str(bus)
          bus_choice = (bus, )
        cb = self.AddComboCtrl(col, bus, bus_choice, right=True)
        cb.handler = self.OnChangeDict
        cb.quisk_data_name = 'HiQSDR_BandDict'
        cb.quisk_band = band
        self.NextRow()
    # Add hermes_bus
    if hermes_bus is not None:
      col += 1
      self.row = heading_row
      self.AddTextCHelp(col, "    IO Bus",
"This is the value to set on the IO bus for each band.  It may be used to select filters.")
      self.row = start_row
      for band in band_list:
        try:
          bus = hermes_bus[band]
        except:
          bus = ''
          bus_choice = ('11', '0x0B', '0b00001011')
        else:
          #b1 = "0b%b" % bus
          b1 = "0x%X" % bus
          b2 = str(bus)
          bus_choice = (b1, b2, '0b00000001')
          bus = b1
        cb = self.AddComboCtrl(col, bus, bus_choice, right=True)
        cb.handler = self.OnChangeDict
        cb.quisk_data_name = 'Hermes_BandDict'
        cb.quisk_band = band
        self.NextRow()
    # Add the Time band
    cb = self.AddCheckBox(1, 'Time', self.OnChangeBands)
    self.band_checks.append(cb)
    if 'Time' in band_labels:
      cb.SetValue(True)
    self.NextRow()
    self.Fit()
    self.SetupScrolling()
  def SortCmp(self, item1, item2):
    # Numerical conversion to wavelength
    if item1[-2:] == 'cm':
      item1 = float(item1[0:-2]) * .01
    elif item1[-1] == 'k':
      item1 = 300.0 / (float(item1[0:-1]) * .001)
    else:
      try:
        item1 = float(item1)
      except:
        item1 = 1.0
    if item2[-2:] == 'cm':
      item2 = float(item2[0:-2]) * .01
    elif item2[-1] == 'k':
      item2 = 300.0 / (float(item2[0:-1]) * .001)
    else:
      try:
        item2 = float(item2)
      except:
        item2 = 1.0
    if item1 > item2:
      return -1
    elif item1 == item2:
      return 0
    else:
      return +1
  def OnChangeBands(self, ctrl):
    band_list = []
    count = 0
    for cb in self.band_checks:
      if cb.IsChecked():
        band = cb.GetLabel()
        count += 1
        if band == '60' and len(conf.freq60) > 1:
          band_list.append(('60', ) * len(conf.freq60))
        elif band == 'Time' and len(conf.bandTime) > 1:
          band_list.append(('Time', ) * len(conf.bandTime))
        else:
          band_list.append(band)
    if count > 14:
      dlg = wx.MessageDialog(None,
        "There are more than the maximum of 14 bands checked.  Please remove some checks.",
        'List of Bands', wx.OK|wx.ICON_ERROR)
      dlg.ShowModal()
      dlg.Destroy()
    else:
      radio_dict = local_conf.GetRadioDict(self.radio_name)
      radio_dict['bandLabels'] = band_list
      local_conf.settings_changed = True
  def OnChangeBandStart(self, ctrl):
    radio_dict = local_conf.GetRadioDict(self.radio_name)
    band_edge = radio_dict['BandEdge']
    band = ctrl.quisk_band
    start, end = band_edge.get(band, (0, 9999))
    value = ctrl.GetValue()
    if self.FormatOK(value, 'numb'):
      start = int(float(value) * 1E6 + 0.1)
      band_edge[band] = (start, end)
      local_conf.settings_changed = True
  def OnChangeBandEnd(self, ctrl):
    radio_dict = local_conf.GetRadioDict(self.radio_name)
    band_edge = radio_dict['BandEdge']
    band = ctrl.quisk_band
    start, end = band_edge.get(band, (0, 9999))
    value = ctrl.GetValue()
    if self.FormatOK(value, 'numb'):
      end = int(float(value) * 1E6 + 0.1)
      band_edge[band] = (start, end)
      local_conf.settings_changed = True
  def OnChangeDict(self, ctrl):
    radio_dict = local_conf.GetRadioDict(self.radio_name)
    dct = radio_dict[ctrl.quisk_data_name]
    band = ctrl.quisk_band
    value = ctrl.GetValue()
    if self.FormatOK(value, 'inte'):
      value = int(value)
      dct[band] = value
      local_conf.settings_changed = True
      if ctrl.quisk_data_name == 'tx_level' and hasattr(application.Hardware, "SetTxLevel"):
        application.Hardware.SetTxLevel()
  def OnChangeDictBlank(self, ctrl):
    radio_dict = local_conf.GetRadioDict(self.radio_name)
    dct = radio_dict[ctrl.quisk_data_name]
    band = ctrl.quisk_band
    value = ctrl.GetValue()
    value = value.strip()
    if not value:
      if dct.has_key(band):
        del dct[band]
        local_conf.settings_changed = True
    elif self.FormatOK(value, 'inte'):
      value = int(value)
      dct[band] = value
      local_conf.settings_changed = True
