# EBI (openEQUELLA Bulk Importer)
The EBI is a popular tool for importing content into openEQUELLA. It can also be used for updating, deleting and exporting content.

The EBI is written in Python and compiled to a standalone version (i.e. will run on a computer without Python) for Windows and Macintosh. The source files are included in the Windows package so that the EBI can be used on Linux computers with Python (and wxPython, see Dependencies) installed.

User guide can be found at: https://openequella.github.io/equella-tools/bulkImporterUserManual.html

## Python 3 Migration
**Note**: This project has been migrated from Python 2 to Python 3. See [PYTHON3_MIGRATION.md](PYTHON3_MIGRATION.md) for details.

## Dependencies
The EBI requires both Python 3.x and the GUI framework wxPython 4.x.
The latest release of MS Windows version does not require Python nor wxPython to be installed.
To run the EBI on Linux and Mac, or running from source files (as required on Linux) both Python 3.x and wxPython 4.x must be installed.
On Linux, wxPython requires GTK+ 3 libraries to be present.

To make modifications to and test EBI, Python 3.x and wxPython 4.x must be installed on the developer’s workstation. To compile the EBI as a standalone package then, as well as Python 3.x and wxPython 4.x, one of the following is required on the workstation:
* py2exe (for Windows), or
* py2app (for Macintosh)

### Quick Setup
```bash
# Install Python 3 dependencies
pip3 install -r requirements.txt

# Run from source
python3 source/ebi.py
```

### Platform-Specific Installation

#### macOS
```bash
pip3 install wxPython
```

#### Linux (Ubuntu/Debian)
```bash
sudo apt-get install build-essential gettext python3-dev libgtk-3-dev python3-wxgtk4.0
# Or:
pip3 install -U -f https://extras.wxpython.org/wxPython4/extras/linux/gtk3/ubuntu-20.04 wxPython
```

#### Windows
```bash
pip3 install wxPython
```

### Installing PyInstaller
To compile the EBI as a standalone package for Windows or Macintosh, PyInstaller must be installed in your Python 3 environment:

```bash
pip3 install PyInstaller
```

Alternatively, you can install it as part of the development dependencies:

```bash
# Install all project dependencies including PyInstaller
pip3 install -r requirements.txt
pip3 install PyInstaller
```

The latest release of MS Windows version does not require installing Python or wxPython.
To run the EBI on Linux and Mac, or running from source files (as required on Linux), both Python 3.8+ and wxPython must be installed.

To make modifications to and test EBI, Python 3.8+ and wxPython must be installed on the developer's workstation. To compile the EBI as a standalone package, as well as Python 3.8+ and wxPython, one of the following is required on the workstation:
* py2exe or PyInstaller (for Windows), or
* py2app or PyInstaller (for Macintosh)

## Compiling/Packaging Standalone
EBI should be compiled as a standalone package for Windows and Macintosh to remove the need for end users to install Python. Compiling a Windows version must be done from a Windows computer and compiling a Macintosh version must be done from a Macintosh computer.

### Compiling a Windows Standalone Package
Make certain all source code files, package.bat, setup.py (for Windows) and package.py is in the same folder on a Windows computer with Python 3.8+, wxPython and py2exe (or PyInstaller) installed.

Run package.bat to create ebi.zip (it will appear in the same folder as the source files).
package.bat does the following automatically:
1.	Removes any previous packages from the working folder
2.	 Invokes setup.py and py2exe to generate a standalone package in a folder called “dist” Dist, amongst other files, contains ebi.exe which is the resulting standalone Windows EBI executable.
3.	Renames the “dist” folder to “ebi”
4.	Copies the source files into the “ebi” folder
5.	Invokes package.py which zips the “ebi” folder to ebi.zip

### Compiling a Macintosh Standalone Package
Use a Macintosh computer with Python 3.8+, wxPython 4.2+ and py2app (or PyInstaller) installed. Place package.command, setup.py (for Macintosh) and ebi.command in the same folder. In that folder create a sub folder called source and in source create a sub folder called ebi. Place all the EBI source files in /source/ebi.
Run package.command to create ebi.dmg (it will appear in a sub folder called dist).
package.command does the following:
1.	Removes any previous packages from the working folder
2.	Invokes setup.py and py2app to generate a standalone app package called “ebi.app” in a folder called “dist”
3.	Copies the image files and ebi.command into the “ebi.app” package
4.	Creates a DMG called ebi.dmg in the “dist” folder from ebi.app (by using hdituil)
