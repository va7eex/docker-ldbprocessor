

#start
#SKU,"Product Description","Product Category",Size,Qty,UOM,"Price per UOM","Extended Price","SU Price","WPP Savings","Cont. Deposit","Original Order#"
#end
#,,,,,,,,,,,

import sys
import json
import codecs
import datetime
import redis

from constants import MYSQL_USER
from constants import MYSQL_PASS
from constants import MYSQL_IP
from constants import MYSQL_PORT
from constants import MYSQL_DATABASE
from constants import REDIS_IP
from constants import REDIS_PORT

scannedlist = {}

key_scan = 'scanned'
key_tally = '_tally'
key_checksum = 'checksum'

r = redis.StrictRedis(REDIS_IP, REDIS_PORT, charset='utf-8',decode_responses=True)

def sumRedisValues( list ):
    return  sum([int(i) for i in list if type(i)== int or i.isdigit()])

#https://stackoverflow.com/questions/21975228/redis-python-how-to-delete-all-keys-according-to-a-specific-pattern-in-python
def deleteRedisDB( scandate ):
	count = 0
	pipe = r.pipeline()
	for key in r.scan_iter(str(scandate) + '*'):
		print(key)
		pipe.delete(key)
		count += 1
	pipe.execute()
	return count

def countBarcodes( scandate ):
	barcodes = {}
	tally = {}
	total = 0
	for key in r.scan_iter(str(scandate) + '*'):
		print(key)
		barcodes[key] = r.hgetall(key)
		tally[key] = sumRedisValues(r.hvals(key))
		total += tally[key]
	return barcodes, tally, total

file=sys.argv[1]
latestscan=0
scangroup=0
previousline=None
previousgroup=scangroup
with open(file) as f:
	for line in f:
		line = line.replace('\n','').split(',')
		datescanned = datetime.datetime.strptime(line[0], '%d/%m/%Y').strftime('%Y%m%d')
#		print( datescanned )
		if( int(datescanned) > latestscan ):
			if( latestscan > 0 ):
				deleteRedisDB(latestscan)
			deleteRedisDB(datescanned)
			latestscan = int(datescanned)
			scangroup = 0

		#if theres some hideous scan error, you can start from the beginning or go back one
		if( 'CLEARCLEARCLEAR' in line[3] ):
			deleteRedisDB(latestscan)
		#note: theres a button on the Motorola CS3000 that does exactly this, but better
		elif( 'CLEARLASTCLEAR' in line[3] ):
			if( previousline != None ):
				r.hincrby(f'{latestscan}_{previousgroup}', previousline,-1)

		#breaks down the count by pallet
		elif( 'scangroupincr' in line[3] ):
			scangroup = (scangroup + 1 ) % 256
		elif( 'scangroupdecr' in line[3] ):
			scangroup = (scangroup - 1 ) % 256

		else:
			r.hincrby(f'{latestscan}_{scangroup}', line[3],1)
			previousline=line[3]
			previousgroup=scangroup



scannedlist = {}
scannedlist[latestscan] = {}
scannedlist[latestscan]['barcodes_by_pallet'], scannedlist[latestscan]['_total_by_pallet'], scannedlist[latestscan]['_total'] = countBarcodes(latestscan)

#scannedlist[latestscan]['barcodes'] = r.hgetall(latestscan)
#scannedlist[latestscan]['_tally'] = sumRedisValues(r.hvals(latestscan))
#scannedlist[latestscan]['barcodes'] = stringifyFields(latestscan)
#scannedlist[latestscan]['tally'] = sum( convertArrayToInts(r.hvals(latestscan)))

with open(sys.argv[2], 'w') as fp:
    json.dump(scannedlist,fp,indent=4,separators=(',', ': '),sort_keys=True)
