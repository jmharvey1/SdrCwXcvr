struct quisk_cFilter {
	double  * dCoefs;	// filter coefficients
	complex double * cpxCoefs;	// make the complex coefficients from dCoefs
	int nBuf;					// dimension of cBuf
	int nTaps;					// dimension of dSamples, cSamples, dCoefs and cpxCoefs
	int decim_index;			// used to count samples for decimation
	complex double * cSamples;	// storage for old samples
	complex double * ptcSamp;	// next available position in cSamples
	complex double * cBuf;		// auxillary buffer for interpolation
} ;

struct quisk_dFilter {
	double  * dCoefs;			// filter coefficients
	complex double * cpxCoefs;	// make the complex coefficients from dCoefs
	int nBuf;					// dimension of dBuf
	int nTaps;					// dimension of dSamples, cSamples, dCoefs and cpxCoefs
	int decim_index;			// used to count samples for decimation
	double  * dSamples;			// storage for old samples
	double  * ptdSamp;			// next available position in dSamples
	double  * dBuf;				// auxillary buffer for interpolation
} ;

struct quisk_cHB45Filter {   // Complex half band decimate by 2 filter with 45 coefficients
	complex double * cBuf;		// auxillary buffer for interpolation
	int nBuf;		// dimension of cBuf
	int toggle;
	complex double samples[22];
	complex double center[11];
} ;

struct quisk_dHB45Filter {   // Real half band decimate by 2 filter with 45 coefficients
	double * dBuf;		// auxillary buffer for interpolation
	int nBuf;		// dimension of dBuf
	int toggle;
	double samples[22];
	double center[11];
} ;

void quisk_filt_cInit(struct quisk_cFilter *, double *, int);
void quisk_filt_dInit(struct quisk_dFilter *, double *, int);
void quisk_filt_tune(struct quisk_dFilter *, double, int);
complex double quisk_dC_out(double, struct quisk_dFilter *);
double quisk_dD_out(double, struct quisk_dFilter *);
int quisk_cInterpolate(complex double *, int, struct quisk_cFilter *, int);
int quisk_dInterpolate(double *, int, struct quisk_dFilter *, int);
int quisk_cDecimate(complex double *, int, struct quisk_cFilter *, int);
int quisk_dDecimate(double *, int, struct quisk_dFilter *, int);
int quisk_cInterpDecim(complex double *, int, struct quisk_cFilter *, int, int);
int quisk_cDecim2HB45(complex double *, int, struct quisk_cHB45Filter *);
int quisk_dInterp2HB45(double *, int, struct quisk_dHB45Filter *);
int quisk_cInterp2HB45(complex double *, int, struct quisk_cHB45Filter *);
int quisk_dFilter(double *, int, struct quisk_dFilter *);
int quisk_cFilter(complex double *, int, struct quisk_cFilter *);

extern double quiskMicFilt48Coefs[325];
extern double quiskMic5Filt48Coefs[424];
extern double quiskMicFilt8Coefs[93];
extern double quiskLpFilt48Coefs[186];
extern double quiskFilt12_19Coefs[64];
extern double quiskFilt185D3Coefs[189];
extern double quiskFilt133D2Coefs[136];
extern double quiskFilt167D3Coefs[174];
extern double quiskFilt111D2Coefs[114];
extern double quiskFilt53D1Coefs[55];
extern double quiskFilt144D3Coefs[195];
extern double quiskFilt240D5Coefs[115];
extern double quiskFilt240D5CoefsSharp[245];
extern double quiskFilt48dec24Coefs[98];
extern double quiskAudio24p6Coefs[36];
extern double quiskAudio48p6Coefs[71];
extern double quiskAudio96Coefs[11];
extern double quiskAudio24p4Coefs[50];
extern double quiskAudioFmHpCoefs[309];
extern double quiskAudio24p3Coefs[100];
extern double quiskFiltTx8kAudioB[168];
extern double quiskFilt16dec8Coefs[62];
extern double quiskFilt120s03[480];
extern double quiskFiltI3D25Coefs[825];
