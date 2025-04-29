# equellaclient41.py
#
# Author: Adam Eijdenberg, Dytech Solutions
# Date: 2005
#
# The EQUELLA SOAP abstraction layer for the EQUELLA Bulk Importer. Effectively a wrapper
# for EQUELLA's SOAP API for invocation by Engine.py. Includes the necessary HTTP network
# plumbing. To support EQUELLA down to version 4.1 it uses the EQUELLA 4.1 API and endpoint
# for the majority of functionality. Some functions included for features supported only in
# higher versions of EQUELLA (e.g. control of item ownership for 5.1+).
#
#~ MF - 2007 - added encoding parameter to AddFile method and created toXml and printXml for MockClient
#~ MF - 2008 - fixed bug in search for multiple itemdefs
#~ JK - 2009 - removeNode() removes all matching nodes instead of just the first
#~ JK - 2010 - added support for multiple cookies (needed for clustering)
#~ JK - 2010 - improved file chunking for large file attachments e.g. 1 GB and greater
#~ JK - 2011 - replaced HTTPConnection and HTTPSConnection with urllib2
#~ JK - 2012 - added Engine.py-dependent logging
#~ JK - 2012 - replaced custom cookie management code with standard Python cookielib library
#~ JK - 2012 - added additional HTTP headers
#~ JK - 2013 - improved xpath indexes support
#~ JK - 2013 - removed the ability to use createNode with complex Python datatypes
#~ JK - 2013 - added getText() and getFile() functions to allow download of attachments in the session
#~ JK - 2013 - removeNode() also supports removing attributes
#~ JK - 2014 - removeNode() supports xpath indexes
#~ JK - 2015 - added support for additional xpath predicates

import time, md5, urllib
import sys, urllib2, re, cookielib
from xml.dom.minidom import parse, parseString
from xml.dom import Node
from binascii import b2a_base64
from urlparse import urlparse
import codecs
import os, os.path, traceback, time
from string import ascii_letters
import base64
import wx
import ssl

ASCII_ENC = codecs.getencoder('us-ascii')

SOAP_HEADER_TOKEN = '<s:Header><equella><token>%(token)s</token></equella></s:Header>'

SOAP_REQUEST = '<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:se="http://schemas.xmlsoap.org/soap/encoding/" se:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">%(header)s<s:Body><ns1:%(method)s xmlns:ns1="%(ns)s">%(params)s</ns1:%(method)s></s:Body></s:Envelope>'

SOAP_PARAMETER = '<ns1:%(name)s xsi:type="%(type)s"%(arrayType)s>%(value)s</ns1:%(name)s>'

STANDARD_INTERFACE = {'url':'services/SoapService51', 'namespace':'http://soap.remoting.web.tle.com'}

HTTP_HEADERS = {
'Content-type': 'text/xml',
'SOAPAction': '',
'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8', 'User-Agent':'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.0.6) Gecko/2009011913 Firefox/3.0.6',
'Accept-Language':'en-us,en;q=0.5',
'Accept-Charset':'ISO-8859-1,utf-8;q=0.7,*;q=0.7',
'Keep-Alive':'300'
}

SOAP_ENDPOINT_V1 = 'services/SoapInterfaceV1'
SOAP_ENDPOINT_V2 = 'services/SoapInterfaceV2'
SOAP_ENDPOINT_V41 = 'services/SoapService41'
SOAP_ENDPOINT_V51 = 'services/SoapService51'

def escape(s):
    return s.replace ('&', '&amp;').replace ('<', '&lt;').replace ('>', '&gt;').replace ('"', '&quot;').replace ("'", '&apos;')

def value_as_string (node):
    node.normalize ()
    return ''.join ([x.nodeValue for x in node.childNodes])

def get_named_child_value (node, name):
    return value_as_string(node.getElementsByTagName(name)[0])

def stripNode(node, recurse=False):
    nodesToRemove = []
    nodeToBeStripped = False
    for childNode in node.childNodes:
        # list empty text nodes (to remove if any should be)
        if (childNode.nodeType == Node.TEXT_NODE and childNode.nodeValue.strip() == ""):
            nodesToRemove.append(childNode)

        # only remove empty text nodes if not a leaf node (i.e. a child element exists)
        if childNode.nodeType == Node.ELEMENT_NODE:
            nodeToBeStripped = True

    # remove flagged text nodes
    if nodeToBeStripped:
        for childNode in nodesToRemove:
            node.removeChild(childNode)

    # recurse if specified
    if recurse:
        for childNode in node.childNodes:
            if childNode.nodeType == Node.ELEMENT_NODE:
                stripNode(childNode, True)

def clean_unicode (s):
    if s.__class__ == unicode:
        return ASCII_ENC (s, 'xmlcharrefreplace') [0]
    else:
        return s

def value_as_node_or_string (cur):
    cur.normalize ()
    if len (cur.childNodes) == 1:
        if cur.firstChild.nodeType == cur.TEXT_NODE:
            return value_as_string (cur)
    # Empty node
    return ''

def generate_soap_envelope (name, params, ns, token=None):
    # Need to handle arrays
    def p(value):
        if isinstance(value, list):
            buf = ''
            for i in value:
                buf += '<input>'+ escape (clean_unicode (i)) + '</input>'
            return buf
        else:
            return escape (clean_unicode (value))
    def arrayType(value, type):
        if isinstance(value, list):
            return ' ns1:arrayType="%s[%s]"' % (type, len(value))
        else:
            return ''
    def t(value, type):
        if isinstance(value, list):
            return 'ns1:Array'
        else:
            return type

    return SOAP_REQUEST % {
        'ns': ns,
        'method': name,
        'params': '' if len(params) == 0 else ''.join([SOAP_PARAMETER % {
                'name': 'in' + str(i),
                'type': t(v[2], v[1]),
                'value': p(v[2]),
                'arrayType': arrayType(v[2], v[1])
            } for i, v in enumerate(params)]),
        'header': '' if token == None or len(token) == 0 else SOAP_HEADER_TOKEN % {'token': token}
    }

def urlEncode(text):
    return urllib.urlencode ({'q': text}) [2:]

def generateToken(username, sharedSecretId, sharedSecretValue):
    seed = str (int (time.time ())) + '000'
    id2 = urlEncode (sharedSecretId)
    if(not(sharedSecretId == '')):
        id2 += ':'

    return '%s:%s%s:%s' % (
            urlEncode(username),
            id2,
            seed,
            binascii.b2a_base64(hashlib.md5(
                username + sharedSecretId + seed + sharedSecretValue
            ).digest())
        )

# Class designed to make communicated with TLE very easy!
class TLEClient:
    # First, instantiate an instance of this class.
    # e,g, client = TLEClient ('lcms.yourinstitution.edu.au', 'admin', 'youradminpasssword')
    def __init__ (self, owner, institutionUrl, username, password, proxy = "", proxyusername = "", proxypassword = "", debug = False, sso=0):

        self.debug = debug
        self.owner = owner

        # trim off logon.do if it is in url
        self.institutionUrl = institutionUrl
        urlLogonPagePos = self.institutionUrl.find("/logon.do")
        if urlLogonPagePos != -1:
            self.institutionUrl = self.institutionUrl[:urlLogonPagePos]

        # make certain instituion URL does not end with a slash
        if self.institutionUrl.endswith("/"):
            self.institutionUrl = self.institutionUrl[:-1]

        self.protocol = urlparse(self.institutionUrl)[0]
        self.host = urlparse(self.institutionUrl)[1]
        self.context = urlparse(self.institutionUrl)[2]

        # cookie management
        #self._cookieJar = cookielib.CookieJar()
        #self._cookieProcessor = urllib2.HTTPCookieProcessor(self._cookieJar)
        self._cookieJar = []

        # set proxy
        self.proxy = proxy
        self.proxyusername = proxyusername
        self.proxypassword = proxypassword
        if self.proxy != "":
            password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
            password_mgr.add_password(None, self.proxy, self.proxyusername, self.proxypassword)
            proxy_auth_handler = urllib2.ProxyBasicAuthHandler(password_mgr)
            proxy_handler = urllib2.ProxyHandler({"http": self.proxy})

            # build URL opener with proxy
            #opener = urllib2.build_opener(proxy_handler, proxy_auth_handler, self._cookieProcessor)
            opener = urllib2.build_opener(proxy_handler, proxy_auth_handler)
        else:
            # build URL opener without proxy
            #opener = urllib2.build_opener(self._cookieProcessor)
            opener = urllib2.build_opener()
        urllib2.install_opener(opener)

        if sso:
            self.sessionid = self._createSoapSessionFromToken (createSSOToken (username, password))
        else:
            self.sessionid = self._createSoapSession (username, password)

    def _call (self, name, args, returns=1, facade=SOAP_ENDPOINT_V41, ns='http://soap.remoting.web.tle.com'):
        try:
            headers = {}
            headers.update(HTTP_HEADERS)
            if len(self._cookieJar) > 0:
                headers['Cookie'] = "; ".join(self._cookieJar)

            endpointUrl = self.institutionUrl + "/" + facade
            wsenvelope = generate_soap_envelope (name, args, ns)

            if self.owner.networkLogging:
                self.owner.echo("\n\n*************************************************************")
                self.owner.echo("---------------- COMMUNICATION WITH EQUELLA -----------------")
                self.owner.echo("-------------------------------------------------------------")
                self.owner.echo("SOAP METHOD:                %s()\n" % name)
                self.owner.echo("HTTP REQUEST:\n")
                self.owner.echo(" Endpoint:\n%s\n" % endpointUrl)
                self.owner.echo(" Headers:\n%s\n" % headers)
                if name not in ['uploadFile'] or len(str(args)) < 1000:
                    if name not in ['login']:
                        self.owner.echo(" Request Body:\n" + wsenvelope + "\n")
                        self.owner.echo(" SOAP Input Parameters:\n" + str(args) + "\n\n")
                    else:
                        # generate a copy of the args and SOAP message with password masked
                        maskedargs = (args[0], (args[1][0], args[1][1], "??????"))
                        wsmaskedenvelope = generate_soap_envelope (name, maskedargs, ns)
                        self.owner.echo(" Request Body:\n" + wsmaskedenvelope + "\n")
                        self.owner.echo(" SOAP Input Parameters:\n" + str(maskedargs) + "\n\n")
                else:
                    self.owner.echo(" Request Body:\n<%s characters including base64 data>\n" % len(wsenvelope))
                    printableArgs = "(%s, %s, ('%s', '%s', <%s characters of base64 data>), %s)" % (args[0], args[1], args[2][0], args[2][1], len(args[2][2]), args[3])
                    self.owner.echo(" SOAP Input Parameters:\n" + printableArgs + "\n\n")
                self.owner.echo(" Cookies:\n%s\n" % self._cookieJar)

            # make request
            request = urllib2.Request(endpointUrl, wsenvelope, headers)
            context = ssl._create_unverified_context()
            response = urllib2.urlopen(request, context=context)
            #response = urllib2.urlopen(request)

            # read response and close connection
            s = response.read ()
            response.close()

            responseInfo = response.info()
            headers = {}
            cookie = responseInfo.getheader('set-cookie')

            added_cookie = []
            for cookie_name in self._cookieJar:
                name = cookie_name.upper().split("=")[0].strip()
                if ";" in name:
                    name = name.split(";")[1].strip()
                added_cookie.append(name)

            if cookie is not None:
                for cookie_part in cookie.split(','):
                    for cookie_name in cookie_part.split(','):
                        name = cookie_name.upper().split("=")[0].strip()
                        if ";" in name:
                            name = name.split(";")[1].strip()
                        if not name in ["PATH", "DOMAIN", "EXPIRES", "SECURE", "HTTPONLY"] and not name in added_cookie:
                            # save cookie
                            self._cookieJar.append(cookie_name)

            if self.owner.networkLogging:
                self.owner.echo("HTTP RESPONSE:\n")
                self.owner.echo(" Headers:\n%s\n" % response.info().headers)
                self.owner.echo(" Cookies:\n%s\n" % self._cookieJar)
                self.owner.echo(" Response Body:\n%s\n" % s)

        except urllib2.HTTPError, e:
            httpErrorBody = ""
            httpError = e.reason
            try:
                httpErrorBody = e.read()
            except:
                pass
            if self.owner.networkLogging:
                self.owner.echo("HTTP ERROR CODE: " + str(e.code))
                self.owner.echo(" Error Reason:\n%s\n" % httpError)
                if httpErrorBody != "":
                    self.owner.echo(" Response Body:\n%s\n" % httpErrorBody)
                self.owner.echo("-------------------------------------------------------------")
                self.owner.echo("--------------------- END COMMUNICATION ---------------------")
                self.owner.echo("*************************************************************\n\n")

            errorString = ""

            if self.debug:
                exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
                errorString += "\n" + ''.join(traceback.format_exception(exceptionType, exceptionValue, exceptionTraceback)) + "\n"

            if httpErrorBody != "":
                try:
                    errordom = parseString(httpErrorBody)
                    faultstring = errordom.firstChild.getElementsByTagName("soap:Body")[0].getElementsByTagName("soap:Fault")[0].getElementsByTagName("faultstring")[0].firstChild.nodeValue
                    errorString += faultstring
                except:
                    errorString += httpError
            else:
                errorString += httpError

            raise Exception, errorString

##        except urllib2.URLError, e:
##            raise Exception, str(e.args[0][1])

        except:
            if self.owner.networkLogging:
                self.owner.echo("ERROR: " + str(sys.exc_info()[1]))
                self.owner.echo("-------------------------------------------------------------")
                self.owner.echo("--------------------- END COMMUNICATION ---------------------")
                self.owner.echo("*************************************************************\n\n")
            if self.debug:
                exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
                errorString = "\n" + ''.join(traceback.format_exception(exceptionType, exceptionValue, exceptionTraceback)) + "\n"
            else:
                errorString = sys.exc_info()[1]
            raise Exception, errorString

        try:
            dom = parseString(s)
        except:
            if self.owner.networkLogging:
                self.owner.echo("ERROR: " + str(sys.exc_info()[1]))
                self.owner.echo("-------------------------------------------------------------")
                self.owner.echo("--------------------- END COMMUNICATION ---------------------")
                self.owner.echo("*************************************************************\n\n")
            errorString = ""
            if self.debug:
                exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
                errorString += "\n" + ''.join(traceback.format_exception(exceptionType, exceptionValue, exceptionTraceback)) + "\n"
            errorString += "Cannot parse server response as XML\n" + s
            raise Exception, errorString

        if len (dom.getElementsByTagNameNS ('http://schemas.xmlsoap.org/soap/envelope/', 'Fault')):
            raise Exception, 'Server returned following SOAP error: %s' % dom.toprettyxml ()
        elif returns: # then return a result

            returnValue = dom.firstChild.getElementsByTagName("soap:Body")[0].firstChild.firstChild

            if self.owner.networkLogging:
                returnValueString = "n/a"
                if returnValue != None:
                    try:
                        returnValueString = value_as_string(returnValue)
                    except:
                        returnValueString = str(returnValue)

                self.owner.echo(" SOAP Return Parameter:\n" + str(returnValueString))
                self.owner.echo("-------------------------------------------------------------")
                self.owner.echo("--------------------- END COMMUNICATION ---------------------")
                self.owner.echo("*************************************************************\n\n")


            return returnValue

        if self.owner.networkLogging:
            self.owner.echo(" SOAP Return Parameter:\nn/a")
            self.owner.echo("-------------------------------------------------------------")
            self.owner.echo("--------------------- END COMMUNICATION ---------------------")
            self.owner.echo("*************************************************************\n\n")


    def _createSoapSessionFromToken (self, token):
        result = self._call ('loginWithToken', (
                ('token', 'xsd:string', token),
            ))
        return value_as_string (result)

    def _createSoapSession (self, username, password):
        result = self._call ('login', (
                ('username', 'xsd:string', username),
                ('password', 'xsd:string', password),
            ))
        return value_as_string (result)

    def logout (self):
        self._call ('logout', (
            ))

    def getFile(self, url, filepath):
        headers = {}
##        headers.update(HTTP_HEADERS)
        headers.update(HTTP_HEADERS)
        if len(self._cookieJar) > 0:
            headers['Cookie'] = "; ".join(self._cookieJar)

        retry = True
        while retry:
            try:
                request = urllib2.Request(url, headers=headers)
                context = ssl._create_unverified_context()
                response = urllib2.urlopen(request, context=context)
                f = open(filepath, "wb")
                f.write(response.read())
                try:
                    f.close()
                except:
                    pass
                retry = False

            except urllib2.URLError, err:
                if hasattr(err, 'reason'):
                    if str(err.reason).find("10054") != -1:
                        print err.reason
                        print "Retrying..."
                    else:
                        retry = False
                        raise Exception, "url/http error: " + str(err.reason)
                if hasattr(err, 'code'):
                        retry = False
                        raise Exception, "url/http error code: " + str(err.code)
            except:
                err = sys.exc_info()[1]
                if str(err).find("10054") != -1:
                    print err
                    print "Retrying..."
                else:
                    retry = False
                    raise err

        return response.info()

    def getText(self, url):
        headers = {}
        headers.update(HTTP_HEADERS)
        retry = True
        while retry:
            try:
                request = urllib2.Request(url, headers=headers)
                context = ssl._create_unverified_context()
                response = urllib2.urlopen(request, context=context)
                retry = False
                return response.read()
            except urllib2.URLError, err:
                if str(err.reason).find("10054"):
                    print err.reason
                    print "Retrying..."
                else:
                    retry = False
                    raise err.reason
            except:
                err = sys.exc_info()[1]
                if str(err).find("10054") != -1:
                    print err
                    print "Retrying..."
                else:
                    retry = False
                    raise err

        return response.info(), data

    def _unzipFile (self, stagingid, zipfile, outpath):
        self._call ('unzipFile', (
                ('item_uuid', 'xsd:string', stagingid),
                ('zipfile', 'xsd:string', zipfile),
                ('outpath', 'xsd:string', outpath),
            ), returns=0)

    def _enumerateItemDefs (self):
        result = self._call('getContributableCollections', (
            ))
        return dict ([(get_named_child_value (itemdef, 'name'), {'uuid': get_named_child_value (itemdef, 'uuid')}) for itemdef in parseString (value_as_string (result)).getElementsByTagName ('itemdef')])

    def _newItem (self, itemdefid):
        result = self._call ('newItem', (
                ('itemdefid', 'xsd:string', itemdefid),
            ))
        return parseString (value_as_string (result))

    # _newVersionItem() only supported in 4.1 and higher
    def _newVersionItem (self, itemid, itemversion, copyattachments):
        result = self._call ('newVersionItem', (
                ('itemid', 'xsd:string', itemid),
                ('version', 'xsd:int', itemversion),
                ('copyattachments', 'xsd:boolean', str(copyattachments)),
            ), 1, SOAP_ENDPOINT_V41)
        return parseString (value_as_string (result))

    def _startEdit (self, itemid, itemversion, copyattachments):
        result = self._call ('editItem', (
                ('itemid', 'xsd:string', itemid),
                ('version', 'xsd:int', str (itemversion)),
                ('copyattachments', 'xsd:boolean', str (copyattachments)),
            ))
        return parseString (value_as_string (result))

    def _forceUnlock (self, itemid, itemversion):
        result = self._call ('unlock', (
                ('itemid', 'xsd:string', itemid),
                ('version', 'xsd:int', str (itemversion)),
            ), returns=0)
        return result

    def _stopEdit (self, xml, submit):
        result = self._call ('saveItem', (
                ('itemXML', 'xsd:string', xml),
                ('bSubmit', 'xsd:boolean', submit),
            ))
        return result

    def _cancelEdit (self, itemid, itemversion):
        result = self._call ('cancelItemEdit', (
                ('itemid', 'xsd:string', itemid),
                ('version', 'xsd:int', str (itemversion)),
            ))
        return result

    def _uploadFile (self, stagingid, filename, data, overwrite):
        result = self._call ('uploadFile', (
                ('item_uuid', 'xsd:string', stagingid),
                ('filename', 'xsd:string', filename),
                ('data', 'xsd:string', data),
                ('overwrite', 'xsd:boolean', overwrite),
            ))
        return result

    def _deleteAttachmentFile (self, stagingid, filename):
        result = self._call ('deleteFile', (
                ('item_uuid', 'xsd:string', stagingid),
                ('filename', 'xsd:string', filename),
            ))
        return result

    def _deleteItem (self, itemid, itemversion):
        result = self._call ('deleteItem', (
                ('itemid', 'xsd:string', itemid),
                ('version', 'xsd:int', str (itemversion)),
            ))
        return result

    def getItem (self, itemid, itemversion, select=''):
        result = self._call ('getItem', (
                ('itemid', 'xsd:string', itemid),
                ('version', 'xsd:int', str (itemversion)),
                ('select', 'xsd:string', select),
            ))
        return PropBagEx(value_as_string(result))

    def getItemFilenames (self, itemUuid, itemVersion, path, system):
        paramSystem = 'false'
        if system:
            paramSystem = 'true'
        result = self._call ('getItemFilenames', (
                ('itemUuid', 'xsd:string', itemUuid),
                ('itemVersion', 'xsd:int', str (itemVersion)),
                ('path', 'xsd:string', path),
                ('system', 'xsd:boolean', paramSystem),
            ), 1, SOAP_ENDPOINT_V51)

        resultList = []
        for childNode in result.childNodes:
            resultList.append(childNode.firstChild.nodeValue)
        return resultList


    def queryCount (self, itemdefs, where):
        result = self._call ('queryCount', (
                ('itemdefs', 'xsd:string', itemdefs),
                ('where', 'xsd:string', where),
            ))
        return int(value_as_string(result))

    # Return an itemdef UUID given a human displayable name.
    # e.g. itemdefUUID = client.getItemdefUUID ('K-12 Educational Resource')
    def getItemdefUUID (self, itemdefName):
        return self._enumerateItemDefs () [itemdefName] ['uuid']

    # Return an ident given a human displayable name.
    # e.g. itemdefUUID = client.getItemdefUUID ('K-12 Educational Resource')
    def getItemdefIdent (self, itemdefName):
        return self._enumerateItemDefs () [itemdefName] ['ident']

    # Create a new repository item of the type specified. See NewItemClient for methods that can be called on the return type.
    # e.g. item = client.createNewItem (itemdefUUID)
    def createNewItem (self, itemdefid):
        rv = NewItemClient(self, self.owner, self._newItem(itemdefid), debug=self.debug)
        return rv

    # Create a new version of the item specified. See NewItemClient for methods that can be called on the return type.
    # e.g. item = client.newVersionItem(itemUUID, "2", itemdefUUID)
    # NOTE: only supported in 4.1 and higher
    def newVersionItem(self, itemid, version, copyattachments = True):
        rv = NewItemClient(self, self.owner, self._newVersionItem(itemid, str(version), copyattachments), debug=self.debug)
        return rv

    # Edit particular item. See NewItemClient for methods that can be called on the return type.
    # e.g. item = client.createNewItem (itemdefUUID)
    def editItem (self, itemid, version, copyattachments):
        dom = self._startEdit (itemid, version, copyattachments)
        if not len (dom.getElementsByTagName ('item')):
            self._forceUnlock (itemid, version)
            dom = self._startEdit (itemid, version, copyattachments)
        rv = NewItemClient (self, self.owner, dom, newversion=0, copyattachments=(copyattachments == 'true'), debug=self.debug)
        return rv

    def search(self, offset=0, limit=10, select='*', itemdefs=[], where='', query='', onlyLive=True, orderType=0, reverseOrder=False):
        paramReverseOrder = 'false'
        if reverseOrder:
            paramReverseOrder = 'true'

        paramOnlyLive = 'false'
        if onlyLive:
            paramOnlyLive = 'true'

        result = self._call ('searchItems', (
                ('freetext', 'xsd:string', query),
                ('collectionUuids', 'xsd:string', itemdefs),
                ('whereClause', 'xsd:string', where),
                ('onlyLive', 'xsd:boolean', paramOnlyLive),
                ('orderType', 'xsd:int', str (orderType)),
                ('reverseOrder', 'xsd:boolean', paramReverseOrder),
                ('offset', 'xsd:int', str(offset)),
                ('limit', 'xsd:int', str(limit)),
            ))
        return PropBagEx(value_as_string(result))

    def searchItemsFast(self, freetext='', collectionUuids=[], whereClause='', onlyLive=True, orderType=0, reverseOrder=False, offset=0, length=50, resultCategories=["basic"]):
        paramReverseOrder = 'false'
        if reverseOrder:
            paramReverseOrder = 'true'

        paramOnlyLive = 'false'
        if onlyLive:
            paramOnlyLive = 'true'

        result = self._call ('searchItemsFast', (
                ('freetext', 'xsd:string', freetext),
                ('collectionUuids', 'xsd:string', collectionUuids),
                ('whereClause', 'xsd:string', whereClause),
                ('onlyLive', 'xsd:boolean', paramOnlyLive),
                ('orderType', 'xsd:int', str (orderType)),
                ('reverseOrder', 'xsd:boolean', paramReverseOrder),
                ('offset', 'xsd:int', str(offset)),
                ('length', 'xsd:int', str(length)),
                ('resultCategories', 'xsd:string', resultCategories),
            ))
        return PropBagEx(value_as_string(result))

    def setOwner (self, itemid, itemversion, ownerid):
        result = self._call ('setOwner', (
                ('itemid', 'xsd:string', itemid),
                ('version', 'xsd:int', str (itemversion)),
                ('userId', 'xsd:string', ownerid),
            ), 1, facade = SOAP_ENDPOINT_V51)

    def setOwnerByUsername(self, itemID, version, username, saveNonexistentUsernamesAsIDs = False):
        matchingUsers = self.searchUsersByGroup("", username)
        matchingUserNodes = matchingUsers.getNodes("user", False)

        # if any matches get first matching user
        if len(matchingUserNodes) > 0:
            userID = matchingUserNodes[0].getElementsByTagName("uuid")[0].firstChild.nodeValue

            # set item owner
            self.setOwner(itemID, version, userID)
        else:
            if saveNonexistentUsernamesAsIDs:
                self.setOwner(itemID, version, username)
            else:
                raise Exception, "User [%s] not found in EQUELLA" % username

    def addSharedOwner (self, itemid, itemversion, ownerid):
        result = self._call ('addSharedOwner', (
                ('itemid', 'xsd:string', itemid),
                ('version', 'xsd:int', str (itemversion)),
                ('userId', 'xsd:string', ownerid),
            ))

    def addSharedOwners (self, itemid, itemversion, collaboratorUsernames, saveNonexistentUsernamesAsIDs = False):
        for username in collaboratorUsernames:

            matchingUsers = self.searchUsersByGroup("", username)
            matchingUserNodes = matchingUsers.getNodes("user", False)

            # if any matches get first matching user
            if len(matchingUserNodes) > 0:
                userid = matchingUserNodes[0].getElementsByTagName("uuid")[0].firstChild.nodeValue

                # set item owner
                self.addSharedOwner(itemid, itemversion, userid)
            else:
                if saveNonexistentUsernamesAsIDs:
                    self.addSharedOwner(itemid, itemversion, username)
                else:
                    raise Exception, "User [%s] not found in EQUELLA" % username

    def removeSharedOwner (self, itemid, itemversion, ownerid):
        result = self._call ('removeSharedOwner', (
                ('itemid', 'xsd:string', itemid),
                ('version', 'xsd:int', str (itemversion)),
                ('userId', 'xsd:string', ownerid),
            ))


    def getUser (self, userId):
        result = self._call ('getUser', (
                ('userId', 'xsd:string', userId),
            ), 1, facade = SOAP_ENDPOINT_V51)
        return PropBagEx(value_as_string(result))

    def searchUsersByGroup (self, groupUuid, searchString):
        result = self._call ('searchUsersByGroup', (
                ('groupUuid', 'xsd:string', groupUuid),
                ('searchString', 'xsd:string', searchString),
            ), 1, SOAP_ENDPOINT_V51)
        return PropBagEx(value_as_string(result))

    def activateItemAttachments (self, uuid, version, courseCode, attachments):
        self._call ('activateItemAttachments', (
                ('uuid', 'xsd:string', uuid),
                ('version', 'xsd:int', version),
                ('courseCode', 'xsd:string', courseCode),
                ('attachments', 'xsd:string', attachments),
            ))

    def addUser (self, uuid, username, password, firstname, lastname, email):
        return value_as_string(self._call ('addUser', (
                ('ssid', 'xsd:string', self.sessionid),
                ('uuid', 'xsd:string', uuid),
                ('name', 'xsd:string', username),
                ('password', 'xsd:string', password),
                ('first', 'xsd:string', firstname),
                ('last', 'xsd:string', lastname),
                ('email', 'xsd:string', email),
            ), facade=SOAP_INTERFACE_V2))

    def editUser (self, uuid, username, password, firstname, lastname, email):
        return value_as_string(self._call ('editUser', (
                ('ssid', 'xsd:string', self.sessionid),
                ('uuid', 'xsd:string', uuid),
                ('name', 'xsd:string', username),
                ('password', 'xsd:string', password),
                ('first', 'xsd:string', firstname),
                ('last', 'xsd:string', lastname),
                ('email', 'xsd:string', email),
            ), facade=SOAP_INTERFACE_V2))

    def removeUser (self, uuid):
        self._call ('removeUser', (
                ('ssid', 'xsd:string', self.sessionid),
                ('uuid', 'xsd:string', uuid),
            ), facade=SOAP_INTERFACE_V2)

    def addUserToGroup (self, uuid, groupId):
        self._call ('addUserToGroup', (
                ('ssid', 'xsd:string', self.sessionid),
                ('uuid', 'xsd:string', uuid),
                ('groupid', 'xsd:string', groupId),
            ), facade=SOAP_INTERFACE_V2)

    def removeUserFromGroup (self, uuid, groupId):
        self._call ('removeUserFromGroup', (
                ('ssid', 'xsd:string', self.sessionid),
                ('uuid', 'xsd:string', uuid),
                ('groupid', 'xsd:string', groupId),
            ), facade=SOAP_INTERFACE_V2)

    def removeUserFromAllGroups (self, userId):
        self._call ('removeUserFromAllGroups', (
                ('ssid', 'xsd:string', self.sessionid),
                ('userUuid', 'xsd:string', userId),
            ), facade=SOAP_INTERFACE_V2)

    def isUserInGroup (self, userId, groupId):
        return value_as_string(self._call ('isUserInGroup', (
                ('ssid', 'xsd:string', self.sessionid),
                ('userUuid', 'xsd:string', userId),
                ('groupUuid', 'xsd:string', groupId),
            ), facade=SOAP_INTERFACE_V2)) == 'true'


class NewItemClient:
    def __init__ (self, parClient, owner, newDom, newversion=0, copyattachments=1, debug = False):
        self.debug = debug
        self.owner = owner
        self.parClient = parClient
        self.newDom = newDom
        self.prop = PropBagEx(self.newDom.firstChild)
        self.xml = self.newDom.firstChild
        self.uuid = self.prop.getNode("item/@id")
        self.version =  self.prop.getNode("item/@version")

        if copyattachments:
            self.stagingid = self.prop.getNode("item/staging")

        # remove old version references to non-existent start-pages
        if newversion and not copyattachments:
            attachmentsNode.removeNode("item/attachments/attachment")

    def getUUID (self):
        return self.uuid

    def getVersion (self):
        return self.version

    def getItemdefUUID (self):
        return self.prop.getNode("item/@itemdefid")

    def read_in_chunks(self, file_object, chunk_size=(1024 * 1024)):
        while True:
            data = file_object.read(chunk_size)
            if not data:
                break
            yield data

    # Upload a file as an attachment to this item. path is where the item will live inside of the repository, and should not contain a preceding slash.
    # e.g. item.attachFile ('support/song.wav', file ('c:\\Documents and Settings\\adame\\Desktop\\song.wav', 'rb'))
    # Parent directories are automatically created as required.
    # Uploads file in chunks of 16MB. If file is large (e.g. over 16MB) pass in parameter showstatus as a prefix to a progress report
    # e.g. item.attachFile ('support/song.wav', file ('video.avi', 'rb'), '     Progress: ')
    def attachFile (self, path, attachment, showstatus=None, chunk_size=(1024 * 2048)):
        if showstatus:
            if self.debug:
                self.owner.echo(showstatus + " Uploading...")
            else:
                self.owner.log.SetReadOnly(False)
                self.owner.log.AppendText(showstatus + " Uploading...")
                self.owner.log.SetReadOnly(True)
                sys.stdout.write(showstatus + " Uploading...")
                sys.stdout.flush()
        try:
            firstChunk = "true"
            filesize = os.path.getsize(attachment.name)
            uploaded = 0
            for chunk in self.read_in_chunks(attachment, chunk_size):
                wx.GetApp().Yield()
                if self.owner.StopProcessing:
                    if self.debug:
                        self.owner.echo(showstatus + " Halted by user")
                    else:
                        self.owner.log.SetReadOnly(False)
                        self.owner.log.AppendText("\n")
                        self.owner.log.SetReadOnly(True)

                        sys.stdout.write("Halted by user\n")
                        self.owner.echo(showstatus + " Uploading...Halted by user", False)
                    break
                uploaded += len(chunk)
                encodedChunk = base64.b64encode(chunk)

                self.parClient._uploadFile (self.stagingid, path, encodedChunk, firstChunk)

                if firstChunk == "true":
                    firstChunk = "false"
                if showstatus:
                    if self.debug:
                        progressReport = showstatus + " chunk=%s, uploaded=%s/%s" % (len(chunk), uploaded, filesize)
                        self.owner.echo(progressReport)
                        if uploaded >= filesize:
                            self.owner.echo("    Done")
                        self.owner.tryPausing("    [Paused]")
                    else:
                        if uploaded >= filesize:
                            self.owner.echo(showstatus + " Uploading...Done", False)
                            sys.stdout.write("Done\n")

                            self.owner.log.DocumentEnd()
                            self.owner.log.SetReadOnly(False)
                            self.owner.log.DelLineLeft()
                            self.owner.log.AppendText(showstatus + " Uploading...Done\n")
                            self.owner.log.SetReadOnly(True)
                        else:
                            sys.stdout.write(".")
                            sys.stdout.flush()

                            progressString = showstatus + " Uploading...%s%%" % ((uploaded * 100)/ filesize)
                            self.owner.log.DocumentEnd()
                            self.owner.log.SetReadOnly(False)
                            self.owner.log.DelLineLeft()
                            self.owner.log.AppendText(progressString)
                            self.owner.log.SetReadOnly(True)
                            self.owner.tryPausing("    [Paused]", newline = True)
        except:
            if not self.debug:
                sys.stdout.write("\n")
            raise

    def unzipFile (self, path, name):
        self.parClient._unzipFile (self.stagingid, path, name)

    # Uploads an IMS package
    def attachIMS (self, file, filename='package.zip', title='', showstatus=None, upload = True, size=1024, uuid="", chunk_size=(4048 * 4048)):
        imsfilename = '_IMS/' + filename
        if upload:
            self.attachFile (imsfilename, file, showstatus, chunk_size)
            if not self.owner.StopProcessing:
                self.parClient._unzipFile (self.stagingid, imsfilename, filename)

        self.prop.setNode("item/itembody/packagefile", filename)
        self.prop.setNode("item/itembody/packagefile/@name", title)
        self.prop.setNode("item/itembody/packagefile/@size", str(size))
        self.prop.setNode("item/itembody/packagefile/@stored", "true")
        if uuid != '':
            self.prop.setNode("item/itembody/packagefile/@uuid", uuid)


    # Uploads a SCORM package
    def attachSCORM (self, file, filename, description, showstatus=None, upload = True, size=1024, uuid = '', chunk_size=(4048 * 4048)):
        if upload:
            scormfilename = '_SCORM/' + filename
            self.attachFile(scormfilename, file, showstatus, chunk_size)
            self.parClient._unzipFile (self.stagingid, scormfilename, filename)

        attachment = self.prop.newSubtree("item/attachments/attachment")
        attachment.createNode("@type", "custom")
        attachment.createNode("type", "scorm")
        attachment.createNode("attributes/entry/string", "fileSize")
        attachment.createNode("attributes/entry/long", str(size))
        scormVersionEntry = attachment.newSubtree("attributes/entry")
        scormVersionEntry.createNode("string", "SCORM_VERSION")
        scormVersionEntry.createNode("string", "1.2")
        attachment.createNode("file", filename)
        attachment.createNode("description", description)
        if uuid != '':
            attachment.createNode("uuid", uuid)

    def attachResource (self, resourceItemUuid, resourceItemVersion, resourceDescription, uuid = '', attachmentUuid = ""):
        # create attachment subtree
        attachment = self.prop.newSubtree("item/attachments/attachment")
        attachment.createNode("@type", "custom")
        attachment.createNode("type", "resource")
        if attachmentUuid != "":
            attachment.createNode("file", attachmentUuid)
        else:
            attachment.createNode("file", "")
        attachment.createNode("description", resourceDescription)
        if uuid != '':
            attachment.createNode("uuid", uuid)

        # create uuid entry and append to attributes
        attributeEntry = attachment.newSubtree("attributes/entry")
        attributeEntry.createNode("string", "uuid")
        attributeEntry.createNode("string", resourceItemUuid)

        # create type entry and append to attributes
        attributeEntry = attachment.newSubtree("attributes/entry")
        attributeEntry.createNode("string", "type")
        if attachmentUuid == "":
            attributeEntry.createNode("string", "p")
        else:
            attributeEntry.createNode("string", "a")

        # create version entry and append to attributes
        attributeEntry = attachment.newSubtree("attributes/entry")
        attributeEntry.createNode("string", "version")
        attributeEntry.createNode("int", str(resourceItemVersion))

    # Mark an attached file as a start page to appear on the item summary page.
    # e.g. item.addStartPage ('Great song!', 'support/song.wav')
    def addStartPage (self, description, path, size=1024, uuid='', thumbnail = ""):

        # delete existing attachment noes of the same /file and /description
        self.prop.removeNode("item/attachments/attachment[file = '%s']" % path)

        attachment = self.prop.newSubtree("item/attachments/attachment")
        attachment.createNode("@type", "local")
        attachment.createNode("file", path)
        attachment.createNode("description", description)
        attachment.createNode("size", str(size))
        if uuid != '':
            attachment.createNode("uuid", uuid)
        if thumbnail != "":
            attachment.createNode("thumbnail", thumbnail)

    def deleteAttachments(self):
        self.getXml().removeNode('item/attachments/attachment')
        self.parClient._deleteAttachmentFile(self.stagingid,"")

    # Add a URL as a resource to this item.
    # e.g. item.addUrl ('Interesting link', 'http://www.thelearningedge.com.au/')
    def addUrl (self, description, url, uuid=''):
        attachment = self.prop.newSubtree("item/attachments/attachment")
        attachment.createNode("@type", "remote")
        attachment.createNode("conversion", "true")
        attachment.createNode("file", url)
        attachment.createNode("description", description)
        if uuid != '':
            attachment.createNode("uuid", uuid)

    # Print tabbed XML for this item, useful for debugging.
    def printXml (self):
        print ASCII_ENC (self.newDom.toprettyxml (), 'xmlcharrefreplace') [0]

    # Print tabbed XML for this item, useful for debugging.
    def toXml (self, enc="utf-8"):
        return self.newDom.toprettyxml ("  ", "\n", enc)

    def forceUnlock(self):
        self.parClient._forceUnlock(self.getUUID (), self.getVersion (), self.getItemdefUUID ())

    def cancelEdit(self):
        self.parClient._cancelEdit(self.getUUID (), self.getVersion (), self.getItemdefUUID ())

    def delete (self):
        self.parClient._deleteItem(self.getUUID (), self.getVersion (), self.getItemdefUUID ())

    # Save this item into the repository.
    # e.g. item.submit ()
    def submit (self, workflow=1):
        self.parClient._stopEdit (self.newDom.toxml(), ('false', 'true') [workflow])

    def getXml(self):
        return self.prop

# PropBag classes - was propbag.py

class PropBagEx:
    def __init__ (self, s, encoding="utf8"):
        if isinstance (s, PropBagEx) :
            self.document = s.document
            self.root = s.root
        elif isinstance (s, str) or isinstance(s, unicode):
            self.document = parseString(s.encode(encoding))
            self.root = None
            for childNode in self.document.childNodes:
                if childNode.nodeType == Node.ELEMENT_NODE:
                    self.root = childNode
                    break
        elif isinstance (s, file) :
            self.document = parse (s)
            self.root = None
            for childNode in self.document.childNodes:
                if childNode.nodeType == Node.ELEMENT_NODE:
                    self.root = childNode
                    break
        else:
            self.document = s.ownerDocument
            self.root = s
        self.xpath = XPath()

    def getNodes (self, xpath, string=True):
        return self.xpath.selectNodes(xpath, self.root, string)

    # Get an XML node on this item. xpath should begin with item, but should not have a preceding slash.
    # e.g. item.getNode ('item/description', 'This item describes ....')
    def getNode (self, xpath):
        nodes = self.getNodes (xpath)
        if len(nodes) > 0:
            return nodes[0]
        return None

    def _createNewNodes(self, xpath, onlyOne = False):
        # determine how much of xpath already exists
        rhs = xpath
        xpathParts = []
        i = 0
        missingParents = False
        while rhs != "":
            lhs, rhs, delimter = self.xpath.splitFirstOuter(rhs, ["/"])
            xpathParts.append(lhs)
            if not missingParents and rhs != "" and len(self.getNodes("/".join(xpathParts))) != 0:
                i += 1
            else:
                missingParents = True
        if i != 0:
            parents = self.getNodes("/".join(xpathParts[0:i]), False)
        else:
            parents = self.getNodes("", False)

        # loop over last existing nodes in xpath and add necessary elements and attributes
        # and return leaf nodes
        returnNodes = []
        for parent in parents:
            for j, childName in enumerate(xpathParts[i:]):
                k = childName.find("[")
                if k != -1:
                    childName = childName[:k]
                if childName[0] != "@":
                    childNode = self.document.createElement(childName)
                    if j + 1 == len(xpathParts[i:]):
                        returnNodes.append(childNode)
                    parent.appendChild(childNode)
                    parent = childNode
                elif j + 1 == len(xpathParts[i:]):
                    parent.setAttribute(childName[1:], "")
                    returnNodes.append(parent.getAttributeNode(childName[1:]))
                else:
                    raise Exception, "Attribute cannot have a child node '%s'" % xpath
            if onlyOne:
                break
        return returnNodes

    def removeNode (self, xpath):
        matchingNodes = self.getNodes(xpath, False)
        for matchingNode in matchingNodes:
            if matchingNode.nodeType == Node.ATTRIBUTE_NODE:
                ownerElement = matchingNode.ownerElement
                ownerElement.removeAttribute(matchingNode.nodeName)
            else:
                parentNode = matchingNode.parentNode
                parentNode.removeChild(matchingNode)

    # Print tabbed XML for this item, useful for debugging.
    def printXml (self):
        print ASCII_ENC (self.root.toprettyxml (), 'xmlcharrefreplace') [0]

    # return underlying minidom of XmlWrapper
    def toXml (self):
        return self.root.toxml ()

    def nodeCount(self, xpath):
        return len(self.getNodes(xpath))

    def createNode (self, xpath, value):
        newNodes = self._createNewNodes(xpath)
        for matchingNode in newNodes:
            if matchingNode.nodeType == Node.ATTRIBUTE_NODE:
                matchingNode.nodeValue = value
            else:
                matchingNode.appendChild(self.document.createTextNode(value))

    def setNode (self, xpath, value, createNew=False):
        if createNew:
            self.createNode(xpath, value)
        else:
            matchingNodes = self.getNodes(xpath, False)
            for matchingNode in matchingNodes:
                if matchingNode.nodeType == Node.ATTRIBUTE_NODE:
                    matchingNode.nodeValue = value
                else:
                    # delete all text nodes
                    for child in matchingNode.childNodes:
                        if child.nodeType == Node.TEXT_NODE:
                            matchingNode.removeChild(child)
                    # add text node
                    matchingNode.appendChild(self.document.createTextNode(value))
            if len(matchingNodes) == 0:
                self.createNode(xpath, value)

    def getSubtree(self, xpath):
        return PropBagEx(self.getNodes(xpath, string=False) [0])

    def newSubtree(self, xpath):
        return PropBagEx(self._createNewNodes(xpath, onlyOne = True)[0])

    # deprecated
    def iterate(self, xpath):
        return self.getSubtrees(xpath)

    def getSubtrees(self, xpath):
        nodes = self.getNodes(xpath, string=False)
        return [PropBagEx(x) for x in nodes]

    def nodeExists(self, xpath):
        return self.nodeCount(xpath) > 0

    def validateXpath(self, xpath):
        return self.xpath.validateXpath(xpath)

class XPath:
    def __init__ (self):
        self.debugLevel = 0
        self.testNode = parseString("<xml/>").firstChild

    # selectNodes() returns list of strings or nodes for the given
    # XPath relative to the given node
    def selectNodes(self, xpath, curNode, asStrings = False):
        self.validateXpath(xpath)
        return self._selectNodes(xpath, asStrings, curNode, False, self.debugLevel)

    # validateXpath() validates the given XPath (lightweight)
    def validateXpath(self, xpath):
        self._selectNodes(xpath, False, self.testNode, True, self.debugLevel, self.debugLevel)
        return True

    def _selectNodes(self, xpath, asStrings, curNode, validateOnly = False, dl = 0, sd = 0):
        if dl > 1:
            print " DEBUG", "".ljust(sd),"_selectNodes(<%s>, %s%s)" % (curNode.nodeName, xpath, ", validateOnly" if validateOnly else "")

        step, remainingXpath, delimiter = self.splitFirstOuter(xpath, ["/"], False, dl = dl, sd = sd + 1)

        stepNodename = step
        stepPredicate = ""
        stepIsAttribute = False
        matchingNodes = []

        i = step.find("[")

        if i != -1:
            stepNodename = step[:i]
            stepPredicate = step[i + 1:-1]
            if stepPredicate == "":
                raise Exception, "Empty predicate ('%s')" % step

        # XPath validation only
        if validateOnly:
            if stepNodename not in ["", ".", "..", "*", "text()", "node()"]:
                if stepNodename.startswith("@"):
                    nodename = stepNodename[1:]
                else:
                    nodename = stepNodename

                # validate nodename
                if nodename not in ["*", "node()"]:
                    if not all(c in ascii_letters+'-_.0123456789' for c in nodename) or nodename[0] in '-_.0123456789':
                        raise Exception, "Invalid token in xpath ('%s')" % stepNodename

                # evaludate predicate to validate it
                if stepPredicate != "":
                    self.evaluateCondition(stepPredicate, curNode, validateOnly, 0, 0, dl = dl, sd = sd + 1)

            # if more xpath left recurse
            if remainingXpath != "":
                self._selectNodes(remainingXpath, False, curNode, validateOnly, dl = dl, sd = sd + 1)

            if dl >= 1:
                print " DEBUG", "".ljust(sd),"_selectNodes(<%s>, %s) -> %s" % (curNode.nodeName, xpath, "VALID")
            return []

        # XPath Processing

        # check if attribute
        if stepNodename.startswith("@") or stepNodename == "node()":
            if stepNodename.startswith("@"):
                attrNodename = stepNodename[1:]
            else:
                attrNodename = stepNodename

            if curNode.nodeType == Node.ELEMENT_NODE:
                if curNode.hasAttribute(attrNodename):
                    # match on attribute name
                    matchingNodes.append(curNode.getAttributeNode(attrNodename))

                elif attrNodename == "*" or attrNodename == "node()":
                    # wildcard so iterate through attributes and do predicate test on each
                    predicateMatch = False
                    i = 0
                    for key in curNode.attributes.keys():
                        i += 1
                        # check for predicate
                        if stepPredicate == "":
                            # no predicate
                            predicateMatch = True
                        else:
                            # get count of attributes (for last())
                            childNodeCount = len(curNode.attributes)

                            # evaluate attriute wildcard predicate
                            predicateMatch = self.evaluateCondition(stepPredicate, curNode.attributes[key], validateOnly, i, childNodeCount, dl = dl, sd = sd + 1)

                        # append node to return if matching
                        if predicateMatch:
                            matchingNodes.append(curNode.attributes[key])

        # check if named element
        if stepNodename not in ["", ".", "..", "text()"] and not stepNodename.startswith("@"):

            # get count of child nodes (for last())
            childNodeCount = 0
            for childNode in curNode.childNodes:
                if childNode.nodeType == Node.ELEMENT_NODE and (childNode.nodeName == stepNodename or stepNodename == "*"):
                    childNodeCount += 1

            # iterate through elements
            i = 0
            for childNode in curNode.childNodes:
                if childNode.nodeType == Node.ELEMENT_NODE:
                    predicateMatch = False

                    # only include child elements whose names match
                    if stepNodename in [childNode.nodeName, "*", "node()"]:
                        i += 1
                        # check for predicate
                        if stepPredicate == "":
                            # no predicate
                            predicateMatch = True
                        else:
                            # evaluate predicate
                            predicateMatch = self.evaluateCondition(stepPredicate, childNode, validateOnly, i, childNodeCount, dl = dl, sd = sd + 1)
                        if predicateMatch:
                            if remainingXpath != "":
                                if remainingXpath.startswith("/"):

                                    # xpath was split on a double slash
                                    remainingXpath = remainingXpath[1:]
                                    matchingNodes += self.queryAllChildElements(remainingXpath, childNode, validateOnly)

                                # more relative xpath remaining so recurse _selectNodes() and include results for returning
                                matchingNodes += self._selectNodes(remainingXpath, asStrings=False, curNode = childNode, validateOnly=validateOnly, dl = dl, sd = sd + 1)

                            else:
                                # no xpath left so include child node for returning
                                matchingNodes.append(childNode)

        # check if empty string
        elif stepNodename == "":
            if remainingXpath != "":
                # absolute path
                curNode = curNode.ownerDocument
                if remainingXpath.startswith("/"):
                    # xpath was split on a double slash
                    remainingXpath = remainingXpath[1:]
                    matchingNodes += self.queryAllChildElements(remainingXpath, curNode, validateOnly)

                matchingNodes += self._selectNodes(remainingXpath, asStrings=False, curNode = curNode, validateOnly=validateOnly, dl = dl, sd = sd + 1)
            else:
                # empty xpath
                matchingNodes.append(curNode)

        # check if self or parent
        elif stepNodename == ".":
            matchingNodes.append(curNode)
        elif stepNodename == "..":
            if remainingXpath != "":
                # more relative xpath remaining so recurse _selectNodes()
                matchingNodes += self._selectNodes(remainingXpath, asStrings=False, curNode = curNode.parentNode, validateOnly=validateOnly, dl = dl, sd = sd + 1)

            else:
                matchingNodes.append(curNode.parentNode)

        # check if text() node test
        elif stepNodename == "text()":
            for child in curNode.childNodes:
                if child.nodeType == Node.TEXT_NODE:
                    matchingNodes.append(child)

        # return matches as nodes or strings
        if not asStrings:
            returnValues = matchingNodes
        else:
            # determine node values depending on elements or attributes
            returnValues = []
            for node in matchingNodes:
                if node.nodeType == Node.ATTRIBUTE_NODE or node.nodeType == Node.TEXT_NODE:
                    returnValues.append(node.nodeValue)
                else:
                    # concatenate all the text nodes
                    value = ""
                    for child in node.childNodes:
                        if child.nodeType == Node.TEXT_NODE:
                            value += child.nodeValue
                    returnValues.append(value)

        if dl >= 1:
            print " DEBUG", "".ljust(sd),"_selectNodes(<%s>, %s) -> %s" % (curNode.nodeName, xpath, returnValues)
        return returnValues

    def queryAllChildElements(self, xpath, curNode, validateOnly, dl = 0, sd = 0):
        result = []
        for childNode in curNode.childNodes:
            # check if childNode is an element
            if childNode.nodeType == Node.ELEMENT_NODE:
                result += self._selectNodes(xpath, asStrings=False, curNode = childNode, validateOnly=validateOnly, dl = dl, sd = sd + 1)

                # recurse queryAllChildElements()
                result += self.queryAllChildElements(xpath, childNode, dl, sd)

        return result

    def reverseString(self, string):
        result = ""
        for char in string:
            result = char + result
        return result

    def splitFirstOuter(self, string, delimiters, reverse=False, dl = 0, sd = 0):
        lhs = ""
        rhs = ""
        foundDelimiter = ""
        unclosedBrackets = 0
        unclosedParentheses = 0
        inDoubleQuote = False
        inSingleQuote = False
        if reverse:
            string = self.reverseString(string)
        for i, char in enumerate(string):
            if char == "'" and not inDoubleQuote and string[i - 1] != "\\":
                if inSingleQuote:
                    inSingleQuote = False
                else:
                    inSingleQuote = True
            if char == '"' and not inSingleQuote and string[i - 1] != "\\":
                if inDoubleQuote:
                    inDoubleQuote = False
                else:
                    inDoubleQuote = True
            if not inSingleQuote and not inDoubleQuote:
                if char == "[":
                    unclosedBrackets += 1
                if char == "]":
                    unclosedBrackets -= 1
                if char == "(":
                    unclosedParentheses += 1
                if char == ")":
                    unclosedParentheses -= 1

                if unclosedBrackets == 0 and unclosedParentheses == 0:
                    for delimiter in delimiters:
                        if string[i:i + len(delimiter)].lower() == delimiter:
                            rhs = string[i + len(delimiter):]
                            foundDelimiter = delimiter
                if foundDelimiter != "":
                    break
            lhs += char

        if unclosedBrackets > 0:
            raise Exception, "Missing ']' in '%s'" % string
        if unclosedBrackets < 0:
            raise Exception, "Extra ']' in '%s'" % string
        if unclosedParentheses > 0:
            raise Exception, "Missing ')' in '%s'" % string
        if unclosedParentheses < 0:
            raise Exception, "Extra ')' in '%s'" % string
        if inDoubleQuote or inSingleQuote:
            raise Exception, "Unterminated string '%s'" % string

        if reverse:
            rhsTemp = self.reverseString(lhs)
            lhs = self.reverseString(rhs)
            rhs = rhsTemp
        if dl >= 7:
            if reverse:
                string = self.reverseString(string)
            print " DEBUG", "".ljust(sd),"splitFirstOuter('%s', %s) -> %s" % (string, delimiters, (lhs, rhs, foundDelimiter))
        return lhs.strip(), rhs.strip(), foundDelimiter.strip()

    def evaluateCondition(self, statement, curNode, validateOnly, nodePosition, sibCount, dl = 0, sd = 0):
        if dl > 2:
            print " DEBUG", "".ljust(sd),"evaluateCondition(%s)" % (statement)
        lhs, rhs, operator = self.splitFirstOuter(statement, [" and ", " or "], False, dl, sd + 1)

        if lhs.strip()[0] == "(":
            i = lhs.rfind(")")
            if i == -1:
                raise Exception, "Missing ')' " + lhs
            # process statement in parantheses
            lhsResult = self.evaluateCondition(lhs.strip()[1:i], curNode, validateOnly, nodePosition, sibCount, dl, sd + 1)
        else:
            # process statement
            lhsResult, lhsResultType = self.evaluateComparison(lhs, curNode, validateOnly, nodePosition, sibCount, dl, sd + 1)

            # nodeset then return false if empty else true
            if lhsResultType == "NODE_SET":
                if len(lhsResult) > 0:
                    lhsResult = True
                else:
                    lhsResult = False

            # int treat as node index
            if lhsResultType == "NUMBER":
                if lhsResult == nodePosition:
                    lhsResult = True
                else:
                    lhsResult = False

        if rhs != "":
            # recurse the righthand side
            rhsResult = self.evaluateCondition(rhs, curNode, validateOnly, nodePosition, sibCount, dl = dl, sd = sd + 1)
            if operator == "and":
                result = lhsResult and rhsResult
            else:
                result = lhsResult or rhsResult
        else:
            result = lhsResult
        if dl >= 2:
            print " DEBUG", "".ljust(sd),"evaluateCondition(%s) -> %s" % (statement, result)
        return result


    def evaluateComparison(self, string, curNode, validateOnly, nodePosition, sibCount, dl = 0, sd = 0):
        if dl > 3:
            print " DEBUG", "".ljust(sd),"evaluateComparison(%s)" % (string)
        lhs, rhs, operator = self.splitFirstOuter(string, ["=", "!=", "<", ">", "<=", ">="], False, dl = dl, sd = sd + 1)
        lhsResult, lhsResultType = self.evaluateStatement(lhs, curNode, validateOnly, nodePosition, sibCount, dl, sd + 1)

        if rhs != "":
            rhsResult, rhsResultType = self.evaluateStatement(rhs, curNode, validateOnly, nodePosition, sibCount, dl, sd + 1)
            result = False, "BOOLEAN"
            if lhsResultType == "NODE_SET" and rhsResultType == "NODE_SET":
                for lhsValue in lhsResult:
                    for rhsValue in rhsResult:
                        result = self.compareValues(operator, lhsValue, "STRING", rhsValue, "STRING", dl, sd), "BOOLEAN"
                        if result[0]:
                            break
                    if result[0]:
                        break
            elif lhsResultType == "NODE_SET":
                for lhsValue in lhsResult:
                    result = self.compareValues(operator, lhsValue, "STRING", rhsResult, rhsResultType, dl, sd), "BOOLEAN"
                    if result[0]:
                        break
            elif rhsResultType == "NODE_SET":
                for rhsValue in rhsResult:
                    result = self.compareValues(operator, lhsResult, rhsResultType, rhsValue, "STRING", dl, sd), "BOOLEAN"
                    if result[0]:
                        break
            else:
                result = self.compareValues(operator, lhsResult, lhsResultType, rhsResult, rhsResultType, dl, sd), "BOOLEAN"
        else:
            result = lhsResult, lhsResultType
        if dl >= 3:
            print " DEBUG", "".ljust(sd),"evaluateComparison(%s) -> %s" % (string, result)
        return result

    # function for evaluating against different operators
    def compareValues(self, operator, lhsValue, lhsValueType, rhsValue, rhsValueType, dl = 0, sd = 0):
        result = False
        if rhsValueType == "NUMBER" and lhsValueType == "STRING":
            try:
                lhsValue = int(lhsValue)
            except ValueError:
                pass
        elif rhsValueType == "STRING" and lhsValueType == "NUMBER":
            try:
                rhsValue = int(rhsValue)
            except ValueError:
                pass
        if operator == "=" and lhsValue == rhsValue:
            result = True
        elif operator == "!=" and lhsValue != rhsValue:
            result = True
        elif operator == "<" and lhsValue < rhsValue:
            result = True, "BOOLEAN"
        elif operator == ">" and lhsValue > rhsValue:
            result = True, "BOOLEAN"
        elif operator == "<=" and lhsValue <= rhsValue:
            result = True, "BOOLEAN"
        elif operator == ">=" and lhsValue >= rhsValue:
            result = True, "BOOLEAN"
        if dl >= 4:
            print " DEBUG", "".ljust(sd),"compareValues(%s %s %s) -> %s" % (lhsValue, operator, rhsValue, result)
        return result

    def evaluateStatement(self, statement, curNode, validateOnly, nodePosition, sibCount, dl = 0, sd = 0):
        if dl > 5:
            print " DEBUG", "".ljust(sd),"evaluateStatement(%s)" % (statement)
        lhs, rhs, operator = self.splitFirstOuter(statement, ["+", " - "], True, dl, sd + 1)

        # check for outer parentheses
        if rhs.strip()[0] == "(":
            i = rhs.rfind(")")
            if i == -1:
                raise Exception, "Missing ')' " + rhs
            # process statement in parantheses
            rhsResult, rhsResultType = self.evaluateStatement(rhs.strip()[1:i], curNode, validateOnly, nodePosition, sibCount, dl, sd + 1)
        else:
            rhsResult, rhsResultType = self.evaluateValue(rhs, curNode, validateOnly, nodePosition, sibCount, dl, sd + 1)

        if lhs != "":
            # recurse the lefthand side
            lhsResult, lhsResultType = self.evaluateStatement(lhs, curNode, validateOnly, nodePosition, sibCount, dl, sd + 1)
            if operator == "+":
                if lhsResultType == "NUMBER" and rhsResultType == "NUMBER":
                    result = lhsResult + rhsResult, "NUMBER"
                else:
                    raise Exception, "Can only use (+) operator for numbers not %s and %s '%s'" % (lhsResultType, rhsResultType, statement)
            else:
                if lhsResultType == "NUMBER" and rhsResultType == "NUMBER":
                    result = lhsResult - rhsResult, "NUMBER"
                else:
                    raise Exception, "Can only use (-) operator for numbers not %s and %s '%s'" % (lhsResultType, rhsResultType, statement)
        else:
            result = rhsResult, rhsResultType
        if dl >= 5:
            print " DEBUG", "".ljust(sd),"evaluateStatement(%s) -> %s" % (statement, result)
        return result


    def evaluateValue(self, value, curNode, validateOnly, nodePosition, sibCount, dl = 0, sd = 0):
        if dl > 5:
            print " DEBUG", "".ljust(sd),"evaluateValue(%s)" % (value)

        # integer
        try:
            integer = int(value)
            evaluation = integer, "NUMBER"
        except ValueError:
            # string
            if (value.strip()[0] == '"' and value.strip()[-1] == '"') or (value.strip()[0] == "'" and value.strip()[-1] == "'"):
                evaluation = value.strip()[1:-1], "STRING"
            # true()
            elif value.strip().startswith("true("):
                parameters = self.getFunctionParameters(value, [], curNode, validateOnly, nodePosition, sibCount, dl = dl, sd = sd + 1)
                evaluation = True, "BOOLEAN"
            # false()
            elif value.strip().startswith("false("):
                parameters = self.getFunctionParameters(value, [], curNode, validateOnly, nodePosition, sibCount, dl = dl, sd = sd + 1)
                evaluation = False, "BOOLEAN"
            # postition()
            elif value.strip().startswith("position("):
                parameters = self.getFunctionParameters(value, [], curNode, validateOnly, nodePosition, sibCount, dl = dl, sd = sd + 1)
                evaluation = nodePosition, "NUMBER"
            # last()
            elif value.strip().startswith("last("):
                parameters = self.getFunctionParameters(value, [], curNode, validateOnly, nodePosition, sibCount, dl = dl, sd = sd + 1)
                evaluation = sibCount, "NUMBER"
            # name()
            elif value.strip().startswith("name("):
                # find closing parenthesis
                i = value.rfind(")")
                if i == -1:
                    raise Exception, "Malformed function '%s'" % value
                parameterString = value[value.find("(") + 1:i].strip()
                if parameterString == "":
                    evaluation = curNode.nodeName, "STRING"
                else:
                    nodes = self._selectNodes(parameterString, asStrings=False, curNode=curNode, validateOnly=validateOnly)
                    if len(nodes) > 0:
                        evaluation = nodes[0].nodeName, "STRING"
                    else:
                        evaluation = "", "STRING"
            # string()
            elif value.strip().startswith("string("):
                parameters = self.getFunctionParameters(value, ["BOOLEAN|STRING|NUMBER|NODE_SET"], curNode, validateOnly, nodePosition, sibCount, dl = dl, sd = sd + 1)
                evaluation = self.convertToString(parameters[0][0], parameters[0][1]), "STRING"
            # upper-case()
            elif value.strip().startswith("upper-case("):
                parameters = self.getFunctionParameters(value, ["BOOLEAN|STRING|NUMBER|NODE_SET"], curNode, validateOnly, nodePosition, sibCount, dl = dl, sd = sd + 1)
                string = self.convertToString(parameters[0][0], parameters[0][1])

                evaluation = string.upper(), "STRING"
            # lower-case()
            elif value.strip().startswith("lower-case("):
                parameters = self.getFunctionParameters(value, ["BOOLEAN|STRING|NUMBER|NODE_SET"], curNode, validateOnly, nodePosition, sibCount, dl = dl, sd = sd + 1)
                string = self.convertToString(parameters[0][0], parameters[0][1])

                evaluation = string.lower(), "STRING"
            # substring()
            elif value.strip().startswith("substring("):
                parameters = self.getFunctionParameters(value, ["BOOLEAN|STRING|NUMBER|NODE_SET","NUMBER","NUMBER"], curNode, validateOnly, nodePosition, sibCount, minParams=2, dl = dl, sd = sd + 1)
                string = self.convertToString(parameters[0][0], parameters[0][1])

                # get substring depending on parameters supplied
                if len(parameters) == 2:
                    evaluation = string[parameters[1][0] - 1:], "STRING"
                elif len(parameters) == 3:
                    evaluation = string[parameters[1][0] - 1:parameters[1][0] - 1 + parameters[2][0]], "STRING"
            # starts-with()
            elif value.strip().startswith("starts-with("):
                parameters = self.getFunctionParameters(value, ["BOOLEAN|STRING|NUMBER|NODE_SET","BOOLEAN|STRING|NUMBER|NODE_SET"], curNode, validateOnly, nodePosition, sibCount, minParams=2, dl = dl, sd = sd + 1)
                string1 = self.convertToString(parameters[0][0], parameters[0][1])
                string2 = self.convertToString(parameters[1][0], parameters[1][1])
                if string2 != "":
                    evaluation = string1.startswith(string2), "BOOLEAN"
                else:
                    evaluation = False, "BOOLEAN"
            # ends-with()
            elif value.strip().startswith("ends-with("):
                parameters = self.getFunctionParameters(value, ["BOOLEAN|STRING|NUMBER|NODE_SET","BOOLEAN|STRING|NUMBER|NODE_SET"], curNode, validateOnly, nodePosition, sibCount, minParams=2, dl = dl, sd = sd + 1)
                string1 = self.convertToString(parameters[0][0], parameters[0][1])
                string2 = self.convertToString(parameters[1][0], parameters[1][1])
                if string2 != "":
                    evaluation = string1.endswith(string2), "BOOLEAN"
                else:
                    evaluation = False, "BOOLEAN"
            # contains()
            elif value.strip().startswith("contains("):
                parameters = self.getFunctionParameters(value, ["BOOLEAN|STRING|NUMBER|NODE_SET","BOOLEAN|STRING|NUMBER|NODE_SET"], curNode, validateOnly, nodePosition, sibCount, minParams=2, dl = dl, sd = sd + 1)
                string1 = self.convertToString(parameters[0][0], parameters[0][1])
                string2 = self.convertToString(parameters[1][0], parameters[1][1])
                if string2 != "":
                    evaluation = string2 in string1, "BOOLEAN"
                else:
                    evaluation = False, "BOOLEAN"
            # string-length()
            elif value.strip().startswith("string-length("):
                parameters = self.getFunctionParameters(value, ["BOOLEAN|STRING|NUMBER|NODE_SET"], curNode, validateOnly, nodePosition, sibCount, minParams=0, dl = dl, sd = sd + 1)

                if len(parameters) == 0:
                    if curNode.firstChild != None:
                        string = self.convertToString(curNode.firstChild.nodeValue, "STRING")
                        if string != None:
                            evaluation = len(string), "NUMBER"
                        else:
                            evaluation = 0, "NUMBER"
                    else:
                        evaluation = 0, "NUMBER"
                else:
                    evaluation = len(self.convertToString(parameters[0][0], parameters[0][1])), "NUMBER"
            # concat()
            elif value.strip().startswith("concat("):
                parameters = self.getFunctionParameters(value, ["BOOLEAN|STRING|NUMBER|NODE_SET","*"], curNode, validateOnly, nodePosition, sibCount, minParams=2, dl = dl, sd = sd + 1)
                string = ""
                for parameter in parameters:
                    string += self.convertToString(parameter[0], parameter[1])
                evaluation = string, "STRING"
            # not()
            elif value.strip().startswith("not("):
                parameters = self.getFunctionParameters(value, ["BOOLEAN"], curNode, validateOnly, nodePosition, sibCount, dl = dl, sd = sd + 1)
                evaluation = not parameters[0][0], "BOOLEAN"
            else:
                # <xpath>
                evaluation = self._selectNodes(value, asStrings=True, curNode=curNode, validateOnly=validateOnly), "NODE_SET"
        if dl >= 5:
            print " DEBUG", "".ljust(sd),"evaluateValue(%s) -> %s" % (value, evaluation)
        return evaluation

    def convertToString(self, value, valueType):
        if valueType == "STRING":
            convertedValue = value
        elif valueType == "NODE_SET":
            convertedValue = value[0] if len(value) > 0 else ""
        elif valueType == "NUMBER":
            convertedValue = str(value)
        elif valueType == "BOOLEAN":
            convertedValue = "true" if value else "false"
        else:
            raise Exception, "Cannot convert type %s '%s'" %(valueType, value)

        return convertedValue

    def getFunctionParameters(self, string, paramTypes, curNode, validateOnly, nodePosition, sibCount, minParams=-1, dl = 0, sd = 0):
        if dl > 6:
            print " DEBUG", "".ljust(sd),"getFunctionParameters(%s, %s)" % (string, paramTypes)

        # find closing parenthesis
        i = string.rfind(")")
        if i == -1:
            raise Exception, "Malformed function '%s'" % string

        # split out parameters
        parameterString = string[string.find("(") + 1:i]
        parameters = []
        while parameterString != "":
            param, parameterString, operator = self.splitFirstOuter(parameterString, [","], False, dl = dl, sd = sd + 1)
            parameters.append((param, ""))

        # if second paramTypes = "*" this indicates any number of the first allowed type above
        # the minimum is allowed so modify paramTypes accordingly
        if len(paramTypes) >= 2 and paramTypes[1] == "*":
            allowedType = paramTypes[0]
            paramTypes = []
            for j in range(len(parameters)):
                paramTypes.append(allowedType)

        # check number of parameters
        if minParams == -1:
            minParams = len(paramTypes)
        if len(parameters) < minParams or len(parameters) > len(paramTypes):
            if len(paramTypes) == 0:
                msg = "Expecting no parameters"
            elif len(paramTypes) == 1:
                msg = "Expecting only 1 parameter"
            elif len(paramTypes) == minParams:
                msg = "Expecting exactly %s parameters" % minParams
            else:
                msg = "Expecting between %s and %s parameters" % (minParams, len(paramTypes))
            raise Exception, "%s '%s'" % (msg, string)

        # evaluate parameters
        for i, parameter in enumerate(parameters):
            allowedTypes = paramTypes[i].split("|")

            if [pt for pt in allowedTypes if pt in ["NUMBER", "STRING", "NODE_SET"]]:
                # process int, string or xpath parameter
                parameters[i] = self.evaluateStatement(parameter[0], curNode, validateOnly, nodePosition, sibCount, dl = dl, sd = sd + 1)

                # verify parameter types match expected
                if parameters[i][1] not in allowedTypes:
                    raise Exception, "Incorrect parameter type %s in '%s' expecting one of the following %s" % (parameters[i][1], string, allowedTypes)

            elif "BOOLEAN" in allowedTypes:
                # process boolean parameter
                parameters[i] = self.evaluateCondition(parameter[0], curNode, validateOnly, nodePosition, sibCount, dl = dl, sd = sd + 1), "BOOLEAN"
        if dl >= 6:
            print " DEBUG", "".ljust(sd),"getFunctionParameters(%s, %s) -> %s" % (string, paramTypes, parameters)
        return parameters


if __name__ == "__main__":
    import doctest
    doctest.testmod()
