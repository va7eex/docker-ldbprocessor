
#!/bin/python3

import os

from flask import Flask
from flask import request
from flaskext.mysql import MySQL
from pymysql.cursors import DictCursor
from flask_redis import FlaskRedis

from markupsafe import escape

from BarcodePrinter import LabelMaker
from LineItem import LineItemOS
from LineItem import LineItemAR

app = Flask(__name__)
app.config['MYSQL_DATABASE_HOST'] = os.getenv('MYSQL_HOST')
app.config['MYSQL_DATABASE_PORT'] = int(os.getenv('MYSQL_PORT'))
app.config['MYSQL_DATABASE_USER'] = os.getenv('MYSQL_USER')
app.config['MYSQL_DATABASE_PASSWORD'] = os.getenv('MYSQL_PASSWORD')
app.config['MYSQL_DATABASE_DB'] = os.getenv('MYSQL_DB')
mysql = MySQL(cursorclass=DictCursor)
mysql.init_app(app)

REDIS_URL = f'redis://{os.getenv("REDIS_IP")}:{os.getenv("REDIS_PORT")}/0'
redis_client = FlaskRedis(app)

def __buildtables():

    cur = mysql.connect().cursor()

    cur.execute('''CREATE TABLE IF NOT EXISTS iteminfolist
        (sku MEDIUMINT(8) ZEROFILL,
        price FLOAT(11,4),
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
    cur.close()

__buildtables()

@app.route('/')
def hello_world():
    return 'Hello, World!'

#
# Barcode Processor
#

@app.route('/bc/add', methods=['POST'])
def __bc_add():
    pass

@app.route('/bc/del', methods=['POST'])
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

@app.route('/osr/getorder', methods=['GET','POST'])
@use_kwargs({'ordernumber': fields.Str()})
>>>>>>> e0720cfd7d517d4e64d3faf5ac0045413b63e492
def __osr_getorder():

    ordernumber = escape(request.args.get('ordernumber',''))

    cur = mysql.connect().cursor()
    query = f'SELECT sku, upc, qty, productdescription FROM orderlog WHERE ordernumber={ordernumber}'
    try:
        cur.execute(query)
    except:
        pass

    rows = cur.fetchall()
    order = {}
    order[ordernumber] = {}
    for row in rows:
    #    sku, upc, qty, productdescription = row
        order[ordernumber][f'{sku:06}'] = row
        #order[ordernumber][f'{sku:06}']['sku'] = f'{sku:06}'
        #order[ordernumber][f'{sku:06}']['upc'] = upc
        #order[ordernumber][f'{sku:06}']['qty'] = qty
        #order[ordernumber][f'{sku:06}']['productdescription'] = productdescription

    return order

@app.route('/osr/addlineitem', methods=['POST'])
def __osr_addlineitem():
    
    cur = mysql.connect().cursor()
    pass
    li = LineItemOS(*line.split(','))

    #query = f'''INSERT INTO orderlog (
    #    ordernumber, orderdate, {li.getkeysconcat()}, thirdparty ) VALUES ( {ordnum}, {orddate}, {li.getvaluesconcat()}, {thirdparty} )
    #    '''
    #try:
    #    cur.execute(query)


#
# ARinvoice
#

@app.route('/ar/pricechange', methods=['GET','POST'])
@use_kwargs({'sku': fields.Str()})
def __ar_pricechange():

    cur = mysql.connect().cursor()
    if request.method == 'POST':

        date = escape(request.args.get('date',''))
        query = 'SELECT DISTINCT sku, suprice, productdescription FROM invoicelog WHERE invoicedate={date})'
        try:
            cur.execute(query)
        except:
            pass

        return cur.fetchone()
        #sku, suprice, proddescr = cur.fetchone()
        #return {'sku': sku, 'suprice': suprice, 'prodescr': proddescr}

    elif request.method == 'GET':

        sku = escape(request.args.get('sku',''))
        query = f'SELECT price, lastupdated, badbarcode FROM iteminfolist WHERE sku={sku}'
        try:
            cur.execute(query)
        except:
            pass

        return cur.fetchone()
        #price, lastupdated, badbarcode = cur.fetchone()
        #return {'price': price, 'lastupdated': lastupdated, 'badbarcode': badbarcode}
    pass

@app.route('/ar/getitem',methods=['GET','POST'])
@use_kwargs({'sku': fields.Int(), 'all': fields.Bool()})
def __ar_getitem():
    
    cur = mysql.connect().cursor()
    sku = escape(request.args.get('sku',''))
    all = escape(request.args.get('all', False))

    query = f'GET * FROM invoicelog WHERE sku={sku} ORDERBY id DESC'
    try:
        cur.execute(query)
    except:
        pass

    if all:
        return cur.fetchall()
    else:
        return cur.fetchone()


@app.route('/ar/addlineitem', methods=['POST'])
@use_kwargs({'orderdate': fields.Str(), 'rawdata': fields.Bool(), 'data': fields.Str()})
def __ar_addlineitem():

    cur = mysql.connect().cursor()
    orderdate = escape(request.args.get('orderdate',''))
    rawdata = escape(request.args.get('raw', False))
    data = escape(request.args.get('data',''))

    li = None
    if rawdata:
        li = LineItemAR(linestring=data)
    else:
        li = LineItemAR(request.args)
        
    query = f"INSERT INTO invoicelog ({li.getkeysconcat()},invoicedate) VALUES ({li.getvaluesconcat()},'{orderdate}')"
    return query

@app.route('/ar/getinvoice', methods=['GET','POST'])
@use_kwargs({'invoicedate': fields.Str()})
def __ar_getinvoice():

    cur = mysql.connect().cursor()

    invoicedate = escape(request.args.get('invoicedate',''))
    query = f"SELECT DISTINCT sku, suprice, suquantity, productdescription, refnum FROM invoicelog WHERE invoicedate='{invoicedate}'"
    try:
        cur.execute(query)
    except:
        pass

    invoice = {}
    rows = cur.fetchall()
    print('Total Rows: %s'%len(rows))

    for row in rows:
        sku, unitprice, qty, productdescr, refnum = row
        invoice[f'{refnum}{sku}'] = {'sku': sku, 'unitprice': unitprice, 'qty': productdescr, 'refnm': refnum}

    return invoice

#
# GUI
#

@app.route('/search', methods=['GET'])
def itemsearch():
    if request.method == 'GET':
        
        cur = mysql.connect().cursor()

        search = escape(request.args.get('search',''))

        query = f'SELECT sku, upc, qty, productdescription FROM orderlog WHERE sku={search} OR upc={search}'
        cur.execute(query)

        print()
        rows = cur.fetchall()
        if len(rows) == 0:
            return 'None'

        sku, upc, qty, productdescription = rows[len(rows)-1]

        return {'sku': sku, 'upc':upc, 'productdescription': productdescription}

@app.route('/barcodeinput', methods=['POST'])
def barcodeinput():
    if request.method == 'POST':
        cur = mysql.connect().cursor()
        input = escape(request.args.get('bc'))

#
# Label Makers
#

@app.route('/labelmaker/print', methods=['GET','POST'])
@use_kwargs({'name': fields.Str(), 'sku': fields.Str(), 'qty': fields.Int()})
def __label_print():

    labelmaker = None
    if os.getenv('LABELMAKER_IP'):
        labelmaker = Label_Maker(ipaddress=labelmaker)
    else:
        return 500

    name = escape(request.args.get('name',''))
    sku = escape(request.args.get('sku',''))
    quantity = Schema(int).validate(escape(request.args.get('sku',12)))

    labelmaker.printlabel(name,sku,quantity)
