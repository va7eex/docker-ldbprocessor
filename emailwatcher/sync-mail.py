import os
import sys
import argparse
import time
import schedule
import json

from mail-attachments-archiver import mail-attachments-archiver as maa

def generateIMAP(file,addr,port,user,pwd):
    credentials = {}
    credentials['server']=addr
    credentials['user']=user
    credentials['password']=pwd

    with open(file, 'w') as fp:
	    json.dump(credentials,fp,indent=2,separators=(',', ': '),sort_keys=True)

def main(maa):
    #every day at noon, check for mail.
    schedule.every().day.at("12:00").do(maa.get_mail())
    
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == '__main__':
    #generate IMAP from docker .env
    generateIMAP('/usr/share/imap.json',os.getenv('IMAP_ADDR'),os.getenv('IMAP_USER'),os.getenv('IMAP_PASS'))

    maa = maa('/usr/share/imap.json','/usr/share/config.json')
    main(maa)
