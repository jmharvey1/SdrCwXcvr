# This is a config file to test the microphone by sending microphone Tx playback to the audio out.
# Set the frequency to zero, and press FDX and PTT.
# Set these values for DEBUG_MIC in sound.c:
# 0:  Normal FFT.
# 1:  Send filtered Tx audio to the FFT.
# 2:  Send mic playback to the FFT.
# 3:  Send unfiltered mono mic audio to the FFT.

import sys
from quisk_hardware_model import Hardware as BaseHardware
import _quisk as QS

from n2adr.quisk_conf import n2adr_sound_pc_capt, n2adr_sound_pc_play, n2adr_sound_usb_play, n2adr_sound_usb_mic
from n2adr.quisk_conf import latency_millisecs, data_poll_usec, favorites_file_path
from n2adr.quisk_conf import mixer_settings

settings_file_path = "../quisk_settings.json"

name_of_sound_capt = n2adr_sound_pc_capt
name_of_sound_play = ''
microphone_name = n2adr_sound_usb_mic
name_of_mic_play = n2adr_sound_usb_play

graph_y_scale = 160

mic_sample_rate = 48000

sample_rate = 48000
mic_playback_rate = 48000
mic_out_volume = 0.6
add_fdx_button = 1

class Hardware(BaseHardware):
  def __init__(self, app, conf):
    BaseHardware.__init__(self, app, conf)
    self.use_sidetone = 1
  def OnButtonPTT(self, event):
    if event.GetEventObject().GetValue():
      QS.set_key_down(1)
    else:
      QS.set_key_down(0)
