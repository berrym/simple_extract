# simple_extract

Simple File Extraction

## Description

A small command line file extraction utility written in Python. It uses external tools to optionally fetch from an url and decompress archives.

## Getting started

Python 3.9+ needed

External tools that can be used:

    * tar
    * gzip
    * bzip2
    * unrar
    * lha
    * 7z
    * unzip
    * rpm2cpio
    * cpio
    * ar
    * xz
    * zstd
    * curl
    * wget
    * fetch

### Installing

    * clone the git repository from https://github.com/berrym/simple_extract.git
    or:
    * python -m pip install simple-extract
    or:
    * python -m pip install --user simple-extract

### Executing program

    * python simple_extract.py some-archive.tar.gz some-other-archive.lzma
    or if installed via pip:
    * simple-extract https://github.com/ibara/mg/releases/download/mg-6.8.1/mg-6.8.1.tar.gz

## Authors

Copyright 2021
Michael Berry <trismegustis@gmail.com>

## Version History

* 0.1.0
    * Initial Release
* 0.1.1
    * Change the way paths are handled if stdout is used
* 0.1.2
    * Updated setup.py
* 0.1.3
    * Fixed setup.py issue preventing proper builds
* 0.1.4
    * Added a simple noclobber option for non piped commands
* 0.1.5
    * Added a command line switch to silence archive downloads
* 0.1.6
    * Stop splitting text at common extensions
* 0.1.7
    * Split archive paths only at valid extensions
* 0.1.8
    * Changed imports, check for local archive existence in should_fetch archive
* 0.1.9
    * Improved url validation and error handling
* 0.2.0
    * Use subprocess.run instead of Popen and check for errors
* 0.2.1
    * Use a dictionary command mapping instead of if else control flow
* 0.2.2
    * Removed glob_multiple_extensions, deprecated
* 0.2.3
    * Refactored main()
* 0.2.4
    * Added logging
* 0.2.5
    * New control switch --force_download bypasses should_fetch_url() check
* 0.2.6
    * Fixed a crash when fetching an url and content length is invalid
* 0.2.7
    * Do no create log file
## License

This project is licensed under the MIT License - see the LICENSE file for details.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
