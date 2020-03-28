

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

from constants import MYSQL_USER
from constants import MYSQL_PASS
from constants import MYSQL_IP
from constants import MYSQL_PORT
from constants import MYSQL_DATABASE
from constants import REDIS_IP
from constants import REDIS_PORT


DIRECTORY='/var/ldbinvoice'
PB_FILE='processedbarcodes.json'

cnx = connection.MySQLConnection(user=MYSQL_USER, password=MYSQL_PASS,
                                host=MYSQL_IP,
                                port=MYSQL_PORT,
                                database=MYSQL_DATABASE)


orderdate='nodatefound'

file=sys.argv[1]
outfile=sys.argv[2]
pricereport=sys.argv[3]

#exists = os.path.isfile('ldbinvoice/processedbarcodes.json')
exists = True
if not exists:
	print( 'Error: Could not find processed_barcodes.json, have you tried following instructions?' )
	exit()
#else:
#	with open('ldbinvoice/processed_barcodes.json', 'r') as fp:

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
	priceperuom FLOAT(7,4),
	extendedprice FLOAT(7,4),
	suquantity SMALLINT UNSIGNED,
	suprice FLOAT(7,4),
	wppsavings FLOAT(7,4),
	contdeposit FLOAT(7,4),
	originalorder INT(10),
	invoicedate VARCHAR(20),
	PRIMARY KEY (id))''')
cur.close()
cnx.commit()

#itemlineok = re.compile('\d+,[\d\w \.]+,\w+,(\d{0,3}\()?[\w\d \.]+\)?,\d+,(BTL|CS),\d*,?\d{1,3}+\.\d{2},\d*,?\d{1,3}+\.\d{2},\d+,\d*,?\d{1,3}+\.\d{2},\d*,?\d{1,3}+\.\d{2},\d*,?\d{1,3}+\.\d{2},\d+')

def itmdb_pricechange( sku, price ):
	cursor = cnx.cursor(buffered=True)

	query = ("SELECT price, lastupdated FROM pricechangelist WHERE sku=%s"%(sku))

	cursor.execute(query)

	if( cursor.rowcount != 0 ):
		dbprice, dbdate = cursor.fetchone()
		if( float(dbprice.strip()) != float(price) ):
#			percent_diff = 0
#			percent_diff = (price - float(dbprice.strip())) / float(dbprice.strip())
			with open(pricereport, 'a') as fp:
				fp.write('%s: %s changed to %s (last updated %s)\n'
				% ( sku, dbprice, price, dbdate ))
			query = "UPDATE pricechangelist SET price = %s WHERE sku = %s"%(price,sku)
			cursor.execute(query)
	else:
		query = ("INSERT INTO pricechangelist (sku, price) VALUES (%s, %s)"%(sku,price))
		cursor.execute(query)
	cnx.commit()
	cursor.close()

def addlineitem( line, orderdate ):
	cursor = cnx.cursor(buffered=True)

	print(orderdate)
	print(line.strip())
#	m = itemlineok.match(line)
#	if( m is None ):
#		print( 'Line failed input validation:' )
#		print( m.group() )
#		return;

	linesplit = line.split(',')

	sku = linesplit[0].strip()		#int
	proddesc = linesplit[1].strip()		#str
	prodcat = linesplit[2].strip()		#str
	size = linesplit[3].strip()		#str
	qty = linesplit[4].strip()		#int
	uom = linesplit[5].strip()		#str
	priceperuom = linesplit[6].strip()	#float
	extprice = linesplit[7].strip()		#float
	suq = linesplit[8].strip()		#int unsigned
	suprice = linesplit[9].strip()		#float
	wpps = linesplit[10].strip()		#float
	contd = linesplit[11].strip()		#float
	ref = linesplit[12].strip()		#int

	query = f'''INSERT INTO invoicelog (
		sku,
		productdescription,
		productcategory,
		size,
		qty,
		uom,
		priceperuom,
		extendedprice,
		suquantity,
		suprice,
		wppsavings,
		contdeposit,
		originalorder,
		invoicedate
		) VALUES ({sku},'{proddesc}','{prodcat}','{size}',{qty},'{uom}',{priceperuom},{extprice},{suq},{suprice},{wpps},{contd},{ref},'{orderdate}')'''

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
			if(len(linesplit) > 13):
				fp.write('\n\t Cause: Errant comma somewhere in line')
	cnx.commit()
	cursor.close()



def printinvoicetofile( date ):
	cursor = cnx.cursor(buffered=True)
	cursor.execute(("SELECT DISTINCT sku, suprice, suquantity, productdescription, originalorder FROM invoicelog WHERE invoicedate='%s'")%(date))

	rows = cursor.fetchall()

	with open(outfile, 'a') as fp:
		for row in rows:
			sku, unitprice, qty, productdescr, originalorder = row
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

dollaramount = re.compile('\$\d+,\d{3}')

emptyline = ',,,,,,,,,,,,,'
with open(file) as f:
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
				print( m.group() )
				line.replace(m.group(), m.group().replace(',',''))

			line = re.sub('([^ \sa-zA-Z0-9.,]| {2,})','',line)
			line = re.sub( '( , |, | ,)', ',', line )
			line = re.sub( '(,,|, ,)', ',0.00,', line )

			addlineitem(line, orderdate)
		if( line.find( 'SKU,Product Description') > -1):
			append=True
			emptyline = re.sub('[^,]','',line)
			print(emptyline)
			print(line.strip())

printinvoicetofile( orderdate )
printpricechangelist( orderdate )

cnx.close()
