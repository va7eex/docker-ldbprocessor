
#!/bin/python3

__author__ = "David Rickett"
__credits__ = ["David Rickett"]
__license__ = "MIT"
__version__ = "1.0.1"
__maintainer__ = "David Rickett"
__email__ = "dap.rickett@gmail.com"
__status__ = "Production"

import os
import csv
import string
import random
import json
import time
import logging
from datetime import datetime

from flask import Flask
from flask import request, current_app, g
from flask import render_template
from flask import session, redirect, url_for
from flask import jsonify
from flaskext.mysql import MySQL
from pymysql.cursors import DictCursor
from flask_redis import FlaskRedis

from flask_selfdoc import Autodoc

from schema import Schema, And, Use, Optional, SchemaError

from markupsafe import escape

from BarcodePrinter import LabelMaker
from Barcode import Barcode
from LineItem import LineItemOS
from LineItem import LineItemAR

app = Flask(__name__)
auto = Autodoc(app)
#testing purposes only PLEASE CHANGE IN PROD
#this is literally the example key
app.secret_key = bytes(os.getenv("FLASK_SECRET").encode(encoding='UTF-8',errors='namereplace'))

app.config['MYSQL_DATABASE_HOST'] = os.getenv('MYSQL_IP')
app.config['MYSQL_DATABASE_PORT'] = int(os.getenv('MYSQL_PORT'))
app.config['MYSQL_DATABASE_USER'] = os.getenv('MYSQL_USER')
app.config['MYSQL_DATABASE_PASSWORD'] = os.getenv('MYSQL_PASSWORD')
app.config['MYSQL_DATABASE_DB'] = os.getenv('MYSQL_DB')
mysql = MySQL(cursorclass=DictCursor)
mysql.init_app(app)

app.config['REDIS_URL'] = f'redis://{os.getenv("REDIS_IP")}:{os.getenv("REDIS_PORT")}/0'
redis_client = FlaskRedis(app, decode_responses=True)

logging.basicConfig(level=int(os.getenv('LOGLEVEL')))

def __buildtables():

    startconnecttime = time.time_ns()
    while not mysql:
        time.sleep(1)
        pass
    endconnecttime = time.time_ns()

    logging.info(f'SQL Database reached after {endconnecttime-startconnecttime} ns')

    connection = mysql.connect()
    cur = connection.cursor()

    cur.execute('''CREATE TABLE IF NOT EXISTS iteminfolist
        (sku MEDIUMINT(8) UNSIGNED ZEROFILL,
        price FLOAT(11,4),
        oldprice FLOAT(11,4),
        badbarcode BOOLEAN NOT NULL DEFAULT 0,
        lastupdated TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        oldlastupdated TIMESTAMP,
        PRIMARY KEY (sku))''')

    cur.execute('''CREATE TABLE IF NOT EXISTS skubarcodelookup
        (upc BIGINT UNSIGNED,
        sku MEDIUMINT(8) UNSIGNED ZEROFILL,
        timeadded TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        timemodified TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        PRIMARY KEY (upc))''')

    #['SKU', 'Product Description', 'Product Category', 'Size', 'Qty', 'UOM', 'Price per UOM', 'Extended Price',
    #'SU Quantity', 'SU Price', 'WPP Savings', 'Cont. Deposit', 'Original Order#']
    cur.execute('''CREATE TABLE IF NOT EXISTS invoicelog (
        id INT NOT NULL AUTO_INCREMENT,
        sku MEDIUMINT(8) UNSIGNED ZEROFILL,
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
        sku MEDIUMINT(8) UNSIGNED ZEROFILL,
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

@app.route('/documentation')
def documentation():
    return auto.html()

@app.route('/')
def page_index():
    return render_template('index.html')

@app.route('/ar')
def page_ar():
    return render_template('ar.html')

@app.route('/bc')
def page_bc():
    if not 'scanner_terminal' in session:
        return redirect(url_for('page_bc_register'))
    return render_template('receiving.html')

@app.route('/osr')
def osrpage():
    return render_template('osr.html')

@app.route('/inv')
def page_inv():
    if not 'scanner_terminal' in session:
        return redirect(url_for('page_bc_register'))
    return render_template('inventory.html')

@app.route('/labelmaker')
def page_labelmaker():
    return render_template('lp.html')

@app.before_request
def before_request():
    g.connection = mysql.connect()
    g.cur = g.connection.cursor()

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

@app.route('/bc/register', methods=['GET','POST'])
@auto.doc(expected_type='application/json')
def page_bc_register():
    """Register endpoint with a mostly-unique name.

    GET: Check if endpoint registered
    POST: Set endpoint name.

    
    """
    if request.method == 'GET':
        if 'check' in request.args:
            return {'success': bool('scanner_terminal' in session) }
        if not 'scanner_terminal' in session:
            return render_template('bcregister.html')
        else:
            return render_template('bcregister.html', scanner_terminal=escape(session["scanner_terminal"]))


    if request.method == 'POST':
        #register with random string if nothing else.
        session['scanner_terminal'] = escape(request.form.get('scanner_terminal',''.join(random.choices(string.ascii_uppercase + string.digits, k=8))).lower())
        if 'headless' in request.form:
            return {'success': True}
        return render_template('bcregister.html', scanner_terminal=escape(session["scanner_terminal"]))

def __sumRedisValues( list ):
    return  sum([int(i) for i in list if type(i)== int or i.isdigit()])

def __crossreference_UPCs(redisvalues):
    processedredisvalues = {}
    for key, qty in redisvalues.items():

        result = __itemsearch(key)
        if len(key) > 14 and key[:1] == '01':
            #if the barcode is over 14 digits it won't match in the system, if the first two characters are 01 they're not useful anyways.
            key = key[2:]
            result = __itemsearch(key)
        if result:
            key = f"{result[len(result)-1]['sku']},    {result[len(result)-1]['productdescription']}"
            processedredisvalues[key] = qty
        else:
            result = __itemsearch(key[2:-1])
            if result:
                key = f"{result[len(result)-1]['sku']}, !! {result[len(result)-1]['productdescription']}"
                processedredisvalues[key] = qty
            else:
                processedredisvalues[key] = qty
    return processedredisvalues

def __countBarcodes(scandate, crossref=False):
    barcodes = {}
    tally = {}
    total = 0
    for key in redis_client.scan_iter(match=f'{scandate}_ingest_*'):
        key = str(key)
        logging.info(key)
        if crossref:
            barcodes[key] = __crossreference_UPCs(redis_client.hgetall(key))
        else:
            barcodes[key] = redis_client.hgetall(key)
        tally[key] = __sumRedisValues(redis_client.hvals(key))
        total += tally[key]
        logging.info(total, tally[key])
    return barcodes, tally, total

@app.route('/bc/countbarcodes', methods=['GET'])
@auto.doc()
def bc_countbarcodes():
    if not 'scanner_terminal' in session:
        return {'success': False, 'reason': 'not registered'}, 401

    datestamp = escape(request.args.get('datestamp',datetime.today().strftime('%Y%m%d')))

    payload = {}
    payload['barcodes'], payload['tally'], payload['total'] = __countBarcodes(datestamp)

    return {'success': True, **payload}, 200

@app.route('/bc/lastscanned', methods=['GET'])
@auto.doc()
def bc_lastscan():
    if not 'scanner_terminal' in session:
        return {'success': False, 'reason': 'no session info'}, 401
    
    if not redis_client.exists(f'lastscanned_{session["scanner_terminal"]}'):
        return {'success': False, 'reason': 'nothing logged.'}, 204

    return {'success': True, 'last_scanned': redis_client.get(f'lastscanned_{session["scanner_terminal"]}') }

@app.route('/bc/scan', methods=['POST'])
@auto.doc(expected_type='application/json')
def page_bcscan():
    """Scan into master record for today."""
    if not 'scanner_terminal' in session:
        return { 'success': False, 'reason': 'not registered'}, 401

    upc, upctype    = Barcode.BarcodeType(escape(request.form.get('upc',0)))
    scangroup       = escape(request.form.get('scangroup',0))
    addremove       = escape(request.form.get('addremove', 'add'))
    datestamp       = escape(request.form.get('datestamp',datetime.today().strftime('%Y%m%d')))

    #TODO: https://supportcommunity.zebra.com/s/article/Determine-Barcode-Symbology-by-using-Symbol-or-AIM-Code-Identifiers?language=en_US
    # implement this

    logging.info(request.form)

    redishashkey = f'{datestamp}_ingest_{escape(session["scanner_terminal"])}_{scangroup.zfill(3)}'

    if 'remove' in addremove:
        if not redis_client.hexists(redishashkey,upc):
            return {'success': True, 'reason': 'nothing to do'}
        if int(redis_client.hget(redishashkey,upc)) > 2:
            redis_client.hincrby(redishashkey, upc,-1)
        elif (redis_client.hget(redishashkey,upc)) <= 1:
            redis_client.hdel(redishashkey,upc)
    else:
        redis_client.hincrby(redishashkey, upc,1)
        logging.info(redishashkey, upc)
        redis_client.expire(redishashkey, (60*60*24)*3) #expire this in 3 days to keep DB size small.

    redis_client.set(f'lastscanned_{session["scanner_terminal"]}', upc)

    payload = {}
    if not 'machine' in request.form:
        payload['barcodes'], payload['tally'], payload['total'] = __countBarcodes(datestamp)

    return {'success': True, 'upc': upc, **payload}

@app.route('/bc/getstatus', methods=['GET'])
@auto.doc(expected_type='application/json')
def __bc_getstatus():
    """Returns data related to barcode scans."""

    datestamp = escape(request.form.get('datestamp',datetime.today().strftime('%Y%m%d')))

    payload = {}
    payload['barcodes'], payload['_tally'], payload['__total'] = __countBarcodes(datestamp)

    return jsonify(**payload)

def __bc_deleteRedisDB( scandate):
        logging.info( f'Deleting databases for {scandate}:' )
        count = 0
        pipe = redis_client.pipeline()
        for key in redis_client.scan_iter(str(f'{scandate}_ingest_{escape(session["scanner_terminal"])}') + '*'):
            logging.info(f'\t{key}')
            pipe.delete(key)
            count += 1
        pipe.execute()
        return count

@app.route('/bc/deleteall', methods=['POST'])
@auto.doc()
def bc_deleteall():
    if not 'scanner_terminal' in session:
        return {'success': False, 'reason': 'nothing to do'}, 401
    
    count = __bc_deleteRedisDB(escape(request.form.get('scandate',datetime.today().strftime('%Y%m%d'))))

    return {'success': True, 'result': f'Deleted {count} tables.'}


@app.route('/bc/linksku', methods=['POST'])
@auto.doc()
def __bc_linksku():
    pass

@app.route('/bc/exportscanlog', methods=['POST'])
@auto.doc(expected_type='application/json')
def bc_exportlog():

    datestamp = escape(request.form.get('datestamp',datetime.today().strftime('%Y%m%d')))

    with open(f'/var/ldbinvoice/{datestamp}_receiving_scan_log.txt', 'w') as f:
        json.dump(__bc_getstatus(), f, indent=2, sort_keys=True)

    return {'success': True}

@app.route('/bc/del', methods=['DELETE'])
@auto.doc()
def __bc_del():
    pass

@app.route('/bc/new', methods=['POST'])
@auto.doc()
def __bc_new():
    pass

@app.route('/bc/get', methods=['GET', 'POST'])
@auto.doc()
def __bc_get():
    pass


#
#OrderSubmission
#

@app.route('/osr/vieworder')
def page_osr_vieworder():
    """Return everything."""
    query = f'SELECT DISTINCT orderdate FROM orderlog'
    g.cur.execute(query)
    rows = g.cur.fetchall()
    
    return render_template('vieworder.html', dates=rows)

@app.route('/osr/getorderdates')
@auto.doc(expected_type='application/json')
def __osr_georderdates():
    """Returns the date of all Order Submission Reports on record."""
    query = f'SELECT DISTINCT orderdate FROM orderlog'
    g.cur.execute(query)
    rows = g.cur.fetchall()

    returnrows = {}
    for row in range(len(rows)):
        returnrows[row] = rows.pop(0)
    return returnrows

@app.route('/osr/getordernumber')
@auto.doc(expected_type='application/json', args={
    'orderdate': 'Date in YYYY-MM-DD'
})
def __osr_getordernumber():
    """Returns the Order Number(s) for a given date.

    :param str orderdate: Date of order, YYYY-MM-DD.
    """
    orderdate = escape(request.args.get('orderdate',''))

    query = f'SELECT DISTINCT ordernumber FROM orderlog WHERE orderdate={orderdate}'
    g.cur.execute(query)
    rows = g.cur.fetchall()
    returnrows = {}
    returnrows['orderdate'] = orderdate
    returnrows['ordernumber'] = []
    for row in rows:
        returnrows['ordernumber'].append(row['ordernumber'])
    return returnrows

@app.route('/osr/getorder', methods=['GET'])
@auto.doc(expected_type='application/json', args={
    'ordernumber': 'Order number to retrieve',
    'thirdparty': 'Include thirdparty warehouse suppliers'
})
#@use_kwargs({'ordernumber': fields.Str(), 'thirdparty': fields.Bool()})
def __osr_getorder():
    """Returns the full order details for a given Order Submission Report

    :param int ordernumber: Order number of order to retrieve.
    :param bool thirdparty: Return items stocked at third-party warehouses.
    """
    ordernumber = escape(request.args.get('ordernumber',''))
    thirdparty = escape(request.args.get('thirdparty',''))
    query = f'SELECT id,sku,upc,productdescription,sellingunitsize,uom,qty,thirdparty FROM orderlog WHERE ordernumber={ordernumber}'
    if thirdparty:
        query += ' AND thirdparty=1'
    g.cur.execute(query)
    rows = g.cur.fetchall()

    query = f'SELECT DISTINCT orderdate, ordernumber FROM orderlog WHERE ordernumber={ordernumber}'
    g.cur.execute(query)
    details = g.cur.fetchone()
    returnrows = {}
    returnrows['items'] = rows
    logging.info(f'{returnrows} || {details}')
    #for row in rows:
    #    returnrows['items'].append(rows.pop(0)
    return { **returnrows, **details}

@app.route('/osr/addlineitem', methods=['POST'])
@auto.doc(expected_type='application/json', args={
    'ordnum': 'Order Number on Order Submission Report',
    'orddate': 'Order Date on Order Submission Report',
    'thirdparty': 'Whether item is in the \'Thirdparty Wholesalers\' table of Order Submission Report'
})
def __osr_addlineitem():
    """Add a line item from an Order Submission Report to the database.
    """
    ordernumber = escape(request.form.get('ordernumber','1'))
    orderdate = escape(request.form.get('orderdate','19990101'))
    thirdparty = escape(request.form.get('thirdparty',False))
    restofrequest = request.form.to_dict(flat=True)
    try:
        li = LineItemOS(**restofrequest)
    except Exception as err:
        logging.error(err)
        return {'success': False, 'reason': 'line item error'}

    query = f'INSERT INTO orderlog (ordernumber, orderdate, {li.getkeysconcat()}, thirdparty ) VALUES ( {ordernumber}, \'{orderdate}\', {li.getvaluesconcat()}, {thirdparty} )'
    g.cur.execute(query)

    return {'success': True, 'lineitem': li.getall()}


#
# ARinvoice
#

@app.route('/ar/pricechange', methods=['GET','POST'])
@auto.doc(expected_type='application/json', args={
    'invoicedate': 'Date of invoice in YYYY-MM-DD',
    'sku': 'SKU of item',
    'price': 'Price of item, float'
})
#@use_kwargs({'sku': fields.Str()})
def __ar_pricechange():
    """Perform a price comparison/change of an item.

    :param str invoicedate: Date of invoice, YYYY-MM-DD.
    :param int sku: SKU of item.
    :param float price: Price of item.
    """

    if request.method == 'POST':

        sku = escape(request.form.get('sku','0'))
        price = escape(request.form.get('price','0.0'))
        query = f'SELECT * FROM iteminfolist WHERE sku={sku}'
        g.cur.execute(query)
        results = g.cur.fetchone()
        newitem = False
        oldprice = -1.0
        oldlastupdated = '1979-01-01 01:01:01'
        #logging.info(len(results), results)
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
        #logging.info(len(results), results)

        return {'newitem': newitem, **results }

    invoicedate = escape(request.args.get('invoicedate',''))

    #https://stackoverflow.com/questions/11357844/cross-referencing-tables-in-a-mysql-query
    query = f'SELECT DISTINCT invoicelog.refnum, invoicelog.sku, invoicelog.suprice, iteminfolist.price, iteminfolist.oldprice, iteminfolist.lastupdated, iteminfolist.oldlastupdated FROM invoicelog, iteminfolist WHERE invoicelog.sku=iteminfolist.sku AND invoicelog.invoicedate=\'{invoicedate}\''
    #logging.info(query)
    
    g.cur.execute(query)

    rows = g.cur.fetchall()

    returnrows = {}
    for row in range(len(rows)):
        returnrows[row] = rows.pop(0)
        if 'sku' in returnrows[row]:
            query = f'SELECT id, upc FROM orderlog WHERE sku={returnrows[row]["sku"]} ORDER BY id DESC'
            g.cur.execute(query)
            result = g.cur.fetchone()
            if result is not None and 'upc' in result:
                # checking whether the barcode *could be* a GTIN-14 based on check digit
                if Barcode.Interleaved2of5(result['upc']):
                    upc = Barcode.CalculateUPC(result['upc'])
                    ean = Barcode.CalculateEAN(result['upc'])
                    if int(upc) != int(ean):
                        returnrows[row]['gtin12'] = upc
                        returnrows[row]['gtin13'] = ean
                    else:
                        returnrows[row]['gtin12'] = upc
    return returnrows


@app.route('/ar/getitem',methods=['GET'])
@auto.doc(expected_type='application/json', args={
    'sku': 'SKU',
    'allitems': 'Select all instances of this SKU, true/false, default false',
    'startdate': 'Select all instances of this SKU after a specific date, YYYY-MM-DD',
    'enddate': 'Select all instances of this SKU before a specific date, YYYY-MM-DD'
})
#@use_kwargs({'sku': fields.Int(), 'all': fields.Bool()})
def __ar_getitem():
    """Search for any/all occurances of a given SKU received in an AR invoice.

    If nothing but sku is specified, this will return the latest occurance of sku.

    :param int sku: SKU to look for.
    :param bool allitems: Return all items.
    :param str startdate: Return an array of items starting at YYYY-MM-DD.
    :param str enddate: Return an array of items ending at YYYY-MM-DD.
    """
    
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
    logging.info(query)

    g.cur.execute(query)
    rows = g.cur.fetchall()

    returnrows = {}
    for row in rows:
        returnrows[row['id']] = rows.pop(0)
    return returnrows


@app.route('/ar/addlineitem', methods=['POST'])
@auto.doc(expected_type='application/json', args={
    'invoicedate': 'Date in YYYY-MM-DD',
    '**kwargs': 'Please refer to the lineitem class'
})
#@use_kwargs({'invoicedate': fields.Str(), 'rawdata': fields.Bool(), 'data': fields.Str()})
def __ar_addlineitem():
    """Add a lineitem from an AR invoice.

    :param str invoicedate: Date AR invoice received. YYYY-MM-DD.
    :param **kwargs: See LineItemAR class for details.
    """

    invoicedate = escape(request.form.get('invoicedate',''))
    restofrequest = request.form.to_dict(flat=True)
    try:
        li = LineItemAR(**restofrequest)
    except Exception as err:
        logging.error(err)
        return {'success': False, 'reason': 'line item error'}

    query = f"INSERT INTO invoicelog ({li.getkeysconcat()},invoicedate) VALUES ({li.getvaluesconcat()},\'{invoicedate}\')"
    g.cur.execute(query)
    return {'success': True, 'lineitem': li.getall()}

@app.route('/ar/getinvoice', methods=['GET'])
@auto.doc(expected_type='application/json', getargs={
            'invoicedate': 'Date in YYYY-MM-DD',
            'year': 'Optional, only used if invoicedate is missing, format: YYYY',
            'month': 'Optional, only used if invoicedate is missing, format: MM',
            'day': 'Optional, only used if invoicedate is missing, format: DD'
            })
#@use_kwargs({'invoicedate': fields.Str()})
def __ar_getinvoice():
    """Returns full AR Invoice as processed in JSON format.

    :param str invoicedate: Date to query in YYYY-MM-DD.
    :param int year: Optional, only used if invoicedate is missing, format: YYYY.
    :param int month: Optional, only used if invoicedate is missing, format: MM.
    :param int day: Optional, only used if invoicedate is missing, format: DD.
    """

    invoicedate = escape(request.args.get('invoicedate',''))
    year = escape(request.args.get('year',''))
    month = escape(request.args.get('month',''))
    day = escape(request.args.get('day',''))

    if not invoicedate and year and month and day:
        invoicedate = f'{year:04}-{month:02}-{day:02}'

    query = f"SELECT DISTINCT sku, suprice, suquantity, productdescription, refnum FROM invoicelog WHERE invoicedate=\'{invoicedate}\'"
    g.cur.execute(query)

    invoice = {}
    rows = g.cur.fetchall()
    logging.info('Total Rows: %s'%len(rows))

    for row in range(len(rows)):
        invoice[row] = rows.pop(0)

    return invoice

@app.route('/ar/findbadbarcodes', methods=['GET'])
@auto.doc(expected_type='application/json', args={
            'invoicedate': 'Date in YYYY-MM-DD'
            })
def __ar_findbadbarcodes():
    """Returns SKUs marked as \'badbarcode\' based on date.
    
    :param date invoicedate: Date query in YYYY-MM-DD
    """

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

@app.route('/misc/itemmod', methods=['GET'])
@auto.doc()
def page_itemmod():
    """View a SKU's non-AR/OSR attributes.

    :param int sku: The SKU to view.
    """

    sku = escape(request.args.get('sku',0))
    data = {}
    if sku:
        query = f'SELECT sku, badbarcode FROM iteminfolist WHERE sku={sku}'
        g.cur.execute(query)
        rows = g.cur.fetchone()
        logging.info(rows)

        query = f'SELECT upc FROM skubarcodelookup WHERE sku={sku}'
        g.cur.execute(query)
        gtin12 = g.cur.fetchone()
        logging.info(gtin12)

        query = f'SELECT upc FROM orderlog WHERE sku={sku}'
        g.cur.execute(query)
        gtin14 = g.cur.fetchone()
        logging.info(gtin14)
        
        data = {'sku':0, 'productdescription': '', 'gtin14': '0', 'gtin12': '0', 'badbarcode': False}
        if rows:
            data.update(rows)
            if gtin14:
                data.update({'gtin14': gtin14.get('upc',0)})
                if not gtin12 and Barcode.Interleaved2of5(gtin14.get('upc',0)):
                    data.update({'gtin12': Barcode.CalculateUPC(gtin14.get('upc',0))})
            if gtin12:
                data.update({'gtin12': gtin12.get('upc',0)})
        logging.info(data)
    return render_template('itemmodify.html', **data)

@app.route('/misc/itemattr', methods=['POST'])
@auto.doc(expected_type='application/json',args={
            'sku': 'Barcode printed on label',
            'badbarcode': '0/1, default 0'
            })
def __misc_itemattr():
    """
    Sets item attributes of a SKU.

    This will return the barcode state of a SKU in a GET message, and will set the barcode state of a SKU in a POST message.

    :param int sku: The SKU to modify
    :param int badbarcode: 0/1. Set to 1 to indicate true.
    :param int gtin12: Barcode of item.
    
    """

    sku = int(escape(request.form.get('sku',0)))
    badbarcode = int(escape(request.form.get('badbarcode',0)))
    gtin12 = int(escape(request.form.get('gtin12',0)))
    if sku == 0:
        return {'success': False, 'reason': 'invalid sku.'}
        logging.warn(f'Invalid SKU.')
    logging.info(f'{sku}, badbarcode={bool(badbarcode)}, gtin12={gtin12}')
    
    query = f'INSERT INTO iteminfolist (sku, badbarcode) VALUES ({sku},{bool(badbarcode)}) ON DUPLICATE KEY UPDATE badbarcode={bool(badbarcode)}'
    logging.info(query)
    g.cur.execute(query)

    query = f'INSERT INTO skubarcodelookup (upc, sku) VALUES ( {gtin12}, {sku} ) ON DUPLICATE KEY UPDATE sku={sku}'
    logging.info(query)
    g.cur.execute(query)

    query = f'SELECT sku, badbarcode FROM iteminfolist WHERE sku={sku}'
    g.cur.execute(query)
    result = g.cur.fetchone()

    return result

@app.route('/misc/badbarcode', methods=['GET','POST'])
@auto.doc(expected_type='application/json',args={
            'sku': 'Barcode printed on label',
            'badbarcode': '0/1, default 0'
            })
def __misc_badbarcode():
    """DEPRECATED: setting badbarcode boolean. Use /misc/itemattr instead.
    
    Gets or Sets the barcode-okayness of a SKU.

    This will return the barcode state of a SKU in a GET message, and will set the barcode state of a SKU in a POST message.

    :param int sku: The SKU to view/modify
    :param int badbarcode: POST only. Set to 1 to indicate true.
    
    """

    sku = escape(request.args.get('sku',0))

    if request.method == 'POST':
        sku = escape(request.form.get('sku',0))
        badbarcode = int(escape(request.form.get('badbarcode',0)))
        logging.info(f'badbarcode={bool(badbarcode)}')
        
        query = f'INSERT INTO iteminfolist (sku, badbarcode) VALUES ({sku},{bool(badbarcode)}) ON DUPLICATE KEY UPDATE badbarcode={bool(badbarcode)}'
        logging.info(query)
        g.cur.execute(query)

    query = f'SELECT sku, badbarcode FROM iteminfolist WHERE sku={sku}'
    g.cur.execute(query)
    result = g.cur.fetchone()

    return result



#
# GUI
#

def __itemsearch(upc):
    upc, upctype = Barcode.BarcodeType(escape(request.args.get('upc','')))
    
    query = f'SELECT sku, upc, productdescription FROM orderlog WHERE sku={upc} OR upc REGEXP {upc}'
    logging.info(query)
    g.cur.execute(query)

    rows = g.cur.fetchall()
    return rows

@app.route('/search', methods=['GET'])
@auto.doc(expected_type='application/json')
def itemsearch():
    """Returns OSR data based on SKU or UPC

    If no item matches search parameters, this will return HTTP status 204
    
    :param str upc: Can be either SKU or UPC.
    """
    upc, upctype    = Barcode.BarcodeType(escape(request.form.get('upc',0)))

    if not upc.isdigit():
        return {'success': False}, 406

    rows = __itemsearch(upc)
    logging.info(rows)
    if len(rows) == 0:
        return {'success': False}, 204

    return rows[len(rows)-1], 200
    #sku, upc, qty, productdescription = rows[len(rows)-1]

    #return {'sku': sku, 'upc':upc, 'productdescription': productdescription}

@app.route('/barcodeinput', methods=['POST'])
@auto.doc(expected_type='application/json')
def barcodeinput():
    upc, upctype    = Barcode.BarcodeType(escape(request.form.get('upc',0)))

#
# Label Makers
#
labelmakers = []
def setupLabelMakers():
    """Generates label makers."""
    #TODO: make better
    if os.getenv('LABEL_MAKER'):
       labelmakers.append(LabelMaker(ipaddress=os.getenv('LABEL_MAKER'),description='ZT410',width=1.0, height=1.0,columns=2,location='Office'))
       labelmakers.append(LabelMaker(ipaddress='192.168.3.138',description='Test LP2824',width=2.0, height=1.0,columns=1, location='Storage'))

    # with open('printers.csv', newline='') as csvfile:
    #     printerreader = csv.reader(csvfile, delimiter=',', quotechar='"')
    #     for row in printerreader:
    #         logging.info(row)
    #         #ipaddress,port,description,width,height,metric,dpi,margins,columns,fontsize
    #         labelmakers.append(LabelMaker(
    #             ipaddress=row['ipaddress'], port=row['port'], metric=row['metric'], dpi=row['dpi'],
    #             width=row['width'], height=row['height'], margins=row['margins'],
    #             columns=row['columns'], fontsize=row['fontsize'], description=row['description']
            # ))

setupLabelMakers()

@app.route('/lp')
@auto.doc()
def lppage():
    """GUI page for accessing available label printers."""
    printers = []
    for p in range(len(labelmakers)):
        printers.append({'index': p, 'description': labelmakers[p].description, 'location': labelmakers[p].location})
    return render_template('labelmaker.html', printers=printers )


@app.route('/labelmaker/info', methods=['GET'])
@auto.doc(expected_type='application/json', args={None})
def __label_info():
    """Returns a list of available label makers by index."""
    printerlist = {}
    for lm in range(len(labelmakers)):
        printerlist[lm] = labelmakers[lm].getinfo()

    return printerlist


@app.route('/labelmaker/print', methods=['POST'])
@auto.doc(expected_type='application/json', args={
            'printer': 'Index of printer from /labelmaker/info',
            'sku': 'Barcode printed on label',
            'name': 'Plaintext printed on label',
            'productdescription': 'alt-name for \'name\'',
            'qty': 'Quantity of labels printed'
            })
#@use_kwargs({'printer': fields.Int(), 'name': fields.Str(), 'sku': fields.Str(), 'qty': fields.Int()})
def __label_print():
    """
    Performs a print function on a designated printer.

    :param int printer: The index of a printer given by /labelmaker/info
    :param str name: Plaintext description to be printed.
    :param str productdescription: Plaintext description to be printed.
    :param str sku: String value of the barcode to be printed.
    :param int qty: Quantity of labels to be printed. Default 12.

    Note: \'Name\' and \'productdescription\' are synonymous and exist for compatability only.
    """

    printer = min(int(escape(request.form.get('printer',0))),0)
    if not printer: printer = 0

    name = escape(request.form.get('name',''))
    productdescription = escape(request.form.get('productdescription',''))
    if not name and productdescription:
        name = productdescription

    sku = escape(request.form.get('sku',''))
    quantity = escape(request.form.get('qty','12'))
    if not quantity: quantity = '12'
    if not quantity.isdigit(): quantity = '12'
    if quantity: quantity = f'{abs(int(quantity))}'

    logging.info(name, sku, quantity)
    try:
        labelmakers[int(printer)].printReplacementLabel(name,sku,int(quantity))
    except ConnectionError as err:
        logging.error(err)

    return {'success': True, 'name': name, 'sku': sku, 'qty': quantity }

if __name__ == "__main__":
    app.run()


#
# Inventory
#

def __countAllBarcodes_inv():
    redis_client.delete('master_inventory')
    for key in redis_client.scan_iter(match=f'inventory_*'):
        barcodes = redis_client.hgetall(key)
        for barcode,quantity in barcodes.items():
            redis_client.hincrby('master_inventory', barcode, quantity)
    return redis_client.hgetall('master_inventory')

@app.route('/inv/scan', methods=['POST'])
@auto.doc(expected_type='application/json', args={
            'scanner_terminal': 'Terminal of user',
            'upc': 'Barcode scanned.',
            'quantity': 'Quantity of specific barcode.',
            'addremove': 'add/remove'
            })
def page_invscan():
    """Scan into master record for today."""

    if not 'scanner_terminal' in session:
        return { 'success': False, 'reason': 'not registered'}, 401

    upc, upctype    = Barcode.BarcodeType(escape(request.form.get('upc',0)))
    quantity = int(escape(request.form.get('quantity',1)))
    addremove = escape(request.form.get('addremove', 'add'))
    datestamp = escape(request.form.get('datestamp',datetime.today().strftime('%Y%m%d')))

    redishashkey = f'inventory_{escape(session["scanner_terminal"])}'

    if 'remove' in addremove:
        if not redis_client.hexists(redishashkey,upc):
            return {'success': True, 'reason': 'nothing to do'}
        if int(redis_client.hget(redishashkey,upc))-quantity >= 0:
            redis_client.hincrby(redishashkey, upc,-quantity)
        elif int(redis_client.hget(redishashkey,upc))-quantity < 0:
            redis_client.hset(redishashkey,upc,0)
    else:
        redis_client.hincrby(redishashkey, upc,quantity)
        logging.info(redishashkey, upc)
        redis_client.expire(redishashkey, (60*60*24)*3) #expire this in 3 days to keep DB size small.

    redis_client.set(f'lastscanned_{session["scanner_terminal"]}', upc)

    payload = {}
    if not 'machine' in request.form:
        payload = {'upc': upc, 'quantity': int(redis_client.hget(redishashkey,upc))}

    return {'success': True, **payload}

@app.route('/inv/linksku', methods=['POST'])
@auto.doc(expected_type='application/json', args={
            'upc': 'upc of item',
            'sku': 'SKU of item'
            })
def inv_linksku():
    """Deprecated. Moved to Item Attributes.

    Links single item barcodes to SKUs.
    """
    upc, upctype    = Barcode.BarcodeType(escape(request.form.get('upc',0)))
    sku = escape(request.form.get('sku',''))

    if not upc.isdigit() or not sku.isdigit():
        return {'success': False, 'reason': 'barcode/sku not a number'}

    query = f'INSERT INTO skubarcodelookup (upc, sku) VALUES ( {upc}, {sku} ) ON DUPLICATE KEY UPDATE sku={sku}'
    g.cur.execute(query)
    
    return {'success': True, 'reason': f'{upc} linked to {sku}', 'upc': upc, 'sku': sku}

@app.route('/inv/exportscanlog', methods=['POST'])
@auto.doc(expected_type='application/json', args={
            'scanner_terminal': 'Terminal of user',
            'allscanners': 'yes/no, clear all scanners or individual unit.'
            })
def inv_exportlog():
    """Exports a csv file formatted for Profitek's inventory task list.
    """

    date = datetime.today().strftime('%Y%m%d')
    scanner_terminal = escape(session["scanner_terminal"])
    allscanners = escape(request.form.get('allscanners','yes'))

    if 'yes' in allscanners.lower():
        #get absolutely everything
        invdict = __countAllBarcodes_inv()
    else:
        invdict = redis_client.hgetall(f'inventory_{scanner_terminal}')
    logging.debug(invdict)

    with open(f'/var/ldbinvoice/{date}_{scanner_terminal}_inventory_scan_log.txt', 'w') as f:
        for k,v in invdict.items():
            line = f"{k},{v}"
            logging.info(line)
            f.write(f'{line}\n')

    return {'success': True}

@app.route('/inv/clearall', methods=['POST'])
@auto.doc(expected_type='application/json', args={
            'scanner_terminal': 'Terminal of user',
            'allscanners': 'yes/no, clear all scanners or individual unit.'
            })
def inv_clearall():
    """Clears any logged inventory counters.
    """

    allscanners = escape(request.form.get('allscanners','yes'))

    redishashkey = f'inventory_{escape(session["scanner_terminal"])}'

    if 'yes' in allscanners.lower():
        for key in redis_client.scan_iter(match=f'inventory_*'):
            redis_client.delete(key)
    else:
        redis_client.delete(redishashkey)
    
    return {'success': True}