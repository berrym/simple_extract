# simple-extract

Simple File Extraction

## Description

A small command line file extraction utility written in Python. It uses external tools to optionally fetch from an url and decompress many types of archives.

## Getting started

Python >= *3.12* **needed**

External tools that can be used:

- `tar`
- `gzip`
- `bzip2`
- `unrar`
- `lha`
- `7z`
- `unzip`
- `rpm2cpio`
- `cpio`
- `ar`
- `xz`
- `zstd`
- `curl`
- `wget`
- `fetch`

### Installing

## Manual local install

    $ clone the git repository from https://github.com/berrym/simple_extract.git
    $ python3 -m venv .venv
    $ source .venv/bin/acivate
    $ python3 -m build
    $ pip3 install .

## Package installation **Recommended**

    $ python3 -m pip install simple-extract         # if you have permissions

**or**

    $ python3 -m pip install --user simple-extract  # will store in user's local directories

**or** **Recommended** install method

    $ pipx install simple-extract  # will install to a venv and install an executable link

### Executing program

    $ /path/to/venv/bin/simple-extract  # if cloned and manually built but no longer in the venv.

**or** if installed via pip, pipx

    $ simple-extract https://github.com/ibara/mg/releases/download/mg-6.8.1/mg-6.8.1.tar.gz

### Tip

If you have a shell environment that supports aliases, it's useful to alias simple-extract.

On common unix/linux shells you might run or put this in your shell rc script.

    $ alias se='simple-extract'

Then you can execute the program by typing `se`

## Authors

Copyright 2025 Michael Berry <trismegustis@gmail.com>

## License

This project is licensed under the MIT License - see the LICENSE file for details.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![build result](https://build.opensuse.org/projects/home:berrym/packages/simple-extract/badge.svg?type=default)](https://build.opensuse.org/package/show/home:berrym/simple-extract)
[![Copr build status](https://copr.fedorainfracloud.org/coprs/mberry/simple-extract/package/simple-extract/status_image/last_build.png)](https://copr.fedorainfracloud.org/coprs/mberry/simple-extract/package/simple-extract/)
