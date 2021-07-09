"""Collection of functions for files.

Methods
--------
atomic_write(data, output_file)
    Write to file as atmoic operation.
mkdir_p(path)
    Mimics the linux call 'mkdir -p'.
open_file(filename, open_mode)
    Returns the file handle for either a gzip file or text file.
parse_options_in_string(options, unique_keys)
    Assumes the input contains option/value pairs and parses them.
"""

import errno
import gzip
import logging
import os
import shlex
import sys
import re
import tempfile

logger = logging.getLogger(__name__)

def atomic_write(data, output_file):
    """Write to file as an atomic operation.

    Parameters
    ----------
    data : str
        Data that we want to write to the file.
    output_file: str
        Path of the output file.
    """
    temp_file = tempfile.NamedTemporaryFile(delete=False, dir=os.path.dirname(output_file))
    try:
        with open_file(temp_file.name, "w") as fout:
            fout.write(data)
            fout.flush()
            os.fsync(fout.fileno())
        os.replace(temp_file.name, output_file)
        logging.debug("Successfully wrote data to {}".format(output_file))
    except:
        logging.error("Failed to write data to {}".format(output_file))


def mkdir_p(path):
    """Creates a directory if it does not already exist. Mimics 'mkdir -p'

    Parameters
    ----------
    path : str
        Name of the directory to create.

    Raises
    ------
    OSError
        If the path cannot be created and it does not already exist.
    """
    try:
        os.makedirs(path)
    except OSError as exception:
        if exception.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


def open_file(filename, open_mode="r", encoding="utf-8"):
    """Returns the file handle to the given file (gzip or text).

    Parameters
    ----------
    filename : str
        Name of file to open, either gzip or text. '-' or None indicates STDIN/STDOUT.
    open_mode : str
        Mode to open the file, e.g. r, w, w+. Default is 'r'.
    encoding : str
        Encoding to use when opening the file. Default is 'utf-8'.

    Returns
    -------
    filehandle : filehandle
        An open filehandle to the given filename for reading.
    """
    if not filename or filename == "-":
        if open_mode == "r":
            return sys.stdin
        if open_mode == "w":
            return sys.stdout
        raise ValueError("Invalid open_mode {} when using STDIN/STDOUT".format(open_mode))
    if filename.endswith(".gz"): # Assume a gzip compressed file.
        if open_mode == "r": # gzip needs to be told text mode explicitly.
            open_mode = "rt"
        return gzip.open(filename, open_mode, encoding)
    return open(filename, open_mode)

def parse_filename(filename):
    """Returns the separate directory, basename, and file suffix for the given
    filename.

    Parameters
    ----------
    filename : str
        Name of a file.

    Returns
    -------
    directory : str
        Directory containing the file.
    basename : str
        Name of file, without any suffix.
    suffix : str
        Suffix of the file, normally the file type (e.g. txt, tgz, wav)
    """
    directory = ""
    suffix = ""
    basename = ""
    data = filename.split('/')
    data = [x for x in data if x]
    if len(data) > 1:
        directory = "/".join(data[:-1])
        directory = directory + "/"
        if filename.startswith("/"):
            directory = "/" + directory
    data = data[-1].split('.')
    basename = data[0]
    if len(data) > 1:
        suffix = ".".join(data[1:])
    return directory, basename, suffix
