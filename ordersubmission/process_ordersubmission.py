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
import time
import datetime
from datetime import date
#import pymysql
from mysql.connector import (connection)

from lineitem import lineitem

	DIRECTORY='/var/ldbinvoice'
	PB_FILE='processedbarcodes.json'

	logtable=['orderlog']

	keys='SKU,UPC,PRODUCT DESCRIPTION,SELLING UNITSIZE,UOM,QTY'

	itemlist = []
	itemlistnonstock = []
	itemlist3rdparty = []
	itemlist3rdpartynonstock = []

	orderline = re.compile('Order , ?\d{4,}$')
	orderdateline = re.compile('Order Booking Date *, *\d{2}[A-Z]{3}\d{2},*$')
	ordershipdateline = re.compile('Expected Ship Date *, *\d{2}[A-Z]{3}\d{2},*$')

	dollarvalue = re.compile('\$\d+,\d{3}')

	itemlistline = re.compile('^\d{8}')

	itemlineok = re.compile('\d+,\d+,[\w\d \.]+,(\d{1,3}\()?[\w\d \.]+\)?,(CS|BTL),\d+')

	def __converttimedatetonum(self, time):

		# %d%b%y = 02DEC20

		time = datetime.datetime.strptime(time.lower(), '%d%b%y').strftime('%Y%m%d')

		return time

	def __getorderfromdatabase(self, ordernumber):

		if ordernumber == 'NaN':
			return

		cursor = cnx.cursor(buffered=True)

	#	query = ("SELECT price, lastupdated FROM pricechangelist WHERE sku=%s"%(sku))
		query = f'SELECT sku, upc, qty, productdescription FROM orderlog WHERE ordernumber={ordernumber}'
		cursor.execute(query)

		rows = cursor.fetchall()
		order = {}
		order[ordernumber] = {}
		for row in rows:
			sku, upc, qty, productdescription = row
			order[ordernumber][f'{sku:06}'] = {}
			order[ordernumber][f'{sku:06}']['sku'] = f'{sku:06}'
			order[ordernumber][f'{sku:06}']['upc'] = upc
			order[ordernumber][f'{sku:06}']['qty'] = qty
			order[ordernumber][f'{sku:06}']['productdescription'] = productdescription
	#		print(('%s (%s) x %s')%(sku.zfill(6), upc, qty))
			print('%s, %s x %s'%(order[ordernumber][f'{sku:06}']['sku'],order[ordernumber][f'{sku:06}']['upc'],order[ordernumber][f'{sku:06}']['qty']))

		cursor.close()

		return order

	def __insertintodatabase(self, line, table, ordnum, orddate, thirdparty):
		if line == 'SKU,UPC,PRODUCT DESCRIPTION,SELLING UNITSIZE,UOM,QTY' or line == ',,,,,':
			return

		cursor = cnx.cursor(buffered=True)

		if( itemlineok.match(line) is None ):
			print( f'Line failed validation:\n\t{line}' )
			return

		li = lineitem(*line.split(','))

		query = f'''INSERT INTO orderlog (
			ordernumber, orderdate, {li.getkeysconcat()}, thirdparty ) VALUES ( {ordnum}, {orddate}, {li.getvaluesconcat()}, {thirdparty} )
			'''

		print(query)
		cursor.execute(query)
		cnx.commit()
		cursor.close()

	def __processCSV(self, inputfile):
		ordernum = 0
		orderdate = 0
		ordershipdate = 0
		append = 0
		with open(inputfile) as f:
			for line in f:

				#check if any dollar values exceed $999, if it does remove errant commas.
				if( dollarvalue.match(line) is not None ):
					print( dollarvalue.group() )
					line = line.replace(m.group(), m.group().replace(',',''))

				#strip all non-alphanumeric characters and whitespace greater than 2

				line = re.sub('([^ \sa-zA-Z0-9.,]| {2,})','',line).strip()

				#regex find the order number, date, and expected ship date
				ols = orderline.search(line)
				if( ols is not None ):
					print(line)
					ordernum = ols.group(0).split(',')[1].strip()
					print(ordernum)
				odls = orderdateline.search(line)
				if( odls is not None ):
					print(line)
					orderdate = converttimedatetonum(odls.group(0).split(',')[1].strip())
					print(orderdate)
				osdls = ordershipdateline.search(line)
				if( osdls is not None ):
					print(line)
					ordershipdate = converttimedatetonum(osdls.group(0).split(',')[1].strip())
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
					line = re.sub('([^ \sa-zA-Z0-9.,]| {2,})','',line)
					line = re.sub( '( , |, | ,)', ',', line)
					line = re.sub( '(,,|, ,)', ',0.00,', line )

					# subtotal denotes the end of a table.
					if 'Subtotal' in line:
						append = 0

					if( append == 1 ):
						if( itemlistline.match(line) is not None ):
							insertintodatabase(line,0,ordernum,orderdate,False)
					elif( append == 4 ):
						if( itemlistline.match(line) is not None ):
							insertintodatabase(line,0,ordernum,orderdate,True)

		return ordernum, orderdate, ordershipdate

	def processCSV(self, inputfile, outputfile):
		order = {}
		order['ordernum'], order['orderdate'], order['ordershipdate'] = processCSV(file)

		with open(f'{DIRECTORY}/order-{order['ordernum']}.txt'), 'w') as fp:
			json.dump({**order, **getorderfromdatabase(order['ordernum'])},fp,indent=2,separators=(',', ': '),sort_keys=True)

	def __mysql_setup(self, mysql_user,mysql_pass,mysql_ip,mysql_port,mysql_db):
		self.__cnx = connection.MySQLConnection(user=mysql_user, password=mysql_pass,
					host=mysql_ip,
					port=mysql_port,
					database=mysql_db)

		cur = self.__cnx.cursor(buffered=True)
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
		self.__cnx.commit()
		cur.close()
		self.__cnx.close()

	def __importconfig(self, file):
		return 0

	def __init__(redis_ip,redis_port,mysql_user,mysql_pass,mysql_ip,mysql_port,mysql_db):
		print('LDB OSR Processor started.')

		self.__mysql_setup(mysql_user,mysql_pass,mysql_ip,mysql_port,mysql_db)


if __name__=='__main__':
	osr = arinvoice(
        os.getenv('REDIS_IP'), 
        os.getenv('REDIS_PORT'), 
        os.getenv('MYSQL_USER'), 
        os.getenv('MYSQL_PASSWORD'),
        os.getenv('MYSQL_IP'),
        os.getenv('MYSQL_PORT'),
        os.getenv('MYSQL_DATABASE'))
    osr.processCSV(
        sys.argv[1])