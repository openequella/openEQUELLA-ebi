# Engine.py
#
# Author: Jim Kurian, Pearson plc.
# Date: October 2014
#
# The CSV processing engine of the EQUELLA Bulk Importer. Loads a
# CSV file and iterates through the rows creating items in EQUELLA
# for each one. Utilizes equellaclient41.py for EQUELLA
# communications. Invoked by Mainframe.py.

from xml.dom import Node
from equellaclient41 import *
import time, datetime
import zipfile, csv, codecs, cStringIO
import sys, platform
import traceback
import random
import os
import zipfile, glob, time, getpass, uuid
import wx

class Engine():
    def __init__(self, owner, Version, Copyright):
        # constants
        self.METADATA = 'Metadata'
        self.ATTACHMENTLOCATIONS = 'Attachment Locations'
        self.ATTACHMENTNAMES = 'Attachment Names'
        self.CUSTOMATTACHMENTS = 'Custom Attachments'
        self.RAWFILES = 'Raw Files'
        self.URLS = 'URLs'
        self.HYPERLINKNAMES = 'Hyperlink Names'
        self.EQUELLARESOURCES = 'EQUELLA Resources'
        self.EQUELLARESOURCENAMES = 'EQUELLA Resource Names'
        self.COMMANDS = 'Commands'
        self.TARGETIDENTIFIER = 'Target Identifier'
        self.TARGETVERSION = 'Target Version'
        self.COLLECTION = 'Collection'
        self.OWNER = 'Owner'
        self.COLLABORATORS = 'Collaborators'
        self.ITEMID = 'Item ID'
        self.ITEMVERSION = 'Item Version'
        self.ROWERROR = 'Row Error'
        self.THUMBNAILS = "Thumbnails"
        self.SELECTEDTHUMBNAIL = "Selected Thumbnail"
        self.IGNORE = 'Ignore'
        
        self.COLUMN_POS = "Pos"
        self.COLUMN_HEADING = "Column Heading"
        self.COLUMN_DATATYPE = "Column Data Type"
        self.COLUMN_DISPLAY = "Display"
        self.COLUMN_SOURCEIDENTIFIER = "Source Identifier"
        self.COLUMN_XMLFRAGMENT = "XML Fragment"
        self.COLUMN_DELIMITER = "Delimiter"      
        
        self.CLEARMETA = 0  
        self.REPLACEMETA = 1
        self.APPENDMETA = 2

        self.OVERWRITENONE = 0
        self.OVERWRITEEXISTING = 1
        self.OVERWRITEALL = 2
                
        self.pause = False
        self.owner = owner

        # default settings (can be overridden in ebi.properties)
        self.debug = False
        self.attachmentMetadataTargets = True
        self.defaultChunkSize = (1024 * 2048)
        self.chunkSize = self.defaultChunkSize
        self.networkLogging = False
        self.scormformatsupport = True
              
        self.copyright = Copyright
        self.rowFilter = ""
        self.logfilesfolder = "logs"
        self.logfilespath = ""
        self.testItemfolder = "test_output"
        self.receiptFolder = "receipts"
        self.sessionName = ""
        self.maxRetry = 5

        # welcome message for command prompt and log files
        self.welcomeLine1 = "EQUELLA Bulk Importer [EBI %s, %s]" % (Version, self.getPlatform())
        self.welcomeLine2 = self.copyright + "\n"

        print self.welcomeLine1
        print self.welcomeLine2

        # CSV and connection settings
        self.institutionUrl = ""
        self.username = ""
        self.password = ""
        self.collection = ""
        self.csvFilePath = ""
        
        # Options
        self.proxy = ""
        self.proxyUsername = ""
        self.proxyPassword = ""
        self.encoding = "utf8"
        self.saveTestXML = False
        self.saveAsDraft = False
        self.saveTestXml = False
        self.existingMetadataMode = self.CLEARMETA
        self.appendAttachments = False
        self.createNewVersions = False
        self.useEBIUsername = False
        self.ignoreNonexistentCollaborators = False
        self.saveNonexistentUsernamesAsIDs = True
        self.attachmentsBasepath = ""
        self.absoluteAttachmentsBasepath = ""
        self.export = False
        self.includeNonLive = False
        self.overwriteMode = self.OVERWRITENONE
        self.whereClause = ""
        self.startScript = ""
        self.endScript = ""
        self.preScript = ""
        self.postScript = ""
        
        self.ebiScriptObject = EbiScriptObject(self)        

        # data structures to store column settings
        self.currentColumns = []
        self.csvArray = []
                
        self.successCount = 0
        self.errorCount = 0
        

        # enum for attachment types
        self.attachmentTypeFile = 0
        self.attachmentTypeZip = 1
        self.attachmentTypeIMS = 2
        self.attachmentTypeSCORM = 3
        
        self.columnHeadings = []
        self.StopProcessing = False
        self.processingStoppedByScript = False
        self.Skip = False
        self.logFileName = ""
        self.collectionIDs = {}
        
        self.itemSystemNodes = [
                                                "staging",
                                                "name",
                                                "description",
                                                "itemdefid",
                                                "datecreated",
                                                "datemodified",
                                                "dateforindex",
                                                "owner",
                                                "collaborativeowners",
                                                "rating",
                                                "badurls",
                                                "moderation",
                                                "newitem",
                                                "attachments",
                                                "navigationnodes",
                                                "url",
                                                "history",
                                                "thumbnail"
                                            ]
        self.sourceIdentifierReceipts = {}
        self.exportedFiles = []
        self.eqVersionmm = ""
        self.eqVersionmmr = ""
        self.eqVersionDisplay = ""
        
    def getPlatform(self):
        ebiPlatform = "Python " + platform.python_version()
        system = platform.system()
        if system == "Windows":
            ebiPlatform += ", Windows " + platform.release()
        elif system == "Darwin":
            ebiPlatform += ", Mac OS " + platform.mac_ver()[0]
        elif system == "Linux":
            # Use freedesktop_os_release() for Python 3.10+ or fallback for older versions
            try:
                if hasattr(platform, 'freedesktop_os_release'):
                    os_info = platform.freedesktop_os_release()
                    ebiPlatform += ", " + os_info.get('NAME', 'Linux') + " " + os_info.get('VERSION', '').strip()
                else:
                    ebiPlatform += ", Linux " + platform.release()
            except Exception:
                ebiPlatform += ", Linux " + platform.release()
        return ebiPlatform
        
    def setDebug(self, debug):
        self.debug = debug
        if self.debug:
            self.echo("debug = True")
            
    def setLog(self, log):
        self.log = log
        self.log.AddLogText(self.welcomeLine1 + "\n", 1)
        self.log.AddLogText(self.welcomeLine2 + "\n", 1)

    def echo(self, entry, display = True, log = True, style = 0):
            
        if log and self.logFileName != "":
        
            # create/open log file
            logfile = open(os.path.join(self.logfilespath, self.logFileName),"a")
              
            # write entry  
            logfile.writelines(entry.encode(self.encoding) + "\n")
            
            logfile.close()
            
        if display:
            self.log.AddLogText(entry.encode(self.encoding) + "\n", style)
            print entry.encode(self.encoding)
        return

    def translateError(self, rawError, context = ""):
        
        rawError = str(rawError)
        
        # check if it is a SOAP error
        if rawError.rfind('</faultstring>') != -1:
            # Extract faultstring from 500 code and display/log
            rawError = rawError[rawError.find('faultstring') + 12:rawError.rfind('</faultstring')].strip()

        # form friendly error messages for common errors
        if "org.mozilla.javascript" in rawError:
            translatedError = "EQUELLA returned the following script error: " + rawError.replace("&quot;", "'")[rawError.find(":") + 1:].strip()
        elif "Cannot parse server response as XML" in rawError:
            if self.proxy == "":
                translatedError = "Receiving back web page instead of normal response. Check Institution URL."
            else:
                translatedError = "Receiving back web page instead of normal response. Check Institution URL and proxy settings."
        elif "getaddrinfo failed" in rawError:
            if self.proxy == "":            
                translatedError = "No response from server. Check Institution URL."
            else:
                translatedError = "No response from server. Check Institution URL and proxy settings."
        elif "Connection refused" in rawError:
            if self.proxy == "":  
                translatedError = "Connection refused by server. Check Institution URL."
            else:
                translatedError = "Connection refused by server. Check Institution URL and proxy settings."
        elif "No service was found" in rawError:
            translatedError = "Supported API was not found. Check EQUELLA version is 4.1 or higher."
        elif "unknown url type" in rawError:
            translatedError = "Unknown URL type. Make certain URL begins with either 'http://' or 'https://'."
        elif "while locating com.tle.beans.entity.itemdef.ItemDefinition" in rawError:
            translatedError = "Collection not found."
        elif "basic auth failed" in rawError:
            translatedError = "Proxy authentication failed. Check proxy settings."
        elif "codec can't decode byte" in rawError:
            translatedError = rawError + ". Try changing encoding."            
            
        else:
            translatedError = rawError
            if rawError.rfind('<html') != -1:
                if context == "login":
                    translatedError = "Receiving back web page instead of normal response. Check Institution URL."
                else:
                    translatedError = "Receiving back web page instead of normal response."

        translatedError = translatedError.replace("\\\\", "\\")
            
        return translatedError
    
    def group(self, number):
        s = '%d' % number     
        groups = []     
        while s and s[-1].isdigit():         
            groups.append(s[-3:])         
            s = s[:-3]     
        return s + ','.join(reversed(groups)) 

    def validateColumnHeadings(self):
        testPB = PropBagEx("<xml><item/></xml>")
        # iterate through columns and check for validity
        for n, columnHeading in enumerate(self.columnHeadings):
            if self.currentColumns[n][self.COLUMN_DATATYPE] == self.METADATA:
                if columnHeading == "":
                    raise Exception, "Blank column heading found on column requiring XPath '%s' (column %s)" % (columnHeading, n + 1)
            
            if self.currentColumns[n][self.COLUMN_DATATYPE] == self.METADATA or \
            (self.currentColumns[n][self.COLUMN_DATATYPE] in [self.ATTACHMENTLOCATIONS, self.URLS, self.EQUELLARESOURCES, self.CUSTOMATTACHMENTS] and \
            columnHeading.strip() != "" and columnHeading.strip()[0] != "#"):
                try:
                    # test xpath
                    testPB.validateXpath(columnHeading.strip())
                except:
                    if self.debug:
                        raise
                    else:
                        exceptionValue = sys.exc_info()[1]
                        scriptErrorMsg = "Invalid column heading '%s' (column %s). %s" % (columnHeading, n + 1, exceptionValue)
                        raise Exception, scriptErrorMsg
                    
                # warn the user if any XPaths are attempting to overwrite system nodes
                xpathParts = columnHeading.split("/")
                if columnHeading.strip() == "item" or len(xpathParts) > 1:
                    if columnHeading.strip() == "item" or (xpathParts[0].strip() == "item" and xpathParts[1].strip() in self.itemSystemNodes):
                        self.echo("WARNING: XPath '%s' in column %s is writing to a system node" % (columnHeading, n + 1))
                
    def getEquellaVersion(self):
        # download and read version.properties
        try:
            versionUrl = self.institutionUrl + "/version.properties"
            versionProperties = ""
            versionProperties = self.tle.getText(versionUrl)
            vpLines = versionProperties.split("\n")
            
            for line in vpLines:
                line = line.strip()
                lineparts = line.split("=")
                if lineparts[0] == "version.mm":
                    self.eqVersionmm = lineparts[1]
                if lineparts[0] == "version.mmr":
                    self.eqVersionmmr = lineparts[1]
                if lineparts[0] == "version.display":
                    self.eqVersionDisplay = lineparts[1]
           
        except:
            if self.debug:
                exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
                self.echo(''.join(traceback.format_exception(exceptionType, exceptionValue, exceptionTraceback)))
    
    def getContributableCollections(self):
        try:
            # connect to EQUELLA
            self.tle = TLEClient(self, self.institutionUrl, self.username, self.password, self.proxy, self.proxyUsername, self.proxyPassword, self.debug)
            self.getEquellaVersion()
        except:
            if self.debug:
                raise
            else:
                raise Exception, self.translateError(str(sys.exc_info()[1]), "login")

        try:
            # get all contributable collections and their IDs
            itemDefs = self.tle._enumerateItemDefs()
            self.collectionIDs.clear()
            for key, value in itemDefs.items():
                self.collectionIDs[key] = value["uuid"] 
                            
            self.tle.logout()
            
            # return collection names (sorted)
            return sorted(self.collectionIDs.keys())
        except:
            if self.debug:
                raise
            else:            
                raise Exception, self.translateError(str(sys.exc_info()[1]))
    
    # find index of first matching instance of value, return -1 if not found
    def lookupColumnIndex(self, columnProperty, value):
        for index, column in enumerate(self.currentColumns):
            if column[columnProperty] == value:
                
                # value found
                return index
            
        # value not found
        return -1
    
    def tryPausing(self, message, newline = False):
        progress = message
        if self.pause:
            self.log.Enable()
            # add message to log
            self.log.SetReadOnly(False)
            if newline:
                self.log.AppendText("\n")
            self.log.AppendText(progress)
            self.log.SetReadOnly(True)
            self.log.GotoPos(self.log.GetLength())
            statusOriginalText = self.owner.mainStatusBar.GetStatusText(0)
            self.owner.mainStatusBar.SetStatusText("PAUSED...", 2)
            
            # pause loop
            count = 0
            while self.pause:
                wx.GetApp().Yield()
                time.sleep(0.5)
                if count == 0:
                    self.owner.mainStatusBar.SetStatusText("PAUSED.", 2)
                    count = 1
                elif count == 1:
                    self.owner.mainStatusBar.SetStatusText("PAUSED..", 2)
                    count = 2
                else:
                    self.owner.mainStatusBar.SetStatusText("PAUSED...", 2)
                    count = 0
                
            
            # remove message
            if message != "":    
                self.log.DocumentEnd()
                self.log.SetReadOnly(False)
                for i in range(len(progress)):
                    self.log.DeleteBack()
                if newline:
                    self.log.DeleteBack()
                self.log.SetReadOnly(True)
            self.log.Disable()
            self.owner.mainStatusBar.SetStatusText("", 2)

    def runImport(self, owner, testOnly=False):
        self.StopProcessing = False
        self.pause = False
        self.processingStoppedByScript = False
        
        try:
            # try opening csv file
            if owner.txtCSVPath.GetValue() != "" and not os.path.isdir(self.csvFilePath):
                f = open(self.csvFilePath, "rb")
                f.close()
        except:
            owner.mainStatusBar.SetStatusText("Processing halted due to an error", 0)
            raise Exception, "CSV file could not be opened, check path: %s" % self.csvFilePath        

        # specify folders
        self.logfilespath = os.path.join(os.path.dirname(self.csvFilePath), self.logfilesfolder)
        self.testItemfolder = os.path.join(os.path.dirname(self.csvFilePath), self.testItemfolder)
        self.receiptFolder = os.path.join(os.path.dirname(self.csvFilePath), self.receiptFolder)
        
        # specify log file name for this run
        if not os.path.exists(self.logfilespath):
            os.makedirs(self.logfilespath)
        self.sessionName = datetime.datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        self.logFileName = self.sessionName + '.txt'
        
        self.echo(self.welcomeLine1, False)
        self.echo(self.welcomeLine2, False)
        if self.debug:
            self.echo("Debug mode on\n", False)
        
        # create objects for EBI scripts
        self.logger = Logger(self)
        self.process = Process(self)

        self.echo(time.strftime("%H:%M:%S: ", time.localtime(time.time())) + "Opening a connection to EQUELLA at %s..." % self.institutionUrl)
        
        try:

            # set stats counters
            self.successCount = 0
            self.errorCount = 0

            # connect to EQUELLA            
            owner.mainStatusBar.SetStatusText("Connecting...", 0)
            wx.GetApp().Yield()
            self.tle = TLEClient(self, self.institutionUrl, self.username, self.password, self.proxy, self.proxyUsername, self.proxyPassword, self.debug)
            
            # get EQUELLA version
            if self.eqVersionmm == "":
                self.getEquellaVersion()
            versionDisplay = ""
            if self.eqVersionDisplay != "":
                versionDisplay = " (%s)" % self.eqVersionDisplay 
            self.echo(time.strftime("%H:%M:%S: ", time.localtime(time.time())) + "Successfully connected to EQUELLA%s" % versionDisplay)

            # Get Collection UUID
            self.echo(time.strftime("%H:%M:%S: ", time.localtime(time.time())) + "Target collection: '" + self.collection  + "'...")

            # if not previously retreieved get all contributable collections and their IDs
            if len(self.collectionIDs) == 0:
                itemDefs = self.tle._enumerateItemDefs()
                for key, value in itemDefs.items():
                    self.collectionIDs[key] = value["uuid"]                
            
            # get ID of selected collection
            if self.collection in self.collectionIDs.keys():
                itemdefuuid = self.collectionIDs[self.collection]
            else:
                raise Exception, "Collection '" + self.collection + "'" + " not found"
            
            try:
                if not os.path.isdir(self.csvFilePath):
                    self.echo(time.strftime("%H:%M:%S: ", time.localtime(time.time())) + "Parsing CSV file (" + self.csvFilePath + ")...")
                else:
                    self.echo(time.strftime("%H:%M:%S: ", time.localtime(time.time())) + "WARNING: No CSV specified. CSV path is " + self.csvFilePath)
                    
                if not owner.verifyCurrentColumnsMatchCSV():
                    raise Exception, 'CSV headings do not match the settings, update the settings to match the CSV column headings'
                
                # determine the column indexes for the following column types
                sourceIdentifierColumn = self.lookupColumnIndex(self.COLUMN_SOURCEIDENTIFIER, "YES")
                targetIdentifierColumn = self.lookupColumnIndex(self.COLUMN_DATATYPE, self.TARGETIDENTIFIER)
                targetVersionColumn = self.lookupColumnIndex(self.COLUMN_DATATYPE, self.TARGETVERSION)
                commandOptionsColumn = self.lookupColumnIndex(self.COLUMN_DATATYPE, self.COMMANDS)
                attachmentLocationsColumn = self.lookupColumnIndex(self.COLUMN_DATATYPE, self.ATTACHMENTLOCATIONS)
                customAttachmentsColumn = self.lookupColumnIndex(self.COLUMN_DATATYPE, self.CUSTOMATTACHMENTS)
                urlsColumn = self.lookupColumnIndex(self.COLUMN_DATATYPE, self.URLS)
                resourcesColumn = self.lookupColumnIndex(self.COLUMN_DATATYPE, self.EQUELLARESOURCES)
                itemIdColumn = self.lookupColumnIndex(self.COLUMN_DATATYPE, self.ITEMID)
                versionColumn = self.lookupColumnIndex(self.COLUMN_DATATYPE, self.ITEMVERSION)
                thumbnailsColumn = self.lookupColumnIndex(self.COLUMN_DATATYPE, self.THUMBNAILS)
                selectedThumbnailColumn = self.lookupColumnIndex(self.COLUMN_DATATYPE, self.SELECTEDTHUMBNAIL)
                rowErrorColumn = self.lookupColumnIndex(self.COLUMN_DATATYPE, self.ROWERROR)
                collectionColumn = self.lookupColumnIndex(self.COLUMN_DATATYPE, self.COLLECTION)
                ownerColumn = self.lookupColumnIndex(self.COLUMN_DATATYPE, self.OWNER)
                collaboratorsColumn = self.lookupColumnIndex(self.COLUMN_DATATYPE, self.COLLABORATORS)
                
                # ignore Source Identifier if column datatype is set to Ignore
                if sourceIdentifierColumn != -1 and self.currentColumns[sourceIdentifierColumn][self.COLUMN_DATATYPE] == self.IGNORE:
                    sourceIdentifierColumn = -1
                
                # parse CSV
                self.csvParse(owner,
                              self.tle,
                              itemdefuuid,
                              testOnly,
                              sourceIdentifierColumn,
                              targetIdentifierColumn,
                              targetVersionColumn,
                              commandOptionsColumn,
                              attachmentLocationsColumn,
                              urlsColumn,
                              resourcesColumn,
                              customAttachmentsColumn,
                              itemIdColumn,
                              versionColumn,
                              rowErrorColumn,
                              collectionColumn,
                              thumbnailsColumn,
                              selectedThumbnailColumn,
                              ownerColumn,
                              collaboratorsColumn)
                              
            except:
                owner.mainStatusBar.SetStatusText("Processing halted due to an error", 0)
                
                err = str(sys.exc_info()[1])
                exact_error = err

                errorString = ""
                exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
                if self.debug:
                    errorString = "\n" + ''.join(traceback.format_exception(exceptionType, exceptionValue, exceptionTraceback))                

                # check if it is a SOAP error
                if err.rfind('</faultstring>') != -1:
                    # Extract faultstring from 500 code and display/log
                    exact_error = err[err.find('faultstring') + 12:err.rfind('</faultstring')]
                self.echo(time.strftime("%H:%M:%S: ", time.localtime(time.time())) + "ERROR: " + exact_error.strip() + errorString, style=2)

            # close EQUELLA connection
            self.tle.logout()
            self.echo(time.strftime("%H:%M:%S: ", time.localtime(time.time())) + "Connection successfully closed\n")

        except:
            owner.mainStatusBar.SetStatusText("Processing halted due to an error", 0)

            # could not connect to EQUELLA
            err = str(sys.exc_info()[1])
            exact_error = err

            # form a stack trace for debugging
            errorString = ""
            exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
            if self.debug:
                errorString = "\n" + ''.join(traceback.format_exception(exceptionType, exceptionValue, exceptionTraceback))               

            # check if it is a SOAP error
            if err.rfind('</faultstring>') != -1:
                # Extract faultstring from 500 code and display/log
                exact_error = err[err.find('faultstring') + 12:err.rfind('</faultstring')].strip()

            # create a friendly error message for common connection errors
            exact_error = self.translateError(exact_error, "login")
                
            self.echo(time.strftime("%H:%M:%S: ", time.localtime(time.time())) + "ERROR whilst trying to connect: " + exact_error.strip() + errorString, style=2)

        return
               
    def removeDuplicates(self, seq, idfun=None): 
        # order preserving
        if idfun is None:
            def idfun(x): return x
        seen = {}
        result = []
        for item in seq:
            marker = idfun(item)
            if marker in seen: continue
            seen[marker] = 1
            result.append(item)
        return result
    
    def unicode_csv_reader(self, utf8_data, encoding, dialect=csv.excel, **kwargs):
        csv_reader = csv.reader(utf8_data, dialect=dialect, **kwargs)
        firstRow = True
        for row in csv_reader:
            # remove BOM for utf-8
            if firstRow:
                if row[0].startswith(codecs.BOM_UTF8):
                    row[0] = row[0].decode("utf-8")[1:]
                firstRow = False

            yield [cell.decode(encoding) for cell in row]
                
    def loadCSV(self, owner=None):
        self.csvArray = []
        if owner == None or owner.txtCSVPath.GetValue() != "":
            if not os.path.isdir(self.csvFilePath):
                reader = self.unicode_csv_reader(open(self.csvFilePath, "rbU"), self.encoding)
                for row in reader:
                    self.csvArray.append(row)
                    
        # trim any trailing rows 
        for row in reversed(self.csvArray):
            if len(row) > 0:
                break
            else:
                del self.csvArray[-1]
                
        # if CSV file is empty or non-existent populate the first row with column headings from settings
        if len(self.csvArray) == 0:
            self.csvArray.append([])
            for columnHeading in self.columnHeadings:
                self.csvArray[0].append(columnHeading)

    def csvParse(self,
                 owner,
                 tle,
                 itemdefuuid,
                 testOnly,
                 sourceIdentifierColumn,
                 targetIdentifierColumn,
                 targetVersionColumn,
                 commandOptionsColumn,
                 attachmentLocationsColumn,
                 urlsColumn,
                 resourcesColumn,
                 customAttachmentsColumn,
                 itemIdColumn,
                 versionColumn,
                 rowErrorColumn,
                 collectionColumn,
                 thumbnailsColumn,
                 selectedThumbnailColumn,
                 ownerColumn,
                 collaboratorsColumn):

        # if real form receipt filename and run check if receipts file is editable
        receiptFilename = ""
        if not self.export:
            if itemIdColumn != -1:
                # form receipts filename
                if owner.txtCSVPath.GetValue() != "" and not os.path.isdir(self.csvFilePath):
                    receiptFilename = os.path.join(self.receiptFolder, os.path.basename(self.csvFilePath)) 
                else:
                    receiptFilename = os.path.join(self.receiptFolder, "receipt.csv") 
                    
                if os.path.exists(receiptFilename):
                    try:
                        # try opening file for editing
                        f = open(receiptFilename, "wb")
                        f.close()
                    except:
                        raise Exception, "Receipts file cannot be written to and may be in use: %s" % receiptFilename


        # read the CSV and store the rows in an array
        self.loadCSV(owner)
        
        # warn if not using attachment metadata targets
        if not self.attachmentMetadataTargets:
            self.echo("\nWARNING: Not using attachments metadata targets (not suitable for EQUELLA 5.0 or higher)\n")

        # calculate absolute appachments basepath for attachments
        self.absoluteAttachmentsBasepath = os.path.join(os.path.dirname(self.csvFilePath), self.attachmentsBasepath.strip())
        if self.debug:
            self.echo(time.strftime("%H:%M:%S: ", time.localtime(time.time())) + "Absolute attachments basepath is " + self.absoluteAttachmentsBasepath)
            
        # indicate what scripts, if any, are present
        scriptsPresent = []
        if self.startScript.strip() != "":
            scriptsPresent.append("Start Script")
        if self.preScript.strip() != "":
            scriptsPresent.append("Row Pre-Script")
        if self.postScript.strip() != "":
            scriptsPresent.append("Row Post-Script")
        if self.endScript.strip() != "":
            scriptsPresent.append("End Script")
        if len(scriptsPresent) > 0:
            self.echo(time.strftime("%H:%M:%S: ", time.localtime(time.time())) + "Scripts present: " + ", ".join(scriptsPresent))

        # set variables for scripts
        self.scriptVariables = {}
        if self.export:
            action = 1
        else:
            action = 0
            
        # run Start Script
        if self.startScript.strip() != "" and not self.export:
            try:
                exec self.startScript in {
                                        "IMPORT":0,
                                        "EXPORT":1,
                                        "mode":action,
                                        "vars":self.scriptVariables,
                                        "testOnly": testOnly,
                                        "institutionUrl":tle.institutionUrl,
                                        "collection":self.collection,
                                        "csvFilePath":self.csvFilePath,
                                        "username":self.username,
                                        "logger":self.logger,
                                        "columnHeadings":self.columnHeadings,
                                        "columnSettings":self.currentColumns,
                                        "successCount":self.successCount,
                                        "errorCount":self.errorCount,
                                        "process":self.process,
                                        "basepath":self.absoluteAttachmentsBasepath,
                                        "sourceIdentifierIndex":sourceIdentifierColumn,
                                        "targetIdentifierIndex":targetIdentifierColumn,
                                        "targetVersionIndex":targetVersionColumn,
                                        "csvData":self.csvArray, 
                                        "ebi":self.ebiScriptObject,                                       
                                        "equella":tle,                                   
                                        }
            except:
                if self.debug:
                    raise
                else:
                    exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
                    formattedException = "".join(traceback.format_exception_only(exceptionType, exceptionValue))[:-1]
                    scriptErrorMsg = "An error occured in the Start Script:\n%s (line %s)" % (formattedException, traceback.extract_tb(exceptionTraceback)[-1][1])
                    raise Exception, scriptErrorMsg  

        if not self.export:
            self.validateColumnHeadings()            

        # set all rows to be processed
        scheduledRows = range(1, len(self.csvArray))
        rowsToBeProcessedCount = len(self.csvArray) - 1
        scheduledRowsLabel = "all rows to be processed"

        # check if row filter applies
        if self.rowFilter.strip() != "":
            try:
                scheduledRows = []
                
                # populate scheduledRows based on rowsFilter
                rowRanges = self.rowFilter.split(",")
                for rowRange in rowRanges:
                    rows = rowRange.split("-")
                    
                    if len(rows) == 1:
                        
                        # single row number encountered
                        scheduledRows.append(int(rows[0]))
                        
                    if len(rows) == 2:
                        
                        # row range provided
                        if rows[1].strip() == "":
                            
                            # no finish row so assume all remaining rows (e.g. "5-")
                            rows[1] = len(self.csvArray) - 1
                            
                        scheduledRows.extend(range(int(rows[0]), int(rows[1]) + 1))
                
                # remove any duplicates (preserving order)
                scheduledRows = self.removeDuplicates(scheduledRows)

                # determine how many rows to be processed
                rowsToBeProcessedCount = 0
                for rc in scheduledRows:
                    if rc < len(self.csvArray):
                        rowsToBeProcessedCount += 1
                    
                # form label for how many rows to be processed
                scheduledRowsLabel = "%s to be processed [%s]" % (rowsToBeProcessedCount, self.rowFilter)
                
            except:
                if self.debug:
                    exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
                    self.echo(''.join(traceback.format_exception(exceptionType, exceptionValue, exceptionTraceback)))
                raise Exception, "Invalid row filter specified"
            
        if not self.export:
            # echo rows to be processed
            if testOnly:
                actionString = "%s row(s) found, %s (test only)" % (len(self.csvArray) - 1 if len(self.csvArray) > 0 else 0, scheduledRowsLabel)
            else:
                actionString = "%s row(s) found, %s" % (len(self.csvArray) - 1 if len(self.csvArray) > 0 else 0, scheduledRowsLabel)
            self.echo(time.strftime("%H:%M:%S: ", time.localtime(time.time())) + actionString)
        
            # echo draft and new version settings
            actionString = ""
            if sourceIdentifierColumn != -1 or targetIdentifierColumn != -1:
                if self.saveAsDraft and self.createNewVersions:
                    actionString = "Options -> Create new versions of existing items in draft status"
                elif self.createNewVersions:
                    actionString = "Options -> Create new versions of existing items"
                elif self.saveAsDraft:
                    actionString = "Options -> Create new items in draft status (status of existing items will remain unchanged)"
            elif self.saveAsDraft:
                actionString = "Options -> Create items in draft status"
            if actionString != "":
                self.echo(time.strftime("%H:%M:%S: ", time.localtime(time.time())) + actionString)
                
            # echo append/replace metadata settings
            actionString = ""
            if sourceIdentifierColumn != -1 or targetIdentifierColumn != -1:
                if self.existingMetadataMode == self.APPENDMETA:
                    actionString = "Options -> Append metadata to existing items"
                if self.existingMetadataMode == self.REPLACEMETA:
                    actionString = "Options -> Replace specified metadata in existing items"
                if actionString != "":
                    self.echo(time.strftime("%H:%M:%S: ", time.localtime(time.time())) + actionString)

                # echo append attachment settings
                if self.appendAttachments:
                    self.echo(time.strftime("%H:%M:%S: ", time.localtime(time.time())) + "Options -> Append attachments to existing items")

                
        # iterate through the rows of metadata from the CSV file creating an item in EQUELLA for each
        rowReceipts = {}
        processedCounter = 0
        self.sourceIdentifierReceipts = {}
        
        self.owner.progressGauge.SetRange(len(scheduledRows))
        self.owner.progressGauge.SetValue(processedCounter)
        self.owner.progressGauge.Show()

        if not self.export:
            
            # if Collection column spectifed check that all collection names resolve to collectionIDs
            if collectionColumn != -1:
                for rowCounter in scheduledRows:
                    collectionName = self.csvArray[rowCounter][collectionColumn]
                    if collectionName.strip() != "" and collectionName not in self.collectionIDs.keys():
                        raise Exception,"Unknown collection '%s' at row %s" % (collectionName, rowCounter)            
            
            rowCounter = 0
            for rowCounter in scheduledRows:
                if self.StopProcessing:
                    break
                
                if rowCounter < len(self.csvArray):
                    self.Skip = False
                    processedCounter += 1
                    
                    self.echo("---")
                    
                    self.tryPausing("[Paused]")                    
                
                    # update UI and log
                    wx.GetApp().Yield()
                    owner.mainStatusBar.SetStatusText("Processing row %s [%s of %s]" % (rowCounter, processedCounter, rowsToBeProcessedCount), 0)
                   
                    action = "Processing item..."
                    if testOnly:
                        action = "Validating item..."
                    self.echo(time.strftime("%H:%M:%S: ", time.localtime(time.time())) + " Row %s [%s of %s]: %s" % (rowCounter, processedCounter, rowsToBeProcessedCount, action))

                    # process row   
                    savedItemID, savedItemVersion, sourceIdentifier, rowData, rowError = self.processRow(rowCounter,
                                                                        self.csvArray[rowCounter],
                                                                        self.tle,
                                                                        itemdefuuid,
                                                                        self.collectionIDs,
                                                                        testOnly,
                                                                        sourceIdentifierColumn,
                                                                        targetIdentifierColumn,
                                                                        targetVersionColumn,
                                                                        commandOptionsColumn,
                                                                        attachmentLocationsColumn,
                                                                        urlsColumn,
                                                                        resourcesColumn,
                                                                        customAttachmentsColumn,
                                                                        collectionColumn,
                                                                        thumbnailsColumn,
                                                                        selectedThumbnailColumn,
                                                                        ownerColumn,
                                                                        collaboratorsColumn)
                                                                        
                    # add to row receipts
                    rowReceipts[rowCounter] = (savedItemID, savedItemVersion)
                    if sourceIdentifierColumn != -1:
                        self.sourceIdentifierReceipts[sourceIdentifier] = (savedItemID, savedItemVersion)                    
                    
                    
                    # update row in CSV array for receipt and script-processed row data
                    if itemIdColumn != -1:
                        # assign itemID to receipt cell
                        rowData[itemIdColumn] = savedItemID
                        rowData[versionColumn] = str(savedItemVersion)
                        if rowErrorColumn != -1:
                            rowData[rowErrorColumn] = rowError
                        self.csvArray[rowCounter] = rowData
                        
                    # update progress bar
                    self.owner.progressGauge.SetValue(processedCounter)
                        
            if self.StopProcessing:
                self.echo("---")
                if self.processingStoppedByScript:
                    self.echo(time.strftime("%H:%M:%S: ", time.localtime(time.time())) + "Processing halted")
                else:
                    self.echo(time.strftime("%H:%M:%S: ", time.localtime(time.time())) + "Processing halted by user")

            self.echo("---")

            # run End Script
            if self.endScript.strip() != "":
                try:
                    exec self.endScript in {
                                            "IMPORT":0,
                                            "EXPORT":1,
                                            "mode":action,
                                            "vars":self.scriptVariables,
                                            "rowCounter":rowCounter,
                                            "testOnly": testOnly,
                                            "institutionUrl":tle.institutionUrl,
                                            "collection":self.collection,
                                            "csvFilePath":self.csvFilePath,
                                            "username":self.username,
                                            "logger":self.logger,
                                            "columnHeadings":self.columnHeadings,
                                            "columnSettings":self.currentColumns,
                                            "successCount":self.successCount,
                                            "errorCount":self.errorCount,
                                            "process":self.process,
                                            "basepath":self.absoluteAttachmentsBasepath,
                                            "sourceIdentifierIndex":sourceIdentifierColumn,
                                            "targetIdentifierIndex":targetIdentifierColumn,
                                            "targetVersionIndex":targetVersionColumn,
                                            "csvData":self.csvArray,
                                            "ebi":self.ebiScriptObject,
                                            "equella":tle,
                                            }
                except:
                    if self.debug:
                        exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
                        scriptErrorMsg = "An error occured in the End Script:\n" + ''.join(traceback.format_exception(exceptionType, exceptionValue, exceptionTraceback))
                        self.echo(time.strftime("%H:%M:%S: ", time.localtime(time.time())) + scriptErrorMsg, style=2)
                    else:
                        exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
                        formattedException = "".join(traceback.format_exception_only(exceptionType, exceptionValue))[:-1]
                        scriptErrorMsg = "An error occured in the End Script:\n%s (line %s)" % (formattedException, traceback.extract_tb(exceptionTraceback)[-1][1])
                        self.echo(time.strftime("%H:%M:%S: ", time.localtime(time.time())) + scriptErrorMsg, style=2)  
                
                
        
            # output receipts if Item ID column specified and real run
            if itemIdColumn != -1:
                
                self.echo(time.strftime("%H:%M:%S: ", time.localtime(time.time())) + "Writing receipts file...")
            
                # create receipts folder if one doesn't exist
                if not os.path.exists(self.receiptFolder):
                    os.makedirs(self.receiptFolder)
                    
                # open csv writer and output orginal csv rows using self.columnHeadings as first row (instead of first row of self.csvArray)
                f = open(receiptFilename, "wb")
                writer = UnicodeWriter(f, self.encoding)
                writer.writerow(list(self.columnHeadings))
                for i in range(1, len(self.csvArray)):
                    writer.writerow(list(self.csvArray[i]))
                f.close()
                
        else:
            # export
            actionString = ""
            if sourceIdentifierColumn == -1 and targetIdentifierColumn == -1:
                if self.includeNonLive:
                    actionString = "Options -> Include non-live items in export"
            if actionString != "":
                self.echo(time.strftime("%H:%M:%S: ", time.localtime(time.time())) + actionString)            
            
            self.exportedFiles = []
            self.exportCSV(owner,
                           self.tle,
                           itemdefuuid,
                           self.collectionIDs,
                           testOnly,
                           scheduledRows,
                           sourceIdentifierColumn,
                           targetIdentifierColumn,
                           targetVersionColumn,
                           commandOptionsColumn,
                           attachmentLocationsColumn,
                           collectionColumn,
                           rowsToBeProcessedCount)
            

        # form outcome report
        errorReport = ""
        if self.errorCount > 0:
            errorReport = " errors: %s" % (self.errorCount)
        resultReport = "Processing complete (success: %s%s)" % (self.successCount, errorReport)
        
        self.echo(time.strftime("%H:%M:%S: ", time.localtime(time.time())) + resultReport)
        
        owner.mainStatusBar.SetStatusText(resultReport, 0)
             
                    
                        
    # getEquellaResourceDetail() retrieves an item or item attachment details necessary for forming an EQUELLA resource-type attachment
    def getEquellaResourceDetail(self, resourceUrl, itemdefuuid, collectionIDs, sourceIdentifierColumn, isCalHolding):

        # break up resource url
        resourceUrlParts = []
        if resourceUrl[0] == "[" or resourceUrl[0] == "{":
            if resourceUrl[-1] == "}":
                resourceUrlParts.append(resourceUrl)
            elif resourceUrl[-2:-1] == "}/":
                resourceUrlParts.append(resourceUrl[:-1])
            else:
                resourceUrlParts.append(resourceUrl.split("}/")[0] + "}")
                resourceUrlParts += resourceUrl.split("}/")[1].split("/")
        else:
            resourceUrlParts = resourceUrl.split("/")
        
        # get item UUID
        resourceItemUuid = resourceUrlParts[0]
        
        # check if itemUUID is actually a sourceIdentifier
        # format is {<source identifier>} or [<collection name>]{<source identifier>} or [<collection name>||<source identifier xpath>]{<source identifier>}
        collection = ""
        sourceIdentifier = ""
        sourceIdentifierXpath = ""
        
        # no collection specified so use same collection as item
        if resourceItemUuid[0] == "{" and resourceItemUuid[-1] == "}":
            sourceIdentifier = resourceItemUuid[1:-1]
            
        # collection specified so resolve to colleciton ID and use that
        if resourceItemUuid[0] == "[" and resourceItemUuid[-1] == "}":
            collSplitPoint = resourceItemUuid.find("]{")
            if collSplitPoint != -1:
                sourceIdentifier = resourceItemUuid[collSplitPoint + 2:-1]
                collection = resourceItemUuid[1:collSplitPoint]
                
                # extract an xpath and a source identifier xpath (if one supplied)
                collectionParts = collection.split("][")
                collection = collectionParts[0]
                if len(collectionParts) == 2:
                    sourceIdentifierXpath = collectionParts[1]
                    
                # get collection ID for collection
                if collection in collectionIDs:
                    itemdefuuid = collectionIDs[collection]
                else:
                    raise Exception, "Collection specified not found: " + collection
        
        # if source identifer (and optionally collection) specified then find resource by that 
        if sourceIdentifier != "":
            
            # first try checking any source identifiers that were processed in the run
            if collection == "" and sourceIdentifier in self.sourceIdentifierReceipts:
                resourceItemUuid = self.sourceIdentifierReceipts[sourceIdentifier][0]

            # if source identifer not processed in this run then look it up in EQUELLA
            else:
                if self.debug:
                    self.echo("    Source identifier = " + sourceIdentifier)
                
                if sourceIdentifierXpath == "":
                    if sourceIdentifierColumn != -1:
                    
                        # determine source identifier xpath if not specified in resource URL
                        sourceIdentifierXpath = "/xml/" + self.columnHeadings[sourceIdentifierColumn]
                        
                    else:
                        raise Exception, "No source identifier specified."
                    
                searchFilter = sourceIdentifierXpath + "='" + sourceIdentifier + "'"
                results = self.tle.search(0, 10, '/item/name', [itemdefuuid], searchFilter, query='')

                # if any matches get first matching item for editing
                if int(results.getNode("available")) > 0:
                    resourceItemUuid = results.getNode("result/xml/item/@id")
                    if self.debug:
                        self.echo("  Resource item found by source identifier = '%s' in collectionID = '%s' (%s)" % (sourceIdentifier, itemdefuuid, resourceItemUuid)) 
                else:
                    raise Exception, "Item not found with source identifier '%s'" % sourceIdentifier

            
        # get item version
        if len(resourceUrlParts) == 1:
            resourceItemVersion = 0
        elif resourceUrlParts[1] == "":
            resourceItemVersion = 0
        else:    
            resourceItemVersion = int(resourceUrlParts[1])
        
        # get attachment path if any
        attachmentPath = ""
        if len(resourceUrlParts) > 2:
            attachmentPath = "/".join(resourceUrlParts[2:])
        
        # retrieve item XML and get attachment UUID and description
        resourceXml= self.tle.getItem(resourceItemUuid, resourceItemVersion)
        resourceAttachmentUuid = ""
        if attachmentPath == "":
            # resource is item itself
            resourceName = resourceXml.getNode("item/name")
            
            # if resource is CAL holding then use explicit item version
            if isCalHolding:
                resourceItemVersion = resourceXml.getNode("item/@version")
        else:
            if attachmentPath.upper() == "<PACKAGE>":
                # get package details
                # try for SCORM package
                for attachmentSubtree in resourceXml.iterate("item/attachments/attachment"):
                    if attachmentSubtree.getNode("@type") == "custom" and attachmentSubtree.getNode("type") == "scorm":
                        resourceAttachmentUuid = attachmentSubtree.getNode("uuid")
                        resourceName = attachmentSubtree.getNode("description")
                        break
                if resourceAttachmentUuid == None or resourceAttachmentUuid == "":
                    # no SCORM package so try for IMS package
                    resourceAttachmentUuid = resourceXml.getNode("item/itembody/packagefile/@uuid")
                    resourceName = resourceXml.getNode("item/itembody/packagefile")
                    if resourceAttachmentUuid == None:
                        raise Exception, "package not found in item %s/%s" % (resourceItemUuid, resourceItemVersion)
            else:
                # resource is a file/url attachment
                for attachmentSubtree in resourceXml.iterate("item/attachments/attachment"):
                    if attachmentSubtree.getNode("file") == attachmentPath:
                        resourceAttachmentUuid = attachmentSubtree.getNode("uuid")
                        resourceName = attachmentSubtree.getNode("description")
                        break
                if resourceAttachmentUuid == "":
                    raise Exception, "%s not found in item %s/%s" % (attachmentPath, resourceItemUuid, resourceItemVersion)
        
        return resourceItemUuid, resourceItemVersion, resourceAttachmentUuid, resourceName
 
    # addCALRelations() adds CAL holding relations to a CAL portion item
    def addCALRelations(self, holdingMetadataTarget, itemXml):       
        holdingAttachmentUUIDs = itemXml.getNodes(holdingMetadataTarget)
        if len(holdingAttachmentUUIDs) > 0:
            holdingAttachmentFound = False
            for attachment in itemXml.iterate("item/attachments/attachment"):
                if attachment.getNode("uuid") == holdingAttachmentUUIDs[0]:
                    relation = itemXml.newSubtree("item/relations/targets/relation")
                    relation.createNode("@resource", attachment.getNode("uuid"))
                    relation.createNode("@type", "CAL_HOLDING")
                    relationitem = relation.newSubtree("item")
                    relationitem.createNode("name", attachment.getNode("description"))

                    holdingUuid = ""
                    holdingVersion = ""
                    for attachmentAttribute in attachment.iterate("attributes/entry"):
                        entryName = attachmentAttribute.getNode("string")
                        if entryName == "uuid":
                            holdingUuid = attachmentAttribute.getNodes("string")[1]
                        if entryName == "version":
                            holdingVersion = attachmentAttribute.getNode("int")                    

                    relationitem.createNode("@uuid", holdingUuid)
                    relationitem.createNode("@version", holdingVersion)
                    holdingAttachmentFound = True
                    break
            if not holdingAttachmentFound:
                raise Exception, "No holding item attached to this portion"
        else:
            raise Exception, "No metadata targets for holding items found in this portion"


    # processRow() creates a single item in EQUELLA based on one row of metadata
    def processRow(self,
                   rowCounter,
                   meta,
                   tle,
                   itemdefuuid,
                   collectionIDs,
                   testOnly,
                   sourceIdentifierColumn,
                   targetIdentifierColumn,
                   targetVersionColumn,
                   commandOptionsColumn,
                   attachmentLocationsColumn,
                   urlsColumn,
                   resourcesColumn,
                   customAttachmentsColumn,
                   collectionColumn,
                   thumbnailsColumn,
                   selectedThumbnailColumn,
                   ownerColumn,
                   collaboratorsColumn):
                       

        # unzipAttachment attachs and unzips an attachment and sets start pages based on tuple of tuples formatted attachment name
        def unzipAttachment():
            self.echo("    Unzip file")
            if not testOnly:
                attemptingUpload = True
                item.attachFile('_zips/' + filename, file(filepath, "rb"), uploadStatus, self.chunkSize)
                if self.StopProcessing:
                    return
                attemptingUpload = False
                wx.GetApp().Yield()
                item.unzipFile('_zips/' + filename, filename)

            if attachmentLinkName != "":
                # 
                try:
                    # read the attachment link name in as a tuple of tuples using exec()
                    # add a superfluous tuple to coax the string into a tuple of tuples even if only one tuple
                    startPagesListAsString = "((\"#####\",\"#####\")," + attachmentLinkName[1:]
                    exec "startPagesList = " + startPagesListAsString  in globals(), locals()

                except:
                    raise Exception, "List of links to unzipped files incorrectly formatted."

                # populate a dictionary rendition of the Start Pages List
                startPagesDict = {}
                for startPage in startPagesList:
                    if startPage[0] != "#####":
                        startPagesDict[startPage[0]] = startPage[1]

                # iterate through Start Pages List
                for startPage in startPagesList:
                    
                    # check if start page for zip itself
                    if startPage[0] == filename:
                        
                        # generate attachment UUID
                        attachmentUUID = str(uuid.uuid4())
                        
                        # add attachment element
                        item.addStartPage(startPage[1], "_zips/" + filename, filesize, attachmentUUID)
                        
                        # add corresponding metadata target for attachment
                        if self.attachmentMetadataTargets:
                            item.getXml().createNode(self.columnHeadings[n], attachmentUUID)
                        
                        
                    # check if wildcard exists
                    elif startPage[0] == "*":
                        for archiveFile in zfobj.namelist():
                            
                            # check if file not already specified, not zip itself and not a folder
                            if (archiveFile not in startPagesDict) and (archiveFile != filename) and not archiveFile.endswith("/"):
                                # get file size
                                archiveFilesize = zfobj.getinfo(archiveFile).file_size
                                
                                # generate attachment UUID
                                attachmentUUID = str(uuid.uuid4())
                                
                                # add attachment element
                                item.addStartPage(os.path.basename(archiveFile), filename + "/" + archiveFile, archiveFilesize, attachmentUUID)

                                # add corresponding metadata target for attachment
                                if self.attachmentMetadataTargets:
                                    item.getXml().createNode(self.columnHeadings[n], attachmentUUID)
                                
                    
                    # not the zip itself or a wildcard so name as specified
                    elif startPage[0] in startPagesDict:
                        # get file size
                        archiveFilesize = zfobj.getinfo(startPage[0]).file_size
                        
                        # generate attachment UUID
                        attachmentUUID = str(uuid.uuid4())
                        
                        # add attachment element
                        item.addStartPage(startPage[1], filename + "/" + startPage[0], archiveFilesize, attachmentUUID)

                        # add corresponding metadata target for attachment
                        if self.attachmentMetadataTargets:
                            item.getXml().createNode(self.columnHeadings[n], attachmentUUID)
                        

        failCount = 0
        retriesDone = False
        
        # loop for retrying if network errors occur
        while not retriesDone: 
            try:
                
                wx.GetApp().Yield()
                createNewItem = True
                createNewVersion = False
                allRowsError = False
                itemID = "nil"
                itemVersion = 0
                savedItemID = ""        
                savedItemVersion = ""
                n = -1
                attemptingUpload = False
                imsmanifest = None
                        
                if self.Skip:
                    self.echo("  Row skipped")
                    return "", "", "", []              
                
                # resolve owner to an ID
                ownerUsername = meta[ownerColumn].strip()
                ownerID = ""
                if ownerColumn != -1 and ownerUsername != "":
                    self.echo("  Owner: " + ownerUsername)
                    try:
                        matchingUsers = self.tle.searchUsersByGroup("", ownerUsername)
                    except:
                        error = str(sys.exc_info()[1])
                        if error.rfind('HTTP') != -1 and  error.rfind('404') != -1:
                            self.echo("  ERROR: Cannot use Owner or Collaborators column datatypes with this version of EQUELLA", style=2)
                            allRowsError = True
                        raise Exception, error
                    
                    matchingUserNodes = matchingUsers.getNodes("user", False)

                    # if any matches get first matching user
                    if len(matchingUserNodes) > 0:
                        ownerID = matchingUserNodes[0].getElementsByTagName("uuid")[0].firstChild.nodeValue
                    elif self.useEBIUsername:
                        ownerColumn = -1
                        self.echo("  '%s' not found so ignoring." % (ownerUsername, self.username))
                    else:
                        if self.saveNonexistentUsernamesAsIDs:
                            ownerID = ownerUsername
                        else:
                            raise Exception, "'%s' not found so cannot set owner." % ownerUsername                    
                
                # resolve collaborators to IDs
                collaboratorIDs = []
                if collaboratorsColumn != -1 and meta[collaboratorsColumn].strip() != "":
                    # check if this column is a multi-value column
                    if self.currentColumns[collaboratorsColumn][self.COLUMN_DELIMITER].strip() != "":
                        # column is a multi-value column
                        actualDelimiter = self.currentColumns[collaboratorsColumn][self.COLUMN_DELIMITER].strip()
                    else:
                        # column is NOT a multi-value column
                        actualDelimiter = "@~@~@~@~@~@~@"
                        
                    specifiedCollaborators = meta[collaboratorsColumn].split(actualDelimiter)           
                    self.echo("  Collaborators: " + ",".join(specifiedCollaborators))
                    for specifiedCollaborator in specifiedCollaborators:
                        try:
                            matchingUsers = self.tle.searchUsersByGroup("", specifiedCollaborator.strip())
                        except:
                            error = str(sys.exc_info()[1])
                            if error.rfind('HTTP') != -1 and  error.rfind('404') != -1:
                                self.echo("  ERROR: Cannot use Owner or Collaborators column datatypes with this version of EQUELLA", style=2)
                                allRowsError = True
                            raise Exception, error                        
                        matchingUserNodes = matchingUsers.getNodes("user", False)

                        # if any matches get first matching user
                        if len(matchingUserNodes) > 0:
                            collaboratorID = matchingUserNodes[0].getElementsByTagName("uuid")[0].firstChild.nodeValue
                            collaboratorIDs.append(collaboratorID)
                        elif self.ignoreNonexistentCollaborators:
                            self.echo("  '%s' not found so ignoring that collaborator." % specifiedCollaborator.strip())
                        else:
                            if self.saveNonexistentUsernamesAsIDs:
                                collaboratorIDs.append(specifiedCollaborator)
                            else:
                                raise Exception, "'%s' not found so cannot set collaborators." % specifiedCollaborator.strip()
                        
                # get command options
                commandOptions = []
                if commandOptionsColumn != -1:
                    
                    # get position of command options column
                    tempCommandOptions = [commandOption.strip().upper() for commandOption in meta[commandOptionsColumn].split(",")]
                    for commandOption in tempCommandOptions:
                        if commandOption != "":
                            commandOptions.append(commandOption)
                    if len(commandOptions) > 0:
                        self.echo("  Command options: " + ",".join(commandOptions))
                        
                # get targeted item version if target version specified
                if targetVersionColumn != -1 and meta[targetVersionColumn].strip() != "":
                    try:
                        itemVersion = int(meta[targetVersionColumn].strip())
                        if itemVersion < -1:
                            raise Exception, "Invalid item version specified"
                    except:
                        raise Exception, "Invalid item version specified"

                # if Source Identifier column specified check if item exists by sourceIdentifier
                if sourceIdentifierColumn != -1:
                    sourceIdentifier = meta[sourceIdentifierColumn].strip()
                    self.echo("  Source identifier = " + sourceIdentifier)
                    if sourceIdentifier.find("'") != -1:
                        raise Exception, "Source identifier cannot contain apostrophes"
                    if targetVersionColumn != -1 and meta[targetVersionColumn].strip() != "":
                        self.echo("  Target version = " + meta[targetVersionColumn].strip())
                    searchFilter = "/xml/" + self.columnHeadings[sourceIdentifierColumn] + "='" + sourceIdentifier + "'"
                    
                    if itemVersion != 0:
                        onlyLive = False
                        limit = 50
                    else:
                        onlyLive = True
                        limit = 1
                    
                    results = tle.search(0, limit, '/item/name', [itemdefuuid], searchFilter, query='', onlyLive=onlyLive)
                    
                    # if any matches get first matching item for editing
                    if int(results.getNode("available")) > 0:
                        
                        if itemVersion == 0:
                            # get first live version
                            itemID = results.getNode("result/xml/item/@id")
                            itemVersion = results.getNode("result/xml/item/@version")
                        else:
                            if itemVersion != -1:
                                # find item by item version
                                itemFound = False
                                for itemResult in results.iterate("result"):
                                    if itemResult.getNode("xml/item/@version") == str(itemVersion):
                                        itemID = itemResult.getNode("xml/item/@id")
                                        itemFound = True
                                        break
                                if not itemFound:
                                    raise Exception, "Item not found"
                            else:
                                # find item with highest version
                                highestVersionFound = 0
                                for itemResult in results.iterate("result"):
                                    if int(itemResult.getNode("xml/item/@version")) > highestVersionFound:
                                        highestVersionFound = int(itemResult.getNode("xml/item/@version"))
                                        itemID = itemResult.getNode("xml/item/@id")
                                        itemVersion = highestVersionFound
                                
                        self.echo("  Item exists in EQUELLA (" + itemID + "/" + str(itemVersion) + ")") 
                        createNewItem = False          
                    else:
                        if itemVersion == 0 or itemVersion == -1:
                            self.echo("  Item not found")
                        else:
                            raise Exception, "Item not found"
                else:
                    # if Target Identifier column specified edit item by ID (using latest version of item)
                    if targetIdentifierColumn != -1 and meta[targetIdentifierColumn].strip() != "":
                        itemID = meta[targetIdentifierColumn].strip()
                        
                        self.echo("  Target identifier = " + itemID)
                        if targetVersionColumn != -1 and meta[targetVersionColumn].strip() != "":
                            self.echo("  Target version = " + meta[targetVersionColumn].strip())                        
                        
                        # try getting item
                        foundItem = tle.getItem(itemID, itemVersion)
                        
                        self.echo("  Item exists in EQUELLA (" + itemID + "/" + foundItem.getNode("item/@version") + ")")
                        createNewItem = False

                if "DELETE" in commandOptions:
                    # check that if using target identifiers is specified that this row has one
                    if targetIdentifierColumn != -1 and meta[targetIdentifierColumn].strip() == "" and sourceIdentifierColumn == -1:
                        raise Exception, "Neither source identifer nor target identifier supplied"
                    
                    # run Row Pre-Script
                    if self.preScript.strip() != "":
                        try:
                            exec self.preScript in {
                                                    "IMPORT":0,
                                                    "EXPORT":1,
                                                    "NEWITEM":0,
                                                    "NEWVERSION":1,
                                                    "EDITITEM":2,
                                                    "DELETEITEM":3,
                                                    "mode":0,                                                    
                                                    "action":3,
                                                    "vars":self.scriptVariables,
                                                    "rowData":meta,
                                                    "rowCounter":rowCounter,
                                                    "testOnly": testOnly,
                                                    "institutionUrl":tle.institutionUrl,
                                                    "collection":self.collection,
                                                    "csvFilePath":self.csvFilePath,
                                                    "username":self.username,
                                                    "logger":self.logger,
                                                    "columnHeadings":self.columnHeadings,
                                                    "columnSettings":self.currentColumns,
                                                    "successCount":self.successCount,
                                                    "errorCount":self.errorCount,
                                                    "process":self.process,
                                                    "basepath":self.absoluteAttachmentsBasepath,
                                                    "sourceIdentifierIndex":sourceIdentifierColumn,
                                                    "targetIdentifierIndex":targetIdentifierColumn,
                                                    "targetVersionIndex":targetVersionColumn,
                                                    "csvData":self.csvArray,
                                                    "ebi":self.ebiScriptObject,
                                                    "equella":tle,                                                 
                                                    }
                        except:
                            if self.debug:
                                raise
                            else:
                                exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
                                formattedException = "".join(traceback.format_exception_only(exceptionType, exceptionValue))[:-1]
                                scriptErrorMsg = "An error occured in the Row Pre-Script:\n%s (line %s)" % (formattedException, traceback.extract_tb(exceptionTraceback)[-1][1])
                                raise Exception, scriptErrorMsg 
                                                    
                    if not createNewItem:
                        if not testOnly:
                            # delete existing item
                            tle._forceUnlock(itemID, itemVersion)
                            tle._deleteItem(itemID, itemVersion)
                            self.echo("  Item successfully deleted")
                            
                            savedItemID = itemID
                            savedItemVersion = itemVersion
                        else:
                            self.echo("  Item valid to delete")

                    self.successCount += 1
                    
                else:
                    scriptAction = 0
                    
                    # create new item or prepare existing one
                    if createNewItem:
                        # get collection ID
                        collectionID = itemdefuuid
                        
                        # override the collection ID if one has been specified in the row
                        if collectionColumn != -1:
                            collectionName = meta[collectionColumn].strip()
                            if collectionName != "":
                                collectionID = collectionIDs[collectionName]
                                self.echo("  Target collection: '%s'" % collectionName)
                            
                        item = tle.createNewItem(collectionID)
                        itemID = item.uuid
                        itemVersion = item.version
                        item.prop.setNode("item/thumbnail", "default")
                    else:
                        if self.createNewVersions or "VERSION" in commandOptions:
                            # create new version
                            item = tle.newVersionItem(itemID, itemVersion)
                            createNewVersion = True
                            scriptAction = 1
                            self.echo("  Creating new version")
                        else:
                            # open existing version for editing
                            tle._forceUnlock(itemID, itemVersion)
                            item = tle.editItem(itemID, itemVersion, 'true')
                            scriptAction = 2
                            self.echo("  Editing item")

                        if collectionColumn != -1 and meta[collectionColumn].strip() != "":
                            self.echo("  Target collection: '%s'. Cannot use target collection for existing items (ignoring)" % meta[collectionColumn].strip())
                                                        
                        # delete all attachments if hyperlinks column or attachments column specified
                        if (urlsColumn != -1 or attachmentLocationsColumn != -1 or resourcesColumn != -1 or customAttachmentsColumn != -1) and \
                        not self.appendAttachments and not 'APPENDATTACH' in commandOptions:

                            # delete attachments
                            item.deleteAttachments()                    

                            # remove any possible package link and navigation nodes
                            item.prop.removeNode("item/itembody/packagefile")
                            item.prop.removeNode("item/navigationNodes/node")
                            
                        # delete all existing custom metadata
                        if self.existingMetadataMode not in [self.REPLACEMETA, self.APPENDMETA] and 'APPENDMETA' not in commandOptions and 'REPLACEMETA' not in commandOptions:
                            for childNode in item.prop.root.childNodes:
                                if childNode.nodeName == "item":
                                    for itemChildNode in childNode.childNodes:
                                        if itemChildNode.nodeName not in self.itemSystemNodes:
                                            childNode.removeChild(itemChildNode)
                                else:
                                    item.prop.root.removeChild(childNode)
                        else:
                           # appending metadata but still delete source identifier node to avoid duplication
                            if sourceIdentifierColumn != -1:
                                # check that it is not an attribute
                                if "@" not in self.columnHeadings[sourceIdentifierColumn]:
                                    item.getXml().removeNode(self.columnHeadings[sourceIdentifierColumn])

                    # run Row Pre-Script
                    if self.preScript.strip() != "":
                        try:
                            exec self.preScript in {
                                                    "IMPORT":0,
                                                    "EXPORT":1,
                                                    "NEWITEM":0,
                                                    "NEWVERSION":1,
                                                    "EDITITEM":2,
                                                    "DELETEITEM":3,
                                                    "mode":0,
                                                    "action":scriptAction,
                                                    "vars":self.scriptVariables,
                                                    "rowData":meta,
                                                    "rowCounter":rowCounter,
                                                    "testOnly": testOnly,
                                                    "institutionUrl":tle.institutionUrl,
                                                    "collection":self.collection,
                                                    "csvFilePath":self.csvFilePath,
                                                    "username":self.username,
                                                    "logger":self.logger,
                                                    "itemId":itemID,
                                                    "itemVersion":itemVersion,                                                    
                                                    "xml":item.prop,
                                                    "xmldom":item.newDom,
                                                    "columnHeadings":self.columnHeadings,
                                                    "columnSettings":self.currentColumns,
                                                    "successCount":self.successCount,
                                                    "errorCount":self.errorCount,
                                                    "process":self.process,
                                                    "basepath":self.absoluteAttachmentsBasepath,
                                                    "sourceIdentifierIndex":sourceIdentifierColumn,
                                                    "targetIdentifierIndex":targetIdentifierColumn,
                                                    "csvData":self.csvArray,
                                                    "ebi":self.ebiScriptObject,
                                                    "equella":tle,                                                  
                                                    }
                        except:
                            if self.debug:
                                raise
                            else:
                                exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
                                formattedException = "".join(traceback.format_exception_only(exceptionType, exceptionValue))[:-1]
                                scriptErrorMsg = "An error occured in the Row Pre-Script:\n%s (line %s)" % (formattedException, traceback.extract_tb(exceptionTraceback)[-1][1])
                                raise Exception, scriptErrorMsg 
                        
                            
                           
                    # process the contents of attachmentMetadataColumn for any {uuid) placeholders
                    attachmentUUIDPlaceholders = {}
                                    
                    hyperlinkColumnCount = 0
                    attachmentColumnCount = 0
                    equellaResourceColumnCount = 0
                    calHoldingMetadataTarget = ""
                    thumbnailSelected = False
                    
                    # get thumbnail settings for row if any
                    thumbnails = []
                    selectedThumbnail = ""
                    if thumbnailsColumn != -1:
                        thumbnailDelimiter = self.currentColumns[thumbnailsColumn][self.COLUMN_DELIMITER].strip()
                        if thumbnailDelimiter != "":
                            thumbnails = meta[thumbnailsColumn].split(thumbnailDelimiter)
                            thumbnails = [thumb.strip() for thumb in thumbnails]
                        else:
                            thumbnails = meta[thumbnailsColumn].strip()
                    if selectedThumbnailColumn != -1:
                        selectedThumbnail = meta[selectedThumbnailColumn].strip()
                    
                    # iterate through the columns of the CSV row
                    for n in range(0, len(meta)):
                        wx.GetApp().Yield()
                        if self.StopProcessing:
                            break
        
                        isMetadataField = True
        
                        # check if this column is a multi-value column
                        if self.currentColumns[n][self.COLUMN_DELIMITER].strip() != "":
                            # column is a multi-value column
                            actualDelimiter = self.currentColumns[n][self.COLUMN_DELIMITER].strip()
                        else:
                            # column is NOT a multi-value column
                            actualDelimiter = "@~@~@~@~@~@~@"

        
                        # add hyperlink from csv
                        if self.currentColumns[n][self.COLUMN_DATATYPE] == self.URLS:
                            
                            hyperlinkColumnCount += 1
                            
                            isMetadataField = False
                            
                            # delete all url metadata targets if first occurence
                            if self.attachmentMetadataTargets:
                                if self.columnHeadings[:n].count(self.columnHeadings[n]) == 0:
                                    item.getXml().removeNode(self.columnHeadings[n])                            
        
                            # split for multi-value field
                            values = meta[n].split(actualDelimiter)
                            for i in range(len(values)):
                                if values[i].strip() != "":
                                    url = unicode(values[i].replace(" ", "%20"))
        
                                    self.echo("  Hyperlink: " + url)
                                    
                                    # find corresponding Hyperlink Name column for URL Location column
                                    hyperlinkName = ""                                    
                                    hyperlinkNameColumnCount = 0
                                    for col in range(0, len(meta)):
                                        if self.currentColumns[col][self.COLUMN_DATATYPE] == self.HYPERLINKNAMES:
                                            
                                            hyperlinkNameColumnCount += 1
        
                                            if hyperlinkNameColumnCount == hyperlinkColumnCount:
                                                # split for multi-value field
                                                names = meta[col].split(actualDelimiter)
                
                                                # match name[i] to value[i] but check for array out of bounds
                                                if i < len(names):
                                                    if names[i].strip() != "":
                                                        # add start page with attachment name
                                                        hyperlinkName = names[i]
                                                break
                                            
                                    # generate uuid for URL's attachment element
                                    attachmentUUID = str(uuid.uuid4())                                   
        
                                    # add start page after checking if a hyperlink name has been specified
                                    if hyperlinkName != "":
                                        item.addUrl(hyperlinkName, url, attachmentUUID)
                                    else:
                                        # add start page WITHOUT hyperlink name
                                        item.addUrl(url, url, attachmentUUID)
                                        
                                    # add metadata target for remote attachment
                                    if self.attachmentMetadataTargets:
                                        if self.columnHeadings[n].strip() != "" and self.columnHeadings[n][:1] != "#":
                                            item.getXml().createNode(self.columnHeadings[n], attachmentUUID)                                        
        
                        # add attachment from csv
                        if self.currentColumns[n][self.COLUMN_DATATYPE] == self.ATTACHMENTLOCATIONS:
                            
                            attachmentColumnCount += 1
        
                            isMetadataField = False
                            
                            # delete all attachment metadata targets if this is the first occurence
                            if self.attachmentMetadataTargets:
                                if self.columnHeadings[:n].count(self.columnHeadings[n]) == 0:
                                    item.getXml().removeNode(self.columnHeadings[n])
                            
                            # split for multi-value field
                            values = meta[n].split(actualDelimiter)
                            for i in range(len(values)):
                                if values[i].strip() != "":
        
                                    # get absolute path to file
                                    filepath = os.path.join(self.absoluteAttachmentsBasepath, values[i])
                                    
                                    # ensure that attachment specified is not a directory
                                    if os.path.isdir(filepath):
                                        raise Exception, filepath + " is not a file"
                                    
                                    # get filename and file size
                                    filename = os.path.basename(filepath)
                                    filesize = os.path.getsize(filepath)
                                    
                                    uploadStatus = "   "
        
                                    # find corresponding Attachment Name column for Attachment Location column
                                    attachmentLinkName = ""                                    
                                    attachmentNameColumnCount = 0
                                    for col in range(0, len(meta)):
                                        if self.currentColumns[col][self.COLUMN_DATATYPE] == self.ATTACHMENTNAMES:
                                            
                                            attachmentNameColumnCount += 1
        
                                            if attachmentNameColumnCount == attachmentColumnCount:
                                                # split for multi-value field
                                                names = meta[col].split(actualDelimiter)
                
                                                # match name[i] to value[i] but check for array out of bounds
                                                if i < len(names):
                                                    if names[i].strip() != "":
                                                        # add start page with attachment name
                                                        attachmentLinkName = names[i]
                                                break
        
                                    # echo out attachment information including start page link
                                    attachmentLinkNameDisplay = ""
                                    if self.debug and attachmentLinkName != "":
                                        attachmentLinkNameDisplay = ' -> "' + attachmentLinkName + '"'
                                    filesizeDisplay = self.group(filesize)
                                    if filesize > 999999 and not self.debug:
                                        filesizeDisplay = filesizeDisplay[:-8] + "." + filesizeDisplay[-7:-5] + " MB"
                                    else:
                                        filesizeDisplay += " bytes"
                                    self.echo("  Attachment: " + filename + " (" + filesizeDisplay + ")" + attachmentLinkNameDisplay)
                                    
                                    # process command options
                                    attachmentType = self.attachmentTypeFile
                                    if ("UNZIP" in commandOptions or "IMS" in commandOptions or "SCORM" in commandOptions or "AUTO" in commandOptions):
        
                                        # check if zip file by extension
                                        if (os.path.splitext(filename)[1].upper() == ".ZIP"):
                                            self.echo("    Attachment is a zip file")
                                            zfobj = zipfile.ZipFile(filepath)
        
                                            # check if commands are either IMS, SCORM or AUTO
                                            if ("IMS" in commandOptions or "SCORM" in commandOptions or "AUTO" in commandOptions):
                                                if ("imsmanifest.xml" in zfobj.namelist()):
                                                    imsmanifest = PropBagEx(zfobj.read("imsmanifest.xml").decode("utf8"))
                                                    self.echo("    IMS manifest found, treat as IMS package")
                                                        
                                                    # generate UUID for IMS package
                                                    attachmentUUID = str(uuid.uuid4())
                                                    
                                                    # add metadata target for attachment
                                                    if self.attachmentMetadataTargets:
                                                        
                                                        # only add an attachment metadata target if the column is neither blank nor starts with a "#"
                                                        if self.columnHeadings[n].strip() != "" and self.columnHeadings[n][:1] != "#":
                                                            item.getXml().createNode(self.columnHeadings[n], attachmentUUID) 
                                                    
                                                    # use filename for IMS/SCORM attachment's description node if no Attachment Name supplied
                                                    if attachmentLinkName == "":
                                                        attachmentLinkName = filename
                                                    
                                                    if ("IMS" in commandOptions or "AUTO" in commandOptions):

                                                        # attach IMS package
                                                        attemptingUpload = True
                                                        
                                                        # if imsmanifest indicates that package is a SCORM package then attach as a SCORM package
                                                        if self.scormformatsupport and imsmanifest.getNode("metadata/schema") == "ADL SCORM":
                                                            self.echo("    Package is a SCORM package")
                                                            item.attachSCORM(file(filepath, "rb"), filename, attachmentLinkName, uploadStatus, not testOnly, filesize, attachmentUUID, self.chunkSize)
                                                        else:
                                                            item.attachIMS(file(filepath, "rb"), filename, attachmentLinkName, uploadStatus, not testOnly, filesize, attachmentUUID, self.chunkSize)
                                                        attemptingUpload = False
                                                        
                                                        attachmentType = self.attachmentTypeIMS
                                                        
                                                    if "SCORM" in commandOptions:
                                                        attemptingUpload = True
                                                        item.attachSCORM(file(filepath, "rb"), filename, attachmentLinkName, uploadStatus, not testOnly, filesize, attachmentUUID, self.chunkSize)
                                                        attemptingUpload = False
                                                        
                                                        attachmentType = self.attachmentTypeSCORM
        
                                                # check if command is AUTO
                                                elif ("AUTO" in commandOptions):
                                                    self.echo("    No IMS manifest found, treat as simple zip file")
        
                                                    # unzip file
                                                    unzipAttachment()
                                                    attachmentType = self.attachmentTypeZip
        
                                                # check if command is IMS
                                                elif ("IMS" in commandOptions or "SCORM" in commandOptions):
                                                    raise Exception, "No IMS manifest found, cannot use IMS or SCORM command option"                                                 
        
                                            # check if command is UNZIP
                                            elif ("UNZIP" in commandOptions):
                                                # unzip file
                                                attemptingUpload = True
                                                unzipAttachment()
                                                attemptingUpload = False
                                                attachmentType = self.attachmentTypeZip
        
                                        # file is not a zip file, check if command is AUTO
                                        elif ("AUTO" in commandOptions):
                                            if not testOnly:
                                                attemptingUpload = True
                                                item.attachFile(filename, file(filepath, "rb"), uploadStatus, self.chunkSize)
                                                attemptingUpload = False
                                            
                                            attachmentType = self.attachmentTypeFile
        
                                        # file is not a zip file but UNZIP command requested
                                        elif ("UNZIP" in commandOptions):
                                            raise Exception, "Not a zip file, cannot use UNZIP or IMS command options" 
                                    else:
                                        # no command options
                                        if not testOnly:
                                            attemptingUpload = True
                                            item.attachFile(filename, file(filepath, "rb"), uploadStatus, self.chunkSize)
                                            attemptingUpload = False
                                            
                                        attachmentType = self.attachmentTypeFile

                                    # add start page if attachment is a simple file
                                    if attachmentType == self.attachmentTypeFile:
                                        
                                        # generate uuid for attachment
                                        attachmentUUID = str(uuid.uuid4())
                                        
                                        # determine if attachment should have thumbnails suppressed
                                        thumbnail = ""
                                        if thumbnailsColumn != -1 and values[i].strip() not in thumbnails:
                                            thumbnail = "suppress"
                                            
                                            # check if custom thumbnail has been specified
                                            for thumb in thumbnails:
                                                thumbparts = thumb.split(":")
                                                if len(thumbparts) == 2:
                                                    if thumbparts[0].strip() == values[i].strip():
                                                        thumbnail = thumbparts[1].strip()
                                            
                                            # check if file extension matches a thumbnail wildcard
                                            if  "*" + os.path.splitext(filepath)[1].lower() in (wildcard.lower() for wildcard in thumbnails):
                                                thumbnail = ""
                                            
                                        if attachmentLinkName != "":
                                            # add start page with provided attachment link name
                                            item.addStartPage(attachmentLinkName, filename, filesize, attachmentUUID, thumbnail)
                                        else:
                                            # add start page using filename as attachment link
                                            item.addStartPage(filename, filename, filesize, attachmentUUID, thumbnail)
                                        
                                        # add metadata target for attachment
                                        if self.attachmentMetadataTargets:
                                            # only add an attachment metadata target if the column is neither blank nor starts with a "#"
                                            if self.columnHeadings[n].strip() != "" and self.columnHeadings[n][:1] != "#":
                                                item.getXml().createNode(self.columnHeadings[n], attachmentUUID)

                                        # check if attachment is selected thumbnail
                                        if values[i].strip() == selectedThumbnail: 
                                            item.getXml().setNode("item/thumbnail", "custom:" + attachmentUUID)
                                            thumbnailSelected = True
                                        
                                        # check if attachment extension matches selected thumbnail wildcard
                                        elif thumbnail != "suppress":
                                            if not thumbnailSelected:
                                                if  "*" + os.path.splitext(filepath)[1].lower() == selectedThumbnail:
                                                    item.getXml().setNode("item/thumbnail", "custom:" + attachmentUUID)
                                                    thumbnailSelected = True
                                                
                        # add raw files from csv
                        if self.currentColumns[n][self.COLUMN_DATATYPE] == self.RAWFILES:
                            
                            attachmentColumnCount += 1
        
                            isMetadataField = False
                            
                            # split for multi-value field
                            values = meta[n].split(actualDelimiter)
                            for i in range(len(values)):
                                if values[i].strip() != "":
        
                                    uploadStatus = "   "
                                    attachIndent = ""
        
                                    # find corresponding Attachment Name column for Attachment Location column
                                    attachmentLinkName = ""                                    
                                    attachmentNameColumnCount = 0
                                    for col in range(0, len(meta)):
                                        if self.currentColumns[col][self.COLUMN_DATATYPE] == self.ATTACHMENTNAMES:
                                            
                                            attachmentNameColumnCount += 1
        
                                            if attachmentNameColumnCount == attachmentColumnCount:
                                                # split for multi-value field
                                                names = meta[col].split(actualDelimiter)
                
                                                # match name[i] to value[i] but check for array out of bounds
                                                if i < len(names):
                                                    if names[i].strip() != "":
                                                        # add start page with attachment name
                                                        attachmentLinkName = names[i]
                                                break

                                    rawFiles = []
                                    
                                    # check if a folder rather than a file is specified
                                    if values[i].strip().endswith("*"):
                                        
                                        uploadStatus = "     "
                                        attachIndent = "  "
                                        prependFolder = ""
                                        targetDisplay = ""
                                        if attachmentLinkName != "":
                                            prependFolder = attachmentLinkName[:-1]       
                                            targetDisplay = " -> " + attachmentLinkName
                                        self.echo("  Folder: " + values[i] + targetDisplay) 
                                        
                                        # recurse through the folder adding files to be uploaded
                                        rootdir = os.path.join(self.absoluteAttachmentsBasepath, values[i]).strip()[:-2]
                                        for dirname, dirnames, filenames in os.walk(rootdir):
                                            for filename in filenames:
                                                rawFile = {}
                                                rawFile["filepath"] = os.path.join(dirname, filename)
                                                rawFile["originalfilename"] = os.path.relpath(rawFile["filepath"], rootdir)
                                                rawFile["filename"] = prependFolder + rawFile["originalfilename"]
                                                rawFile["filesize"] = os.path.getsize(rawFile["filepath"])
                                                os.path.relpath(os.path.join(dirname, filename), rootdir)
                                                rawFiles.append(rawFile)
                                        
                                    else:
                                        # a single file was specified so add that as the only file to be uploaded
                                        rawFile = {}
                                        rawFile["filepath"] = os.path.join(self.absoluteAttachmentsBasepath, values[i])

                                        # ensure that attachment specified is not a directory
                                        if os.path.isdir(rawFile["filepath"]):
                                            raise Exception, filepath + " is not a file"                                        
                                        
                                        rawFile["filename"] = os.path.basename(rawFile["filepath"])
                                        rawFile["originalfilename"] = rawFile["filename"]
                                        if attachmentLinkName != "":
                                            rawFile["filename"] = attachmentLinkName
                                        rawFile["filesize"] = os.path.getsize(rawFile["filepath"])
                                        rawFiles.append(rawFile)
                                    

                                    # upload all raw files specified
                                    for rawFile in rawFiles:
                                        
                                        # echo out attachment information including start page link
                                        attachmentLinkNameDisplay = ""
                                        if attachmentLinkName != "" and not values[i].strip().endswith("*"):
                                            attachmentLinkNameDisplay = ' -> "' + attachmentLinkName + '"'
                                        filesizeDisplay = self.group(rawFile["filesize"])
                                        if rawFile["filesize"] > 999999 and not self.debug:
                                            filesizeDisplay = filesizeDisplay[:-8] + "." + filesizeDisplay[-7:-5] + " MB"
                                        else:
                                            filesizeDisplay += " bytes"
                                        self.echo(attachIndent + "  Attachment: " + rawFile["originalfilename"] + " (" + filesizeDisplay + ")" + attachmentLinkNameDisplay)
                                    
                                        if not testOnly:
                                            attemptingUpload = True
                                            item.attachFile(rawFile["filename"], file(rawFile["filepath"], "rb"), uploadStatus, self.chunkSize)
                                            attemptingUpload = False
        
                                        
                         
                        # add EQUELLA resources
                        if self.currentColumns[n][self.COLUMN_DATATYPE] == self.EQUELLARESOURCES:

                            equellaResourceColumnCount += 1

                            isMetadataField = False
                            
                            isCalHolding = False
                            if calHoldingMetadataTarget == "" and "CAL_PORTION" in commandOptions:
                                isCalHolding = True
                                calHoldingMetadataTarget = self.columnHeadings[n]
                        
                            # delete all attachment metadata targets if this is the first occurence
                            if self.attachmentMetadataTargets:
                                if self.columnHeadings[:n].count(self.columnHeadings[n]) == 0:
                                    item.getXml().removeNode(self.columnHeadings[n])

                            # split for multi-value field
                            values = meta[n].split(actualDelimiter)
                            for i in range(len(values)):
                                if values[i].strip() != "":

                                    resourceUrl = unicode(values[i])
                                    self.echo("  EQUELLA resource: " + resourceUrl)
   
                                    resourceItemUuid, resourceItemVersion, resourceAttachmentUuid, resourceName = self.getEquellaResourceDetail(resourceUrl, itemdefuuid, collectionIDs, sourceIdentifierColumn, isCalHolding)
                                    if self.debug:
                                        self.echo("   resourceItemUuid = " + resourceItemUuid)
                                        self.echo("   resourceItemVersion = " + str(resourceItemVersion))
                                        self.echo("   resourceAttachmentUuid = " + resourceAttachmentUuid)
                                        self.echo("   resourceName = " + resourceName)
                                        
                                    # find corresponding EQUELLA Resource Name column for URL Location column
                                    equellaResourceNameColumnCount = 0
                                    for col in range(0, len(meta)):
                                        if self.currentColumns[col][self.COLUMN_DATATYPE] == self.EQUELLARESOURCENAMES:
                                            
                                            equellaResourceNameColumnCount += 1
        
                                            if equellaResourceNameColumnCount == equellaResourceColumnCount:
                                                # split for multi-value field
                                                names = meta[col].split(actualDelimiter)
                
                                                # match name[i] to value[i] but check for array out of bounds
                                                if i < len(names):
                                                    if names[i].strip() != "":
                                                        # add start page with attachment name
                                                        resourceName = names[i]
                                                break                                        
                                        
                                    # generate uuid for URL's attachment element
                                    attachmentUUID = str(uuid.uuid4())                                        
                                    
                                    # add item resource
                                    item.attachResource(resourceItemUuid, resourceItemVersion, resourceName, attachmentUUID, resourceAttachmentUuid)
                                    
                                    # add metadata target for resource
                                    if self.attachmentMetadataTargets:
                                        if self.columnHeadings[n].strip() != "" and self.columnHeadings[n][:1] != "#":
                                            item.getXml().createNode(self.columnHeadings[n], attachmentUUID)                                     

                        # process custom attachments
                        if self.currentColumns[n][self.COLUMN_DATATYPE] == self.CUSTOMATTACHMENTS and meta[n].strip() != "":

                            # form XML document from fragment (no root nodes needed in fragment)
                            xmlAttachmentElementsFragmentString = "<?xml version=\"1.0\" encoding=\"%s\"?><fragment>%s</fragment>" % (self.encoding, meta[n].strip())
                            xmlAttachmentElements = PropBagEx(xmlAttachmentElementsFragmentString.encode(self.encoding))
                            
                            # check /uuid elements for UUID placeholders
                            for attachmentElement in xmlAttachmentElements.iterate("attachment"):
                                
                                # get attachment UUID if supplied
                                attachmentUUID = attachmentElement.getNode("uuid")
                                
                                # generate an attachment UUID if one is not supplied
                                if attachmentUUID == None or attachmentUUID == "":

                                    # generate UUID
                                    attachmentUUID = str(uuid.uuid4())
                                    
                                    # replace placeholder in /uuid element with generated UUID
                                    attachmentElement.setNode("uuid", attachmentUUID)
                                    
                                    if attachmentElement.getNode("selected_thumbnail") == "true":
                                        item.getXml().setNode("item/thumbnail", "custom:" + attachmentUUID)
                                        thumbnailSelected = True
                               
                                # append to system attachments
                                item.getXml().setNode("item/attachments", "")
                                item.getXml().root.getElementsByTagName("item")[0].getElementsByTagName("attachments")[0].appendChild(attachmentElement.root.cloneNode(True))                                    
                                    
                                # add metadata target
                                if self.attachmentMetadataTargets:
                                    if self.columnHeadings[n].strip() != "" and self.columnHeadings[n][:1] != "#":
                                        item.getXml().createNode(self.columnHeadings[n], attachmentUUID)                                      
                                        
                        # process metadata field
                        if self.currentColumns[n][self.COLUMN_DATATYPE] == self.METADATA:
        
                            # check if column is flagged for XML fragments
                            if self.currentColumns[n][self.COLUMN_XMLFRAGMENT] == "YES":
                                
                                # display to log if necessary
                                if self.currentColumns[n][self.COLUMN_DISPLAY] == "YES":
                                    self.echo("  %s: %s" % (self.columnHeadings[n], meta[n].strip()))                        
        
                                if meta[n].strip() != "":
        
                                    # form XML document from fragment (no root nodes needed in fragment)
                                    xmlFragmentString = "<?xml version=\"1.0\" encoding=\"UTF-8\"?><fragment>%s</fragment>" % (meta[n])
                                    xmlFragment = PropBagEx(unicode(xmlFragmentString))
                                    
                                    # remove all indenting
                                    stripNode(xmlFragment.root, True)
        
                                    # create element if it doesn't exist
                                    if len(item.prop.getNodes(self.columnHeadings[n], False)) == 0:
                                        item.getXml().createNode(self.columnHeadings[n], "")
                                    else:
                                        # remove any xml subtrees the same name as the nodes in the fragment if first occurence
                                        if self.columnHeadings[:n].count(self.columnHeadings[n]) == 0 and self.existingMetadataMode != self.APPENDMETA and 'APPENDMETA' not in commandOptions:
                                            for child in xmlFragment.root.childNodes:                                    
                                                item.prop.removeNode(self.columnHeadings[n] + "/" + child.nodeName)
        
                                    # append xml fragment
                                    parentNode = item.prop.getNodes(self.columnHeadings[n], False)[0]
                                    for child in xmlFragment.root.childNodes:
                                        parentNode.appendChild(child.cloneNode(True))
                                else:
                                    # empty cell so clear the text of the node
                                    if self.existingMetadataMode != self.APPENDMETA and 'APPENDMETA' not in commandOptions:
                                        if len(item.prop.getNodes(self.columnHeadings[n], False)) != 0:
                                            parentNode = item.prop.getNodes(self.columnHeadings[n], False)[0]
                                            for child in parentNode.childNodes:
                                                if child.nodeType == Node.TEXT_NODE:
                                                    child.nodeValue = ""
                                                
                            # simple metadata, not an XML fragment 
                            else:
                                
                                # split for multi-value field
                                newValues = meta[n].split(actualDelimiter)
    
                                # remove existing elements if first occurence
                                if self.columnHeadings[:n].count(self.columnHeadings[n]) == 0 and self.existingMetadataMode != self.APPENDMETA and 'APPENDMETA' not in commandOptions:
                                    item.getXml().removeNode(self.columnHeadings[n])
    
                                # iterate through new values
                                for i in range(len(newValues)):
    
                                    # display to log if necessary
                                    if self.currentColumns[n][self.COLUMN_DISPLAY] == "YES":
                                        self.echo("  %s: %s" % (self.columnHeadings[n], newValues[i].strip()))

                                    # create element if not empty string
                                    if newValues[i].strip() != "":
                                        
                                        # if null specified then create empty element
                                        if newValues[i].strip().lower() == "<null>":
                                            newValues[i] = ""
                                            
                                        item.getXml().createNode(self.columnHeadings[n], unicode(newValues[i].strip()))

                        # column is set to IGNORE
                        if self.currentColumns[n][self.COLUMN_DATATYPE] == self.IGNORE:
        
                            # display to log if necessary
                            if self.currentColumns[n][self.COLUMN_DISPLAY] == "YES":
                                self.echo("  %s: %s" % (self.columnHeadings[n], meta[n].strip()))
                    
                    
                    # set selected thumbnail to none if applicable
                    if selectedThumbnail != "":
                        if selectedThumbnail.upper() == "NONE":
                            item.getXml().setNode("item/thumbnail", "none")                        
                    
                    
                    # if necesary set owner and collaborators for new items and new versions
                    if createNewVersion or createNewItem:
                        if ownerColumn != -1 and ownerUsername != "":
                            
                            # add owner to new item/version
                            item.getXml().setNode("item/owner", ownerID)

                        if collaboratorsColumn != -1:
                            
                            # NOTE: EQUELLA automatically clears out collaborators when
                            # creating new versions so this is actually unneccesary. Not
                            # actually possible to "append" collaborators to a new version.
                            if self.existingMetadataMode != self.APPENDMETA and 'APPENDMETA' not in commandOptions:
                                item.getXml().removeNode("item/collaborativeowners/collaborator")
                            
                            # add collaborators to new item/version
                            for collaboratorID in collaboratorIDs:
                                item.getXml().createNode("item/collaborativeowners/collaborator", collaboratorID)
                    
                    # ##############################
                    # submit item or cancel editing
                    # ##############################
                    n = -1
                    wx.GetApp().Yield()
                    if not self.StopProcessing:

                        savedItemID = item.getUUID()
                        savedItemVersion = item.getVersion()
                        
                        
                        # run Row Post-Script
                        if self.postScript.strip() != "":
                            try:
                                exec self.postScript in {
                                                        "IMPORT":0,
                                                        "EXPORT":1,
                                                        "NEWITEM":0,
                                                        "NEWVERSION":1,
                                                        "EDITITEM":2,
                                                        "DELETEITEM":3,
                                                        "mode":0,
                                                        "action":scriptAction,
                                                        "vars":self.scriptVariables,
                                                        "rowData":meta,
                                                        "rowCounter":rowCounter,
                                                        "testOnly": testOnly,
                                                        "institutionUrl":tle.institutionUrl,
                                                        "collection":self.collection,
                                                        "csvFilePath":self.csvFilePath,
                                                        "username":self.username,
                                                        "logger":self.logger,
                                                        "columnHeadings":self.columnHeadings,
                                                        "columnSettings":self.currentColumns,
                                                        "successCount":self.successCount,
                                                        "errorCount":self.errorCount,
                                                        "itemId":savedItemID,
                                                        "itemVersion":savedItemVersion,
                                                        "xml":item.prop,
                                                        "xmldom":item.newDom,
                                                        "process":self.process,
                                                        "basepath":self.absoluteAttachmentsBasepath,
                                                        "sourceIdentifierIndex":sourceIdentifierColumn,
                                                        "targetIdentifierIndex":targetIdentifierColumn,
                                                        "targetVersionIndex":targetVersionColumn,
                                                        "imsmanifest":imsmanifest,
                                                        "csvData":self.csvArray,
                                                        "ebi":self.ebiScriptObject,
                                                        "equella":tle,
                                                        }
                            except:
                                if self.debug:
                                    raise
                                else:
                                    exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
                                    formattedException = "".join(traceback.format_exception_only(exceptionType, exceptionValue))[:-1]
                                    scriptErrorMsg = "An error occured in the Row Post-Script:\n%s (line %s)" % (formattedException, traceback.extract_tb(exceptionTraceback)[-1][1])
                                    raise Exception, scriptErrorMsg
                                
                                                                            
                    if not self.StopProcessing and not self.Skip:

                        if testOnly:
                            # check to see if test XML files should be produced
                            if self.saveTestXML:
                                
                                # add CAL holding relations metadata if necessary
                                if calHoldingMetadataTarget != "":
                                    self.addCALRelations(calHoldingMetadataTarget, item.getXml())                                
                                
                                # create folder if one doesn't exist
                                xmlFolderName = os.path.join(self.testItemfolder, self.sessionName)
                                if not os.path.exists(xmlFolderName):
                                    os.makedirs(xmlFolderName)
                                    
                                # form filename  
                                xmlFilename = os.path.join(xmlFolderName, "ebi-%06d.xml" % rowCounter)
                                
                                # save file
                                fp = file(xmlFilename, 'w')
                                fp.write(item.newDom.toprettyxml("    ", "\n", self.encoding))
                                fp.close()
                            
                            # cancel edit (test only)
                            item.parClient._cancelEdit(item.getUUID(), item.getVersion())
                            self.echo("  Item valid for import")
                        else:
                            
                            # add CAL holding relations metadata (if necessary) prior to saving if editing existing item
                            if calHoldingMetadataTarget != "" and not (createNewItem or createNewVersion):
                                    self.addCALRelations(calHoldingMetadataTarget, item.getXml())                             
                            
                            # determine bSubmit parameter for saveItem() (controls status of item)
                            bSubmit = 0
                            statusMessage = " in draft status"
                            if (createNewItem or createNewVersion) and (not self.saveAsDraft and "DRAFT" not in commandOptions):
                                bSubmit = 1
                                statusMessage = ""
                            
                            # submit the item
                            item.submit(bSubmit)
                            
                            self.tryPausing("[Paused]")
                            
                            # update owner if one specified and existing item being edited
                            if ownerColumn != -1 and not createNewVersion and not createNewItem and ownerID != "" and ownerUsername != "":
                                
                                self.echo("  Setting owner to '%s'" % ownerUsername)
                                
                                # only update owner if different from current
                                if item.getXml().getNode("item/owner") != ownerID:
                                    try:
                                        tle.setOwner(savedItemID, savedItemVersion, ownerID)
                                    except:
                                        exactError = str(sys.exc_info()[1])
                                        errorDebug = ""
                                        if self.debug:
                                            exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
                                            errorDebug = "\n" + ''.join(traceback.format_exception(exceptionType, exceptionValue, exceptionTraceback))

                                        exactError = self.translateError(exactError)
                                        
                                        self.echo(time.strftime("%H:%M:%S: ", time.localtime(time.time())) + "ERROR: %s%s" % (exactError, errorDebug), style=2)

                            # add collaborators if any specified and existing item being edited
                            if collaboratorsColumn != -1 and not createNewVersion and not createNewItem and len(collaboratorIDs) > 0:
                                self.echo("  Setting collaborators")
                                try:
                                    # if remove all existing collaborators unless appending metadata
                                    if self.existingMetadataMode != self.APPENDMETA and 'APPENDMETA' not in commandOptions:
                                        existingCollaboratorIDs = item.getXml().getNodes("item/collaborativeowners/collaborator")
                                        
                                        for existingCollaboratorID in existingCollaboratorIDs:
                                            if existingCollaboratorID not in collaboratorIDs:
                                                tle.removeSharedOwner(savedItemID, savedItemVersion, existingCollaboratorID)
                              
                              
                                    # add specified collaborators
                                    for collaboratorID in collaboratorIDs:
                                        if collaboratorID not in existingCollaboratorIDs:
                                            tle.addSharedOwner(savedItemID, savedItemVersion, collaboratorID)

                                except:
                                    exactError = str(sys.exc_info()[1])
                                    errorDebug = ""
                                    if self.debug:
                                        exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
                                        errorDebug = "\n" + ''.join(traceback.format_exception(exceptionType, exceptionValue, exceptionTraceback))

                                    exactError = self.translateError(exactError)
                                    
                                    self.echo(time.strftime("%H:%M:%S: ", time.localtime(time.time())) + "ERROR: %s%s" % (exactError, errorDebug), style=2)
                                
                            if createNewItem:
                                self.echo("  Item successfully imported%s (%s/%s)" % (statusMessage, savedItemID, savedItemVersion))
                            else:
                                if createNewVersion:
                                    self.echo("  New version successfully created" + statusMessage)
                                else:
                                    self.echo("  Item successfully updated")
                                    
                            # re-edit and add CAL holding relations metadata if necessary
                            if (createNewItem or createNewVersion) and calHoldingMetadataTarget != "":
                                self.echo("  Re-editing to add CAL metadata...")
                                tle._forceUnlock(savedItemID, savedItemVersion)
                                item = tle.editItem(savedItemID, savedItemVersion, 'true')
                                self.addCALRelations(calHoldingMetadataTarget, item.getXml())
                                item.submit(bSubmit)
                                self.echo("  Item successfully updated")
                        
                        # increment success count
                        self.successCount += 1
                    else:
                        item.parClient._cancelEdit(item.getUUID(), item.getVersion())
                        if self.Skip:
                            self.echo("  Row skipped")

                retriesDone = True

                # return Item ID, Item Version and Source Identifier
                sourceIdentifier = ""
                if sourceIdentifierColumn != -1:
                    sourceIdentifier = meta[sourceIdentifierColumn].strip()
                return savedItemID, savedItemVersion, sourceIdentifier, meta, ""
                              
            except:
                exactError = str(sys.exc_info()[1])

                # check if it is worthwhile recycling the session and retrying
                if failCount < self.maxRetry and ("(10054)" in exactError or "(10060)" in exactError or "(10061)" in exactError or "(104)" in exactError):
                    failCount += 1
                    self.echo("  %s. Retrying..." % (exactError))

                    # pause for increasing periods with each fail. 5 seconds, 10 seconds, 15 seconds... so on until maximum number of retries
                    time.sleep(5 * failCount)
                    try:
                        item.parClient._cancelEdit(item.getUUID(), item.getVersion())
                    except:
                        pass
                    self.tle = None
                    self.tle = TLEClient(self.institutionUrl, self.username, self.password, self.proxy, self.proxyUsername, self.proxyPassword, self.debug)                    
                    
                else:
                    self.errorCount += 1
                    
                    # form error string for debugging
                    errorDebug = ""
                    if self.debug:
                        exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
                        errorDebug = "\n" + ''.join(traceback.format_exception(exceptionType, exceptionValue, exceptionTraceback))

                    exactError = self.translateError(exactError)
                    
                    if "Collection not found" in exactError:
                        allRowsError = True
                    
                    # add further information if error is with a particular column etc
                    actionError = ""
                    if n != -1 and not attemptingUpload:
                        actionError =  " parsing column %s '%s'" % (n + 1, self.columnHeadings[n])
                    if attemptingUpload:
                        actionError =  " uploading file"
                        attemptingUpload = False

                    self.echo(time.strftime("%H:%M:%S: ", time.localtime(time.time())) + "ERROR%s: %s%s" % (actionError, exactError, errorDebug), style=2)

                    # halt processing if the error will apply to all rows
                    if allRowsError:
                        raise Exception, "Halting process"

                    # return Item ID, Item Version and Source Identifier
                    sourceIdentifier = ""
                    if sourceIdentifierColumn != -1:
                        sourceIdentifier = meta[sourceIdentifierColumn].strip()
                        
                    return savedItemID, savedItemVersion, sourceIdentifier, meta, "ERROR%s: %s%s" % (actionError, exactError, errorDebug)
    
    def exportCSV(self,
                    owner,
                    tle,
                    itemdefuuid,
                    collectionIDs,
                    testOnly,
                    scheduledRows,
                    sourceIdentifierColumn, 
                    targetIdentifierColumn,
                    targetVersionColumn,
                    commandOptionsColumn,                   
                    attachmentLocationsColumn,
                    collectionColumn,
                    rowsToBeProcessedCount):

        if not testOnly:
            if owner.txtCSVPath.GetValue() != "" and not os.path.isdir(self.csvFilePath):
                try:
                    # test opening file for writing (append test only)
                    
                    f = open(self.csvFilePath, "ab")
                    f.close()
                except:
                    raise Exception, "CSV cannot be written to and may be in use: %s" % self.csvFilePath

        allRowsError = False
        self.successCount = 0
        self.errorCount = 0
        processedCounter = 0
        
        # run Start Script
        if self.startScript.strip() != "":
            try:
                exec self.startScript in {
                                        "IMPORT":0,
                                        "EXPORT":1,
                                        "mode":1,
                                        "vars":self.scriptVariables,
                                        "testOnly": testOnly,
                                        "institutionUrl":tle.institutionUrl,
                                        "collection":self.collection,
                                        "csvFilePath":self.csvFilePath,
                                        "username":self.username,
                                        "logger":self.logger,
                                        "columnHeadings":self.columnHeadings,
                                        "columnSettings":self.currentColumns,
                                        "successCount":self.successCount,
                                        "errorCount":self.errorCount,
                                        "process":self.process,
                                        "basepath":self.absoluteAttachmentsBasepath,
                                        "sourceIdentifierIndex":sourceIdentifierColumn,
                                        "targetIdentifierIndex":targetIdentifierColumn,
                                        "targetVersionIndex":targetVersionColumn,
                                        "csvData":self.csvArray,
                                        "ebi":self.ebiScriptObject,                                       
                                        "equella":tle,
                                        }
            except:
                if self.debug:
                    raise
                else:
                    exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
                    formattedException = "".join(traceback.format_exception_only(exceptionType, exceptionValue))[:-1]
                    scriptErrorMsg = "An error occured in the Start Script:\n%s (line %s)" % (formattedException, traceback.extract_tb(exceptionTraceback)[-1][1])
                    raise Exception, scriptErrorMsg
        
        # check column headings
        self.validateColumnHeadings()
            
        actionString = ""
        if self.includeNonLive:
            actionString = "Options -> Export non-live items"
        if actionString != "":
            self.echo(time.strftime("%H:%M:%S: ", time.localtime(time.time())) + actionString)
                                    
        if sourceIdentifierColumn == -1 and targetIdentifierColumn == -1:
            
            # WHERE Clause
            if self.whereClause.strip() != "":
                self.echo(time.strftime("%H:%M:%S: ", time.localtime(time.time())) + "WHERE Clause: %s" % self.whereClause)
            
            # determine which collection to search (seach all collections if Collections column present)
            if collectionColumn == -1:
                collectionsToSearch = [itemdefuuid]
            else:
                collectionsToSearch = []
                
            # get available
            try:
                searchResults = tle.search(query='',
                                                itemdefs=collectionsToSearch,
                                                where=self.whereClause.strip(),
                                                onlyLive=not self.includeNonLive,
                                                orderType=0,
                                                reverseOrder=False,
                                                offset=0,
                                                limit=1)
                                            
                                            
            except:
                if self.debug:
                    exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
                    errorString = "\n" + ''.join(traceback.format_exception(exceptionType, exceptionValue, exceptionTraceback)) + "\n"
                else:
                    errorString = "Error whist attempting to search: " + str(sys.exc_info()[1])
                raise Exception, errorString                                            
                                            
                                                    
            rowCounter = 0
            available = int(searchResults.getNode("available"))
            pageSize = 50
            
            # determine how many rows to be processed
            itemsToBeProcessedCount = available
            if self.rowFilter.strip() != "":
                itemsToBeProcessedCount = 0
                for rc in scheduledRows:
                    if rc <= available:
                        itemsToBeProcessedCount += 1
                        
            # echo rows to be processed
            scheduledRowsLabel = " "
            if itemsToBeProcessedCount > 0:
                scheduledRowsLabel = ", all to be exported "
            if self.rowFilter != "":
                scheduledRowsLabel = ", %s to be processed [%s] " % (itemsToBeProcessedCount, self.rowFilter)
            if testOnly:
                actionString = "%s item(s) found%s(test only)" % (available, scheduledRowsLabel)
            else:
                actionString = "%s item(s) found%s" % (available, scheduledRowsLabel)
            self.echo(time.strftime("%H:%M:%S: ", time.localtime(time.time())) + actionString)
            
            self.owner.progressGauge.SetRange(itemsToBeProcessedCount)
            self.owner.progressGauge.SetValue(processedCounter)
            self.owner.progressGauge.Show()            
            
            # crop list down to first row
            self.csvArray = self.csvArray[:1]
            
            # outer loop of "pages" of pageSize
            pagesRequired = available / pageSize + 1
            offset = 0
            lastScheduledItem = -1
            if len(scheduledRows) > 0:
                lastScheduledItem = max(scheduledRows)
            
            for pageCounter in range(1, pagesRequired + 1):
            
                searchResults = tle.search(query='',
                                                itemdefs=collectionsToSearch,
                                                where=self.whereClause.strip(),
                                                onlyLive=not self.includeNonLive,
                                                orderType=0,
                                                reverseOrder=False,
                                                offset=offset,
                                                limit=pageSize)

                wx.GetApp().Yield()

                for result in searchResults.iterate("result"):
                    if not self.StopProcessing:
                        try:
                        
                            # increment rowCounter
                            rowCounter += 1
                            
                            self.Skip = False
                            
                            if self.rowFilter.strip() == "" or rowCounter in scheduledRows:
                                
                                processedCounter += 1
                                
                                self.echo("---")
                                
                                itemXml = result.getSubtree("xml")
                                itemID = itemXml.getNode("item/@id")
                                itemVersion = itemXml.getNode("item/@version")
                            
                                # update UI and log
                                owner.mainStatusBar.SetStatusText("Exporting item %s [%s of %s]" % (rowCounter, processedCounter, itemsToBeProcessedCount), 0)
                                self.owner.progressGauge.SetValue(processedCounter)
                                if testOnly:
                                    action = "Exporting item %s/%s (test only)..." % (itemID, itemVersion)
                                else:
                                    action = "Exporting item %s/%s..." % (itemID, itemVersion)
                                    
                                    
                                self.echo(time.strftime("%H:%M:%S: ", time.localtime(time.time())) + " Item %s [%s of %s]: %s" % (rowCounter, processedCounter, itemsToBeProcessedCount, action))
                                wx.GetApp().Yield()

                                rowData = self.exportItem(rowCounter,
                                                    itemXml,
                                                    tle,
                                                    itemdefuuid,
                                                    testOnly,
                                                    sourceIdentifierColumn, 
                                                    targetIdentifierColumn,
                                                    targetVersionColumn,
                                                    commandOptionsColumn,
                                                    attachmentLocationsColumn,
                                                    collectionIDs,
                                                    self.csvArray)
                                
                                if not self.Skip:
                                    if len(self.csvArray) > rowCounter:
                                        self.csvArray[rowCounter] = rowData
                                    else:
                                        self.csvArray.append(rowData)
                                    self.successCount += 1
                            
                            if self.rowFilter.strip() != "" and rowCounter == lastScheduledItem:
                                break
                            offset = rowCounter

                        except:
                            exactError = str(sys.exc_info()[1])
                            self.errorCount += 1
                            
                            # form error string for debugging
                            errorDebug = ""
                            if self.debug:
                                exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
                                errorDebug = "\n" + ''.join(traceback.format_exception(exceptionType, exceptionValue, exceptionTraceback))

                            exactError = self.translateError(exactError)
                            self.echo(time.strftime("%H:%M:%S: ", time.localtime(time.time())) + "ERROR: %s%s" % (exactError, errorDebug), style=2)

                            # halt processing if the error will apply to all rows
                            if allRowsError:
                                raise Exception, "Halting process"
                        
                    # stop processing
                    else:
                        break
                if self.StopProcessing:
                    self.echo("---")
                    if self.processingStoppedByScript:
                        self.echo(time.strftime("%H:%M:%S: ", time.localtime(time.time())) + "Export halted")
                    else:
                        self.echo(time.strftime("%H:%M:%S: ", time.localtime(time.time())) + "Export halted by user")
                    break
                elif self.rowFilter.strip() != "" and rowCounter == lastScheduledItem:
                    break                
        else:
            
            # echo rows to be processed
            scheduledRowsLabel = "all to be exported"
            if self.rowFilter != "":
                scheduledRowsLabel = "%s to be processed [%s]" % (rowsToBeProcessedCount, self.rowFilter)
            if testOnly:
                actionString = str(len(self.csvArray) - 1) + " row(s) found, %s (test only)" % (scheduledRowsLabel)
            else:
                actionString = str(len(self.csvArray) - 1) + " row(s) found, %s" % (scheduledRowsLabel)
            self.echo(time.strftime("%H:%M:%S: ", time.localtime(time.time())) + actionString)
            
            self.owner.progressGauge.SetRange(rowsToBeProcessedCount)
            self.owner.progressGauge.SetValue(processedCounter)
            self.owner.progressGauge.Show()          

            # iterate through the rows of metadata from the CSV file exporting an item from EQUELLA for each
            for rowCounter in scheduledRows:
                
                if not self.StopProcessing and rowCounter < len(self.csvArray):
                    try:
                        processedCounter += 1
                        self.Skip = False
                        
                        self.echo("---")
                    
                        # update UI and log
                        owner.mainStatusBar.SetStatusText("Exporting row %s [%s of %s]" % (rowCounter, processedCounter, rowsToBeProcessedCount), 0)
                        self.owner.progressGauge.SetValue(processedCounter)
                        if testOnly:
                            action = "Exporting item (test only)..."
                        else:
                            action = "Exporting item..."
                        self.echo(time.strftime("%H:%M:%S: ", time.localtime(time.time())) + " Row %s [%s of %s]: %s" % (rowCounter, processedCounter, rowsToBeProcessedCount, action))
                        wx.GetApp().Yield()
                        
                        rowitemdefuuid = itemdefuuid
                        # override the collection ID if one has been specified in the row
                        if collectionColumn != -1:
                            collectionName = self.csvArray[rowCounter][collectionColumn].strip()
                            if collectionName != "":
                                if collectionName in collectionIDs:
                                    rowitemdefuuid = collectionIDs[collectionName]
                                    self.echo("  Source collection: '%s'" % collectionName)
                                else:
                                    raise Exception, "'" + collectionName + "' collection not found"
                            
                    
                        itemFound = False
                        
                        # get targeted item version if target version specified
                        itemVersion = 0
                        if targetVersionColumn != -1 and self.csvArray[rowCounter][targetVersionColumn].strip() != "":
                            try:
                                itemVersion = int(self.csvArray[rowCounter][targetVersionColumn].strip())
                                if itemVersion < -1:
                                    raise Exception, "Invalid item version specified"
                            except:
                                raise Exception, "Invalid item version specified"                        
                        
                        # if Source Identifier column specified check if item exists by sourceIdentifier
                        if sourceIdentifierColumn != -1:
                            if self.csvArray[rowCounter][sourceIdentifierColumn].strip() != "":
                                if targetVersionColumn == -1 or self.csvArray[rowCounter][targetVersionColumn].strip() == "":
                                    noVersionSpecified = True
                                else:
                                    noVersionSpecified = False
                                
                                # determine if items versions of any status need to be returned
                                if itemVersion != 0 or (self.includeNonLive and noVersionSpecified):
                                    onlyLive = False
                                    limit = 50
                                else:
                                    onlyLive = True
                                    limit = 1                                

                                sourceIdentifier = self.csvArray[rowCounter][sourceIdentifierColumn].strip()
                                self.echo("  Source identifier = " + sourceIdentifier)
                                if targetVersionColumn != -1 and self.csvArray[rowCounter][targetVersionColumn].strip() != "":
                                    self.echo("  Target version = " + self.csvArray[rowCounter][targetVersionColumn].strip())
                                searchFilter = "/xml/" + self.columnHeadings[sourceIdentifierColumn] + "='" + sourceIdentifier + "'"
                                results = tle.search(0, limit, '', [rowitemdefuuid], searchFilter, query='', onlyLive=onlyLive)
                                
                                # if any matches get first matching item for editing
                                if int(results.getNode("available")) > 0:
                                    if itemVersion == 0 and not (self.includeNonLive and noVersionSpecified):
                                        # get first live version
                                        itemXml = results.getSubtree("result/xml")
                                        itemID = results.getNode("result/xml/item/@id")
                                        itemVersion = results.getNode("result/xml/item/@version")
                                        itemFound = True                                        
                                    else:
                                        if itemVersion > 0:
                                            # find item by item version
                                            for itemResult in results.iterate("result"):
                                                if itemResult.getNode("xml/item/@version") == str(itemVersion):
                                                    itemXml = itemResult.getSubtree("xml")
                                                    itemID = itemResult.getNode("xml/item/@id")
                                                    itemFound = True
                                                    break
                                            if not itemFound:
                                                self.echo("  Item not found in EQUELLA")
                                        else:
                                            # find item with highest version
                                            highestVersionFound = 0
                                            highestLiveVersionFound = 0
                                            for itemResult in results.iterate("result"):
                                                if int(itemResult.getNode("xml/item/@version")) > highestVersionFound:
                                                    
                                                    itemXml = itemResult.getSubtree("xml")
                                                    itemID = itemResult.getNode("xml/item/@id")
                                                    
                                                    highestVersionFound = int(itemResult.getNode("xml/item/@version"))
                                                    if itemResult.getNode("xml/item/@status") == "live":
                                                        highestLiveVersionFound = highestVersionFound
                                                        
                                            if itemVersion == 0:
                                                itemVersion = highestLiveVersionFound
                                            else:
                                                itemVersion = highestVersionFound
                                            itemFound = True
                                    if itemFound:
                                        self.echo("  Item exists in EQUELLA (" + itemID + "/" + str(itemVersion) + ")")
                                else:
                                    self.echo("  Item not found in EQUELLA")
                            else:
                                self.echo("  No source identifier specified")

                        # if Target Identifier column specified edit item by ID (using latest version of item)
                        elif targetIdentifierColumn != -1:
                            if self.csvArray[rowCounter][targetIdentifierColumn].strip() != "":
                                targetIdentifier = self.csvArray[rowCounter][targetIdentifierColumn].strip()
                                self.echo("  Target identifier = " + targetIdentifier)
                                if targetVersionColumn != -1 and self.csvArray[rowCounter][targetVersionColumn].strip() != "":
                                    self.echo("  Target version = " + self.csvArray[rowCounter][targetVersionColumn].strip())
                                elif self.includeNonLive:
                                    itemVersion = -1
                                    
                                itemID = targetIdentifier
                                
                                # try retreiving item
                                try:
                                    itemXml = tle.getItem(itemID, itemVersion)
                                    itemFound = True
                                    self.echo("  Item exists in EQUELLA (" + itemID + "/" + itemXml.getNode("item/@version") + ")")
                                except:
                                    self.echo("  Could not find item (" + str(sys.exc_info()[1]) + ")")
                            else:
                                self.echo("  No target identifier specified")

                        if itemFound:
                            rowData = self.exportItem(rowCounter,
                                                        itemXml,
                                                        tle,
                                                        itemdefuuid,
                                                        testOnly,
                                                        sourceIdentifierColumn, 
                                                        targetIdentifierColumn,
                                                        targetVersionColumn,
                                                        commandOptionsColumn,
                                                        attachmentLocationsColumn,
                                                        collectionIDs,
                                                        self.csvArray[rowCounter])  

                            if not self.Skip:                
                                self.csvArray[rowCounter] = rowData
                                self.successCount += 1
                                  
                    except:
                        exactError = str(sys.exc_info()[1])
                        self.errorCount += 1
                        
                        # form error string for debugging
                        errorDebug = ""
                        if self.debug:
                            exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
                            errorDebug = "\n" + ''.join(traceback.format_exception(exceptionType, exceptionValue, exceptionTraceback))

                        exactError = self.translateError(exactError)
                        self.echo(time.strftime("%H:%M:%S: ", time.localtime(time.time())) + "ERROR: %s%s" % (exactError, errorDebug), style=2)

                        # halt processing if the error will apply to all rows
                        if allRowsError:
                            raise Exception, "Halting process"

                # stop processing
                else:
                    if self.StopProcessing:
                        self.echo("---")
                        self.echo(time.strftime("%H:%M:%S: ", time.localtime(time.time())) + "Export halted by user")
                    break
        
        self.echo("---")

        # run End Script
        if self.endScript.strip() != "":
            try:
                exec self.endScript in {
                                        "IMPORT":0,
                                        "EXPORT":1,
                                        "mode":1,
                                        "vars":self.scriptVariables,
                                        "testOnly": testOnly,
                                        "institutionUrl":tle.institutionUrl,
                                        "collection":self.collection,
                                        "csvFilePath":self.csvFilePath,
                                        "username":self.username,
                                        "logger":self.logger,
                                        "columnHeadings":self.columnHeadings,
                                        "columnSettings":self.currentColumns,
                                        "successCount":self.successCount,
                                        "errorCount":self.errorCount,
                                        "process":self.process,
                                        "basepath":self.absoluteAttachmentsBasepath,                                       
                                        "csvData":self.csvArray,
                                        "sourceIdentifierIndex":sourceIdentifierColumn,
                                        "targetIdentifierIndex":targetIdentifierColumn,
                                        "targetVersionIndex":targetVersionColumn,
                                        "ebi":self.ebiScriptObject,
                                        "equella":tle,
                                        }
            except:
                if self.debug:
                    exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
                    scriptErrorMsg = "An error occured in the End Script:\n" + ''.join(traceback.format_exception(exceptionType, exceptionValue, exceptionTraceback))
                    self.echo(time.strftime("%H:%M:%S: ", time.localtime(time.time())) + scriptErrorMsg)
                else:
                    exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
                    formattedException = "".join(traceback.format_exception_only(exceptionType, exceptionValue))[:-1]
                    scriptErrorMsg = "An error occured in the End Script:\n%s (line %s)" % (formattedException, traceback.extract_tb(exceptionTraceback)[-1][1])
                    self.echo(time.strftime("%H:%M:%S: ", time.localtime(time.time())) + scriptErrorMsg)   

        
        # open csv writer and output write local copy to csv
        if not testOnly and not os.path.isdir(self.csvFilePath):
            f = open(self.csvFilePath, "wb")
            writer = UnicodeWriter(f, self.encoding)
            writer.writerows(self.csvArray)
            f.close()
            
    def exportItem(self,
                    rowCounter,
                    itemXml,
                    tle,
                    itemdefuuid,
                    testOnly,
                    sourceIdentifierColumn, 
                    targetIdentifierColumn,
                    targetVersionColumn,
                    commandOptionsColumn, 
                    attachmentLocationsColumn,
                    collectionIDs,
                    oldRowData = None):

        itemID = itemXml.getNode("item/@id")
        itemVersion = itemXml.getNode("item/@version")
        
        self.tryPausing("[Paused]")
        
        # run Row Pre-Script
        if self.preScript.strip() != "":
            
            ebiScriptObject = EbiScriptObject(self)
            
            try:
                exec self.preScript in {
                                        "IMPORT":0,
                                        "EXPORT":1,
                                        "action":1,
                                        "vars":self.scriptVariables,
                                        "rowCounter":rowCounter,
                                        "testOnly": testOnly,
                                        "institutionUrl":tle.institutionUrl,
                                        "collection":self.collection,
                                        "csvFilePath":self.csvFilePath,
                                        "username":self.username,
                                        "logger":self.logger,
                                        "columnHeadings":self.columnHeadings,
                                        "columnSettings":self.currentColumns,
                                        "successCount":self.successCount,
                                        "errorCount":self.errorCount,
                                        "itemId":itemID,
                                        "itemVersion":itemVersion,
                                        "xml":itemXml,
                                        "xmldom":itemXml.root,
                                        "process":self.process,
                                        "basepath":self.absoluteAttachmentsBasepath,
                                        "sourceIdentifierIndex":sourceIdentifierColumn,
                                        "targetIdentifierIndex":targetIdentifierColumn,
                                        "targetVersionIndex":targetVersionColumn,
                                        "csvData":self.csvArray,
                                        "ebi":self.ebiScriptObject,
                                        "equella":tle,
                                        }
                
            except:
                if self.debug:
                    raise
                else:
                    exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
                    formattedException = "".join(traceback.format_exception_only(exceptionType, exceptionValue))[:-1]
                    scriptErrorMsg = "An error occured in the Row Pre-Script:\n%s (line %s)" % (formattedException, traceback.extract_tb(exceptionTraceback)[-1][1])
                    raise Exception, scriptErrorMsg
            
            self.csvFilePath = ebiScriptObject.csvFilePath              

        rowData = ['']*(len(self.columnHeadings))
        filesDownloaded = []
        command = ""
        hyperlinkColumnCount = 0
        attachmentColumnCount = 0
        equellaResourceColumnCount = 0
        
        if self.Skip:
            self.echo("  Skipping item")
            return rowData
        
        for n in range(0, len(self.columnHeadings)):
            cellValues = []
            delimiter = self.currentColumns[n][self.COLUMN_DELIMITER].strip()

            # get metadata values if column datatype uses an xpath
            values = []
            if self.currentColumns[n][self.COLUMN_DATATYPE] == self.METADATA or \
            (self.currentColumns[n][self.COLUMN_DATATYPE] in [self.ATTACHMENTLOCATIONS, self.URLS, self.EQUELLARESOURCES, self.CUSTOMATTACHMENTS] and \
            self.columnHeadings[n].strip() != "" and self.columnHeadings[n].strip()[0] != "#"):
                           
                # Get all matching values
                values = itemXml.getNodes(self.columnHeadings[n])
                
                # detemine how many values to "discount" away (-1 means discount all of them) to
                # spread repeating values across columns with same xpaths
                valuesUsed = 0
                for i in range(0, n):
                    if self.columnHeadings[i] == self.columnHeadings[n] and self.currentColumns[i][self.COLUMN_DATATYPE] == self.currentColumns[n][self.COLUMN_DATATYPE]:
                        if self.currentColumns[i][self.COLUMN_DELIMITER].strip() == "" and valuesUsed != -1:
                            valuesUsed += 1
                        else:
                            valuesUsed = -1
            
            if self.currentColumns[n][self.COLUMN_DATATYPE] == self.METADATA:
                # check if column is flagged for XML fragments
                if self.currentColumns[n][self.COLUMN_XMLFRAGMENT] == "YES":
                    
                    # process node as XML fragment
                    xmlFragNodes = itemXml.getNodes(self.columnHeadings[n], False)
                    if len(xmlFragNodes) > 0:
                        xmlFragment = ""
                        for childNode in xmlFragNodes[0].childNodes:
                            # only add node if it is not an empty text node
                            if (childNode.nodeType == Node.TEXT_NODE and childNode.nodeValue.strip() != "") or (childNode.nodeType != Node.TEXT_NODE):
                                xmlFragment += childNode.toxml()
                    
                        cellValues.append(xmlFragment)
                        
                # not an xml fragment
                else:
                    if len(values) > 0 and valuesUsed != -1:
                        if delimiter != "":
                            # get all non-discounted values
                            cellValues = values[valuesUsed:]
                        else:
                            if len(values) > valuesUsed:
                                cellValues.append(values[valuesUsed])
                        
            elif self.currentColumns[n][self.COLUMN_DATATYPE] == self.URLS:
                hyperlinkColumnCount += 1
                
                if len(values) > 0 and valuesUsed != -1:
                    
                    attachmentNames = []

                    # calculate first and last index of values applicable to this column
                    if delimiter != "":
                        lastValueIndex = len(values)
                    else:
                        lastValueIndex = valuesUsed + 1

                    # iterate through the attachment UUIDs applicable to this column to calculate
                    # cell values whilst downloading files as necessary
                    for attachmentUUID in values[valuesUsed:lastValueIndex]:
                        for attachment in itemXml.getSubtree("item/attachments").iterate("attachment"):
                            filename = attachment.getNode("file").replace(" ", "%20")
                            if attachment.getNode("uuid") == attachmentUUID:                        
                                if attachment.getNode("@type") == "remote":
                                    
                                    # get URL from attachment metadata
                                    self.echo("  Hyperlink: " + filename)
                                
                                    # collect attachment name
                                    attachmentName = attachment.getNode("description")
                                    if attachmentName == filename:
                                        attachmentName = ""
                                    attachmentNames.append(attachmentName)

                                    # set cell value
                                    cellValues.append(filename)
                                elif attachment.getNode("@type") == "local":
                                    if self.debug:
                                        self.echo("  Ignoring: " + filename)                                    
                                    
                    # find corresponding Attachment Names column to populate with attachment names
                    attachmentNameColumnCount = 0
                    for col in range(0, len(self.currentColumns)):
                        if self.currentColumns[col][self.COLUMN_DATATYPE] == self.HYPERLINKNAMES:
                            
                            attachmentNameColumnCount += 1

                            if attachmentNameColumnCount == hyperlinkColumnCount:
                                # populate with attachment names
                                attachmentNameColumnDelimiter = self.currentColumns[col][self.COLUMN_DELIMITER].strip()
                                if attachmentNameColumnDelimiter != "":
                                    rowData[col] = attachmentNameColumnDelimiter.join(attachmentNames)
                                else:
                                    rowData[col] = attachmentNames[0]
                                break                                                           

            elif self.currentColumns[n][self.COLUMN_DATATYPE] == self.ATTACHMENTLOCATIONS:
                attachmentColumnCount += 1
                
                if len(values) > 0 and valuesUsed != -1:
                    
                    # get absolute path to file relative to base path (from Options) and then relative to csv folder
                    filesfolder = self.absoluteAttachmentsBasepath
                    attachmentNames = []
                    attachmentNamesZip = []
                    zipFiles = []
                    
                    # get item URL (used for downloading files)
                    itemUrl = self.institutionUrl + "/file/" + itemID + "/" + itemVersion + "/"
                    
                    # calculate first and last index of values applicable to this column
                    if delimiter != "":
                        lastValueIndex = len(values)
                    else:
                        lastValueIndex = valuesUsed + 1

                    # iterate through the attachment UUIDs applicable to this column to calculate
                    # cell values whilst downloading files as necessary
                    for attachmentUUID in values[valuesUsed:lastValueIndex]:
                        for attachment in itemXml.getSubtree("item/attachments").iterate("attachment"):
                            if attachment.getNode("uuid") == attachmentUUID:
                                filename = attachment.getNode("file")
                                if attachment.getNode("@type") == "local":
                                    if filename.find("/") == -1:
                                        # download simple file
                                        filepath = os.path.join(filesfolder, filename)
                                        fileUrl = itemUrl + urllib.quote(filename)
                                        
                                        if not testOnly and not fileUrl in filesDownloaded:
                                            self.echo("  Attachment: " + filename)
                                            
                                            # "deconflict" files of same name
                                            filepath = self.deconflict(filepath, self.exportedFiles, self.overwriteMode)
                                            
                                            tle.getFile(fileUrl, filepath)
                                            filesDownloaded.append(fileUrl)
                                            self.exportedFiles.append(filepath)
                                        
                                        # collect attachment name
                                        attachmentName = attachment.getNode("description")
                                        if attachmentName == filename:
                                            attachmentName = ""
                                        attachmentNames.append(attachmentName)
                                        
                                        # set cell value
                                        if not filename in cellValues:
                                            cellValues.append(os.path.relpath(filepath, filesfolder))
                                    else:
                                        # possibly a zip file
                                        rootFolder = filename[:filename.find("/")]
                                        if rootFolder.endswith(".zip"):
                                            # download zip file
                                            zipfilename = rootFolder
                                            relfilename = filename[filename.find("/") + 1:]
                                            filepath = os.path.join(filesfolder, zipfilename)
                                            fileUrl = itemUrl + "_zips/" + urllib.quote(zipfilename)
                                            
                                            if not testOnly and not fileUrl in filesDownloaded:
                                                self.echo("  Attachment (ZIP): " + zipfilename)
                                                
                                                # "deconflict" files of same name
                                                filepath = self.deconflict(filepath, self.exportedFiles, self.overwriteMode)
                                                
                                                tle.getFile(fileUrl, filepath)
                                                filesDownloaded.append(fileUrl)
                                                self.exportedFiles.append(filepath)
                                            
                                            # collect attachment name
                                            attachmentNamesZip.append([relfilename, attachment.getNode("description")])
                                            
                                            # set command
                                            if command == "":
                                                command = "UNZIP"
                                            elif command != "UNZIP":
                                                command = "AUTO"
                                                
                                            # add to cell values if zip not already there
                                            if zipfilename not in zipFiles:
                                                cellValues.append(os.path.relpath(filepath, filesfolder))
                                                zipFiles.append(zipfilename)
                                    
                                elif attachment.getNode("@type") == "custom" and attachment.getNode("type") == "scorm":
                                    # download SCORM package
                                    filepath = os.path.join(filesfolder, filename)
                                    
                                    # "deconflict" files of same name
                                    filepath = self.deconflict(filepath, self.exportedFiles, self.overwriteMode)
                                    
                                    fileUrl = itemUrl + "_SCORM/" + urllib.quote(filename)
                                    
                                    if not testOnly and not fileUrl in filesDownloaded:
                                        self.echo("  Attachment (SCORM): " + filename)
                                        tle.getFile(fileUrl, filepath)
                                        filesDownloaded.append(fileUrl)
                                        self.exportedFiles.append(filepath)

                                    # collect attachment name
                                    attachmentName = attachment.getNode("description")
                                    if attachmentName == filename:
                                        attachmentName = ""
                                    attachmentNames = []
                                    attachmentNames.append(attachmentName)
                                                                                
                                    # set command
                                    if command == "":
                                        command = "IMS"
                                    elif command != "IMS":
                                        command = "AUTO"

                                    # set cell value
                                    if not filename in cellValues:
                                        cellValues.append(filename)    
                                elif attachment.getNode("@type") == "remote":
                                    if self.debug:
                                        self.echo("  Ignoring: " + filename)
                                else:
                                    # attachment not supported for export
                                    self.echo("  Unknown or unsupported attachment: " + filename)
                                    
                        if itemXml.getNode("item/itembody/packagefile/@uuid") == attachmentUUID:
                            filename = itemXml.getNode("item/itembody/packagefile")

                            # download IMS package
                            filepath = os.path.join(filesfolder, filename)
                            
                            # "deconflict" files of same name
                            filepath = self.deconflict(filepath, self.exportedFiles, self.overwriteMode)
                            
                            fileUrl = itemUrl + "_IMS/" + urllib.quote(filename)
                            
                            if not testOnly and not fileUrl in filesDownloaded:
                                self.echo("  Attachment (IMS): " + filename)  
                                tle.getFile(fileUrl, filepath)
                                filesDownloaded.append(fileUrl)
                                self.exportedFiles.append(filepath)

                            # collect attachment name
                            attachmentName = itemXml.getNode("item/itembody/packagefile/@name")
                            if attachmentName == filename:
                                attachmentName = ""
                            attachmentNames = []
                            attachmentNames.append(attachmentName)
                                    
                            # set command
                            if command == "":
                                command = "IMS"
                            elif command != "IMS":
                                command = "AUTO"
                            
                            # set cell value
                            if not filename in cellValues:
                                cellValues.append(filename)
                    
                    # find corresponding Attachment Names column to populate with attachment names
                    attachmentNameColumnCount = 0
                    for col in range(0, len(self.currentColumns)):
                        if self.currentColumns[col][self.COLUMN_DATATYPE] == self.ATTACHMENTNAMES:
                            
                            attachmentNameColumnCount += 1

                            if attachmentNameColumnCount == attachmentColumnCount:
                                # populate with attachment names
                                if len(attachmentNamesZip) == 0:
                                    attachmentNameColumnDelimiter = self.currentColumns[col][self.COLUMN_DELIMITER].strip()
                                    if attachmentNameColumnDelimiter != "":
                                        rowData[col] = attachmentNameColumnDelimiter.join(attachmentNames)
                                    else:
                                        rowData[col] = attachmentNames[0]
                                else:
                                    attachmentName = "("
                                    for pair in attachmentNamesZip:
                                        attachmentName += "("
                                        attachmentName += "\"" + pair[0] + "\",\"" + pair[1] + "\""
                                        attachmentName += "),"
                                    attachmentName = attachmentName[:-1]
                                    attachmentName += ")"
                                    rowData[col] = attachmentName
                                break
                            
            elif self.currentColumns[n][self.COLUMN_DATATYPE] == self.OWNER:
                
                self.echo("  Exporting owner")

                # get owner ID
                userID = itemXml.getNodes("item/owner")[0]
                
                try:
                    # get username from user ID
                    username = tle.getUser(userID).getNode("username")
                except:
                    
                    # handle inability to retrieve username from user ID
                    if self.saveNonexistentUsernamesAsIDs:
                        self.echo("  User ID '%s' not found so exporting raw." % (userID))
                        username = userID
                    else:
                        raise Exception, "No user found with matching user ID: %s" % userID
                    
                cellValues = [username]

            elif self.currentColumns[n][self.COLUMN_DATATYPE] == self.ITEMID:
                cellValues = [itemID]

            elif self.currentColumns[n][self.COLUMN_DATATYPE] == self.ITEMVERSION:
                cellValues = [itemVersion]
                
            elif self.currentColumns[n][self.COLUMN_DATATYPE] == self.COLLABORATORS:

                self.echo("  Exporting collaborators")

                # get collaborators
                userIDs = itemXml.getNodes("item/collaborativeowners/collaborator")
                
                if delimiter == "" and len(userIDs) > 1:
                    userIDs = userIDs[:1]
                    
                cellValues = []
                
                for userID in userIDs:
                    try:
                        # get username from user ID
                        username = tle.getUser(userID).getNode("username")
                    except:
                        
                        # handle inability to retrieve username from user ID
                        if self.saveNonexistentUsernamesAsIDs:
                            self.echo("  User ID '%s' not found so exporting raw." % (userID))
                            username = userID
                        else:
                            raise Exception, "No user found with matching user ID: %s" % userID
                        
                    cellValues.append(username)

            elif self.currentColumns[n][self.COLUMN_DATATYPE] == self.COLLECTION:
                collID = itemXml.getNode("item/@itemdefid")
                collName = (key for key,value in collectionIDs.items() if value==collID).next()
                cellValues = [collName]

            elif self.currentColumns[n][self.COLUMN_DATATYPE] == self.ITEMID:
                cellValues = [itemID]

            elif self.currentColumns[n][self.COLUMN_DATATYPE] == self.ITEMVERSION:
                cellValues = [itemVersion]

            elif self.currentColumns[n][self.COLUMN_DATATYPE] == self.ATTACHMENTLOCATIONS:
                attachmentColumnCount += 1

            elif self.currentColumns[n][self.COLUMN_DATATYPE] in [self.IGNORE, self.TARGETIDENTIFIER, self.TARGETVERSION]:
                if oldRowData != None:
                    cellValues = [oldRowData[n]]
                                                    
            # delimit cell values
            cellValue = delimiter.join(cellValues)

            # display to log if necessary
            if self.currentColumns[n][self.COLUMN_DISPLAY] == "YES":
                self.echo("  %s: %s" % (self.columnHeadings[n], cellValue))
                
            # populate delimited list of cell values in row data
            if len(cellValues) > 0:
                rowData[n] = cellValue
        
        # add Commands cell
        if commandOptionsColumn != -1:
            rowData[commandOptionsColumn] = command
            
        # run Row Post-Script
        if self.postScript.strip() != "":
            try:
                exec self.postScript in {
                                        "IMPORT":0,
                                        "EXPORT":1,
                                        "action":1,
                                        "vars":self.scriptVariables,                                
                                        "rowData":rowData,
                                        "rowCounter":rowCounter,
                                        "testOnly": testOnly,
                                        "institutionUrl":tle.institutionUrl,
                                        "collection":self.collection,
                                        "csvFilePath":self.csvFilePath,
                                        "username":self.username,
                                        "logger":self.logger,
                                        "columnHeadings":self.columnHeadings,
                                        "columnSettings":self.currentColumns,
                                        "successCount":self.successCount,
                                        "errorCount":self.errorCount,
                                        "itemId":itemID,
                                        "itemVersion":itemVersion,
                                        "xml":itemXml,
                                        "xmldom":itemXml.root,
                                        "process":self.process,
                                        "basepath":self.absoluteAttachmentsBasepath,
                                        "sourceIdentifierIndex":sourceIdentifierColumn,
                                        "targetIdentifierIndex":targetIdentifierColumn,
                                        "targetVersionIndex":targetVersionColumn,
                                        "csvData":self.csvArray,
                                        "ebi":self.ebiScriptObject,
                                        "equella":tle,
                                        }             
            except:
                if self.debug:
                    raise
                else:
                    exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
                    formattedException = "".join(traceback.format_exception_only(exceptionType, exceptionValue))[:-1]
                    scriptErrorMsg = "An error occured in the Row Post-Script:\n%s (line %s)" % (formattedException, traceback.extract_tb(exceptionTraceback)[-1][1])
                    raise Exception, scriptErrorMsg
            
            
        if testOnly:
            self.echo("  Item valid for export")
        else:
            self.echo("  Item successfully exported")
        return rowData

    def deconflict(self, filepath, exportedFiles, overwriteMode):
        deconflictedFilepath = filepath
        
        if overwriteMode == self.OVERWRITEEXISTING:
            if filepath in exportedFiles:
                conflictFolderNumber = 0
                conflictFolderUsed = True
                while conflictFolderUsed:
                    conflictFolderNumber += 1
                    conflictFilepath = os.path.join(os.path.dirname(filepath), str(conflictFolderNumber), os.path.basename(filepath))
                    if conflictFilepath not in exportedFiles:
                        conflictFolderUsed = False
                        if not os.path.exists(os.path.dirname(conflictFilepath)):
                            os.makedirs(os.path.dirname(conflictFilepath))
                        deconflictedFilepath = conflictFilepath
                
        elif overwriteMode == self.OVERWRITENONE:
            if os.path.isfile(filepath):
                conflictFolderNumber = 0
                conflictFolderUsed = True
                while conflictFolderUsed:
                    conflictFolderNumber += 1
                    conflictFilepath = os.path.join(os.path.dirname(filepath), str(conflictFolderNumber), os.path.basename(filepath))
                    if not os.path.isfile(conflictFilepath):
                        conflictFolderUsed = False
                        if not os.path.exists(os.path.dirname(conflictFilepath)):
                            os.makedirs(os.path.dirname(conflictFilepath))
                        deconflictedFilepath = conflictFilepath
                                
        return deconflictedFilepath

class UnicodeWriter:
    def __init__(self, f, encoding="utf-8", dialect=csv.excel, **kwds):
        # Redirect output to a queue
        self.queue = cStringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, row):
        self.writer.writerow([s.encode("utf-8") for s in row])
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row) 

# script object used by EBI scripts
class EbiScriptObject(object):
    def __init__(self, parent):
        self.parent = parent

    def getCsvFilePath(self):
        return self.parent.csvFilePath
    def setCsvFilePath(self, value):
        self.parent.csvFilePath = value
    csvFilePath = property(getCsvFilePath, setCsvFilePath)

    def getBasepath(self):
        return self.parent.absoluteAttachmentsBasepath
    def setBasepath(self, value):
        self.parent.absoluteAttachmentsBasepath = value
    basepath = property(getBasepath, setBasepath)
  
    def loadCsv(self):
        self.parent.loadCSV(self.parent.owner)

# Logger class only used by EBI scripts
class Logger:
    def __init__(self, parent):
        self.parent = parent
    def log(self, entry, display = True, log = True):
        if not isinstance(entry, basestring):
            entry = str(entry)
        self.parent.echo(entry=entry, display=display, log=log, style=3)

# Process class only used by EBI scripts
class Process:
    def __init__(self, parent):
        self.parent = parent
        self.halted = False
    def halt(self):
        self.parent.StopProcessing = True
        self.parent.processingStoppedByScript = True
        self.halted = True
    def skip(self):
        self.parent.Skip = True        

