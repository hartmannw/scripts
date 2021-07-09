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
    return "\033[38;5;36m{}\033[0;0m".format(mark)

def default_json():
    data = dict()
    data["mark"] = dict()
    data["count"] = collections.defaultdict(float)
    data["ignore"] = dict()
    data["time"] = dict()
    return data

def discount_counts(data):
    for key in data["count"]:
        data["count"][key] *= DISCOUNT_FACTOR

def handle_selection(selection, options, data):
    if selection in options:
        logging.debug("Selection {} maps to {}".format(selection, options[selection]))
        return [options[selection]]
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
    for target in targets:
        if target not in directory:
            return False
    return True

def load_data(filename):
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
    ret = list()
    for key in marks:
        if key.startswith(mark):
            ret.append("  {} {}".format(color_mark(key), marks[key]))
    return "\n".join(ret)

def print_menu(data):
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

def remove_old_directories(data):
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
    json_data = json.dumps(data)
    lumann.utils.file.atomic_write(json_data, filename)
    #with open(filename, "w") as fout:
    #    json.dump(data, fout)

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
    make_jump = False

    if args.mark:
        if args.delete:
            if args.mark in data["mark"]:
                dir = data["mark"].pop(args.mark)
                logging.debug("Removed mark {} for directory {}".format(args.mark, dir))
            else:
                logging.info("Mark {} does not exist.".format(args.mark))
        else:
            data["mark"][args.mark] = current_directory
            logging.debug("Added mark {} for {}".format(args.mark, current_directory))
    elif args.ignore:
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
    elif args.jump:
        if args.jump in data["mark"]:
            args.directory = [data["mark"][args.jump]] 
        else:
            logging.error("Mark {} does not exist.". format(args.jump))
            print("Mark {} does not exist.". format(args.jump))
            possible_marks = mark_prefix(args.jump, data["mark"])
            if possible_marks:
                print("Did you mean one of these marks?")
                print(possible_marks)
                print()
    elif not args.directory:
        options = print_menu(data)
        selection = input()
        selection = handle_selection(selection, options, data)
        if selection:
            args.directory = selection
    if args.directory:
        args.directory = process_directory(args.directory, data)
        make_jump = True # Even if we can't get there with Python, let bash handle the error.
        valid = False
        try:
            os.chdir(args.directory)
            logging.debug("We can move to {}".format(args.directory))
            current_directory = os.getcwd()
            valid = True
        except FileNotFoundError:
            logging.debug("{} does not appear to be a valid directory".format(args.directory))
        if valid:
            logging.debug("{} maps to {}".format(args.directory, current_directory))
            if current_directory not in data["ignore"]:
                data["count"][current_directory] += 1
                logging.debug("Increasing count for '{}' to {}".format(current_directory, data["count"][current_directory]))
                data["time"][current_directory] = time.time()
                discount_counts(data)
                remove_old_directories(data)

    write_data(data, filename)

    if make_jump:
        print(args.directory)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
