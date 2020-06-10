#!/usr/bin/python

import wx
from wx import py
from wx import stc
import os, sys, webbrowser

# Change to the directory of quisk.py.
os.chdir(os.path.normpath(os.path.dirname(__file__)))

# Command line parsing: be able to specify the config file.
from optparse import OptionParser
parser = OptionParser()
parser.add_option('-c', '--config', dest='config_file_path',
		help='Specify the configuration file path')
parser.add_option('-e', '--edit', action='store_true', dest='edit',
                help='Edit the config file')
parser.add_option('-d', '--defaults', action='store_true', dest='defaults',
                help='Show a window with the configuration defaults')
parser.add_option('-r', '--docs', action='store_true', dest='docs',
                help='Show a window with the docs.html file')
argv_options = parser.parse_args()[0]

ConfigPath = argv_options.config_file_path	# Get config file path
if not ConfigPath:	# Use default path; Duplicated from quisk.py
  if sys.platform == 'win32':
    ConfigPath = os.getenv('HOMEDRIVE', '') + os.getenv('HOMEPATH', '')
    ConfigPath = os.path.join(ConfigPath, "My Documents")
    ConfigPath = os.path.join(ConfigPath, "quisk_conf.py")
    if not os.path.isfile(ConfigPath):	# See if the user has a config file
      try:
        import shutil	# Try to create an initial default config file
        shutil.copyfile('quisk_conf_win.py', ConfigPath)
      except:
        pass
  else:
    ConfigPath = os.path.expanduser('~/.quisk_conf.py')

class EditApp(wx.App):
  def __init__(self):
    wx.App.__init__(self, redirect=False)
  def OnInit(self):
    wx.InitAllImageHandlers()
    frame = None
    if argv_options.defaults:
      frame = py.editor.EditorFrame(filename="quisk_conf_defaults.py")
      frame.editor.window.SetReadOnly(True)
      frame.SetTitle("Configuration defaults quisk_conf_defaults.py")
      frame.Show()
    if argv_options.edit:
      frame = py.editor.EditorFrame(filename=ConfigPath)
      frame.SetTitle(ConfigPath)
      frame.Show()
    if argv_options.docs:
      webbrowser.open("docs.html", new=2)
    if frame:
      self.SetTopWindow(frame)

    return True

def main():
  app = EditApp()
  app.MainLoop()

if __name__ == '__main__':
    main()
