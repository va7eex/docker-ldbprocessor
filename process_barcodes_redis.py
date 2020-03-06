

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

file=sys.argv[1]
latestscan=0
with open(file) as f:
	for line in f:
		line = line.replace('\n','').split(',')
		datescanned = datetime.datetime.strptime(line[0], '%d/%m/%Y').strftime('%Y%m%d')
#		print( datescanned )
		if( int(datescanned) > latestscan ):
			latestscan = int(datescanned)
			r.delete(latestscan)

		r.hincrby(int(datescanned), line[3],1)

scannedlist = {}
scannedlist[latestscan] = {}
scannedlist[latestscan]['barcodes'] = r.hgetall(latestscan)
scannedlist[latestscan]['_tally'] = sumRedisValues(r.hvals(latestscan))
#scannedlist[latestscan]['barcodes'] = stringifyFields(latestscan)
#scannedlist[latestscan]['tally'] = sum( convertArrayToInts(r.hvals(latestscan)))

with open(sys.argv[2], 'w') as fp:
    json.dump(scannedlist,fp,indent=4,separators=(',', ': '),sort_keys=True)
