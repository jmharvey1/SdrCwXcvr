/*
 * JMH 20190911
 * Reworked portions of this sketch to improve support the use of external manual keying
 * JMH 20190815
 * Added pin A2 to band selection scheme to support 8 band change (80 through 10 meters)
 * JMH 20180709
 * Revised sketch to include support for CW Key Stroke keying via USB serial port; On the computer side using modified versions of QUISK & FLDIGI to generate & send the data stream
 * JMH 20180514
 * modified to lockout ptt off command if carrier is on at the time the command is recieved via the serial port; this is to allow the last code symbol to complete before reating to the command
 * 
 *sketch written by Jim Harvey (KW4KD) 20180601 
 * parts of this sketch may contain code written by: Jason Milldrum as well as other unknown sources
 *  Copyright (C) 2015 - 2016 Jason Milldrum <milldrum@gmail.com>
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

/*
 * Setting the phase of a clock requires that you manually set the PLL and
 * take the PLL frequency into account when calculation the value to place
 * in the phase register. As shown on page 10 of Silicon Labs Application
 * Note 619 (AN619), the phase register is a 7-bit register, where a bit
 * represents a phase difference of 1/4 the PLL period. Therefore, the best
 * way to get an accurate phase setting is to make the PLL an even multiple
 * of the clock frequency, depending on what phase you need.
 *
 * If you need a 90 degree phase shift (as in many RF applications), then
 * it is quite easy to determine your parameters. Pick a PLL frequency that
 * is an even multiple of your clock frequency (remember that the PLL needs
 * to be in the range of 600 to 900 MHz). Then to set a 90 degree phase shift,
 * you simply enter that multiple into the phase register. Remember when
 * setting multiple outputs to be phase-related to each other, they each need
 * to be referenced to the same PLL.
 */

#include "si5351.h"
#include "Wire.h"
#define KeyPin 11 //input signal
#define PTTPin 10 //output signal

Si5351 si5351;
char buf[50];
char KeyStream[255];
unsigned long HiVal;
unsigned long LoVal;
String inputString = "";         // a string to hold incoming data
boolean stringComplete = false;  // whether the string is complete
boolean SetRX = false;
boolean SetTX = false;
boolean KeyClosed = false;
boolean PTT = false;
boolean DldPTToff = false;
boolean KeyActive = false; //Used to recognize external manual keying activity
int contactcntr =0;
int spd =0;
int loopcnt = 0;   //delays turning off at the end of what had been a period of active streaming of key data commands
//boolean TXRFON = false;
float RXcenterFreq = 0.0;
float TXfreq = 0.0;
unsigned long timesUP = 0; 
int XtalErr = -9500; // integer value measured to 0.01 Hertz ie 100 = 1.00Hz

void setup()
{
  // Start serial and initialize the Si5351
  Serial.begin(9600);
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
   if ( MyserialEvent()){  // check micro serial port for activity
      Serial.print(inputString);
      Serial.println(": QUISK msg String"); //echo back new rcvd instruction from QUISK
      if(!KeyActive){ // if the SSmcro is being actively manually keyed, ignore commands/signals coming from the computer
        String CMDstr = inputString.substring(0, 2);
        //String CMDptt = inputString.substring(0, 2);
        if( CMDstr.equals("RF")){
          inputString = inputString.substring(2);
          RXcenterFreq = inputString.toFloat();
          SetRX = true;
          if(SetRX){
            sendFrequency(RXcenterFreq);
            SetRX = false;
          }
          Serial.print("Clock0/1 (RX) Freq: ");
          Serial.println(RXcenterFreq);
        }
        else if( CMDstr.equals("TX")){
          inputString = inputString.substring(2);
          TXfreq = inputString.toFloat();
          Serial.println(TXfreq);
        }
        else if(inputString.substring(0, 5).equals("PTTON")){
          inputString = "";
          PTT = true;
          DldPTToff = false;
          if(!timesUP) KeyOpen = 1; // if we don't have an active data stream, Force key input to look open at onset of ptt going active
          Serial.println("Set PTT = True");
          digitalWrite(PTTPin, HIGH);  //Set T/R Relay to Transmit position
        }
        else if(inputString.substring(0, 6).equals("PTTOFF")){
          inputString = "";
          if(KeyStream[0]){
            int KSptr;
            bool kydwn = false;
            for (KSptr = 0; KSptr < 255; KSptr++) {
              if( KeyStream[KSptr]==0) break;
            }
            for (int i = 0; i < KSptr; i++) {
              if( KeyStream[i]<90) kydwn = true;
            }
            if(kydwn){
              DldPTToff = true;
              Serial.println("Set DldPTToff = true");
              Serial.print("WPM: ");
              Serial.println(spd);
            }
            else{
              PTT = false;
              Serial.println("Set PTT = False Active stream bt no keydwn data");
              Serial.print("WPM: ");
              Serial.println(spd);
            }
          }
          else{ 
            PTT = false;
            Serial.println("Set PTT = False");
            Serial.print("WPM: ");
            Serial.println(spd);
          }
          
          //digitalWrite(PTTPin, LOW);  //Set T/R Relay to receive; defer this action until the keyclosed manual input goes high or the stream data sends a key high command
        }
        else if(inputString.substring(0, 2).equals("KS")){ // found info related to cw keying sent by host computer (QUISK) via USB serial port
          // concatenate new keying command(s) with existing stream data
          // 1st, Find the last cmd in the key data buffer
          int KSptr;
          for (KSptr = 0; KSptr < 255; KSptr++) {
            if( KeyStream[KSptr]==0) break;
          }
          // now starting at the index ptr just past the the last command, copy in the new set of commands
          for (int i = 2; i < inputString.length(); ++i) {
            KeyStream[KSptr++] = inputString[i];
            if(!inputString[i]) break;
            if(KSptr>=254) break;
          }
          KeyStream[254]= 0;
          inputString = "";// clr the usb serial text buffer for next serial message
          ///Serial.println(KeyStream); //echo back current CW Key command data buffer
        }
        else stringComplete = false;
        inputString = "";
      }
      else{
        
        inputString = "";
      }
   }//end if Stringcomplete is true
   else if(KeyStream[0]== 0){ //Only look at external manual key signals when no active streaming is being processed
    //Start Manual keying  /////////////////////////////////////////////////////////////////////////////////////////////////////
    if(!KeyOpen){ // looks like SSMicro/Radio is being manually keyed by an external key
      //KeyDown
      
      if(contactcntr >0 & KeyClosed) contactcntr =0; //Contact DeBounce reset
      contactcntr +=1;
      if(contactcntr >15){ //Contact DeBounce check/pass
        contactcntr =0;
//       if(true){
        // First, place TR relay in TX position
        if (!PTT){ //if T/R relay is not in the TX position, Give it a chance to pickup before applying carrier
          timesUP = 5+millis();
          while (millis() < timesUP) {
            digitalWrite(PTTPin, HIGH);  //Set T/R Relay to Transmit position
            PTT = true;
          }
          timesUP =0;
        }
        //Next, notify QUISK of external KeyDown State (Mainly to kill the receiver)
        Serial.println("KEYDWN");
        if(!KeyClosed){
          //SetRX = false;
          StartTX();
//          if(KeyClosed) Serial.println("KEYDWN");
          KeyActive = true;
        }
      }
    }
    else{ //Manual KeyUp
//      if(PTT){
//        Serial.print("cntr: ");
//        Serial.print(contactcntr);
//        Serial.print(";\ttimesUP: ");
//        Serial.print(timesUP);
//        Serial.print(";\tKeyActive: ");
//        if(KeyActive)Serial.println("TRUE");
//        else Serial.println("FALSE");
//      }
      if(contactcntr >0 & !KeyClosed) contactcntr =0; //Contact DeBounce reset
      contactcntr +=1;
      if(contactcntr >15){ //Contact DeBounce check/pass
        contactcntr =0; 
        if(KeyClosed){
          timesUP =0;
          StopTX(); // Turn Tx Off; 
          //Serial.println("KEYUP");
          timesUP = 300+millis();
        }
      }
      if(!KeyClosed & (millis()>timesUP) & (timesUP!=0) & KeyActive){//Added the 'KeyActive" to ensure this code does not operate while streaming CW keying via QUISK/FLDIGI 
        timesUP =0;
        PTT = false;
        KeyActive = false;
        digitalWrite(PTTPin, LOW);  //Return T/R Relay to RX position after delay
        Serial.println("KEYUP");
      }
    }
   }//End Manual Keying ////////////////////////////////////////////////////////////////////////////////////////////////////////////////
   
   if(!KeyActive ){ // Manage Streaming keying here
       if(timesUP){
        if(millis()>timesUP)// we have been working with active usb cw keying data; its now time go check to see what to do next (cw keying wise)
        { 
         getNxtKeyStroke(true);
        }
       }
       else getNxtKeyStroke(false); //Keystroke buffer has been empty; But Need to check and see if that's still the case
       
       if(!PTT && !KeyClosed) KeyOpen = 1; // if not transmitting [ie; ptt not closed & No RF carrier], ingnore key input state.
       if(KeyOpen && !timesUP){
        //Serial.println("KEYUP");
        StopTX(); // Turn Tx Off; timesUP=0 indicates no active streaming keying command; this is needed here to support external manual keying; same test/function is launched in "getNxtKeyStroke" routine
       }
       if(!PTT && !KeyClosed) digitalWrite(PTTPin, LOW);  //Set T/R Relay to Receive position
   }
} //End main Loop
/////////////////////////////////////////////////////////////////////////////
bool MyserialEvent() {
  bool stringComplete = false;
  
  while (Serial.available() ) {
    // get the new byte:
    char inChar = (char)Serial.read();
    // if the incoming character is a 'Carrage Return', set a flag
    // so the main loop can do something about it:
    if (inChar == '\r') {
      stringComplete = true;
    }
    else inputString += inChar;  // add it to the inputString:
  }
  return stringComplete;
}
/////////////////////////////////////////////////////////////////////////////
void sendFrequency(float HzFreq) {
  
  float KhzFreq = (HzFreq)/1000; 
  int FreqMult = 0;
  int PllFrq = 0; // in Mhz
  int ClkMult = 0;
  int PllLoLim = 400;
  if( KhzFreq> 4800) PllLoLim = 600;
  if(SetRX){
   Serial.print("Clock Freq: ");
   Serial.print( KhzFreq);
   Serial.println("Khz");
   //Set appropriate TX low pass filter via 2 bit input to 74145 BCD to Decimal converter
   //Band0
   if (KhzFreq < 6000){ //80 meters; lowest freg low pass filter
    digitalWrite(A0, LOW);
    digitalWrite(A1, LOW);
    digitalWrite(A2, LOW);  
   }
   //Band1
    if (KhzFreq < 8000 && KhzFreq >= 6000){ //40 meters
    digitalWrite(A0, HIGH);
    digitalWrite(A1, LOW);
    digitalWrite(A2, LOW);  
   }
   //Band3
   if (KhzFreq < 12000 && KhzFreq >= 8000){ //30 meters
    digitalWrite(A0, HIGH);
    digitalWrite(A1, HIGH);
    digitalWrite(A2, LOW);  
   }
   //Band2
   if (KhzFreq >= 12000 && KhzFreq <16000){ //20 meters
    digitalWrite(A0, LOW);
    digitalWrite(A1, HIGH);
    digitalWrite(A2, LOW);  
   }
   //Band4
   if (KhzFreq >= 16000 && KhzFreq <19500){ //17 meters
    digitalWrite(A0, LOW);
    digitalWrite(A1, LOW);
    digitalWrite(A2, HIGH);  
   }
   //Band5
   if (KhzFreq >= 19500 && KhzFreq <22500){ //15 meters
    digitalWrite(A0, HIGH);
    digitalWrite(A1, LOW);
    digitalWrite(A2, HIGH);  
   }
   //Band6
   if (KhzFreq >= 22500 && KhzFreq <26000){ //12 meters
    digitalWrite(A0, LOW);
    digitalWrite(A1, HIGH);
    digitalWrite(A2, HIGH);  
   }
   //Band7
   if (KhzFreq >= 26000){ //10 meters; highest freg low pass filter
    digitalWrite(A0, HIGH);
    digitalWrite(A1, HIGH);
    digitalWrite(A2, HIGH);  
   }       
  } 
  while ((PllFrq<900)&&(PllFrq < PllLoLim || FreqMult & 1 ==1 || ClkMult & 1 ==1) ){
     FreqMult++;
     PllFrq = FreqMult* (KhzFreq/1000);
     ClkMult = PllFrq/25;
  }
 
  
  unsigned long long freq_2Decml = (KhzFreq * 100000)   ; //1410000000ULL;
  unsigned long long pll_freq = freq_2Decml * FreqMult; //70500000000ULL;
  if(SetRX){
   Serial.print("FreqMult: ");
   Serial.print( FreqMult);
   Serial.print(";  PllFrq: ");
   Serial.print( PllFrq);
   Serial.print("Mhz; ");
   Serial.print(";  Pll_Frq: ");
  }
  HiVal = (unsigned long)(pll_freq/1000000);
  LoVal = (unsigned long)(pll_freq -(HiVal*1000000));
  if(pll_freq> 0xFFFFFFFFLL) sprintf(buf, "%ld %06ld" ,  (unsigned long)HiVal, (unsigned long)LoVal );
  else sprintf(buf, "%ld", (unsigned long)pll_freq);
  if(SetRX){ 
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
    si5351.set_pll(pll_freq ,SI5351_PLLA);
    // Set CLK0 and CLK1 to output 14.1 MHz with a fixed PLL frequency
    si5351.set_freq_manual(freq_2Decml, pll_freq, SI5351_CLK0);
    si5351.set_freq_manual(freq_2Decml, pll_freq, SI5351_CLK1);
    if(FreqMult>126) FreqMult=126;
    si5351.set_phase(SI5351_CLK0, FreqMult);//si5351.set_phase(SI5351_CLK1, 0);
    // We need to reset the PLL before they will be in phase alignment
    si5351.pll_reset(SI5351_PLLA);
  }

  if(SetTX){ 
    si5351.set_pll(pll_freq ,SI5351_PLLB);
    si5351.set_freq_manual(freq_2Decml, pll_freq, SI5351_CLK2);
  }
}// end sendFrequency() Function
//////////////////////////////////////////////////////////

void StartTX(void){
  if(!KeyClosed){ // Turn Tx On
     si5351.output_enable(SI5351_CLK0, 0);
     si5351.output_enable(SI5351_CLK1, 0);
     SetTX = true;
     if(TXfreq>= 3500000.0) sendFrequency(TXfreq);
     SetTX = false;
     KeyClosed = true;
   }
}
//////////////////////////////////////////////////////////

void StopTX(void){
  if(KeyClosed){  // Turn Tx Off
      si5351.output_enable(SI5351_CLK2, 0);// disable xmit clock/oscillator.
      si5351.output_enable(SI5351_CLK0, 1);// Activate I phase RX clock/oscillator 
      si5351.output_enable(SI5351_CLK1, 1);// Activate Q phase RX clock/oscillator
      if(!timesUP) KeyClosed = false;// if we are NOT actively processing streaming keying data, reset this flag 
   }
}
//////////////////////////////////////////////////////////
void getNxtKeyStroke(bool Active) // unpack Keystroke buffer/FIFO one character at time; set TX output (ON/OFF) per command, & set next clock value for timeout of this current command 
{
  if(KeyStream[0]){
    //Serial.println(KeyStream); //echo back current CW Key command data buffer
    //Serial.print(KeyStream[0]);
    int keycmd = int(KeyStream[0]);
    if(keycmd>90){// key "UP" or "Open" signal
      keycmd = keycmd-90;//convert keyUp command to its WPM value
      if(DldPTToff){
        DldPTToff = false;
        PTT = false;
      }
      
      if(!PTT) digitalWrite(PTTPin, LOW);
      StopTX();
      KeyClosed = false;
      
    }
    else{ // its a "keydown" command
      if(!PTT){
        digitalWrite(PTTPin, HIGH);  //Set T/R Relay to Transmit position
        Serial.println("Forced PTT ON");
        delay(20);// wait for relay to operate
        PTT = true;
      }
      loopcnt =0;
      keycmd = keycmd-40;//convert keydown command to its WPM value
      //KeyClosed = true;
      StartTX();
    }
    //Serial.print("; WPM: ");
    //Serial.println(keycmd);
    int dlyftr = 1000;
    spd = keycmd;
    //if(keycmd==17) dlyftr = 900;
    keycmd = dlyftr/keycmd; //convert this keycmd to the number of milliseconds it needs to presist for
    timesUP = keycmd+millis(); 
    //sprintf(KeyStream, "%s", KeyStream.substring(1)); //shift the cw keycommand data buffer one data point to the left
    for (int KSptr = 1; KSptr < 255; KSptr++) {
      KeyStream[KSptr-1] = KeyStream[KSptr];
      if( KeyStream[KSptr]==0) break;
    } 
  }
  else{
//    if(PTT && Active && loopcnt <100){
//      loopcnt++;
//      delay(1);
//      //Serial.println(loopcnt);
//      return;
//    }
    timesUP = 0; // The CW Key command data buffer is empty; clr the timesUP variable
    if(PTT && Active){//if 'Active' isn't "true", then this clean-up should not be needed; added the 'Active' flag to prevent clring the PTT flag (which is normally set before keying data is sent)
        StopTX();// we should not be transmitting, but double check
        KeyClosed = false;
        digitalWrite(PTTPin, LOW);  //Set T/R Relay to receive position
        PTT = false;
        Serial.println("timesUP, Set PTT OFF");
      }
  }
}// end getNxtKeyStroke() Function

//////////////////////////////////////////////////////////
uint64_t pll_calc(enum si5351_pll pll, uint64_t freq, struct Si5351RegSet *reg, int32_t correction, uint8_t vcxo)
{
  uint64_t ref_freq;
  if(pll == SI5351_PLLA)
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
  HiVal = (unsigned long)(freq/1000000);
  LoVal = (unsigned long)(freq -(HiVal*1000000));
  if(freq> 0xFFFFFFFFLL) sprintf(buf, "%ld %06ld" ,  (unsigned long)HiVal, (unsigned long)LoVal );
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
  if(vcxo)
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

  if(vcxo)
  {
    return (uint64_t)(128 * a * 1000000ULL + b);
  }
  else
  {
    return freq;
  }
}
