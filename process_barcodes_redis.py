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
import redis

MYSQL_IP='127.0.0.1'
MYSQL_PORT=3306
MYSQL_USER=None
MYSQL_PASS=None
MYSQL_DB=None
REDIS_IP='127.0.0.1'
REDIS_PORT=6783

r = None

scannedlist = {}

key_scan = 'scanned'
key_tally = '_tally'
key_checksum = 'checksum'


def sumRedisValues( list ):
    return  sum([int(i) for i in list if type(i)== int or i.isdigit()])

#https://stackoverflow.com/questions/21975228/redis-python-how-to-delete-all-keys-according-to-a-specific-pattern-in-python
def deleteRedisDB( scandate ):
	print( f'Deleting databases for {scandate}:' )
	count = 0
	pipe = r.pipeline()
	for key in r.scan_iter(str(scandate) + '*'):
		print(f'\t{key}')
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
forReview=[]
scanuser=''

def processCSV(file):
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
				forReview=[]
				scanuser=''

			#if theres some hideous scan error, you can start from the beginning or go back one
			if( 'CLEARCLEARCLEAR' in line[3] ):
				deleteRedisDB(latestscan)
				forReview=[]
			#note: theres a button on the Motorola CS3000 that does exactly this, but better
			elif( 'CLEARLASTCLEAR' in line[3] ):
				if( previousline != None ):
					r.hincrby(f'{latestscan}_{previousgroup}', previousline,-1)

			elif( 'scanuser_' in line[3] ):
				scanuser=line[3].replace('scanuser_','')

			#breaks down the count by pallet
			elif( 'scangroupincr' in line[3] ):
				scangroup = (scangroup + 1 ) % 256
			elif( 'scangroupdecr' in line[3] ):
				scangroup = (scangroup - 1 ) % 256

			else:
				r.hincrby(f'{latestscan}_{scangroup}{scanuser}', line[3],1)
				if( len(line[3]) > 20 ):
					forReview.append(line[3])
				previousline=line[3]
				previousgroup=scangroup



	scannedlist = {}
	scannedlist[latestscan] = {}
	scannedlist[latestscan]['barcodes_by_pallet'], scannedlist[latestscan]['_total_by_pallet'], scannedlist[latestscan]['_total'] = countBarcodes(latestscan)
	if( len(forReview) > 0 ):
		scannedlist[latestscan]['_possible_scan_errors'] = forReview
	#scannedlist[latestscan]['barcodes'] = r.hgetall(latestscan)
	#scannedlist[latestscan]['_tally'] = sumRedisValues(r.hvals(latestscan))
	#scannedlist[latestscan]['barcodes'] = stringifyFields(latestscan)
	#scannedlist[latestscan]['tally'] = sum( convertArrayToInts(r.hvals(latestscan)))

	with open(outfile, 'w') as fp:
	    json.dump(scannedlist,fp,indent=4,separators=(',', ': '),sort_keys=True)

def importconfig(file):
	return

def main(file, outfile, **kwargs):
        print('Called myscript with:')
        for k, v in kwargs.items():
                print('keyword argument: {} = {}'.format(k, v))

        global MYSQL_USER
        global MYSQL_PASS
        global MYSQL_IP
        global MYSQL_PORT
	global MYSQL_DB
        global REDIS_IP
        global REDIS_PORT
	global r

        #import a config file
        if 'configfile' in kwargs:
                importconfig(kwargs['configfile'])

        if 'MYSQL_USER' in kwargs:
                MYSQL_USER = kwargs['MYSQL_USER']
        if 'MYSQL_PASS' in kwargs:
                MYSQL_PASS = kwargs['MYSQL_PASS']
        if 'MYSQL_IP' in kwargs:
                MYSQL_IP = kwargs['MYSQL_IP']
        if 'MYSQL_PORT' in kwargs:
                MYSQL_PORT = int(kwargs['MYSQL_PORT'])
        if 'MYSQL_DB' in kwargs:
                MYSQL_DB = kwargs['MYSQL_DB']
        if 'REDIS_IP' in kwargs:
                REDIS_IP = kwargs['REDIS_IP']
        if 'REDIS_PORT' in kwargs:

	r = redis.StrictRedis(REDIS_IP, REDIS_PORT, charset='utf-8',decode_responses=True)
                REDIS_PORT = int(kwargs['REDIS_PORT'])

	processCSV(file, outfile)

if __name__=='__main__':
        main(sys.argv[1], sys.argv[2], **dict(arg.split('=') for arg in sys.argv[2:])) # kwargs
