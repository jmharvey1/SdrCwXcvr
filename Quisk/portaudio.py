#! /usr/bin/python

# Test for PortAudio devices using ctypes

from __future__ import print_function

import ctypes, ctypes.util

class PaDeviceInfo (ctypes.Structure):
  _fields_ = [
	('structVersion', ctypes.c_int),
	('name', ctypes.c_char_p),
	('hostApi', ctypes.c_int),							# PaHostApiIndex
	('maxInputChannels', ctypes.c_int),
	('maxOutputChannels', ctypes.c_int),
	('defaultLowInputLatency', ctypes.c_double),		# PaTime
	('defaultLowOutputLatency', ctypes.c_double),		# PaTime
	('defaultHighInputLatency', ctypes.c_double),		# PaTime
	('defaultHighOutputLatency', ctypes.c_double),		# PaTime
	('defaultSampleRate', ctypes.c_double),
	]

class PaHostApiInfo (ctypes.Structure):
  _fields_ = [
	('structVersion', ctypes.c_int),
	('type', ctypes.c_int),			# enum PaHostApiTypeId
	('name', ctypes.c_char_p),
	('deviceCount', ctypes.c_int),
	('defaultInputDevice', ctypes.c_int),
	('defaultOutputDevice', ctypes.c_int),
	]

class PaStreamParameters (ctypes.Structure):
  _fields_ = [
	('device', ctypes.c_int),						#PaDeviceIndex
	('channelCount', ctypes.c_int),
	('sampleFormat', ctypes.c_ulong),				#PaSampleFormat
	('suggestedLatency', ctypes.c_double),			# PaTime
	('hostApiSpecificStreamInfo', ctypes.c_void_p),
	]

pa_name = ctypes.util.find_library("portaudio")
pa = ctypes.CDLL(pa_name)

pa.Pa_GetDeviceInfo.restype		= ctypes.POINTER(PaDeviceInfo)
pa.Pa_GetHostApiInfo.restype	= ctypes.POINTER(PaHostApiInfo)
pa.Pa_GetVersionText.restype	= ctypes.c_char_p

inputParameters = PaStreamParameters (device=0, channelCount=2,
			sampleFormat=2, suggestedLatency=0,		# format 2 is paInt32
			hostApiSpecificStreamInfo=ctypes.c_void_p() )

outputParameters =  PaStreamParameters (device=0, channelCount=2,
			sampleFormat=2, suggestedLatency=0,		# format 2 is paInt32
			hostApiSpecificStreamInfo=ctypes.c_void_p() )

print('Open', pa.Pa_Initialize())
try:
  print('Version', pa.Pa_GetVersion())
  print('Version Text', pa.Pa_GetVersionText())
  count = pa.Pa_GetDeviceCount()
  print('NumDev', count)
  for i in range(count):
    pt_info = pa.Pa_GetDeviceInfo(i)
    info = pt_info.contents
    print("Device %2d, host api %s" % (i, pa.Pa_GetHostApiInfo(info.hostApi).contents.name))
    print("    Name %s" %  info.name)
    print("    Max inputs %d,  Max outputs %d" % (info.maxInputChannels, info.maxOutputChannels))
    inputParameters.device = i
    outputParameters.device = i
    if info.maxInputChannels >= 2:
      ptIn = ctypes.pointer(inputParameters)
    else:
      ptIn = ctypes.c_void_p()
    if info.maxOutputChannels >= 2:
      ptOut = ctypes.pointer(outputParameters)
    else:
      ptOut = ctypes.c_void_p()
    print("    Speeds for 2-channel paInt32:", end=' ')
    for speed in (44100, 48000, 96000, 192000):
      if pa.Pa_IsFormatSupported(ptIn, ptOut, ctypes.c_double(speed)) == 0:
        print("  %d" % speed, end=' ')
    print()
finally:
  print('Close', pa.Pa_Terminate())
