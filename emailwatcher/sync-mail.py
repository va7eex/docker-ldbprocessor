import os
import sys
import argparse
import time
import schedule
import json

from mailattachmentsarchiver import mailattachmentsarchiver as maa_app

def generateIMAP(file,addr,port,user,pwd):
    credentials = {}
    credentials['server']=addr
    credentials['user']=user
    credentials['password']=pwd

    print('connecting to server %s with username %s'%(addr,user))

    with open(file, 'w') as fp:
	    json.dump(credentials,fp,indent=2,separators=(',', ': '),sort_keys=True)

def main(maa, hours):
    #if we don't define it, its an hour interval
    if hours is None or hours == '' or not hours.isDigit(): hours = 1

    print('Script started, initial mail check commencing')
    maa.get_mail()

    #every day at noon, check for mail.
    schedule.every(int(hours)).hours.do(getmail,maa)
    print(f'Will check mail every {hours} hour(s) from now on.')
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == '__main__':
    #generate IMAP from docker .env
    generateIMAP('/tmp/imap.json',os.getenv('IMAP_ADDR'),os.getenv('IMAP_PORT'),os.getenv('IMAP_USER'),os.getenv('IMAP_PASS'))

    maa = maa_app('/tmp/imap.json','/usr/share/config.json')
    main(maa, os.getenv('SYNCTIME'))
