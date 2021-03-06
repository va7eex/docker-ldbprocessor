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

    def __init__(self, redis_ip, redis_port, mysql_user, mysql_pass, mysql_ip, mysql_port, mysql_db, labelmaker=''):

        self.orderdate='nodatefound'
        self.__cnx = None
        self.__mysql_setup(mysql_user,mysql_pass,mysql_db,mysql_ip,mysql_port)

        self.labelmaker = None
        if labelmaker:
            self.labelmaker = Label_Maker(ipaddress=labelmaker)
        
    def __mysql_setup(self, mysql_user, mysql_pass,mysql_db,mysql_ip,mysql_port=3306):
        self.__cnx = connection.MySQLConnection(user=mysql_user, password=mysql_pass,
                    host=mysql_ip,
                    port=mysql_port,
                    database=mysql_db)


        cur = self.__cnx.cursor(buffered=True)
        cur.execute('''CREATE TABLE IF NOT EXISTS pricechangelist
            (sku MEDIUMINT(8) ZEROFILL,
            price VARCHAR(20),
            badbarcode BOOLEAN NOT NULL DEFAULT 0,
            lastupdated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP)''')

    #['SKU', 'Product Description', 'Product Category', 'Size', 'Qty', 'UOM', 'Price per UOM', 'Extended Price',
    #'SU Quantity', 'SU Price', 'WPP Savings', 'Cont. Deposit', 'Original Order#']
        cur.execute('''CREATE TABLE IF NOT EXISTS invoicelog (
            id INT NOT NULL AUTO_INCREMENT,
            sku MEDIUMINT(8) ZEROFILL,
            productdescription VARCHAR(255),
            productcategory VARCHAR(255),
            size VARCHAR(20),
            qty SMALLINT UNSIGNED,
            uom VARCHAR(20),
            priceperuom FLOAT(11,4),
            extendedprice FLOAT(11,4),
            suquantity SMALLINT UNSIGNED,
            suprice FLOAT(11,4),
            wppsavings FLOAT(11,4),
            contdeposit FLOAT(11,4),
            refnum INT(10),
            invoicedate VARCHAR(20),
            PRIMARY KEY (id))''')
        cur.close()
        self.__cnx.commit()

    #itemlineok = re.compile('\d+,[\d\w \.]+,\w+,(\d{0,3}\()?[\w\d \.]+\)?,\d+,(BTL|CS),\d*,?\d{1,3}+\.\d{2},\d*,?\d{1,3}+\.\d{2},\d+,\d*,?\d{1,3}+\.\d{2},\d*,?\d{1,3}+\.\d{2},\d*,?\d{1,3}+\.\d{2},\d+')


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
        cursor = self.__cnx.cursor(buffered=True)
        badbarcode = False

        query = f'SELECT price, lastupdated, badbarcode FROM pricechangelist WHERE sku={sku}'

        cursor.execute(query)

        if( cursor.rowcount != 0 ):
            dbprice, dbdate, badbarcode = cursor.fetchone()
            if( float(dbprice.strip()) != float(price) ):
                dbprice = float(dbprice)
                self.__addtopricechangelist( orderdate, sku, price, databaseprice=dbprice, databasedate=dbdate )
                query = f'UPDATE pricechangelist SET price = {price} WHERE sku = {sku}'
                if bool(badbarcode) and self.labelmaker != None:
                    print('Bad Barcode Detected')
                    self.labelmaker.printlabel(name,sku)
                cursor.execute(query)
        else:
            query = f'INSERT INTO pricechangelist (sku, price) VALUES ({sku},{price})'
            cursor.execute(query)
            self.__addtopricechangelist( orderdate, sku, price )
        self.__cnx.commit()
        cursor.close()

        return bool(badbarcode)

    def __addlineitem(self, line, orderdate):
        cursor = self.__cnx.cursor(buffered=True)

        li = lineitem(*line.split(','))
        query = f"INSERT INTO invoicelog ({li.getkeysconcat()},invoicedate) VALUES ({li.getvaluesconcat()},'{orderdate}')"

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

        cursor = self.__cnx.cursor(buffered=True)
        cursor.execute(f"SELECT DISTINCT sku, suprice, suquantity, productdescription, refnum FROM invoicelog WHERE invoicedate='{date}'")

        rows = cursor.fetchall()

        print('Total Rows: %s'%len(rows))

        if not os.path.exists(f'{self.DIRECTORY}/{date}_for-PO-import.txt'):
            with open(f'{self.DIRECTORY}/{date}_for-PO-import.txt', 'a') as fp:
                for row in rows:
                    sku, unitprice, qty, productdescr, refnum = row
                    fp.write('%s,%s,%s,%s\n' % ( f'{sku:06}', int(qty), unitprice, productdescr ))

        cursor.close()


    def __printpricechangelist(self, date):
        cursor = self.__cnx.cursor(buffered=True)
        cursor.execute(("SELECT DISTINCT sku, suprice, productdescription FROM invoicelog WHERE invoicedate='%s'")%(date))

        rows = cursor.fetchall()

        for row in rows:
            sku, price, name = row
            badbarcode = self.__itmdb_pricechange( date, sku, price, name )
            if badbarcode and self.labelmaker:
                self.labelmaker.printlabel(name,sku)

        cursor.close()


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
                        print( f'!!! WARNING: comma in dollar amount !!! {imparsabledollaramount.group()}'' )
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