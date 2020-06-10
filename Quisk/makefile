
all:
	python setup.py build_ext --force --inplace

win:
	C:/Python27/python.exe setup.py build_ext -c mingw32 --inplace --force

winrun:
	C:/Python27/python.exe quisk.py

winmsi:
	C:/Python27/python.exe wix/files.py

wininstall:
	msiexec -i wix\\quisk.msi

winuninstall:
	msiexec -x wix\\quisk.msi

macports:
	env ARCHFLAGS="-arch x86_64" python setup.py build_ext --force --inplace -D USE_MACPORTS
