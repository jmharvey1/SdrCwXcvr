# This code was contributed by Christof, DJ4CM.  Many Thanks!!

import threading
import time
import telnetlib
import sys
import quisk_conf_defaults as conf

class DxEntry():
  def __init__(self):
    self.info = []
    
  def getFreq(self):
    return self.freq
    
  def getDX(self):
    return self.dx
  
  def getSpotter(self, index):
    return self.info[index][0]
    
  def getTime(self, index):
    return self.info[index][1]

  def setTime(self, index, value):
    L1 = list(self.info)
    L2 = list(L1[index])
    L2[1] = value
    L1[index] = tuple(L2)
    self.info = tuple(L1)
    return 
  
  def getLocation(self, index):
    return self.info[index][2]
  
  def getComment(self, index):
    return self.info[index][3]
  
  def getLen(self):
    return len(self.info)
  
  def equal(self, element):
    if element.getDX() == self.dx:
      return True
    else:
      return False
    
  def join (self, element):
    for i in range (0, len(element.info)):
      self.info.insert(0, element.info[i])
    length = len(self.info)
    # limit to max history
    if length > 3:
      del (self.info[length-1])
    self.timestamp = max (self.timestamp, element.timestamp)  
    
  def isExpired(self):
    #print(time.time()-self.timestamp)
    #if time.time()-self.timestamp > conf.dxClExpireTime * 60:
    #  print("DELETE ENTRY")             
    return time.time()-self.timestamp > conf.dxClExpireTime * 60
    
  def parseMessage(self, message):  
    words = message.split()
    sTime = ''
    locator = ''
    comment = ''
    if len(words) > 3 and words[0].lower() == 'dx' and words[1].lower() == 'de':
      spotter = words[2].strip(':')
      self.freq = int(float(words[3])*1000)
      self.dx = words[4]
      locator = self.dx
      for index in range (5, len(words)):
        word = words[index]
#        print(index, word)
        try:
          if index < len(words)-1:
            if comment != '':
              comment += ' '
            comment += word
           
#         if sTime != '':
#            locator = word.strip('\07')
          #search time
          if word[0:3].isdigit() and word[4].isalpha():
            sTime = word.strip('\07')
            sTime = sTime[0:2]+':'+sTime[2:4]+ ' UTC'
          
#          if sTime == '':
#            print(word) 
#            if comment != '':
#              comment += ' '
#            comment += word
      
        except:
          pass
      self.info.insert(0, (spotter, sTime, locator, comment))
      self.timestamp = time.time()
#      print(self.dx, self.freq, spotter, sTime, locator, comment)
      return True
    return False   
  
class DxCluster(threading.Thread):
  def __init__(self, dxClHost, dxClPort, user_call_sign, dxClPassword, dxClFltrCmd ):
    self.do_init = 1
    threading.Thread.__init__(self)
    self.doQuit = threading.Event()
    self.dxSpots = []
    self.doQuit.clear()
    self.dxClHost = dxClHost
    self.dxClPort = dxClPort
    self.user_call_sign = user_call_sign
    self.dxClFltrCmd = dxClFltrCmd
    try:
      if not (conf.TelnetTalk == None):
        self.TelnetTalk = conf.TelnetTalk
    except:
      self.TelnetTalk = True
    
  def run(self):
    self.telnetInit()
    if self.telnetConnect():
      if not self.dxClFltrCmd =='':
        self.tn.write(str(self.dxClFltrCmd) + "\n")
        if(self.TelnetTalk): print(str(self.dxClFltrCmd + "\n"))
      
      while not self.doQuit.isSet():
        try:
          self.telnetRead()
        except:
          self.tn.close()
          time.sleep(20)
          if not self.doQuit.isSet():
            self.telnetConnect()
    self.tn.close()
      
  def setListener (self, listener):  
    self.listener = listener
        
  def telnetInit(self):
    self.tn = telnetlib.Telnet()
      
  def telnetConnect(self):
    #if(self.TelnetTalk): self.tn.set_debuglevel(3)
    HstPrt = (str(self.dxClHost), str(self.dxClPort))
    try:
        self.tn.open(self.dxClHost, self.dxClPort, 10)
        if(self.TelnetTalk): print('Connected to:  %s; Port: %s\n' %HstPrt)
        try:
          self.tn.read_until('login:', 10)
          self.tn.write(str(self.user_call_sign) + "\n")
                  # user_call_sign may be Unicode
          if conf.dxClPassword:
            self.tn.read_until("Password: ")
            self.tn.write(str(self.dxClPassword) + "\n")
          return True
        except Exception:
          print("DX Cluster Connection error: {}:{}".format(self.dxClHost, self.dxClPort))
          return False
    except Exception:
      print("DX Cluster Telnet.Open() error: {}:{}".format(self.dxClHost, self.dxClPort))
      return False    

  def telnetRead(self):
    message = self.tn.read_until('\n', 60).decode(encoding='utf-8', errors='replace')
    if self.doQuit.isSet() == False:
      dxEntry = DxEntry();
      if dxEntry.parseMessage(message):
        if(self.TelnetTalk): print(message)
        for i, listElement in enumerate(self.dxSpots):
          if (listElement.equal(dxEntry)):
            listElement.join (dxEntry)
            return
          if listElement.isExpired():
            del (self.dxSpots[i])
        self.dxSpots.append(dxEntry)
        if self.listener:
          self.listener()
        
  def getHost(self):
    return self.tn.host + ':' + str(self.tn.port)
        
  def stop(self):
    self.doQuit.set()
