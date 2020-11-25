import os
import sys
import argparse
import time
import schedule
import json

from mailattachmentsarchiver import mailattachmentsarchiver as maa

def generateIMAP(file,addr,port,user,pwd):
    credentials = {}
    credentials['server']=addr
    credentials['user']=user
    credentials['password']=pwd

    with open(file, 'w') as fp:
	    json.dump(credentials,fp,indent=2,separators=(',', ': '),sort_keys=True)

def getmail(maa):
    print("Getting mail")
    maa.get_mail()

def main(maa):
    #every day at noon, check for mail.
    schedule.every().day.at("12:00").do(getmail,maa)
    
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == '__main__':
    #generate IMAP from docker .env
    generateIMAP('/tmp/imap.json',os.getenv('IMAP_ADDR'),os.getenv('IMAP_USER'),os.getenv('IMAP_PASS'))

    maa = maa('/tmp/imap.json','/usr/share/config.json')
    main(maa)
