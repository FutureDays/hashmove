#!/usr/bin/env python
#hashmove.py


#######################################################################################################################
###REQUIRED LIBRARIES####
###simply_salesforce
#######################################################################################################################

import os
import sys
import shutil
import time
import re
import argparse
import getpass
import subprocess
import config
from simple_salesforce import Salesforce

def querySF(sf,barcode):
    result = sf.query("SELECT messageDigest__c FROM Preservation_Object__c WHERE Name = '" + barcode + "'")
    return result

def getChecksumFromRecord(sfData):
    checksum = sfData["records"][0].get("messageDigest__c")
    return checksum

def initLog(sourceList,destination,hashalg):
    '''
    initializes log file
    '''
    txtFile = open(destination + "/LoadingScript.log", "a+")
    txtFile.write("Load and Verify Script Started at: " + time.strftime("%Y-%m-%d_%H:%M:%S") + "\n")
    for f in sourceList:
        txtFile.write("From: " + f + "\n")
    txtFile.write("To: " + destination + "\n")
    txtFile.write("Hash algorithm: " + hashalg + "\n")
    txtFile.write("\n\n")
    txtFile.close()

def logNewLine(text,destination):
    txtFile = open(destination + "/LoadingScript.log", "a+")
    txtFile.write("\n" + time.strftime("%Y-%m-%d_%H:%M:%S") + ": " + text)

def logSameLine(text,destination):
    txtFile = open(destination + "/LoadingScript.log", "a+")
    txtFile.write(text)

def make_args():
    '''
    initialize arguments from the cli
    '''
    parser = argparse.ArgumentParser()
    parser.add_argument('-d','--delete',action='store_true',dest='c',default=False,help="delete source files after copying")
    parser.add_argument('-q','--quiet',action='store_true',dest='q',default=False,help="quiet mode, don't print anything to console")
    parser.add_argument('-a','--algorithm',action='store',dest='a',default='md5',choices=['md5','sha1','sha256','sha512'],help="the hashing algorithm to use")
    parser.add_argument('sourceAndDestObj',nargs='+',help="the file or directory to hash/ move/ copy/ verify/ delete")
    parser.add_argument('-xr','--bottomFolder',action='store_true',dest='xr',default=False,help="eXclude Root mode. This will move the folders and directories in the selecte input folders directly in the output, rather than the standard rsync style nesting")
    #parser.add_argument('destinationDir',nargs='?',default=os.getcwd(),help="the destination parent directory")
    return parser.parse_args()

def main():
    '''
    do the thing
    '''
    #init args from cli
    #args = make_args()
    ###INIT VARS###

    #Initialize log
    #initLog(sourceList,destinationDir,args.a)

    sf = Salesforce(
    username=config.username,
    password=config.password,
    security_token=config.security_token
    )

    #Query SalesForce and parse the data
    sfData = querySF(sf,"1007008")
    print(getChecksumFromRecord(sfData))


main()
