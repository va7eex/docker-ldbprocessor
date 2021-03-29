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
import urllib3
from datetime import date

from LineItem import LineItemAR as LineItem

class arinvoice:

    DIRECTORY='/var/ldbinvoice'
    PB_FILE='processedbarcodes.json'

    DOLLARAMOUNT = re.compile(r'\$\d+,\d{3}')

    def __init__(self, apiurl, apikey='', pricechangeignore=0.0):

        self.http = urllib3.PoolManager()
        self.apikey = apikey
        self.apiurl = apiurl
        self.pricechangeignore = float(pricechangeignore)

    def __apiquery(self, method='GET', url='', **kwargs):
        print(f'API query to: http://{self.apiurl}{url}')
        if self.apikey:
            r = self.http.request(f'{method}', f'http://{self.apiurl}{url}', fields={'apikey': self.apikey, **kwargs})
        else:
            r = self.http.request(f'{method}', f'http://{self.apiurl}{url}', fields={**kwargs})
        if r.status != 200:
            raise Exception(f'HTTP Response {r.status}')
        
        rows = json.loads(r.data.decode('utf-8'))
        return rows, r.status

    # write price report to file, later will make this a redis DB
    def __addtopricechangereport(self, invoicedate, **kwargs):
        with open(f'{self.DIRECTORY}/{invoicedate}_pricedeltareport.txt', 'a') as fp:
            if kwargs['oldprice'] is not None and kwargs['oldlastupdated'] is not None:
                #ignore price changes below a threshold
                if abs(kwargs['suprice']-kwargs['oldprice'])<self.pricechangeignore: return

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

    def __itmdb_checkchange(self, invoicedate):
        rows, status = self.__apiquery('GET', '/ar/pricechange', **{'invoicedate': invoicedate})

        print(len(rows))

        for row in rows.values():
            print(**row)
            self.__addtopricechangereport( invoicedate, **row )
            

    def __dopricechangelist(self, invoicedate):

        rows, status = self.__apiquery('GET', '/ar/getinvoice', **{'invoicedate': invoicedate})
        for row in rows.values():
            rows, status = self.__apiquery('POST', '/ar/pricechange', **{'sku': f"{row['sku']}", 'price': f"{row['suprice']}"})
        
        self.__itmdb_checkchange(invoicedate)

    def __addlineitem(self, line, invoicedate):

        li = LineItem(*line.split(','))
        
        self.__apiquery('POST', '/ar/addlineitem', **{'invoicedate': invoicedate, **li.getall(urlsafe=True)})


    def __printinvoicetofile(self, invoicedate):
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
        rows, status = self.__apiquery('GET', '/ar/findbadbarcodes', **{'invoicedate': invoicedate})
        print(len(rows))

        for row in rows.values():
            if not row['success']: 
                raise Exception()
            self.__apiquery('GET', '/labelmaker/print', **row)

    def processCSV(self, inputfile):
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