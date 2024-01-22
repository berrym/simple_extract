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

    $ clone the git repository from https://github.com/berrym/simple_extract.git
    or:
    $ python3 -m pip install simple-extract
    or:
    $ python3 -m pip install --user simple-extract

### Executing program

    $ python3 simple_extract.py some-archive.tar.gz some-other-archive.lzma
    or if installed via pip:
    $ simple-extract https://github.com/ibara/mg/releases/download/mg-6.8.1/mg-6.8.1.tar.gz

## Authors

Copyright 2024 Michael Berry <trismegustis@gmail.com>

## License

This project is licensed under the MIT License - see the LICENSE file for details.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![build result](https://build.opensuse.org/projects/home:berrym/packages/simple-extract/badge.svg?type=default)](https://build.opensuse.org/package/show/home:berrym/simple-extract)
