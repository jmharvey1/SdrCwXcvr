#!/usr/bin/python

import quisk	# May be quisk.py or package quisk

if quisk.__file__.find('__init__') >= 0:	# quisk is the package
  import quisk.quisk as quisk

quisk.main()
