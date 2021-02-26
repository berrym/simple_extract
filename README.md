# simple_extract

Simple File Extraction

## Description

A small command line file extraction utility written in Python. It uses external tools to optionally fetch from a url and decompress archives.

## Getting started

Python 3.6+ needed. Tested with 3.9

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
    * pip install simple-extract
    or:
    * pip install --user simple-extract

### Executing program

    * python simple_extract.py some-archive.tar.gz some-other-archive.lzma
    or if installed via pip:
    * simple-extract some-archize.bz2

## Authors

Copyright 2021
Michael Berry <trismegustis@gmail.com>

## Version History

* 0.1.0
    * Initial Release
* 0.1.1
    * Change the way paths are handled if stdout is used

## License

This project is licensed under the MIT License - see the LICENSE file  for details.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
