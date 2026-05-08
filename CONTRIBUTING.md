# Contributing

Thank you for your interest in contributing to the EBI (openEQUELLA Bulk Importer)!
Contributions of all kinds are welcome — bug fixes, new features, documentation improvements, and issue reports.

## Development Setup

Follow the [Developer Guide in README.md](README.md#developer-guide) to set up your local environment.
That guide covers installing Python 3.8+, wxPython 4.x, creating a virtual environment, and running EBI from source.

## Contribution Workflow

1. **Fork** the repository on GitHub and clone your fork locally.
2. **Create a branch** for your change:
   ```bash
   git checkout -b my-feature-or-fix
   ```
3. **Make your changes** and verify they work by running EBI from source (see [Running the App Locally](README.md#developer-guide)).
4. **Commit** with a clear, descriptive message.
5. **Push** your branch to your fork and open a **Pull Request** against the `develop` branch of this repository.
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