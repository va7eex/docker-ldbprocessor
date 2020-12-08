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
import re
from mysql.connector import (connection)

scannedlist = {}

key_scan = 'scanned'
key_tally = '_tally'
key_checksum = 'checksum'

barcodetypelookuptable = {
    '01':'Code 39',
    '02':'Codabar',
    '03':'Code 128',
    '0C':'Code 11',
    '72':'Chinese 2 of 5',
    '04':'Discrete 2 of 5',
    '05':'IATA 2 of 5',
    '06':'Interleaved 2 of 5',
    '07':'Code 93',
    '08':'UPC-A',
    '48':'UPC-A.2',
    '88':'UPC-A.5',
    '09':'UPC-E0',
    '49':'UPC-E0.2',
    '89':'UPC-E0.5',
    '0A':'EAN-8',
    '4A':'EAN-8.2',
    '8A':'EAN-8.5',
    '0B':'EAN-13',
    '4B':'EAN-13.2',
    '8B':'EAN-13.5',
    '0E':'MSI',
    '0F':'GS1-128',
    '10':'UPC-E1',
    '50':'UPC-E1.2',
    '90':'UPC-E1.5',
    '15':'Trioptic Code 39',
    '17':'Bookland EAN',
    '23':'GS1 Databar Ltd',
    '24':'GS1 Databar Omni',
    '25':'GS1 Databar Exp'
}

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
    
def lookupUPC(barcodes):
#    return barcodes
    cursor = cnx.cursor(buffered=True)
    parsedbarcodes = {}
    for bc, qty in barcodes.items():
        if bc.isdigit():
            query = f'SELECT sku, productdescription FROM orderlog WHERE upc REGEXP {bc}'
            cursor.execute(query)
            print(query)
            print(cursor.rowcount)

            if( cursor.rowcount != 0 ):
                sku, description = cursor.fetchone()
                parsedbarcodes[f'{sku:06},{description}'] = qty
            else:
                #if not found in db, put in the UPC.
                parsedbarcodes[bc] = qty
        else:
            parsedbarcodes[bc] = qty
    return parsedbarcodes

def countBarcodes( scandate ):
    barcodes = {}
    tally = {}
    total = 0
    for key in r.scan_iter(str(scandate) + '*'):
        print(key)
        if not f'{scandate}_scanstats' in key:
            barcodes[key] = lookupUPC(r.hgetall(key))
            tally[key] = sumRedisValues(r.hvals(key))
            total += tally[key]
    return barcodes, tally, total

def processCSV(file, outfile):

    latestscan=0            #
    scangroup=0            #
    previousline=None        #
    previousgroup=scangroup        #
    forReview=[]            #anything that the program deems 'strange'
    scanuser=''            #allow a user to mark that they were the ones scanning, probably never to be used
    inventorytype='liquor'        #set the type of inventory scanned, by default this will be BC LDB Store 100

    with open(file) as f:
        for line in f:
            line = re.sub('([^ \sa-zA-Z0-9.,]| {2,})','',line)
            line = line.replace('\n','').split(',')
            datescanned = datetime.datetime.strptime(line[0], '%d%m%Y').strftime('%Y%m%d')
    #        print( datescanned )
            if( int(datescanned) > latestscan ):
                if( latestscan > 0 ):
                    deleteRedisDB(latestscan)
                deleteRedisDB(datescanned)
                latestscan = int(datescanned)
                scangroup = 0
                forReview=[]
                scanuser=''
                inventorytype='liquor'

            #if theres some hideous scan error, you can start from the beginning or go back one
            if( 'CLEARCLEARCLEAR' in line[3] ):
                deleteRedisDB(latestscan)
                forReview=[]
            #note: theres a button on the Motorola CS3000 that does exactly this, but better
            elif( 'CLEARLASTCLEAR' in line[3] ):
                if( previousline != None ):
                    r.hincrby(f'{latestscan}_{scangroup}{scanuser}_{inventorytype}',previousline,-1)
            #allow other programs to act on type of scanned inventory
            elif( 'inventorytype=' in line[3] ):
                inventorytype = line[3].replace('inventorytype=','')
            #assign initials to a specific scan group
            elif( 'scanneruser=' in line[3] ):
                scanuser=line[3].replace('scanneruser=','')

            #breaks down the count by pallet
            elif( 'scangroupincr' in line[3] ):
                scangroup = (scangroup + 1 ) % 256
            elif( 'scangroupdecr' in line[3] ):
                scangroup = (scangroup - 1 ) % 256

            else:
                # increment the key 'scanned barcode' by 1. If the key doesn't exist create and make it 1
                r.hincrby(f'{latestscan}_{scangroup}{scanuser}_{inventorytype}', line[3],1)
                #generate stats, I love stats.
                if not 'DOESNOTSCAN' in line[3]:
                    r.hincrby(f'{latestscan}_scanstats', 'length: %s'%len(line[3]),1)
                    r.hincrby(f'{latestscan}_scanstats', barcodetypelookuptable[line[2]],1)
                #if the data on the line is larger than 20 flag it for review.
                if( len(line[3]) > 20 ):
                    forReview.append(line[3])
                previousline=line[3]
                previousgroup=scangroup



    scannedlist = {}
    scannedlist[latestscan] = {}
    scannedlist[latestscan]['receiving_type']=inventorytype
    scannedlist[latestscan]['barcodes_by_pallet'], scannedlist[latestscan]['_total_by_pallet'], scannedlist[latestscan]['_total'] = countBarcodes(latestscan)
    scannedlist[latestscan]['stats4nerds'] = r.hgetall(f'{latestscan}_scanstats')
    if( len(forReview) > 0 ):
        scannedlist[latestscan]['_possible_scan_errors'] = forReview
    #scannedlist[latestscan]['barcodes'] = r.hgetall(latestscan)
    #scannedlist[latestscan]['_tally'] = sumRedisValues(r.hvals(latestscan))
    #scannedlist[latestscan]['barcodes'] = stringifyFields(latestscan)
    #scannedlist[latestscan]['tally'] = sum( convertArrayToInts(r.hvals(latestscan)))

    with open(outfile, 'w') as fp:
        json.dump(scannedlist,fp,indent=2,separators=(',', ' x '),sort_keys=True)

def importconfig(file):
    return

def main(file, outfile, **kwargs):
    for k, v in kwargs.items():
        print('keyword argument: {} = {}'.format(k, v))

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
    if 'MYSQL_DB' in kwargs:
        MYSQL_DB = kwargs['MYSQL_DB']
    if 'REDIS_IP' in kwargs:
        REDIS_IP = kwargs['REDIS_IP']
    if 'REDIS_PORT' in kwargs:
        REDIS_PORT = kwargs['REDIS_PORT']

    global cnx
    cnx = connection.MySQLConnection(user=MYSQL_USER, password=MYSQL_PASS,
                host=MYSQL_IP,
                port=MYSQL_PORT,
                database=MYSQL_DB)
    global r
    r = redis.StrictRedis(REDIS_IP, REDIS_PORT, charset='utf-8',decode_responses=True)

    processCSV(file, outfile)

if __name__=='__main__':
    main(sys.argv[1], sys.argv[2], **dict(arg.split('=') for arg in sys.argv[3:])) # kwargs
