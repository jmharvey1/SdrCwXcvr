# This is my HomeBrew SoftRock like SDR using a AD9850 DDS VFO & SS Micro (Arduino) as a USB serial interface
# I also added the folder "USB" to this version of QUISH (4.1.55)
# it to your own quisk_hardware.py and make changes there.
# See quisk_hardware_model.py for documentation.
#
# This hardware module sends the IF output of an AOR SftRkSDR
# to the input of an SDR-IQ by RfSpace
#

import time
import _quisk as QS
from sdriqpkg import sdriq
import serial			# From the pyserial package
import struct, threading, time, traceback, math ## JMH 20180227 Added the following in an attempt to support hombrew ssmicro/si5351 sdr as a tramsmitter
                                                ## this code in its original form was taken from softrock/hardware_usb.py file
import usb.core, usb.util
import wx
from quisk_hardware_model import Hardware as BaseHardware

#IN =  usb.util.build_request_type(usb.util.CTRL_IN,  usb.util.CTRL_TYPE_VENDOR, usb.util.CTRL_RECIPIENT_DEVICE)

#class Hardware(BaseHardware):
#  def __init__(self, app, conf):
#    BaseHardware.__init__(self, app, conf)
#    self.vfo = self.conf.fixed_vfo_freq		# Fixed VFO frequency in Hertz
#    self.tune = self.vfo + 10000		# Current tuning frequency in Hertz
#  def ChangeFrequency(self, tune, vfo, source='', band='', event=None):
#    # Change and return the tuning and VFO frequency.  See quisk_hardware_model.py.
#    self.tune = tune
#    return tune, self.vfo
#  def ReturnFrequency(self):
#    # Return the current tuning and VFO frequency.  See quisk_hardware_model.py.
#    return self.tune, self.vfo

# Use the SDR-IQ hardware as the base class
#from sdriqpkg import quisk_hardware as SdriqHardware
#BaseHardware = SdriqHardware.Hardware

DEBUG = 0

class Hardware(BaseHardware):
  def __init__(self, app, conf):
    BaseHardware.__init__(self, app, conf)
    self.vfo_frequency = self.conf.fixed_vfo_freq		# current vfo frequency
    self.tune = self.vfo_frequency + 10000		# Current tuning frequency in Hertz
    self.is_cw = False                  ##20180226 JMH added this property to support SSmicro Si5351 TX setup
##    self.ptt_button = 0                 ##20180226 JMH added this property to support SSmicro Si5351 TX setup
    self.key_thread = None              ##20180226 JMH added this property to support SSmicro Si5351 TX setup
    self.usb_dev = None                 ##20180226 JMH added this property to support SSmicro Si5351 TX setup
    self.CmdStr= ''                     ##20180226 JMH added this property to support SSmicro Si5351 TX setup
    self.tty_name = '/dev/ttyACM0'	# serial port name for SftRkSDR
    self.serial = None			# the open serial port
    self.timer = 0.02			# time between SftRkSDR commands in seconds
    self.time0 = 0			# time of last SftRkSDR command
    self.serial_out = []		# send commands slowly
    try:
      if not (conf.HrdwrTalk == None):
        self.HrdwrTalk = conf.HrdwrTalk
    except:
      self.HrdwrTalk = True
  def open(self, application):
     # find our device
    text ="XXX" 
    usb_dev = usb.core.find(idVendor=self.conf.usb_vendor_id, idProduct=self.conf.usb_product_id)
    if usb_dev is None:
      text = 'USB SSmicro not found VendorID 0x%X ProductID 0x%X' % (
          self.conf.usb_vendor_id, self.conf.usb_product_id)
      print(text)
      return text
    
    if DEBUG and usb_dev:
      if(self.HrdwrTalk): print ('DeBug: Found SSmicro 0x%X; ProductID 0x%X' % (
          self.conf.usb_vendor_id, self.conf.usb_product_id))
    if usb_dev:  
      self.serial = serial.Serial(port=self.tty_name, baudrate=9600,
            stopbits=serial.STOPBITS_TWO, xonxoff=1, timeout=0)
      #self.SendSSmicro('MD0\r')		# set WFM mode so the IF output is available
      self.usb_dev = usb_dev		# success
      ver = 'unknown'
      sound = self.conf.name_of_sound_capt
      if len(sound) > 50:
        sound = sound[0:30] + '|||' + sound[-17:]
      text = 'Capture from SSmicro USB on %s, Firmware %s' % (sound, ver)
      if DEBUG: print("DeBug: %s" %text)
      ##if self.conf.name_of_mic_play and self.conf.key_poll_msec:
      if self.conf.key_poll_msec:
        #self.key_thread = KeyThread(usb_dev, self.conf.key_poll_msec / 1000.0, self.conf.key_hang_time)
        self.key_thread = KeyThread(self.serial, self.conf.key_poll_msec / 1000.0, self.conf.key_hang_time, self.HrdwrTalk)
        self.key_thread.start()
        if DEBUG: print("DeBug: Key_thread Started")

          
      QS.invert_spectrum(1)
      text = BaseHardware.open(self)		# save the message
      sdriq.freq_sdriq(10700000)
    return text
  def close(self):
    BaseHardware.close(self)
    if self.serial:
      self.serial.write('EX\r')
      time.sleep(1)			# wait for output to drain, but don't block
      self.serial.close()
      self.serial = None
  def ChangeFrequency(self, rx_freq, vfo_freq, source='', band='', event=None):
    vfo_freq = (vfo_freq + 5000) / 10000 * 10000		# round frequency
    if vfo_freq != self.vfo_frequency and vfo_freq >= 100000:
      self.vfo_frequency = vfo_freq
      self.SendSSmicro('RF%010d\r' % vfo_freq)
    return rx_freq, vfo_freq
  def ChangeTXFreq(self, tx_freq): ##20180226 JMH added this method to support SSmicro Si5351 TX setup
    self.SendSSmicro('TX%010d\r' %tx_freq)
    return
  def SndKeyStream(self, keystream): ##201800708 JMH added this method to support SSmicro key via usb serial link
    self.SendSSmicro('KS%s\r' %keystream)
    return
  
  def ChangeBand(self, band):	# Defeat base class method
    return
  def ChangeMode(self, mode):	# Change the tx/rx mode  ##20180226 JMH added this method to support SSmicro Si5351 TX setup
    # mode is a string: "USB", "AM", etc.
    if mode in ('CWU', 'CWL'):
      self.is_cw = True
    else:
      self.is_cw = False
    if self.key_thread:
      self.key_thread.IsCW(self.is_cw)
    elif hasattr(self, 'OnButtonPTT'):
      self.OnButtonPTT()
  def SendSSmicro(self, msg):	# JMH changed this to SendSSmicro to make it easier to understand what the method does
    if self.serial:
      if time.time() - self.time0 > self.timer:
        self.serial.write(msg)			# send message now
        self.time0 = time.time()
      else:
        self.serial_out.append(msg)		# send message later
   ## JMH 20180227 Added the following in an attempt to support hombrew ssmicro/si5351 sdr as a tramsmitter
  def OnSpot(self, level):
    if self.key_thread:
      self.key_thread.OnSpot(level)
  def OnButtonPTT(self, event=None):
    if event:
      if event.GetEventObject().GetValue():
        self.ptt_button = 1
        self.CmdStr= 'PTTON\r'
      else:
        self.ptt_button = 0
        self.CmdStr= 'PTTOFF\r'
      try:
        self.SendSSmicro(self.CmdStr) #self.usb_dev.ctrl_transfer(IN, 0x50, self.ptt_button, 0, 3)
      except usb.core.USBError:
        if DEBUG: traceback.print_exc()  
##    if self.key_thread:
##      self.key_thread.OnPTT(self.ptt_button)
##    elif self.usb_dev:
##      if self.is_cw:
##        QS.set_key_down(0)
##        QS.set_transmit_mode(self.ptt_button)
##      else:
##        QS.set_key_down(self.ptt_button)
##      try:
##        self.SendSSmicro(self.CmdStr) #self.usb_dev.ctrl_transfer(IN, 0x50, self.ptt_button, 0, 3)
##      except usb.core.USBError:
##        if DEBUG: traceback.print_exc()
##        try:
##         self.SendSSmicro(self.CmdStr) #self.usb_dev.ctrl_transfer(IN, 0x50, self.ptt_button, 0, 3)
##        except usb.core.USBError:
##          if DEBUG: traceback.print_exc()   
      
  def Getkey_down(self):
     if self.key_thread:
       keystate = self.key_thread.Getkey_down()
       if keystate is None: return 2
       else:
         if keystate : return 1
         else: return 0  
     else: return 0
     
  def HeartBeat(self):	# Called at about 10 Hz by the main
    ## JMH 20190909 Not used in current version of quisk_KW4KD.py; replaced by KeyThread routine
    BaseHardware.HeartBeat(self)
    if self.serial:
      chars = self.serial.read(1024)
      if chars:
        if(self.HrdwrTalk): print chars ##JMH Only print SS micro response if .quisk_conf.py 'HrdwrTalk' has been set to 'True'
      if self.serial_out and time.time() - self.time0 > self.timer:
        self.serial.write(self.serial_out[0])
        self.time0 = time.time()
        del self.serial_out[0]

## JMH 20180227 Added the following in an attempt to support hombrew ssmicro/si5351 sdr as a tramsmitter
## this code in its original form was taken from softrock/hardware_usb.py file
class KeyThread(threading.Thread):
  """Create a thread to monitor the key state."""
  def __init__(self, dev, poll_secs, key_hang_time,  HrdwrTalk):
    #self.usb_dev = dev
    self.text = ""
    self.serial = dev
    self.poll_secs = poll_secs
    self.key_down = False       ##JMH ADDED to track ssmicro external key state 
    self.stateChng = False
    self.stateChng1 = False
    self.key_hang_time = key_hang_time
    self.ptt_button = 0         ##JMH TODO don't think when using the SSmicro interface this property has a a real role 
    self.spot_level = -1	# level is -1 for Spot button Off; else the Spot level 0 to 1000.
    self.currently_in_tx = 0
    self.is_cw = False
    self.key_timer = 0
    self.key_transmit = 0
    threading.Thread.__init__(self)
    self.doQuit = threading.Event()
    self.doQuit.clear()
    self.HrdwrTalk = HrdwrTalk
    
  def run(self):
    while not self.doQuit.isSet():
      if DEBUG:
        if not self.text == "":
          print("DeBug: self.text: %s" %self.text)
          self.text = ""
      
      try:		# Test key up/down state
        #ret = self.usb_dev.ctrl_transfer(IN, 0x51, 0, 0, 1)
        if self.serial: ##JMH 20190909 ADDED to support keying SSMicro via external key
          chars = self.serial.read(1024)
          if chars:
            if(self.HrdwrTalk): print("SSMicro: %s" %chars)
            if(chars[0:6]=="KEYDWN"):
              self.key_down = True
              self.stateChng = True
              self.stateChng1 = True
            if(chars[0:5]=="KEYUP"):
              self.key_down = False
              self.stateChng = True
              self.stateChng1 = True
              
      except usb.core.USBError:
        if DEBUG: traceback.print_exc()
      if self.is_cw:
        if self.stateChng:      
          if self.spot_level >= 0 or self.key_down:		# key is down
            QS.set_key_down(1)
            self.key_transmit = 1
            #self.key_timer = time.time()
          else:			# key is up
            QS.set_key_down(0)
##            if self.key_transmit and time.time() - self.key_timer > self.key_hang_time:
##              self.key_transmit = 0
          self.stateChng =False
        if self.spot_level >= 0 or self.key_down:		# key is down
          self.key_timer = time.time()
        else:
          if self.key_transmit and time.time() - self.key_timer > self.key_hang_time:
            self.key_transmit = 0
          
        if self.key_transmit != self.currently_in_tx:
          QS.set_transmit_mode(self.key_transmit)
          #wx.CallAfter(self.application.OnButtonPTT(None))
          #self.application.pttButton.SetValue(0, self.key_transmit)
          #self.ptt_button = self.key_transmit
          self.currently_in_tx = self.key_transmit	# success
          
##          try:
##            #self.usb_dev.ctrl_transfer(IN, 0x50, self.key_transmit, 0, 3)
##            print("key_transmit state %d" %self.key_transmit)
##          except usb.core.USBError:
##            if DEBUG: traceback.print_exc()
##          else:
##            self.currently_in_tx = self.key_transmit	# success
##            QS.set_transmit_mode(self.key_transmit)
##            if DEBUG: print ("Change CW currently_in_tx", self.currently_in_tx)
##      else:  #weare not in the CW mode
##        if self.key_down or self.ptt_button:
##          self.key_transmit = 1
##        else:
##          self.key_transmit = 0
##        if self.key_transmit != self.currently_in_tx:
##          QS.set_key_down(self.key_transmit)
##          try:
##            #self.usb_dev.ctrl_transfer(IN, 0x50, self.key_transmit, 0, 3)
##            print("key_transmit state %d" %self.key_transmit)
##          except usb.core.USBError:
##            if DEBUG: traceback.print_exc()
##          else:
##            self.currently_in_tx = self.key_transmit	# success
##            if DEBUG: print ("Change currently_in_tx", self.currently_in_tx)
      time.sleep(self.poll_secs)
  def stop(self):
    """Set a flag to indicate that the thread should end."""
    self.doQuit.set()
  def OnPTT(self, ptt):
    self.ptt_button = ptt
  def OnSpot(self, level):
    self.spot_level = level
  def IsCW(self, is_cw):
    self.is_cw = is_cw
  def Getkey_down(self):
    if self.stateChng1:
      self.stateChng1 = False
      return self.key_down
    else: return None  
       
