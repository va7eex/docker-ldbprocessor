#"LDB Stocked Product Expected for Delivery"
#"Third Party Warehouse Stocked Product Currently Unavailable"
#end at "Subtotal:"

import json
import sys
import re
import time
import datetime
from datetime import date
from mysql.connector import (connection)

DIRECTORY='/var/ldbinvoice'
PB_FILE='processedbarcodes.json'

cnx = connection.MySQLConnection(user=MYSQL_USER, password=MYSQL_PASS,
				host=MYSQL_IP,
				port=MYSQL_PORT,
				database=MYSQL_DATABASE)

cur = cnx.cursor(buffered=True)
cur.execute('''CREATE TABLE IF NOT EXISTS orderlog (
		id INT NOT NULL AUTO_INCREMENT,
		sku MEDIUMINT(8) ZEROFILL,
		upc BIGINT UNSIGNED,
		productdescription VARCHAR(255),
		sellingunitsize VARCHAR(32),
		uom VARCHAR(20),
		qty SMALLINT UNSIGNED,
		orderdate INT(8) UNSIGNED,
		ordernumber INT UNSIGNED,
		thirdparty BOOL,
		PRIMARY KEY (id))''')
cnx.commit()
cur.close()

ordernum='NaN'
orderdate='NaN'
ordershipdate='NaN'

logtable=['orderlog']

keys='SKU,UPC,PRODUCT DESCRIPTION,SELLING UNITSIZE,UOM,QTY'

itemlist = []
itemlistnonstock = []
itemlist3rdparty = []
itemlist3rdpartynonstock = []
append=0

orderline = re.compile('Order *, *\d{4,},$')
orderdateline = re.compile('Order Booking Date *, *\d{8},$')
ordershipdateline = re.compile('Expected Ship Date *, *\d{8},$')

dollarvalue = re.compile('\$\d+,\d{3}')

itemlistline = re.compile('^\d{8}')

itemlineok = re.compile('\d+,\d+,[\w\d \.]+,(\d{1,3}\()?[\w\d \.]+\)?,(CS|BTL),\d+')

def getorderfromdatabase(ordernumber):
	cursor = cnx.cursor(buffered=True)

#	query = ("SELECT price, lastupdated FROM pricechangelist WHERE sku=%s"%(sku))
	query = ('''SELECT sku, upc, qty FROM orderlog WHERE ordernumber=%s''')%(ordernumber)
	cursor.execute(query)

	rows = cursor.fetchall()

	for row in rows:
		sku, upc, qty = row
#		print(('%s (%s) x %s')%(sku.zfill(6), upc, qty))
		print(('%s (%s) x %s')%(f'{sku:06}', upc, qty))

	cursor.close()

def insertintodatabase(line, table, ordnum, orddate, thirdparty):
	cursor = cnx.cursor(buffered=True)

	if( itemlineok.match(line) is None ):
		print( 'Line failed validation:' )
		print(string)
		return;

	linesplit = line.split(',')

	sku = linesplit[0].strip()
	upc = linesplit[1].strip()
	productdescription = linesplit[2].strip()
	sellingunitsize = linesplit[3].strip()
	uom = linesplit[4].strip()
	qty = linesplit[5].strip()

	query = ('''INSERT INTO orderlog (
		ordernumber, orderdate, sku, upc, productdescription, sellingunitsize, uom, qty, thirdparty ) VALUES ( %s, %s, %s, %s, %s, '%s', '%s', '%s', %s )
		''') % (
		ordnum, orddate, sku, upc, productdescription,
		sellingunitsize, uom, qty, thirdparty )

#	print(query)
	cursor.execute(query)
	cnx.commit()
	cursor.close()

file=sys.argv[1]
with open(file) as f:
	for line in f:

		#check if any dollar values exceed $999

#		p = re.compile('\$\d+,\d{3}')
#		m = p.match(line)
		if( dollarvalue.match(line) is not None ):
			print( dollarvalue.group() )
			line.replace(m.group(), m.group().replace(',',''))

		#strip all non-alphanumeric characters and whitespace greater than 2

		line = re.sub('([^ \sa-zA-Z0-9.,]| {2,})','',line).strip()

#		if( append == 0 ):
#			print( line )

		#regex find the order number, date, and expected ship date
		ols = orderline.search(line)
		if( ols is not None ):
			print(line)
			ordernum = ols.group(0).split(',')[1].strip()
			print(ordernum)
		odls = orderdateline.search(line)
		if( odls is not None ):
			print(line)
			orderdate = odls.group(0).split(',')[1].strip()
			print(orderdate)
		osdls = ordershipdateline.search(line)
		if( osdls is not None ):
			print(line)
			ordershipdate = osdls.group(0).split(',')[1].strip()
			print(ordershipdate)

		#find and fill table

		if( line.find('LDB Stocked Product Expected for Delivery') > -1):
			append=1
		elif( line.find('LDB Stocked Product Currently Unavailable') > -1):
			append=2
		elif( line.find('Third Party Warehouse Stocked Product on Order') > -1):
			append=4
		elif( line.find('Third Party Warehouse Stocked Product Currently Unavailable') > -1):
			append=8

		if( append > 0 ):
			line = re.sub('([^ \sa-zA-Z0-9.,]| {2,})','',line)
			line = re.sub( '( , |, | ,)', ',', line)
			line = re.sub( '(,,|, ,)', ',0.00,', line )


		if( append == 1 ):
			if( itemlistline.match(line) is not None ):
				insertintodatabase(line,0,ordernum,orderdate,False)
#				itemlist.append(line)
#				print( line )
#		elif( append == 2 ):
#			if( itemlistline.match(line) is not None ):
#				insertintodatabase(line,0,ordernum,orderdate)
#				itemlistnonstock.append(line)
#				print( line )
		elif( append == 4 ):
			if( itemlistline.match(line) is not None ):
				insertintodatabase(line,0,ordernum,orderdate,True)
#				itemlist3rdparty.append(line)
#				print( line )
#		elif( append == 8 ):
#			if( itemlistline.match(line) is not None ):
#				insertintodatabase(line,0,ordernum,orderdate)
#				itemlist3rdpartynonstock.append(line)
#				print( line )

#for item in itemlist:
#	print( item )
#for item in itemlist2wk:
#	print( item )

#print( list )

#with open('/tmp/Order_' + list['OrderNumber']+'.json', 'w') as fp:
#	json.dump(list,fp,indent=4,separators=(',', ': '),sort_keys=True)

getorderfromdatabase(ordernum)
cnx.close()
