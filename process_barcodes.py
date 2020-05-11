#!/usr/bin/env python

__author__ = "David Rickett"
__credits__ = ["David Rickett"]
__license__ = "GPL"
__version__ = "1.0.1"
__maintainer__ = "David Rickett"
__email__ = "dap.rickett@gmail.com"
__status__ = "Production"

#start
#SKU,"Product Description","Product Category",Size,Qty,UOM,"Price per UOM","Extended Price","SU Price","WPP Savings","Cont. Deposit","Original Order#"
#end
#,,,,,,,,,,,

import sys
import json
import codecs
import datetime

from constants import MYSQL_USER
from constants import MYSQL_PASS
from constants import MYSQL_IP
from constants import MYSQL_PORT
from constants import MYSQL_DATABASE

scannedlist = {}

key_scan = 'scanned'
key_tally = '_tally'
key_checksum = 'checksum'

file=sys.argv[1]
with open(file) as f:
	for line in f:
		line = line.replace('\n','').split(',')
		datescanned = datetime.datetime.strptime(line[0], '%d/%m/%Y').strftime('%Y-%m-%d')
#		print( datescanned )
		if datescanned in scannedlist:
			if line[3] in scannedlist[datescanned][key_scan]:
				scannedlist[datescanned][key_scan][line[3]] = scannedlist[datescanned][key_scan][line[3]] + 1
			else:
				scannedlist[datescanned][key_scan][line[3]] = 1
			scannedlist[datescanned][key_tally] = scannedlist[datescanned][key_tally] + 1
			scannedlist[datescanned][key_checksum] = (
							(int)(datescanned.split('-')[0])
							+ (int)(datescanned.split('-')[1])
							+ (int)(datescanned.split('-')[2])
							+ scannedlist[datescanned][key_tally]) % 256
		else:
			scannedlist[datescanned] = {}
			scannedlist[datescanned][key_scan] = {}
			scannedlist[datescanned][key_scan][line[3]] = 1
			scannedlist[datescanned][key_tally] = 1
			scannedlist[datescanned][key_checksum] = (
							(int)(datescanned.split('-')[0])
							+ (int)(datescanned.split('-')[1])
							+ (int)(datescanned.split('-')[2])
							+ scannedlist[datescanned][key_tally]) % 256

#print(scannedlist)

with open(sys.argv[2], 'w') as fp:
    json.dump(scannedlist,fp,indent=4,separators=(',', ': '),sort_keys=True)
