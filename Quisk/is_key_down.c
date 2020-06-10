#include <Python.h>		// used by quisk.h
#include <complex.h>	// Used by quisk.h
#include "quisk.h"

// This module provides methods to access the state of the key.
// First call quisk_open_key(name) to choose a method and initialize.
// Subsequent key access uses the method chosen.

static int key_is_down = 0;		// internal key state

// Changes for MacOS support thanks to Mario, DL3LSM.
#if defined(MS_WINDOWS) || defined(__MACH__)

int quisk_open_key(const char * name)
{	// Open the hardware key; return 0 for success, else an error code.
	return 0;
}

void quisk_close_key(void)
{
}

int quisk_is_key_down(void)
{
	return key_is_down;
}

void quisk_set_key_down(int state)
{		// Set the key state internally
	if (state)
		key_is_down = 1;
	else
		key_is_down = 0;
}
#else
// Not MS Windows:
#include <stdio.h>
#include <fcntl.h>
#include <netinet/in.h>
#ifdef __linux__
#include <linux/ppdev.h>
#endif
#ifdef __FreeBSD__
#include <dev/ppbus/ppi.h>
#include <dev/ppbus/ppbconf.h>
#endif
#include <sys/ioctl.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <arpa/inet.h>

static int open_key_pport(const char * name);
static int open_key_serport(const char * name);
static int open_key_enet(const char * name);
static void close_key_pport(void);
static void close_key_serport(void);
static void close_key_enet(void);
static int is_key_down_pport(void);
static int is_key_down_serport(void);
static int is_key_down_enet(void);

static enum {	// The key access method
	None,		// Return the internal state; default key is always up
	ParPort,	// Use the parallel port
	SerPort,	// Use the serial port
	Udp			// Use UDP Ethernet
	} key_method = None;

static int fd = -1;		// File descriptor to read the parallel or serial port
static int KEY_PORT = 0x553C;	// Ethernet UDP port
static int key_socket = -1;		// Ethernet socket

int quisk_open_key(const char * name)
{	// Open the hardware key; return 0 for success, else an error code.
	int ret;

	if (!name[0]){					// null string means internal key state
		key_method = None;
		ret = 0;
	}
	else if (!strncmp(name, "/dev/tty", 8)){	// serial port
		key_method = SerPort;
		ret = open_key_serport(name);
	}
	else if (name[0] == '/'){		// starting '/' means parallel port name
		key_method = ParPort;
		ret = open_key_pport(name);
	}
	else if (isdigit(name[0])){		// IP address
		key_method = Udp;
		ret = open_key_enet(name);
	}
	else {
		ret = 5;
	}
	return ret;
}

void quisk_close_key(void)
{
	switch(key_method) {
	case None:
		break;
	case ParPort:
		close_key_pport();
		break;
	case SerPort:
		close_key_serport();
		break;
	case Udp:
		close_key_enet();
		break;
	}
	return;
}

int quisk_is_key_down(void)
{
	switch(key_method) {
	case None:
		return key_is_down;
	case SerPort:
		return is_key_down_serport();
	case ParPort:
		return is_key_down_pport();
	case Udp:
		return is_key_down_enet();
	}
	return 0;
}

void quisk_set_key_down(int state)
{		// Set the key state internally
	if (state)
		key_is_down = 1;
	else
		key_is_down = 0;
}

// ***************************************************
// Access the parallel port
static int open_key_pport(const char * name)
{
	int byte;

	if (fd >= 0)
		close(fd);
	fd = open(name, O_RDONLY);
	if (fd == -1) {
			printf("Open %s failed, try modprobe ppdev.\n", name);
	}
#ifdef __linux__
	else if (ioctl (fd, PPCLAIM)) {
		perror ("PPCLAIM");
		close (fd);
		fd = -1;
	}
#endif
	else {
		byte = 0x0;
#if defined(__linux__)
		ioctl(fd, PPWCONTROL, &byte);		
#endif
		return 0;	// Success
	}
	return -1;
}

static void close_key_pport(void)
{
	int byte;

	if (fd >= 0) {
#ifdef __linux__
		byte = 0x0;
		ioctl(fd, PPWCONTROL, &byte);
#endif
		close(fd);
	}
	fd = -1;
}

// This code writes to the control register so the PC can send a signal.
// Currently unused.
//	ioctl(fd, PPRCONTROL, &byte);
//	byte |= 0x02;
//	ioctl(fd, PPWCONTROL, &byte);

static int is_key_down_pport(void)
{
#if defined(__linux__)
	int byte;
	if (fd < 0)		// port not open
		return 0;	// Key is up
	byte = 0;
	ioctl(fd, PPRSTATUS, &byte);
	if (byte & 0x10)
		return 1;	// Key is down
#elif defined(__FreeBSD__)
	uint8_t byte;
	if (fd < 0)		// port not open
		return 0;	// Key is up
	byte = 0;
	ioctl(fd, PPIGSTATUS, &byte);
	if (byte & 0x10)
		return 1;	// Key is down
#endif
	return 0;		// Key is up
}



// ***************************************************
// Access using Ethernet
// Check for a UDP packet from the network to determine key status

static int open_key_enet(const char * ip)
{
	struct sockaddr_in Addr;

	close_key_enet();
	key_socket = socket(PF_INET, SOCK_DGRAM, 0);
	if (key_socket < 0)
		return -1;
	memset(&Addr, 0, sizeof(Addr));		// Assign an address to our socket
	Addr.sin_family = AF_INET;
	Addr.sin_addr.s_addr = htonl(INADDR_ANY);
	Addr.sin_port = htons(KEY_PORT);
	if (bind(key_socket, (struct sockaddr *)&Addr, sizeof(Addr)) != 0) {
		close_key_enet();
		return -1;
	}
	memset(&Addr, 0, sizeof(Addr));		// Only accept UDP from this host
	Addr.sin_family = AF_INET;
	inet_aton(ip, &Addr.sin_addr);
	Addr.sin_port = htons(KEY_PORT);
	if (connect(key_socket, (struct sockaddr *)&Addr, sizeof(Addr)) != 0) {
		close_key_enet();
		return -1;
	}
	return 0;	// Success
}

static void close_key_enet(void)
{
	if (key_socket != -1) {
		shutdown(key_socket, SHUT_RDWR);
		close(key_socket);
		key_socket = -1;
	}
}

static int is_key_down_enet(void)
{
	static int keyed = 0;
	unsigned char buf[4];

	if (key_socket >= 0 && recv(key_socket, buf, 2, MSG_DONTWAIT) == 2)
		keyed = buf[0];	// new key state is available
	return keyed;		// return current key state 
}


// ***************************************************
// Access the serial port.  This code sets DTR high, and monitors DSR.
// When DSR is high the key is down (else up).
// Set the RTS signal high when the key is down; else low after a delay.
static int open_key_serport(const char * name)
{
	int bits;

	if (fd >= 0)
		close(fd);
	fd = open(name, O_RDWR | O_NOCTTY);
	if (fd == -1) {
		printf("Open serial port %s failed.\n", name);
		return -1;
	}
	ioctl(fd, TIOCMGET, &bits);		// read modem bits
	bits |= TIOCM_DTR;				// Set DTR
	bits &= ~TIOCM_RTS;				// Clear RTS at first
	ioctl(fd, TIOCMSET, &bits);
	return 0;	// Success
}

static void close_key_serport(void)
{
	if (fd >= 0)
		close(fd);
	fd = -1;
}

// Delay clearing RTS when the key goes up (semi breakin)
#define KEY_UP_DELAY_SECS		1.5
static int is_key_down_serport(void)
{
	int bits;
	struct timeval tv;
	double time;
	static double time0=0;	// time when the key was last down

	if (fd < 0)		// Port not open
		return 0;	// Key is up

	gettimeofday(&tv, NULL);
	time = tv.tv_sec + tv.tv_usec / 1.0E6;		// time is in seconds
	ioctl(fd, TIOCMGET, &bits);		// read modem bits
	if (bits & TIOCM_DSR) {		// Key is down
		bits |= TIOCM_RTS;		// Set RTS
		ioctl(fd, TIOCMSET, &bits);
		time0 = time;
		return 1;
	}
    else {						// Key is up
		if (time - time0 > KEY_UP_DELAY_SECS) {
			bits &= ~TIOCM_RTS;		// Clear RTS after a delay
			ioctl(fd, TIOCMSET, &bits);
		}
		return 0;
	}
}
#endif
