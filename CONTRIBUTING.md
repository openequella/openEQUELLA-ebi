# Contributing

Thank you for your interest in contributing to the EBI (openEQUELLA Bulk Importer)!
Contributions of all kinds are welcome — bug fixes, new features, documentation improvements, and issue reports.

## Development Setup

For a user-focused overview and release links, see [README.md](README.md). This guide covers contributor and maintainer workflows.

### Prerequisites

- Python 3.8+
- wxPython 4.x
- On Linux, GTK+ 3 development libraries are required for wxPython

Creating a virtual environment is recommended to avoid dependency conflicts:

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

Install the project dependencies:

```bash
pip install -r requirements.txt
```

> **Note on Linux**: You may need to install GTK+ 3 development libraries before installing `wxPython`. See the Linux setup notes in [README.md](README.md#platform-specific-installation).

### Running the App Locally

From the repository root, launch the GUI application with:

```bash
python3 source/ebi.py
```

### Code Structure Overview

- `source/ebi.py`: Main entry point script that launches the GUI.
- `source/MainFrame.py`: Core wxPython GUI definitions and flow wiring.
- `source/Engine.py`: CSV processing state and data orchestration.
- `source/RowProcessor.py`: Row-to-item processing logic using a `RowContext`.
- `source/equellaclient41.py`: SOAP API client for communicating with an openEQUELLA instance.

## Contribution Workflow

1. **Fork** the repository on GitHub and clone your fork locally.
2. **Create a branch** for your change:
   ```bash
   git checkout -b my-feature-or-fix
   ```
3. **Make your changes** and verify they work by running EBI from source (see [Running the App Locally](#running-the-app-locally)).
4. **Commit** with a clear, descriptive message.
5. **Push** your branch to your fork and open a **Pull Request** against the repository's current default branch, which reflects the latest development state.
6. Respond to any review feedback.

## Code Conventions

- Follow [PEP 8](https://peps.python.org/pep-0008/) style guidelines for Python code.
- Keep changes focused — one logical change per pull request makes review easier.
- Use descriptive variable and function names.

## Testing

EBI does not currently have an automated test suite.
Before submitting a pull request, manually verify your changes by running EBI from source:

```bash
python3 source/ebi.py
```

Exercise any workflows affected by your change (e.g. import, export, update, delete) against a running openEQUELLA instance to confirm correct behaviour.

## Packaging and CI

Standalone packages for Windows, macOS, and Linux are built automatically via GitHub Actions.
See the [Compiling/Packaging Standalone](README.md#compilingpackaging-standalone) section of README.md for details.
You do not need to build packages locally to contribute code changes.

## Reporting Issues

Please use [GitHub Issues](https://github.com/openequella/openEQUELLA-ebi/issues) to report bugs or request features.
When reporting a bug, include:
- EBI version or commit used
- Operating system and Python version (if running from source)
- Steps to reproduce the problem
- Any relevant error messages or screenshots
