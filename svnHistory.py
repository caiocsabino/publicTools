import re
import argparse
import subprocess
import os
import datetime

bug_report_pattern = "SCM-"

authors_to_exclude = ["eagle", "neojenkins"]

debug_authors_list = []

debug_target_revision_number = None

debug_target_month = None

debug_logs_on = debug_target_month != None or len(debug_authors_list) > 0 or debug_target_revision_number != None

TAG_REVISION = "revision"
TAG_DATE = "date"
TAG_DATE_YEAR_MONTH = "date_year_month"
TAG_LINE_COUNT = "line_count"
TAG_AUTHOR = "author"
TAG_COMMENT = "comment"
TAG_CHANGES = "changes"
TAG_COMMITS = "commits"

TAG_FILES_ADDED = "files_added"
TAG_FILES_REMOVED = "files_removed"
TAG_LINES_ADDED = "lines_added"
TAG_LINES_REMOVED = "lines_removed"
TAG_BUGS_MENTIONED = "bugs_mentioned"
TAG_COPIED_LARGE_ADDITIONS = "copied_large_additions"
TAG_BINARIES_CHANGED = "binaries_changed"
TAG_GENERATED_FILE_CHANGES = "generated_file_changes"
TAG_FRAMEWORK_CHANGES = "framework_changes"

binary_files_to_ignore_in_line_count = [".stamp", ".dbg", ".so", ".map", ".png", ".jpg", ".geo", ".skin", ".mtl", ".sha1"]
code_files = [".h", ".cpp", ".mkf", ".mkb", ".xml", ".py", ".bat", ".sh", ".icf", ".json", ".kts", ".java", ".plist", ".md", ".c", ".cmake"]
generated_files_directories = ["data/ui/MenuXML", "src/protobuf", "src/simcity/uiassets"]

framework_detection_patterns = [r"/[\w\d.]+\.framework/", r"/[\w\d.]+\.bundle/"]

# if there's a svn diff which detects more lnes were added than this threshold, it shouldn't be considered authored, probably was copied
large_added_files_threshold = 5000

def get_month_index(date_str):

    zero_year = 2010

    year = int(date_str[:4])
    month = int(date_str[5:7])

    return (year - zero_year) * 12 + month 

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

def get_last_line(multiline_string):
    # Split the multiline string into lines
    lines = multiline_string.splitlines()

    # Check if there are lines
    if lines:
        return lines[-1]  # Return the last line
    else:
        return None  # Return None if the multiline string is empty

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

#SVN HISTORY
# ------------------------------------------------------------------------
# commit data

# commit comment


#SVN DIFF
# Index: data_advisorTest/data/ui3d/models/advisorTrains_top.geo
# ===================================================================

# separates an input string in sectors delimited by a line separator
def get_sectors(input, separator, include_headers):
    # Initialize an array to store the entries
    input_lines = input.splitlines()
    entries = []

    entry_lines = []  # Temporary list to store lines of each entry
    headers = []
    capture_entry = False  # Flag to indicate when to capture an entry

    previous_line = ""
    for line in input_lines:
        line = line.rstrip()  # Remove trailing newline characters

        # Check if the line consists of the separator
        if line == separator:
            if capture_entry:
                # Join the lines of the current entry and add it to the entries list
                entries.append("\n".join(entry_lines))
                entry_lines = []  # Clear the temporary list

            else:
                capture_entry = True  # Start capturing the next entry

            if include_headers:
                entry_lines.append(previous_line)
                entry_lines.append(separator)
        elif capture_entry:
            # Append the line to the temporary list for the current entry
            entry_lines.append(line)

        previous_line = line
        

    # Check if there's any remaining entry to capture
    if entry_lines:
        entries.append("\n".join(entry_lines))

    return entries


def parse_svn_log(log_file_path):

    # Initialize an array to store the entries
    entries = []

    # Read the text file
    with open(log_file_path, "r") as file:
        entries = get_sectors(file.read(), "------------------------------------------------------------------------", False)

    log_entries = []

    for entry in entries:

        commitLine = get_first_line(entry)
        comment = remove_empty_lines(entry)
        comment = remove_first_line(comment)

        match = log_line_regex.match(commitLine)
        if match:
            revision, author, date, line_count = match.groups()
            log_entries.append({
                TAG_REVISION: int(revision),
                TAG_AUTHOR: author,
                TAG_DATE: date,
                TAG_LINE_COUNT: int(line_count),
                TAG_COMMENT: comment
            })

    return log_entries

def header_file_path_in_list(header, input_list):
    if header.startswith("Index: "):
        # Remove the "Index: " tag to get the file path
        header_file_path = header[len("Index: "):]

        for directory in input_list:
            if directory in header_file_path:
                return True
    return False

def header_file_path_extension_in_list(header, input_list):
    if header.startswith("Index: "):
        # Remove the "Index: " tag to get the file path
        header_file_path = header[len("Index: "):]

        for extension in input_list:
            if header_file_path.endswith(extension):
                return True
    return False

def debug_log(message, commit_data):
    if debug_logs_on:
        print(str(commit_data[TAG_REVISION]) + " (" + commit_data[TAG_AUTHOR] + "): " + message)

def parse_svn_diff(revision, repo_dir, commit_data):
    changes = {}
    changes[TAG_FILES_ADDED] = 0
    changes[TAG_FILES_REMOVED] = 0
    changes[TAG_LINES_ADDED] = 0
    changes[TAG_LINES_REMOVED] = 0
    changes[TAG_BUGS_MENTIONED] = 0
    changes[TAG_BINARIES_CHANGED] = 0
    changes[TAG_COPIED_LARGE_ADDITIONS] = 0
    changes[TAG_GENERATED_FILE_CHANGES] = 0
    changes[TAG_FRAMEWORK_CHANGES] = 0

    current_directory = os.getcwd()
    os.chdir(repo_dir)
    command = "svn diff -c " + str(revision)

    diff_result = None

    try:
        diff_result = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT, universal_newlines=True)
    except subprocess.CalledProcessError as e:
        # Handle the exception (e.g., print an error message)
        print("SVN DIFF FAILED:", e)
        diff_result = None
    except Exception as e:
        # Handle other exceptions if necessary
        print("An error occurred:", e)
        diff_result = None

    os.chdir(current_directory)

    if diff_result == None:
        return changes

    diff_sectors = get_sectors(diff_result, "===================================================================", True)

    binary_files_listed = {}
    generated_files_listed = {}

    frameworks_listed = {}

    # --- file (nonexistent) addition
    # +++ file (nonexistent) removal

    added_file_pattern = r"^---.*\(nonexistent\)$"
    removed_file_pattern = r"^\+\+\+.*\(nonexistent\)$"

    for sector in diff_sectors:

        sector_header = get_first_line(sector)

        is_source = header_file_path_extension_in_list(sector_header, code_files)
        is_binary = header_file_path_extension_in_list(sector_header, binary_files_to_ignore_in_line_count)
        is_generated = header_file_path_in_list(sector_header, generated_files_directories)

        is_framework = False
        framework_name = ""

        for pattern in framework_detection_patterns:
            match = re.search(pattern, sector_header)
            if match:
                is_framework = True
                framework_name = match.group()
                break

        # HANDLES FILE ADDITIONS AND REMOVALS (FRAMEWORKS CHANGE FILE STRUCTURE OFTEN, SO WE DON't CONSIDER THOSE AS AUTHORED)

        if not is_framework:
            matches = re.finditer(added_file_pattern, sector, re.MULTILINE)

            matched_lines_addition = [match.group(0) for match in matches]
            for line in matched_lines_addition:
                debug_log("Added files " + line + " " + sector_header, commit_data)

            changes[TAG_FILES_ADDED] = changes[TAG_FILES_ADDED] + len(matched_lines_addition)

            matches = re.finditer(removed_file_pattern, sector, re.MULTILINE)

            matched_lines_removal = [match.group(0) for match in matches]
            
            for line in matched_lines_removal:
                debug_log("Removed files " + line + " " + sector_header, commit_data)

            changes[TAG_FILES_REMOVED] = changes[TAG_FILES_REMOVED] + len(matched_lines_removal)
        
        #HANDLES SOURCE FILE MODIFICATIONS

        if is_source and not is_generated and not is_binary and not is_framework:
            # print("SOURCE SPOTTED " + sector_header)
            # IF TOO MANY LINES WERE ADDED, WE COUNT THEM AS COPIED FROM SOMEWHERE ELSE
            lines_added_count = count_line_changes(sector, True)
            if (lines_added_count >= large_added_files_threshold):
                changes[TAG_COPIED_LARGE_ADDITIONS] = changes[TAG_COPIED_LARGE_ADDITIONS] + 1
                debug_log("Large addition: " + sector_header, commit_data)
            else:
                changes[TAG_LINES_ADDED] = changes[TAG_LINES_ADDED] + lines_added_count
                debug_log("Source lines added: " + sector_header, commit_data)

            # FILE WAS NOT REMOVED, COUNT IT AS MANUALLY REMOVED LINE
            if len(matched_lines_removal) == 0:
                # print("LINES_REMOVED " + str(count_line_changes(sector, False)))
                changes[TAG_LINES_REMOVED] = changes[TAG_LINES_REMOVED] + count_line_changes(sector, False)
                debug_log("Source lines removed: " + sector_header, commit_data)

        #BINARIES, GENERATED AND FRAMEWORKS

        if is_framework:
            debug_log("Framework changes detected: " + sector_header + " (" + framework_name + ")", commit_data)
            frameworks_listed[framework_name] = True
        else:
            if is_binary:
                binary_files_listed[sector_header] = True
                debug_log("Binary detected: " + sector_header, commit_data)

            if is_generated:
                debug_log("Generated files detected: " + sector_header, commit_data)
                generated_files_listed[sector_header] = True

        changes[TAG_BUGS_MENTIONED] = changes[TAG_BUGS_MENTIONED] + sector.count(bug_report_pattern)

    changes[TAG_BINARIES_CHANGED] = len(binary_files_listed)
    changes[TAG_GENERATED_FILE_CHANGES] = len(generated_files_listed)
    changes[TAG_FRAMEWORK_CHANGES] = len(frameworks_listed)

    return changes

def get_simplified_date(long_date):
    date_pattern = r"(\d{4}-\d{2})"

    match = re.search(date_pattern, long_date)

    if match:
        date_str = match.group(1)
        return date_str
    else:
        return long_date

def dump_table_to_disk(table_name, table):
    cummulative_properties = [TAG_LINES_ADDED, TAG_LINES_REMOVED, TAG_BUGS_MENTIONED, TAG_FILES_ADDED, TAG_FILES_REMOVED, TAG_BINARIES_CHANGED, TAG_COPIED_LARGE_ADDITIONS, TAG_GENERATED_FILE_CHANGES, TAG_FRAMEWORK_CHANGES]

    author_entries = {}

    for entry in table:

        author_name = entry[TAG_AUTHOR]

        if author_name not in author_entries:
            author_entries[author_name] = {}
            author_entries[author_name][TAG_COMMITS] = 0

            for property_name in cummulative_properties:
                author_entries[author_name][property_name] = 0

        author_entries[author_name][TAG_COMMITS] += 1

        for property_name in cummulative_properties:
            author_entries[author_name][property_name] += entry[TAG_CHANGES][property_name]

    # writing to CSV
    csv_str = "Author;Commits;Lines added;Lines removed;Bugs mentioned;Files added;Files removed;Binaries changed;Copied (large additions);Generated files changed;Frameworks changed;\n"

    for author_entry_name, author_entry in author_entries.items():
        csv_str += author_entry_name + ";" + str(author_entry[TAG_COMMITS]) + ";"
        for property_name in cummulative_properties:
            csv_str += str(author_entry[property_name]) + ";"
        csv_str += "\n"

    with open(table_name + ".csv", "w", encoding="utf-8") as file:
        # Write the content to the file
        file.write(csv_str)

def main():
    # Create a command-line argument parser
    parser = argparse.ArgumentParser(description='Parse SVN log file')
    parser.add_argument('input_file', help='Path to the SVN log file')
    parser.add_argument('repo_dir', help='Path to the SVN repository directory')
    parser.add_argument('months', help='How many previous months to analyze')

    # Parse command-line arguments
    args = parser.parse_args()

    # Parse the SVN log file and get log entries
    log_entries = parse_svn_log(args.input_file)

    current_date = datetime.datetime.now()

    formatted_date = current_date.strftime("%Y-%m-%d")

    current_month_index = get_month_index(formatted_date)

    debug_month_year_index = None

    if debug_target_month != None:
        debug_month_year_index = get_month_index(debug_target_month)

    months = int(args.months)

    lowest_month_index = int(current_month_index) - months

    if months < 0:
        lowest_month_index = 0

    last_table_name = None
    csv_tables = {}

    for entry in log_entries:

        if entry[TAG_AUTHOR] in authors_to_exclude or (len(debug_authors_list) > 0 and entry[TAG_AUTHOR] not in debug_authors_list) or (debug_target_revision_number != None and int(entry[TAG_REVISION]) != debug_target_revision_number):
            continue

        year_month = get_simplified_date(entry["date"])
        year_month_index = get_month_index(year_month)

        #debugging for target specific month for inspection
        if debug_month_year_index != None and debug_month_year_index != year_month_index:
            continue
        else:
            # has reached month limit      
            if year_month_index < lowest_month_index:
                print("BREAK " + str(year_month_index) + " "  + str(lowest_month_index))
                break

        if last_table_name != None and last_table_name != year_month:
            print("DUMPING " + last_table_name)
            dump_table_to_disk(last_table_name, csv_tables[last_table_name])

        last_table_name = year_month

        if year_month not in csv_tables:
            csv_tables[year_month] = []

        # print("DATE " + year_month)
        entryObj = {}
        entryObj[TAG_REVISION] = entry[TAG_REVISION]
        entryObj[TAG_DATE] = entry[TAG_DATE]
        entryObj[TAG_DATE_YEAR_MONTH] = get_simplified_date(entry[TAG_DATE])
        entryObj[TAG_LINE_COUNT] = entry[TAG_LINE_COUNT]
        print("Parsing commit " + str(entry[TAG_REVISION]))
        entryObj[TAG_CHANGES] = parse_svn_diff(int(entry[TAG_REVISION]), args.repo_dir, entry)
        entryObj[TAG_AUTHOR] = entry[TAG_AUTHOR]

        csv_tables[year_month].append(entryObj)

    if last_table_name != None and last_table_name != year_month:
        dump_table_to_disk(last_table_name, csv_tables[last_table_name])

if __name__ == '__main__':
    main()
