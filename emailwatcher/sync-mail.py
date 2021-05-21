import os
import sys
import argparse
import time
import schedule
import json

from mailattachmentsarchiver import mailattachmentsarchiver as maa_app

def generateIMAP(file,addr,port,user,pwd):
    """Generates IMAP credentials from sensitive environmental values.

    :param file: File to output.
    :param addr: Email server address, ex imap.gmail.com
    :param port: Email server port.
    :param user: Username used to authenticate.
    :param pwd: Password used to authenticate.
    """
    credentials = {}
    credentials['server']=addr
    credentials['user']=user
    credentials['password']=pwd

    print('connecting to server %s with username %s'%(addr,user))

    with open(file, 'w') as fp:
	    json.dump(credentials,fp,indent=2,separators=(',', ': '),sort_keys=True)

#this is for scheduling
def getmail(maa):
    """Gets the mail."""
    maa.get_mail()

def main(maa, hours: int = 1):
    """
    Retreives the mail every X hours.
    
    :param maa: Mailattachmentarchiver used for getting email attachments.
    :param hours: Interval between checking email in hours, default 1.
    """
    #if we don't define it, its an hour interval
    if hours is None or hours == '' or not hours.isdigit(): hours = 1

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
    main(maa, int(os.getenv('SYNCTIME')))
