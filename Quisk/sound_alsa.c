/*
 * This modue provides sound access for QUISK using the ALSA
 * library for Linux.
*/
#include <Python.h>
#include <complex.h>
#include <math.h>
#include <alsa/asoundlib.h>
#include "quisk.h"

/*
 The sample rate is in frames per second.  Each frame has a number of channels,
 and each channel has a sample of size sample_bytes.  The channels are interleaved:
 (channel0, channel1), (channel0, channel1), ...
*/

#define CORRECT_PLAY_RATE	1

extern struct sound_conf quisk_sound_state;	// Current sound status

static int is_little_endian;		// Test byte order; is it little-endian?
static short buffer2[SAMP_BUFFER_SIZE];				// Buffer for 2-byte samples from sound
static unsigned char buffer3[3 * SAMP_BUFFER_SIZE];	// Buffer for 3-byte samples from sound
static int buffer4[SAMP_BUFFER_SIZE];				// Buffer for 4-byte samples from sound
static int bufferz[SAMP_BUFFER_SIZE];				// Buffer for zero samples

int quisk_read_alsa(struct sound_dev * dev, complex double * cSamples)
{	// Read sound samples from the ALSA soundcard.
	// Samples are converted to 32 bits with a range of +/- CLIP32 and placed into cSamples.
	int i;
	snd_pcm_sframes_t frames, avail;
	short si, sq;
	int ii, qq;
	int nSamples;
	complex double c;

	if (!dev->handle)
		return -1;

	switch(snd_pcm_state(dev->handle)) {
	case SND_PCM_STATE_RUNNING:
		break;
	case SND_PCM_STATE_PREPARED:
		break;
	case SND_PCM_STATE_XRUN:
#if DEBUG_IO
		QuiskPrintTime("read_alsa: Capture overrun", 0);
#endif
		snd_pcm_prepare(dev->handle);
		break;
	default:
#if DEBUG_IO
		QuiskPrintTime("read_alsa: State UNKNOWN", 0);
#endif
		break;
	}

	snd_pcm_delay(dev->handle, &avail);	// available frames
	dev->dev_latency = avail;
	if (dev->read_frames == 0) {		// non-blocking: read available frames
		if (avail == 0)
			avail = 32;	// read frames to restart from error
		if (avail > SAMP_BUFFER_SIZE / dev->num_channels)		// limit read request to buffer size
			avail = SAMP_BUFFER_SIZE / dev->num_channels;
	}
	else {
		avail = dev->read_frames;	// size of read request
	}
	nSamples = 0;
	switch (dev->sample_bytes) {
	case 2:
		frames = snd_pcm_readi (dev->handle, buffer2, avail);	// read samples
		if (frames == -EAGAIN) {	// no samples available
			break;
		}
		else if (frames <= 0) {		// error
			dev->dev_error++;
#if DEBUG_IO
			QuiskPrintTime("read_alsa: frames < 0", 0);
#endif
			snd_pcm_prepare (dev->handle);
			snd_pcm_start (dev->handle);
			break;
		}
		for (i = 0; frames; i += dev->num_channels, nSamples++, frames--) {
			si = buffer2[i + dev->channel_I];
			sq = buffer2[i + dev->channel_Q];
			if (si >=  CLIP16 || si <= -CLIP16)
				dev->overrange++;	// assume overrange returns max int
			if (sq >=  CLIP16 || sq <= -CLIP16)
				dev->overrange++;
			ii = si << 16;
			qq = sq << 16;
			cSamples[nSamples] = ii + I * qq;
		}
		break;
	case 3:
		frames = snd_pcm_readi (dev->handle, buffer3, avail);	// read samples
		if (frames == -EAGAIN) {	// no samples available
			break;
		}
		else if (frames <= 0) {		// error
			dev->dev_error++;
#if DEBUG_IO
			QuiskPrintTime("read_alsa: frames < 0", 0);
#endif
			snd_pcm_prepare (dev->handle);
			snd_pcm_start (dev->handle);
			break;
		}
		for (i = 0; frames; i += dev->num_channels, nSamples++, frames--) {
			ii = qq = 0;
			if (!is_little_endian) {	// convert to big-endian
				*((unsigned char *)&ii    ) = buffer3[(i + dev->channel_I) * 3 + 2];
				*((unsigned char *)&ii + 1) = buffer3[(i + dev->channel_I) * 3 + 1];
				*((unsigned char *)&ii + 2) = buffer3[(i + dev->channel_I) * 3    ];
				*((unsigned char *)&qq    ) = buffer3[(i + dev->channel_Q) * 3 + 2];
				*((unsigned char *)&qq + 1) = buffer3[(i + dev->channel_Q) * 3 + 1];
				*((unsigned char *)&qq + 2) = buffer3[(i + dev->channel_Q) * 3    ];
			}
			else {		// convert to little-endian
				memcpy((unsigned char *)&ii + 1, buffer3 + (i + dev->channel_I) * 3, 3);
				memcpy((unsigned char *)&qq + 1, buffer3 + (i + dev->channel_Q) * 3, 3);
			}
			if (ii >=  CLIP32 || ii <= -CLIP32)
				dev->overrange++;	// assume overrange returns max int
			if (qq >=  CLIP32 || qq <= -CLIP32)
				dev->overrange++;
			cSamples[nSamples] = ii + I * qq;
		}
		break;
	case 4:
		frames = snd_pcm_readi (dev->handle, buffer4, avail);	// read samples
		if (frames == -EAGAIN) {	// no samples available
			break;
		}
		else if (frames <= 0) {		// error
			dev->dev_error++;
#if DEBUG_IO
			QuiskPrintTime("read_alsa: frames < 0", 0);
#endif
			snd_pcm_prepare (dev->handle);
			snd_pcm_start (dev->handle);
			break;
		}
		for (i = 0; frames; i += dev->num_channels, nSamples++, frames--) {
			ii = buffer4[i + dev->channel_I];
			qq = buffer4[i + dev->channel_Q];
			if (ii >=  CLIP32 || ii <= -CLIP32)
				dev->overrange++;	// assume overrange returns max int
			if (qq >=  CLIP32 || qq <= -CLIP32)
				dev->overrange++;
			cSamples[nSamples] = ii + I * qq;
		}
		break;
	}
	for (i = 0; i < nSamples; i++) {	// DC removal; R.G. Lyons page 553
		c = cSamples[i] + dev->dc_remove * 0.95;
		cSamples[i] = c - dev->dc_remove;
		dev->dc_remove = c;
	}
	return nSamples;
}

void quisk_play_alsa(struct sound_dev * playdev, int nSamples,
		complex double * cSamples, int report_latency, double volume)
{	// Play the samples; write them to the ALSA soundcard.
	int i, n, index;
	snd_pcm_sframes_t frames, delay;
	int ii, qq;
#if DEBUG_IO
	static int timer=0;
#endif

	if (!playdev->handle || nSamples <= 0)
		return;
// Note: snd_pcm_delay() is not reliable when using the "default" ALSA device and
// arbitrary sample rates.  It seems to be confused by the rate conversion.  So we
// are changing rates (decimate) ourselves.
//
	switch(snd_pcm_state(playdev->handle)) {
	case SND_PCM_STATE_RUNNING:
		//printf("State RUNNING\n");
		snd_pcm_delay(playdev->handle, &delay);	// samples left in play buffer
		break;
	case SND_PCM_STATE_PREPARED:
#if DEBUG_IO
		//QuiskPrintTime("play_alsa: State PREPARED", 0);
#endif
		snd_pcm_delay(playdev->handle, &delay);
		delay = 0;
		break;
	case SND_PCM_STATE_XRUN:
#if DEBUG_IO
		QuiskPrintTime("", 0);
		printf("play_alsa: Play underrun; nSamples %d\n", nSamples);
#endif
		quisk_sound_state.underrun_error++;
		playdev->dev_underrun++;
		snd_pcm_prepare(playdev->handle);
		delay = 0;
		break;
	default:
#if DEBUG_IO
		QuiskPrintTime("play_alsa: State UNKNOWN", 0);
#endif
		delay = 0;
		break;
	}
	playdev->dev_latency = delay;
	if (report_latency) {		// Report for main playback device
		quisk_sound_state.latencyPlay = delay;		// samples left in play buffer
	}
	// There will be additional samples available to read in the capture buffer.
	index = 0;
#if CORRECT_PLAY_RATE
#if DEBUG_IO
	timer += nSamples;
	if (timer > playdev->sample_rate) {
		timer = 0;
		printf("play_alsa %s: Samples new %d old %ld total %ld latency_frames %d\n", playdev->name, nSamples, delay, nSamples + delay, playdev->latency_frames);
	}
#endif
	if (nSamples + delay > playdev->latency_frames * 9 / 10) {
		nSamples--;
#if DEBUG_IO
		printf("play_alsa %s: Remove a sample nSamples %d  delay %d  total %d\n", playdev->name, nSamples, (int)delay, nSamples + (int)delay);
#endif
	}
	else if(nSamples + delay < playdev->latency_frames * 5 / 10) {
		cSamples[nSamples] = cSamples[nSamples - 1];
		nSamples++;
#if DEBUG_IO
		printf ("play_alsa %s: Add a sample nSamples %d  delay %d  total %d\n", playdev->name, nSamples, (int)delay, nSamples + (int)delay);
#endif
	}
#endif
	if (nSamples + delay > playdev->latency_frames) {
		index = nSamples + delay - playdev->latency_frames;	// write only the most recent samples
		quisk_sound_state.write_error++;
		playdev->dev_error++;
#if DEBUG_IO
		//QuiskPrintTime("", 0);
		printf("play_alsa %s: Discard %d of %d samples at %ld delay\n", playdev->name, index, nSamples, delay);
#endif
	}

	if (playdev->sample_bytes == 2) {
		while (index < nSamples) {
			for (i = 0, n = index; n < nSamples; i += playdev->num_channels, n++) {
				ii = (int)(volume * creal(cSamples[n]) / 65536);
				qq = (int)(volume * cimag(cSamples[n]) / 65536);
				buffer2[i + playdev->channel_I] = (short)ii;
				buffer2[i + playdev->channel_Q] = (short)qq;
			}
			n = n - index;
			frames = snd_pcm_writei (playdev->handle, buffer2, n);
			if (frames <= 0) {
#if DEBUG_IO
				QuiskPrintTime("play_alsa: frames < 0", 0);
#endif
				if (frames == -EPIPE) {	// underrun
					quisk_sound_state.underrun_error++;
					playdev->dev_underrun++;
				}
				else {
					quisk_sound_state.write_error++;
					playdev->dev_error++;
				}
				snd_pcm_prepare(playdev->handle);
				frames = snd_pcm_writei (playdev->handle, buffer2, n);
				if (frames <= 0) {
					index = nSamples;	// give up
				}
				else {
					index += frames;
				}
			}
			else {
				index += frames;
			}
		}
	}
	else if (playdev->sample_bytes == 3) {
		while (index < nSamples) {
			for (i = 0, n = index; n < nSamples; i += playdev->num_channels, n++) {
				ii = (int)(volume * creal(cSamples[n]) / 256);
				qq = (int)(volume * cimag(cSamples[n]) / 256);
				if (!is_little_endian) {	// convert to big-endian
					buffer3[(i + playdev->channel_I) * 3    ] = *((unsigned char *)&ii + 2);
					buffer3[(i + playdev->channel_Q) * 3    ] = *((unsigned char *)&qq + 2);
					buffer3[(i + playdev->channel_I) * 3 + 1] = *((unsigned char *)&ii + 1);
					buffer3[(i + playdev->channel_Q) * 3 + 1] = *((unsigned char *)&qq + 1);
					buffer3[(i + playdev->channel_I) * 3 + 2] = *((unsigned char *)&ii    );
					buffer3[(i + playdev->channel_Q) * 3 + 2] = *((unsigned char *)&qq    );
				}
				else {	// convert to little-endian
					memcpy(buffer3 + (i + playdev->channel_I) * 3, (unsigned char *)&ii + 1, 3);
					memcpy(buffer3 + (i + playdev->channel_Q) * 3, (unsigned char *)&qq + 1, 3);
				}
			}
			n = n - index;
			frames = snd_pcm_writei (playdev->handle, buffer3, n);
			if (frames <= 0) {
#if DEBUG_IO
				QuiskPrintTime("play_alsa: frames < 0", 0);
#endif
				if (frames == -EPIPE) {	// underrun
					quisk_sound_state.underrun_error++;
					playdev->dev_underrun++;
				}
				else {
					quisk_sound_state.write_error++;
					playdev->dev_error++;
				}
				snd_pcm_prepare(playdev->handle);
				frames = snd_pcm_writei (playdev->handle, buffer3, n);
				if (frames <= 0) {
					index = nSamples;	// give up
				}
				else {
					index += frames;
				}
			}
			else {
				index += frames;
			}
		}
	}
	else if (playdev->sample_bytes == 4) {
		while (index < nSamples) {
			for (i = 0, n = index; n < nSamples; i += playdev->num_channels, n++) {
				ii = (int)(volume * creal(cSamples[n]));
				qq = (int)(volume * cimag(cSamples[n]));
				buffer4[i + playdev->channel_I] = ii;
				buffer4[i + playdev->channel_Q] = qq;
			}
			n = n - index;
			frames = snd_pcm_writei (playdev->handle, buffer4, n);
			if (frames <= 0) {
#if DEBUG_IO
				QuiskPrintTime("play_alsa: frames < 0", 0);
#endif
				if (frames == -EPIPE) {	// underrun
					quisk_sound_state.underrun_error++;
					playdev->dev_underrun++;
				}
				else {
					quisk_sound_state.write_error++;
					playdev->dev_error++;
				}
				snd_pcm_prepare(playdev->handle);
				frames = snd_pcm_writei (playdev->handle, buffer4, n);
				if (frames <= 0) {
					index = nSamples;	// give up
				}
				else {
					index += frames;
				}
			}
			else {
				index += frames;
			}
		}
	}
}

static int device_list(PyObject * py, snd_pcm_stream_t stream, char * name)
{	// return 1 if the card name was substituted
	snd_ctl_t *handle;
	int card, err, dev;
	char buf100[100];
	const char * card_text, * pcm_text;
	snd_ctl_card_info_t *info;
	snd_pcm_info_t *pcminfo;

	snd_ctl_card_info_alloca(&info);
	snd_pcm_info_alloca(&pcminfo);

	card = -1;
	if (snd_card_next(&card) < 0 || card < 0) {
		printf("no soundcards found...\n");
		return 0;
	}
	while (card >= 0) {
		sprintf(buf100, "hw:%d", card);
		if ((err = snd_ctl_open(&handle, buf100, 0)) < 0) {
			printf("device_list: control open (%i): %s", card, snd_strerror(err));
			goto next_card;
		}
		if ((err = snd_ctl_card_info(handle, info)) < 0) {
			printf("device_list: control hardware info (%i): %s", card, snd_strerror(err));
			snd_ctl_close(handle);
			goto next_card;
		}
		dev = -1;
		while (1) {
			if (snd_ctl_pcm_next_device(handle, &dev)<0)
				printf("device_list: snd_ctl_pcm_next_device\n");
			if (dev < 0)
				break;
			snd_pcm_info_set_device(pcminfo, dev);
			snd_pcm_info_set_subdevice(pcminfo, 0);
			snd_pcm_info_set_stream(pcminfo, stream);
			card_text = snd_ctl_card_info_get_name(info);
			if ( ! card_text || ! card_text[0])
				card_text = snd_ctl_card_info_get_id(info);
			if ((err = snd_ctl_pcm_info(handle, pcminfo)) < 0) {
				if (err != -ENOENT)
					printf ("device_list: control digital audio info (%i): %s", card, snd_strerror(err));
				continue;
			}
			else {
				pcm_text = snd_pcm_info_get_name(pcminfo);
				if ( ! pcm_text || ! pcm_text[0])
					pcm_text = snd_pcm_info_get_id(pcminfo);
			}
			snprintf(buf100, 100, "%s %s (hw:%d,%d)", card_text, pcm_text, card, dev);
			if (py) {		// add to list of devices
				PyList_Append(py, PyString_FromString(buf100));
			}
			if (name) {		// return the "hw:" name
				if (strstr(buf100, name)) {
					snprintf(name, QUISK_SC_SIZE, "hw:%d,%d", card, dev);
					snd_ctl_close(handle);
					return 1;
				}
			}
		}
		snd_ctl_close(handle);
	next_card:
		if (snd_card_next(&card) < 0) {
			printf("snd_card_next\n");
			break;
		}
	}
	return 0;
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
	device_list(pycapt, SND_PCM_STREAM_CAPTURE, NULL);
	device_list(pyplay, SND_PCM_STREAM_PLAYBACK, NULL);
	return pylist;
}

static snd_pcm_format_t check_formats(struct sound_dev * dev, snd_pcm_hw_params_t *hware)
{
	snd_pcm_format_t format = SND_PCM_FORMAT_UNKNOWN;
	dev->sample_bytes = 0;

	strncpy (dev->msg1, "Available formats: ", QUISK_SC_SIZE);
	if (snd_pcm_hw_params_test_format (dev->handle, hware, SND_PCM_FORMAT_S32) == 0) {
		if (!dev->sample_bytes) {
			strncat(dev->msg1, "*", QUISK_SC_SIZE);
			dev->sample_bytes = 4;
			format = SND_PCM_FORMAT_S32;
		}
		strncat(dev->msg1, "S32 ", QUISK_SC_SIZE);
	}
	if (snd_pcm_hw_params_test_format (dev->handle, hware, SND_PCM_FORMAT_U32) == 0) {
		strncat(dev->msg1, "U32 ", QUISK_SC_SIZE);
	}
	if (snd_pcm_hw_params_test_format (dev->handle, hware, SND_PCM_FORMAT_S24) == 0) {
		strncat(dev->msg1, "S24 ", QUISK_SC_SIZE);
	}
	if (snd_pcm_hw_params_test_format (dev->handle, hware, SND_PCM_FORMAT_U24) == 0) {
		strncat(dev->msg1, "U24 ", QUISK_SC_SIZE);
	}
	if (snd_pcm_hw_params_test_format (dev->handle, hware, SND_PCM_FORMAT_S24_3LE) == 0) {
		if (!dev->sample_bytes) {
			strncat(dev->msg1, "*", QUISK_SC_SIZE);
			dev->sample_bytes = 3;
			format = SND_PCM_FORMAT_S24_3LE;
		}
		strncat(dev->msg1, "S24_3LE ", QUISK_SC_SIZE);
	}
	if (snd_pcm_hw_params_test_format (dev->handle, hware, SND_PCM_FORMAT_S16) == 0) {
		if (!dev->sample_bytes) {
			strncat(dev->msg1, "*", QUISK_SC_SIZE);
			dev->sample_bytes = 2;
			format = SND_PCM_FORMAT_S16;
		}
		strncat(dev->msg1, "S16 ", QUISK_SC_SIZE);
	}
	if (snd_pcm_hw_params_test_format (dev->handle, hware, SND_PCM_FORMAT_U16) == 0) {
		strncat(dev->msg1, "U16 ", QUISK_SC_SIZE);
	}
	if (format == SND_PCM_FORMAT_UNKNOWN)
		strncat(dev->msg1, "*UNSUPPORTED", QUISK_SC_SIZE);
	else
		snd_pcm_hw_params_set_format (dev->handle, hware, format);
	return format;
}

static int quisk_open_alsa_capture(struct sound_dev * dev)
{	// Open the ALSA soundcard for capture.  Return non-zero for error.
	int err, dir, sample_rate;
	int poll_size;
	unsigned int ui;
	snd_pcm_hw_params_t *hware;
	snd_pcm_sw_params_t *sware;
	snd_pcm_uframes_t frames;
	snd_pcm_t * handle;

	if ( ! dev->name[0])	// Check for null capture name
		return 0;

#if DEBUG_IO
	printf("*** Capture on alsa device %s\n", dev->name);
#endif
	if ( ! strncmp (dev->name, "alsa:", 5)) {	// search for the name in info strings
		char buf[QUISK_SC_SIZE];
		strncpy(buf, dev->name + 5, QUISK_SC_SIZE);
		device_list(NULL, SND_PCM_STREAM_CAPTURE, buf);
		err = snd_pcm_open (&handle, buf, SND_PCM_STREAM_CAPTURE, 0);
	}
	else {		// just try to open the name
		err = snd_pcm_open (&handle, dev->name, SND_PCM_STREAM_CAPTURE, 0);
	}
	if (err < 0) {
		snprintf(quisk_sound_state.err_msg, QUISK_SC_SIZE, "Cannot open capture device %s (%s)",
				dev->name, snd_strerror (err));
		return 1;
	}
	dev->handle = handle;
	dev->driver = DEV_DRIVER_ALSA;
	if ((err = snd_pcm_sw_params_malloc (&sware)) < 0) {
		snprintf (quisk_sound_state.err_msg, QUISK_SC_SIZE, "Cannot allocate software parameter structure (%s)\n",
				snd_strerror (err));
		return 1;
	}
	if ((err = snd_pcm_hw_params_malloc (&hware)) < 0) {
		snprintf (quisk_sound_state.err_msg, QUISK_SC_SIZE, "Cannot allocate hardware parameter structure (%s)\n",
				snd_strerror (err));
		snd_pcm_sw_params_free (sware);
		return 1;
	}
	if ((err = snd_pcm_hw_params_any (handle, hware)) < 0) {
		snprintf (quisk_sound_state.err_msg, QUISK_SC_SIZE, "Cannot initialize capture parameters (%s)\n",
				snd_strerror (err));
		goto errend;
	}
	/* UNAVAILABLE
	if ((err = snd_pcm_hw_params_set_rate_resample (handle, hware, 0)) < 0) {
		snprintf (quisk_sound_state.err_msg, QUISK_SC_SIZE, "Cannot disable resampling (%s)\n",
			snd_strerror (err));
		goto errend;
	}
	*/
	// Get some parameters to send back
	if (snd_pcm_hw_params_get_rate_min(hware, &dev->rate_min, &dir) != 0)
		dev->rate_min = 0;	// Error
	if (snd_pcm_hw_params_get_rate_max(hware, &dev->rate_max, &dir) != 0)
		dev->rate_max = 0;	// Error
	if (snd_pcm_hw_params_get_channels_min(hware, &dev->chan_min) != 0)
		dev->chan_min= 0;	// Error
	if (snd_pcm_hw_params_get_channels_max(hware, &dev->chan_max) != 0)
		dev->chan_max= 0;	// Error
#if DEBUG_IO
	printf("Sample rate min %d  max %d\n",  dev->rate_min, dev->rate_max);
	printf("Number of channels min %d  max %d\n",  dev->chan_min, dev->chan_max);
#endif
	// Set the capture parameters
	if (check_formats(dev, hware) == SND_PCM_FORMAT_UNKNOWN) {
		strncpy(quisk_sound_state.msg1, dev->msg1, QUISK_SC_SIZE);
		strncpy (quisk_sound_state.err_msg, "Quisk does not support your capture format.", QUISK_SC_SIZE);
		goto errend;
	}
	strncpy(quisk_sound_state.msg1, dev->msg1, QUISK_SC_SIZE);
	sample_rate = dev->sample_rate;
	if (snd_pcm_hw_params_set_rate (handle, hware, sample_rate, 0) < 0) {
		snprintf (quisk_sound_state.err_msg, QUISK_SC_SIZE, "Can not set sample rate %d",
			sample_rate);
		goto errend;
	}
	if (snd_pcm_hw_params_set_access (handle, hware, SND_PCM_ACCESS_RW_INTERLEAVED) < 0) {
		strncpy(quisk_sound_state.err_msg, "Interleaved access is not available", QUISK_SC_SIZE);
		goto errend;
	}
	if (snd_pcm_hw_params_get_channels_min(hware, &ui) != 0)
		ui = 0;	// Error
	if (dev->num_channels < ui)		// increase number of channels to minimum available
		dev->num_channels = ui;
	if (snd_pcm_hw_params_set_channels (handle, hware, dev->num_channels) < 0) {
		snprintf (quisk_sound_state.err_msg, QUISK_SC_SIZE, "Can not set channels to %d", dev->num_channels);
		goto errend;
	}
	// Try to set a capture buffer larger than needed
	frames = sample_rate * 200 / 1000;	// buffer size in milliseconds
	if (snd_pcm_hw_params_set_buffer_size_near (handle, hware, &frames) < 0) {
		snprintf (quisk_sound_state.err_msg, QUISK_SC_SIZE, "Can not set capture buffer size");
		goto errend;
	}
	poll_size = (int)(quisk_sound_state.data_poll_usec * 1e-6 * sample_rate + 0.5);
	if (frames < poll_size * 3) {		// buffer size is too small, reduce poll time
		quisk_sound_state.data_poll_usec = (int)(frames * 1.e6 / sample_rate / 3 + 0.5);
#if DEBUG_IO
		printf("Reduced data_poll_usec %d for small sound capture buffer\n",
			quisk_sound_state.data_poll_usec);
#endif
	}
#if DEBUG_IO
	printf("sample rate %d\n", sample_rate);
	printf("num_channels %d, %s\n", dev->num_channels, dev->msg1);
	printf("Capture buffer size %d\n", (int)frames);
	if (frames > SAMP_BUFFER_SIZE / dev->num_channels)
		printf("Capture buffer exceeds size of sample buffers\n");
#endif
	if ((err = snd_pcm_hw_params (handle, hware)) < 0) {
		snprintf (quisk_sound_state.err_msg, QUISK_SC_SIZE, "Cannot set hw capture parameters (%s)\n",
				snd_strerror (err));
		goto errend;
	}
	if ((err = snd_pcm_sw_params_current (handle, sware)) < 0) {
		snprintf (quisk_sound_state.err_msg, QUISK_SC_SIZE, "Cannot get software capture parameters (%s)\n",
				snd_strerror (err));
		goto errend;
	}

	if ((err = snd_pcm_prepare (handle)) < 0) {
		snprintf (quisk_sound_state.err_msg, QUISK_SC_SIZE, "Cannot prepare capture interface for use (%s)\n",
			snd_strerror (err));
		goto errend;
	}
	// Success
	snd_pcm_hw_params_free (hware);
	snd_pcm_sw_params_free (sware);
#if DEBUG_IO
    printf("*** End capture on alsa device %s %s\n", dev->name, quisk_sound_state.err_msg);
#endif
	return 0;
errend:
	snd_pcm_hw_params_free (hware);
	snd_pcm_sw_params_free (sware);
#if DEBUG_IO
    printf("*** Error end for capture on alsa device %s %s\n", dev->name, quisk_sound_state.err_msg);
#endif
	return 1;
}

static int quisk_open_alsa_playback(struct sound_dev * dev)
{	// Open the ALSA soundcard for playback.  Return non-zero on error.
	int err, dir, sample_rate;
	unsigned int ui;
	snd_pcm_hw_params_t *hware;
	snd_pcm_sw_params_t *sware;
	snd_pcm_uframes_t frames;
	snd_pcm_t * handle;

	if ( ! dev->name[0])	// Check for null play name
		return 0;

#if DEBUG_IO
	printf("*** Playback on alsa device %s\n", dev->name);
	printf("quisk_open_alsa_playback(): %s\n", dev->stream_description);
#endif
	if ( ! strncmp (dev->name, "alsa:", 5)) {	// search for the name in info strings
		char buf[QUISK_SC_SIZE];
		strncpy(buf, dev->name + 5, QUISK_SC_SIZE);
		device_list(NULL, SND_PCM_STREAM_PLAYBACK, buf);
		err = snd_pcm_open (&handle, buf, SND_PCM_STREAM_PLAYBACK, 0);
	}
	else {		// just try to open the name
		err = snd_pcm_open (&handle, dev->name, SND_PCM_STREAM_PLAYBACK, 0);
	}
	if (err < 0) {
		snprintf (quisk_sound_state.err_msg, QUISK_SC_SIZE, "Cannot open playback device %s (%s)\n",
				dev->name, snd_strerror (err));
		return 1;
	}
	dev->handle = handle;
	if ((err = snd_pcm_sw_params_malloc (&sware)) < 0) {
		snprintf (quisk_sound_state.err_msg, QUISK_SC_SIZE, "Cannot allocate software parameter structure (%s)\n",
				snd_strerror (err));
		return 1;
	}
	if ((err = snd_pcm_hw_params_malloc (&hware)) < 0) {
		snprintf (quisk_sound_state.err_msg, QUISK_SC_SIZE, "Cannot allocate hardware parameter structure (%s)\n",
				snd_strerror (err));
		snd_pcm_sw_params_free (sware);
		return 1;
	}
	if ((err = snd_pcm_hw_params_any (handle, hware)) < 0) {
		snprintf (quisk_sound_state.err_msg, QUISK_SC_SIZE, "Cannot initialize playback parameter structure (%s)\n",
				snd_strerror (err));
		goto errend;
	}
	// Get some parameters to send back
	if (snd_pcm_hw_params_get_rate_min(hware, &dev->rate_min, &dir) != 0)
		dev->rate_min = 0;	// Error
	if (snd_pcm_hw_params_get_rate_max(hware, &dev->rate_max, &dir) != 0)
		dev->rate_max = 0;	// Error
	if (snd_pcm_hw_params_get_channels_min(hware, &dev->chan_min) != 0)
		dev->chan_min= 0;	// Error
	if (snd_pcm_hw_params_get_channels_max(hware, &dev->chan_max) != 0)
		dev->chan_max= 0;	// Error
#if DEBUG_IO
	printf("Sample rate min %d  max %d\n",  dev->rate_min, dev->rate_max);
	printf("Number of channels min %d  max %d\n",  dev->chan_min, dev->chan_max);
#endif
	// Set the playback parameters
	sample_rate = dev->sample_rate;
	if (snd_pcm_hw_params_set_rate (handle, hware, sample_rate, 0) < 0) {
		snprintf (quisk_sound_state.err_msg, QUISK_SC_SIZE, "Cannot set playback rate %d",
			sample_rate);
		goto errend;
	}
	if (snd_pcm_hw_params_set_access (handle, hware, SND_PCM_ACCESS_RW_INTERLEAVED) < 0) {
		snprintf (quisk_sound_state.err_msg, QUISK_SC_SIZE, "Cannot set playback access to interleaved.");
		goto errend;
	}
	if (snd_pcm_hw_params_get_channels_min(hware, &ui) != 0)
		ui = 0;	// Error
	if (dev->num_channels < ui)		// increase number of channels to minimum available
		dev->num_channels = ui;
	if (snd_pcm_hw_params_set_channels (handle, hware, dev->num_channels) < 0) {
		snprintf (quisk_sound_state.err_msg, QUISK_SC_SIZE, "Cannot set playback channels to %d",
			dev->num_channels);
		goto errend;
	}
	if (check_formats(dev, hware) == SND_PCM_FORMAT_UNKNOWN) {
		strncpy(quisk_sound_state.msg1, dev->msg1, QUISK_SC_SIZE);
		snprintf (quisk_sound_state.err_msg, QUISK_SC_SIZE, "Cannot set playback format.");
		goto errend;
	}
	// Try to set a play buffer larger than needed
	frames = sample_rate * 200 / 1000;	// buffer size in milliseconds
	if (snd_pcm_hw_params_set_buffer_size_near (handle, hware, &frames) < 0) {
		snprintf (quisk_sound_state.err_msg, QUISK_SC_SIZE, "Can not set playback buffer size");
		goto errend;
	}
	dev->play_buf_size = frames;
#if DEBUG_IO
	printf("num_channels %d, %s\n", dev->num_channels, dev->msg1);
	printf("Playback buffer size %d\n", dev->play_buf_size);
#endif
	if ((err = snd_pcm_hw_params (handle, hware)) < 0) {
		snprintf (quisk_sound_state.err_msg, QUISK_SC_SIZE, "Cannot set playback hw_params (%s)\n",
			snd_strerror (err));
		goto errend;
	}
	if ((err = snd_pcm_sw_params_current (handle, sware)) < 0) {
		snprintf (quisk_sound_state.err_msg, QUISK_SC_SIZE, "Cannot get software playback parameters (%s)\n",
				snd_strerror (err));
		goto errend;
	}
	if (dev->latency_frames > dev->play_buf_size) {
		dev->latency_frames = dev->play_buf_size;
#if DEBUG_IO
		printf("Latency frames limited to buffer size\n");
#endif
	}
#if DEBUG_IO
	printf("Audio rate %d latency_frames %d\n", sample_rate, dev->latency_frames);
#endif
	if (snd_pcm_sw_params_set_start_threshold (handle, sware, dev->latency_frames * 7 / 10) < 0) {
		snprintf (quisk_sound_state.err_msg, QUISK_SC_SIZE, "Cannot set start threshold\n");
		goto errend;
	}
	if ((err = snd_pcm_sw_params (handle, sware)) < 0) {
		snprintf (quisk_sound_state.err_msg, QUISK_SC_SIZE, "Cannot set playback sw_params (%s)\n",
			snd_strerror (err));
		goto errend;
	}
#if DEBUG_IO
		snd_pcm_sw_params_get_silence_threshold(sware, &frames);
		printf("play silence threshold %d\n", (int)frames);
		snd_pcm_sw_params_get_silence_size(sware, &frames);
		printf("play silence size %d\n", (int)frames);
		snd_pcm_sw_params_get_start_threshold(sware, &frames);
		printf("play start threshold %d\n", (int)frames);
		printf ("play channels are %d %d\n", dev->channel_I, dev->channel_Q);
#endif
	if ((err = snd_pcm_prepare (handle)) < 0) {
		snprintf (quisk_sound_state.err_msg, QUISK_SC_SIZE, "Cannot prepare playback interface for use (%s)\n",
			snd_strerror (err));
		goto errend;
	}
	// Success
	snd_pcm_hw_params_free (hware);
	snd_pcm_sw_params_free (sware);
#if DEBUG_IO
    printf("*** End playback on alsa device %s %s\n", dev->name, quisk_sound_state.err_msg);
#endif
	return 0;
errend:
	snd_pcm_hw_params_free (hware);
	snd_pcm_sw_params_free (sware);
#if DEBUG_IO
    printf("*** Error end for playback on alsa device %s %s\n", dev->name, quisk_sound_state.err_msg);
#endif
	return 1;
}

void quisk_start_sound_alsa (struct sound_dev ** pCapture, struct sound_dev ** pPlayback)
{
	struct sound_dev * pDev;

	memset(bufferz, 0, sizeof(int) * SAMP_BUFFER_SIZE);
	is_little_endian = 1;	// Test machine byte order
	if (*(char *)&is_little_endian == 1)
		is_little_endian = 1;
	else
		is_little_endian = 0;
	if (quisk_sound_state.err_msg[0])
		return;		// prior error
	// Open the alsa playback devices
	while (1) {
		pDev = *pPlayback++;
		if ( ! pDev)
			break;
		if ( ! pDev->handle && pDev->driver == DEV_DRIVER_ALSA)
			if (quisk_open_alsa_playback(pDev))
				return;		// error
	}
	// Open the alsa capture devices and start them
	while (1) {
		pDev = *pCapture++;
		if ( ! pDev)
			break;
		if ( ! pDev->handle && pDev->driver == DEV_DRIVER_ALSA) {
			if (quisk_open_alsa_capture(pDev))
				return;		// error
			if (pDev->handle)
				snd_pcm_start((snd_pcm_t *)pDev->handle);
		}
	}
}

void quisk_close_sound_alsa(struct sound_dev ** pCapture, struct sound_dev ** pPlayback)
{
	struct sound_dev * pDev;

	while (*pCapture) {
		pDev = *pCapture;
		if (pDev->handle && pDev->driver == DEV_DRIVER_ALSA) {
			snd_pcm_drop((snd_pcm_t *)pDev->handle);
			snd_pcm_close((snd_pcm_t *)pDev->handle);
		}
		pDev->handle = NULL;
		pDev->driver = DEV_DRIVER_NONE;
		pCapture++;
	}
	while (*pPlayback) {
		pDev = *pPlayback;
		if (pDev->handle && pDev->driver == DEV_DRIVER_ALSA) {
			snd_pcm_drop((snd_pcm_t *)pDev->handle);
			snd_pcm_close((snd_pcm_t *)pDev->handle);
		}
		pDev->handle = NULL;
		pDev->driver = DEV_DRIVER_NONE;
		pPlayback++;
	}
}

void quisk_mixer_set(char * card_name, int numid, PyObject * value, char * err_msg, int err_size)
// Set card card_name mixer control numid to value for integer, boolean, enum controls.
// If value is a float, interpret value as a decimal fraction of min/max.
{
	int err;
	static snd_ctl_t * handle = NULL;
	snd_ctl_elem_info_t *info;
	snd_ctl_elem_id_t * id;
	snd_ctl_elem_value_t * control;
	unsigned int idx;
	long imin, imax, tmp;
	snd_ctl_elem_type_t type;
	unsigned int count;

	snd_ctl_elem_info_alloca(&info);
	snd_ctl_elem_id_alloca(&id);
	snd_ctl_elem_value_alloca(&control);

	err_msg[0] = 0;

	snd_ctl_elem_id_set_interface(id, SND_CTL_ELEM_IFACE_MIXER);
	snd_ctl_elem_id_set_numid(id, numid);
	//snd_ctl_elem_id_set_index(id, index);
	//snd_ctl_elem_id_set_device(id, device);
	//snd_ctl_elem_id_set_subdevice(id, subdevice);
	if ( ! strncmp (card_name, "alsa:", 5)) {	// search for the name in info strings
		char buf[QUISK_SC_SIZE];
		strncpy(buf, card_name + 5, QUISK_SC_SIZE);
		if ( ! device_list(NULL, SND_PCM_STREAM_CAPTURE, buf))	// check capture and play names
			device_list(NULL, SND_PCM_STREAM_PLAYBACK, buf);
		buf[4] = 0;		// Remove device nuumber
		err = snd_ctl_open(&handle, buf, 0);
	}
	else {		// just try to open the name
		err = snd_ctl_open(&handle, card_name, 0);
	}
	if (err < 0) {
		snprintf (err_msg, err_size, "Control %s open error: %s\n", card_name, snd_strerror(err));
		return;
	}
	snd_ctl_elem_info_set_id(info, id);
	if ((err = snd_ctl_elem_info(handle, info)) < 0) {
		snprintf (err_msg, err_size, "Cannot find the given element from control %s\n", card_name);
		return;
	}
	snd_ctl_elem_info_get_id(info, id);
	type = snd_ctl_elem_info_get_type(info);
	snd_ctl_elem_value_set_id(control, id);
	count = snd_ctl_elem_info_get_count(info);
	
	for (idx = 0; idx < count; idx++) {
		switch (type) {
		case SND_CTL_ELEM_TYPE_BOOLEAN:
			if (PyObject_IsTrue(value))
				snd_ctl_elem_value_set_boolean(control, idx, 1);
			else
				snd_ctl_elem_value_set_boolean(control, idx, 0);
			break;
		case SND_CTL_ELEM_TYPE_INTEGER:
			imin = snd_ctl_elem_info_get_min(info);
			imax = snd_ctl_elem_info_get_max(info);
			if (PyFloat_CheckExact(value)) {
				tmp = (long)(imin + (imax - imin) * PyFloat_AsDouble(value) + 0.4);
				snd_ctl_elem_value_set_integer(control, idx, tmp);
			}
			else if(PyInt_Check(value)) {
				tmp = PyInt_AsLong(value);
				snd_ctl_elem_value_set_integer(control, idx, tmp);
			}
			else {
				snprintf (err_msg, err_size, "Control %s id %d has bad value\n", card_name, numid);
			}
			break;
		case SND_CTL_ELEM_TYPE_INTEGER64:
			imin = snd_ctl_elem_info_get_min64(info);
			imax = snd_ctl_elem_info_get_max64(info);
			if (PyFloat_CheckExact(value)) {
				tmp = (long)(imin + (imax - imin) * PyFloat_AsDouble(value) + 0.4);
				snd_ctl_elem_value_set_integer64(control, idx, tmp);
			}
			else if(PyInt_Check(value)) {
				tmp = PyInt_AsLong(value);
				snd_ctl_elem_value_set_integer64(control, idx, tmp);
			}
			else {
				snprintf (err_msg, err_size, "Control %s id %d has bad value\n", card_name, numid);
			}
			break;
		case SND_CTL_ELEM_TYPE_ENUMERATED:
			if(PyInt_Check(value)) {
				tmp = PyInt_AsLong(value);
				snd_ctl_elem_value_set_enumerated(control, idx, (unsigned int)tmp);
			}
			else {
				snprintf (err_msg, err_size, "Control %s id %d has bad value\n", card_name, numid);
			}
			break;
		default:
			snprintf (err_msg, err_size, "Control %s element has unknown type\n", card_name);
			break;
		}
		if ((err = snd_ctl_elem_write(handle, control)) < 0) {
			snprintf (err_msg, err_size, "Control %s element write error: %s\n", card_name, snd_strerror(err));
			return;
		}
	}
	snd_ctl_close(handle);
	return;
}

