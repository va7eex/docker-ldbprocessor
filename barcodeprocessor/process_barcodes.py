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

from logging import exception
import sys
import os
import json
import codecs
import datetime
import re
import random
import string

import requests

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

    def __init__(self, apiurl, apikey=''):
        """
        Initialize class.

        :param apiurl: Base URL for API endpoint, such as 'localhost:5000', or 'prod.example.com:12345'.
        :param apikey: API key if present.
        :param pricechangeignore: When generating a price difference report, ignore changes less than this value.
        """

        self.apikey = apikey
        self.apiurl = apiurl
        self.scannedlist = {}
        self.__s = requests.Session() 

        if not self.__apiquery(method='GET', url='/bc/register', **{'check': True})[0]['success']:
            self.__apiquery(method='POST', url='/bc/register', **{'scanner_terminal': f'bcprocessor_{random.randint(1000,9999)}', 'headless': True})

    def __apiquery(self, method='GET', url='', **kwargs):
        """
        Send an API query.

        :param method: The HTTP method to use, ex GET/SET/PUT.
        :param url: Example the '/foo/bar' of 'localhost:1234/foo/bar'
        :param kwargs: All data to be sent, as a json dict.
        """
        print(f'API query to: http://{self.apiurl}{url}')
        if self.apikey:
            if method == 'POST':
                r = self.__s.post(f'http://{self.apiurl}{url}', data={'apikey': self.apikey, **kwargs})
            else:
                r = self.__s.get(f'http://{self.apiurl}{url}', params={'apikey': self.apikey, **kwargs})
        else:
            if method == 'POST':
                r = self.__s.post(f'http://{self.apiurl}{url}', data={**kwargs})
            else:
                r = self.__s.get(f'http://{self.apiurl}{url}', params={**kwargs})
        if r.status_code >= 500:
            raise Exception(f'Error on server: {r.status_code}')
        elif r.status_code >= 400:
            if r.status_code == 401: raise Exception('Not authorized')
            raise Exception(f'Error in client, GET/POST/PUT/PATCH/DELETE mismatch: {r.status_code}')

        return r.json(), r.status_code
    
    def __countbarcodes(self, datestamp):
        payload, status = self.__apiquery('GET','/bc/lastscanned')

        if not payload['success']: raise exception('not authorized')

        barcodes = {}
        for scangroup in payload['barcodes'].keys():
            barcodes[scangroup] = self.__lookupUPC(payload['barcodes']['scangroup'])

        return barcodes, payload['tally'], payload['total']

    def __lookupUPC(self, barcodes):
        cursor = self.__cnx.cursor(buffered=True)
        parsedbarcodes = {}
        for bc, qty in barcodes.items():
            # only perform queries on numbers only.
            if bc.isdigit():
                if len(bc) > 14 and bc[:1] == '01':
                    #if the barcode is over 14 digits it won't match in the system, if the first two characters are 01 they're not useful anyways.
                    bc = bc[2:]
                # check the API for data if the UPC exists
                payload, status = self.__apiquery('GET','/search', **{'upc': bc})
                # if there is a result substitute sku, and product name where barcode is.
                if status == 200:
                    sku, description = payload['sku'], payload['productdescription']
                    parsedbarcodes[f'{sku:06},    {description}'] = qty
                elif status == 204:
                    #TODO: refactor this
                    #if the first attempt fails try again but with a broader search
                    payload, status = self.__apiquery('GET','/search', **{'upc': int(bc[2:-1]) })
                    if cursor.rowcount != 0:
                        sku, description = payload['sku'], payload['productdescription']
                        parsedbarcodes[f'{sku:06}, !! {description}'] = qty # the '!!' indicates loose match
                    else:
                        #if not found in db, put in the UPC.
                        parsedbarcodes[bc] = qty
            else:
                parsedbarcodes[bc] = qty
        return parsedbarcodes

    def __urlpayload(self, upc, datestamp):
        return {'machine': True,
                'upc': upc,
                'scangroup': self.scangroup,
                'datestamp': datestamp}

    def processCSV(self, file, outfile):

        latestscan=0            #
        self.scangroup=0             #
        previousline=None       #
        previousgroup=self.scangroup #
        forReview=[]            #anything that the program deems 'strange'
        scanuser=''             #allow a user to mark that they were the ones scanning, probably never to be used
        inventorytype='liquor'  #set the type of inventory scanned, by default this will be BC LDB Store 100

        with open(file) as f:
            #for line in reversed(f): #processing lines from bottom to top.
            for line in f: #just in case we need this later
                line = re.sub(r'([^ \sa-zA-Z0-9.,]| {2,})','',line)
                line = line.replace('\n','').split(',')
                datescanned = datetime.datetime.strptime(line[0], '%d%m%Y').strftime('%Y%m%d')

                #we are reversing the order of which things are processed
                if int(datescanned) < latestscan:
                    break

                if( int(datescanned) > latestscan ):
                    if( latestscan > 0 ):
                        payload, status = self.__apiquery('POST','/bc/deleteall',**{'scandate': latestscan})
                    payload, status = self.__apiquery('POST','/bc/deleteall',**{'scandate': datescanned})
                    latestscan = int(datescanned)
                    self.scangroup = 0
                    forReview=[]
                    scanuser=''
                    inventorytype='liquor'

                #if theres some hideous scan error, you can start from the beginning or go back one
                if( 'DELALL' in line[3] ):
                    payload, status = self.__apiquery('POST','/bc/deleteall',**{'scandate': latestscan})
                    forReview=[]
                #note: theres a button on the Motorola CS3000 that does exactly this, but better
                elif( 'DELLAST' in line[3] ):
                    rows, status = self.__apiquery('GET','/bc/lastscanned')
                    if status == 200:
                        self.__apiquery('POST', '/bc/scan', **{ 'addremove': 'remove', **self.__urlpayload(rows['last_scanned'], datescanned) })
                #allow other programs to act on type of scanned inventory
                elif( 'inventorytype=' in line[3] ):
                    inventorytype = line[3].replace('inventorytype=','')
                #assign initials to a specific scan group
                elif( 'scanneruser=' in line[3] ):
                    scanuser=line[3].replace('scanneruser=','')

                #breaks down the count by pallet
                elif( 'scangroupincr' in line[3] ):
                    self.scangroup = (self.scangroup + 1 ) % 256
                elif( 'scangroupdecr' in line[3] ):
                    self.scangroup = (self.scangroup - 1 ) % 256

                else:
                    # increment the key 'scanned barcode' by 1. If the key doesn't exist create and make it 1
                    self.__apiquery('POST', '/bc/scan', **self.__urlpayload(line[3], datescanned))
                    #generate stats, I love stats.
                    # if not 'DOESNOTSCAN' in line[3]:
                    #     self.__r.hincrby(f'{latestscan}_scanstats', 'length: %s'%len(line[3]),1)
                    #     self.__r.hincrby(f'{latestscan}_scanstats', self.BARCODETYPELOOKUPTABLE[line[2]],1)
                    #if the data on the line is larger than 20 flag it for review.
                    if( len(line[3]) > 20 ):
                        forReview.append(line[3])
                    previousline=line[3]
                    previousgroup=self.scangroup



        self.scannedlist = {}
        self.scannedlist[latestscan] = {}
        # self.scannedlist[latestscan]['receiving_type']=inventorytype
        self.scannedlist[latestscan]['barcodes_by_pallet'], self.scannedlist[latestscan]['_total_by_pallet'], self.scannedlist[latestscan]['_total'] = self.__countBarcodes(latestscan)
        # self.scannedlist[latestscan]['stats4nerds'] = self.__r.hgetall(f'{latestscan}_scanstats')
        if( len(forReview) > 0 ):
            self.scannedlist[latestscan]['_possible_scan_errors'] = forReview

        with open(outfile, 'w') as fp:
            json.dump(self.scannedlist,fp,indent=2,separators=(',', ' x '),sort_keys=True)

    def __importconfig(self,file):
        return

if __name__=='__main__':
    bc = BarcodeProcessor(
        os.getenv('APIURL'),
        os.getenv('APIKEY'))
    bc.processCSV(sys.argv[1], sys.argv[2])