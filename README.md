# EBI (openEQUELLA Bulk Importer)
> ⚠️ **Deprecated and archived:** The EBI is no longer maintained or supported. It relies on openEQUELLA's SOAP API, and SOAP support has been removed from openEQUELLA, so the EBI will not work with current openEQUELLA versions. This repository is archived and kept read-only for reference.
>
> If you need a bulk import tool for openEQUELLA, please contact [Edalex](https://www.edalex.com) at [info@edalex.com](mailto:info@edalex.com) for more information.

The EBI is a popular tool for importing content into openEQUELLA. It can also be used for updating, deleting and exporting content.

The EBI is written in Python and distributed as standalone packages for Windows, macOS, and Linux, so most users can run it without installing Python or other dependencies.

User guide can be found at: https://openequella.github.io/equella-tools/bulkImporterUserManual.html

## Getting Started

For most users, the quickest way to get started is to download the latest standalone package from [Latest Releases](https://github.com/openequella/openEQUELLA-ebi/releases/latest).

1. Download the package for your operating system.
2. Extract or open the downloaded archive.
3. Launch the EBI application included in the package.

> **Note for macOS users:** When downloading the `ebi.dmg` release asset, macOS Gatekeeper may flag the application as "damaged" because it was downloaded from the internet and lacks an Apple Developer certificate. To run the application, remove the quarantine attribute:
> ```bash
> xattr -cr /path/to/ebi.app
> ```
> Alternatively, right-click the application bundle and choose **Open** to bypass the initial security prompt.

## Contributing

Developer and contributor guidance lives in [CONTRIBUTING.md](CONTRIBUTING.md), including:

- local development environment setup
- running EBI from source
- build and packaging instructions
- contribution workflow and pull request guidance
- testing expectations and code structure notes
