#include <Python.h>
#include <stdlib.h>
#include <math.h>
#include <complex.h>
#include "quisk.h"

// If you set add_extern_demod in your config file, you will get another
// button that will call this module.  Change it to what you want.  Save
// a copy because new releases of Quisk will overwrite this file.
//
// NOTE:  NEW RELEASES OF QUISK WILL OVERWRITE THIS FILE!

int quisk_extern_demod(complex double * cSamples, int nSamples, double decim)
{	// Filter and demodulate the I/Q samples into audio play samples.
// cSamples:	The input I/Q samples, and the output stereo play samples.
// nSamples:	The number of input samples; maximum is SAMP_BUFFER_SIZE.
// decim:		The decimation needed (1.0 for no decimation).
// The output play samples are stereo, and are placed into cSamples.
// The return value is the number of output samples = nSamples / decim.
// See quisk.h for useful data in quisk_sound_state.  For example, the
// sample rate is quisk_sound_state.sample_rate.  If you need decimation,
// look at iDecimate() and fDecimate() in quisk.c.

	int i;
	double d, di;
	complex double cx;
	static complex double fm_1 = 10;		// Sample delayed by one
	static complex double fm_2 = 10;		// Sample delayed by two

	if (fabs (decim - 1.0) > 0.001)		// no provision for decimation
		return 0;

	for (i = 0; i < nSamples; i++) {	// narrow FM
		cx = cSamples[i];
		di = creal(fm_1) * (cimag(cx) - cimag(fm_2)) -
		     cimag(fm_1) * (creal(cx) - creal(fm_2));
		d = creal(fm_1) * creal(fm_1) + cimag(fm_1) * cimag(fm_1);
		if (d == 0)	// I don't think this can happen
			di = 0;
		else
			di = di / d * quisk_sound_state.sample_rate;
		fm_2 = fm_1;	// fm_2 is sample cSamples[i - 2]
		fm_1 = cx;		// fm_1 is sample cSamples[i - 1]
		cSamples[i] = di + I * di;	// monophonic sound, two channels
	}
	return nSamples;	// Number of play samples
}
