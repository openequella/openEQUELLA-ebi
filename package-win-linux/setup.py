from distutils.core import setup
import py2exe
import sys,os
import ebi

origIsSystemDLL = py2exe.build_exe.isSystemDLL
def isSystemDLL(pathname):
    if os.path.basename(pathname).lower() in ("msvcp71.dll", "gdiplus.dll", "msvcp90.dll"): 
        return 0
    return origIsSystemDLL(pathname)
py2exe.build_exe.isSystemDLL = isSystemDLL

setup(
    name = "EQUELLA Bulk Importer (EBI)",
    version = ebi.Version,      
    windows=[{"script":"ebi.py","icon_resources":[(0x0004,"ebismall.ico")],"copyright":"Copyright (c) 2014 Pearson plc. All rights reserved."}],
    options={
        'py2exe': {
            "dll_excludes": [
                "MSVCP90.dll",
                "api-ms-win-core-string-l1-1-0.dll",
                "api-ms-win-core-string-obsolete-l1-1-0.dll",
                "api-ms-win-core-com-l1-1-0.dll",
                "api-ms-win-core-sysinfo-l1-1-0.dll",
                "api-ms-win-core-debug-l1-1-0.dll",
                "api-ms-win-core-profile-l1-1-0.dll",
                "api-ms-win-core-synch-l1-2-0.dll",
                "api-ms-win-core-synch-l1-1-0.dll",
                "api-ms-win-core-errorhandling-l1-1-0.dll",
                "api-ms-win-core-libraryloader-l1-2-0.dll",
                "api-ms-win-core-delayload-l1-1-1.dll",
                "api-ms-win-core-delayload-l1-1-0.dll",
                "api-ms-win-core-processthreads-l1-1-0.dll",
                "api-ms-win-core-processenvironment-l1-1-0.dll",
                "api-ms-win-eventing-provider-l1-1-0.dll",
                "api-ms-win-core-file-l1-1-0.dll",
                "api-ms-win-core-memory-l1-1-0.dll",
                "api-ms-win-core-threadpool-l1-2-0.dll",
                "api-ms-win-core-localization-l1-2-0.dll",
                "api-ms-win-core-handle-l1-1-0.dll",
                "api-ms-win-core-kernel32-legacy-l1-1-0.dll",
                "api-ms-win-core-heap-l1-1-0.dll",
                "api-ms-win-core-heap-l2-1-0.dll",
                "api-ms-win-core-heap-obsolete-l1-1-0.dll",
                "api-ms-win-security-base-l1-1-0.dll",
                "api-ms-win-core-libraryloader-l1-2-1.dll",
                "api-ms-win-core-rtlsupport-l1-1-0.dll"
            ]
        }
    },
    description = "EQUELLA Bulk Importer for uploading content into the EQUELLA(R) content management system",
)

