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

import os
import sys
import json
import time
import datetime
import re
import requests
import logging
from datetime import date

from LineItem import LineItemAR as LineItem

class arinvoice:
    """
    For processing BCLDB Store 100 ARinvoice files sent out to accompany the weekly order.

    Files are sent with the name format `XXARNEWINVOICE_[0-9]{5,}_1.xls`.
    BCLDB uses Oracle BI Publisher to send files.
    """

    DIRECTORY='/var/ldbinvoice'
    PB_FILE='processedbarcodes.json'

    DOLLARAMOUNT = re.compile('\$\d+,\d{3}')

    def __init__(self, apiurl, apikey='', pricechangeignore=0.0):
        """
        Initialize class.

        :param apiurl: Base URL for API endpoint, such as 'localhost:5000', or 'prod.example.com:12345'.
        :param apikey: API key if present.
        :param pricechangeignore: When generating a price difference report, ignore changes less than this value.
        """

        self.apikey = apikey
        self.apiurl = apiurl
        self.__s = requests.Session() 
        self.pricechangeignore = abs(float(pricechangeignore))

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
        logging.debug(f'API query to: http://{self.apiurl}{url}')
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
        
        time.sleep(0.05) #if we don't limit the number of queries per second the server will 503 us.
        return r.json(), r.status_code

    # write price report to file, later will make this a redis DB
    def __addtopricechangereport(self, pricechanges, newitems, **kwargs):
        """
        Compares incoming price per sku and outputs a price change to file.

        This will prepend various alerts for quick recognition of large changes.

        :param pricechanges: 1D Array of price changes, passed as a reference.
        :param newitems: 1D array of new items, passed as a reference.
        :param kwargs: Dict of values to compare against.

        :return: Returns 1 if a price change is suppressed, returns 0 under normal conditions.
        :rtype: int
        """
        if kwargs['oldprice'] is not None and kwargs['oldlastupdated'] is not None:
            #ignore price changes below a threshold
            
            if abs(kwargs['suprice']-kwargs['oldprice'])<self.pricechangeignore: return 1

            alert=''
            if( (kwargs['suprice']-kwargs['oldprice'])/ kwargs['oldprice'] > 0.1 ):
                alert += '[pc>10%]'

            if( kwargs['suprice'] >= (kwargs['oldprice'] + 5) ):
                alert += '[pc$5+]'
            elif( kwargs['suprice'] >= (kwargs['oldprice'] + 3) ):
                alert += '[pc$3+]'
            elif( kwargs['suprice'] >= (kwargs['oldprice'] + 1) ):
                alert += '[pc$1+]'

            pricechanges.append(f"{alert} {kwargs['sku']:06}: {kwargs['oldprice']} changed to {kwargs['suprice']} (last updated {kwargs['oldlastupdated']})")
        else:
            upc = ''
            #if this is a new item, calculate the UPC of the item if available.
            if 'gtin12' in kwargs and 'gtin13' in kwargs:
                upc = f"\t\tCalculated UPC**:  \t{kwargs['gtin13'][:1]}+{kwargs['gtin12']}/{kwargs['gtin13'][-1:]}"
            elif 'gtin12' in kwargs:
                upc = f"\t\tCalculated UPC-A*: \t{kwargs['gtin12']}"
            elif 'gtin13' in kwargs:
                upc = f"\t\tCalculated EAN-13*:\t{kwargs['gtin13']}"
            
            newitems.append(f"[NEW] {kwargs['sku']:06}: {kwargs['suprice']}{upc}")
        
        return 0

    def __itmdb_generatechangereport(self, invoicedate):
        """
        Queries API to find price changes and starts the report process.
        
        :param invoicedate: The date to check against.
        
        :rtype: None
        """
        rows, status = self.__apiquery('GET', '/ar/pricechange', **{'invoicedate': invoicedate})

        logging.debug(len(rows))

        suppressedchanges = 0 # number of suppressed changes
        newitems = []
        pricechanges = []

        for row in rows.values():
            logging.debug(row)
            suppressedchanges += self.__addtopricechangereport( pricechanges, newitems, **row )

        with open(f'{self.DIRECTORY}/{invoicedate}_pricedeltareport.txt', 'w') as fp:
            #document title
            fp.write(f'Price Delta Report for {invoicedate}\n\n')
            #list of changes
            for item in pricechanges:
                fp.write(f'{item}\n')
            #if one or more price changes were below threshold, report that.
            if suppressedchanges > 0:
                fp.write(f"\n{suppressedchanges} items were below the ${self.pricechangeignore} threshold and have been ignored.\n")
            #list of new items
            if newitems:
                fp.write(f'\n\nNew Items as of {invoicedate}:\n\n')
                for item in newitems:
                    fp.write(f'{item}\n')
                fp.write('\n\nDisclaimer:\n')
                fp.write('\t*  Product barcode is calculated based on automated reports and may not be accurate.\n')
                fp.write('\t** If UPC is presented as A+BBB/C format, UPC-A can be extracted by taking BBB.\n')
                fp.write('\t   EAN-13 can be extracted by adding A to BBB and replacing the last B with C.\n')
            

    def __dopricechangelist(self, invoicedate):
        """
        Updates API with order's prices.

        :param invoicedate: Date of invoice.

        :rtype: None
        """

        rows, status = self.__apiquery('GET', '/ar/getinvoice', **{'invoicedate': invoicedate})
        for row in rows.values():
            rows, status = self.__apiquery('POST', '/ar/pricechange', **{'sku': f"{row['sku']}", 'price': f"{row['suprice']}"})
        
        self.__itmdb_generatechangereport(invoicedate)

    def __addlineitem(self, line, invoicedate):
        """
        Converts a static line from the incoming arinvoice.xls file to a structured dict and uploads to the API.

        :param line: A line read from the incoming csv file.
        :param invoicedate: Date of invoice.

        :rtype: None
        """

        li = LineItem(*line.split(','))
        
        self.__apiquery('POST', '/ar/addlineitem', **{'invoicedate': invoicedate, **li.getall(urlsafe=True)})


    def __printinvoicetofile(self, invoicedate):
        """
        Exports invoice stored in API to a format Profitek POS can understand.

        File is a headerless CSV file with the format '$sku,$suquantity,$suprice,$unneccessarydetails'
        Please note, all values after and including $unneccessarydetails are ignored, they're just there for humans.

        :param invoicedate: Date of invoice.

        :rtype: None
        """
        logging.info(f'Printing invoice {invoicedate} to file')

        rows, status = self.__apiquery('GET', '/ar/getinvoice', **{'invoicedate': invoicedate})

        logging.info('Total Rows: %s'%len(rows))

        with open(f'{self.DIRECTORY}/{invoicedate}_for-PO-import.txt', 'w') as fp:
            for row in rows.values():
                fp.write('%s,%s,%s,%s\n' % ( f'{row["sku"]:06}', row['suquantity'], row['suprice'], row['productdescription'] ))


    def __checkforbadbarcodes(self, invoicedate):
        """
        Checks for bad barcodes in API and if they exist on this order print replacement barcode stickers.

        Label templates are preformatted and mathematically generated via the BarcodePrinter class in API.

        :param invoicedate: Date of invoice.

        :rtype: None
        """
        rows, status = self.__apiquery('GET', '/ar/findbadbarcodes', **{'invoicedate': invoicedate})
        logging.info(len(rows))

        for row in rows.values():
            self.__apiquery('POST', '/labelmaker/print', **row)

    def processCSV(self, inputfile):
        """
        Reads the ARinvoice .xls file line by line and sends to API.

        This function will sanitize strings for undesirable characters as well as cleanup dollar amounts >999.99.
        This will also extract the invoice date from the file.

        :param inputfile: File to read from. Can be full or relative path.

        :rtype: None
        """
        #this is what an empty line looks like
        emptyline = ',,,,,,,,,,,,,'
        with open(inputfile) as f:
            append=False
            for line in f:
                #trim all whitespace to start`
                line = line.strip()

        #        if( not append ):
        #            logging.info(line)

                if(line.find('Invoice Date:') > -1 ):
                    invoicedatefromldb=str(line.split(',')[len(line.split(','))-1].strip())
        #            invoicedate = datetime.datetime.strptime(invoicedatefromldb,'%Y-%m-%d %H:%M:%S.%f')
                    invoicedate = datetime.datetime.strptime(invoicedatefromldb,'%d-%b-%y').strftime('%Y-%m-%d')
                    logging.info(invoicedate)
                if( line.strip() == emptyline.strip() and append ):
                    append=False
                if( append ):
                    imparsabledollaramount = self.DOLLARAMOUNT.search(line)
                    if imparsabledollaramount is not None:
                        logging.warning( f'!!! WARNING: comma in dollar amount !!! {imparsabledollaramount.group()}' )
                        line = line.replace(imparsabledollaramount.group(), imparsabledollaramount.group().replace(',',''))

                    line = re.sub('([^ \sa-zA-Z0-9.,]| {2,})','',line)
                    line = re.sub('( , |, | ,)', ',', line)
                    line = re.sub('(,,|, ,)', ',0.00,', line)

                    self.__addlineitem(line, invoicedate)
                if( line.find( 'SKU,Product Description') > -1):
                    append=True
                    emptyline = re.sub('[^,]','',line)
                    logging.info(emptyline)
                    logging.info(line.strip())

        self.__checkforbadbarcodes( invoicedate )
        self.__dopricechangelist( invoicedate )
        self.__printinvoicetofile( invoicedate )


if __name__=='__main__':
    ari = arinvoice(
        os.getenv('APIURL'),
        os.getenv('APIKEY'),
        pricechangeignore=os.getenv('PRICECHANGEIGNORE'))
    ari.processCSV(
        sys.argv[1])