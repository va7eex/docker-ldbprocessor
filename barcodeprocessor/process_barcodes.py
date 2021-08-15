#!/usr/bin/env python

__author__ = "David Rickett"
__credits__ = ["David Rickett"]
__license__ = "MIT"
__version__ = "1.0.1"
__maintainer__ = "David Rickett"
__email__ = "dap.rickett@gmail.com"
__status__ = "Production"

#start:
#SKU,"Product Description","Product Category",Size,Qty,UOM,"Price per UOM","Extended Price","SU Price","WPP Savings","Cont. Deposit","Original Order#"

#end:
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
import time
import logging

import requests

class BarcodeProcessor:

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
            if os.getenv('CONTAINER_ID'):
                ID = os.getenv('CONTAINER_ID')
            else:
                ID = random.randint(1000,9999)
            self.__apiquery(method='POST', url='/bc/register', **{'scanner_terminal': f'bcprocessor_{ID}', 'headless': True})

    def __apiquery(self, method='GET', url='', **kwargs):
        """
        Send an API query.

        :param method: The HTTP method to use, ex GET/SET/PUT.
        :param url: Example the '/foo/bar' of 'localhost:1234/foo/bar'
        :param kwargs: All data to be sent, as a json dict.

        :raise Exception: Raises exception when http code is not 200.
        :return: Returns a tuple containing the json response and http status code.
        :rtype: dict, int
        """
        logging.info(f'API query to: http://{self.apiurl}{url}')
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
        time.sleep(0.01)
        return r.json(), r.status_code
    
    def __lookupUPC(self, barcodes):
        """
        Crossreferences barcodes scanned by CS3000 series scanners with CSPC/SKU numbers provided by Order Report Processor.
        Will attempt two rounds of matching in descending order of accuracy:
        - First round is a direct search
        - Second round is searching with a substring by removing the GTIN-14 Indicator and Check Digit.

        If a match is found, this will replace the key `barcode` with the key `sku,    description`. The presence of `!!` in this indicates it is a round 2 match and may not be as accurate.

        :param dict barcodes: A key-value list formatted as `{ barcode: quantity }`.
        :rtype: dict
        :return: Returns a dict formatted as `{ barcode/sku: quantity }`.
        """
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
                    if status == 204:
                        sku, description = payload['sku'], payload['productdescription']
                        parsedbarcodes[f'{sku:06}, !! {description}'] = qty # the '!!' indicates loose match
                    else:
                        #if not found in db, put in the UPC.
                        parsedbarcodes[bc] = qty
            else:
                parsedbarcodes[bc] = qty
        return parsedbarcodes

    def __countBarcodes(self, datestamp):
        """
        Retrieves the list of barcodes scanned, and totals. Attempts to cross reference UPCs with SKUs.

        :param str datestamp: A date in YYYYMMDD.

        :rtype: dict, dict, int
        :return: Returns a list of barcodes, a tally per scangroup, and a total of all barcodes.
        """
        payload, status = self.__apiquery('GET','/bc/countbarcodes', **{'datestamp': datestamp})

        logging.debug(payload)

        barcodes = {}
        for scangroup in payload['barcodes'].keys():
            barcodes[scangroup] = self.__lookupUPC(payload['barcodes'][scangroup])

        return barcodes, payload['tally'], payload['total']

    def __urlpayload(self, upc, datestamp):
        """Formats url payload.

        :param int upc: UPC scanned.
        :param datetime: Datestamp in YYYYMMDD.
        
        :rtype: dict
        :return: Returns a dict of values to be sent in a web request.
        """
        return {'machine': True, #supresses some checks on the server side
                'upc': upc,
                'scangroup': self.scangroup,
                'datestamp': datestamp}

    def __santitizeline(self, line):
        """
        Strips any unwanted characters and whitespace from the line and reformats date stamp.
        
        :param str line: A full line from the file.
        :rtype: str
        :return: A sanitized string.
        """
        line = re.sub('([^ \sa-zA-Z0-9.,]| {2,})','',line)
        line = line.replace('\n','').split(',')
        datescanned = datetime.datetime.strptime(line[0], '%d%m%Y').strftime('%Y%m%d')
        return f'{datescanned},' + ','.join(line[1:])

    def __findlastdate(self, file):
        """
        Finds and returns the latest date in the file uploaded from the CS3070.
        
        :param str file:

        :rtype: str
        :return: Finds the latest date in the scanned file.
        """
        with open(file, 'r') as f:
            lines = f.read().splitlines()
            last_line = self.__santitizeline(lines[-1]).split(',')
            return last_line[0]

    def processCSV(self, file, outfile):

        latestdate = self.__findlastdate(file)

        #if this list already exists, delete it.
        payload, status = self.__apiquery('POST','/bc/deleteall',**{'scandate': latestdate})

        self.scangroup=0             #
        previousline=None       #
        previousgroup=self.scangroup #
        forReview=[]            #anything that the program deems 'strange'
        scanuser=''             #allow a user to mark that they were the ones scanning, probably never to be used
        inventorytype='liquor'  #set the type of inventory scanned, by default this will be BC LDB Store 100

        with open(file,'r') as f:
            #for line in reversed(f): #processing lines from bottom to top.
            for line in f: #just in case we need this later
                line = self.__santitizeline(line).split(',')
                datescanned = line[0]

                if latestdate != datescanned: continue

                #if theres some hideous scan error, you can start from the beginning or go back one
                if( 'DELALL' in line[3] ):
                    payload, status = self.__apiquery('POST','/bc/deleteall',**{'scandate': latestdate})
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
                    self.__apiquery('POST', '/bc/scan', **self.__urlpayload(f'cs,{line[2]}{line[3]}', datescanned))
                    
                    #if the data on the line is larger than 20 flag it for review.
                    #this occurs on some products that concatenate two different GS1 codes into a single barcode.
                    if( len(line[3]) > 20 ):
                        forReview.append(line[3])
                    previousline=line[3]
                    previousgroup=self.scangroup



        self.scannedlist = {}
        self.scannedlist[latestdate] = {}
        self.scannedlist[latestdate]['barcodes_by_pallet'], self.scannedlist[latestdate]['_total_by_pallet'], self.scannedlist[latestdate]['_total'] = self.__countBarcodes(latestdate)
        if( len(forReview) > 0 ):
            self.scannedlist[latestdate]['_possible_scan_errors'] = forReview

        with open(outfile, 'w') as fp:
            json.dump(self.scannedlist,fp,indent=2,separators=(',', ' x '),sort_keys=True)

    def __importconfig(self,file):
        return

if __name__=='__main__':
    bc = BarcodeProcessor(
        os.getenv('APIURL'),
        os.getenv('APIKEY'))
    bc.processCSV(sys.argv[1], sys.argv[2])