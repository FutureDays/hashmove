#!/usr/bin/env python
#hashmove.py
#better file movement
#takes arguments for source or dest, source can be file or dir, dest must be dir
#copies files, hashes pre and post copy, deletes if hashes match, deletes dir if empty
#you can also:
#verify against another directory or the given directory (-v)
#copy files, don't delete from source directory (-c)
#quiet mode (-q)
#eXclude Root mode (-xr)
#print logs to current directory (-l)
#

#######################################################################################################################

#######################################################################################################################


import hashlib
import os
import sys
import shutil
import time
import re
import argparse
import getpass
import subprocess

#generate list of destination files of pairs of start and end files
def makeFileList(sourceList,dest,hashalg,hashlengths,excludeRoot):
    '''
returns a list of file(s) to hashmove
    '''
    flist = []
    for s in sourceList:
        if os.path.isdir(s) is False: #if first argument is a file it's p easy
            destinationObj = os.path.join(dest, os.path.basename(s)) # this is the file that we wanted to move, in its destination
            flist.extend([(s, destinationObj)])
            flist.extend([((s + "." + hashalg),(destinationObj + "." + hashalg))])
        #if the start object is a directory things get tricky
        elif os.path.isdir(s) is True:
            if excludeRoot: #this part makes the -xr flag work
                rootDirName = ""
            else:
                rootDirName = os.path.basename(s)
            if not s.endswith("/"):
                s = s + "/" #later, when we do some string subs, this keeps os.path.join() from breaking on a leading / I HATE HAVING TO DO THIS
            for dirs, subdirs, files in os.walk(s): #walk recursively through the dirtree
                for x in files: #ok, for all files rooted at start object
                    b = os.path.join(dirs,x) #make the full path to the file
                    b = b.replace(s,'') #extract just path relative to startObj (the subdirtree that x is in)
                    destinationObj = os.path.join(dest,rootDirName,b) #recombine the subdirtree with given destination (and file.extension)
                    sourceFile = os.path.join(dirs, x) #grab the start file full path
                    sourceFilename, ext = os.path.splitext(sourceFile) #separate extension from filename
                    sourceBasename = os.path.basename(sourceFilename)
                    if (not sourceBasename.startswith('.')) and (not ext.replace(".","") in hashlengths): #check that the file isn't DS_store and that file found doesn't have the hash extension (no hashes of hashes here my friend)
                        flist.extend([(sourceFile,destinationObj)]) #add these items as a tuple to the list of files
                        flist.extend([((sourceFile + "." + hashalg),(destinationObj + "." + hashalg))])
        else:
            print("Critical Error. Could not determine if the input is a file or directory. Something is very wrong.")
            sys.exit()
    return flist


#generate checksums for both source and dest
def generateHash(inputFile, hashalg, blocksize=65536):
    '''
    using a buffer, hash the file
    '''
    with open(inputFile, 'rb') as f:
        hasher = hashlib.new(hashalg) #grab the hashing algorithm decalred by user
        buf = f.read(blocksize) # read the file into a buffer cause it's more efficient for big files
        while len(buf) > 0: # little loop to keep reading
            hasher.update(buf) # here's where the hash is actually generated
            buf = f.read(blocksize) # keep reading
    return hasher.hexdigest()

#write hash to a file
def writeHash(inputFile, hashalg, logDir, resultsList):
    logNewLine("Writing New Sidecar Hash For " + os.path.basename(inputFile) + "........",logDir)
    try:
        hash = generateHash(inputFile, hashalg)
        hashFile = inputFile + "." + hashalg
        txt = open(hashFile, "w") #old school
        txt.write(hash + " *" + os.path.basename(inputFile))
        txt.close()
        logSameLine("Complete!",logDir)
        resultsList[1] += 1
        return resultsList
    except:
        logSameLine("ERROR!",logDir)
        resultsList[4] += 1
        return resultsList

#gets the hash from a sidecar text file
def readHash(hashFile, hashlength):
    with open(hashFile,'r') as f: #open it
        storedHash = re.search('\w{'+hashlength+'}',f.read()).group() #get the hash
    return storedHash

#verify's a hash from the sidecar file
def verifyHash(sidecarFile, hashalg, hashlength, logDir, resultsList):
    logNewLine("Verifying Hash For " + os.path.basename(sidecarFile) + "........",logDir)
    try:
        writtenHash = readHash(sidecarFile, hashlength) #read the hash written in the sidecar
        generatedHash = generateHash(sidecarFile.replace("." + hashalg, ""), hashalg) #generate the hash of the associated file
        if writtenHash == generatedHash: #then verify the checksums
            pass
            logSameLine("Complete! Checksum Verified",logDir)
            resultsList[2] += 1
            return resultsList
        else:
            pass
            logSameLine("ERROR: Checksum Verification Failed!",logDir)
            resultsList[4] += 1
            return resultsList
    except:
        logSameLine("ERROR!",logDir)

def removeUpToDateFiles(flist, hashalg, hashlength):
    '''
    iterates through the input list, creates output list
    '''
    removeFilesList = []
    reloadFileList = []
    for sf,df in flist: #get each item of flist, which contains a source file (sf) and destination file (df)
        if os.path.exists(df): #if the destination file exists
            if (hashalg in df): #this portion checks to see if a sidecar exists in the destination without an associated file.
                if not os.path.exists(sf): #if the destination checksum exists but the source doesn't then reload the hash. if we don't do this it can crash in some cases
                    reloadFileList.extend([(sf,df)])
                if not os.path.exists(df.replace("." + hashalg, "")):
                    reloadFileList.extend([(sf,df)]) #if this happens we need to reload the sidecar file so that it verifies when the assocaited file is reloaded
            elif (compare_modtime(sf,df)) and (compare_filesize(sf,df)): #if source files are older than destination and same size, things are good
                removeFilesList.extend([(sf,df)])
                if (hashalg not in sf): #this removes the associated sidecar files
                    removeFilesList.extend(((sf + "." + hashalg),(df + "." + hashalg)))
            else: #if destination files are older than source files, need to resync
                pass #leave item in the list, so it's reloaded
    flist = [x for x in flist if x not in removeFilesList] #remove the files already there from the file list
    flist.extend(reloadFileList)
    return flist



#performs the copy from one location (src) to another (dest)
def copyFiles(src,dest,logDir,resultsList):
    '''
    copies src file to the dest location
    using the native copy utility for a given platform
    '''
    logNewLine("Copying file: " + os.path.basename(src) + "........",logDir)
    try:
        win=mac=False
        if sys.platform.startswith("darwin"):
            mac=True
        elif sys.platform.startswith("win"):
            win=True
        cmd=None
        _dest = os.path.dirname(os.path.normpath(dest))
        if not os.path.exists(_dest):
            os.makedirs(_dest)
        if mac:
            cmd=['cp',src,dest]
        elif win:
            srce = os.path.dirname(src)
            dest = os.path.dirname(dest)
            name,ext = os.path.split(src)
            cmd=['robocopy',srce,dest,ext]
            print(cmd)

        subprocess.call(cmd)
        logSameLine("Complete!",logDir)
        resultsList[0] += 1
        return resultsList
    except:
        logSameLine("ERROR!",logDir)
        resultsList[4] += 1
        return resultsList

#this steps through the file list, creates checksums when needed, moves files, and verifies
def processList(flist, hashalg, hashlength, logDir, resultsList):
    for sf,df in flist:
        if (hashalg not in sf):    #if not a hash file
            if os.path.exists(sf + "." + hashalg): #see if hash file exists
                if compare_modtime(sf, sf + "." + hashalg): #check if hash file is newer than actual file
                    resultsList = copyFiles(sf,df,logDir, resultsList) #if hash is newer, we're good to move the file
                else:
                    logNewLine("WARNING! The checksum file for " + os.path.basename(sf) + " is out of date. Creating a new sidecare checksum file",logDir)
                    resultsList[3] += 1
                    resultsList = writeHash(sf, hashalg,logDir,resultsList) #if has is older, recreate sidecar file
                    resultsList = copyFiles(sf,df,logDir, resultsList) #once the hash is written we can move the file
            else:
                resultsList = writeHash(sf, hashalg,logDir, resultsList) #if no sidecar file exists, make one!
                resultsList = copyFiles(sf,df,logDir, resultsList) #once the hash is written we can move the file
        else: #if it's a hash file
            if os.path.exists(sf): #if the has exists
                resultsList = copyFiles(sf,df,logDir, resultsList) #move the hashe
                resultsList = verifyHash(df, hashalg, hashlength, logDir, resultsList) #verify the checksum from the sidecar file
            else: #if the hash file doesn't exist, we gotta make it, then copy it, then verify it (this is important if the file and hash are loaded, but the source hash has been deleted. could be skipped if i could figure this out)
                resultsList = writeHash(sf.replace("." + hashalg, ""), hashalg,logDir,resultsList) #write the hash
                resultsList = copyFiles(sf,df,logDir, resultsList) #move the hash
                resultsList = verifyHash(df, hashalg, hashlength, logDir, resultsList) #verify the checksum from the sidecar file
    return resultsList

#compares two files. If olderFile was created before newerFile then return true. else return false
def compare_modtime(olderFile, newerFile):
    olderFileMod = os.path.getmtime(olderFile)
    newerFileMod = os.path.getmtime(newerFile)
    if newerFileMod > olderFileMod:
        return True
    else:
        return False

#compares two files. If file1 and file2 are same size returns true, otherwise returns false
def compare_filesize(file1, file2):
    file1Size = os.stat(file1).st_size
    file2Size = os.stat(file2).st_size
    if file1Size == file2Size:
        return True
    else:
        return False

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
    args = make_args()
    ###INIT VARS###
    flist = []
    successCopyCount = 0
    successWriteHashCount = 0
    successVerifyHashCount = 0
    warningCount = 0
    errorCount =0
    resultsList = [successCopyCount,successWriteHashCount,successVerifyHashCount,warningCount,errorCount]
    ###END INIT###

    #housekeeping
    if len(args.sourceAndDestObj) < 2: #if less than two input arguments we have to exit
        print("CRITICAL ERROR: You must give this script at least two input arguments, with the last argument being the destination directory")
        sys.exit()

    destinationDir = args.sourceAndDestObj.pop(-1)

    if os.path.isdir(destinationDir) is False:
        print("CRITICAL ERROR: The last argument must be a directory")
        sys.exit()

    sourceList = args.sourceAndDestObj

    for s in sourceList:
        s.replace("\\","/") #everything is gonna break if we don't do this for windows ppl
    if args.q is True: #quiet mode redirects standard out to nul
        f = open(os.devnull,'w')
        sys.stdout = f
    hashAlgorithm = hashlib.new(args.a) #creates a hashlib object that is the algorithm we're using
    hashlengths = {'md5':'32','sha1':'40','sha256':'64','sha512':'128'}
    hashlength = hashlengths[args.a] #set value for comparison later

    #Initialize log
    initLog(sourceList,destinationDir,args.a)

    #Create giant list of input files and output files
    flist = makeFileList(sourceList,destinationDir,args.a,hashlengths,args.xr)

    #updates file list, removing all files that were already there
    flist = removeUpToDateFiles(flist, args.a, hashlength)

    #process files in the list
    resultsList = processList(flist, args.a, hashlength, destinationDir, resultsList)

    print("\nCopy and Verify Completed! Here are the results. See log for details")
    print("\nFiles Copied: " + str(resultsList[0]))
    print("Checksums Written: " + str(resultsList[1]))
    print("Checksums Verified: " + str(resultsList[2]))
    print("Warnings: " + str(resultsList[3]))
    print("Errors: " + str(resultsList[4]))
    print("\n")

    logSameLine("\n***************************\n\n\n\n",destinationDir)

main()
