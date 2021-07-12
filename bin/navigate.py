#! /usr/bin/env python3
"""Efficient directory navigation.
"""

import argparse
import collections
import json
import logging
import operator
import os
import sys
import time
import lumann.utils.file

MAX_CHOICES = 10
MAX_AGE = 30 * 24 * 3600
DISCOUNT_FACTOR = 0.99

def color_mark(mark):
    """Add color to the mark output."""
    return "\033[38;5;36m{}\033[0;0m".format(mark)

def default_json():
    """Create a default JSON file to store necessary information."""
    data = dict()
    data["mark"] = dict()
    data["count"] = collections.defaultdict(float)
    data["ignore"] = dict()
    data["time"] = dict()
    return data

def discount_counts(data):
    """Multiply all counts by the DISCOUNT_FACTOR."""
    for key in data["count"]:
        data["count"][key] *= DISCOUNT_FACTOR

def handle_selection(selection, options, data):
    """Process the input, finding the right directory or printing results."""
    if selection in options:
        logging.debug("Selection {} maps to {}".format(selection, options[selection]))
        return options[selection]
    if selection == 'i':
        logging.debug("Printing ignored directories")
        print("Ignored directories:")
        for key in data['ignore']:
            print("  {}".format(key))
    elif selection == 'm':
        logging.debug("Printing marked directories")
        print("Marked directories: ")
        for key in sorted(data['mark']):
            print("  {} {}".format(color_mark(key), data["mark"][key]))
    else:
        logging.error("Invalid option: {}".format(selection))
    return None

def is_directory_match(targets, directory):
    """For each string in target, see if it is a substring of directory."""
    for target in targets:
        if target not in directory:
            return False
    return True

def load_data(filename):
    """Load the JSON storing our data."""
    data = dict()
    try:
        with open(filename) as fin:
            data = json.load(fin)
            logging.debug("Loaded file {}".format(filename))
            count = collections.defaultdict(float)
            for key in data["count"]:
                count[key] = data["count"][key]
            data["count"] = count
    except FileNotFoundError:
        logging.debug("Creating new json file")
        data = default_json()
    return data

def mark_prefix(mark, marks):
    """Find all marks where mark is a prefix."""
    ret = list()
    for key in marks:
        if key.startswith(mark):
            ret.append("  {} {}".format(color_mark(key), marks[key]))
    return "\n".join(ret)

def print_menu(data):
    """
    Print the menu for user selection. Note that we have to print to stderr because we assume
    a bash script is capturing stdout output.
    """
    ret = dict()
    print("Most Frequent Directories:", file=sys.stderr)
    idx = 0
    for entry in sorted(data["count"].items(), key=operator.itemgetter(1), reverse=True)[:MAX_CHOICES]:
        print("  ({}) {}".format(idx, entry[0]), file=sys.stderr)
        ret[str(idx)] = entry[0]
        idx += 1
    print("Most Recent Directories:", file=sys.stderr)
    for entry in sorted(data["time"].items(), key=operator.itemgetter(1), reverse=True)[:MAX_CHOICES]:
        print("  ({}) {}".format(idx, entry[0]), file=sys.stderr)
        ret[str(idx)] = entry[0]
        idx += 1
    
    print("Other options:", file=sys.stderr)
    print("  (i) List ignored directories", file=sys.stderr)
    print("  (m) List all marks", file=sys.stderr)
    return ret

def process_directory(directory, data):
    """Either return a directory or search for a matching directory."""
    sort_type = ""
    logging.debug("Directory is currently set to {}".format(directory))
    if len(directory) == 1:
        return directory[0]
    if directory[0] == "f":
        sort_type = "count"
    elif directory[0] == "r":
        sort_type = "time"
    else:
        logging.error("'{}' is an invalid search type. Use 'r' for recent and 'f' for frequent.".format(directory[0]))
        sys.exit(1)
    for entry in sorted(data[sort_type].items(), key=operator.itemgetter(1), reverse=True):
        if is_directory_match(directory[1:], entry[0]):
            return entry[0]
    print("Could not find a directory that matches '{}'".format(" ".join(directory[1:])))
    sys.exit(1)

def process_ignore(args, data, current_directory):
    """Handle ignoring of a directory."""
    if args.delete:
        if current_directory in data["ignore"]:
            data["ignore"].pop(current_directory)
            logging.debug("Removed directory {} from ignore.".format(current_directory))
        else:
            logging.info("Directory '{}' was not being ignored.".format(current_directory))
    else:
        data["ignore"][current_directory] = 1
        data["time"].pop(current_directory, None)
        data["count"].pop(current_directory, None)
    return None

def process_mark(args, data, current_directory):
    """Handle marking of a directory."""
    if args.delete:
        if args.mark in data["mark"]:
            dir = data["mark"].pop(args.mark)
            logging.debug("Removed mark {} for directory {}".format(args.mark, dir))
        else:
            logging.info("Mark {} does not exist.".format(args.mark))
    else:
        data["mark"][args.mark] = current_directory
        logging.debug("Added mark {} for {}".format(args.mark, current_directory))
    return None

def process_jump(args, data, current_directory):
    """Handle jumping to a directory."""
    if args.jump in data["mark"]:
        logging.debug("Mark {} maps to {}.".format(args.jump, data["mark"][args.jump]))
        return data["mark"][args.jump]
    else:
        logging.error("Mark {} does not exist.". format(args.jump))
        print("Mark {} does not exist.". format(args.jump))
        possible_marks = mark_prefix(args.jump, data["mark"])
        if possible_marks:
            print("Did you mean one of these marks?")
            print(possible_marks)
            print()
    return None

def remove_old_directories(data):
    """Remove directories that have not been accessed within the specified time window."""
    now = time.time()
    deletion_set = set()
    for key, val in data["time"].items():
        if now - val > MAX_AGE:
            deletion_set.add(key)
    for key in deletion_set:
        logging.debug("Deleting directory {}".format(key))
        del data["time"][key]
        del data["count"][key]

def write_data(data, filename):
    """Write the JSON file back out."""
    json_data = json.dumps(data)
    lumann.utils.file.atomic_write(json_data, filename)

def main():
    """Efficient directory navigation."""
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('directory', default=None, nargs='*',
                        help=('Change the current working directory. If you give multiple options, '
                              'then this becomes a search. With a search, the first option '
                              'determines the order to search. f means search the most frequent '
                              'directories first, and r means search the most recent. The '
                              'remaining arguments are the search terms and they must all be '
                              'matched.'))
    parser.add_argument('-a', '--add', default=None,
                        help='Add the given directory to the database.')
    parser.add_argument('-c', '--current_directory', default=None,
                        help='Specify the current directory. Useful if you do not want Python to '
                             'expand symlinks.')
    parser.add_argument('-m', '--mark', default=None,
                        help='Mark the current directory with the given name.')
    parser.add_argument('-d', '--delete', action='store_true',
                        help='Remove information from the database.')
    parser.add_argument('-i', '--ignore', action='store_true',
                        help='Ignore the current directory for all purposes.')
    parser.add_argument('-j', '--jump', default=None,
                        help='Jump to the given mark.')

    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG,format='%(asctime)s - %(levelname)s - %(message)s')

    if not "LUMANN_DATA" in os.environ:
        print("Need to set LUMANN_DATA environment variable.")
        sys.exit(1)

    filename = os.environ["LUMANN_DATA"] + "/navigate.json"
    data = load_data(filename)
    current_directory = os.getcwd()
    if args.current_directory:
        current_directory = args.current_directory
    jump_directory = None

    if args.mark:
        process_mark(args, data, current_directory)
    elif args.ignore:
        process_ignore(args, data, current_directory)
    elif args.jump:
        jump_directory = process_jump(args, data, current_directory)
    elif args.add and args.add not in data["ignore"]:
        data["count"][args.add] += 1
        logging.debug("Increasing count for '{}' to {}".format(args.add, data["count"][args.add]))
        data["time"][args.add] = time.time()
        discount_counts(data)
        remove_old_directories(data)
    elif not args.directory:
        options = print_menu(data)
        selection = input()
        selection = handle_selection(selection, options, data)
        if selection:
            jump_directory = selection
    else:
        jump_directory = process_directory(args.directory, data)

    write_data(data, filename)

    if jump_directory:
        print(jump_directory)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
