#include <Python.h>
#ifdef MS_WINDOWS
#include <windows.h>
#else
#include <stdlib.h>
#include <sys/time.h>
#endif
#include <complex.h>
#include "quisk.h"

// Access to config file attributes.
// NOTE:  These must be called only from the main (GUI) thread,
//        not from the sound thread.

int QuiskGetConfigInt(const char * name, int deflt)
{  // return deflt for failure.  Accept int or float.
  int res;
  PyObject * attr;  
  if (!quisk_pyConfig || PyErr_Occurred()) {
    return deflt;
  }
  attr = PyObject_GetAttrString(quisk_pyConfig, name);
  if (attr) {
    res = (int)PyInt_AsUnsignedLongMask(attr);  // This works for floats too!
    Py_DECREF(attr);
    return res;		// success
  }
  else {
    PyErr_Clear();
  }
  return deflt;		// failure
}

double QuiskGetConfigDouble(const char * name, double deflt)
{  // return deflt for failure.  Accept int or float.
  double res;
  PyObject * attr;  

  if (!quisk_pyConfig || PyErr_Occurred())
    return deflt;
  attr = PyObject_GetAttrString(quisk_pyConfig, name);
  if (attr) {
    res = PyFloat_AsDouble(attr);
    Py_DECREF(attr);
    return res;		// success
  }
  else {
    PyErr_Clear();
  }
  return deflt;		// failure
}

char * QuiskGetConfigString(const char * name, char * deflt)
{  // return deflt for failure.
  char * res;
  PyObject * attr;  

  if (!quisk_pyConfig || PyErr_Occurred())
    return deflt;
  attr = PyObject_GetAttrString(quisk_pyConfig, name);
  if (attr) {
    res = PyString_AsString(attr);
    Py_DECREF(attr);
    if (res)
      return res;		// success
    else
      PyErr_Clear();
  }
  else {
    PyErr_Clear();
  }
  return deflt;		// failure
}

double QuiskTimeSec(void)
{  // return time in seconds as a double
#ifdef MS_WINDOWS
	FILETIME ft;
	ULARGE_INTEGER ll;

	GetSystemTimeAsFileTime(&ft);
	ll.LowPart  = ft.dwLowDateTime;
	ll.HighPart = ft.dwHighDateTime;
	return (double)ll.QuadPart * 1.e-7;
#else
	struct timeval tv;

	gettimeofday(&tv, NULL);
	return (double)tv.tv_sec + tv.tv_usec * 1e-6;
#endif
}

void QuiskPrintTime(const char * str, int index)
{  // print the time and a message and the delta time for index 0 to 9
	double tm;
	int i;
	static double time0 = 0;
	static double start_time[10];
#ifdef MS_WINDOWS
	static long long timer_rate = 0;
	LARGE_INTEGER L;
	if ( ! timer_rate) {
		if (QueryPerformanceFrequency(&L))
			timer_rate = L.QuadPart;
		else
			timer_rate = 1;
	}
	if (QueryPerformanceCounter(&L))
		tm = (double)L.QuadPart / timer_rate;
	else
		tm = 0;
#else
	struct timeval tv;
	gettimeofday(&tv, NULL);
	tm = (double)tv.tv_sec + tv.tv_usec * 1e-6;
#endif
	if (index < -9 || index > 9)	// error
		return;
	if (index < 0) {
		start_time[ - index] = tm;
		return;
	}
	if ( ! str) {		// initialize
		time0 = tm;
		for (i = 0; i < 10; i++)
			start_time[i] = tm;
		return;
	}
	// print the time since startup, and the time since the last call
	if (index > 0) {
		if (str[0])	// print message and a newline
			printf ("%12.6lf  %9.3lf  %9.3lf  %s\n",
				tm - time0, (tm - start_time[0])*1e3, (tm - start_time[index])*1e3, str);
		else		// no message; omit newline
			printf ("%12.6lf  %9.3lf  %9.3lf  ",
				tm - time0, (tm - start_time[0])*1e3, (tm - start_time[index])*1e3);
	}
	else {
		if (str[0])	// print message and a newline
			printf ("%12.6lf  %9.3lf  %s\n",
				tm - time0, (tm - start_time[0])*1e3, str);
		else		// no message; omit newline
			printf ("%12.6lf  %9.3lf  ",
				tm - time0, (tm - start_time[0])*1e3);
	}
	start_time[0] = tm;
}

void QuiskSleepMicrosec(int usec)
{
#ifdef MS_WINDOWS
	int msec = (usec + 500) / 1000;		// convert to milliseconds
	if (msec < 1)
		msec = 1;
	Sleep(msec);
#else
	struct timespec tspec;
	tspec.tv_sec = usec / 1000000;
	tspec.tv_nsec = (usec - tspec.tv_sec * 1000000) * 1000;
	nanosleep(&tspec, NULL);
#endif
}

void QuiskMeasureRate(const char * msg, int count)
{  //measure the sample rate
	double tm;
	static int total;
	static double time0=0, time_pr;

	if ( ! msg) {	// init
		time0 = 0;
		return;
	}
	if (count && time0 == 0) {		// init
		time0 = time_pr = QuiskTimeSec();
		total = 0;
		return;
	}
	if (time0 == 0)
		return;
	total += count;
	if (QuiskTimeSec() > time_pr + 1.0) {	// time to print
		time_pr = tm = QuiskTimeSec();
		printf("%s count %d, time %.3lf, rate %.3lf\n", msg, total, tm - time0, total / (tm - time0));
	}
}
