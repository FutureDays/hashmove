#!/usr/bin/env python
#hashmove.py


#######################################################################################################################
###REQUIRED LIBRARIES####
###simply_salesforce
#######################################################################################################################

import hashlib
import os
import time
import re
import argparse
import config
from simple_salesforce import Salesforce

def makeFileList(sourceList,hashalg):
    '''
returns a list of file(s) to hashmove. list is a set of tuples with (filepath,hash). for now the hash is empty
    '''
    flist = []
    for s in sourceList:
        if os.path.isdir(s) is False: #if first argument is a file it's p easy
            sourceFile = os.path.join(dirs, x)
            sourceBasename = os.path.basename(s)
            if sourceBasename.endswith(hashalg):
                fileDict = {"Filepath": sourceFile,"Filename" : sourceBasename,"Barcode" : "","SFHash" : "","SidecarHash" : "", "Result": ""}
                flist.append(dict(fileDict))
            else:
                print("WARNING: Input file " + sourceBasename + " ignored because it's not a hash file")
        #if the start object is a directory things get tricky
        elif os.path.isdir(s) is True:
            if not s.endswith("/"):
                s = s + "/" #later, when we do some string subs, this keeps os.path.join() from breaking on a leading / I HATE HAVING TO DO THIS
            for dirs, subdirs, files in os.walk(s): #walk recursively through the dirtree
                for x in files: #ok, for all files rooted at start object
                    sourceFile = os.path.join(dirs, x) #grab the start file full path
                    sourceBasename = os.path.basename(sourceFile)
                    if sourceBasename.endswith(hashalg): #look only for sidecar checksum files
                        fileDict = {"Filepath": sourceFile,"Filename" : sourceBasename,"Barcode" : "","SFHash" : "","SidecarHash" : "","Result": ""}
                        flist.append(dict(fileDict))

        else:
            print("Critical Error. Could not determine if the input is a file or directory. Something is very wrong.")
            sys.exit()
    return flist

def processList(sf,dictList,hashlength):

    for dict in dictList:
        dict = getBarcode(dict)
        dict["SFHash"] = getChecksumFromRecord(querySF(sf,dict["Barcode"]))
        dict["SidecarHash"] = readHash(dict.get("Filepath"), hashlength) #get the checksum from the sidecar file
        if dict["SFHash"] == dict["SidecarHash"]:
            dict["Result"] = True
        else:
            dict["Result"] = False
    return dictList

def getBarcode(dict):
    barcode = dict.get("Filename")[4:11] #get the barcode from the filename
    for b in barcode:
        if not b.isdigit(): #this makes sure that the barcode is 7 numbers. if not it'll throw a failure
            print("ERROR: File Barcode Not Found for " + sourceBasename)
        else:
            dict["Barcode"] = barcode
    return dict


def readHash(hashFile, hashlength):
    with open(hashFile,'r') as f: #open it
        storedHash = re.search('\w{'+hashlength+'}',f.read()).group() #get the hash
    return storedHash

def querySF(sf,barcode):
    result = sf.query("SELECT messageDigest__c FROM Preservation_Object__c WHERE Name = '" + barcode + "'")
    return result

def getChecksumFromRecord(sfData):
    checksum = sfData["records"][0].get("messageDigest__c")
    return checksum

def processResults(dictList):
    count = 0
    success = 0
    fail = 0
    failList = []

    for dict in dictList:
        if dict["Result"]:
            success += 1
        else:
            failList.append(dict["Filename"])
            fail += 1
        count += 1
    print("\n")
    print("Number of Checksums Processed: " + str(count))
    print("Number of Successes: " + str(success))
    print("Number of Failures: " + str(fail))
    if fail > 0:
        print("\n")
        print("List of Failed Files:")
        for f in failList:
            print(f)
    print("\n")

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
    parser.add_argument('-a','--algorithm',action='store',dest='a',default='md5',choices=['md5','sha1','sha256','sha512'],help="the hashing algorithm to use")
    parser.add_argument('sourceObj',nargs='+',help="As many files are directories you would like processed. Only sidecar checksum files are processed.")
    return parser.parse_args()

def main():
    '''
    do the thing
    '''
    #init args from cli
    args = make_args()

    #init salesforce login#
    sf = Salesforce(username=config.username,password=config.password,security_token=config.security_token)

    #Initialize log
    #initLog(sourceList,destinationDir,args.a)

    #init variables
    dictList = []
    hashAlgorithm = hashlib.new(args.a) #creates a hashlib object that is the algorithm we're using
    hashlengths = {'md5':'32','sha1':'40','sha256':'64','sha512':'128'}
    hashlength = hashlengths[args.a] #set value for comparison later

    #Check that input conforms
    if len(args.sourceObj) < 1: #if less than two input arguments we have to exit
        print("CRITICAL ERROR: You must give this script at least one argument")
        sys.exit()

    #create list of dictionarie (which represent hash files) to be processed
    dictList = makeFileList(args.sourceObj,args.a)

    #process the list
    dictList = processList(sf,dictList,hashlength)

    #tally up the success and failures, print the failed files.
    processResults(dictList)

main()
