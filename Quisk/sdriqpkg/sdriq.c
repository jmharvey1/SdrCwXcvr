#include <Python.h>

#ifdef MS_WINDOWS
#include <windows.h>
#include "ftd2xx.h"
#elif defined(__MACH__)
// Changes for MacOS support (__MACH__) thanks to Mario, DL3LSM.
#include "ftd2xx.h"
#else
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/time.h>
#include <time.h>
#include <fcntl.h>
#include <termios.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <stdlib.h>
#include <unistd.h>
#endif

#include <complex.h>

#define IMPORT_QUISK_API
#include "quisk.h"
#include "sdriq.h"

// This module provides access to the SDR-IQ by RfSpace.  It is the source
// for the Python extension module sdriq.  It can be used as a model for an
// extension module for other hardware.  Read the end of this file for more
// information.  This module was written by James Ahlstrom, N2ADR.

// This module uses the Python interface to import symbols from the parent _quisk
// extension module.  It must be linked with import_quisk_api.c.  See the documentation
// at the start of import_quisk_api.c.

// Start of SDR-IQ specific code:
//
#define DEBUG		0

#define SDRIQ_BLOCK		8194
#define SDRIQ_BUF_SIZE	131072
#define INC_IREAD		if (++iread >= SDRIQ_BUF_SIZE) iread = 0;

// Number of milliseconds to wait for SDR-IQ data on each read
#define SDRIQ_MSEC	4
// Timeout for SDR-IQ as a multiple of SDRIQ_MSEC
#define SDRIQ_TIMEOUT	50

// Type field for the message block header; upper 3 bits of byte
#define TYPE_HOST_SET	0
#define TYPE_HOST_GET	(1 << 5)
#define NAME_SIZE		16

static double sdriq_clock;

static int	sdr_ack;	// got ACK
static int	sdr_nak;	// got NAK
static char sdr_name[NAME_SIZE];		// control item 1
static char sdr_serial[NAME_SIZE];		// item 2
static int  sdr_interface;				// item 3
static int  sdr_firmware;				// item 4
static int  sdr_bootcode;				// item 4
static int  sdr_status;					// item 5
static int	sdr_idle;					// item 0x18, 1==idle, 2==run
static int	sdriq_freq=7220000;					// set SDR-IQ to this frequency
static int	sdriq_gstate=2, sdriq_gain=127;		// set SDR-IQ gain to this value
static int  sdriq_decimation = 360;				// set SDR-IQ decimation to this value
static int	cur_freq, cur_gstate, cur_gain;		// current value of frequency and gain
static int  cur_decimation;						// current value of decimation

// Changes for MacOS support (__MACH__) thanks to Mario, DL3LSM.
#if defined(MS_WINDOWS) || defined(__MACH__)
static FT_HANDLE quisk_sdriq_fd = INVALID_HANDLE_VALUE;

static int Read(void * buf, int bufsize)
{
	DWORD bytes, rx_bytes;

	if (quisk_sdriq_fd == INVALID_HANDLE_VALUE)
		return 0;

	if (FT_GetQueueStatus(quisk_sdriq_fd, &rx_bytes) != FT_OK) {
		pt_quisk_sound_state->read_error++;
		return 0;
	}
	if (rx_bytes > bufsize)
		rx_bytes = bufsize;
	if (rx_bytes == 0) {
		return 0;
	}
	else if (FT_Read(quisk_sdriq_fd, buf, rx_bytes, &bytes) == FT_OK) {
		return bytes;
	}
	else {
		pt_quisk_sound_state->read_error++;
		return 0;	
	}
}

static int Write(void * buf, int length)
{
	DWORD bytes;

	if (quisk_sdriq_fd == INVALID_HANDLE_VALUE)
		return 0;

	if (FT_Write(quisk_sdriq_fd, buf, length, &bytes) == FT_OK) {
		return bytes;
	}
	else {
		return 0;
	}
}
#else
#define INVALID_HANDLE_VALUE	-1
static int quisk_sdriq_fd = INVALID_HANDLE_VALUE;
static int Read(void * buf, int bufsize)
{
	int res;

	if (quisk_sdriq_fd == INVALID_HANDLE_VALUE)
		return 0;
	res = read(quisk_sdriq_fd, buf, bufsize);
	if (res < 0) {
		if (errno != EAGAIN && errno != EWOULDBLOCK) {
			pt_quisk_sound_state->read_error++;
		}
		return 0;
	}
	return res;
}

static int Write(void * buf, int length)
{
	int res;

	if (quisk_sdriq_fd == INVALID_HANDLE_VALUE)
		return 0;
	res = write(quisk_sdriq_fd, buf, length);
    if (res <= 0)
		return 0;
	return res;
}
#endif

static void update_item(int item, const unsigned char * data)
{
	switch(item) {
	case 1:
		strncpy(sdr_name, (char *)data, NAME_SIZE);
		sdr_name[NAME_SIZE - 1] = 0;
		break;
	case 2:
		strncpy(sdr_serial, (char *)data, NAME_SIZE);
		sdr_serial[NAME_SIZE - 1] = 0;
		break;
	case 3:
		sdr_interface = (data[1] << 8) | data[0];
		break;
	case 4:
		if (data[0])
			sdr_firmware = (data[2] << 8) | data[1];
		else
			sdr_bootcode = (data[2] << 8) | data[1];
		break;
	case 5:
		sdr_status = data[0];
		if (data[0] == 0x20)
			pt_quisk_sound_state->overrange++;
#if DEBUG
		if (data[0] == 0x20)
			printf ("Got overrange (clip)\n");
		else
			printf ("Got status 0x%X\n", data[0]);
#endif
		break;
	case 0x18:
		sdr_idle = data[1];
#if DEBUG
		if (sdr_idle == 1)
			printf ("Got idle code IDLE\n");
		else if (sdr_idle == 2)
			printf ("Got idle code RUN\n");
		else
			printf ("Got idle code UNKNOWN\n");
#endif
		break;
	}
}

static void get_item(		// Host sends a request for a control item
	int item,				// the item number
	int nparams,			// the length of params
	char * params)			// byte array of parameters, or NULL iff nparams==0
{
	int length;				// length of message block
	char buf[64];			// message block header and control item and data

	length = 4 + nparams;
	if (length > 60)
		return;		// error
	buf[0] = length & 0xFF;			// length LSB
	buf[1] = TYPE_HOST_GET | ((length >> 8) & 0x1F);	// 3-bit type and 5-bit length MSB
	buf[2] = item & 0xFF;			// item LSB
	buf[3] = (item >> 8) & 0xFF;	// item MSB
	if (nparams)
		memcpy(buf + 4, params, nparams);
	if (Write(buf, length) != length) {
		pt_quisk_sound_state->read_error++;
#if DEBUG
		printf("get_item write error\n");
#endif
	}
#if DEBUG > 1
	printf ("get_item 0x%X\n", item);
#endif
	return;
}

static void set_item(	// host command to set a control item
	int item,			// the item number
	int nparams,		// the length of params
	char * params)		// byte array of parameters, or NULL iff nparams==0
{
	int length;
	char buf[64];			// message block header and control item and data

	length = 4 + nparams;		// total length 
	if (length > 60)
		return;		// error
	buf[0] = length & 0xFF;				// length LSB
	buf[1] = TYPE_HOST_SET | ((length >> 8) & 0x1F);	// 3-bit type and 5-bit length MSB
	buf[2] = item & 0xFF;			// item LSB
	buf[3] = (item >> 8) & 0xFF;	// item MSB
	if (nparams)
		memcpy(buf + 4, params, nparams);
	if (Write(buf, length) != length) {
		pt_quisk_sound_state->read_error++;
#if DEBUG
		printf("set_item write error\n");
#endif
	}
#if DEBUG > 1
		printf ("set_item 0x%X\n", item);
#endif
}

// The ft245 driver does not have a circular buffer for input; bytes are just appended
// to the buffer.  When all bytes are read and the buffer goes empty, the pointers are reset to zero.
// Be sure to empty out the ft245 frequently so its buffer does not overflow.
static int sdr_recv(complex double * samp, int sampsize)
{		// Read all data from the SDR-IQ and process it.
		// Return the number >= 0 of I/Q data samples that are available in samp.
	int k, res, item, navail, nSamples;
	short ii, qq;
	unsigned char buf128[128];
	static unsigned char buf[SDRIQ_BUF_SIZE];
	static int iread=0;
	static int iwrite=0;
	static int state=0;
	static int length;
	static int type;
	static int sample_count;

	nSamples = 0;		// number of samples added to samp
	// first read all characters from the ft245 driver into our large buffer
	if (iread == 0) {
		k = SDRIQ_BUF_SIZE - iwrite - 1;
		if (k > 65536)		// maximum read for ft245
			k = 65536;
		if (k > 0) {
			res = Read(buf + iwrite, k);
			iwrite += res;
		}
	}
	else if (iread <= iwrite) {
		k = SDRIQ_BUF_SIZE - iwrite;
		if (k > 65536)		// maximum read for ft245
			k = 65536;
		res = Read(buf + iwrite, k);
		if (res == k)
			iwrite = 0;
		else if (res > 0)
			iwrite += res;
	}
	if (iread > iwrite) {
		k = iread - iwrite - 1;
		if (k > 65536)		// maximum read for ft245
			k = 65536;
		if (k > 0) {
			res = Read(buf + iwrite, k);
			iwrite += res;
		}
	}

	// Now process the data we have in buf
start_here:
	if (iread > iwrite)		// calculate number of available bytes: navail
		navail = SDRIQ_BUF_SIZE - iread + iwrite;
	else
		navail = iwrite - iread;
	if (state == 0) {		// starting state; we need to read the first two bytes for length and type
		if (navail < 2)
			return nSamples;		// no more data available
		// we have the first two bytes
		length = buf[iread];
		INC_IREAD
		type = (buf[iread] >> 5) & 0x7;			// 3-bit type
		length |= (buf[iread] & 0x1F) << 8;		// length including header
		INC_IREAD
#if DEBUG > 1
		if (length != 0 && !(type == 3 && length == 3))
			printf("Got message type %d length %d\n", type, length);
#endif
		if (type > 3 && length == 0)			// data block with zero length
			length = 8194;	// special data length
		length -= 2;		// we read two bytes; length is the remaining bytes
		if (length < 0) {
			state = 9;		// bad length; attempt resync
		}
		else if (length == 0) {			// NAK
			sdr_nak = 1;
#if DEBUG
			printf("Got NAK\n");
#endif
			// state remains at zero
		}
		else if (samp && length > 50 && length < 8192) {	// No such message; we are out of sync
			state = 9;
		}
		else if (samp && type == 4 && length == 8192) {		// ADC samples data block
			state = 5;
			sample_count = 2048;
		}
		else if (navail >= length) {
			state = 3;
		}
		else {
			state = 2;
		}
		goto start_here;		// process the next state
	}
	else if (state == 2) {		// waiting for all "length" bytes to be read
		if (navail < length)
			return nSamples;	// partially read block
		state = 3;
		goto start_here;		// process the next state
	}
	else if (state == 3) {		// we have all the bytes of the record available
		if (length == 1 && type == 3) {	// ACK
			sdr_ack = buf[iread];
			INC_IREAD
#if DEBUG > 1
			printf("Got ACK for 0x%X\n", sdr_ack);
#endif
		}
		else if ((type == 0 || type == 1) && length >= 2) {		// control item
			item = buf[iread];
			INC_IREAD
			item |= buf[iread] << 8;		// control item number
			INC_IREAD
			length -= 2;
			for (k = 0; k < length; k++) {
				if (k < 128)
					buf128[k] = buf[iread];
				INC_IREAD
			}
			update_item(item, buf128);
		}
		else {
			iread += length;	// discard block
			if (iread >= SDRIQ_BUF_SIZE)
				iread -= SDRIQ_BUF_SIZE;
		}
		state = 0;
		goto start_here;		// we read a whole block
	}
	else if (state == 5) {		// read available samples into samp
		//ptimer(4096);
		while (navail >= 4 && sample_count && nSamples < sampsize) {			// samples are 16-bit little-endian
			ii = buf[iread];	// assumes a short is two bytes
			INC_IREAD
			ii |= buf[iread] << 8;
			INC_IREAD
			qq = buf[iread];
			INC_IREAD
			qq |= buf[iread] << 8;
			INC_IREAD
			navail -= 4;	// we read four bytes
			// convert 16-bit samples to 32-bit samples
			samp[nSamples++] = 65536.0 * ii + 65536.0 * qq * I;	// return sample as complex number
			sample_count--;		// we added one sample
		}
//printf("State %d navail %d sample_count %d nSamples %d\n", state, navail, sample_count, nSamples);
		if (sample_count > 0)		// no more samples available
			return nSamples;		// return the available samples
		state = 0;				// this block was completely read
		goto start_here;		// process the next state
	}
	else if (state == 9) {		// try to re-synchronize
		pt_quisk_sound_state->read_error++;
#if DEBUG
		printf ("Lost sync: type %d  length %d\n", type, length);
#endif
		while (1) {		// empty the buffer
			if (Read(buf, 1024) == 0)
				break;
		}
#if DEBUG > 2
			printf("Buffer is empty\n");
#endif
		while (1) {		// look for the start of data blocks "\x00\x80"
			res = Read(buf, 1);
			if (res != 1) {
				QuiskSleepMicrosec(SDRIQ_MSEC * 1000);
			}
			else if (state == 9) {		// look for 0x00
				if (buf[0] == 0x00)
					state = 10;
			}
			else {		// state 10: look for 0x80
				if (buf[0] == 0x80) {
					state = 5;
					iread = iwrite = 0;
					sample_count = 2048;
#if DEBUG
					printf("Regained sync\n");
#endif
					break;	// we probably have a data block start
				}
				else if (buf[0] != 0x00) {
					state = 9;
				}
			}
		}
		goto start_here;		// process the next state
	}
	return nSamples;		// should not happen
}

static void set_ad6620(	// host command to set an AD6620 register
	int address,		// the register address
	int value)			// the value; up to 4 bytes
{
	char buf[12];

	buf[0] = '\x09';
	buf[1] = '\xA0';
	buf[2] = address & 0xFF;			// low byte
	buf[3] = (address >> 8) & 0xFF;		// high byte
	buf[4] = value & 0xFF;				// low byte
	value = value >> 8;
	buf[5] = value & 0xFF;
	value = value >> 8;
	buf[6] = value & 0xFF;
	value = value >> 8;
	buf[7] = value & 0xFF;
	buf[8] = 0;
	if (Write(buf, 9) != 9) {
		pt_quisk_sound_state->read_error++;
#if DEBUG
		printf ("set_ad6620 write error\n");
#endif
	}
#if DEBUG > 1
	printf ("set_ad6620 address 0x%X\n", address);
#endif
}

static void wset_ad6620(int address, int value)
{	// Set AD6620 register and wait for ACK
	int i;

	sdr_ack = -1;
	set_ad6620(address, value);
	for (i = 0; i < SDRIQ_TIMEOUT; i++) {
		sdr_recv(NULL, 0);
		if (sdr_ack != -1)
			break;
		QuiskSleepMicrosec(SDRIQ_MSEC * 1000);
	}
#if DEBUG
	if (sdr_ack != 1)
		printf ("Failed to get ACK for AD6620 address 0x%X\n", address);
#endif
}

static void set_freq_sdriq(void)		// Set SDR-IQ frequency
{
	char buf[8];
	int freq;

	freq = sdriq_freq;
	buf[0] = 0;
	buf[1] = freq & 0xFF;				// low byte
	freq = freq >> 8;
	buf[2] = freq & 0xFF;
	freq = freq >> 8;
	buf[3] = freq & 0xFF;
	freq = freq >> 8;
	buf[4] = freq & 0xFF;
	buf[5] = 1;
	set_item(0x0020, 6, buf);
	cur_freq = sdriq_freq;
}

static void set_gain_sdriq(void)
{
	char buf[2];

	switch (sdriq_gstate) {
	case 0:
		buf[0] = 0;
		buf[1] = sdriq_gain & 0xFF;
		break;
	case 1:
		buf[0] = 1;
		buf[1] = sdriq_gain & 0x7F;
		buf[1] |= 0x80;
		break;
	case 2:
		buf[0] = 1;
		buf[1] = sdriq_gain & 0x7F;
		break;
	}
	set_item(0x0038, 2, buf);
	cur_gstate = sdriq_gstate;
	cur_gain = sdriq_gain;
}

static void program_ad6620(void)		// Set registers
{
	int i;
	struct ad6620 *pt;

	switch (sdriq_decimation) {
		case 360:
			pt = &dec360;
			break;
		case 500:
			pt = &dec500;
			break;
		case 600:
			pt = &dec600;
			break;
		case 1250:
			pt = &dec1250;
			break;
		default:
			pt = &dec1250;
			break;
	}
	wset_ad6620(0x300, 1);		// soft reset
	for (i = 0; i < 256; i++)
		wset_ad6620(i, pt->coef[i]);
	wset_ad6620(0x301, 0);
	wset_ad6620(0x302, -1);
	wset_ad6620(0x303, 0);
	wset_ad6620(0x304, 0);
	wset_ad6620(0x305, pt->Scic2);
	wset_ad6620(0x306, pt->Mcic2 - 1);
	wset_ad6620(0x307, pt->Scic5);
	wset_ad6620(0x308, pt->Mcic5 - 1);
	wset_ad6620(0x309, pt->Sout);
	wset_ad6620(0x30A, pt->Mrcf - 1);
	wset_ad6620(0x30B, 0);
	wset_ad6620(0x30C, 255);
	wset_ad6620(0x30D, 0);
	set_freq_sdriq();
	set_gain_sdriq();
	wset_ad6620(0x300, 0);
	cur_decimation = sdriq_decimation;
}


#if defined(MS_WINDOWS) || defined(__MACH__)
static void quisk_open_sdriq_dev(const char * name, char * buf, int bufsize)
{
#if DEBUG
	FT_STATUS ftStatus;
	FT_DEVICE_LIST_INFO_NODE *devInfo;
	DWORD numDevs;
	int i;

	// create the device information list
	ftStatus = FT_CreateDeviceInfoList(&numDevs);
	if (ftStatus == FT_OK) {
		printf("Number of devices is %d\n", (int)numDevs);
	}
	else {
		printf("Number of devices failed\n");
		numDevs = 0;
	 }
	if (numDevs > 0) {
		// allocate storage for list based on numDevs
		devInfo = (FT_DEVICE_LIST_INFO_NODE*)malloc(sizeof(FT_DEVICE_LIST_INFO_NODE)*numDevs);
		// get the device information list
		ftStatus = FT_GetDeviceInfoList(devInfo, &numDevs);
		if (ftStatus == FT_OK) {
			for (i = 0; i < numDevs; i++) {
				printf("Dev %d:\n",i);
				printf(" Flags=0x%x\n", (unsigned int)devInfo[i].Flags);
				printf(" Type=0x%x\n", (unsigned int)devInfo[i].Type);
				printf(" ID=0x%x\n", (unsigned int)devInfo[i].ID);
				printf(" LocId=0x%x\n", (unsigned int)devInfo[i].LocId);
				printf(" SerialNumber=%s\n", devInfo[i].SerialNumber);
				printf(" Description=%s\n", devInfo[i].Description);
				printf(" ftHandle=0x%x\n", (unsigned int)devInfo[i].ftHandle);
			}
		}
		free(devInfo);
	}
#endif		// DEBUG

	if (FT_OpenEx ("SDR-IQ", FT_OPEN_BY_DESCRIPTION, &quisk_sdriq_fd) != FT_OK) {
		strncpy(buf, "Open SDR-IQ failed", bufsize);
		quisk_sdriq_fd = INVALID_HANDLE_VALUE;
		return;
	}
	if (FT_SetTimeouts(quisk_sdriq_fd, 2, 100) != FT_OK) {
		strncpy(buf, "Set Timeouts failed", bufsize);
		return;
	}
}
#else
static void quisk_open_sdriq_dev(const char * name, char * buf, int bufsize)
{
    struct termios newtio;

	if (!strncmp(name, "/dev/ttyUSB", 11)) {	// use ftdi_sio driver
		quisk_sdriq_fd = open(name, O_RDWR | O_NOCTTY);
		if (quisk_sdriq_fd < 0) {
			strncpy(buf, "Open SDR-IQ : ", bufsize);
			strncat(buf, strerror(errno), bufsize - strlen(buf) - 1);
			quisk_sdriq_fd = INVALID_HANDLE_VALUE;
			return;
		}
		bzero(&newtio, sizeof(newtio));
		newtio.c_cflag = CS8 | CLOCAL | CREAD;
		newtio.c_iflag = IGNPAR;
		newtio.c_oflag = 0;
		cfsetispeed(&newtio, B230400);
		cfsetospeed(&newtio, B230400);
		newtio.c_lflag = 0;
		newtio.c_cc[VTIME]    = 0;	// specify non-blocking read 
		newtio.c_cc[VMIN]     = 0;
		tcflush(quisk_sdriq_fd, TCIFLUSH);
		tcsetattr(quisk_sdriq_fd, TCSANOW, &newtio);
	}
	else {		// use ft245 or similar driver
		quisk_sdriq_fd = open(name, O_RDWR | O_NONBLOCK); 
		if (quisk_sdriq_fd < 0) {
			strncpy(buf, "Open SDR-IQ: ", bufsize);
			strncat(buf, strerror(errno), bufsize - strlen(buf) - 1);
			quisk_sdriq_fd = INVALID_HANDLE_VALUE;
			return;
		}
	}
	return;
}
#endif

static void quisk_open_sdriq(const char * name, char * buf, int bufsize)
{
	char buf1024[1024];
	int i, freq;

	quisk_open_sdriq_dev(name, buf, bufsize);
	if (quisk_sdriq_fd == INVALID_HANDLE_VALUE)
		return;		// error

	sdr_name[0] = 0;
	sdr_serial[0] = 0;
	sdr_idle = -1;			// unknown state
	set_item(0x0018, 4, "\x81\x01\x00\x00");
	QuiskSleepMicrosec(1000000);
	while (1) {		// read and discard any available output
		if (Read(buf1024, 1024) == 0)
			break;
	}
	set_item(0x0018, 4, "\x81\x01\x00\x00");
	get_item(0x0002, 0, NULL);		// request serial number
	get_item(0x0005, 0, NULL);		// request status
	// set sample rate
	freq = sdriq_clock;
	buf1024[0] = 0;
	buf1024[1] = freq & 0xFF;				// low byte
	freq = freq >> 8;
	buf1024[2] = freq & 0xFF;
	freq = freq >> 8;
	buf1024[3] = freq & 0xFF;
	freq = freq >> 8;
	buf1024[4] = freq & 0xFF;
	set_item(0x00B0, 5, buf1024);	// set actual clock speed
	get_item(0x0001, 0, NULL);		// request name
	// loop for input
	for (i = 0; i < SDRIQ_TIMEOUT; i++) {
		sdr_recv(NULL, 0);
		if (sdr_name[0] != 0)
			break;
		QuiskSleepMicrosec(SDRIQ_MSEC * 1000);
	}
	if (sdr_name[0]) {		// we got a response
		snprintf(buf, bufsize, "Capture from %s serial %s.",
			sdr_name, sdr_serial);
		program_ad6620();
	}
	else {
		snprintf(buf, bufsize, "No response from SDR-IQ");
	}
#if DEBUG
	printf ("%s\n", buf);
#endif
}

static void WaitForPoll(void)
{
	static double time0 = 0;	// time in seconds
	double timer;				// time remaining from last poll usec

	timer = pt_quisk_sound_state->data_poll_usec - (QuiskTimeSec() - time0) * 1e6;
	if (timer > 1000.0)	// see if enough time has elapsed
		QuiskSleepMicrosec((int)timer);		// wait for the remainder of the poll interval
	time0 = QuiskTimeSec();		// reset starting time value
}

// End of most SDR-IQ specific code.

///////////////////////////////////////////////////////////////////////////
// The API requires at least two Python functions for Open and Close, plus
// additional Python functions as needed.  And it requires exactly three
// C funcions for Start, Stop and Read samples.  Quisk runs in two threads,
// a GUI thread and a sound thread.  You must not call the GUI or any Python
// code from the sound thread.  You must return promptly from functions called
// by the sound thread.
//
// The calling sequence is Open, Start, then repeated calls to Read, then
// Stop, then Close.

// Start of Application Programming Interface (API) code:

// Start sample capture; called from the sound thread.
static void quisk_start_sdriq(void)
{
	if (sdr_idle != 2)
		set_item(0x0018, 4, "\x81\x02\x00\x01");
}

// Stop sample capture; called from the sound thread.
static void quisk_stop_sdriq(void)
{
	int msec;
	complex double samples[2048];

	for (msec = 0; msec < 1001; msec++) {
		if (msec % 100 == 0)
			set_item(0x0018, 4, "\x81\x01\x00\x00");
		sdr_recv(samples, 2048);
		if (sdr_idle == 1)
			break;
		QuiskSleepMicrosec(1000);
	}
#if DEBUG
	if (msec < 1001)
		printf("quisk_stop_sdriq succeeded\n");
	else
		printf("quisk_stop_sdriq timed out\n");
#endif
}

// Called in a loop to read samples; called from the sound thread.
static int quisk_read_sdriq(complex double * cSamples)
{
	int length;

	WaitForPoll();
	if (quisk_sdriq_fd == INVALID_HANDLE_VALUE)
		return -1;		// sdriq is closed
	length = sdr_recv(cSamples, SAMP_BUFFER_SIZE);	// get all available samples
	if (cur_freq != sdriq_freq)		// check frequency
		set_freq_sdriq();
	if (cur_gstate != sdriq_gstate || cur_gain != sdriq_gain)	// check gain
		set_gain_sdriq();
	if (cur_decimation != sdriq_decimation) {		// check decimation
		quisk_stop_sdriq();
		program_ad6620();
		quisk_start_sdriq();
	}
	return length;	// return number of samples
}

// Called to close the sample source; called from the GUI thread.
static PyObject * close_samples(PyObject * self, PyObject * args)
{
	if (!PyArg_ParseTuple (args, ""))
		return NULL;
	if (quisk_sdriq_fd != INVALID_HANDLE_VALUE) {
		sdr_idle = -1;		// unknown state
#if defined(MS_WINDOWS) || defined(__MACH__)
		FT_Close(quisk_sdriq_fd);
#else
		close(quisk_sdriq_fd);
#endif
		quisk_sdriq_fd = INVALID_HANDLE_VALUE;
	}
	Py_INCREF (Py_None);
	return Py_None;
}

// Called to open the sample source; called from the GUI thread.
static PyObject * open_samples(PyObject * self, PyObject * args)
{
	const char * name;
	char buf[128];

	if (!PyArg_ParseTuple (args, ""))
		return NULL;

	name = QuiskGetConfigString("sdriq_name", "NoName");
	sdriq_clock = QuiskGetConfigDouble("sdriq_clock", 66666667.0);

// Record our C-language Start/Stop/Read functions for use by sound.c.
	quisk_sample_source(&quisk_start_sdriq, &quisk_stop_sdriq, &quisk_read_sdriq);
//////////////
	quisk_open_sdriq(name, buf, 128);		// SDR-IQ specific
	return PyString_FromString(buf);		// return a string message
}

// Miscellaneous functions needed by the SDR-IQ; called from the GUI thread as
// a result of button presses.

// Set the receive frequency; called from the GUI thread.
static PyObject * freq_sdriq(PyObject * self, PyObject * args)
{
	if (!PyArg_ParseTuple (args, "i", &sdriq_freq))
		return NULL;
	Py_INCREF (Py_None);
	return Py_None;
}

// Set the preamp gain; called from the GUI thread.
static PyObject * gain_sdriq(PyObject * self, PyObject * args)	// Called from GUI thread
{	// gstate == 0:  Gain must be 0, -10, -20, or -30
	// gstate == 1:  Attenuator is on  and gain is 0 to 127 (7 bits)
	// gstate == 2:  Attenuator is off and gain is 0 to 127 (7 bits)

	if (!PyArg_ParseTuple (args, "ii", &sdriq_gstate, &sdriq_gain))
		return NULL;
	Py_INCREF (Py_None);
	return Py_None;
}

// Set the decimation; called from the GUI thread.
static PyObject * set_decimation(PyObject * self, PyObject * args)
{
	if (!PyArg_ParseTuple (args, "i", &sdriq_decimation))
		return NULL;
	Py_INCREF (Py_None);
	return Py_None;
}

// Functions callable from Python are listed here:
static PyMethodDef QuiskMethods[] = {
	{"open_samples", open_samples, METH_VARARGS, "Open the RfSpace SDR-IQ."},
	{"close_samples", close_samples, METH_VARARGS, "Close the RfSpace SDR-IQ."},
	{"freq_sdriq", freq_sdriq, METH_VARARGS, "Set the frequency of the SDR-IQ"},
	{"gain_sdriq", gain_sdriq, METH_VARARGS, "Set the gain of the SDR-IQ"},
	{"set_decimation", set_decimation, METH_VARARGS, "Set the decimation of the SDR-IQ"},
	{NULL, NULL, 0, NULL}		/* Sentinel */
};

// Initialization, and registration of public symbol "initsdriq":
PyMODINIT_FUNC initsdriq (void)
{
	if (Py_InitModule ("sdriq", QuiskMethods) == NULL) {
		printf("Py_InitModule failed!\n");
		return;
	}
	// Import pointers to functions and variables from module _quisk
	if (import_quisk_api()) {
		printf("Failure to import pointers from _quisk\n");
		return;		//Error
	}
}
