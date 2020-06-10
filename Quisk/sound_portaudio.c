/*
 * This module provides sound access for QUISK using the portaudio library.
*/
#include <Python.h>
#include <complex.h>
#include <math.h>
#include <portaudio.h>
#include <sys/time.h>
#include <time.h>
#include "quisk.h"

/*
 The sample rate is in frames per second.  Each frame has a number of channels,
 and each channel has a sample of size sample_bytes.  The channels are interleaved:
 (channel0, channel1), (channel0, channel1), ...
*/

extern struct sound_conf quisk_sound_state;	// Current sound status

static float fbuffer[SAMP_BUFFER_SIZE];		// Buffer for float32 samples from sound

int quisk_read_portaudio(struct sound_dev * dev, complex double * cSamples)
{	// Read sound samples from the soundcard.
	// Samples are converted to 32 bits with a range of +/- CLIP32 and placed into cSamples.
	int i;
	long avail;
	int nSamples;
	complex double c;
	PaError error;
	float fi, fq;

	if (!dev->handle)
		return -1;

	avail = Pa_GetStreamReadAvailable((PaStream * )dev->handle);
	dev->dev_latency = avail;
	if (dev->read_frames == 0) {		// non-blocking: read available frames
		if (avail > SAMP_BUFFER_SIZE / dev->num_channels)	// limit read request to buffer size
			avail = SAMP_BUFFER_SIZE / dev->num_channels;
	}
	else {		// size of read request
		avail = dev->read_frames;
	}
	error = Pa_ReadStream ((PaStream * )dev->handle, fbuffer, avail);
	if (error != paNoError) {
		dev->dev_error++;
	}
	nSamples = 0;
	for (i = 0; avail; i += dev->num_channels, nSamples++, avail--) {
		fi = fbuffer[i + dev->channel_I];
		fq = fbuffer[i + dev->channel_Q];
		if (fi >=  1.0 || fi <= -1.0)
			dev->overrange++;	// assume overrange returns max int
		if (fq >=  1.0 || fq <= -1.0)
			dev->overrange++;
		cSamples[nSamples] = (fi + I * fq) * CLIP32;
	}
	for (i = 0; i < nSamples; i++) {	// DC removal; R.G. Lyons page 553
		c = cSamples[i] + dev->dc_remove * 0.95;
		cSamples[i] = c - dev->dc_remove;
		dev->dc_remove = c;
	}
	return nSamples;
}

void quisk_play_portaudio(struct sound_dev * playdev, int nSamples, complex double * cSamples,
		int report_latency, double volume)
{	// play the samples; write them to the portaudio soundcard
	int i, n, index;
	long delay;
	float fi, fq;
	PaError error;

	if (!playdev->handle || nSamples <= 0)
		return;

	// "delay" is the number of samples left in the play buffer
	delay = playdev->play_buf_size - Pa_GetStreamWriteAvailable(playdev->handle);
	//printf ("play available %ld\n", Pa_GetStreamWriteAvailable(playdev->handle));
	playdev->dev_latency = delay;
	if (report_latency) {		// Report for main playback device
		quisk_sound_state.latencyPlay = delay;
	}
//printf ("nSamples %d, delay %ld\n", nSamples, delay);
	index = 0;
#if 0
	// Timing is too crude to support this logic
	if (nSamples + delay > playdev->latency_frames * 9 / 10) {
		nSamples--;
#if DEBUG_IO
		printf("Remove a sample %s nSamples %4d  delay %4d  total %4d\n", playdev->name, nSamples, (int)delay, nSamples + (int)delay);
#endif
	}
	else if(nSamples + delay < playdev->latency_frames * 5 / 10) {
		cSamples[nSamples] = cSamples[nSamples - 1];
		nSamples++;
#if DEBUG_IO
		printf("Add    a sample %s nSamples %4d  delay %4d  total %4d\n", playdev->name, nSamples, (int)delay, nSamples + (int)delay);
#endif
	}
#endif
	if (nSamples + delay > playdev->latency_frames) {		// too many samples
		index = nSamples + delay - playdev->latency_frames;	// write only the most recent samples
		if (index > nSamples)
			index = nSamples;
		quisk_sound_state.write_error++;
		playdev->dev_error++;
#if DEBUG_IO
		printf("Discard %d of %d samples at %d delay\n", index, nSamples, (int)delay);
#endif
		if (nSamples == index)		// no samples to play
			return;
	}
	else if (delay < 16) {		// Buffer is too empty; fill it back up with zeros.
		n = playdev->latency_frames * 7 / 10 - nSamples;
#if DEBUG_IO
		printf("Add %d zero samples at %ld delay\n", n, delay);
#endif
		for (i = 0; i < n; i++)
			cSamples[nSamples++] = 0;
	}
	for (i = 0, n = index; n < nSamples; i += playdev->num_channels, n++) {
		fi = volume * creal(cSamples[n]);
		fq = volume * cimag(cSamples[n]);
		fbuffer[i + playdev->channel_I] = fi / CLIP32;
		fbuffer[i + playdev->channel_Q] = fq / CLIP32;
	}
	error = Pa_WriteStream ((PaStream * )playdev->handle, fbuffer, nSamples - index);
//printf ("Write %d\n", nSamples - index);
	if (error == paNoError)
		;
	else if (error == paOutputUnderflowed) {
		quisk_sound_state.underrun_error++;
		playdev->dev_underrun++;
	}
	else {
		quisk_sound_state.write_error++;
		playdev->dev_error++;
#if DEBUG_IO
		printf ("Play error: %s\n", Pa_GetErrorText(error));
#endif
	}
}

static void info_portaudio (struct sound_dev * cDev, struct sound_dev * pDev)
{	// Return information about the device
	const PaDeviceInfo * info;
	PaStreamParameters params;
	int index, rate;

	if (cDev)
		index = cDev->portaudio_index;
	else if (pDev)
		index = pDev->portaudio_index;
	else
		return;
	info = Pa_GetDeviceInfo(index);
	if ( ! info)
		return;

	params.device = index;
	params.channelCount = 1;
	params.sampleFormat = paFloat32;
	params.suggestedLatency = 0.10;
	params.hostApiSpecificStreamInfo = NULL;

	if (cDev) {
		cDev->chan_min = 1;
		cDev->chan_max = info->maxInputChannels;
		cDev->rate_min = cDev->rate_max = 0;
		cDev->portaudio_latency = info->defaultHighInputLatency;
#if DEBUG_IO
		printf ("Capture latency low %lf,  high %lf\n",
				info->defaultLowInputLatency, info->defaultHighInputLatency);
#endif
		for (rate = 8000; rate <= 384000; rate += 8000) {
			if (Pa_IsFormatSupported(&params, NULL, rate) == paFormatIsSupported) {
				if (cDev->rate_min == 0)
					cDev->rate_min = rate;
				cDev->rate_max = rate;
			}
		}
	}

	if (pDev) {
		pDev->chan_min = 1;
		pDev->chan_max = info->maxOutputChannels;
		pDev->rate_min = pDev->rate_max = 0;
		pDev->portaudio_latency = quisk_sound_state.latency_millisecs / 1000.0 * 2.0;
		if (pDev->portaudio_latency < info->defaultHighOutputLatency)
			pDev->portaudio_latency = info->defaultHighOutputLatency;
#if DEBUG_IO
		printf ("Play latency low %lf,  high %lf\n",
				info->defaultLowOutputLatency, info->defaultHighOutputLatency);
#endif
		for (rate = 8000; rate <= 384000; rate += 8000) {
			if (Pa_IsFormatSupported(&params, NULL, rate) == paFormatIsSupported) {
				if (pDev->rate_min == 0)
					pDev->rate_min = rate;
				pDev->rate_max = rate;
			}
		}
	}
}

static int quisk_pa_name2index (struct sound_dev * dev, int is_capture)
{	// Based on the device name, set the portaudio index, or -1.
	// Return non-zero for error.  Not a portaudio device is not an error.
	const PaDeviceInfo * pInfo;
	int i, count;

	if (strncmp (dev->name, "portaudio", 9)) {
		dev->portaudio_index = -1;	// Name does not start with "portaudio"
		return 0;		// Not a portaudio device, not an error
	}
	if ( ! strcmp (dev->name, "portaudiodefault")) {
		if (is_capture)		// Fill in the default device index
			dev->portaudio_index = Pa_GetDefaultInputDevice();
		else
			dev->portaudio_index = Pa_GetDefaultOutputDevice();
		strncpy (dev->msg1, "Using default portaudio device", QUISK_SC_SIZE);
		return 0;
	}
	if ( ! strncmp (dev->name, "portaudio#", 10)) {		// Integer index follows "#"
		dev->portaudio_index = i = atoi(dev->name + 10);
		pInfo = Pa_GetDeviceInfo(i);
		if (pInfo) {
			snprintf (dev->msg1, QUISK_SC_SIZE, "PortAudio device %s",  pInfo->name);
			return 0;
		}
		else {
			snprintf (quisk_sound_state.err_msg, QUISK_SC_SIZE,
				"Can not find portaudio device number %s", dev->name + 10);
		}
		return 1;
	}
	if ( ! strncmp (dev->name, "portaudio:", 10)) {
		dev->portaudio_index = -1;
		count = Pa_GetDeviceCount();		// Search for string in device name
		for (i = 0; i < count; i++) {
			pInfo = Pa_GetDeviceInfo(i);
			if (pInfo && strstr(pInfo->name, dev->name + 10)) {
				dev->portaudio_index = i;
				snprintf (dev->msg1, QUISK_SC_SIZE, "PortAudio device %s",  pInfo->name);
				break;
			}
		}
		if (dev->portaudio_index == -1)	{	// Error
			snprintf (quisk_sound_state.err_msg, QUISK_SC_SIZE,
				"Can not find portaudio device named %s", dev->name + 10);
			return 1;
		}
		return 0;
	}
	snprintf (quisk_sound_state.err_msg, QUISK_SC_SIZE,
		"Did not recognize portaudio device %s", dev->name);
	return 1;
}

static int quisk_open_portaudio (struct sound_dev * cDev, struct sound_dev * pDev)
{	// Open the portaudio soundcard for capture on cDev and playback on pDev (or NULL).
	// Return non-zero for error.
	PaStreamParameters cParams, pParams;
	PaError error;
	PaStream * hndl;

	info_portaudio (cDev, pDev);

	if (pDev && cDev && pDev->sample_rate != cDev->sample_rate) {
		strncpy(quisk_sound_state.err_msg, "Capture and Play sample rates must be equal.", QUISK_SC_SIZE);
		return 1;
	}

	cParams.sampleFormat = paFloat32;
	pParams.sampleFormat = paFloat32;
	cParams.hostApiSpecificStreamInfo = NULL;
	pParams.hostApiSpecificStreamInfo = NULL;

	if (cDev) {
		cDev->handle = NULL;
		cParams.device = cDev->portaudio_index;
		cParams.channelCount = cDev->num_channels;
		cParams.suggestedLatency = cDev->portaudio_latency;
	}

	if (pDev) {
		pDev->handle = NULL;
		pParams.device = pDev->portaudio_index;
		pParams.channelCount = pDev->num_channels;
		pParams.suggestedLatency = pDev->portaudio_latency;
	}

	if (cDev && pDev) {
		error = Pa_OpenStream (&hndl, &cParams, &pParams,
				(double)cDev->sample_rate, cDev->read_frames, 0, NULL, NULL);
		pDev->handle = cDev->handle = (void *)hndl;
	}
	else if (cDev) {
		error = Pa_OpenStream (&hndl, &cParams, NULL,
				(double)cDev->sample_rate, cDev->read_frames, 0, NULL, NULL);
		cDev->handle = (void *)hndl;
	}
	else if (pDev) {
		error = Pa_OpenStream (&hndl, NULL, &pParams,
				(double)pDev->sample_rate, 0, 0, NULL, NULL);
		pDev->handle = (void *)hndl;
	}
	else {
		error = paNoError;
	}
	if (pDev) {
		pDev->play_buf_size = Pa_GetStreamWriteAvailable(pDev->handle);
		if (pDev->latency_frames > pDev->play_buf_size) {
#if DEBUG_IO
			printf("Latency frames %d limited to buffer size %d\n",
					pDev->latency_frames, pDev->play_buf_size);
#endif
			pDev->latency_frames = pDev->play_buf_size;
		}
	}
#if DEBUG_IO
	if (pDev) {
		printf ("play_buf_size %d\n", pDev->play_buf_size);
		printf ("latency_frames %d\n", pDev->latency_frames);
	}
#endif
	if (error == paNoError)
		return 0;
	strncpy(quisk_sound_state.err_msg, Pa_GetErrorText(error), QUISK_SC_SIZE);
	return 1;
}

void quisk_start_sound_portaudio(struct sound_dev ** pCapture, struct sound_dev ** pPlayback)
{
	int index, err, match;
	struct sound_dev ** pCapt, ** pPlay;

	Pa_Initialize();
	// Set the portaudio index from the name.  Return on error.
	pCapt = pCapture;
	while (*pCapt) {
		if( (*pCapt)->driver == DEV_DRIVER_PORTAUDIO && quisk_pa_name2index (*pCapt, 1))
			return;		// Error
		pCapt++;
	}
	pPlay = pPlayback;
	while (*pPlay) {
		if( (*pPlay)->driver == DEV_DRIVER_PORTAUDIO && quisk_pa_name2index (*pPlay, 0))
			return;
		pPlay++;
	}
	// Open the sound cards.  If a capture device equals a playback device, they must be opened jointly.
	pCapt = pCapture;
	while (*pCapt) {
		index = (*pCapt)->portaudio_index;
		if((*pCapt)->driver == DEV_DRIVER_PORTAUDIO && index >= 0) {   // This is a portaudio device
			pPlay = pPlayback;
			match = 0;
			while (*pPlay) {
				if((*pPlay)->driver == DEV_DRIVER_PORTAUDIO &&
						(*pPlay)->portaudio_index == index) {   // same device, open both
					err = quisk_open_portaudio (*pCapt, *pPlay);
					match = 1;
					break;
				}
				pPlay++;
			}
			if ( ! match)
				err = quisk_open_portaudio (*pCapt, NULL);		// no matching device
			if (err)
				return;		// error
		}
		pCapt++;
	}
	strncpy (quisk_sound_state.msg1, (*pCapture)->msg1, QUISK_SC_SIZE);	// Primary capture device
	// Open remaining portaudio devices
	pPlay = pPlayback;
	while (*pPlay) {
      if ((*pPlay)->driver == DEV_DRIVER_PORTAUDIO
         && (*pPlay)->portaudio_index >= 0
         && ! (*pPlay)->handle
      ) {
			err = quisk_open_portaudio (NULL, *pPlay);
			if (err)
				return;		// error
		}
		pPlay++;
	}
     	if ( ! quisk_sound_state.msg1[0])	// Primary playback device
		strncpy (quisk_sound_state.msg1, (*pPlayback)->msg1, QUISK_SC_SIZE);
	pCapt = pCapture;
	while (*pCapt) {
		if ((*pCapt)->handle)
			Pa_StartStream((PaStream * )(*pCapt)->handle);
		pCapt++;
	}
	pPlay = pPlayback;
	while (*pPlay) {
		if ((*pPlay)->handle && Pa_IsStreamStopped((PaStream * )(*pPlay)->handle))
			Pa_StartStream((PaStream * )(*pPlay)->handle);
		pPlay++;
	}
}

void quisk_close_sound_portaudio(void)
{
	Pa_Terminate();
}

// Changes for MacOS support (__MACH__) thanks to Mario, DL3LSM.
#if defined(__MACH__)

static int device_list(PyObject * py, int input)
{
	int retNum = 0;
    char buf100[100];
	
    PaError err;
    
    err = Pa_Initialize();
    
    if ( err == paNoError ) {
        PaDeviceIndex numDev = Pa_GetDeviceCount();
        for (PaDeviceIndex dev = 0; dev < numDev; dev++) {
            const PaDeviceInfo *info = Pa_GetDeviceInfo(dev);
#if (0)
            printf("found audio device: %d, name=%s, #inp %d, #outp %d defsample %f\n", dev, info->name, info->maxInputChannels, 
                  info->maxOutputChannels, info->defaultSampleRate);
#endif
            if ((input && info->maxInputChannels > 0) ||
                (!input && info->maxOutputChannels > 0)) { // check the available channels for the type)
                // found one
                if (py) {
                    snprintf(buf100, 100, "%s", info->name);
					PyList_Append(py, PyString_FromString(buf100));
                } 
            }
        }
        Pa_Terminate();
    }
    return retNum;
	
}
					   
PyObject * quisk_sound_devices(PyObject * self, PyObject * args)
{	// Return a list of ALSA device names [pycapt, pyplay]
	PyObject * pylist, * pycapt, * pyplay;
	
	if (!PyArg_ParseTuple (args, ""))
		return NULL;
	// Each pycapt and pyplay is [pydev, pyname]
	pylist = PyList_New(0);		// list [pycapt, pyplay]
	pycapt = PyList_New(0);		// list of capture devices
	pyplay = PyList_New(0);		// list of play devices
	PyList_Append(pylist, pycapt);
	PyList_Append(pylist, pyplay);
	device_list(pycapt, 1);
	device_list(pyplay, 0);
	return pylist;
}

void quisk_play_alsa(struct sound_dev * dev, int nSamples,
					 complex double * cSamples, int report_latency, double volume)
{
}

void quisk_start_sound_alsa(struct sound_dev ** pCapture, struct sound_dev ** pPlayback)
{
}

void quisk_close_sound_alsa(struct sound_dev ** pCapture, struct sound_dev ** pPlayback)
{
}

int  quisk_read_alsa(struct sound_dev * dev, complex double * samp)
{
	return 0;
}

void quisk_mixer_set(char * card_name, int numid, PyObject * value, char * err_msg, int err_size)
{
    err_msg[0] = 0;
}

#if !defined USE_MACPORTS
int  quisk_read_pulseaudio(struct sound_dev * dev, complex double * samp)
{
	return 0;
}

void quisk_play_pulseaudio(struct sound_dev * dev, int j, complex double * samp, int i, double volume)
{
}

void quisk_start_sound_pulseaudio(struct sound_dev ** pCapture, struct sound_dev ** pPlayback)
{
}

void quisk_close_sound_pulseaudio()
{
}


PyObject * quisk_pa_sound_devices(PyObject * self, PyObject * args)
{	// Return a list of PulseAudio device names [pycapt, pyplay]
	PyObject * pylist, * pycapt, * pyplay;

	if (!PyArg_ParseTuple (args, ""))
		return NULL;
	pylist = PyList_New(0);		// list [pycapt, pyplay]
	pycapt = PyList_New(0);		// list of capture devices
	pyplay = PyList_New(0);		// list of play devices
	PyList_Append(pylist, pycapt);
	PyList_Append(pylist, pyplay);
	return pylist;
}
#endif
#endif
