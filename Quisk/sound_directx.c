#include <Python.h>
#include <complex.h>
#include <math.h>
#include "quisk.h"
#include "dsound.h"
//#include <audiodefs.h>
#include <Mmreg.h>
//#include <ksmedia.h>
//#include <uuids.h>


// This module provides sound card access using Direct Sound

HRESULT errFound, errOpen;

static GUID IEEE = {0x00000003, 0x0000, 0x0010, {0x80, 0x00, 0x00, 0xaa, 0x00, 0x38, 0x9b, 0x71}};
static GUID PCMM = {0x00000001, 0x0000, 0x0010, {0x80, 0x00, 0x00, 0xaa, 0x00, 0x38, 0x9b, 0x71}};

static BOOL CALLBACK DSEnumNames(LPGUID lpGUID, LPCTSTR lpszDesc, LPCTSTR lpszDrvName, LPVOID pyseq)
{
	PyList_Append((PyObject *)pyseq, PyString_FromString(lpszDesc));
	return( TRUE );
}

static BOOL CALLBACK DsEnumPlay(LPGUID lpGUID, LPCTSTR lpszDesc, LPCTSTR lpszDrvName, LPVOID dev)
{	// Open the play device if the name is found in the description
	LPDIRECTSOUND8 DsDev;

	if (strstr (lpszDesc, ((struct sound_dev *)dev)->name)) {
		errFound = DS_OK;
		errOpen = DirectSoundCreate8(lpGUID, &DsDev, NULL);
		if (errOpen == DS_OK) {
			((struct sound_dev *)dev)->handle = DsDev;
		}
		return FALSE;	// Stop iteration
	}
	else {
		return TRUE;
	}
}

static BOOL CALLBACK DsEnumCapture(LPGUID lpGUID, LPCTSTR lpszDesc, LPCTSTR lpszDrvName, LPVOID dev)
{	// Open the capture device if the name is found in the description
	LPDIRECTSOUNDCAPTURE8 DsDev;

	if (strstr (lpszDesc, ((struct sound_dev *)dev)->name)) {
		errFound = DS_OK;
		errOpen = DirectSoundCaptureCreate8(lpGUID, &DsDev, NULL);
		if (errOpen == DS_OK)
			((struct sound_dev *)dev)->handle = DsDev;
		return FALSE;	// Stop iteration
	}
	else {
		return TRUE;
	}
}

static void MakeWFext(int use_new, int use_float, struct sound_dev * dev, WAVEFORMATEXTENSIBLE * pwfex)
{	// fill in a WAVEFORMATEXTENSIBLE structure
	if (use_float)
		dev->sample_bytes = 4;
	if (use_new) {
		pwfex->Format.wFormatTag = WAVE_FORMAT_EXTENSIBLE;
		pwfex->Format.cbSize = 22;
		pwfex->Samples.wValidBitsPerSample = dev->sample_bytes * 8;
		if (dev->num_channels == 1)
			pwfex->dwChannelMask = SPEAKER_FRONT_LEFT;
		else
			pwfex->dwChannelMask = SPEAKER_FRONT_LEFT | SPEAKER_FRONT_RIGHT;
		if (use_float) {
			pwfex->SubFormat = IEEE;
			dev->use_float = 1;
		}
		else {
			pwfex->SubFormat = PCMM;
			dev->use_float = 0;
		}
	}
	else {
		pwfex->Format.cbSize = 0;
		if (use_float) {
			pwfex->Format.wFormatTag = 0x03;	//WAVE_FORMAT_IEEE;
			dev->use_float = 1;
		}
		else {
			pwfex->Format.wFormatTag = WAVE_FORMAT_PCM;
			dev->use_float = 0;
		}
	}
	pwfex->Format.nChannels = dev->num_channels;
	pwfex->Format.nSamplesPerSec = dev->sample_rate;
	pwfex->Format.nAvgBytesPerSec = dev->num_channels * dev->sample_rate * dev->sample_bytes;
	dev->play_buf_size = pwfex->Format.nAvgBytesPerSec;
	pwfex->Format.nBlockAlign = dev->num_channels * dev->sample_bytes;
	pwfex->Format.wBitsPerSample = dev->sample_bytes * 8;
}

static int quisk_open_capture(struct sound_dev * dev)
{	// Open the soundcard for capture.  Return non-zero for error.
	LPDIRECTSOUNDCAPTUREBUFFER ptBuf;
	DSCBUFFERDESC dscbd;
	HRESULT hr;
	WAVEFORMATEXTENSIBLE wfex;

	dev->handle = NULL; 
	dev->buffer = NULL; 
	dev->started = 0;
	dev->dataPos = 0;
	dev->portaudio_index = -1;
	if ( ! dev->name[0])	// Check for null play name; not an error
		return 0;
	errFound = ~DS_OK;
	DirectSoundCaptureEnumerate((LPDSENUMCALLBACK)DsEnumCapture, dev);
	if (errFound != DS_OK) {
		snprintf (quisk_sound_state.err_msg, SC_SIZE,
			"DirectSound capture device name %s not found", dev->name);
		return 1;
	}
	if (errOpen != DS_OK) {
		snprintf (quisk_sound_state.err_msg, SC_SIZE,
			"DirectSound capture device %s open failed", dev->name);
		return 1;
	}
	dev->sample_bytes = 4;
	MakeWFext (1, 0, dev, &wfex);		// fill in wfex
	memset(&dscbd, 0, sizeof(DSCBUFFERDESC));
	dscbd.dwSize = sizeof(DSCBUFFERDESC);
	dscbd.dwFlags = 0;
	dscbd.dwBufferBytes = dev->play_buf_size;	// one second buffer
	dscbd.lpwfxFormat = (WAVEFORMATEX *)&wfex;
	hr = IDirectSoundCapture_CreateCaptureBuffer(
		(LPDIRECTSOUNDCAPTURE8)dev->handle, &dscbd, &ptBuf, NULL);
	if (hr == DS_OK) {
		dev->buffer = ptBuf;
#if DEBUG_IO
		printf("Created capture buffer size %d bytes for %s\n",
			dev->play_buf_size, dev->name);
#endif
	}
	else {
		snprintf (quisk_sound_state.err_msg, SC_SIZE,
			"DirectSound capture device %s buffer create failed (0x%lX)", dev->name, hr);
		return 1;
	}
	ptBuf = (LPDIRECTSOUNDCAPTUREBUFFER)dev->buffer;
	hr = IDirectSoundCaptureBuffer8_Start(ptBuf, DSCBSTART_LOOPING);
	if (hr != DS_OK) {
#if DEBUG_IO
		printf("Capture start error 0x%lX", hr);
#endif
		snprintf (quisk_sound_state.err_msg, SC_SIZE,
			"DirectSound capture device %s capture start failed", dev->name);
		return 1;
	}
	return 0;
}

static int quisk_open_playback(struct sound_dev * dev)
{	// Open the soundcard for playback.  Return non-zero for error.
	LPDIRECTSOUNDBUFFER ptBuf;
	WAVEFORMATEXTENSIBLE wfex;
	DSBUFFERDESC dsbdesc; 
	HRESULT hr;

	dev->handle = NULL; 
	dev->buffer = NULL; 
	dev->started = 0;
	dev->oldPlayPos = 0;
	dev->play_delay = 0;
	dev->dataPos = 0;
	dev->portaudio_index = -1;
	dev->sample_bytes = 2;
	if ( ! dev->name[0])	// Check for null play name; not an error
		return 0;
	errFound = ~DS_OK;
	DirectSoundEnumerate((LPDSENUMCALLBACK)DsEnumPlay, dev);
	if (errFound != DS_OK) {
		snprintf (quisk_sound_state.err_msg, SC_SIZE,
			"DirectSound play device name %s not found", dev->name);
		return 1;
	}
	if (errOpen != DS_OK) {
		snprintf (quisk_sound_state.err_msg, SC_SIZE,
			"DirectSound play device %s open failed", dev->name);
		return 1;
	}
	hr = IDirectSound_SetCooperativeLevel ((LPDIRECTSOUND8)dev->handle, (HWND)quisk_mainwin_handle, DSSCL_PRIORITY);
	if (hr != DS_OK) {
		snprintf (quisk_sound_state.err_msg, SC_SIZE,
			"DirectSound play device %s cooperative level failed", dev->name);
		return 1;
	}
	dev->sample_bytes = 4;
	MakeWFext (1, 0, dev, &wfex);		// fill in wfex
	memset(&dsbdesc, 0, sizeof(DSBUFFERDESC));
	dsbdesc.dwSize = sizeof(DSBUFFERDESC); 
	dsbdesc.dwFlags = DSBCAPS_GETCURRENTPOSITION2|DSBCAPS_GLOBALFOCUS;
	dsbdesc.dwBufferBytes = dev->play_buf_size;	// one second buffer
	dsbdesc.lpwfxFormat = (LPWAVEFORMATEX)&wfex;
	hr = IDirectSound_CreateSoundBuffer(
		(LPDIRECTSOUND8)dev->handle, &dsbdesc, &ptBuf, NULL); 
	if (hr == DS_OK) {
		dev->buffer = ptBuf;
	}
	else {
		snprintf (quisk_sound_state.err_msg, SC_SIZE,
			"DirectSound play device %s buffer create failed (0x%X)", dev->name, hr);
		return 1;
	}
	return 0;
}

PyObject * quisk_sound_devices(PyObject * self, PyObject * args)
{	// Return a list of DirectSound device names
	PyObject * pylist, * pycapt, * pyplay;

	if (!PyArg_ParseTuple (args, ""))
		return NULL;

	// Each pycapt and pyplay is a device name
	pylist = PyList_New(0);		// list [pycapt, pyplay]
	pycapt = PyList_New(0);		// list of capture devices
	pyplay = PyList_New(0);		// list of play devices
	PyList_Append(pylist, pycapt);
	PyList_Append(pylist, pyplay);
	DirectSoundCaptureEnumerate((LPDSENUMCALLBACK)DSEnumNames, pycapt);
	DirectSoundEnumerate((LPDSENUMCALLBACK)DSEnumNames, pyplay);
	return pylist;
}

void quisk_start_sound_alsa (struct sound_dev ** pCapture, struct sound_dev ** pPlayback)
{
	struct sound_dev * pDev;

	if (quisk_sound_state.err_msg[0])
		return;		// prior error
	// DirectX must open the playback device before the (same) capture device
	while (1) {
		pDev = *pPlayback++;
		if ( ! pDev)
			break;
		if (quisk_open_playback(pDev))
			return;		// error
	}
	while (1) {
		pDev = *pCapture++;
		if ( ! pDev)
			break;
		if (quisk_open_capture(pDev))
			return;		// error
	}
}

void quisk_close_sound_alsa(struct sound_dev ** pCapture, struct sound_dev ** pPlayback)
{
	struct sound_dev * pDev;

	while (*pPlayback) {
		pDev = *pPlayback;
		if (pDev->buffer)
			IDirectSoundBuffer8_Stop((LPDIRECTSOUNDBUFFER)pDev->buffer);
		pDev->handle = NULL;
		pPlayback++;
	}
	while (*pCapture) {
		pDev = *pCapture;
		if (pDev->buffer)
			IDirectSoundCaptureBuffer_Stop((LPDIRECTSOUNDCAPTUREBUFFER)pDev->buffer);
		pDev->handle = NULL;
		pCapture++;
	}
}


int  quisk_read_alsa(struct sound_dev * dev, complex double * cSamples)
{
	LPDIRECTSOUNDCAPTUREBUFFER ptBuf = (LPDIRECTSOUNDCAPTUREBUFFER)dev->buffer;
	HRESULT hr;
	DWORD readPos, captPos;
	LPVOID pt1, pt2;
	DWORD i, n1, n2;
	short si, sq, * pts;
	float fi, fq, * ptf;
	int   li, lq, * ptl;	// int must be 32 bits
	complex double c;
	int ii, qq, nSamples;
	int bytes, frames, poll_size, millisecs, bytes_per_frame;
	
	if ( ! dev->handle || ! dev->buffer)
		return 0;

	bytes_per_frame = dev->num_channels * dev->sample_bytes;
	hr = IDirectSoundCaptureBuffer8_GetCurrentPosition(ptBuf, &captPos, &readPos);
	if (hr != DS_OK) {
#if DEBUG_IO
		printf ("Get CurrentPosition error 0x%lX\n", hr);
#endif
		dev->dev_error++;
		return 0;
	}
// printf("dataPos %d\n", dev->dataPos);
	if ( ! dev->started) {
		dev->started = 1;
		dev->dataPos = readPos;
	}
	if (readPos >= dev->dataPos)
		bytes = readPos - dev->dataPos;
	else
		bytes = readPos - dev->dataPos + dev->play_buf_size;
	frames = bytes / bytes_per_frame;	// frames available to read
	poll_size = dev->read_frames;
	millisecs = (poll_size - frames) * 1000 / dev->sample_rate;	// time to read remaining poll size
	if (millisecs > 0) {		// wait for additional frames
#if DEBUG_IO > 2
			printf ("Wait %d millisecs for more samples\n", millisecs);
#endif
		Sleep(millisecs);
		hr = IDirectSoundCaptureBuffer8_GetCurrentPosition(ptBuf, &captPos, &readPos);
		if (hr != DS_OK) {
#if DEBUG_IO
			printf ("Get CurrentPosition two error 0x%lX\n", hr);
#endif
			dev->dev_error++;
			return 0;
		}
		if (readPos >= dev->dataPos)
			bytes = readPos - dev->dataPos;
		else
			bytes = readPos - dev->dataPos + dev->play_buf_size;
	}
	frames = bytes / bytes_per_frame;	// frames available to read
	dev->dev_latency = frames;
	bytes = frames * bytes_per_frame;	// round to frames
	if ( ! bytes) {
		return 0;
	}
	i = poll_size * bytes_per_frame * 4;	// Limit size of read
	if (i > 0 && bytes > i) {	// zero poll_size is allowed
		bytes = i;
		frames = bytes / bytes_per_frame;
	}
	if (IDirectSoundCaptureBuffer8_Lock(ptBuf, dev->dataPos, bytes, &pt1, &n1, &pt2, &n2, 0) != DS_OK) {
		dev->dev_error++;
#if DEBUG_IO
		printf ("DirecctX capture lock error bytes %d\n", bytes);
#endif
		return 0;
	}
//printf ("%d %d %d %d\n", dev->channel_I, dev->channel_Q, bytes_per_frame, dev->num_channels);
#if DEBUG_IO > 3
	printf("%s read %4d bytes %4d frames from %9d to (%9lu %9lu) diff %9lu\n", dev->name,
		bytes, frames, dev->dataPos, readPos, captPos, captPos - readPos);
#endif
#if DEBUG_IO
	if (bytes != n1 + n2)
		printf ("Lock not equal to bytes\n");
#endif
	dev->dataPos += bytes;
	dev->dataPos = dev->dataPos % dev->play_buf_size;
	nSamples = 0;
	switch (dev->sample_bytes + dev->use_float) {
	case 2:
		pts = (short *)pt1;
		frames = (n1 + n2) / bytes_per_frame;
		bytes = 0;
		while (frames) {
			si = pts[dev->channel_I];
			sq = pts[dev->channel_Q];
			pts += dev->num_channels;
			if (si >=  CLIP16 || si <= -CLIP16)
				dev->overrange++;	// assume overrange returns max int
			if (sq >=  CLIP16 || sq <= -CLIP16)
				dev->overrange++;
			ii = si << 16;
			qq = sq << 16;
			cSamples[nSamples++] = ii + I * qq;
			bytes += bytes_per_frame;
			frames--;
			if (bytes == n1)
				pts = (short *)pt2;
		}
		break;
	case 4:
		ptl = (int *)pt1;
		frames = (n1 + n2) / bytes_per_frame;
		bytes = 0;
		while (frames) {
			li = ptl[dev->channel_I];
			lq = ptl[dev->channel_Q];
			ptl += dev->num_channels;
			if (li >=  CLIP32 || li <= -CLIP32)
				dev->overrange++;	// assume overrange returns max int
			if (lq >=  CLIP32 || lq <= -CLIP32)
				dev->overrange++;
			cSamples[nSamples++] = li + I * lq;
			bytes += bytes_per_frame;
			frames--;
			if (bytes == n1)
				ptl = (int *)pt2;
		}
		break;
	case 5:		// use IEEE float
		ptf = (float *)pt1;
		frames = (n1 + n2) / bytes_per_frame;
		bytes = 0;
		while (frames) {
			fi = ptf[dev->channel_I];
			fq = ptf[dev->channel_Q];
			ptf += dev->num_channels;
			if (fabsf(fi) >= 1.0 || fabsf(fq) >= 1.0)
				dev->overrange++;	// assume overrange returns maximum
			cSamples[nSamples++] = (fi + I * fq) * 16777215;
			bytes += bytes_per_frame;
			frames--;
			if (bytes == n1) {
				ptf = (float *)pt2;
			}
		}
		break;
	}
	IDirectSoundCaptureBuffer8_Unlock(ptBuf, pt1, n1, pt2, n2);
	for (i = 0; i < nSamples; i++) {	// DC removal; R.G. Lyons page 553
		c = cSamples[i] + dev->dc_remove * 0.95;
		cSamples[i] = c - dev->dc_remove;
		dev->dc_remove = c;
	}
	return nSamples;
}

void quisk_play_alsa(struct sound_dev * dev, int nSamples,
		complex double * cSamples, int report_latency, double volume)
{
	LPDIRECTSOUNDBUFFER ptBuf = (LPDIRECTSOUNDBUFFER)dev->buffer;
	DWORD playPos, writePos;	// hardware index into buffer
	LPVOID pt1, pt2;
	DWORD n1, n2;
	short * pts;
	float * ptf;
	int   * ptl;	// int must be 32 bits
	int n, unavail, count, frames, bytes, pass, bytes_per_frame;

	if ( ! dev->handle || ! dev->buffer)
		return;

	bytes_per_frame = dev->num_channels * dev->sample_bytes;
	// Note: writePos moves ahead with playPos; it is not associated with write activity
	if (IDirectSoundBuffer8_GetCurrentPosition(ptBuf, &playPos, &writePos) != DS_OK) {
#if DEBUG_IO
		printf ("Bad GetCurrentPosition\n");
#endif
		quisk_sound_state.write_error++;
		dev->dev_error++;
		playPos = writePos = 0;
	}
	unavail = (int)writePos - (int)playPos;   // Must not write to this region
	if (unavail < 0)
		unavail += dev->play_buf_size;
	count = (int)playPos - dev->oldPlayPos;     // number of bytes played
	if (count < 0)
		count += dev->play_buf_size;    // assume no wrap-around beyond play_buf_size
	dev->oldPlayPos = playPos;
	dev->play_delay -= count;                // bytes in buffer available to play
	dev->dev_latency = dev->play_delay / bytes_per_frame;
	if (report_latency)			// Report latency for main playback device
		quisk_sound_state.latencyPlay = dev->dev_latency;
#if DEBUG_IO
	if (nSamples || count)
		printf ("DirectX playPos %6d writePos %6d no-write %6d dev->dev_latency %6d data_pos %6d samples %6d\n",
	    	(int)playPos, (int)writePos, unavail, dev->dev_latency, dev->dataPos, nSamples);
#endif
	switch(dev->started) {
	case 0:     // Starting state; wait for buffer to fill before starting play
		if (dev->dev_latency + nSamples >= dev->latency_frames) {
			IDirectSoundBuffer8_Play (ptBuf, 0, 0, DSBPLAY_LOOPING);
			dev->started = 1;
#if DEBUG_IO
		    printf ("Start DirectX play at dev->latency_frames %d\n", dev->latency_frames);
#endif
		}
		break;
	case 1:     // Normal run state
		// Measure the space available to write samples
		frames = (dev->play_buf_size - dev->play_delay - unavail) / bytes_per_frame;
	    // Check for underrun
	    n = unavail / bytes_per_frame + dev->latency_frames * 2 / 10 - nSamples;   // minimum frames
	    if (dev->dev_latency < n) {
		    quisk_sound_state.underrun_error++;
		    dev->dev_underrun++;
			n += dev->latency_frames * 2 / 10;
			while (n-- > 0)
				cSamples[nSamples++] = 0;   // add zero samples
#if DEBUG_IO
		    printf ("Underrun error, frames %d\n", dev->dev_latency);
#endif
	    }
		// Check if play buffer is too full
		else if (dev->dev_latency > dev->latency_frames * 18 / 10 || nSamples >= frames) {
			quisk_sound_state.write_error++;
			dev->dev_error++;
			nSamples = 0;
			dev->started = 2;
#if DEBUG_IO
			printf("Discard %d samples\n", nSamples);
#endif
		}
		break;
	case 2:     // Buffer is too full; wait for it to drain
		nSamples = 0;
		if (dev->dev_latency <= dev->latency_frames) {
			dev->started = 1;
#if DEBUG_IO
			printf("Resume adding samples\n");
#endif
		}
		break;
	}
	bytes = nSamples * bytes_per_frame;
	if (bytes <= 0)
		return;
	// write our data bytes at our data position dataPos
	if (IDirectSoundBuffer8_Lock(ptBuf, dev->dataPos, bytes, &pt1, &n1, &pt2, &n2, 0) != DS_OK) {
#if DEBUG_IO
		printf ("DirectX play lock error\n");
#endif
		quisk_sound_state.write_error++;
		dev->dev_error++;
		return;
	}
	dev->dataPos += bytes;	// update data write position
	dev->dataPos = dev->dataPos % dev->play_buf_size;
	dev->play_delay += bytes;                // bytes available to play
	pass = 0;
	n = 0;
	switch (dev->sample_bytes + dev->use_float) {
	case 2:
		pts = (short *)pt1;	// Start writing at pt1
		frames = n1 / bytes_per_frame;
		for (n = 0; n < nSamples && pass < 2; n++) {
			pts[dev->channel_I] = (short)(volume * creal(cSamples[n]) / 65536);
			pts[dev->channel_Q] = (short)(volume * cimag(cSamples[n]) / 65536);
			pts += dev->num_channels;
			if (--frames <= 0) {
				pass++;
				// change to pt2
				pts = (short *)pt2;
				frames = n2 / bytes_per_frame;
			}
		}
		break;
	case 4:
		ptl = (int *)pt1;	// Start writing at pt1
		frames = n1 / bytes_per_frame;
		for (n = 0; n < nSamples && pass < 2; n++) {
			ptl[dev->channel_I] = (int)(volume * creal(cSamples[n]));
			ptl[dev->channel_Q] = (int)(volume * cimag(cSamples[n]));
			ptl += dev->num_channels;
			if (--frames <= 0) {
				pass++;
				// change to pt2
				ptl = (int *)pt2;
				frames = n2 / bytes_per_frame;
			}
		}
		break;
	case 5:		// use IEEE float
		ptf = (float *)pt1;	// Start writing at pt1
		frames = n1 / bytes_per_frame;
		for (n = 0; n < nSamples && pass < 2; n++) {
			ptf[dev->channel_I] = (volume * creal(cSamples[n]) / CLIP32);
			ptf[dev->channel_Q] = (volume * cimag(cSamples[n]) / CLIP32);
			ptf += dev->num_channels;
			if (--frames <= 0) {
				pass++;
				// change to pt2
				ptf = (float *)pt2;
				frames = n2 / bytes_per_frame;
			}
		}
		break;
	}
	IDirectSoundBuffer8_Unlock(ptBuf, pt1, n1, pt2, n2);
}




void quisk_play_portaudio(struct sound_dev * dev, int j, complex double * samp, int i, double volume)
{
}

void quisk_start_sound_portaudio(struct sound_dev ** pCapture, struct sound_dev ** pPlayback)
{
}

void quisk_close_sound_portaudio(void)
{
}

int  quisk_read_portaudio(struct sound_dev * dev, complex double * samp)
{
	return 0;
}

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

void quisk_mixer_set(char * card_name, int numid, PyObject * value, char * err_msg, int err_size)
{
	err_msg[0] = 0;
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
