
#!/bin/python3

import os
import csv
from datetime import datetime

from flask import Flask
from flask import request, current_app, g
from flask import render_template
from flaskext.mysql import MySQL
from pymysql.cursors import DictCursor
from flask_redis import FlaskRedis

from schema import Schema, And, Use, Optional, SchemaError

from markupsafe import escape

from BarcodePrinter import LabelMaker
from LineItem import LineItemOS
from LineItem import LineItemAR

app = Flask(__name__)
app.config['MYSQL_DATABASE_HOST'] = os.getenv('MYSQL_IP')
app.config['MYSQL_DATABASE_PORT'] = int(os.getenv('MYSQL_PORT'))
app.config['MYSQL_DATABASE_USER'] = os.getenv('MYSQL_USER')
app.config['MYSQL_DATABASE_PASSWORD'] = os.getenv('MYSQL_PASSWORD')
app.config['MYSQL_DATABASE_DB'] = os.getenv('MYSQL_DB')
mysql = MySQL(cursorclass=DictCursor)
mysql.init_app(app)

app.config['REDIS_URL'] = f'redis://{os.getenv("REDIS_IP")}:{os.getenv("REDIS_PORT")}/0'
redis_client = FlaskRedis(app)

def __buildtables():

    connection = mysql.connect()
    cur = connection.cursor()

    cur.execute('''CREATE TABLE IF NOT EXISTS iteminfolist
        (sku MEDIUMINT(8) ZEROFILL UNIQUE,
        price FLOAT(11,4),
        oldprice FLOAT(11,4),
        badbarcode BOOLEAN NOT NULL DEFAULT 0,
        lastupdated TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        oldlastupdated TIMESTAMP,
        PRIMARY KEY (sku))''')

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
        invoicedate DATE,
        PRIMARY KEY (id))''')

    cur.execute('''CREATE TABLE IF NOT EXISTS orderlog (
        id INT NOT NULL AUTO_INCREMENT,
        sku MEDIUMINT(8) ZEROFILL,
        upc BIGINT UNSIGNED,
        productdescription VARCHAR(255),
        sellingunitsize VARCHAR(32),
        uom VARCHAR(20),
        qty SMALLINT UNSIGNED,
        orderdate DATE,
        ordernumber INT UNSIGNED,
        thirdparty BOOL,
        PRIMARY KEY (id))''')
    connection.commit()
    cur.close()


__buildtables()

@app.route('/')
def hello_world():
    return render_template('index.html')

@app.route('/ar')
def arpage():
    return render_template('ar.html')

@app.route('/bc')
def bcpage():
    return render_template('bc.html')

@app.route('/osr')
def osrpage():
    return render_template('osr.html')

@app.route('/labelmaker')
def labelmakerpage():
    return render_template('lp.html')

@app.before_request
def before_request():
    g.connection = mysql.connect()
    g.cur = g.connection.cursor()
    print()

@app.after_request
def after_request_func(response):
    return response

@app.teardown_request
def teardown_request(error=None):
    g.connection.commit()
    g.cur.close()


#
# Barcode Processor
#

def __sumRedisValues( list ):
    return  sum([int(i) for i in list if type(i)== int or i.isdigit()])


def __countBarcodes(scandate):
    barcodes = {}
    tally = {}
    total = 0
    for key in redis_client.scan_iter(str(scandate) + '*'):
        print(key)
        if not f'{scandate}_scanstats' in str(key):
#            barcodes[key] = self.__lookupUPC(self.__r.hgetall(key))
            tally[key] = __sumRedisValues(redis_client.hvals(key))
            total += tally[key]
    return barcodes, tally, total

@app.route('/bc/scan', methods=['POST'])
def __bc_scan():
    upc = escape(request.form.get('upc',0))
    scangroup = escape(request.form.get('scangroup',0))
    addremove = escape(request.form.get('addremove', 'add'))
    datestamp = escape(request.form.get('datestamp',datetime.today().strftime('%Y-%m-%d')))

    if addremove == 'remove':
        if not redis_client.hexists(f'{datestamp}_{scangroup}',upc):
            return
        if int(redis_client.hget(f'{datestamp}_{scangroup}',upc)) > 2:
            redis_client.hincrby(f'{datestamp}_{scangroup}', upc,-1)
        elif (redis_client.hget(f'{datestamp}_{scangroup}',upc)) <= 1:
            redis_client.hdel(f'{datestamp}_{scangroup}',upc)
    else:
        redis_client.hincrby(f'{datestamp}_{scangroup}', upc,1)

    payload = {}
    payload['barcodes'], payload['tally'], payload['total'] = __countBarcodes(datestamp)

    return payload

@app.route('/bc/getstatus', methods=['GET'])
def __bc_getstatus():

    datestamp = escape(request.form.get('datestamp',datetime.today().strftime('%Y-%m-%d')))

    payload = {}
    payload['barcodes'], payload['tally'], payload['total'] = __countBarcodes(datestamp)

    return payload


@app.route('/bc/linksku', methods=['POST'])
def __bc_linksku():
    pass
    

@app.route('/bc/del', methods=['DELETE'])
def __bc_del():
    pass

@app.route('/bc/new', methods=['POST'])
def __bc_new():
    pass

@app.route('/bc/get', methods=['GET', 'POST'])
def __bc_get():
    pass


#
#OrderSubmission
#

@app.route('/osr/getorder', methods=['GET'])
#@use_kwargs({'ordernumber': fields.Str(), 'thirdparty': fields.Bool()})
def __osr_getorder():

    ordernumber = escape(request.args.get('ordernumber',''))
    thirdparty = escape(request.args.get('thirdparty',''))
    orderdate = escape(request.args.get('orderdate',''))

    if orderdate:
        query = f'SELECT DISTINCT ordernumber FROM orderlog WHERE orderdate={orderdate}'
        g.cur.execute(query)
        rows = g.cur.fetchall()
        returnrows = {}
        returnrows['orderdate'] = orderdate
        returnrows['ordernumber'] = []
        for row in rows:
            returnrows['ordernumber'].append(row['ordernumber'])
        return returnrows

    query = f'SELECT id,sku,upc,productdescription,sellingunitsize,uom,qty,thirdparty FROM orderlog WHERE ordernumber={ordernumber}'
    if thirdparty:
        query += ' AND thirdparty={thirdparty}'
    g.cur.execute(query)
    rows = g.cur.fetchall()

    query = f'SELECT DISTINCT orderdate, ordernumber FROM orderlog WHERE ordernumber={ordernumber}'
    g.cur.execute(query)
    details = g.cur.fetchone()
    returnrows = {}
    returnrows['items'] = rows
    #for row in rows:
    #    returnrows['items'].append(rows.pop(0)
    return { **returnrows, **details}

@app.route('/osr/addlineitem', methods=['POST'])
def __osr_addlineitem():
    
    ordnum = escape(request.args.get('ordnum',''))
    orddate = escape(request.args.get('orddate',''))
    thirdparty = escape(request.args.get('thirdparty',''))
    restofrequest = request.form.to_dict(flat=True)
    li = LineItemOS(**restofrequest)

    query = f'INSERT INTO orderlog (ordernumber, orderdate, {li.getkeysconcat()}, thirdparty ) VALUES ( {ordnum}, {orddate}, {li.getvaluesconcat()}, {thirdparty} )'
    g.cur.execute(query)

    return li.getall()


#
# ARinvoice
#

@app.route('/ar/pricechange', methods=['GET','PUT'])
#@use_kwargs({'sku': fields.Str()})
def __ar_pricechange():

    if request.method == 'PUT':

        sku = escape(request.form.get('sku','0'))
        price = escape(request.form.get('price','0.0'))
        query = f'SELECT * FROM iteminfolist WHERE sku={sku}'
        g.cur.execute(query)
        results = g.cur.fetchone()
        newitem = False
        oldprice = -1.0
        oldlastupdated = '1979-01-01 01:01:01'
        #print(len(results), results)
        if not results:
            newitem = True
        else:
            oldprice = results['price']
            oldlastupdated = results['lastupdated']

        if float(results['price']) == float(price):
            return {'newitem': False, **results }

        query = f'INSERT INTO iteminfolist (sku, price) VALUES ({sku},{price}) ON DUPLICATE KEY UPDATE price={price}, oldprice={oldprice}, oldlastupdated=\'{oldlastupdated}\''
        g.cur.execute(query)

        # return {'newitem': newitem, 'sku': sku, 'price': price}

        query = f'SELECT * FROM iteminfolist WHERE sku={sku}'
        g.cur.execute(query)
        results = g.cur.fetchone()
        #print(len(results), results)

        return {'newitem': newitem, **results }

    invoicedate = escape(request.args.get('invoicedate',''))

    #https://stackoverflow.com/questions/11357844/cross-referencing-tables-in-a-mysql-query
    query = f'SELECT invoicelog.sku, invoicelog.suprice, iteminfolist.price, iteminfolist.oldprice, iteminfolist.lastupdated, iteminfolist.oldlastupdated FROM invoicelog, iteminfolist WHERE invoicelog.sku=iteminfolist.sku AND invoicelog.invoicedate=\'{invoicedate}\''
    #print(query)
    
    g.cur.execute(query)

    rows = g.cur.fetchall()

    returnrows = {}
    for row in range(len(rows)):
        returnrows[row] = rows.pop(0)
    return returnrows


@app.route('/ar/getitem',methods=['GET'])
#@use_kwargs({'sku': fields.Int(), 'all': fields.Bool()})
def __ar_getitem():
    
    sku = escape(request.args.get('sku',''))
    allitems = escape(request.args.get('all','false'))
    startdate = escape(request.args.get('startdate',''))
    enddate = escape(request.args.get('enddate',''))

    query = f'SELECT * FROM invoicelog WHERE sku={sku}'
    if startdate:
        query += f' AND invoicedate >= \'{startdate}\''
    if enddate:
        query += f' AND invoicedate <= \'{enddate}\''
    query += ' ORDER BY invoicedate DESC'
    if not allitems.lower() == 'true' or not (startdate or enddate):
        query += ' LIMIT 1'
    print(query)

    g.cur.execute(query)
    rows = g.cur.fetchall()

    returnrows = {}
    for row in rows:
        returnrows[row['id']] = rows.pop(0)
    return returnrows


@app.route('/ar/addlineitem', methods=['POST'])
#@use_kwargs({'invoicedate': fields.Str(), 'rawdata': fields.Bool(), 'data': fields.Str()})
def __ar_addlineitem():

    invoicedate = escape(request.form.get('invoicedate',''))
    restofrequest = request.form.to_dict(flat=True)
    li = LineItemAR(**restofrequest)

    query = f"INSERT INTO invoicelog ({li.getkeysconcat()},invoicedate) VALUES ({li.getvaluesconcat()},\'{invoicedate}\')"
    g.cur.execute(query)
    return {'success': True}

@app.route('/ar/getinvoice', methods=['GET'])
#@use_kwargs({'invoicedate': fields.Str()})
def __ar_getinvoice():

    invoicedate = escape(request.args.get('invoicedate',''))
    year = escape(request.args.get('year',''))
    month = escape(request.args.get('month',''))
    day = escape(request.args.get('day',''))

    if not invoicedate and year and month and day:
        invoicedate = f'{year}{month}{day}'

    query = f"SELECT DISTINCT sku, suprice, suquantity, productdescription, refnum FROM invoicelog WHERE invoicedate=\'{invoicedate}\'"
    g.cur.execute(query)

    invoice = {}
    rows = g.cur.fetchall()
    print('Total Rows: %s'%len(rows))

    for row in range(len(rows)):
        invoice[row] = rows.pop(0)

    return invoice

@app.route('/ar/findbadbarcodes', methods=['GET'])
def __ar_findbadbarcodes():

    invoicedate = escape(request.args.get('invoicedate',''))

    #https://stackoverflow.com/questions/11357844/cross-referencing-tables-in-a-mysql-query
    query = f'SELECT invoicelog.id, invoicelog.sku, invoicelog.productdescription FROM invoicelog, iteminfolist WHERE invoicelog.invoicedate=\'{invoicedate}\' AND invoicelog.sku=iteminfolist.sku AND iteminfolist.badbarcode=1'
    g.cur.execute(query)

    rows = g.cur.fetchall()
    data = {}
    for row in rows:
        data[row['id']] = rows.pop(0)
    return data

#
# Misc
#

@app.route('/misc/badbarcode', methods=['GET','POST'])
def __misc_badbarcode():

    sku = escape(request.args.get('sku',''))

    if request.method == 'POST':
        sku = escape(request.form.get('sku',''))
        badbarcode = escape(request.form.get('badbarcode',0))
        
        query = f'INSERT INTO iteminfolist (sku, badbarcode) VALUES ({sku},{badbarcode}) ON DUPLICATE KEY UPDATE badbarcode={badbarcode}'
        g.cur.execute(query)
        mysql.connect().commit()

    query = f'SELECT sku, badbarcode FROM iteminfolist WHERE sku={sku}'
    g.cur.execute(query)
    result = g.cur.fetchone()

    return result



#
# GUI
#

@app.route('/search', methods=['GET'])
def itemsearch():
    search = escape(request.args.get('search',''))

    query = f'SELECT sku, upc, qty, productdescription FROM orderlog WHERE sku={search} OR upc={search}'
    print(query)
    g.cur.execute(query)

    rows = g.cur.fetchall()
    print(rows)
    if len(rows) == 0:
        return 'None'

    return rows[len(rows)-1]
    #sku, upc, qty, productdescription = rows[len(rows)-1]

    #return {'sku': sku, 'upc':upc, 'productdescription': productdescription}

@app.route('/barcodeinput', methods=['POST'])
def barcodeinput():
    input = escape(request.args.get('bc'))

#
# Label Makers
#
labelmakers = []
def setupLabelMakers():
    #TODO: make better
   if os.getenv('LABEL_MAKER'):
       labelmakers.append(LabelMaker(ipaddress=os.getenv('LABEL_MAKER'),description='ZT410'))

    # with open('printers.csv', newline='') as csvfile:
    #     printerreader = csv.reader(csvfile, delimiter=',', quotechar='"')
    #     for row in printerreader:
    #         print(row)
    #         #ipaddress,port,description,width,height,metric,dpi,margins,columns,fontsize
    #         labelmakers.append(LabelMaker(
    #             ipaddress=row['ipaddress'], port=row['port'], metric=row['metric'], dpi=row['dpi'],
    #             width=row['width'], height=row['height'], margins=row['margins'],
    #             columns=row['columns'], fontsize=row['fontsize'], description=row['description']
            # ))

setupLabelMakers()

@app.route('/labelmaker/info', methods=['GET'])
def __label_info():
    printerlist = {}
    for lm in range(len(labelmakers)):
        printerlist[lm] = labelmakers[lm].getinfo()

    return printerlist


@app.route('/labelmaker/print', methods=['POST'])
#@use_kwargs({'printer': fields.Int(), 'name': fields.Str(), 'sku': fields.Str(), 'qty': fields.Int()})
def __label_print():

    printer = escape(request.form.get('printer',0))
    if not printer: printer = 0

    name = escape(request.form.get('name',''))
    productdescription = escape(request.args.get('productdescription',''))
    if not name and productdescription:
        name = productdescription

    sku = escape(request.form.get('sku',''))
    quantity = escape(request.form.get('qty','12'))
    if not quantity: quantity = '12'

    print(name, sku, quantity)
    labelmakers[int(printer)].printlabel(name,sku,int(quantity))

    return {'success': True, 'name': name, 'sku': sku, 'qty': quantity }

if __name__ == "__main__":
    app.run()