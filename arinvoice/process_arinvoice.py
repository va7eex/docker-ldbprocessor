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
from datetime import date
#import mysqlclient
from mysql.connector import (connection)

from lineitem import lineitem
from barcode_printer import Label_Maker

class arinvoice:

    DIRECTORY='/var/ldbinvoice'
    PB_FILE='processedbarcodes.json'

    DOLLARAMOUNT = re.compile('\$\d+,\d{3}')

    def __init__(self, redis_ip, redis_port, mysql_user, mysql_pass, mysql_ip, mysql_port, mysql_db):

        self.orderdate='nodatefound'

        self.http = urllib3.PoolManager()
        self.apiurl = ''

    # write price report to file, later will make this a redis DB
    def __addtopricechangelist(self, orderdate, sku, price, databaseprice=None, databasedate=None):
        with open(f'{self.DIRECTORY}/{orderdate}_pricedeltareport.txt', 'a') as fp:
            if bool(databaseprice):
                #ignore price changes below a threshold
                if abs(price-databaseprice)<os.getenv('PRICECHANGEIGNORE'): return

                alert=''
                if( (price - databaseprice)/ databaseprice > 0.1 ):
                    alert += '[pc>10%] '

                if( price >= (databaseprice + 5) ):
                    alert += '[pc$5+] '
                elif( price >= (databaseprice + 3) ):
                    alert += '[pc$3+] '
                elif( price >= (databaseprice + 1) ):
                    alert += '[pc$1+] '

                fp.write(f'{alert}{sku:06}: {databaseprice} changed to {price} (last updated {databasedate})\n')
            else:
                fp.write(f'[NEW] {sku:06}: {price}\n')

    #does nothing yet
    def __generatepricechangereport(self):
        return

    def __itmdb_pricechange(self, orderdate, sku, price, name=''):
        r = self.http.request('GET', f'http://{self.apiurl}/ar/pricechange', fields={'invoicedate': date})
        rows = json.dumps(r.data)

        for row in rows.values()
            self.__addtopricechangelist( row['orderdate'], row['sku'], row['price'] )
            r = self.http.request('POST', f'http://{self.apiurl}/ar/pricechange',
                fields={'sku': row['sku'], 'price': row['suprice']})
            r.status
        self.__cnx.commit()
        cursor.close()

        return bool(badbarcode)


#TODO: fix this
    def __addlineitem(self, line, orderdate):
        cursor = self.__cnx.cursor(buffered=True)

        li = lineitem(*line.split(','))
        query = f"INSERT INTO invoicelog ({li.getkeysconcat()},invoicedate) VALUES ({li.getvaluesconcat()},'{orderdate}')"
        
        r = self.http.request('GET', f'http://{self.apiurl}/ar/getinvoice', fields={'invoicedate': date})
        
        print(r.status)
        rows = json.loads(r.data)
        try:
            cursor.execute(query)
        except Exception as err:
            print(f'\n!!! ERROR !!!\n{err}\n{line}\n{query}\n')
            with open(f'{self.DIRECTORY}/database-errors.txt', 'a') as fp:
                fp.write('Error at line:\n%s'%line)
                fp.write(f'\n{err}')
                if(len(li) > 13):
                    fp.write('\n\t Cause: Errant comma somewhere in line')
                fp.write('\nNOTE: This line has been omitted from the final PO Import file due to errors\n')
        self.__cnx.commit()
        cursor.close()


    def __printinvoicetofile(self, date):
        print(f'Printing invoice {date} to file')

        r = self.http.request('GET', f'http://{self.apiurl}/ar/getinvoice', fields={'invoicedate': date})
        print(r.status)
        rows = json.loads(r.data)

        print('Total Rows: %s'%len(rows))

        if not os.path.exists(f'{self.DIRECTORY}/{date}_for-PO-import.txt'):
            with open(f'{self.DIRECTORY}/{date}_for-PO-import.txt', 'a') as fp:
                for row in rows:
                    fp.write('%s,%s,%s,%s\n' % ( f'{row["sku"]:06}', row['qty'], row['unitprice'], row['productdescription'] ))



    def __printpricechangelist(self, date):
        r = self.http.request('GET', f'http://{self.apiurl}/ar/pricechange', fields={'orderdate': orderdate})
        print(r.status)
        rows = json.loads(r.data)

        for row in rows:
            self.__itmdb_pricechange( row['sku'], row['price'], row['name'] )


    def __checkforbadbarcodes(self, orderdate):
        r = self.http.request('GET', f'http://{self.apiurl}/ar/findbadbarcodes', fields={'orderdate': orderdate})
        print(r.status)
        data = json.loads(r.data)
        print(len(data))

        for row in data.values():
            if not row['success']: 
                raise Exception()
            r = self.http.request('GET', f'http://{self.apiurl}/labelmaker/print', fields=row)

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
                    orderdatefromldb=str(line.split(',')[len(line.split(','))-1].strip())
        #            orderdate = datetime.datetime.strptime(orderdatefromldb,'%Y-%m-%d %H:%M:%S.%f')
                    orderdate = datetime.datetime.strptime(orderdatefromldb,'%d-%b-%y').strftime('%Y-%m-%d')
                    print(orderdate)
                if( line.strip() == emptyline.strip() and append ):
                    append=False
                if( append ):
                    imparsabledollaramount = self.DOLLARAMOUNT.search(line)
                    if( imparsabledollaramount is not None ):
                        print( f'!!! WARNING: comma in dollar amount !!! {imparsabledollaramount.group()}' )
                        line = line.replace(imparsabledollaramount.group(), imparsabledollaramount.group().replace(',',''))

                    line = re.sub('([^ \sa-zA-Z0-9.,]| {2,})','',line)
                    line = re.sub( '( , |, | ,)', ',', line )
                    line = re.sub( '(,,|, ,)', ',0.00,', line )

                    self.__addlineitem(line, orderdate)
                if( line.find( 'SKU,Product Description') > -1):
                    append=True
                    emptyline = re.sub('[^,]','',line)
                    print(emptyline)
                    print(line.strip())

        self.__printinvoicetofile( orderdate )
        self.__printpricechangelist( orderdate )

        self.__cnx.close()

    def __importconfig(inputfile):
        return 0

if __name__=='__main__':
    ari = arinvoice(
        os.getenv('REDIS_IP'), 
        os.getenv('REDIS_PORT'), 
        os.getenv('MYSQL_USER'), 
        os.getenv('MYSQL_PASSWORD'),
        os.getenv('MYSQL_IP'),
        os.getenv('MYSQL_PORT'),
        os.getenv('MYSQL_DATABASE'),
        os.getenv('LABEL_MAKER'))
    ari.processCSV(
        sys.argv[1])