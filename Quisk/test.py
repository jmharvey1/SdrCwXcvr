#! /usr/bin/python
# -*- coding: utf-8 -*-
import sys
import _quisk as QS
dict = {'Name': 'Zabra', 'Age': 7}
Mode2Index = {'CWL':0, 'CWU':1, 'LSB':2, 'USB':3, 'AM':4, 'FM':5, 'EXT':6, 'DGT-U':7, 'DGT-L':8, 'DGT-IQ':9,
      'IMD':10, 'FDV-U':11, 'FDV-L':12, 'DGT-FM':13}
print "Value : %s" %  dict.get('Name')
print "Value : %s" %  Mode2Index.get('CWU')
print "Value : %s" %  dict.get('Education', "Never")
#print(num,"is not a prime number")
print("Done")
