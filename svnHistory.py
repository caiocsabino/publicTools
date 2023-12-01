import re
import argparse
import subprocess
import os

# Regular expression pattern to match the SVN log line format
log_line_pattern = r'^r(\d+) \| (\w+) \| (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} [+\-]\d{4}) \(.*\) \| (\d+) line[s]?'
log_line_regex = re.compile(log_line_pattern)

def parse_svn_log(log_file_path):
    # List to store parsed log entries
    log_entries = []

    # Read and parse the log file
    with open(log_file_path, 'r') as file:
        for line in file:
            match = log_line_regex.match(line)
            if match:
                revision, author, date, line_count = match.groups()
                log_entries.append({
                    'revision': int(revision),
                    'author': author,
                    'date': date,
                    'line_count': int(line_count)
                })

    return log_entries

def parse_svn_diff(revision, repo_dir):
    current_directory = os.getcwd()
    os.chdir(repo_dir)
    command = "svn diff -c " + str(revision)

    result = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT, universal_newlines=True)

    os.chdir(current_directory)

    print("result " + result )

def main():
    # Create a command-line argument parser
    parser = argparse.ArgumentParser(description='Parse SVN log file')
    parser.add_argument('input_file', help='Path to the SVN log file')
    parser.add_argument('repo_dir', help='Path to the SVN repository directorye')

    # Parse command-line arguments
    args = parser.parse_args()

    # Parse the SVN log file and get log entries
    log_entries = parse_svn_log(args.input_file)

    # Print the parsed log entries

    print("HERE " + str(len(log_entries)))

    collection = {}

    revisions = []

    for entry in log_entries:
        if not entry["author"] in collection:
            collection[entry["author"]] = []

        entryObj = {}
        entryObj["revision"] = entry["revision"]
        entryObj["date"] = entry["date"]
        entryObj["line_count"] = entry["line_count"]

        revisions.append(int(entryObj["revision"]))

        collection[entry["author"]].append(entryObj)

    authors = []
    sorted_revisions = sorted(revisions, reverse=True)

    for k, v in collection.items():
        authors.append(k)

    parse_svn_diff(sorted_revisions[0], args.repo_dir)

    # print("revisiosn " + str(sorted_revisions[:10]))
    # print("Authors: " + str(authors))
    # print("CAIO " + str(len(collection["mnurmikari"])))


if __name__ == '__main__':
    main()
