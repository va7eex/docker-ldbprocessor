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
from datetime import date

from LineItem import LineItemAR as LineItem

class arinvoice:
    """
    For processing BCLDB Store 100 ARinvoice files sent out to accompany the weekly order.

    Files are sent with the name format r'XXARNEWINVOICE_[0-9]{5,}_1.xls'.
    BCLDB uses Oracle BI Publisher to send files.
    """

    DIRECTORY='/var/ldbinvoice'
    PB_FILE='processedbarcodes.json'

    DOLLARAMOUNT = re.compile(r'\$\d+,\d{3}')

    def __init__(self, apiurl, apikey='', pricechangeignore=0.0):
        """
        Initialize class.

        :param apiurl: Base URL for API endpoint, such as 'localhost:5000', or 'prod.example.com:12345'.
        :param apikey: API key if present.
        :param pricechangeignore: When generating a price difference report, ignore changes less than this value.
        """

        self.apikey = apikey
        self.apiurl = apiurl
        self.pricechangeignore = float(pricechangeignore)

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
                r = requests.post(f'{method}', f'http://{self.apiurl}{url}', cookies=self.cookies, data={'apikey': self.apikey, **kwargs})
            else:
                r = requests.get(f'{method}', f'http://{self.apiurl}{url}', cookies=self.cookies, params={'apikey': self.apikey, **kwargs})
        else:
            if method == 'POST':
                r = requests.post(f'{method}', f'http://{self.apiurl}{url}', cookies=self.cookies, data={**kwargs})
            else:
                r = requests.get(f'{method}', f'http://{self.apiurl}{url}', cookies=self.cookies, params={**kwargs})
        if r.status >= 500:
            raise Exception(f'Error on server: {r.status}')
        elif r.status >= 400:
            if r.status == 401: raise Exception('Not authorized')
            raise Exception(f'Error in client, GET/POST/PUT/PATCH/DELETE mismatch: {r.status}')
        
        self.cookies = requests.cookies.RequestsCookiesJar()

        return r.json(), r.status_code

    # write price report to file, later will make this a redis DB
    def __addtopricechangereport(self, invoicedate, **kwargs):
        """
        Compares incoming price per sku and outputs a price change to file.

        This will prepend various alerts for quick recognition of large changes.

        :param invoicedate: Date of invoice, to be placed in filename.
        :param kwargs: Dict of values to compare against.
        """
        with open(f'{self.DIRECTORY}/{invoicedate}_pricedeltareport.txt', 'a') as fp:
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

                fp.write(f"{alert} {kwargs['sku']:06}: {kwargs['oldprice']} changed to {kwargs['suprice']} (last updated {kwargs['oldlastupdated']})\n")
            else:
                fp.write(f"[NEW] {kwargs['sku']:06}: {kwargs['suprice']}\n")
            
            return 0

    def __itmdb_checkchange(self, invoicedate):
        """
        Queries API to find price changes and starts the report process.
        
        :param invoicedate: The date to check against.
        """
        rows, status = self.__apiquery('GET', '/ar/pricechange', **{'invoicedate': invoicedate})

        print(len(rows))

        suppressedchanges = 0

        for row in rows.values():
            print(row)
            suppressedchanges += self.__addtopricechangereport( invoicedate, **row )

        #if one or more price changes were below threshold, report that.
        if suppressedchanges > 0:
            with open(f'{self.DIRECTORY}/{invoicedate}_pricedeltareport.txt', 'a') as fp:
                fp.write(f"\n\n{suppressedchanges} items were below the ${self.pricechangeignore} threshold and have been ignored.")
            

    def __dopricechangelist(self, invoicedate):
        """
        Updates API with order's prices.

        :param invoicedate: Date of invoice.
        """

        rows, status = self.__apiquery('GET', '/ar/getinvoice', **{'invoicedate': invoicedate})
        for row in rows.values():
            rows, status = self.__apiquery('PUT', '/ar/pricechange', **{'sku': f"{row['sku']}", 'price': f"{row['suprice']}"})
        
        self.__itmdb_checkchange(invoicedate)

    def __addlineitem(self, line, invoicedate):
        """
        Converts a static line from the incoming arinvoice.xls file to a structured dict and uploads to the API.

        :param line: A line read from the incoming csv file.
        :param invoicedate: Date of invoice.
        """

        li = LineItem(*line.split(','))
        
        self.__apiquery('POST', '/ar/addlineitem', **{'invoicedate': invoicedate, **li.getall(urlsafe=True)})


    def __printinvoicetofile(self, invoicedate):
        """
        Exports invoice stored in API to a format Profitek POS can understand.

        File is a headerless CSV file with the format '$sku,$suquantity,$suprice,$unneccessarydetails'
        Please note, all values after and including $unneccessarydetails are ignored, they're just there for humans.

        :param invoicedate: Date of invoice.
        """
        print(f'Printing invoice {invoicedate} to file')

        rows, status = self.__apiquery('GET', '/ar/getinvoice', **{'invoicedate': invoicedate})

        print('Total Rows: %s'%len(rows))

        if not os.path.exists(f'{self.DIRECTORY}/{invoicedate}_for-PO-import.txt'):
            with open(f'{self.DIRECTORY}/{invoicedate}_for-PO-import.txt', 'a') as fp:
                for row in rows.values():
                    fp.write('%s,%s,%s,%s\n' % ( f'{row["sku"]:06}', row['suquantity'], row['suprice'], row['productdescription'] ))
        else:
            print('Error: PO File exists')

    def __checkforbadbarcodes(self, invoicedate):
        """
        Checks for bad barcodes in API and if they exist on this order print replacement barcode stickers.

        Label templates are preformatted and mathematically generated via the BarcodePrinter class in API.

        :param invoicedate: Date of invoice.
        """
        rows, status = self.__apiquery('GET', '/ar/findbadbarcodes', **{'invoicedate': invoicedate})
        print(len(rows))

        for row in rows.values():
            if not row['success']: 
                raise Exception()
            self.__apiquery('POST', '/labelmaker/print', **row)

    def processCSV(self, inputfile):
        """
        Reads the ARinvoice .xls file line by line and sends to API.

        This function will sanitize strings for undesirable characters as well as cleanup dollar amounts >999.99.
        This will also extract the invoice date from the file.

        :param inputfile: File to read from. Can be full or relative path.
        """
        #this is what an empty line looks like
        emptyline = ',,,,,,,,,,,,,'
        with open(inputfile) as f:
            append=False
            for line in f:
                #trim all whitespace to start`
                line = line.strip()

        #        if( not append ):
        #            print(line)

                if(line.find('Invoice Date:') > -1 ):
                    invoicedatefromldb=str(line.split(',')[len(line.split(','))-1].strip())
        #            invoicedate = datetime.datetime.strptime(invoicedatefromldb,'%Y-%m-%d %H:%M:%S.%f')
                    invoicedate = datetime.datetime.strptime(invoicedatefromldb,'%d-%b-%y').strftime('%Y-%m-%d')
                    print(invoicedate)
                if( line.strip() == emptyline.strip() and append ):
                    append=False
                if( append ):
                    imparsabledollaramount = self.DOLLARAMOUNT.search(line)
                    if imparsabledollaramount is not None:
                        print( f'!!! WARNING: comma in dollar amount !!! {imparsabledollaramount.group()}' )
                        line = line.replace(imparsabledollaramount.group(), imparsabledollaramount.group().replace(',',''))

                    line = re.sub(r'([^ \sa-zA-Z0-9.,]| {2,})','',line)
                    line = re.sub(r'( , |, | ,)', ',', line)
                    line = re.sub(r'(,,|, ,)', ',0.00,', line)

                    self.__addlineitem(line, invoicedate)
                if( line.find( 'SKU,Product Description') > -1):
                    append=True
                    emptyline = re.sub(r'[^,]','',line)
                    print(emptyline)
                    print(line.strip())

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