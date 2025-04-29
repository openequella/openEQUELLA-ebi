#!/usr/bin/env python
#Boa:App:ebi

# EQUELLA BULK IMPORTER (EBI)
# Author: Jim Kurian, Pearson plc.
#
# This program creates items in EQUELLA based on metadata specified in a csv file. The csv file
# must commence with a row of metadata xpaths (e.g. metadata/name,metadata/description,...).
# Subsequent rows should contain the metadata that populate the element identified by the
# xpath in the column header.
#
# metadata/title,metadata/description
# Our House,"This is a picture of my house, my lawn, my cat and my dog"
# Our Car,This is a picture of my car
#
# User Guide
# A detailed and comprehensive user guide is distributed with this program. Please see this for more
# detailed usage instructions and troubleshooting tips.

# system settings (do not change!)
Version = "4.73"
Copyright = """
Copyright (c) 2024, The Apereo Foundation

This project includes software developed by The Apereo Foundation.
http://www.apereo.org/

Licensed under the Apache License, Version 2.0, (the "License"); you may not
use this software except in compliance with the License. You may obtain a
copy of the License at:

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
License for the specific language governing permissions and limitations under
the License.
"""
License = """
                                 Apache License
                           Version 2.0, January 2004
                        http://www.apache.org/licenses/

   TERMS AND CONDITIONS FOR USE, REPRODUCTION, AND DISTRIBUTION

   1. Definitions.

      "License" shall mean the terms and conditions for use, reproduction,
      and distribution as defined by Sections 1 through 9 of this document.

      "Licensor" shall mean the copyright owner or entity authorized by
      the copyright owner that is granting the License.

      "Legal Entity" shall mean the union of the acting entity and all
      other entities that control, are controlled by, or are under common
      control with that entity. For the purposes of this definition,
      "control" means (i) the power, direct or indirect, to cause the
      direction or management of such entity, whether by contract or
      otherwise, or (ii) ownership of fifty percent (50%) or more of the
      outstanding shares, or (iii) beneficial ownership of such entity.

      "You" (or "Your") shall mean an individual or Legal Entity
      exercising permissions granted by this License.

      "Source" form shall mean the preferred form for making modifications,
      including but not limited to software source code, documentation
      source, and configuration files.

      "Object" form shall mean any form resulting from mechanical
      transformation or translation of a Source form, including but
      not limited to compiled object code, generated documentation,
      and conversions to other media types.

      "Work" shall mean the work of authorship, whether in Source or
      Object form, made available under the License, as indicated by a
      copyright notice that is included in or attached to the work
      (an example is provided in the Appendix below).

      "Derivative Works" shall mean any work, whether in Source or Object
      form, that is based on (or derived from) the Work and for which the
      editorial revisions, annotations, elaborations, or other modifications
      represent, as a whole, an original work of authorship. For the purposes
      of this License, Derivative Works shall not include works that remain
      separable from, or merely link (or bind by name) to the interfaces of,
      the Work and Derivative Works thereof.

      "Contribution" shall mean any work of authorship, including
      the original version of the Work and any modifications or additions
      to that Work or Derivative Works thereof, that is intentionally
      submitted to Licensor for inclusion in the Work by the copyright owner
      or by an individual or Legal Entity authorized to submit on behalf of
      the copyright owner. For the purposes of this definition, "submitted"
      means any form of electronic, verbal, or written communication sent
      to the Licensor or its representatives, including but not limited to
      communication on electronic mailing lists, source code control systems,
      and issue tracking systems that are managed by, or on behalf of, the
      Licensor for the purpose of discussing and improving the Work, but
      excluding communication that is conspicuously marked or otherwise
      designated in writing by the copyright owner as "Not a Contribution."

      "Contributor" shall mean Licensor and any individual or Legal Entity
      on behalf of whom a Contribution has been received by Licensor and
      subsequently incorporated within the Work.

   2. Grant of Copyright License. Subject to the terms and conditions of
      this License, each Contributor hereby grants to You a perpetual,
      worldwide, non-exclusive, no-charge, royalty-free, irrevocable
      copyright license to reproduce, prepare Derivative Works of,
      publicly display, publicly perform, sublicense, and distribute the
      Work and such Derivative Works in Source or Object form.

   3. Grant of Patent License. Subject to the terms and conditions of
      this License, each Contributor hereby grants to You a perpetual,
      worldwide, non-exclusive, no-charge, royalty-free, irrevocable
      (except as stated in this section) patent license to make, have made,
      use, offer to sell, sell, import, and otherwise transfer the Work,
      where such license applies only to those patent claims licensable
      by such Contributor that are necessarily infringed by their
      Contribution(s) alone or by combination of their Contribution(s)
      with the Work to which such Contribution(s) was submitted. If You
      institute patent litigation against any entity (including a
      cross-claim or counterclaim in a lawsuit) alleging that the Work
      or a Contribution incorporated within the Work constitutes direct
      or contributory patent infringement, then any patent licenses
      granted to You under this License for that Work shall terminate
      as of the date such litigation is filed.

   4. Redistribution. You may reproduce and distribute copies of the
      Work or Derivative Works thereof in any medium, with or without
      modifications, and in Source or Object form, provided that You
      meet the following conditions:

      (a) You must give any other recipients of the Work or
          Derivative Works a copy of this License; and

      (b) You must cause any modified files to carry prominent notices
          stating that You changed the files; and

      (c) You must retain, in the Source form of any Derivative Works
          that You distribute, all copyright, patent, trademark, and
          attribution notices from the Source form of the Work,
          excluding those notices that do not pertain to any part of
          the Derivative Works; and

      (d) If the Work includes a "NOTICE" text file as part of its
          distribution, then any Derivative Works that You distribute must
          include a readable copy of the attribution notices contained
          within such NOTICE file, excluding those notices that do not
          pertain to any part of the Derivative Works, in at least one
          of the following places: within a NOTICE text file distributed
          as part of the Derivative Works; within the Source form or
          documentation, if provided along with the Derivative Works; or,
          within a display generated by the Derivative Works, if and
          wherever such third-party notices normally appear. The contents
          of the NOTICE file are for informational purposes only and
          do not modify the License. You may add Your own attribution
          notices within Derivative Works that You distribute, alongside
          or as an addendum to the NOTICE text from the Work, provided
          that such additional attribution notices cannot be construed
          as modifying the License.

      You may add Your own copyright statement to Your modifications and
      may provide additional or different license terms and conditions
      for use, reproduction, or distribution of Your modifications, or
      for any such Derivative Works as a whole, provided Your use,
      reproduction, and distribution of the Work otherwise complies with
      the conditions stated in this License.

   5. Submission of Contributions. Unless You explicitly state otherwise,
      any Contribution intentionally submitted for inclusion in the Work
      by You to the Licensor shall be under the terms and conditions of
      this License, without any additional terms or conditions.
      Notwithstanding the above, nothing herein shall supersede or modify
      the terms of any separate license agreement you may have executed
      with Licensor regarding such Contributions.

   6. Trademarks. This License does not grant permission to use the trade
      names, trademarks, service marks, or product names of the Licensor,
      except as required for reasonable and customary use in describing the
      origin of the Work and reproducing the content of the NOTICE file.

   7. Disclaimer of Warranty. Unless required by applicable law or
      agreed to in writing, Licensor provides the Work (and each
      Contributor provides its Contributions) on an "AS IS" BASIS,
      WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
      implied, including, without limitation, any warranties or conditions
      of TITLE, NON-INFRINGEMENT, MERCHANTABILITY, or FITNESS FOR A
      PARTICULAR PURPOSE. You are solely responsible for determining the
      appropriateness of using or redistributing the Work and assume any
      risks associated with Your exercise of permissions under this License.

   8. Limitation of Liability. In no event and under no legal theory,
      whether in tort (including negligence), contract, or otherwise,
      unless required by applicable law (such as deliberate and grossly
      negligent acts) or agreed to in writing, shall any Contributor be
      liable to You for damages, including any direct, indirect, special,
      incidental, or consequential damages of any character arising as a
      result of this License or out of the use or inability to use the
      Work (including but not limited to damages for loss of goodwill,
      work stoppage, computer failure or malfunction, or any and all
      other commercial damages or losses), even if such Contributor
      has been advised of the possibility of such damages.

   9. Accepting Warranty or Additional Liability. While redistributing
      the Work or Derivative Works thereof, You may choose to offer,
      and charge a fee for, acceptance of support, warranty, indemnity,
      or other liability obligations and/or rights consistent with this
      License. However, in accepting such obligations, You may act only
      on Your own behalf and on Your sole responsibility, not on behalf
      of any other Contributor, and only if You agree to indemnify,
      defend, and hold each Contributor harmless for any liability
      incurred by, or claims asserted against, such Contributor by reason
      of your accepting any such warranty or additional liability.

   END OF TERMS AND CONDITIONS

   APPENDIX: How to apply the Apache License to your work.

      To apply the Apache License to your work, attach the following
      boilerplate notice, with the fields enclosed by brackets "{}"
      replaced with your own identifying information. (Don't include
      the brackets!)  The text should be enclosed in the appropriate
      comment syntax for the file format. We also recommend that a
      file or class name and description of purpose be included on the
      same "printed page" as the copyright notice for easier
      identification within third-party archives.

   Copyright {yyyy} {name of copyright owner}

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""
EBIDownloadPage = "https://github.com/openequella/openEQUELLA-ebi/releases"
Debug = False
SuppressVersion = False

import sys, os, traceback
import wx
import MainFrame
import ConfigParser
import platform

modules ={'MainFrame': [1, u'Main frame of EBI', 'none://MainFrame.py']}

propertiesFile = "ebi.properties"
if sys.path[0].endswith(".zip"):
    propertiesFile = os.path.join(os.path.dirname(sys.path[0]), propertiesFile)
else:
    propertiesFile = os.path.join(sys.path[0], propertiesFile)
            
display = True

class ebi(wx.App):
    global display

    def OnInit(self):
        self.main = MainFrame.create(None)
        if display:
            self.main.Show()
            self.SetTopWindow(self.main)
        return True

def alert(message):
    message = message + "\n\n" + Copyright
    app = wx.PySimpleApp()
    dialog = wx.Dialog(None, title='EQUELLA Bulk Importer ' + Version, size=wx.Size(500, 300), style=wx.RESIZE_BORDER|wx.DEFAULT_DIALOG_STYLE)
    dialog.Center()
    box = wx.BoxSizer(wx.VERTICAL)
    dialog.SetSizer(box)
    txtMessage = wx.TextCtrl(dialog, -1, message, style=wx.TE_MULTILINE|wx.TE_READONLY)    
    box.Add(txtMessage, 1, wx.ALIGN_CENTER|wx.ALL|wx.EXPAND)
    
    btnsizer = wx.StdDialogButtonSizer()
    btn = wx.Button(dialog, wx.ID_OK)
    btn.SetDefault()
    btnsizer.AddButton(btn)
    btnsizer.Realize()
    box.Add(btnsizer, 0, wx.ALIGN_CENTER|wx.CENTER|wx.ALL, 5)   
    btn.SetFocus() 
    
    dialog.ShowModal()
    dialog.Destroy()
    app.MainLoop()
      

def main():
    try:
        global display
        global Version
        global Debug
        global SuppressVersion
        global propertiesFile
        
        # create properties file
        config = ConfigParser.ConfigParser()
        config.read(propertiesFile)
        if not "Configuration" in config.sections():
            config.add_section('Configuration')
            config.set('Configuration','LoadLastSettingsFile', 'False')
            config.write(open(propertiesFile, 'w'))
        else:
            try:
                if config.has_option('Configuration','debug'):
                    Debug = config.getboolean('Configuration','debug')
            except:
                alert("Error reading properties file for debug setting: " + str(sys.exc_info()[1]))

        # usage syntax to display in command line
        usageSyntax = """USAGE:
    
ebi.py [-start] [-test] [<filename>]
ebi.exe [-start] [-test] [<filename>]

<filename>
Run the EBI visually and load the specified settings file.

-start <filename>
Run the EBI non-visually using the specified settings file.

-test <filename>
Run the EBI non-visually in test mode using the specified settings file, no items will be submitted to EQUELLA.
        """

        settingsFile = ""

        if "?" in sys.argv:
            alert(usageSyntax)
            
        else:
            usageCorrect = True
            i = 1

            #loop through arguments (skip first argument as it is the command itself)
            while i < len(sys.argv):
                if sys.argv[i] in ["-test", "-start"]:

                    # check that an argument exists after the -start or -test argument
                    if i + 1 <= (len(sys.argv) - 1):

                        # check that argument after -settings does not start with a dash
                        if sys.argv[i + 1][0] != "-":

                            # get settings filename
                            settingsFile = sys.argv[i + 1]

                            # step over filename
                            i += 1
                        else:
                            usageCorrect = False
                    else:
                        usageCorrect = False
                        
                elif sys.argv[i] not in ["-test", "-start"]:
                    settingsFile = sys.argv[i]
                    # usageCorrect = False

                i += 1

            if "-test" in sys.argv and usageCorrect :
                # run non-visually in test mode
                # print "Testing " + settingsFile
                try:
                    display = False
                    application = ebi(0)
                    if SuppressVersion:
                        Version = ""
                    application.main.createEngine(Version, Copyright, License, EBIDownloadPage, propertiesFile)                
                    application.main.setDebug(Debug)
                    if settingsFile != "":
                        if application.main.loadSettings(settingsFile):
                            application.main.startImport(testOnly = True)
                except:
                    exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
                    errorString = "ERROR: " + str(exceptionValue)
                    if Debug:
                        errorString += ': ' + ''.join(traceback.format_exception(exceptionType, exceptionValue, exceptionTraceback))
                    alert(errorString)
                
            elif "-start" in sys.argv and usageCorrect :
                try:
                    # run non-visually
                    # print "Running " + settingsFile
                    display = False
                    application = ebi(0)
                    if SuppressVersion:
                        Version = ""
                    application.main.createEngine(Version, Copyright, License, EBIDownloadPage, propertiesFile)
                    application.main.setDebug(Debug)
                    if settingsFile != "":
                        if application.main.loadSettings(settingsFile):
                            application.main.startImport(testOnly = False)
                except:
                    exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
                    errorString = "ERROR: " + str(exceptionValue)
                    if Debug:
                        errorString += ': ' + ''.join(traceback.format_exception(exceptionType, exceptionValue, exceptionTraceback))
                    alert(errorString)            
                
            elif usageCorrect:
                try:
                    # run visually starting with the main form
                    application = ebi(0)
                    if SuppressVersion:
                        Version = ""
                    application.main.createEngine(Version, Copyright, License, EBIDownloadPage, propertiesFile)                
                    application.main.setDebug(Debug)
                    if settingsFile != "":
                        application.main.loadSettings(settingsFile)
                    elif "Configuration" in config.sections() and config.getboolean('Configuration','loadlastsettingsfile'):
                        try:
                            application.main.loadSettings(config.get('State','settingsfile'))
                        except:
                            if Debug:
                                alert(str(sys.exc_info()[1]))
                        
                    application.MainLoop()
                except:
                    exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
                    errorString = "ERROR: " + str(exceptionValue)
                    if Debug:
                        errorString += ': ' + ''.join(traceback.format_exception(exceptionType, exceptionValue, exceptionTraceback))
                    alert(errorString)
            else:
                alert(usageSyntax)
    except:
        exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
        errorString = "ERROR: " + str(exceptionValue)
        if "Errno 30" in errorString:
            errorString += "\n\nEBI cannot read and write files in its current location. Try installing EBI in a different location."
            if platform.system() == "Darwin":
                errorString += "\n\nIf launching EBI from a mounted disk image (*.dmg) first copy the EBI package to Applications or another local directory."
        if Debug:
            errorString += "\n\n" + ''.join(traceback.format_exception(exceptionType, exceptionValue, exceptionTraceback))                
        alert(errorString)


if __name__ == '__main__':
    main()
