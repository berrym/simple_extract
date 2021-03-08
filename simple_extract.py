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
import urllib.error
import urllib.parse
import urllib.request


class ArchiveCommand:
    """Object for storing information needed to extract archives."""

    def __init__(
        self, extract_cmd="", pipe_cmd="", uses_stdin=False, uses_stdout=False
    ):
        """Set attributes for decompression and piping.

        @param extract_cmd: command string to decompress archive
        @param pipe_cmd: command string to pipe
        @param uses_stdin: boolean value if extract_cmd uses stdin
        @param uses_stdout: boolean value extract_cmd uses stdout

        @returns: None
        """

        self.extract_cmd = extract_cmd
        self.pipe_cmd = pipe_cmd
        self.uses_stdin = uses_stdin
        self.uses_stdout = uses_stdout

    def __repr__(self):
        """Representation of the object.

        @returns: string representing ArchiveCommand
        """

        msg = f"[ extract_cmd = {self.extract_cmd!r} "
        msg += f"pipe_cmd = {self.pipe_cmd!r} "
        msg += f"uses_stdin = {self.uses_stdin!r} "
        msg += f"uses_stdout = {self.uses_stdout!r} ] "
        return msg


def command_exists(cmd):
    """Test for an external command's existence.

    @param cmd: external command to check for existence

    @returns: boolean value True if cmd exists, False otherwise
    """

    try:
        subprocess.Popen([cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError as e:
        if e.errno == errno.ENOENT:
            return False

    return True


def glob_multiple_extensions(extensions):
    """Iterate over a sequence of extensions to glob.

    @param extensions: a sequence of extensions to iterate over

    @returns: a list of positive glob matches
    """

    glob_files = []

    for ext in extensions:
        glob_files.extend(glob.glob(ext))

    return glob_files


def simple_extract(archive, archive_cmd, no_clobber=False):
    """Extract an archive using external tools.

    @param archive: the archive to be extracted
    @param archive_cmd: a completed ArchiveCommand object
    @param no_clobber: boolean option not to overwrite existing files

    @returns: None
    """

    uses_stdin = archive_cmd.uses_stdin
    uses_stdout = archive_cmd.uses_stdout

    if uses_stdin or uses_stdout:
        extract_cmd = shlex.split(archive_cmd.extract_cmd)
    else:
        extract_cmd = shlex.split(archive_cmd.extract_cmd + " " + archive)

    pipe_cmd = shlex.split(archive_cmd.pipe_cmd)

    # Valid extension suffixes
    valid_suffixes = (
        ".tbz2",
        ".tbz",
        ".tgz",
        ".txz",
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

    if os.path.exists(target) and no_clobber:
        print(f"Target: {target} already exists not overwriting...")
        return

    # Extract archive
    with open(archive) as fin:
        if not pipe_cmd:
            if uses_stdin and not uses_stdout:
                try:
                    subprocess.run(extract_cmd, stdin=fin, check=True)
                except subprocess.CalledProcessError as e:
                    print(f"Error: Return Code = {e.returncode} {e.output or ''}")
            elif uses_stdin and uses_stdout:
                with open(target, "w+") as outfile:
                    try:
                        subprocess.run(
                            extract_cmd, stdin=fin, stdout=outfile, check=True
                        )
                    except subprocess.CalledProcessError as e:
                        print(f"Error: Return Code = {e.returncode} {e.output or ''}")
                        os.remove(target)
            else:
                try:
                    subprocess.run(extract_cmd, check=True)
                except subprocess.CalledProcessError as e:
                    print(f"Error: Return Code = {e.returncode} {e.output or ''}")
        else:
            with subprocess.Popen(
                extract_cmd, stdin=fin, stdout=subprocess.PIPE
            ) as cmd:
                try:
                    subprocess.run(pipe_cmd, stdin=cmd.stdout, check=True)
                except subprocess.CalledProcessError as e:
                    print(f"Error: Return Code = {e.returncode} {e.output or ''}")


def should_fetch_url(archive_url, local_archive):
    """Check if an archive should be fetched by comparing remote and local file sizes.

    @param archive_url: url of archive to be downloaded
    @param local_archive: possible local archive that may already have been downloaded

    @returns: boolean True if archive should downloaded, False otherwise
    """

    print(f"Validating archive url: {archive_url}")

    # get content-size of remote archive
    req = urllib.request.Request(archive_url, method="HEAD")
    try:
        with urllib.request.urlopen(req) as f:
            remote_size = f.headers["content-length"]
    except urllib.error.HTTPError as e:
        print("Error: The server couldn't fulfil the request")
        print(f"Error Code: {e.code}")
        return False
    except urllib.error.URLError as e:
        print("Error: failed to reach the server")
        print(f"Reason: {e.reason}")
        return False

    # archive should be fetched if a local copy does not exist
    if not os.path.exists(local_archive):
        return True

    # get size of local archive
    local_size = os.path.getsize(local_archive)

    print(f"Comparing remote and local archives")
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

    @param url: url of archive to be downloaded
    @param silent_download: boolean switch to quiet download output

    @returns: boolean False if failure, target archive if successful
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
        return target

    print(f"Fetching archive {target}")

    with open(target, "w+") as outfile:
        try:
            subprocess.run(fetch_cmd, stdin=subprocess.PIPE, stdout=outfile, check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error: Return Code = {e.returncode} {e.output or ''}")
            os.remove(target)
            return False

    return target


def extract_urls(args):
    """Extract urls from a sequence.

    @param args: list of possible valid urls to download

    @returns: list of valid urls to download
    """

    possibles = [urllib.parse.urlsplit(x) for x in args]
    unfiltered = [x if x.scheme and x.netloc and x.path else None for x in possibles]
    processed_urls = list(filter(lambda x: x is not None, unfiltered))

    return [x.scheme + "://" + x.netloc + x.path for x in processed_urls]


def main():
    """Main function.
    This is where setup.py defines it's entry-point to create the simple-extract installable.

    @returns: None
    """

    parser = argparse.ArgumentParser(
        prog="simple-extract",
        description="A small command line utility to extract compressed archives.",
        epilog="Copyright (c) 2021 Michael Berry",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.2.1",
    )
    parser.add_argument(
        "--no_clobber",
        action="store_true",
        help="Don't overwrite existing files",
        dest="no_clobber",
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
    glob_files = []
    commands = []
    command_map = {
        "*.tar.bz2": ArchiveCommand(extract_cmd="tar -xvjf -", uses_stdin=True),
        "*.tbz2": ArchiveCommand(extract_cmd="tar -xvjf -", uses_stdin=True),
        "*.tbz": ArchiveCommand(extract_cmd="tar -xvjf -", uses_stdin=True),
        "*.tar.gz": ArchiveCommand(extract_cmd="tar -xvzf -", uses_stdin=True),
        "*.tgz": ArchiveCommand(extract_cmd="tar -xvzf -", uses_stdin=True),
        "*.tar.xz": ArchiveCommand(extract_cmd="tar -xvJf -", uses_stdin=True),
        "*.txz": ArchiveCommand(extract_cmd="tar -xvJf -", uses_stdin=True),
        "*.tar.lzma": ArchiveCommand(extract_cmd="tar -xvJf -", uses_stdin=True),
        "*.tar.zst": ArchiveCommand(extract_cmd="tar --zstd -xvf -", uses_stdin=True),
        "*.tar": ArchiveCommand(extract_cmd="tar -xvf -", uses_stdin=True),
        "*.rar": ArchiveCommand(extract_cmd="unrar x"),
        "*.lzh": ArchiveCommand(extract_cmd="lha x"),
        "*.7z": ArchiveCommand(extract_cmd="7z x"),
        "*.zip": ArchiveCommand(extract_cmd="unzip"),
        "*.jar": ArchiveCommand(extract_cmd="unzip"),
        "*.rpm": ArchiveCommand(extract_cmd="rpm2cpio -", pipe_cmd="cpio -idvm"),
        "*.deb": ArchiveCommand(extract_cmd="ar -x"),
        "*.bz2": ArchiveCommand(
            extract_cmd="bzip2 -d -c -", uses_stdin=True, uses_stdout=True
        ),
        "*.gz": ArchiveCommand(
            extract_cmd="gzip -d -c -", uses_stdin=True, uses_stdout=True
        ),
        "*.Z": ArchiveCommand(
            extract_cmd="gzip -d -c -", uses_stdin=True, uses_stdout=True
        ),
        "*.xz": ArchiveCommand(
            extract_cmd="xz -d -c -", uses_stdin=True, uses_stdout=True
        ),
        "*.lzma": ArchiveCommand(
            extract_cmd="xz -d -c -", uses_stdin=True, uses_stdout=True
        ),
        "*.zst": ArchiveCommand(
            extract_cmd="zstd -d -c -", uses_stdin=True, uses_stdout=True
        ),
    }

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

    if len(archives):
        print(f"archives: {archives}")

        # create an ArchiveCommand for each archive, pass them to simple_extract
        for archive in archives:
            print(f"Examining archive: {archive}")

            pathname, filename = os.path.split(archive)
            if pathname and archive not in url_archives:
                os.chdir(pathname)

            for extension, command in command_map.items():
                if filename in glob.glob(extension):
                    if archive not in glob_files:
                        glob_files.append(archive)
                        commands.append(command_map[extension])

        if glob_files:
            print(f"Files to extract: {glob_files}")
    else:
        print("Nothing to do.")
        print("Try passing --help as an argument for more information.")
        sys.exit(0)

    os.chdir(working_dir)

    # pass archives and their ArchiveCommand's to simple_extract
    for archive, archive_cmd in zip(glob_files, commands):
        root_cmd = archive_cmd.extract_cmd.split()[0]
        if not command_exists(root_cmd):
            print(f"Error: {root_cmd} does not exist...not extracting {archive}.")
            continue
        print(f"Extracting file {archive}")
        simple_extract(archive, archive_cmd, no_clobber=parsed.no_clobber)


# Program entry point if ran as a normal script, e.g. python simple_extract.py
if __name__ == "__main__":
    main()
