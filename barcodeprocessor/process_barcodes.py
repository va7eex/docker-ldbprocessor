#!/usr/bin/env python

__author__ = "David Rickett"
__credits__ = ["David Rickett"]
__license__ = "MIT"
__version__ = "1.0.1"
__maintainer__ = "David Rickett"
__email__ = "dap.rickett@gmail.com"
__status__ = "Production"

#start
#SKU,"Product Description","Product Category",Size,Qty,UOM,"Price per UOM","Extended Price","SU Price","WPP Savings","Cont. Deposit","Original Order#"
#end
#,,,,,,,,,,,

import sys
import os
import json
import codecs
import datetime
import redis
import re
from mysql.connector import (connection)

class BarcodeProcessor:

    BARCODETYPELOOKUPTABLE = {
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

    key_scan = 'scanned'
    key_tally = '_tally'
    key_checksum = 'checksum'

    def __init__(self, redis_ip, redis_port, mysql_ip, mysql_port, mysql_user, mysql_pass, mysql_db): 

        self.scannedlist = {}

        self.__cnx = connection.MySQLConnection(user=mysql_user, password=mysql_pass,
                    host=mysql_ip,
                    port=mysql_port,
                    database=mysql_db)
        self.__r = redis.StrictRedis(redis_ip, redis_port, charset='utf-8',decode_responses=True)

    def __sumRedisValues( self, list ):
        return  sum([int(i) for i in list if type(i)== int or i.isdigit()])

    #https://stackoverflow.com/questions/21975228/redis-python-how-to-delete-all-keys-according-to-a-specific-pattern-in-python
    def __deleteRedisDB(self, scandate ):
        print( f'Deleting databases for {scandate}:' )
        count = 0
        pipe = self.__r.pipeline()
        for key in self.__r.scan_iter(str(scandate) + '*'):
            print(f'\t{key}')
            pipe.delete(key)
            count += 1
        pipe.execute()
        return count
        
    def __lookupUPC(self, barcodes):
        cursor = self.__cnx.cursor(buffered=True)
        parsedbarcodes = {}
        for bc, qty in barcodes.items():
            # only perform queries on numbers only.
            if bc.isdigit():
                if len(bc) > 14 and bc[:1] == '01':
                    #if the barcode is over 14 digits it won't match in the system, if the characters are 01 they're not useful anyways.
                    bc = bc[2:]
                # check the orderlog for data if the UPC exists
                query = f'SELECT sku, productdescription FROM orderlog WHERE upc REGEXP {int(bc)}'
                cursor.execute(query)
                # if there is a result substitute sku, and product name where barcode is.
                if( cursor.rowcount != 0 ):
                    sku, description = cursor.fetchone()
                    parsedbarcodes[f'{sku:06},    {description}'] = qty
                else:
                    #TODO: refactor this
                    #if the first attempt fails try again but with a broader search
                    query = f'SELECT sku, productdescription FROM orderlog WHERE upc REGEXP {int(bc[2:-1])}'
                    cursor.execute(query)
                    if cursor.rowcount != 0:
                        sku, description = cursor.fetchone()
                        parsedbarcodes[f'{sku:06}, !! {description}'] = qty # the '!!' indicates loose match
                    else:
                        #if not found in db, put in the UPC.
                        parsedbarcodes[bc] = qty
            else:
                parsedbarcodes[bc] = qty
        return parsedbarcodes

    def __countBarcodes(self, scandate ):
        barcodes = {}
        tally = {}
        total = 0
        for key in self.__r.scan_iter(str(scandate) + '*'):
            print(key)
            if not f'{scandate}_scanstats' in key:
                barcodes[key] = self.__lookupUPC(self.__r.hgetall(key))
                tally[key] = self.__sumRedisValues(self.__r.hvals(key))
                total += tally[key]
        return barcodes, tally, total

    def processCSV(self, file, outfile):

        latestscan=0            #
        scangroup=0             #
        previousline=None       #
        previousgroup=scangroup #
        forReview=[]            #anything that the program deems 'strange'
        scanuser=''             #allow a user to mark that they were the ones scanning, probably never to be used
        inventorytype='liquor'  #set the type of inventory scanned, by default this will be BC LDB Store 100

        with open(file) as f:
            for line in f:
                line = re.sub('([^ \sa-zA-Z0-9.,]| {2,})','',line)
                line = line.replace('\n','').split(',')
                datescanned = datetime.datetime.strptime(line[0], '%d%m%Y').strftime('%Y%m%d')
        #        print( datescanned )
                if( int(datescanned) > latestscan ):
                    if( latestscan > 0 ):
                        self.__deleteRedisDB(latestscan)
                    self.__deleteRedisDB(datescanned)
                    latestscan = int(datescanned)
                    scangroup = 0
                    forReview=[]
                    scanuser=''
                    inventorytype='liquor'

                #if theres some hideous scan error, you can start from the beginning or go back one
                if( 'CLEARCLEARCLEAR' in line[3] ):
                    self.__deleteRedisDB(latestscan)
                    forReview=[]
                #note: theres a button on the Motorola CS3000 that does exactly this, but better
                elif( 'CLEARLASTCLEAR' in line[3] ):
                    if( previousline != None ):
                        self.__r.hincrby(f'{latestscan}_{scangroup}{scanuser}_{inventorytype}',previousline,-1)
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
                    self.__r.hincrby(f'{latestscan}_{scangroup}{scanuser}_{inventorytype}', line[3],1)
                    #generate stats, I love stats.
                    if not 'DOESNOTSCAN' in line[3]:
                        self.__r.hincrby(f'{latestscan}_scanstats', 'length: %s'%len(line[3]),1)
                        self.__r.hincrby(f'{latestscan}_scanstats', self.BARCODETYPELOOKUPTABLE[line[2]],1)
                    #if the data on the line is larger than 20 flag it for review.
                    if( len(line[3]) > 20 ):
                        forReview.append(line[3])
                    previousline=line[3]
                    previousgroup=scangroup



        self.scannedlist = {}
        self.scannedlist[latestscan] = {}
        self.scannedlist[latestscan]['receiving_type']=inventorytype
        self.scannedlist[latestscan]['barcodes_by_pallet'], scannedlist[latestscan]['_total_by_pallet'], scannedlist[latestscan]['_total'] = self.__countBarcodes(latestscan)
        self.scannedlist[latestscan]['stats4nerds'] = self.__r.hgetall(f'{latestscan}_scanstats')
        if( len(forReview) > 0 ):
            self.scannedlist[latestscan]['_possible_scan_errors'] = forReview

        with open(outfile, 'w') as fp:
            json.dump(self.scannedlist,fp,indent=2,separators=(',', ' x '),sort_keys=True)

    def __importconfig(self,file):
        return

if __name__=='__main__':
    bc = BarcodeProcessor(os.getenv('REDIS_IP'),
        os.getenv('REDIS_PORT'),
        os.getenv('MYSQL_IP'),
        os.getenv('MYSQL_PORT'),
        os.getenv('MYSQL_USER'),
        os.getenv('MYSQL_PASSWORD'), 
        os.getenv('MYSQL_DATABASE'))
    bc.processCSV(sys.argv[1], sys.argv[2])