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
import requests
import logging
from datetime import date
#import pymysql

from LineItem import LineItemOS as LineItem

class OrderSubmissionReport:
    """For processing BCLDB Store 100 Order Submission Reports .xls reports.


    """

    DIRECTORY='/var/ldbinvoice'
    PB_FILE='processedbarcodes.json'

    LOGTABLE=['orderlog']

    KEYS='SKU,UPC,PRODUCT DESCRIPTION,SELLING UNITSIZE,UOM,QTY'

    ORDERLINE = re.compile('Order , ?\d{4,}$')
    ORDERDATELINE = re.compile('Order Booking Date *, *\d{2}[A-Z]{3}\d{2},*$')
    ORDERSHIPDATELINE = re.compile('Expected Ship Date *, *\d{2}[A-Z]{3}\d{2},*$')

    DOLLARAMOUNT = re.compile('\$\d+,\d{3}')

    ITEMLISTLINE = re.compile('^\d{8}')

    ITEMLINEOK = re.compile('\d+,\d+,[\w\d \.]+,(\d{1,3}\()?[\w\d \.]+\)?,(CS|BTL),\d+')

    def __init__(self, apiurl, apikey=''):
        """
        """
        logging.info('LDB OSR Processor started.')

        self.apiurl = apiurl
        self.apikey = apikey
        self.__s = requests.Session() 

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
        #logging.info(f'API query to: http://{self.apiurl}{url}')
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

        time.sleep(0.05) #we need to rate limit this or the server will 503 us.
        return r.json(), r.status_code

    def __converttimedatetonum(self, time):
        """Standardizes timestamp.

        :rtype: str
        :return: Returns a re-formatted date stamp.
        """

        # %d%b%y = 02DEC20

        return datetime.datetime.strptime(time.lower(), '%d%b%y').strftime('%Y-%m-%d')

    def __getorderfromdatabase(self, ordernumber):
        """
        Gets a specific order from API.

        :param ordernumber: The order number to retrieve.
        :rtype: dict
        :return: Returns a json array from the server.
        """

        if ordernumber == 'NaN':
            return

    #    query = ("SELECT price, lastupdated FROM pricechangelist WHERE sku=%s"%(sku))
        rows, status = self.__apiquery('GET', '/osr/getorder', **{'ordernumber': ordernumber})
        return rows

    def __insertintodatabase(self, line, table, ordernumber, orderdate, thirdparty):
        """
        Uploads each line to API.

        :param line: Line item, will be converted to a structured dict.
        :param table: Reserved.
        :param ordernumber: The order this item was submitted from.
        :param orderdate: The date this item was ordered.
        :param thirdparty: Whether this is coming from a third party warehouse.

        :rtype: None
        """
        if line == 'SKU,UPC,PRODUCT DESCRIPTION,SELLING UNITSIZE,UOM,QTY' or line == ',,,,,':
            return

        if( self.ITEMLINEOK.match(line) is None ):
            logging.warning( f'Line failed validation:\n\t{line}' )
            return

        li = LineItem(*line.split(','))

        rows, status= self.__apiquery('POST', '/osr/addlineitem',
            **{'orderdate': orderdate, 'ordernumber': ordernumber, 'thirdparty': thirdparty, **li.getall(urlsafe=True)}
            )

        logging.debug(status)

    def __processCSV(self, inputfile):
        """
        Processes CSV file line by line.

        This function will sanitize strings for unwanted characters and clean up dollar amounts >$999.99
        
        This function will extract various key values, such as Order Number, Order Date, and Expected Ship Date.
        Line items will also be tagged whether they are shipping via third party warehouse or direct.

        :param inputfile: File to process.
        """
        ordernum = 0
        orderdate = 0
        ordershipdate = 0
        append = 0
        with open(inputfile) as f:
            for line in f:

                #check if any dollar values exceed $999, if it does remove errant commas.
                imparsabledollaramount = self.DOLLARAMOUNT.search(line)
                if imparsabledollaramount is not None:
                    logging.warning( f'!!! WARNING: comma in dollar amount !!! {imparsabledollaramount.group()}' )
                    line = line.replace(imparsabledollaramount.group(), imparsabledollaramount.group().replace(',',''))

                #strip all non-alphanumeric characters and whitespace greater than 2

                line = re.sub('([^ \sa-zA-Z0-9.,]| {2,})','',line).strip()

                #regex find the order number, date, and expected ship date
                ols = self.ORDERLINE.search(line)
                if( ols is not None ):
                    logging.info(line)
                    ordernum = ols.group(0).split(',')[1].strip()
                    logging.info(ordernum)
                odls = self.ORDERDATELINE.search(line)
                if( odls is not None ):
                    logging.info(line)
                    orderdate = self.__converttimedatetonum(odls.group(0).split(',')[1].strip())
                    logging.info(orderdate)
                osdls = self.ORDERSHIPDATELINE.search(line)
                if( osdls is not None ):
                    logging.info(line)
                    ordershipdate = self.__converttimedatetonum(osdls.group(0).split(',')[1].strip())
                    logging.info(ordershipdate)

                # each of these headers indicates the start of a new table.

                if( line.find('LDB Stocked Product Expected for Delivery') > -1):
                    #we care about this one
                    append=1
                    logging.info('Append = 1')
                elif( line.find('LDB Stocked Product Currently Unavailable') > -1):
                    append=2
                    logging.info('Append = 2')
                elif( line.find('Third Party Warehouse Stocked Product on Order') > -1):
                    #we care about this one
                    append=4
                    logging.info('Append = 4')
                elif( line.find('Third Party Warehouse Stocked Product Currently Unavailable') > -1):
                    append=8
                    logging.info('Append = 8')

                if( append > 0 ):
                    #remove non-standard characters, whitespace between commas, and if multiple commas exist back to back replace with 0.
                    line = re.sub('([^ \sa-zA-Z0-9.,]| {2,})','',line)
                    line = re.sub('( , |, | ,)', ',', line)
                    line = re.sub('(,,|, ,)', ',0.00,', line )

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
        """
        Process incoming CSV file for API.

        :param inputfile: File to be processed.
        """
        order = {}
        order['ordernum'], order['orderdate'], order['ordershipdate'] = self.__processCSV(inputfile)
        with open(f"{self.DIRECTORY}/order-{order['ordernum']}.txt", 'w') as fp:
            json.dump({**order, **self.__getorderfromdatabase(order['ordernum'])},fp,indent=2,separators=(',', ': '),sort_keys=True)


if __name__=='__main__':
    osr = OrderSubmissionReport(
        os.getenv('APIURL'),
        os.getenv('APIKEY'))
    osr.processCSV(sys.argv[1])
