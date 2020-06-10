
from __future__ import print_function

import threading, time, math, socket, re
from quisk_hardware_model import Hardware as BaseHardware

DEBUG = 1

import _quisk as QS

class Hardware(BaseHardware):
  def __init__(self, app, conf):
    BaseHardware.__init__(self, app, conf)
    self.vfo = None
    self.ptt_button = 0
    self.usbsr_ip_address = conf.usbsr_ip_address
    self.usbsr_port = conf.usbsr_port

  def open(self):			# Called once to open the Hardware
    freq = self.GetFreq()
    if freq:
      print ('Run freq', freq)
      text = "found usbsoftrock daemon"
    else:
      print ('cannot find usbsoftrock daemon')
      text = "cannot find usbsoftrock daemon"
    return text

  def close(self):
    pass
  def ChangeFrequency(self, tune, vfo, source='', band='', event=None):
    if self.vfo != vfo:
       self.SetFreq(vfo) 
       self.vfo = vfo
    return tune, vfo
  
  def ReturnFrequency(self):
    # Return the current tuning and VFO frequency.  If neither have changed,
    # you can return (None, None).  This is called at about 10 Hz by the main.
    # return (tune, vfo)	# return changed frequencies
    return None, None		# frequencies have not changed
 
  def ChangeBand(self, band):
    # band is a string: "60", "40", "WWV", etc.
    pass

  def HeartBeat(self):	# Called at about 10 Hz by the main
    pass

  def GetFreq(self):	# return the running frequency
    MESSAGE = "get freq"
    srsock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    srsock.settimeout(1)
    srsock.sendto(MESSAGE, (self.usbsr_ip_address, self.usbsr_port))
    try:
      data, addr = srsock.recvfrom(1024) # buffer size is 1024 bytes
    except:
      srsock.close()
      print ('error')
      return None #maybe return None instead to simplify if statement
    else:
      srsock.close()
      print ('recieved data', data)
      freq = float(re.findall("\d+.\d+", data)[0])
      freq = int(freq * 1.0e6)
      return freq
  
  def SetFreq(self, freq):
    if freq <= 0 or freq > 30000000:
      return
    freq = freq/float(1.0e6)
    MESSAGE = "set freq " + str(freq)
    srsock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    srsock.sendto(MESSAGE, (self.usbsr_ip_address, self.usbsr_port))
    print (MESSAGE)
    return True

  def OnButtonPTT(self, event=None):
    if event:
      if event.GetEventObject().GetValue():
        self.ptt_button = 1
	message = "set ptt on"
      else:
        self.ptt_button = 0
	message = "set ptt off"
      srsock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
      srsock.settimeout(1)
      srsock.sendto(message, (self.usbsr_ip_address, self.usbsr_port))
      data, addr = srsock.recvfrom(1024) # buffer size is 1024 bytes
      srsock.close()
      print (data)
      if data == "ok":
        QS.set_key_down(self.ptt_button)
      else:
        print ('error doing', message)
        text = "error setting ptt on or off!"
        self.config_text = text
  def OnSpot(self, level):
    self.spot_level = level

   
