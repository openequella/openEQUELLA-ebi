# EBI (openEQUELLA Bulk Importer)
> 🛠 **Status:** This branch reflects the latest development. For the most recent stable executable, please see [Latest Releases](https://github.com/openequella/openEQUELLA-ebi/releases/latest).

The EBI is a popular tool for importing content into openEQUELLA. It can also be used for updating, deleting and exporting content.

The EBI is written in Python and compiled to standalone versions (i.e. they will run on a computer without Python) for Windows, macOS, and Linux. The EBI can also be run from the source files on systems with Python (and wxPython, see Dependencies) installed.

User guide can be found at: https://openequella.github.io/equella-tools/bulkImporterUserManual.html

## Dependencies
The EBI requires both Python 3.x and the GUI framework wxPython 4.x.
The latest releases of the standalone packages for Windows, macOS, and Linux do not require Python nor wxPython to be installed.
To run the EBI from source files, both Python 3.x and wxPython 4.x must be installed.
On Linux, wxPython requires GTK+ 3 libraries to be present.

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

## Contributing

Contributor and developer setup guidance now lives in [CONTRIBUTING.md](CONTRIBUTING.md), including:

- local development environment setup
- running EBI from source
- contribution workflow and pull request guidance
- testing expectations and code structure notes

## Compiling/Packaging Standalone
EBI can be compiled as a standalone package to remove the need for end users to install Python. 

### Automated Builds (GitHub Actions)
The project includes a GitHub Actions CI workflow that automatically compiles all three standalone versions (Windows, Mac, Linux) for supported pull requests and pushes to the active development branch. The resulting packages are uploaded as GitHub Actions build artifacts for those workflow runs. On tag pushes, the workflow also publishes these packages as release assets in GitHub Releases.

> **Note for macOS Users**: When downloading the `ebi.dmg` artifact from GitHub Actions or GitHub Releases, macOS Gatekeeper may flag the application as "damaged" because it was downloaded from the internet and lacks an Apple Developer certificate. To run the application, you must remove the quarantine attribute. Open your Terminal and run:
> ```bash
> xattr -cr /path/to/ebi.app
> ```
> Alternatively, you can right-click the application bundle and select "Open" to bypass the initial security prompt.

### Manual Compilation
For local testing or manual builds, compiling a Windows version must be done from a Windows computer, a Linux version from a Linux computer, and a Macintosh version must be done from a Macintosh computer.

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
