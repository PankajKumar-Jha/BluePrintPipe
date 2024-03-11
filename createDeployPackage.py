#This script should be used to load source code to a Git Repository
#
r"""
Copyright (C) 2010-2023 Micro Focus.  All Rights Reserved.
This software may be used, modified, and distributed 
(provided this notice is included without modification)
solely for internal demonstration purposes with other 
Micro Focus software, and is otherwise subject to the EULA at
https://www.microfocus.com/en-us/legal/software-licensing.
THIS SOFTWARE IS PROVIDED "AS IS" AND ALL IMPLIED 
WARRANTIES, INCLUDING THE IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE,
SHALL NOT APPLY.
TO THE EXTENT PERMITTED BY LAW, IN NO EVENT WILL 
MICRO FOCUS HAVE ANY LIABILITY WHATSOEVER IN CONNECTION
WITH THIS SOFTWARE.

"""

import os
import sys
import logging
import platform
import datetime

import glob
import shutil
import yaml

from git import Repo, Git


def createDeployPackage(loadDir, gitBaseDir, branch, appVersion, packageType):
    
    currentOS = platform.system()
    cwd = os.getcwd()
    
    #setting up logging 
    logging.basicConfig(filename='createPackage.log', encoding='utf-8', level=logging.INFO)
    logging.basicConfig(format='%(asctime)16s %(process)8d %(message)s')

    if packageType == 'APP':
         createAppDeployPackage(loadDir, gitBaseDir, branch, appVersion) 

    if  packageType == 'SYS':
        createSysDeployPackage(loadDir, gitBaseDir, branch, appVersion)   

def createSysDeployPackage(loadDir, gitBaseDir, branch, appVersion):

    currentOS = platform.system()
    cwd = os.getcwd()

    logging.info(f'Create System Package')
    packageBaseDir = os.path.join(cwd, 'systemartefacts')
    packageSubDir = os.path.join(packageBaseDir, appVersion)

    try:
         shutil.copytree(loadDir, packageSubDir)
    except Exception as excp:
                    s = repr(excp)
                    logging.error(f"{s}")
                    raise

    if currentOS == 'Windows':
        archType = 'zip'
    else:
        archType = 'tar'

    curDatetime = (f'{datetime.datetime.now():%Y-%m-%d-%H-%M-%S}')    
    fileName = 'system_' + appVersion + '_' + curDatetime
    
    zipFile = os.path.join (cwd, fileName)
    
    try:
        shutil.make_archive(zipFile, archType, root_dir=packageBaseDir)
    except Exception as excp:
                    s = repr(excp)
                    logging.error(f"{s}")
                    raise

    textOut = f'System Deployment package {zipFile} created successfully.'
    logging.info(textOut)
    print(textOut)
    print('Review createPackage.log for details')

def createAppDeployPackage(loadDir, gitBaseDir, branch, appVersion):
    ## Connect to Git Repo and determine all files changed in the last commit
    try:
        currentRepo = Repo(gitBaseDir)
        res = currentRepo.git.checkout(branch)
    except Exception as excp:
                    s = repr(excp)
                    logging.error(f"{s}")
                    raise
    
    logging.info(f'Connect to source repo and set branch to {branch}')

    if appVersion == 'Init':    
        # currentCommits = currentRepo.git.log('--oneline', '--grep=Initial Load')
        currentCommits = currentRepo.git.log('--oneline', '--grep=Init')
    else:
        currentCommits = currentRepo.git.log('--oneline', '-n', '1')

    commitHash = currentCommits.split(' ')

    changedFiles = currentRepo.git.execute(['git', 'show', '--name-only', '-r', commitHash[0]]).split()

    ## Create Manifest Files
    returnedFile = createManifest(loadDir, changedFiles, appVersion)

    ## Create Package from Manifest File
    createPackage (loadDir, returnedFile, gitBaseDir)

def createPackage (loadDir, manifestFile, gitBaseDir):    
   
    currentOS = platform.system()
    cwd = os.getcwd()

    packageBaseDir = os.path.join(cwd, 'buildartefacts')
    packageSubDir = os.path.join(packageBaseDir, appVersion)
    packageLoadDir = os.path.join(packageSubDir, 'load')
    packageCICSDir = os.path.join(packageSubDir, 'cics')
    packageJCLDir = os.path.join(packageSubDir, 'jcl')
    packagePROCDir = os.path.join(packageSubDir, 'proclib')
    packageCTLDir = os.path.join(packageSubDir, 'ctlcards')

   
    makeDirectory(packageBaseDir)
    makeDirectory(packageSubDir)
    makeDirectory(packageLoadDir)
    makeDirectory(packageCICSDir)
    makeDirectory(packageJCLDir)
    makeDirectory(packagePROCDir)
    makeDirectory(packageCTLDir)
    
    logging.info(f'Package folder structure created')
    print(f'Temporary structure created for build artifacts')
    
    with open (manifestFile, 'r') as f:
        manifestLines = f.readlines()
        for line in manifestLines:
            lineType = line.split('--')[0]
            if lineType == 'Load' or lineType == 'MOD':
                fromFile = (line.split('--')[3]).strip()
                toFile = os.path.join(packageLoadDir, line.split('--')[1])
                copyFileToArchive(fromFile, toFile)
                logging.info(f'Loading {fromFile} to package archive')
            if lineType == 'JCL':
                tmp = (line.split('--')[3]).strip()
                fromFile = os.path.join(gitBaseDir, tmp)
                toFile = os.path.join(packageJCLDir, line.split('--')[1])
                copyFileToArchive(fromFile, toFile)
                logging.info(f'Loading {fromFile} to package archive')
            if lineType == 'PROC':
                tmp = (line.split('--')[3]).strip()
                fromFile = os.path.join(gitBaseDir, tmp)
                toFile = os.path.join(packagePROCDir, line.split('--')[1])
                copyFileToArchive(fromFile, toFile)
                logging.info(f'Loading {fromFile} to package archive')
            if lineType == 'CTLCRD':
                tmp = (line.split('--')[3]).strip()
                fromFile = os.path.join(gitBaseDir, tmp)
                toFile = os.path.join(packageCTLDir, line.split('--')[1])
                copyFileToArchive(fromFile, toFile)
                logging.info(f'Loading {fromFile} to package archive')


    baseName = os.path.basename(manifestFile)
    toFile = os.path.join(packageBaseDir, baseName)

    try:
        shutil.copyfile(manifestFile, toFile)
    except Exception as excp:
                    s = repr(excp)
                    logging.error(f"{s}")
                    raise
    
    logging.info(f'Loading manifest {manifestFile} to package archive') 

    cicsFolder = gitBaseDir + '/CICS/*.rdt'

    for file in glob.glob(cicsFolder):
        baseName = os.path.basename(file)    
        toFile = os.path.join(packageCICSDir, baseName)
        try:
            shutil.copyfile(file, toFile)
        except Exception as excp:
                    s = repr(excp)
                    logging.error(f"{s}")
                    raise
    
    if currentOS == 'Windows':
        archType = 'zip'
    else:
        archType = 'tar'
        
    tmp = manifestFile.replace('.txt', '')
    zipFile = tmp.replace('manifest', 'build')

    try:
        shutil.make_archive(zipFile, archType, root_dir=packageBaseDir)
    except Exception as excp:
                    s = repr(excp)
                    logging.error(f"{s}")
                    raise
    
    textOut = f'Deployment package {zipFile} created successfully.'
    logging.info(textOut)
    print(textOut)
    print('Review createPackage.log for details')

def makeDirectory(dirName):

    logging.info(f'Creating directory {dirName}') 

    try:
          os.mkdir(dirName)
    except FileExistsError:
        pass
    except Exception as excp:
                    s = repr(excp)
                    logging.error(f"{s}")
                    raise

def copyFileToArchive(fromFile, toFile):
     
    try:    
        shutil.copyfile(fromFile, toFile)
    except Exception as excp:
        s = repr(excp)
        logging.error(f"{s}")
        raise

def createManifest (loadDir, changedFiles, appVersion):

    currentOS = platform.system()
    cwd = os.getcwd()
    
    curDatetime = (f'{datetime.datetime.now():%Y-%m-%d-%H-%M-%S}')
    fileName = 'manifest_' + appVersion + '_' + curDatetime + '.txt'

    manifestFile = os.path.join(cwd, fileName)

    if currentOS == 'Windows':
        loadExt = 'dll'
    else:
        loadExt = 'so'

    searchName = loadDir + '/*.' + loadExt

    logging.info(f'Writing Manifest file {manifestFile}')

    with open(manifestFile, 'w') as f:
        for file in glob.glob(searchName):
            baseName = os.path.basename(file)
            isModified = checkIfChanged(file, changedFiles)
            f.write ('Load--{}--{}--{} \n'.format(baseName, isModified, file))
        searchName = loadDir + '/*.mod'
        for file in glob.glob(searchName):
            baseName = os.path.basename(file)
            isModified = checkIfChanged(file, changedFiles)
            f.write ('MOD--{}--{}--{} \n'.format(baseName, isModified, file))
        for file in changedFiles:
            if '.jcl' in file:
                baseName = os.path.basename(file)
                f.write('JCL--{}--Changed--{} \n'.format(baseName, file))
        for file in changedFiles:
            if '.ctl' in file:
                baseName = os.path.basename(file)
                f.write('CTLCRD--{}--Changed--{} \n'.format(baseName, file))
        for file in changedFiles:
            if '.prc' in file:
                baseName = os.path.basename(file)
                f.write('PROC--{}--Changed--{} \n'.format(baseName, file))
        f.close

    textOut = f'Manifest file {manifestFile} created'
    logging.info(textOut)
    print(textOut)

    return manifestFile

def checkIfChanged (loadFile, changedFiles):

    baseName = os.path.splitext(os.path.basename(loadFile))[0]
    baseExt = os.path.splitext(os.path.basename(loadFile))[1]

    retValue = [s for s in changedFiles if baseName in s]

    if retValue != '':
        res = 'Changed'
    else:
        res = 'Unchanged'

    return res

if __name__ == '__main__':

    loadDir = sys.argv[1]
    gitBaseDir = sys.argv[2]
    branch = sys.argv[3]
    appVersion = sys.argv[4]
    packageType = sys.argv[5]

    print(f'Starting creation of package archive')

    createDeployPackage(loadDir, gitBaseDir, branch, appVersion, packageType)