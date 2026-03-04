# EBI (openEQUELLA Bulk Importer)
The EBI is a popular tool for importing content into openEQUELLA. It can also be used for updating, deleting and exporting content.

The EBI is written in Python and compiled to a standalone version (i.e. will run on a computer without Python) for Windows and Macintosh. The source files are included in the Windows package so that the EBI can be used on Linux computers with Python (and wxPython, see Dependencies) installed.

User guide can be found at: https://openequella.github.io/equella-tools/bulkImporterUserManual.html

## Dependencies
The EBI requires both Python 3.x and the GUI framework wxPython 4.x.
The latest release of MS Windows version does not require Python nor wxPython to be installed.
To run the EBI on Linux and Mac, or running from source files (as required on Linux) both Python 3.x and wxPython 4.x must be installed.
On Linux, wxPython requires GTK+ 3 libraries to be present.

To make modifications to and test EBI, Python 3.x and wxPython 4.x must be installed on the developer’s workstation. To compile the EBI as a standalone package then, as well as Python 3.x and wxPython 4.x, PyInstaller is required on the workstation.

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
Dependencies required for wxPython:
```bash
sudo apt-get install build-essential gettext python3-dev libgtk-3-dev
```

Install wxPython (using a pre-built wheel is recommended):
```bash
pip3 install -U -f https://extras.wxpython.org/wxPython4/extras/linux/gtk3/ubuntu-20.04 wxPython>=4.2.0
```
Or build from source (takes longer):
```bash
pip3 install -r requirements.txt
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

To make modifications to and test EBI, Python 3.8+ and wxPython must be installed on the developer's workstation. To compile the EBI as a standalone package, PyInstaller must be installed on the workstation.

## Developer Guide

For developers looking to contribute, extend, or maintain the codebase, here's how to set up your environment:

1. **Prerequisites**
   Ensure you have Python 3.8+ installed. Creating a virtual environment is highly recommended to avoid dependency conflicts.
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Dependencies**
   Install the necessary requirements. For GUI work, you need `wxPython>=4.2.0`.
   ```bash
   pip install -r requirements.txt
   ```
   > **Note on Linux**: You may need to install GTK+ 3 development libraries before installing `wxPython`. See the Linux Platform-Specific Installation section above.

3. **Running the App Locally**
   To launch the main EBI GUI application during development from the root directory:
   ```bash
   python source/ebi.py
   ```

4. **Code Structure Overview**
   - `source/ebi.py`: The main entry point script that launches the GUI.
   - `source/MainFrame.py`: Contains the core wxPython GUI definitions and logic to connect UI steps.
   - `source/Engine.py`: Handles CSV processing state and data orchestration.
   - `source/RowProcessor.py`: Isolated logic mapping rows to EQUELLA Items using a `RowContext`.
   - `source/equellaclient41.py`: The core SOAP API client to communicate with an EQUELLA instance.

## Compiling/Packaging Standalone
EBI should be compiled as a standalone package to remove the need for end users to install Python. Compiling a Windows version must be done from a Windows computer, a Linux version from a Linux computer, and a Macintosh version must be done from a Macintosh computer.

### Compiling a Windows Standalone Package
Use a Windows computer with Python 3.8+, wxPython, and PyInstaller installed.

Navigate to the `package-win` directory and run `package.bat`. It will create `ebi.zip` containing the packaged application.
`package.bat` does the following automatically:
1. Validates Python and PyInstaller dependencies.
2. Removes any previous packages from the working folder.
3. Invokes `setup.py`, which uses PyInstaller to generate a standalone package in a folder called `dist`. The `dist` folder contains `ebi.exe`, which is the standalone Windows EBI executable.
4. Renames the `dist` folder to `ebi`.
5. Copies the source files into the `ebi\source` folder for reference.
6. Invokes `package.py` which zips the `ebi` folder into `ebi.zip`.

### Compiling a Linux Standalone Package
Use a Linux computer with Python 3.8+, wxPython, and PyInstaller installed.

Navigate to the `package-linux` directory and run `bash package.sh`. It will create `ebi.zip` containing the packaged application compatible with Linux environments.
`package.sh` performs the exact same operations automatically as its Windows counterpart (`package.bat`), yielding an Elf executable (`ebi`) inside `ebi/ebi` rather than an `.exe`, and finally zips it uniformly into `ebi.zip`.

### Compiling a Macintosh Standalone Package
Use a Macintosh computer with Python 3.8+, wxPython 4.2+, and PyInstaller installed. 

Navigate to the `package-mac` directory and run `bash ebi-package.command` (or make it executable and run it). It will create `ebi.dmg` in the `dist` sub folder.
`ebi-package.command` does the following:
1. Validates dependencies and checks for PyInstaller.
2. Removes previous builds from the `build` and `dist` directories.
3. Invokes `setup.py` which uses PyInstaller to generate a macOS application bundle (`ebi.app`) inside the `dist` folder.
4. Copies the launcher script wrapper into the `ebi.app` package.
5. Creates a disk image `ebi.dmg` in the `dist` folder from `ebi.app` using `hdiutil`.
