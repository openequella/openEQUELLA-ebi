#!/usr/bin/env python3
"""
Package script for creating EBI Windows distribution zip file

Creates ebi.zip containing the ebi directory with all required files.
"""

import zipfile
import os
import sys

print("Zipping files...")

try:
    if not os.path.exists("ebi"):
        print("ERROR: 'ebi' directory not found")
        print("Make sure to run this script from the package-win directory")
        sys.exit(1)

    archive = zipfile.ZipFile("ebi.zip", "w", zipfile.ZIP_DEFLATED)
    file_count = 0

    for root, dirs, files in os.walk("ebi"):
        for fileName in files:
            file_path = os.path.join(root, fileName)
            archive.write(file_path)
            file_count += 1
            print(f"  Added: {file_path}")

    archive.close()
    print(f"Successfully created ebi.zip with {file_count} files")

except Exception as e:
    print(f"ERROR: Failed to create zip file: {e}")
    sys.exit(1)
