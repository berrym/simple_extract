#!/usr/bin/env python

"""simple-extract.py

A small script to simplify the extraction of compressed archives.

Copyright (c) 2021 Michael Berry

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""


from pathlib import Path
from urllib.request import Request
from urllib.request import urlopen
from urllib.parse import urlsplit

import errno
import glob
import os
import shlex
import subprocess
import sys


class ArchiveCommand:
    """Object for storing information needed to extract archives."""

    def __init__(self, decomp_cmd="", pipe_cmd="", uses_stdin=False, uses_stdout=False):
        """Set attributes for decompression and piping."""

        self.decomp_cmd = decomp_cmd
        self.pipe_cmd = pipe_cmd
        self.uses_stdin = uses_stdin
        self.uses_stdout = uses_stdout

    def __repr__(self):
        """Representation of the object."""

        msg = f"[ decomp_cmd = {self.decomp_cmd!r} "
        msg += f"pipe_cmd = {self.pipe_cmd!r} "
        msg += f"uses_stdin = {self.uses_stdin!r} "
        msg += f"uses_stdout = {self.uses_stdout!r} ] "
        return msg


def command_exists(cmd):
    """Test for an external command's existence."""

    try:
        subprocess.Popen([cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError as e:
        if e.errno == errno.ENOENT:
            return False

    return True


def glob_multiple_extensions(extensions):
    """Iterate over a sequence of extensions to glob."""

    files_globbed = []

    for ext in extensions:
        files_globbed.extend(glob.glob(ext))

    return files_globbed


def simple_extract(archive, archive_cmd):
    """Extract an archive using external tools."""

    uses_stdin = archive_cmd.uses_stdin
    uses_stdout = archive_cmd.uses_stdout

    if uses_stdin or uses_stdout:
        decomp_cmd = shlex.split(archive_cmd.decomp_cmd)
    else:
        decomp_cmd = shlex.split(archive_cmd.decomp_cmd + " " + archive)

    pipe_cmd = shlex.split(archive_cmd.pipe_cmd)

    # Split archive name separating extensions
    path = Path(archive)
    target, _ = os.path.split(path.stem)

    # Extract archive
    with open(archive) as fin:
        if not pipe_cmd:
            if uses_stdin and not uses_stdout:
                # use a context manager so each subprocess is waited on
                with subprocess.Popen(decomp_cmd, stdin=fin) as sproc:
                    sproc.communicate()
            elif uses_stdin and uses_stdout:
                with open(target, "w+") as fout:
                    with subprocess.Popen(decomp_cmd, stdin=fin, stdout=fout) as sproc:
                        sproc.communicate()
            else:
                with subprocess.Popen(decomp_cmd) as _:
                    pass
        else:
            with subprocess.Popen(decomp_cmd, stdin=fin, stdout=subprocess.PIPE) as cmd:
                subprocess.run(pipe_cmd, stdin=cmd.stdout, check=True)


def should_fetch_url(url, fp):
    """Check if an archive should be fetched by comparing remote and local file sizes."""

    req = Request(url, method="HEAD")
    with urlopen(req) as f:
        remote_size = f.headers["content-length"]
        local_size = os.path.getsize(fp)

    print(f"remote size: {remote_size}, local size: {local_size}")

    if int(remote_size) == int(local_size):
        print(f"Remote archive {url} is the same size as local file {fp}. Skipping...")
        return False
    else:
        print(f"Remote and local archives differ in size, downloading...")

    return True


def fetch_archive(url):
    """Download an archive for extraction."""

    _, target = os.path.split(url)

    if command_exists("curl"):
        fetch_cmd = shlex.split("curl -L -s -o -" + " " + url)
    elif command_exists("wget"):
        fetch_cmd = shlex.split("wget -q -O -" + " " + url)
    elif command_exists("fetch"):
        fetch_cmd = shlex.split("fetch -q -o -" + " " + url)
    else:
        print("Error: no suitable download program found.")
        return False

    # Check if an archive should be downloaded
    if os.path.exists(target):
        if not should_fetch_url(url, target):
            return False

    print(f"Fetching archive {target}")

    with open(target, "w+") as fout:
        with subprocess.Popen(fetch_cmd, stdin=subprocess.PIPE, stdout=fout) as sproc:
            sproc.communicate()

    return target


def extract_urls(args):
    """Extract urls from a sequence."""

    possibles = [urlsplit(x) for x in args]
    unfiltered = [x if x.scheme and x.netloc and x.path else None for x in possibles]
    processed_urls = list(filter(lambda x: x is not None, unfiltered))

    return [x.scheme + "://" + x.netloc + x.path for x in processed_urls]


def main():
    """Main function."""

    working_dir = os.getcwd()
    args = sys.argv[1:]
    files_globbed = []
    commands = []

    # sanitize inputs
    possibles = [os.path.realpath(x) for x in args]
    unfiltered = [x if os.path.exists(x) else None for x in possibles]
    archives = list(filter(lambda x: x is not None, unfiltered))

    url_archives = extract_urls(args)
    for url in url_archives:
        target = fetch_archive(url)
        if not target:
            continue
        archives.append(target)

    print(f"archives: {archives}")

    for archive in archives:
        print(f"Examining archive: {archive}")

        pn, fn = os.path.split(archive)
        if pn and archive not in url_archives:
            os.chdir(pn)

        if fn in glob_multiple_extensions(("*tar.bz2", "*tbz2", "*tbz")):
            files_globbed.append(archive)
            cmd = ArchiveCommand(decomp_cmd="tar -xvjf -", uses_stdin=True)
            commands.append(cmd)
        elif fn in glob_multiple_extensions(("*tar.gz", "*tgz")):
            files_globbed.append(archive)
            cmd = ArchiveCommand(decomp_cmd="tar -xvzf -", uses_stdin=True)
            commands.append(cmd)
        elif fn in glob_multiple_extensions(("*tar.xz", "*txz", "*tar.lzma")):
            files_globbed.append(archive)
            cmd = ArchiveCommand(decomp_cmd="tar -xvJf -", uses_stdin=True)
            commands.append(cmd)
        elif fn in glob.glob("*tar.zst"):
            files_globbed.append(archive)
            cmd = ArchiveCommand(decomp_cmd="tar --zstd -xvf -", uses_stdin=True)
            commands.append(cmd)
        elif fn in glob.glob("*tar"):
            files_globbed.append(archive)
            cmd = ArchiveCommand(decomp_cmd="tar -xvf -", uses_stdin=True)
            commands.append(cmd)
        elif fn in glob.glob("*rar"):
            files_globbed.append(archive)
            cmd = ArchiveCommand(decomp_cmd="unrar x")
            commands.append(cmd)
        elif fn in glob.glob("*lzh"):
            files_globbed.append(archive)
            cmd = ArchiveCommand(decomp_cmd="lha x")
            commands.append(cmd)
        elif fn in glob.glob("*7z"):
            files_globbed.append(archive)
            cmd = ArchiveCommand(decomp_cmd="7z x")
            commands.append(cmd)
        elif fn in glob_multiple_extensions(("*zip", "*jar")):
            files_globbed.append(archive)
            cmd = ArchiveCommand(decomp_cmd="unzip")
            commands.append(cmd)
        elif fn in glob.glob("*rpm"):
            files_globbed.append(archive)
            cmd = ArchiveCommand(decomp_cmd="rpm2cpio -", pipe_cmd="cpio -idvm")
            commands.append(cmd)
        elif fn in glob.glob("*deb"):
            files_globbed.append(archive)
            cmd = ArchiveCommand(decomp_cmd="ar -x")
            commands.append(cmd)
        elif fn in glob.glob("*bz2"):
            files_globbed.append(archive)
            cmd = ArchiveCommand(
                decomp_cmd="bzip2 -d -c -", uses_stdin=True, uses_stdout=True
            )
            commands.append(cmd)
        elif fn in glob_multiple_extensions(("*gz", "*Z")):
            files_globbed.append(archive)
            cmd = ArchiveCommand(
                decomp_cmd="gzip -d -c -", uses_stdin=True, uses_stdout=True
            )
            commands.append(cmd)
        elif fn in glob_multiple_extensions(("*xz", "*lzma")):
            files_globbed.append(archive)
            cmd = ArchiveCommand(
                decomp_cmd="xz -d -c -", uses_stdin=True, uses_stdout=True
            )
            commands.append(cmd)
        elif fn in glob.glob("*zst"):
            files_globbed.append(archive)
            cmd = ArchiveCommand(
                decomp_cmd="zstd -d -c -", uses_stdin=True, uses_stdout=True
            )
            commands.append(cmd)

    if files_globbed:
        print(f"Files to extract: {files_globbed}")
    else:
        print("Nothing to do.")
        sys.exit(0)

    os.chdir(working_dir)

    for archive, archive_cmd in zip(files_globbed, commands):
        root_cmd = archive_cmd.decomp_cmd.split()[0]
        if not command_exists(root_cmd):
            print(f"Error: {root_cmd} does not exist...not extracting {archive}.")
            continue
        print(f"Extracting file {archive}")
        simple_extract(archive, archive_cmd)


if __name__ == "__main__":
    main()
