#!/usr/bin/env python

__author__ = "David Rickett"
__credits__ = ["David Rickett"]
__license__ = "MIT"
__version__ = "1.0.1"
__maintainer__ = "David Rickett"
__email__ = "dap.rickett@gmail.com"
__status__ = "Production"

#"LDB Stocked Product Expected for Delivery"
#"Third Party Warehouse Stocked Product Currently Unavailable"
#end at "Subtotal:"

import json
import sys
import re
import os
import time
import datetime
import urllib3
from datetime import date
#import pymysql

from LineItem import LineItemOS as LineItem

class OrderSubmissionReport:

    DIRECTORY='/var/ldbinvoice'
    PB_FILE='processedbarcodes.json'

    LOGTABLE=['orderlog']

    KEYS='SKU,UPC,PRODUCT DESCRIPTION,SELLING UNITSIZE,UOM,QTY'

    ORDERLINE = re.compile(r'Order , ?\d{4,}$')
    ORDERDATELINE = re.compile(r'Order Booking Date *, *\d{2}[A-Z]{3}\d{2},*$')
    ORDERSHIPDATELINE = re.compile(r'Expected Ship Date *, *\d{2}[A-Z]{3}\d{2},*$')

    DOLLARVALUE = re.compile(r'\$\d+,\d{3}')

    ITEMLISTLINE = re.compile(r'^\d{8}')

    ITEMLINEOK = re.compile(r'\d+,\d+,[\w\d \.]+,(\d{1,3}\()?[\w\d \.]+\)?,(CS|BTL),\d+')

    def __init__(self, apiurl):
        print('LDB OSR Processor started.')

        self.http = urllib3.PoolManager()
        self.apiurl = apiurl

    def __converttimedatetonum(self, time):

        # %d%b%y = 02DEC20

        return datetime.datetime.strptime(time.lower(), '%d%b%y').strftime('%Y%m%d')

    def __getorderfromdatabase(self, ordernumber):

        if ordernumber == 'NaN':
            return

    #    query = ("SELECT price, lastupdated FROM pricechangelist WHERE sku=%s"%(sku))
        r = self.http.request('GET', f'http://{self.apiurl}/osr/getorder', fields={'ordernumber': ordernumber})

        return json.dumps(r.data)

    def __insertintodatabase(self, line, table, ordernumber, orderdate, thirdparty):
        if line == 'SKU,UPC,PRODUCT DESCRIPTION,SELLING UNITSIZE,UOM,QTY' or line == ',,,,,':
            return

        if( self.ITEMLINEOK.match(line) is None ):
            print( f'Line failed validation:\n\t{line}' )
            return

        li = LineItem(*line.split(','))

        r = self.http.request('POST', f'http://{self.apiurl}/osr/addlineitem',
            fields={'orderdate': orderdate, 'ordernumber': ordernumber, 'thirdparty': thirdparty, **li.getall()}
            )

        print(r.status)

    def __processCSV(self, inputfile):
        ordernum = 0
        orderdate = 0
        ordershipdate = 0
        append = 0
        with open(inputfile) as f:
            for line in f:

                #check if any dollar values exceed $999, if it does remove errant commas.
                if( self.DOLLARVALUE.match(line) is not None ):
                    print( self.DOLLARVALUE.group() )
                    line = line.replace(m.group(), m.group().replace(',',''))

                #strip all non-alphanumeric characters and whitespace greater than 2

                line = re.sub(r'([^ \sa-zA-Z0-9.,]| {2,})','',line).strip()

                #regex find the order number, date, and expected ship date
                ols = self.ORDERLINE.search(line)
                if( ols is not None ):
                    print(line)
                    ordernum = ols.group(0).split(',')[1].strip()
                    print(ordernum)
                odls = self.ORDERDATELINE.search(line)
                if( odls is not None ):
                    print(line)
                    orderdate = self.__converttimedatetonum(odls.group(0).split(',')[1].strip())
                    print(orderdate)
                osdls = self.ORDERSHIPDATELINE.search(line)
                if( osdls is not None ):
                    print(line)
                    ordershipdate = self.__converttimedatetonum(osdls.group(0).split(',')[1].strip())
                    print(ordershipdate)

                # each of these headers indicates the start of a new table.

                if( line.find('LDB Stocked Product Expected for Delivery') > -1):
                    #we care about this one
                    append=1
                    print('Append = 1')
                elif( line.find('LDB Stocked Product Currently Unavailable') > -1):
                    append=2
                    print('Append = 2')
                elif( line.find('Third Party Warehouse Stocked Product on Order') > -1):
                    #we care about this one
                    append=4
                    print('Append = 4')
                elif( line.find('Third Party Warehouse Stocked Product Currently Unavailable') > -1):
                    append=8
                    print('Append = 8')

                if( append > 0 ):
                    #remove non-standard characters, whitespace between commas, and if multiple commas exist back to back replace with 0.
                    line = re.sub(r'([^ \sa-zA-Z0-9.,]| {2,})','',line)
                    line = re.sub(r'( , |, | ,)', ',', line)
                    line = re.sub(r'(,,|, ,)', ',0.00,', line )

                    # subtotal denotes the end of a table.
                    if 'Subtotal' in line:
                        append = 0

                    if( append == 1 ):
                        if( self.ITEMLISTLINE.match(line) is not None ):
                            self.__insertintodatabase(line,0,ordernum,orderdate,False)
                    elif( append == 4 ):
                        if( self.ITEMLISTLINE.match(line) is not None ):
                            self.__insertintodatabase(line,0,ordernum,orderdate,True)

        return ordernum, orderdate, ordershipdate

    def processCSV(self, inputfile):
        order = {}
        order['ordernum'], order['orderdate'], order['ordershipdate'] = self.__processCSV(inputfile)
        ordernum = order['ordernum']
        with open(f'{self.DIRECTORY}/order-{ordernum}.txt', 'w') as fp:
            json.dump({**order, **self.__getorderfromdatabase(order['ordernum'])},fp,indent=2,separators=(',', ': '),sort_keys=True)


if __name__=='__main__':
    osr = OrderSubmissionReport(
        os.getenv('APIURL'))
    osr.processCSV(sys.argv[1])
