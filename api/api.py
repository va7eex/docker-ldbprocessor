

import os

from flask import Flask
from flask import request
from flaskext.mysql import MySQL
from flask_redis import FlaskRedis

from markupsafe import escape

app = Flask(__name__)
app.config['MYSQL_DATABASE_HOST'] = os.getenv('MYSQL_HOST')
app.config['MYSQL_DATABASE_PORT'] = int(os.getenv('MYSQL_PORT'))
app.config['MYSQL_DATABASE_USER'] = os.getenv('MYSQL_USER')
app.config['MYSQL_DATABASE_PASSWORD'] = os.getenv('MYSQL_PASSWORD')
app.config['MYSQL_DATABASE_DB'] = os.getenv('MYSQL_DB')
mysql = MySQL()
mysql.init_app(app)

REDIS_URL = f'redis://{os.getenv("REDIS_IP")}:{os.getenv("REDIS_PORT")}/0'
redis_client = FlaskRedis(app)

def __buildtables():

    cur = mysql.get_db().cursor()

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

@app.route('/')
def hello_world():
    return 'Hello, World!'

#
#OrderSubmission
#

@app.route('/osr/getorder', methods=['GET','POST'])
def __osr_getorder():


    ordernumber = escape(request.args.get('ordernumber',''))

    cur = mysql.get_db().cursor()
	query = f'SELECT sku, upc, qty, productdescription FROM orderlog WHERE ordernumber={ordernumber}'
    try:
        cur.execute(query)

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

    return order

@app.route('/osr/addlineitem', methods=['POST'])
def __osr_addlineitem():
    
    cur = mysql.get_db().cursor()

    li = lineitem(*line.split(','))

    query = f'''INSERT INTO orderlog (
        ordernumber, orderdate, {li.getkeysconcat()}, thirdparty ) VALUES ( {ordnum}, {orddate}, {li.getvaluesconcat()}, {thirdparty} )
        '''
    try:
        cur.execute(query)


#
# ARinvoice
#

@app.route('/ar/pricechange', methods=['GET','POST'])
def __ar_pricechange():

    cur = mysql.get_db().cursor()
    if request.method == 'GET':

        date = escape(request.args.get('date',''))
        query = 'SELECT DISTINCT sku, suprice, productdescription FROM invoicelog WHERE invoicedate={date})'
        try:
            cur.execute(query)

        sku, suprice, proddescr = cur.fetchone()
        return {'sku': sku, 'suprice': suprice, 'prodescr': proddescr}

        return result

    elif request.method == 'POST':

        sku = escape(request.args.get('sku',''))
        query = f'SELECT price, lastupdated, badbarcode FROM iteminfolist WHERE sku={sku}'
        try:
            cur.execute(query)

        price, lastupdated, badbarcode = cur.fetchone()
        return {'price': price, 'lastupdated': lastupdated, 'badbarcode': badbarcode}

        return result

        return
    pass

@app.route('/ar/addlineitem', methods=['GET','POST'])
def __ar_addlineitem():

    cur = mysql.get_db().cursor()


    date = escape(request.args.get('date',''))

    li = lineitem(*line.split(','))
    query = f"INSERT INTO invoicelog ({li.getkeysconcat()},invoicedate) VALUES ({li.getvaluesconcat()},'{orderdate}')"
    pass

@app.route('/ar/getinvoice', methods=['GET','POST'])
def __ar_getinvoice():

    cur = mysql.get_db().cursor()

    date = escape(request.args.get('date',''))
    query = f"SELECT DISTINCT sku, suprice, suquantity, productdescription, refnum FROM invoicelog WHERE invoicedate='{date}'"
    try:
        cur.execute(query)

    invoice = {}
    rows = cursor.fetchall()
    print('Total Rows: %s'%len(rows))

    for row in rows:
        sku, unitprice, qty, productdescr, refnum = row
        invoice[date] = { 'sku': sku, 'unitprice': unitprice, 'qty': productdescr, 'refnm', refnum}

    return invoice

#
# GUI
#

@app.route('/search', methods=['GET'])
def itemsearch():
    if request.method == 'GET':
        
        cur = mysql.get_db().cursor()

        search = escape(request.args.get('search',''))

        query = f'SELECT sku, upc, qty, productdescription FROM orderlog WHERE sku={search} OR upc={search}'
        try:
            cur.execute(query)

        rows = cur.fetchall()
        if len(rows) == 0:
            return 'None'

        sku, upc, qty, productdescription = rows[len(rows)-1]

        return {'sku': sku, 'upc':upc, 'productdescription': productdescription}

@app.route('/barcodeinput', methods=['POST'])
def barcodeinput():
    if request.method == 'POST':
        cur = mysql.get_db().cursor()
        input = escape(request.args.get('bc'))
