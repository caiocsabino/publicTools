import re
import argparse
import subprocess
import os

bug_report_pattern = "SCM-"

def get_first_line(input_string):
    # Split the input string into lines
    lines = input_string.splitlines()

    # Check if there is at least one line
    if lines:
        # Get the first line
        first_line = lines[0]
    else:
        # If there are no lines, return an empty string or None as desired
        first_line = ""

    return first_line


def remove_first_line(input_string):
    # Split the input string into lines
    lines = input_string.splitlines()

    # Check if there are lines to remove
    if len(lines) > 1:
        # Join all lines except the first one
        result_string = "\n".join(lines[1:])
    else:
        # If there's only one line or no lines, return an empty string
        result_string = ""

    return result_string

def remove_empty_lines(input_string):
    # Split the input string into lines
    lines = input_string.splitlines()

    # Filter out empty lines using a list comprehension
    non_empty_lines = [line for line in lines if line.strip()]

    # Join the non-empty lines back together
    result_string = "\n".join(non_empty_lines)

    return result_string

def count_line_changes(input_string, addition):
    # Split the input string into lines
    lines = input_string.splitlines()

    # Initialize a counter for lines starting with a single "+"
    count = 0

    for line in lines:
        # Check if the line starts with a single "+"
        if addition == True:
            if line.startswith('+') and not line.startswith('++') and not line.startswith('+*'):
                count += 1
        else:
             if line.startswith('-') and not line.startswith('--') and not line.startswith('-*'):
                count += 1
        

    return count

# Regular expression pattern to match the SVN log line format
log_line_pattern = r'^r(\d+) \| (\w+) \| (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} [+\-]\d{4}) \(.*\) \| (\d+) line[s]?'
log_line_regex = re.compile(log_line_pattern)

# separates an input string in sectors delimited by a line separator
def get_sectors(input, separator):
    # Initialize an array to store the entries
    input_lines = input.splitlines()
    entries = []

    entry_lines = []  # Temporary list to store lines of each entry
    capture_entry = False  # Flag to indicate when to capture an entry

    for line in input_lines:
        line = line.rstrip()  # Remove trailing newline characters

        # Check if the line consists of dashes repeated 72 times
        if line == separator:
            if capture_entry:
                # Join the lines of the current entry and add it to the entries list
                entries.append("\n".join(entry_lines))
                entry_lines = []  # Clear the temporary list
            else:
                capture_entry = True  # Start capturing the next entry
        elif capture_entry:
            # Append the line to the temporary list for the current entry
            entry_lines.append(line)
        

    # Check if there's any remaining entry to capture
    if entry_lines:
        entries.append("\n".join(entry_lines))

    return entries


def parse_svn_log(log_file_path):

    # Initialize an array to store the entries
    entries = []

    # Read the text file
    with open(log_file_path, "r") as file:
        entries = get_sectors(file.read(), "------------------------------------------------------------------------")

    log_entries = []

    for entry in entries:
        commitLine = get_first_line(entry)
        comment = remove_empty_lines(entry)
        comment = remove_first_line(comment)

        match = log_line_regex.match(commitLine)
        if match:
            revision, author, date, line_count = match.groups()
            log_entries.append({
                'revision': int(revision),
                'author': author,
                'date': date,
                'line_count': int(line_count),
                'comment': comment
            })

    return log_entries

def parse_svn_diff(revision, repo_dir, commit_message):
    changes = {}
    current_directory = os.getcwd()
    os.chdir(repo_dir)
    command = "svn diff -c " + str(revision)

    diff_result = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT, universal_newlines=True)

    diff_sectors = get_sectors(diff_result, "===================================================================")

    os.chdir(current_directory)

    changes["files_added"] = 0
    changes["files_removed"] = 0
    changes["lines_added"] = 0
    changes["lines_removed"] = 0
    changes["bugs_mentioned"] = 0
    changes["files_added"] = 0
    changes["files_removed"] = 0

    added_file_pattern = r"^---.*\(nonexistent\)$"
    removed_file_pattern = r"^\+\+\+.*\(nonexistent\)$"

    for sector in diff_sectors:

        # Extract and print the matched lines
        matches = re.finditer(added_file_pattern, sector, re.MULTILINE)

        matched_lines_addition = [match.group(0) for match in matches]
        for line in matched_lines_addition:
            print("Added files " + line)

        changes["files_added"] = changes["files_added"] + len(matched_lines_addition)

        matches = re.finditer(removed_file_pattern, sector, re.MULTILINE)

        matched_lines_removal = [match.group(0) for match in matches]
        for line in matched_lines_removal:
            print("Removed files " + line)

        changes["files_removed"] = changes["files_removed"] + len(matched_lines_removal)
        
        changes["lines_added"] = changes["lines_added"] + count_line_changes(sector, True)

        if len(matched_lines_removal) == 0:
            changes["lines_removed"] = changes["lines_removed"] + count_line_changes(sector, False)

        changes["bugs_mentioned"] = changes["bugs_mentioned"] + sector.count(bug_report_pattern)
        
    # --- file (nonexistent) addition
    # +++ file (nonexistent) removal

    return changes

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


    collection = {}

    revisions = []

    cutoff = 0

    unsortedEntries = []

    for entry in log_entries:
        if not entry["author"] in collection:
            collection[entry["author"]] = []

        entryObj = {}
        entryObj["revision"] = entry["revision"]
        entryObj["date"] = entry["date"]
        entryObj["line_count"] = entry["line_count"]
        print("Parsing commit " + str(entry["revision"]))
        entryObj["changes"] = parse_svn_diff(int(entry["revision"]), args.repo_dir, entry["comment"])
        entryObj["author"] = entry["author"]

        revisions.append(int(entryObj["revision"]))

        collection[entry["author"]].append(entryObj)

        unsortedEntries.append(entryObj)

        cutoff = cutoff + 1

        if cutoff > 10:
            break

    for entry in unsortedEntries:
        print("ENTRY " + str(entry))


    authors = []
    sorted_revisions = sorted(revisions, reverse=True)

    for k, v in collection.items():
        authors.append(k)

if __name__ == '__main__':
    main()
