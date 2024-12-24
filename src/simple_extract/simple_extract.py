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

from typing import override

from . import __version__


# Enable logging
logging.basicConfig(level=logging.DEBUG, format="[%(levelname)-8s]  %(message)s")


class ArchiveCommand:
    """Object for storing information needed to extract archives."""

    def __init__(
        self,
        extract_cmd: str = "",
        pipe_cmd: str = "",
        uses_stdin: bool = False,
        uses_stdout: bool = False,
    ) -> None:
        """Set attributes for decompression and piping.

        @param extract_cmd: command string to decompress archive
        @param pipe_cmd: command string to pipe
        @param uses_stdin: boolean value if extract_cmd uses stdin
        @param uses_stdout: boolean value extract_cmd uses stdout

        @return: None
        """

        self.extract_cmd: str = extract_cmd
        self.pipe_cmd: str = pipe_cmd
        self.uses_stdin: bool = uses_stdin
        self.uses_stdout: bool = uses_stdout

    @override
    def __repr__(self) -> str:
        """Representation of the object.

        @return: string representing ArchiveCommand
        """

        msg = f"[ extract_cmd = {self.extract_cmd!r} "
        msg += f"pipe_cmd = {self.pipe_cmd!r} "
        msg += f"uses_stdin = {self.uses_stdin!r} "
        msg += f"uses_stdout = {self.uses_stdout!r} ] "
        return msg

    @override
    def __str__(self) -> str:
        """String representation of the object.

        @return: string representing ArchiveCommand
        """

        msg = f"[ extract_cmd = {self.extract_cmd} "
        msg += f"pipe_cmd = {self.pipe_cmd} "
        msg += f"uses_stdin = {self.uses_stdin} "
        msg += f"uses_stdout = {self.uses_stdout} ] "
        return msg


def command_exists(path: str) -> bool:
    """Test for an external command's existence.

    @param path: external command path to check for existence

    @return: boolean value True if cmd exists, False otherwise
    """

    try:
        with subprocess.Popen(
            [path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        ) as _:
            pass
    except OSError as e:
        if e.errno == errno.ENOENT:
            return False

    return True


def strip_suffix(archive: str) -> str:
    """Remove extensions from extraction target.

    @param archive: complete archive path with extension suffixes.

    @return: complete archive path with extension suffixes removed.
    """

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

    target_path = pathlib.PurePath(archive)
    target = target_path.stem
    for suffix in target_path.suffixes:
        if suffix in valid_suffixes:
            target = target.removesuffix(suffix)

    return target


def simple_extract(
    archive: str, archive_cmd: ArchiveCommand, no_clobber: bool = False
) -> None:
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

    target = strip_suffix(archive)

    logging.info("Target: %s", target)

    if os.path.exists(target) and no_clobber:
        logging.warning("Target: %s already exists not overwriting...", target)
        return

    # Extract archive
    with open(archive, encoding="utf8") as infile:
        if not pipe_cmd:
            if uses_stdin and not uses_stdout:
                try:
                    _ = subprocess.run(extract_cmd, stdin=infile, check=True)
                except OSError as e:
                    logging.warning(
                        "Errno %d: %s - %s", e.errno, e.strerror, extract_cmd
                    )
                return

            if uses_stdin and uses_stdout:
                with open(target, "w+", encoding="utf8") as outfile:
                    try:
                        _ = subprocess.run(
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
                    return
            else:
                try:
                    _ = subprocess.run(extract_cmd, check=True)
                except OSError as e:
                    logging.warning(
                        "Errno %d: %s - %s", e.errno, e.strerror, extract_cmd
                    )
                return

        # Piped command
        with subprocess.Popen(extract_cmd, stdin=infile, stdout=subprocess.PIPE) as cmd:
            try:
                _ = subprocess.run(pipe_cmd, stdin=cmd.stdout, check=True)
            except OSError as e:
                logging.warning("Errno %d: %s -> %s", e.errno, e.strerror, extract_cmd)


def should_fetch_url(archive_url: str, local_archive: str) -> bool:
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
        f: urllib.request.Request
        with urllib.request.urlopen(req) as f:
            if not f.headers["content-length"]:
                logging.warning(
                    "Error: invalid archive content-length, skipping download"
                )
                return False

            remote_size: str = f.headers["content-length"]
    except urllib.error.HTTPError as e:
        logging.warning("Error: The server couldn't fulfill the request")
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

    logging.info("Archives differ in size, downloading...")

    return True


def make_download_command(url: str, silent_download: bool = False) -> list[str] | None:
    """Make a valid command line string to download a url.

    @param url: url of archive to be downloaded
    @param silent_download: boolean switch to suppress download output

    @return: command string or None
    """

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
        return None

    return fetch_cmd


def fetch_archive(
    url: str, silent_download: bool = False, force_download: bool = False
) -> str | None:
    """Download an archive for extraction.

    @param url: url of archive to be downloaded
    @param silent_download: boolean switch to quiet download output
    @param force_download: boolean switch to bypass should_fetch_url()

    @return: None if failure, target archive if successful
    """

    _, target = os.path.split(url)

    fetch_cmd = make_download_command(url, silent_download=silent_download)

    if fetch_cmd is None:
        return None

    # Check if an archive should be downloaded
    if not force_download:
        logging.info("Checking if archive should be downloaded")
        if not should_fetch_url(url, target):
            return None

    logging.info("Fetching archive %s", target)

    with open(target, "w+", encoding="utf8") as outfile:
        try:
            _ = subprocess.run(
                fetch_cmd, stdin=subprocess.PIPE, stdout=outfile, check=True
            )
        except OSError as e:
            logging.warning("Errno %d: %s - %s", e.errno, e.strerror, fetch_cmd)
            os.remove(target)
            return None

    return target


def extract_urls(args: list[str]) -> list[str]:
    """Extract urls from a sequence.

    @param args: list of possible valid urls to download

    @return: list of valid urls to download
    """

    possibles = [urllib.parse.urlsplit(x) for x in args]
    unfiltered = [x if x.scheme and x.netloc and x.path else None for x in possibles]
    processed_urls = list(filter(lambda x: x is not None, unfiltered))

    return [
        x.scheme + "://" + x.netloc + x.path for x in processed_urls if x is not None
    ]


def process_archives(
    paths: list[str], force_download: bool = False, silent_download: bool = False
) -> tuple[list[str], list[str]]:
    """Create lists of archives.

    @param paths: a list of paths to archives
    @param force_download: a boolean switch to force downloading an archive
    @param silent_download: a boolean switch to suppress output when downloading

    @return: a list of archives and url archives
    """

    # sanitize inputs, silently drop bad paths
    possibles: list[str] = [os.path.realpath(x) for x in paths]
    unfiltered = [x if os.path.exists(x) else None for x in possibles]
    filtered = list(filter(lambda x: x is not None, unfiltered))
    archives: list[str] = [x for x in filtered if x is not None]

    # append url archives
    url_archives = extract_urls(paths)
    for url in url_archives:
        target = fetch_archive(
            url,
            silent_download=silent_download,
            force_download=force_download,
        )
        if not target:
            continue
        archives.append(target)

    if not archives:
        logging.info("Nothing to do.")
        logging.info("Try passing --help as an argument for more information.")
        sys.exit(0)

    return archives, url_archives


def process_commands(
    archives: list[str], url_archives: list[str]
) -> tuple[list[str], list[ArchiveCommand]]:
    """Create ArchiveCommands.

    @param archives: a list of local archives
    @param url_archives: a list of potential archives to download

    @return: a tuple of a list of archive files and a list of ArchiveCommands
    """

    working_dir = os.getcwd()
    glob_files: list[str] = []
    commands: list[ArchiveCommand] = []
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

    return glob_files, commands


def do_simple_extract(
    glob_files: list[str], commands: list[ArchiveCommand], no_clobber: bool = False
) -> None:
    """Run simple_extract on corresponding lists of archives and commands.

    @glob_files: list of archives
    @commands: list of ArchiveCommand

    @return: None
    """

    # pass archives and their ArchiveCommand's to simple_extract
    for archive, archive_cmd in zip(glob_files, commands):
        root_cmd = archive_cmd.extract_cmd.split()[0]
        if not command_exists(root_cmd):
            logging.warning(
                "Error: %s does not exist...not extracting %s.", root_cmd, archive
            )
            continue
        logging.info("Extracting archive %s", archive)
        simple_extract(archive, archive_cmd, no_clobber=no_clobber)


def main() -> None:
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
    _ = parser.add_argument(
        "--version",
        action="version",
        version=f"{__version__}",
    )
    _ = parser.add_argument(
        "--no-clobber",
        action="store_true",
        help="Don't overwrite existing files",
        dest="no_clobber",
    )
    _ = parser.add_argument(
        "--force-download",
        action="store_true",
        default=False,
        help="Bypass checks and always download remote archive",
        dest="force_download",
    )
    _ = parser.add_argument(
        "--silent-download",
        action="store_true",
        default=False,
        help="Don't show archive download progress",
        dest="silent_download",
    )
    _ = parser.add_argument("ARCHIVES", nargs="*")
    opts = vars(parser.parse_args())

    start_time = datetime.datetime.now()
    logging.info("Starting simple-extract @ %s", start_time)

    paths: list[str] = opts["ARCHIVES"]
    force_download: bool = opts["force_download"]
    silent_download: bool = opts["silent_download"]
    no_clobber: bool = opts["no_clobber"]

    archives, url_archives = process_archives(
        paths, force_download=force_download, silent_download=silent_download
    )

    logging.info("Archives queued for extraction: %r", archives)

    glob_files, commands = process_commands(archives, url_archives)

    do_simple_extract(glob_files, commands, no_clobber=no_clobber)

    end_time = datetime.datetime.now()
    logging.info("simple-extract finished @ %s", end_time)
    elapsed_time = end_time - start_time
    logging.info("Total time elapsed %s", elapsed_time)
