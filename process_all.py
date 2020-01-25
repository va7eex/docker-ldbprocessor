import os
import sys
import json
import time
import datetime
import re
from datetime import date
from mysql.connector import (connection)

from constants import MYSQL_USER
from constants import MYSQL_PASS
from constants import MYSQL_IP
from constants import MYSQL_PORT
from constants import MYSQL_DATABASE

DIRECTORY='/var/ldbinvoice'
PB_FILE='processedbarcodes.json'

cnx = connection.MySQLConnection(user=MYSQL_USER, password=MYSQL_PASS,
                                host=MYSQL_IP,
                                port=MYSQL_PORT,
                                database=MYSQL_DATABASE)


exists = os.path.isfile(('%s/%s')%(DIRECTORY, PB_FILE)
if not exists:
        print( 'Error: Could not find processed_barcodes.json, have you tried following instructions?')
        exit()

def printinvoicetofile( date ):
        cursor = cnx.cursor(buffered=True)
        cursor.execute(("SELECT DISTINCT sku, suprice, suquantity, productdescription, originalorder FROM invoicelog WHERE invoicedate='%s'")%(date))

        rows = cursor.fetchall()

        with open(outfile, 'a') as fp:
                for row in rows:
                        sku, unitprice, qty, productdescr, originalorder = row
                        fp.write('%s,%s,%s,%s\n' % ( f'{sku:06}', int(qty), unitprice, productdescr ))

        cursor.close()

