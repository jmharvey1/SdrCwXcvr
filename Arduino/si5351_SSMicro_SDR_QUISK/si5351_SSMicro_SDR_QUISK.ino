/*
   JMH 20210128
    Minor tweak to cleanup a portion of the getNxtKeyStroke() routine. Removed second condition in if(PTT && Active) statement. Ensuring, when there's no active key streaming,
    the T/R data line is set to "receive". This sometimes would happen using FLDIGI's "TUNE" mode. Because streaming in this mode ends with a "keydown" signal
   JMH 20210101
   Streamlined streaming key data buffering and TR relay management(See getNxtKeyStroke() & SetPTT() routines). Also added SpdTbl[41]) to set interval timing Vs WPM (spd) with
   better precision than previous methods afforded.
   JMH 20201228
   Changed streaming scheme such that a "dit" is sent as four "keydown" duration intervals. This update also invloved changing timing measurement from millisconds to micro seconds.
   Additionally added dynamic timing adjustments to regulate the buffer backlog. Helping to ensure it doesn't underrun or over flow.
   JMH 20190911
   Reworked portions of this sketch to improve support the use of external manual keying
   JMH 20190815
   Added pin A2 to band selection scheme to support 8 band change (80 through 10 meters)
   JMH 20180709
   Revised sketch to include support for CW Key Stroke keying via USB serial port; On the computer side using modified versions of QUISK & FLDIGI to generate & send the data stream
   JMH 20180514
   modified to lockout ptt off command if carrier is on at the time the command is recieved via the serial port; this is to allow the last code symbol to complete before reating to the command

  sketch written by Jim Harvey (KW4KD) 20180601
   parts of this sketch may contain code written by: Jason Milldrum as well as other unknown sources
    Copyright (C) 2015 - 2016 Jason Milldrum <milldrum@gmail.com>

   This program is free software: you can redistribute it and/or modify
   it under the terms of the GNU General Public License as published by
   the Free Software Foundation, either version 3 of the License, or
   (at your option) any later version.

   This program is distributed in the hope that it will be useful,
   but WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
   GNU General Public License for more details.

   You should have received a copy of the GNU General Public License
   along with this program.  If not, see <http://www.gnu.org/licenses/>.
*/

/*
   Setting the phase of a clock requires that you manually set the PLL and
   take the PLL frequency into account when calculation the value to place
   in the phase register. As shown on page 10 of Silicon Labs Application
   Note 619 (AN619), the phase register is a 7-bit register, where a bit
   represents a phase difference of 1/4 the PLL period. Therefore, the best
   way to get an accurate phase setting is to make the PLL an even multiple
   of the clock frequency, depending on what phase you need.

   If you need a 90 degree phase shift (as in many RF applications), then
   it is quite easy to determine your parameters. Pick a PLL frequency that
   is an even multiple of your clock frequency (remember that the PLL needs
   to be in the range of 600 to 900 MHz). Then to set a 90 degree phase shift,
   you simply enter that multiple into the phase register. Remember when
   setting multiple outputs to be phase-related to each other, they each need
   to be referenced to the same PLL.
*/

#include "si5351.h"
#include "Wire.h"
#define KeyPin 11 //input signal
#define PTTPin 10 //output signal

Si5351 si5351;
char buf[50];
char KeyStream[510];
unsigned long HiVal;
unsigned long LoVal;
String inputString = "";         // a string to hold incoming data
boolean stringComplete = false;  // whether the string is complete
boolean SetRX = false;
boolean SetTX = false;
boolean KeyClosed = false;
boolean PTT = false;
boolean DldPTToff = true;
boolean DldPTTon = true;
boolean KeyActive = false; //Used to recognize external manual keying activity
boolean AdjDur = false;
unsigned long BufLpCntr = 100;
unsigned long AvgPtrVal = 0;
unsigned long KyDwnTime = 0;
long BufAdj = 0;
int contactcntr = 0;
int OldBufLen = 0;
int spd = 0;
int loopcnt = 0;   //delays turning off at the end of what had been a period of active streaming of key data commands
int AvgKSptr = 0;
//boolean TXRFON = false;
float RXcenterFreq = 0.0;
float TXfreq = 0.0;
//unsigned long timesUP = 0;
unsigned long DlyIntrvl = 0;
unsigned long lastTime = 0;
int XtalErr = -9500; // integer value measured to 0.01 Hertz ie 100 = 1.00Hz
typedef struct
{
  unsigned long Intrvl;
  int Inc;
  int Dec;
  int BufDpth;
}  record_type;

const record_type SpdTbl[41]{
{0,0,0, 40},
{((1200000 / 16) / 4) - 2300, 80, 40, 15},
{((1200000 / 2) / 4), 2, 1, 40},
{((1200000 / 3) / 4), 2, 1, 40},
{((1200000 / 4) / 4), 2, 1, 40},
{((1200000 / 5) / 4) - 830, 3, 15, 8},
{((1200000 / 6) / 4) - 860, 3, 15, 10},
{((1200000 / 7) / 4) - 890, 20, 10, 12},
{((1200000 / 8) / 4) - 890, 20, 10, 15},
{((1200000 / 9) / 4) - 915, 16, 8, 15},
{((1200000 / 10) / 4) - 930, 16, 8, 17},
{((1200000 / 11) / 4) - 940, 8, 4, 20},
{((1200000 / 12) / 4) - 950, 6, 3, 22},
{((1200000 / 13) / 4) - 960, 6, 3, 25}, //- 3300
{((1200000 / 14) / 4) - 975, 6, 3, 25},
{((1200000 / 15) / 4) - 975, 6, 3, 25},
{((1200000 / 16) / 4) - 975, 2, 1, 25},
{((1200000 / 17) / 4) - 1015, 2, 1, 28},
{((1200000 / 18) / 4) - 1000, 2, 1, 30},
{((1200000 / 19) / 4) - 1000, 2, 1, 30},
{((1200000 / 20) / 4) - 1025, 2, 1, 30},
{((1200000 / 21) / 4) - 1025, 2, 1, 30},
{((1200000 / 22) / 4) - 1025, 2, 1, 30},
{((1200000 / 23) / 4) - 1025, 2, 1, 30},
{((1200000 / 24) / 4) - 1050, 2, 1, 30},
{((1200000 / 25) / 4) - 1050, 2, 1, 30},
{((1200000 / 26) / 4) - 1050, 2, 1, 30},
{((1200000 / 27) / 4) - 1050, 2, 1, 30},
{((1200000 / 28) / 4) - 1050, 2, 1, 30},
{((1200000 / 29) / 4) - 1050, 2, 1, 30},
{((1200000 / 30) / 4) - 900, 2, 1, 30},
{((1200000 / 31) / 4) - 900, 2, 1, 30},
{((1200000 / 32) / 4) - 900, 2, 1, 30},
{((1200000 / 33) / 4) - 900, 2, 1, 30},
{((1200000 / 34) / 4) - 900, 2, 1, 30},
{((1200000 / 35) / 4) - 900, 2, 1, 30},
{(1200000 / 36) / 4, 2, 1, 40},
{(1200000 / 37) / 4, 2, 1, 40},
{(1200000 / 38) / 4, 2, 1, 40},
{(1200000 / 39) / 4, 2, 1, 40},
{(1200000 / 40) / 4, 0, 0, 40}
};

void setup()
{
  // Start serial and initialize the Si5351
  Serial.begin(9600);// Serial.begin(115200);//
  si5351.init(SI5351_CRYSTAL_LOAD_10PF, 0, XtalErr);//si5351.init(SI5351_CRYSTAL_LOAD_8PF, 0, XtalErr);
  si5351.set_ms_source(SI5351_CLK0, SI5351_PLLA);
  si5351.set_ms_source(SI5351_CLK1, SI5351_PLLA);
  si5351.set_ms_source(SI5351_CLK2, SI5351_PLLB);
  si5351.set_clock_invert(SI5351_CLK0, 0);
  si5351.set_clock_invert(SI5351_CLK1, 1);
  si5351.set_phase(SI5351_CLK0, 0);
  si5351.set_phase(SI5351_CLK1, 0);
  si5351.drive_strength(SI5351_CLK0, SI5351_DRIVE_2MA); //SI5351_DRIVE_2MA ; SI5351_DRIVE_4MA ; SI5351_DRIVE_8MA
  si5351.drive_strength(SI5351_CLK1, SI5351_DRIVE_2MA);
  si5351.drive_strength(SI5351_CLK2, SI5351_DRIVE_8MA);// Tx Clock
  si5351.set_clock_disable(SI5351_CLK2, SI5351_CLK_DISABLE_LOW); //enum si5351_clock_disable {SI5351_CLK_DISABLE_LOW, SI5351_CLK_DISABLE_HIGH, SI5351_CLK_DISABLE_HI_Z, SI5351_CLK_DISABLE_NEVER};

  //  if(FreqMult>126) FreqMult=126;
  //  si5351.set_phase(SI5351_CLK1, FreqMult);

  // We need to reset the PLL before they will be in phase alignment
  si5351.pll_reset(SI5351_PLLA);

  pinMode(KeyPin, INPUT_PULLUP);
  pinMode(PTTPin, OUTPUT);
  pinMode(A0, OUTPUT);
  digitalWrite(A0, LOW);
  pinMode(A1, OUTPUT);
  digitalWrite(A1, LOW);
  pinMode(A2, OUTPUT);
  digitalWrite(A2, LOW);
  digitalWrite(PTTPin, LOW); //Set T/R Relay to receive
  //digitalWrite(10, HIGH);
  inputString.reserve(200);
  //RXcenterFreq = 3.59260e6; //80M WSPR freq
  RXcenterFreq = 3.980e6; //80M TN Phone Net
}

void loop()
{
  int KeyOpen = digitalRead(KeyPin);//read Morse Straight Key input pin; Will be high (or int 1) when SSmicro key input is open
  if ( MyserialEvent()) { // check micro serial port for activity
    //Serial.println(inputString);
    //Serial.println(": QUISK msg String"); //echo back new rcvd instruction from QUISK
    if (!KeyActive) { // if the SSmcro is being actively manually keyed, ignore commands/signals coming from the computer
      String CMDstr = inputString.substring(0, 2);
      //String CMDptt = inputString.substring(0, 2);
      if ( CMDstr.equals("RF")) {
        inputString = inputString.substring(2);
        RXcenterFreq = inputString.toFloat();
        inputString = "";
        SetRX = true;
        if (SetRX) {
          sendFrequency(RXcenterFreq);
          SetRX = false;
        }
        //Serial.print("Clock0/1 (RX) Freq: ");
        //Serial.println(RXcenterFreq);
      }
      else if ( CMDstr.equals("TX")) {
        inputString = inputString.substring(2);
        TXfreq = inputString.toFloat();
        inputString = "";
        //Serial.println(TXfreq);
      }
      else if (inputString.substring(0, 5).equals("PTTON")) {
        inputString = "";
        if (!DlyIntrvl) {//if (!timesUP) {
          PTT = true;
          //DldPTToff = false;//20201230 commented out
          if (!DlyIntrvl) KeyOpen = 1;//if (!timesUP) KeyOpen = 1; // if we don't have an active data stream, Force key input to look open at onset of ptt going active
          //Serial.println("Set PTT = True");
          digitalWrite(PTTPin, HIGH);  //Set T/R Relay to Transmit position
        }
      }
      else if (inputString.substring(0, 6).equals("PTTOFF")) {
        inputString = "";
        if (!DlyIntrvl) {//if (!timesUP) {
          PTT = false;//20201229 added
        }
      }
      else if (inputString.substring(0, 2).equals("KS")) { // found info related to cw keying sent by host computer (QUISK) via USB serial port
        // concatenate new keying command(s) with existing stream data
        // 1st, Find the last cmd in the key data buffer
        //Serial.println(inputString);
        int KSptr;
        for (KSptr = 0; KSptr < 510; KSptr++) {
          if ( KeyStream[KSptr] == 0) break;
        }
        // now starting at the index ptr just past the the last command, copy in the new set of commands
        for (int i = 2; i < inputString.length(); ++i) {
          KeyStream[KSptr++] = inputString[i];
          if (!inputString[i]) break;
          if (KSptr >= 509) {
            Serial.println("!!!!BUFFER OVERFLOW!!!!");
            for (KSptr = 0; KSptr < 510; KSptr++) {
              KeyStream[KSptr] = 0;
            }
            break;
          }
        }
        KeyStream[509] = 0;
        inputString = "";// clr the usb serial text buffer for next serial message
        ///Serial.println(KeyStream); //echo back current CW Key command data buffer
      }
      else stringComplete = false;
      inputString = "";
    }
    else {

      inputString = "";
    }
  }//end if Stringcomplete is true
  else if (KeyStream[0] == 0) { //Only look at external manual key signals when no active streaming is being processed
    //Start Manual keying  /////////////////////////////////////////////////////////////////////////////////////////////////////
    if (!KeyOpen) { // looks like SSMicro/Radio is being manually keyed by an external key
      //KeyDown

      if (contactcntr > 0 & KeyClosed) contactcntr = 0; //Contact DeBounce reset
      contactcntr += 1;
      if (contactcntr > 15) { //Contact DeBounce check/pass
        contactcntr = 0;
        //       if(true){
        // First, place TR relay in TX position
        if (!PTT) { //if T/R relay is not in the TX position, Give it a chance to pickup before applying carrier
          unsigned long trwait = 5 + millis();
          while (millis() < trwait) {

            digitalWrite(PTTPin, HIGH);  //Set T/R Relay to Transmit position
            PTT = true;
          }
          DlyIntrvl = 0; //timesUP = 0;
        }
        //Next, notify QUISK of external KeyDown State (Mainly to kill the receiver)
        Serial.println("KEYDWN");
        if (!KeyClosed) {
          //SetRX = false;
          StartTX();
          //          if(KeyClosed) Serial.println("KEYDWN");
          KeyActive = true;
        }
      }
    }
    else { //Manual KeyUp
      if (contactcntr > 0 & !KeyClosed) contactcntr = 0; //Contact DeBounce reset
      contactcntr += 1;
      if (contactcntr > 15) { //Contact DeBounce check/pass
        contactcntr = 0;
        if (KeyClosed) {
          StopTX(); // Turn Tx Off;
          //Serial.println("KEYUP");//no longer needed
          DlyIntrvl = 300000;
          lastTime = micros();

        }
      }
      if (!KeyClosed && (((unsigned long)(micros() - lastTime) >= DlyIntrvl)) && DlyIntrvl && KeyActive) { //Added the 'KeyActive" to ensure this code does not operate while streaming CW keying via QUISK/FLDIGI
        DlyIntrvl = 0;
        PTT = false;
        KeyActive = false;
        digitalWrite(PTTPin, LOW);  //Return T/R Relay to RX position after delay
        Serial.println("KEYUP");
      }
    }
  }//End Manual Keying ////////////////////////////////////////////////////////////////////////////////////////////////////////////////

  if (!KeyActive ) { // Manage Streaming keying here
    checkTime();// if needed checktime will do "getNxtKeyStroke()";
    if (!PTT && !KeyClosed && !DlyIntrvl && digitalRead(PTTPin)) {//KeyClosed flag changes to true with first application of StartTX()//// & StopTX() functions
      digitalWrite(PTTPin, LOW);  //Set T/R Relay to Receive position
      //Serial.println("TR = RX mode");
    }
  }// End Streaming keying
} //End main Loop
/////////////////////////////////////////////////////////////////////////////
bool MyserialEvent() {
  bool stringComplete = false;

  while (Serial.available() && !stringComplete ) {
    // get the new byte:
    char inChar = (char)Serial.read();
    // if the incoming character is a 'Carrage Return', set a flag
    // so the main loop can do something about it:
    if (inChar == '\r') {
      stringComplete = true;
      Serial.flush();
    }
    else {
      inputString += inChar;  // add it to the inputString:

    }
    if (DlyIntrvl) checkTime(); // if streaming keying is active check to see whats going on.
  }
  return stringComplete;
}
/////////////////////////////////////////////////////////////////////////////
void sendFrequency(float HzFreq) {

  float KhzFreq = (HzFreq) / 1000;
  int FreqMult = 0;
  int PllFrq = 0; // in Mhz
  int ClkMult = 0;
  int PllLoLim = 400;
  if ( KhzFreq > 4800) PllLoLim = 600;
  if (SetRX) {
    Serial.print("Clock Freq: ");
    Serial.print( KhzFreq);
    Serial.println("Khz");
    //Set appropriate TX low pass filter via 2 bit input to 74145 BCD to Decimal converter
    //Band0
    if (KhzFreq < 6000) { //80 meters; lowest freg low pass filter
      digitalWrite(A0, LOW);
      digitalWrite(A1, LOW);
      digitalWrite(A2, LOW);
    }
    //Band1
    if (KhzFreq < 8000 && KhzFreq >= 6000) { //40 meters
      digitalWrite(A0, HIGH);
      digitalWrite(A1, LOW);
      digitalWrite(A2, LOW);
    }
    //Band3
    if (KhzFreq < 12000 && KhzFreq >= 8000) { //30 meters
      digitalWrite(A0, HIGH);
      digitalWrite(A1, HIGH);
      digitalWrite(A2, LOW);
    }
    //Band2
    if (KhzFreq >= 12000 && KhzFreq < 16000) { //20 meters
      digitalWrite(A0, LOW);
      digitalWrite(A1, HIGH);
      digitalWrite(A2, LOW);
    }
    //Band4
    if (KhzFreq >= 16000 && KhzFreq < 19500) { //17 meters
      digitalWrite(A0, LOW);
      digitalWrite(A1, LOW);
      digitalWrite(A2, HIGH);
    }
    //Band5
    if (KhzFreq >= 19500 && KhzFreq < 22500) { //15 meters
      digitalWrite(A0, HIGH);
      digitalWrite(A1, LOW);
      digitalWrite(A2, HIGH);
    }
    //Band6
    if (KhzFreq >= 22500 && KhzFreq < 26000) { //12 meters
      digitalWrite(A0, LOW);
      digitalWrite(A1, HIGH);
      digitalWrite(A2, HIGH);
    }
    //Band7
    if (KhzFreq >= 26000) { //10 meters; highest freg low pass filter
      digitalWrite(A0, HIGH);
      digitalWrite(A1, HIGH);
      digitalWrite(A2, HIGH);
    }
  }
  while ((PllFrq < 900) && (PllFrq < PllLoLim || FreqMult & 1 == 1 || ClkMult & 1 == 1) ) {
    FreqMult++;
    PllFrq = FreqMult * (KhzFreq / 1000);
    ClkMult = PllFrq / 25;
  }


  unsigned long long freq_2Decml = (KhzFreq * 100000)   ; //1410000000ULL;
  unsigned long long pll_freq = freq_2Decml * FreqMult; //70500000000ULL;
  if (SetRX) {
    Serial.print("FreqMult: ");
    Serial.print( FreqMult);
    Serial.print(";  PllFrq: ");
    Serial.print( PllFrq);
    Serial.print("Mhz; ");
    Serial.print(";  Pll_Frq: ");
  }
  HiVal = (unsigned long)(pll_freq / 1000000);
  LoVal = (unsigned long)(pll_freq - (HiVal * 1000000));
  if (pll_freq > 0xFFFFFFFFLL) sprintf(buf, "%ld %06ld" ,  (unsigned long)HiVal, (unsigned long)LoVal );
  else sprintf(buf, "%ld", (unsigned long)pll_freq);
  if (SetRX) {
    Serial.print( buf);
    Serial.print("Hz; ");
    Serial.print( FreqMult);
    Serial.print(";  ClkMult: ");
    Serial.print( ClkMult);
    Serial.println("");

    // Set CLK0 and CLK1 to use PLLA as the MS source.
    // This is not explicitly necessary in v2 of this library,
    // as these are already the default assignments.
    // si5351.set_ms_source(SI5351_CLK0, SI5351_PLLA);
    // si5351.set_ms_source(SI5351_CLK1, SI5351_PLLA);
    si5351.set_pll(pll_freq , SI5351_PLLA);
    // Set CLK0 and CLK1 to output 14.1 MHz with a fixed PLL frequency
    si5351.set_freq_manual(freq_2Decml, pll_freq, SI5351_CLK0);
    si5351.set_freq_manual(freq_2Decml, pll_freq, SI5351_CLK1);
    if (FreqMult > 126) FreqMult = 126;
    si5351.set_phase(SI5351_CLK0, FreqMult);//si5351.set_phase(SI5351_CLK1, 0);
    // We need to reset the PLL before they will be in phase alignment
    si5351.pll_reset(SI5351_PLLA);
  }

  if (SetTX) {
    si5351.set_pll(pll_freq , SI5351_PLLB);
    si5351.set_freq_manual(freq_2Decml, pll_freq, SI5351_CLK2);
  }
}// end sendFrequency() Function
//////////////////////////////////////////////////////////

void StartTX(void) {
  if (!KeyClosed) { // Turn Tx On
    si5351.output_enable(SI5351_CLK0, 0);
    si5351.output_enable(SI5351_CLK1, 0);
    SetTX = true;
    if (TXfreq >= 3500000.0) sendFrequency(TXfreq);//don't activate TX RF below 80 mtrs
    SetTX = false;
    //Serial.println("StartTX()");
    KeyClosed = true;
  }
}
//////////////////////////////////////////////////////////

void StopTX(void) {
  if (KeyClosed) { // Turn Tx Off
    si5351.output_enable(SI5351_CLK2, 0);// disable xmit clock/oscillator.
    si5351.output_enable(SI5351_CLK0, 1);// Activate I phase RX clock/oscillator
    si5351.output_enable(SI5351_CLK1, 1);// Activate Q phase RX clock/oscillator
    KeyClosed = false;
  }
}
//////////////////////////////////////////////////////////

void checkTime() {
  // How much time has passed, accounting for rollover with subtraction!
  if (DlyIntrvl == 0) {
    getNxtKeyStroke(0);
    return;
  }
  unsigned long CurIntrvl = (unsigned long)(micros() - lastTime);
  if (CurIntrvl >= DlyIntrvl) {
    // It's time to do something!
    getNxtKeyStroke(CurIntrvl - DlyIntrvl);
    return;
  } else return; //Serial.println("tryagain");
}
//////////////////////////////////////////////////////////

// unpack Keystroke buffer/FIFO one element at time; set TX output (ON/OFF) per command, & set "timeout" variable to the clock value signifying the end of this current command
//this function also adjusts the base duration interval to compensate for how "deep" the buffer que is and by how much it missed the last time stamp.
void getNxtKeyStroke(unsigned long lateTime) {
  boolean KyUpFlg = false;
  boolean KyDwnFlg = false;
  boolean Active = false;
  if (KeyStream[0] > 0) {
    Active = true;

    //        if(timesUP>0){
    //          Serial.print("TIMEDELTA: ");
    //          Serial.println(millis()-timesUP);
    //        }
    int keycmd = int(KeyStream[0]);
    if (keycmd > 90) { // key "UP" or "Open" signal
      spd = keycmd - 90; //convert keyUp command to its WPM value
      KyUpFlg = true;
      StopTX();
      if (KyDwnTime > 0) {
        //Serial.println(KyDwnTime);
        KyDwnTime = 0;
      }

    }
    else { // its a "keydown" command
      KyDwnFlg = true;

      if (!PTT) {// make sure the TR relay is set to transmitt before applying RF
        digitalWrite(PTTPin, HIGH);  //Set T/R Relay to Transmit position
        Serial.println("Forced PTT ON");
        delay(20);// wait for relay to operate
        PTT = true;
      }
      loopcnt = 0;
      spd = keycmd - 40; //convert keydown command to its WPM value
      StartTX();
      KyDwnTime += SpdTbl[spd].Intrvl;
    }

    unsigned long dlyInt = SpdTbl[spd].Intrvl; //convert this spd to the number of microseconds the standard interval needs to presist
    unsigned long KyUpIntrvl = 0;
    long DlyIntMs;
    DlyIntrvl = dlyInt + BufAdj - lateTime;
    if (DlyIntrvl < 7500) DlyIntrvl = 7500;
    lastTime = micros();
    int KSptr = 0;
    int KyUpCnt = 0;
    bool CntKyUp = true;
    //shift the buffer one position to the left, and while you're at, collect the info needed to calc how long the keyup event will last
    for (KSptr = 1; KSptr < 510; KSptr++) {
      KeyStream[KSptr - 1] = KeyStream[KSptr];
      if ((KeyStream[KSptr] > 90) && CntKyUp) { //20201229 added
        KyUpIntrvl += dlyInt + BufAdj; //20201229 added
        KyUpCnt++;
      } else if (KeyStream[KSptr]) CntKyUp = false; //20201229 added; found a keydwn event yet to be processed in buffer
      if ( KeyStream[KSptr] == 0) break; //20201229 added
    }
    if (KeyStream[0] == 0) Serial.println("*** BUFFER Zeroed ***");
    //if needed apply corrections interval timing for the current WPM
    AvgKSptr = ((19 * AvgKSptr) + KSptr) / 20;
    KSptr = AvgKSptr;

    if (KSptr < SpdTbl[spd].BufDpth && AdjDur) { // AdjDur = "false" should inhibit timining corrections for single letter enteries
      if (OldBufLen > KSptr) BufAdj += SpdTbl[spd].Inc; // we're still going too fast; need to slow down a bit
      if (OldBufLen < KSptr) BufAdj -= SpdTbl[spd].Dec;
      if (BufAdj > 0){
        BufAdj = 0;
        AdjDur = false;
      }
    } else if (KSptr > SpdTbl[spd].BufDpth) {
      //KSptr = AvgKSptr;
      if (OldBufLen < KSptr) BufAdj -= SpdTbl[spd].Inc; // we're still falling behind; need to Speed up a bit
      if (OldBufLen > KSptr) BufAdj += SpdTbl[spd].Dec; //we're gaining on the buffer, so we can slow down a bit
      if ((dlyInt + BufAdj) < 7500) BufAdj += 10; // don't reduce interval to something less than a speed > 40WPM
      AdjDur = true;
    }
    OldBufLen = KSptr; //remember how deep the Buffer is;

//    Serial.print("spd: ");
//    Serial.print(spd);
    //Serial.print("; ");
    //    Serial.print("lateTime: ");
    //    Serial.print(lateTime);
//    Serial.print("DotLen: ");
//    Serial.print((4*DlyIntrvl)/1000);
//    Serial.print("; BufAdj: ");
//    Serial.print(BufAdj);
//    Serial.print("; KSptr: ");
//    Serial.print(KSptr);
//    if(KyUpFlg) Serial.println(" OFF");
//    if(KyDwnFlg) Serial.println(" ON");
    if (DlyIntrvl > 16000) { // for the Key Up intervals are greater than 16ms, make keyup keydwn decisions based on the key number of keyup intervals remaining
      if (KyUpCnt > 1) {
        //Serial.println("^^^^^ ");
        SetPTT(false); //(KyUpFlg, KyDwnFlg)
      } else if (!CntKyUp) { //there are more intervals to process, but the next one is a keydwn event so prepare the TR relay to switch to transmitt position
        SetPTT(true);//New Keydown event is about to happen, So need to prep the T/R relay to get back in TX position before we need to apply RF
      }
    }//end intervals >16 ms logic
    else { // start tr decision process where interval timing is <16ms
      if (KyUpIntrvl > 60000) { //KyUpIntrvl //(dlyInt+BufAdj)*KyUpCnt
        SetPTT(false); //(KyUpFlg, KyDwnFlg);
      } else if ((KyUpIntrvl < 20000) && !CntKyUp) { //if(!CntKyUp && (KyUpIntrvl>0)){ //the Key up time is now < 20 ms, an there is a keydwn event coming, so prepare the TR relay to switch back to transmitt position
        SetPTT(true);//New Keydown event is about to happen, So need to prep the T/R relay to get back in TX position before we need to apply RF
      }
    }//END tr decision process for intervals <16ms
  }//end processing active key stream buffer
  else { //nothing currently in key stream buffer
    //timesUP = 0; // The CW Key command data buffer is empty; clr the timesUP variable
    lastTime = 0;
    DlyIntrvl = 0;
    AdjDur = false;
    BufAdj = 0;
    DldPTTon = true;
    DldPTToff = true;
    if (PTT) { //if 'Active' isn't "true", then this clean-up should not be needed; added the 'Active' flag to prevent clring the PTT flag (which is normally set before keying data is sent)
      StopTX();// we should not be transmitting, but double check
      KeyClosed = false;
      digitalWrite(PTTPin, LOW);  //Set T/R Relay to receive position
      PTT = false;
      Serial.println("timesUP");
      Serial.println("KEYUP");
    }
  }
}// end getNxtKeyStroke() Function

//////////////////////////////////////////////////////////

void SetPTT(bool KyDwnFlg) {//(bool KyUpFlg, bool KyDwnFlg)

  //  Serial.print("KyDwnFlg=");
  //  if (KyDwnFlg) Serial.print("1 ;");
  //  else Serial.print("0 ;");
  //  Serial.print("DldPTTon=");
  //  if (DldPTTon) Serial.print("1 ;");
  //  else Serial.print("0 ;");
  //  Serial.print("DldPTToff=");
  //  if (DldPTToff) Serial.println("1 ;");
  //  else Serial.println("0 ;");

  if (!KyDwnFlg && DldPTToff) {
    digitalWrite(PTTPin, LOW);//20201229 added//Set T/R Relay to RX position if it appears that the KeyUp state is going to presist for more than 60ms
    //Serial.println("TR = RX mode");
    Serial.println("KEYUP");//20201229 added
    //          Serial.println("****");//20201229 added
    PTT = false;
    DldPTTon = true;
    DldPTToff = false;//20201229 added
  } else if (KyDwnFlg && DldPTTon) {
    digitalWrite(PTTPin, HIGH);//20201229 added//Set T/R Relay to RX position if it appears that the KeyUp state is going to presist for more than 60ms
    //Serial.println("TR = RX mode");
    Serial.println("KEYDWN");//20201229 added
    PTT = true;
    DldPTTon = false;
    DldPTToff = true;
  }
}

//////////////////////////////////////////////////////////
uint64_t pll_calc(enum si5351_pll pll, uint64_t freq, struct Si5351RegSet *reg, int32_t correction, uint8_t vcxo)
{
  uint64_t ref_freq;
  if (pll == SI5351_PLLA)
  {
    ref_freq = SI5351_XTAL_FREQ * SI5351_FREQ_MULT;
  }
  else
  {
    ref_freq = SI5351_XTAL_FREQ * SI5351_FREQ_MULT;
  }
  //ref_freq = 15974400ULL * SI5351_FREQ_MULT;
  uint32_t a, b, c, p1, p2, p3;
  uint64_t lltmp; //, denom;

  // Factor calibration value into nominal crystal frequency
  // Measured in parts-per-billion

  ref_freq = ref_freq + (int32_t)((((((int64_t)correction) << 31) / 1000000000LL) * ref_freq) >> 31);

  // PLL bounds checking
  if (freq < 600000000 * SI5351_FREQ_MULT)//SI5351_PLL_VCO_MIN=600000000; SI5351_FREQ_MULT =100ULL
  {
    freq = SI5351_PLL_VCO_MIN * SI5351_FREQ_MULT;
  }
  if (freq > SI5351_PLL_VCO_MAX * SI5351_FREQ_MULT)
  {
    freq = SI5351_PLL_VCO_MAX * SI5351_FREQ_MULT;
  }
  Serial.print("pll_calc freq: ");
  //Serial.print( freq);
  HiVal = (unsigned long)(freq / 1000000);
  LoVal = (unsigned long)(freq - (HiVal * 1000000));
  if (freq > 0xFFFFFFFFLL) sprintf(buf, "%ld %06ld" ,  (unsigned long)HiVal, (unsigned long)LoVal );
  else sprintf(buf, "%ld", (unsigned long)freq);
  Serial.print( buf);
  Serial.print("; ");
  // Determine integer part of feedback equation
  a = freq / ref_freq;

  if (a < SI5351_PLL_A_MIN) //SI5351_PLL_A_MIN =15
  {
    freq = ref_freq * SI5351_PLL_A_MIN;
  }
  if (a > SI5351_PLL_A_MAX)  //SI5351_PLL_A_MAX =90
  {
    freq = ref_freq * SI5351_PLL_A_MAX;
  }

  // Find best approximation for b/c = fVCO mod fIN
  // denom = 1000ULL * 1000ULL;
  // lltmp = freq % ref_freq;
  // lltmp *= denom;
  // do_div(lltmp, ref_freq);

  //b = (((uint64_t)(freq % ref_freq)) * RFRAC_DENOM) / ref_freq;
  if (vcxo)
  {
    b = (((uint64_t)(freq % ref_freq)) * 1000000ULL) / ref_freq;
    c = 1000000ULL;
  }
  else
  {
    b = (((uint64_t)(freq % ref_freq)) * RFRAC_DENOM) / ref_freq;
    c = b ? RFRAC_DENOM : 1;
  }

  // Calculate parameters
  p1 = 128 * a + ((128 * b) / c) - 512;
  p2 = 128 * b - c * ((128 * b) / c);
  p3 = c;

  // Recalculate frequency as fIN * (a + b/c)
  lltmp = ref_freq;
  lltmp *= b;
  do_div(lltmp, c); // defined in the  "si5351.h" header file
  freq = lltmp;
  freq += ref_freq * a;

  reg->p1 = p1;
  reg->p2 = p2;
  reg->p3 = p3;

  if (vcxo)
  {
    return (uint64_t)(128 * a * 1000000ULL + b);
  }
  else
  {
    return freq;
  }
}
