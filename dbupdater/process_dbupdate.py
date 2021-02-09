#!/usr/bin/env python

__author__ = "David Rickett"
__credits__ = ["David Rickett"]
__license__ = "MIT"
__version__ = "1.0.1"
__maintainer__ = "David Rickett"
__email__ = "dap.rickett@gmail.com"
__status__ = "Production"


import toml
import os
import mysql

class dbupdater:

    debug = True

    def __init__(self, redis_ip, redis_port, mysql_user, mysql_pass, mysql_ip, mysql_port, mysql_db):
        self.__cnx = connection.MySQLConnection(user=mysql_user, password=mysql_pass,
                    host=mysql_ip,
                    port=mysql_port,
                    database=mysql_db)

    def __dbupdate(self, sku, key, value, table='invoicelog'):
        cursor = self.__cnx.cursor(buffered=True)
        query = f'UPDATE {table} SET {key}={value} WHERE sku={sku}'
        if debug:
            print(query)
        else:
            cursor.execute(query)
        self.__cnx.commit()
        cursor.close()

    def parse(self, filename):
        tomlstr = toml.load(filename)
        for k,v in tomlstr.items():
            if v[0] is 'badbarcode':
                self.__dbupdate(k, v[0], v[1], 'pricechangelist')


if __name__ == '__main__':
    dbu = dbupdater(
        os.getenv('REDIS_IP'), 
        os.getenv('REDIS_PORT'), 
        os.getenv('MYSQL_USER'), 
        os.getenv('MYSQL_PASSWORD'),
        os.getenv('MYSQL_IP'),
        os.getenv('MYSQL_PORT'),
        os.getenv('MYSQL_DATABASE'))
    dbu.parse(
        sys.argv[1])