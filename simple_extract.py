#!/usr/bin/env python

"""simple-extract.py

A small command line utility to download and extract compressed archives.

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


import argparse
import errno
import glob
import os
import pathlib
import shlex
import subprocess
import sys
import urllib.parse
import urllib.request


class ArchiveCommand:
    """Object for storing information needed to extract archives."""

    def __init__(self, decomp_cmd="", pipe_cmd="", uses_stdin=False, uses_stdout=False):
        """Set attributes for decompression and piping.

        :param decomp_cmd: command string to decompress archive
        :param pipe_cmd: command string to pipe
        :param uses_stdin: boolean value if decomp_cmd uses stdin
        :param uses_stdout: boolean value decomp_cmd uses stdout

        :returns: None
        """

        self.decomp_cmd = decomp_cmd
        self.pipe_cmd = pipe_cmd
        self.uses_stdin = uses_stdin
        self.uses_stdout = uses_stdout

    def __repr__(self):
        """Representation of the object.

        :returns: string representing ArchiveCommand
        """

        msg = f"[ decomp_cmd = {self.decomp_cmd!r} "
        msg += f"pipe_cmd = {self.pipe_cmd!r} "
        msg += f"uses_stdin = {self.uses_stdin!r} "
        msg += f"uses_stdout = {self.uses_stdout!r} ] "
        return msg


def command_exists(cmd):
    """Test for an external command's existence.

    :param cmd: external command to check for existence

    :returns: boolean value True if cmd exists, False otherwise
    """

    try:
        subprocess.Popen([cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError as e:
        if e.errno == errno.ENOENT:
            return False

    return True


def glob_multiple_extensions(extensions):
    """Iterate over a sequence of extensions to glob.

    :param extensions: a sequence of extensions to iterate over

    :returns: a list of positive matches globbed
    """

    files_globbed = []

    for ext in extensions:
        files_globbed.extend(glob.glob(ext))

    return files_globbed


def simple_extract(archive, archive_cmd, noclobber=False):
    """Extract an archive using external tools.

    :param archive: the archive to be extracted
    :param archive_cmd: a completed ArchiveCommand object
    :param noclobber: boolean option not to overwrite existing files (doesn't work with pipes)

    :returns: None
    """

    uses_stdin = archive_cmd.uses_stdin
    uses_stdout = archive_cmd.uses_stdout

    if uses_stdin or uses_stdout:
        decomp_cmd = shlex.split(archive_cmd.decomp_cmd)
    else:
        decomp_cmd = shlex.split(archive_cmd.decomp_cmd + " " + archive)

    pipe_cmd = shlex.split(archive_cmd.pipe_cmd)

    # Valid extension suffixes
    valid_suffixes = (
        ".tar.bz2",
        ".tbz2",
        ".tbz",
        ".tar.gz",
        ".tgz",
        ".tar.xz",
        ".txz",
        ".tar.lzma",
        ".tar.zst",
        ".tar",
        ".rar",
        ".lzh",
        ".7z",
        ".zip",
        ".jar",
        ".rpm",
        ".deb",
        ".bz2",
        ".gz",
        ".Z",
        ".xz",
        ".lzma",
        ".zst",
    )

    # Remove extensions from extraction target
    target_path = pathlib.PurePath(archive)
    target = target_path.stem
    for suffix in target_path.suffixes:
        if suffix in valid_suffixes:
            target = target.removesuffix(suffix)

    print(f"Target: {target}")

    if os.path.exists(target) and noclobber:
        print(f"Target: {target} already exists not overwriting...")
        return

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


def should_fetch_url(archive_url, local_archive):
    """Check if an archive should be fetched by comparing remote and local file sizes.

    :param archive_url: url of archive to be downloaded
    :param local_archive: possible local archive that may already have been downloaded

    :returns: boolean True if archive should downloaded, False otherwise
    """

    # return False if local archive does not exist
    if not os.path.exists(local_archive):
        return True

    # get content-size of remote archive
    req = urllib.request.Request(archive_url, method="HEAD")
    with urllib.request.urlopen(req) as f:
        remote_size = f.headers["content-length"]

    # get size of local archive
    local_size = os.path.getsize(local_archive)

    print(f"remote size: {remote_size}, local size: {local_size}")

    # compare remote and local sizes, if equal return False
    if int(remote_size) == int(local_size):
        print(
            f"Remote archive {archive_url} is the same size as local file {local_archive}. Skipping..."
        )
        return False
    else:
        print(
            f"Remote {archive_url} and local {local_archive} archives differ in size, downloading..."
        )

    return True


def fetch_archive(url, silent_download=False):
    """Download an archive for extraction.

    :param url: url of archive to be downloaded
    :param silent_download: boolean switch to quiet download output

    :returns: boolean False if failure, target archive if successful
    """

    _, target = os.path.split(url)

    if command_exists("curl"):
        if silent_download:
            fetch_cmd = shlex.split("curl -L -s -o -" + " " + url)
        else:
            fetch_cmd = shlex.split("curl -L -o -" + " " + url)
    elif command_exists("wget"):
        if silent_download:
            fetch_cmd = shlex.split("wget -q -O -" + " " + url)
        else:
            fetch_cmd = shlex.split("wget -O -" + " " + url)
    elif command_exists("fetch"):
        if silent_download:
            fetch_cmd = shlex.split("fetch -q -o -" + " " + url)
        else:
            fetch_cmd = shlex.split("fetch -o -" + " " + url)
    else:
        print("Error: no suitable download program found.")
        return False

    # Check if an archive should be downloaded
    if not should_fetch_url(url, target):
        return False

    print(f"Fetching archive {target}")

    with open(target, "w+") as fout:
        with subprocess.Popen(fetch_cmd, stdin=subprocess.PIPE, stdout=fout) as sproc:
            sproc.communicate()

    return target


def extract_urls(args):
    """Extract urls from a sequence.

    :param args: list of possible valid urls to download

    :returns: list of valid urls to download
    """

    possibles = [urllib.parse.urlsplit(x) for x in args]
    unfiltered = [x if x.scheme and x.netloc and x.path else None for x in possibles]
    processed_urls = list(filter(lambda x: x is not None, unfiltered))

    return [x.scheme + "://" + x.netloc + x.path for x in processed_urls]


def main():
    """Main function.
    This is where setup.py defines it's entry-point to create the simple-extract installable.

    :returns: None
    """

    parser = argparse.ArgumentParser(
        prog="simple-extract",
        description="A small command line utility to extract compressed archives.",
        epilog="Copyright (c) 2021 Michael Berry",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.8",
    )
    parser.add_argument(
        "--noclobber",
        action="store_true",
        help="Don't overwrite existing files",
        dest="noclobber",
    )
    parser.add_argument(
        "--silent_download",
        action="store_true",
        help="Don't show archive download progress",
        dest="silent_download",
    )
    parser.add_argument("ARCHIVES", nargs="*")
    parsed = parser.parse_args()

    working_dir = os.getcwd()
    args = [x for x in parsed.ARCHIVES]
    files_globbed = []
    commands = []

    # sanitize inputs
    possibles = [os.path.realpath(x) for x in args]
    unfiltered = [x if os.path.exists(x) else None for x in possibles]
    archives = list(filter(lambda x: x is not None, unfiltered))

    # append url archives
    url_archives = extract_urls(args)
    for url in url_archives:
        target = fetch_archive(url, silent_download=parsed.silent_download)
        if not target:
            continue
        archives.append(target)

    print(f"archives: {archives}")

    # create an ArchiveCommand for each archive, pass them to simple_extract
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
        print("Try passing --help as an argument for more information.")
        sys.exit(0)

    os.chdir(working_dir)

    # pass archives and their ArchiveCommand's to simple_extract
    for archive, archive_cmd in zip(files_globbed, commands):
        root_cmd = archive_cmd.decomp_cmd.split()[0]
        if not command_exists(root_cmd):
            print(f"Error: {root_cmd} does not exist...not extracting {archive}.")
            continue
        print(f"Extracting file {archive}")
        simple_extract(archive, archive_cmd, noclobber=parsed.noclobber)


# Program entry point if ran as a normal script, e.g. python simple_extract.py
if __name__ == "__main__":
    main()
