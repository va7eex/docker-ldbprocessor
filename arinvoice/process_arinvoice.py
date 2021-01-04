#!/usr/bin/env python

__author__ = "David Rickett"
__credits__ = ["David Rickett"]
__license__ = "GPL"
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

MYSQL_IP='127.0.0.1'
MYSQL_PORT=3306
MYSQL_USER=None
MYSQL_PASS=None
MYSQL_DB=None
REDIS_IP='127.0.0.1'
REDIS_PORT=6783

DIRECTORY='/var/ldbinvoice'
PB_FILE='processedbarcodes.json'

cnx = None

dollaramount = re.compile('\$\d+,\d{3}')

orderdate='nodatefound'

file=None
outfile=None
pricereport=None

#exists = os.path.isfile('ldbinvoice/processedbarcodes.json')
exists = True
if not exists:
	print( 'Error: Could not find processed_barcodes.json, have you tried following instructions?' )
	exit()
#else:
#	with open('ldbinvoice/processed_barcodes.json', 'r') as fp:

def mysql_setup():
	global cnx
	cnx = connection.MySQLConnection(user=MYSQL_USER, password=MYSQL_PASS,
				host=MYSQL_IP,
				port=MYSQL_PORT,
				database=MYSQL_DB)


	cur = cnx.cursor(buffered=True)
	cur.execute('''CREATE TABLE IF NOT EXISTS pricechangelist
		(sku MEDIUMINT(8) ZEROFILL,
		price VARCHAR(20),
		lastupdated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP)''')

#['SKU', 'Product Description', 'Product Category', 'Size', 'Qty', 'UOM', 'Price per UOM', 'Extended Price',
#'SU Quantity', 'SU Price', 'WPP Savings', 'Cont. Deposit', 'Original Order#']
	cur.execute('''CREATE TABLE IF NOT EXISTS invoicelog (
		id INT NOT NULL AUTO_INCREMENT,
		sku MEDIUMINT(6) ZEROFILL,
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
                badbarcode BOOLEAN NOT NULL DEFAULT 0
		PRIMARY KEY (id))''')
	cur.close()
	cnx.commit()

#itemlineok = re.compile('\d+,[\d\w \.]+,\w+,(\d{0,3}\()?[\w\d \.]+\)?,\d+,(BTL|CS),\d*,?\d{1,3}+\.\d{2},\d*,?\d{1,3}+\.\d{2},\d+,\d*,?\d{1,3}+\.\d{2},\d*,?\d{1,3}+\.\d{2},\d*,?\d{1,3}+\.\d{2},\d+')


# write price report to file, later will make this a redis DB
def addtopricechangelist( sku, price, databaseprice=None, databasedate=None, newitem=False ):
	with open(pricereport, 'a') as fp:
		if not newitem:
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
def generatepricechangereport():
	return

def itmdb_pricechange( sku, price ):
	cursor = cnx.cursor(buffered=True)

	query = f'SELECT price, lastupdated FROM pricechangelist WHERE sku={sku}'

	cursor.execute(query)

	if( cursor.rowcount != 0 ):
		dbprice, dbdate = cursor.fetchone()
		if( float(dbprice.strip()) != float(price) ):
			dbprice = float(dbprice)
			addtopricechangelist( sku, price, databaseprice=dbprice, databasedate=dbdate )
			query = f'UPDATE pricechangelist SET price = {price} WHERE sku = {sku}'
			cursor.execute(query)
	else:
		query = f'INSERT INTO pricechangelist (sku, price) VALUES ({sku},{price})'
		cursor.execute(query)
		addtopricechangelist( sku, price, newitem=True )
	cnx.commit()
	cursor.close()

def addlineitem( line, orderdate ):
	cursor = cnx.cursor(buffered=True)

	li = lineitem(*line.split(','))
	query = f"INSERT INTO invoicelog ({li.getkeysconcat()},invoicedate) VALUES ({li.getvaluesconcat()},'{orderdate}')"

	try:
		cursor.execute(query)
	except Exception as err:
		print('')
		print('!!! ERROR !!!')
		print(err)
		print('')
		print(line)
		print('')
		print(query)
		with open(DIRECTORY + '/database-errors.txt', 'a') as fp:
			fp.write('Error at line:\n%s'%line)
			fp.write(f'\n{err}')
			if(len(li) > 13):
				fp.write('\n\t Cause: Errant comma somewhere in line')
			fp.write('\nNOTE: This line has been omitted from the final PO Import file due to errors\n')
	cnx.commit()
	cursor.close()



def checkforinvoicefile(overwritefile):
	print(f'Checking for invoice file at {overwritefile}')

	if os.path.exists(overwritefile):
		with open(overwritefile, 'w') as fp:
			fp.write('')
		print(f'{overwritefile} was found and cleared in preperation for new csv import.')


def printinvoicetofile( date ):
	print(f'Printing invoice {date} to file')

	cursor = cnx.cursor(buffered=True)
	cursor.execute(f"SELECT DISTINCT sku, suprice, suquantity, productdescription, refnum, badbarcode FROM invoicelog WHERE invoicedate='{date}'")

	rows = cursor.fetchall()

	print('Total Rows: %s'%len(rows))

	with open(outfile, 'a') as fp:
		for row in rows:
			sku, unitprice, qty, productdescr, refnum, badbarcode = row
			if badbarcode:
				pass
			fp.write('%s,%s,%s,%s\n' % ( f'{sku:06}', int(qty), unitprice, productdescr ))

	cursor.close()


def printpricechangelist( date ):
	cursor = cnx.cursor(buffered=True)
	cursor.execute(("SELECT DISTINCT sku, suprice FROM invoicelog WHERE invoicedate='%s'")%(date))

	rows = cursor.fetchall()

	for row in rows:
		sku, price = row
		itmdb_pricechange( sku, price )

	cursor.close()


def processCSV(inputfile):
	#this is what an empty line looks like
	emptyline = ',,,,,,,,,,,,,'
	with open(inputfile) as f:
		append=False
		for line in f:
			#trim all whitespace to start`
			line = line.strip()

	#		if( not append ):
	#			print(line)

			if(line.find('Invoice Date:') > -1 ):
				orderdatefromldb=str(line.split(',')[len(line.split(','))-1].strip())
	#			orderdate = datetime.datetime.strptime(orderdatefromldb,'%Y-%m-%d %H:%M:%S.%f')
				orderdate = datetime.datetime.strptime(orderdatefromldb,'%d-%b-%y').strftime('%Y-%m-%d')
				print(orderdate)
			if( line.strip() == emptyline.strip() and append ):
				append=False
			if( append ):
				imparsabledollaramount = dollaramount.search(line)
				if( imparsabledollaramount is not None ):
					print( '!!! WARNING: comma in dollar amount !!! %s'%imparsabledollaramount.group() )
					line = line.replace(imparsabledollaramount.group(), imparsabledollaramount.group().replace(',',''))


				line = re.sub('([^ \sa-zA-Z0-9.,]| {2,})','',line)
				line = re.sub( '( , |, | ,)', ',', line )
				line = re.sub( '(,,|, ,)', ',0.00,', line )

				addlineitem(line, orderdate)
			if( line.find( 'SKU,Product Description') > -1):
				append=True
				emptyline = re.sub('[^,]','',line)
				print(emptyline)
				print(line.strip())

	checkforinvoicefile( outfile )
	printinvoicetofile( orderdate )
	printpricechangelist( orderdate )

	cnx.close()

def importconfig(inputfile):
	return 0

def main(file_input, file_output, file_pricereport, **kwargs):

	global MYSQL_USER
	global MYSQL_PASS
	global MYSQL_IP
	global MYSQL_PORT
	global MYSQL_DB
	global REDIS_IP
	global REDIS_PORT

	global file
	global outfile
	global pricereport

	file=file_input
	outfile=file_output
	pricereport=file_pricereport

	#import a config file
	if 'configfile' in kwargs:
		importconfig(kwargs['configfile'])

	if 'MYSQL_USER' in kwargs:
		MYSQL_USER = kwargs['MYSQL_USER']
	if 'MYSQL_PASS' in kwargs:
		MYSQL_PASS = kwargs['MYSQL_PASS']
	if 'MYSQL_IP' in kwargs:
		MYSQL_IP = kwargs['MYSQL_IP']
	if 'MYSQL_PORT' in kwargs:
		MYSQL_PORT = int(kwargs['MYSQL_PORT'])
	if 'MYSQL_DB' in kwargs:
		MYSQL_DB = kwargs['MYSQL_DB']
	if 'REDIS_IP' in kwargs:
		REDIS_IP = kwargs['REDIS_IP']
	if 'REDIS_PORT' in kwargs:
		REDIS_PORT = int(kwargs['REDIS_PORT'])

	mysql_setup()
	processCSV(file)

if __name__=='__main__':
	main(sys.argv[1], sys.argv[2], sys.argv[3], **dict(arg.split('=') for arg in sys.argv[4:])) # kwargs
