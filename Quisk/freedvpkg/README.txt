
Note:  The directory freedvpkg no longer contains source files.  It only contains copies of
       the codec2 libraries for use by Quisk.  If any other files are present, delete them.

FreeDV and Directory freedvpkg
==============================

FreeDV is the combination of the codec2 codec and the fdmdv modem.  It provides digital voice
in 1200 Hz bandwidth suitable for HF transmission.  Quisk has native (built-in) support for
FreeDV.  Just push the FDV mode and talk.  This freedvpkg directory contains copies of the
codec2 libraries for use by Quisk.

You can also use the separate FreeDV program available at freedv.org, and the Quisk DGT-U mode
which attaches to external digital programs. The setup is identical to fldigi and other external
digital programs.

Quisk will add the FDV mode button unless your config file contains the line
    add_freedv_button = 0
If there is a problem with the freedv module, the button will be grayed out.

The freedv module requires the codec2 library.  This library is included for Windows and for
Ubuntu 14.04 LTS 32-bit and 64-bit.  For other systems (such as ARM) you will need to build another
codec2.  Just try the FDV mode and see if it works.  It should always work on Windows, and may work
on Linux.  If the FDV button is grayed out, you need a different codec2 than the one included.  Make
a new codec2 library, and copy it to freedvpkg/libcodec2.so.

Search Order
============

Quisk will search for a valid codec2 library in this order on Windows:
1.  freedvpkg/libcodec2.dll.     Not included.  Copy the codec2 you want to use to this name.
2.  freedvpkg/libcodec2_32.dll.  The 32-bit codec2 shipped with Quisk.
3.  The system codec2 library installed outside of Quisk by another program.

Quisk will search for a valid codec2 library in this order on Linux:
1.  freedvpkg/libcodec2.so.     Not included.  Copy the codec2 you want to use to this name.
2.  freedvpkg/libcodec2_32.so.  The 32-bit codec2 shipped with Quisk.
3.  freedvpkg/libcodec2_64.so.  The 64-bit codec2 shipped with Quisk.
4.  The system codec2 library installed outside of Quisk by another program.

How to Build a New codec2
=========================

The source for codec2 is in SourceForge in the freetel project.  Or google for other sources or perhaps
a pre-built library.  If you need to compile codec2 from source, first change to a suitable directory
(not the Quisk directory) and download the source with svn:

  svn co https://svn.code.sf.net/p/freetel/code/codec2-dev codec2-dev

Note that we are using codec2-dev to get the most recent source.  Then build codec2 using the directions
found in README.cmake.  The directions given below are current as of August 2015, but check for changes.
Then copy the codec2 library to the freedvpkg directory under Quisk.  Nothing else is required.

Build a New codec2 on Linux
===========================
The Speex "-dev" packages are not needed by codec2, but are required for the Unit Test modules.
Create the codec2 shared library.  Note the "../".

  cd codec2-dev
  mkdir build_linux
  cd build_linux
  cmake -DCMAKE_BUILD_TYPE=Release -DUNITTEST=OFF  ../
  make codec2
  cd src
  cp libcodec2*  my-quisk-directory/freedvpkg

Build a New codec2 on Windows
=============================
For Windows you need to install MinGW, MSYS, and g++.  Use the MSYS bash shell.  The Speex libraries
are not needed by codec2, but are required for the Unit Test modules.  To build the Unit Test modules,
you need to install Speex and add -DSPEEXDSP_INCLUDE_DIR=../speex/include/speex -DSPEEXDSP_LIBRARY=../speex/bin.

  cd codec2-dev
  mkdir build_win32
  cd build_win32
  cmake -G "MSYS Makefiles" -DCMAKE_BUILD_TYPE=Release -DUNITTEST=OFF  ../
  make codec2
  cd src
  cp libcodec2.dll  my-quisk-directory/freedvpkg

Testing
=======
You can just start Quisk and see if the FDV button is not grayed out, and FDV works.  Or you can
test the import of freedv and look for error messages.

  cd my-quisk-directory
  c:/python27/python.exe        # (or just "python" on Linux)
    import _quisk
    _quisk.freedv_get_version()        # This should return 10 or higher for a recent codec2

