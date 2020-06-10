/*
This module uses the Python CObject or Capsule interface to import pointers to
functions and variables defined in the _quisk Python extension module.  These functions and
variables can then be used in another extension module.  This is an alternative to linking
the other extension module to _quisk with the C linker.  This interface is used by the SDR-IQ
extension module, and you can use that as a model.

This feature exists because of Maitland Bottoms, AA4HS, who requested the feature and provided patches.

To use this interface in your own extension module, first modify your setup.py or makefile so that
you are not linking in symbols from the _quisk module.  Add import_quisk_api.c to your source files.

Then add this define before including quisk.h:
#define IMPORT_QUISK_API
#include "quisk.h"

Add this code after Py_InitModule() in your module init function (PyMODINIT_FUNC):
	// Import pointers to functions and variables from module _quisk
	if (import_quisk_api()) {
		printf("Failure to import pointers from _quisk\n");
		return;		//Error
	}

Use this new function to set your Start/Stop/Read functions (if used):
	quisk_sample_source(&quisk_start_sdriq, &quisk_stop_sdriq, &quisk_read_sdriq);

Change references to quisk_sound_state to use the pointer pt_quisk_sound_state everywhere.  For
example, replace this:
	quisk_sound_state.read_error++;
with this:
	pt_quisk_sound_state->read_error++;
*/

#include <Python.h>

void ** Quisk_API;		// array of pointers to functions and variables from module _quisk
struct sound_conf * pt_quisk_sound_state;		// pointer to quisk_sound_state

#if ( (PY_VERSION_HEX <  0x02070000) || ((PY_VERSION_HEX >= 0x03000000) && (PY_VERSION_HEX <  0x03010000)) )
// Old Python interface using CObject
int import_quisk_api(void)
{
	PyObject *c_api_object;
	PyObject *module;

	module = PyImport_ImportModule("_quisk");
	if (module == NULL) {
		printf("Failure 1 to import Quisk_API\n");
		return -1;
	}
	c_api_object = PyObject_GetAttrString(module, "QUISK_C_API");
	if (c_api_object == NULL) {
		Py_DECREF(module);
		printf("Failure 2 to import Quisk_API\n");
		return -1;
	}
	if (PyCObject_Check(c_api_object)) {
		Quisk_API = (void **)PyCObject_AsVoidPtr(c_api_object);
	}
	else {
		printf("Failure 3 to import Quisk_API\n");
		Py_DECREF(c_api_object);
		Py_DECREF(module);
		return -1;
	}
	Py_DECREF(c_api_object);
	Py_DECREF(module);
	pt_quisk_sound_state = (struct sound_conf *)Quisk_API[0];
	return 0;
}
#else
// New Python interface using Capsule
int import_quisk_api(void)
{
	Quisk_API = (void **)PyCapsule_Import("_quisk.QUISK_C_API", 0);
	if (Quisk_API == NULL) {
		printf("Failure to import Quisk_API\n");
		return -1;
	}
	pt_quisk_sound_state = (struct sound_conf *)Quisk_API[0];
	return 0;
}
#endif
