#!/usr/bin/env python3

"""simple_extract.py

simple-extract

A small command line utility to download and extract compressed archives.

Copyright (c) 2024 Michael Berry

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
import datetime
import errno
import glob
import logging
import os
import pathlib
import shlex
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

from . import __version__


# Enable logging
logging.basicConfig(
    level=logging.DEBUG, format="[%(levelname)-8s]  %(message)s"
)


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

        @return: None
        """

        self.extract_cmd = extract_cmd
        self.pipe_cmd = pipe_cmd
        self.uses_stdin = uses_stdin
        self.uses_stdout = uses_stdout

    def __repr__(self):
        """Representation of the object.

        @return: string representing ArchiveCommand
        """

        msg = f"[ extract_cmd = {self.extract_cmd!r} "
        msg += f"pipe_cmd = {self.pipe_cmd!r} "
        msg += f"uses_stdin = {self.uses_stdin!r} "
        msg += f"uses_stdout = {self.uses_stdout!r} ] "
        return msg


def command_exists(cmd):
    """Test for an external command's existence.

    @param cmd: external command to check for existence

    @return: boolean value True if cmd exists, False otherwise
    """

    try:
        subprocess.Popen(
            [cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    except OSError as e:
        if e.errno == errno.ENOENT:
            return False

    return True


def simple_extract(archive, archive_cmd, no_clobber=False):
    """Extract an archive using external tools.

    @param archive: the archive to be extracted
    @param archive_cmd: a completed ArchiveCommand object
    @param no_clobber: boolean option not to overwrite existing files

    @return: None
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

    logging.info("Target: %s", target)

    if os.path.exists(target) and no_clobber:
        logging.warning("Target: %s already exists not overwriting...", target)
        return

    # Extract archive
    with open(archive) as infile:
        if not pipe_cmd:
            if uses_stdin and not uses_stdout:
                try:
                    subprocess.run(extract_cmd, stdin=infile, check=True)
                except OSError as e:
                    logging.warning(
                        "Errno %d: %s - %s", e.errno, e.strerror, extract_cmd
                    )
            elif uses_stdin and uses_stdout:
                with open(target, "w+") as outfile:
                    try:
                        subprocess.run(
                            extract_cmd,
                            stdin=infile,
                            stdout=outfile,
                            check=True,
                        )
                    except OSError as e:
                        logging.warning(
                            "Errno %d: %s - %s", e.errno, e.strerror, extract_cmd
                        )
                        os.remove(target)
            else:
                try:
                    subprocess.run(extract_cmd, check=True)
                except OSError as e:
                    logging.warning(
                        "Errno %d: %s - %s", e.errno, e.strerror, extract_cmd
                    )
        else:
            with subprocess.Popen(
                extract_cmd, stdin=infile, stdout=subprocess.PIPE
            ) as cmd:
                try:
                    subprocess.run(pipe_cmd, stdin=cmd.stdout, check=True)
                except OSError as e:
                    logging.warning(
                        "Errno %d: %s - %s", e.errno, e.strerror, extract_cmd
                    )


def should_fetch_url(archive_url, local_archive):
    """Check if an archive should be fetched by comparing
    remote and local file sizes.

    @param archive_url: url of archive to be downloaded
    @param local_archive: local archive that may not need downloaded

    @return: boolean True if archive should be downloaded, False otherwise
    """

    logging.info("Validating archive url: %s", archive_url)

    # get content-size of remote archive
    req = urllib.request.Request(archive_url, method="HEAD")
    try:
        with urllib.request.urlopen(req) as f:
            if not f.headers["content-length"]:
                logging.warning(
                    "Error: invalid archive content-length, skipping download"
                )
                return False
            else:
                remote_size = f.headers["content-length"]
    except urllib.error.HTTPError as e:
        logging.warning("Error: The server couldn't fulfil the request")
        logging.warning("Error Code: %d", e.code)
        return False
    except urllib.error.URLError as e:
        logging.warning("Error: failed to reach the server")
        logging.warning("Reason: %s", e.reason)
        return False

    # archive should be fetched if a local copy does not exist
    if not os.path.exists(local_archive):
        return True

    # get size of local archive
    local_size = os.path.getsize(local_archive)

    logging.info("Comparing remote and local archives")
    logging.info("remote size: %d, local size: %d", remote_size, local_size)

    # compare remote and local sizes, if equal return False
    if int(remote_size) == int(local_size):
        logging.warning("Archive sizes are the same. Skipping download...")
        return False
    else:
        logging.info("Archives differ in size, downloading...")

    return True


def fetch_archive(url, silent_download=False, force_download=False):
    """Download an archive for extraction.

    @param url: url of archive to be downloaded
    @param silent_download: boolean switch to quiet download output
    @param force_download: boolean switch to bypass should_fetch_url()

    @return: boolean False if failure, target archive if successful
    """

    _, target = os.path.split(url)

    # determine which download tool to use
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
        logging.error("Error: no suitable download program found")
        return False

    # Check if an archive should be downloaded
    if not force_download:
        logging.info("Checking if archive should be downloaded")
        if not should_fetch_url(url, target):
            return False

    logging.info("Fetching archive %s", target)

    with open(target, "w+") as outfile:
        try:
            subprocess.run(
                fetch_cmd, stdin=subprocess.PIPE, stdout=outfile, check=True
            )
        except OSError as e:
            logging.warning(
                "Errno %d: %s - %s", e.errno, e.strerror, fetch_cmd
            )
            os.remove(target)
            return False

    return target


def extract_urls(args):
    """Extract urls from a sequence.

    @param args: list of possible valid urls to download

    @return: list of valid urls to download
    """

    possibles = [urllib.parse.urlsplit(x) for x in args]
    unfiltered = [
        x if x.scheme and x.netloc and x.path else None for x in possibles
    ]
    processed_urls = list(filter(lambda x: x is not None, unfiltered))

    return [x.scheme + "://" + x.netloc + x.path for x in processed_urls]


def main():
    """Main function.
    This is where project metadata defines an entry-point to
    create the simple-extract executable.

    @return: None
    """

    parser = argparse.ArgumentParser(
        prog="simple-extract",
        description="A small command line utility to extract compressed archives.",
        epilog="Copyright (c) 2024 Michael Berry",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"{__version__}",
    )
    parser.add_argument(
        "--no-clobber",
        action="store_true",
        help="Don't overwrite existing files",
        dest="no_clobber",
    )
    parser.add_argument(
        "--force-download",
        action="store_true",
        help="Bypass checks and always download remote archive",
        dest="force_download",
    )
    parser.add_argument(
        "--silent-download",
        action="store_true",
        help="Don't show archive download progress",
        dest="silent_download",
    )
    parser.add_argument("ARCHIVES", nargs="*")
    parsed = parser.parse_args()

    start_time = datetime.datetime.now()
    logging.info("Starting simple-extract @ %s, start_time")

    working_dir = os.getcwd()
    args = [x for x in parsed.ARCHIVES]
    glob_files = []
    commands = []
    command_map = {
        "*.tar.bz2": ArchiveCommand(
            extract_cmd="tar -xvjf -", uses_stdin=True
        ),
        "*.tbz2": ArchiveCommand(extract_cmd="tar -xvjf -", uses_stdin=True),
        "*.tbz": ArchiveCommand(extract_cmd="tar -xvjf -", uses_stdin=True),
        "*.tar.gz": ArchiveCommand(extract_cmd="tar -xvzf -", uses_stdin=True),
        "*.tgz": ArchiveCommand(extract_cmd="tar -xvzf -", uses_stdin=True),
        "*.tar.xz": ArchiveCommand(extract_cmd="tar -xvJf -", uses_stdin=True),
        "*.txz": ArchiveCommand(extract_cmd="tar -xvJf -", uses_stdin=True),
        "*.tar.lzma": ArchiveCommand(
            extract_cmd="tar -xvJf -", uses_stdin=True
        ),
        "*.tar.zst": ArchiveCommand(
            extract_cmd="tar --zstd -xvf -", uses_stdin=True
        ),
        "*.tar": ArchiveCommand(extract_cmd="tar -xvf -", uses_stdin=True),
        "*.rar": ArchiveCommand(extract_cmd="unrar x"),
        "*.lzh": ArchiveCommand(extract_cmd="lha x"),
        "*.7z": ArchiveCommand(extract_cmd="7z x"),
        "*.zip": ArchiveCommand(extract_cmd="unzip"),
        "*.jar": ArchiveCommand(extract_cmd="unzip"),
        "*.rpm": ArchiveCommand(
            extract_cmd="rpm2cpio -", pipe_cmd="cpio -idvm"
        ),
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

    # sanitize inputs, silently drop bad paths
    possibles = [os.path.realpath(x) for x in args]
    unfiltered = [x if os.path.exists(x) else None for x in possibles]
    archives = list(filter(lambda x: x is not None, unfiltered))

    # append url archives
    url_archives = extract_urls(args)
    for url in url_archives:
        target = fetch_archive(
            url,
            silent_download=parsed.silent_download,
            force_download=parsed.force_download,
        )
        if not target:
            continue
        archives.append(target)

    if not archives:
        logging.info("Nothing to do.")
        logging.info("Try passing --help as an argument for more information.")
        sys.exit(0)

    logging.info("Archives queued for extraction: %r", archives)

    # store an archive and an ArchiveCommand to be zipped
    # then passed to simple_extract
    for archive in archives:
        logging.info("Examining archive: %s", archive)

        pathname, filename = os.path.split(archive)
        if pathname and archive not in url_archives:
            os.chdir(pathname)

        for extension, command in command_map.items():
            if filename in glob.glob(extension):
                if archive not in glob_files:
                    glob_files.append(archive)
                    commands.append(command)

    logging.info("Archives that can be extracted: %r", glob_files)

    os.chdir(working_dir)

    # pass archives and their ArchiveCommand's to simple_extract
    for archive, archive_cmd in zip(glob_files, commands):
        root_cmd = archive_cmd.extract_cmd.split()[0]
        if not command_exists(root_cmd):
            logging.warning(
                "Error: %s does not exist...not extracting %s.",root_cmd, archive
            )
            continue
        logging.info("Extracting archive %s", archive)
        simple_extract(archive, archive_cmd, no_clobber=parsed.no_clobber)

    end_time = datetime.datetime.now()
    logging.info("simple-extract finished @ %s", end_time)
    elapsed_time = end_time - start_time
    logging.info("Total time elapsed %s", elapsed_time)


if __name__ == "__main__":
    main()
