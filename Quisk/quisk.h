
#define DEBUG_IO	0
#define DEBUG_MIC	0

// Sound parameters
//
#define QUISK_SC_SIZE		128
#define QUISK_PATH_SIZE     256         // max file path length
#define IP_SIZE				32
#define MAX_FILTER_SIZE		10001
#define BIG_VOLUME			2.2e9
#define CLOSED_TEXT			"The sound device is closed."
#define CLIP32				2147483647
#define CLIP16				32767
#define SAMP_BUFFER_SIZE	66000		// size of arrays used to capture samples
#define IMD_TONE_1			1200		// frequency of IMD test tones
#define IMD_TONE_2			1600
#define INTERP_FILTER_TAPS	85			// interpolation filter
#define MIC_OUT_RATE		48000		// mic post-processing sample rate
#define PA_LIST_SIZE 		16			// max number of pulseaudio devices
#define QUISK_MAX_RECEIVERS	9			// max number of receiver channels

// Test the audio: 0 == No test; normal operation;
// 1 == Copy real data to the output; 2 == copy imaginary data to the output;
// 3 == Copy transmit audio to the output.
#define TEST_AUDIO	0


// Pulseaudio support added by Philip G. Lee.  Many thanks!
/*!
 * \brief Specifies which driver a \c sound_dev is opened with
 */
typedef enum dev_driver{
   DEV_DRIVER_NONE = 0,
   DEV_DRIVER_PORTAUDIO,
   DEV_DRIVER_ALSA,
   DEV_DRIVER_PULSEAUDIO
} dev_driver_t;

struct sound_dev {				// data for sound capture or playback device
	char name[QUISK_SC_SIZE];	// string name of device
	char stream_description[QUISK_SC_SIZE]; // Short description of device/stream
	void * handle;				// Handle of open device, or NULL
	dev_driver_t driver;		// Which audio driver the device is using
	void * buffer;				// Handle of buffer for device
	int portaudio_index;		// index of portaudio device, or -1
	int doAmplPhase;			// Amplitude and Phase corrections
	double AmPhAAAA;
	double AmPhCCCC;
	double AmPhDDDD;
	double portaudio_latency;	// Suggested latency for portaudio device
	int sample_rate;			// Sample rate such as 48000, 96000, 192000
	int sample_bytes;			// Size of one channel sample in bytes, either 2 or 3 or 4
	int num_channels;			// number of channels per frame: 1, 2, 3, ...
	int channel_I;				// Index of I and Q channels: 0, 1, ...
	int channel_Q;
	int channel_Delay;			// Delay this channel by one sample; -1 for no delay, else channel_I or _Q
	int overrange;				// Count for ADC overrange (clip) for device
   // Number of frames for a read request.
   // If 0, the read should be non-blocking and read all available
   // frames.
	int read_frames;
	int latency_frames;			// desired latency in audio play samples
	int play_buf_size;			// size of playback buffer in samples
	int use_float;				// DirectX: Use IEEE floating point
	int dataPos;				// DirectX: data position
	int oldPlayPos;				// DirectX: previous value of playPos
	int play_delay;				// DirectX: bytes of sound available to play
	int started;				// DirectX: started flag or state
	int dev_error;				// read or write error
	int dev_underrun;			// lack of samples to play
	int dev_latency;			// latency frames
	unsigned int rate_min;		// min and max available sample rates
	unsigned int rate_max;
	unsigned int chan_min;		// min and max available number of channels
	unsigned int chan_max;
	complex double dc_remove;			// filter to remove DC from samples
	double save_sample;			// Used to delay the I or Q sample
	char msg1[QUISK_SC_SIZE];	// string for information message
	int stream_dir_record;		// 1 for recording, 0 for playback
	char server[IP_SIZE];		// server string for remote pulseaudio
	int stream_format;			// format of pulseaudio device
	volatile int cork_status;	// 1 for corked, 0 for uncorked
} ;

struct sound_conf {
	char dev_capt_name[QUISK_SC_SIZE];
	char dev_play_name[QUISK_SC_SIZE];
	int sample_rate;		// Input sample rate from the ADC
	int playback_rate;		// Output play rate to sound card
	int data_poll_usec;
	int latency_millisecs;
	unsigned int rate_min;
	unsigned int rate_max;
	unsigned int chan_min;
	unsigned int chan_max;
	int read_error;
	int write_error;
	int underrun_error;
	int overrange;		// count of ADC overrange (clip) for non-soundcard device
	int latencyCapt;
	int latencyPlay;
	int interupts;
	char msg1[QUISK_SC_SIZE];
	char err_msg[QUISK_SC_SIZE];
	// These parameters are for the microphone:
	char mic_dev_name[QUISK_SC_SIZE];		// capture device
	char name_of_mic_play[QUISK_SC_SIZE];		// playback device
	char mic_ip[IP_SIZE];
	int mic_sample_rate;				// capture sample rate
	int mic_playback_rate;				// playback sample rate
	int tx_audio_port;
	int mic_read_error;
	int mic_channel_I;		// channel number for microphone: 0, 1, ...
	int mic_channel_Q;
	double mic_out_volume;
	char IQ_server[IP_SIZE];	//IP address of optional streaming IQ server (pulseaudio)
	int verbose_pulse;      //verbose output for pulse audio
} ;

enum quisk_rec_state {
	IDLE,
	RECORD_RADIO,
	RECORD_MIC,
	PLAYBACK,
	PLAY_FILE } ;
extern enum quisk_rec_state quisk_record_state;

struct QuiskWav {			// data to create a WAV or RAW audio file
    double scale;
    int sample_rate;
    short format;			// RAW is 0; PCM integer is 1; IEEE float is 3.
    short nChan;
    short bytes_per_sample;
    FILE * fp;
    unsigned int samples;
    int fpStart;
    int fpEnd;
    int fpPos;
} ;

void QuiskWavClose(struct QuiskWav *);
int QuiskWavWriteOpen(struct QuiskWav *, char *, short, short, short, int, double);
void QuiskWavWriteC(struct QuiskWav *, complex double *, int);
void QuiskWavWriteD(struct QuiskWav *, double *, int);
int QuiskWavReadOpen(struct QuiskWav *, char *, short, short, short, int, double);
void QuiskWavReadC(struct QuiskWav *, complex double *, int);
void QuiskWavReadD(struct QuiskWav *, double *, int);
void QuiskMeasureRate(const char *, int);

extern struct sound_conf quisk_sound_state, * pt_quisk_sound_state;
extern int mic_max_display;		// display value of maximum microphone signal level
extern int quiskSpotLevel;		// 0 for no spotting; else the level 10 to 1000
extern int data_width;
extern int quisk_using_udp;	// is a UDP port used for capture (0 or 1)?
extern int quisk_rx_udp_started;		// have we received any data?
extern int rxMode;				// mode CWL, USB, etc.
extern int quisk_tx_tune_freq;	// Transmit tuning frequency as +/- sample_rate / 2
extern PyObject * quisk_pyConfig;		// Configuration module instance
extern long quisk_mainwin_handle;		// Handle of the main window
extern double quisk_mic_preemphasis;	// Mic preemphasis 0.0 to 1.0; or -1.0
extern double quisk_mic_clip;			// Mic clipping; try 3.0 or 4.0
extern int quisk_noise_blanker;			// Noise blanker level, 0 for off
extern int quisk_sidetoneCtrl;			// sidetone control value 0 to 1000
extern double quisk_audioVolume;		// volume control for radio sound playback, 0.0 to 1.0
extern int quiskImdLevel;				// level for rxMode IMD
extern int quiskTxHoldState;			// state machine for Tx wait for repeater frequency shift
extern double quisk_ctcss_freq;			// frequency in Hertz
extern unsigned char quisk_pc_to_hermes[17 * 4];	// Data to send from the PC to the Hermes hardware
extern int quisk_use_rx_udp;					// Method of access to UDP hardware
extern complex double cRxFilterOut(complex double, int, int);
extern int quisk_multirx_count;			// number of additional receivers zero or 1, 2, 3, ..
extern struct sound_dev quisk_DigitalRx1Output;		// Output sound device for sub-receiver 1

extern PyObject * quisk_set_spot_level(PyObject * , PyObject *);
extern PyObject * quisk_get_tx_filter(PyObject * , PyObject *);

extern PyObject * quisk_set_ampl_phase(PyObject * , PyObject *);
extern PyObject * quisk_capt_channels(PyObject * , PyObject *);
extern PyObject * quisk_play_channels(PyObject * , PyObject *);
extern PyObject * quisk_micplay_channels(PyObject * , PyObject *);
extern PyObject * quisk_sound_devices(PyObject * , PyObject *);
extern PyObject * quisk_pa_sound_devices(PyObject * , PyObject *);
extern PyObject * quisk_sound_errors(PyObject *, PyObject *);
extern PyObject * quisk_set_file_record(PyObject *, PyObject *);
extern PyObject * quisk_set_tx_audio(PyObject *, PyObject *, PyObject *);
extern PyObject * quisk_is_vox(PyObject *, PyObject *);
extern PyObject * quisk_set_udp_tx_correct(PyObject *, PyObject *);

extern PyObject * quisk_freedv_open(PyObject *, PyObject *);
extern PyObject * quisk_freedv_close(PyObject *, PyObject *);
extern PyObject * quisk_freedv_get_snr(PyObject *, PyObject *);
extern PyObject * quisk_freedv_get_version(PyObject *, PyObject *);
extern PyObject * quisk_freedv_get_rx_char(PyObject *, PyObject *);
extern PyObject * quisk_freedv_set_options(PyObject *, PyObject *, PyObject *);

// These function pointers are the Start/Stop/Read interface for
// the SDR-IQ and any other C-language extension modules that return
// radio data samples.
typedef void (* ty_sample_start)(void);
typedef void (* ty_sample_stop)(void);
typedef int  (* ty_sample_read)(complex double *);

void quisk_open_sound(void);
void quisk_close_sound(void);
int quisk_process_samples(complex double *, int);
void quisk_play_samples(double *, int);
void quisk_play_zeros(int);
void quisk_start_sound(void);
int quisk_get_overrange(void);
void quisk_mixer_set(char *, int, PyObject *, char *, int);
int quisk_read_sound(void);
int quisk_process_microphone(int, complex double *, int);
void quisk_open_mic(void);
void quisk_close_mic(void);
int quisk_open_key(const char *);
void quisk_close_key(void);
int quisk_is_key_down(void);
void quisk_set_key_down(int);
void quisk_set_tx_mode(void);
void ptimer(int);
int quisk_extern_demod(complex double *, int, double);
void quisk_tmp_microphone(complex double *, int);
void quisk_tmp_record(complex double * , int, double);
void quisk_file_microphone(complex double *, int);
void quisk_file_playback(complex double *, int, double);
void quisk_tmp_playback(complex double *, int, double);
void quisk_hermes_tx_add(complex double *, int);
void quisk_hermes_tx_send(int, int *);
void quisk_udp_mic_error(char *);
void quisk_check_freedv_mode(void);

// Functions supporting digital voice codecs
typedef int  (* ty_dvoice_codec_rx)(complex double *, double *, int, int);
typedef int  (* ty_dvoice_codec_tx)(complex double *, double *, int);
extern ty_dvoice_codec_rx  pt_quisk_freedv_rx;
extern ty_dvoice_codec_tx  pt_quisk_freedv_tx;

// Driver function definitions=================================================
int  quisk_read_alsa(struct sound_dev *, complex double *);
void quisk_play_alsa(struct sound_dev *, int, complex double *, int, double);
void quisk_start_sound_alsa(struct sound_dev **, struct sound_dev **);
void quisk_close_sound_alsa(struct sound_dev **, struct sound_dev **);

int  quisk_read_portaudio(struct sound_dev *, complex double *);
void quisk_play_portaudio(struct sound_dev *, int, complex double *, int, double);
void quisk_start_sound_portaudio(struct sound_dev **, struct sound_dev **);
void quisk_close_sound_portaudio(void);

void play_sound_interface(struct sound_dev * , int, complex double * , int, double);

int  quisk_read_pulseaudio(struct sound_dev *, complex double *);
void quisk_play_pulseaudio(struct sound_dev *, int, complex double *, int, double);
void quisk_start_sound_pulseaudio(struct sound_dev **, struct sound_dev **);
void quisk_close_sound_pulseaudio(void);
void quisk_cork_pulseaudio(struct sound_dev *, int);
void quisk_flush_pulseaudio(struct sound_dev *);
//+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

/*
Functions defined below this point are available for export to other extension modules using the
standard Python CObject or Capsule interface.  See the documentation in import_quisk_api.c.  Note
that index zero is used for a structure pointer, not a function pointer.

To add a function, declare it twice, use the next array index, and add it to QUISK_API_INIT.
Be very careful; here be dragons!
*/

#ifdef IMPORT_QUISK_API
// For use by modules that import the _quisk symbols
extern void ** Quisk_API;	// array of pointers to functions and variables from module _quisk
int import_quisk_api(void);	// used to initialize Quisk_API

#define QuiskGetConfigInt	(*(	int	(*)	(const char *, int)	)Quisk_API[1])
#define QuiskGetConfigDouble	(*(	double	(*)	(const char *, double)	)Quisk_API[2])
#define QuiskGetConfigString	(*(	char *	(*)	(const char *, char *)	)Quisk_API[3])
#define QuiskTimeSec		(*(	double	(*)	(void)			)Quisk_API[4])
#define QuiskSleepMicrosec	(*(	void	(*)	(int)			)Quisk_API[5])
#define QuiskPrintTime		(*(	void	(*)	(const char *, int)	)Quisk_API[6])
#define quisk_sample_source	(*(	void	(*)	(ty_sample_start, ty_sample_stop, ty_sample_read)	)Quisk_API[7])
#define quisk_dvoice_freedv	(*(	void	(*)	(ty_dvoice_codec_rx, ty_dvoice_codec_tx)	)Quisk_API[8])

#else
// Used to export symbols from _quisk in quisk.c

int	QuiskGetConfigInt(const char *, int);
double	QuiskGetConfigDouble(const char *, double);
char *	QuiskGetConfigString(const char *, char *);
double	QuiskTimeSec(void);
void	QuiskSleepMicrosec(int);
void	QuiskPrintTime(const char *, int);
void	quisk_sample_source(ty_sample_start, ty_sample_stop, ty_sample_read);
void	quisk_dvoice_freedv(ty_dvoice_codec_rx, ty_dvoice_codec_tx);

#define QUISK_API_INIT	{ \
 &quisk_sound_state, &QuiskGetConfigInt, &QuiskGetConfigDouble, &QuiskGetConfigString, &QuiskTimeSec, \
 &QuiskSleepMicrosec, &QuiskPrintTime, &quisk_sample_source, &quisk_dvoice_freedv \
 }

#endif

