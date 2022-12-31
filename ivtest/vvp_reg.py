#! python
'''
Usage:
    vvp_reg
    vvp_reg <list-paths>...

<list-paths> is a list of files in the current working directory that
            each contain a list of tests. By convention, the file has the
            suffix ".list". The files will be processed in order, so tests
            can be overridden if listed twice. If no files are given, a
            default list is used.
'''

from docopt import docopt
import test_lists
import run_ivl


def process_test(item: list) -> str:
    '''Process a single test

    This takes in the list of tokens from the tests list file, and converts
    them (interprets them) to a collection of values.'''

    # This is the name of the test, and the name of the main sorce file
    it_key = item[0]
    # This is the name of the subdirectory that contains the test.
    it_directory = item[2]
    # The type is broken into a test type and a list of compiler flags,
    # like this:
    #    normal,arg1,arg2,...
    # Convert this into the type and an it_args list.
    it_type = item[1].split(',')
    it_args = it_type[1:len(it_type)]
    it_type = it_type[0]

    # The extra field (4th item in the list) is of one of these forms:
    #    <modulename>
    #    gold=<filename>
    #    unordered=<filename>
    #    diff=<<file1>:<file2>:<skip>
    it_modulename = None
    it_gold = None
    it_diff = None
    if len(item) >= 4:
        extra = item[3].split('=')
        if len(extra) == 1:
            it_modulename = extra[0]
        elif extra[0] == 'gold':
            it_gold = extra[1]
        elif extra[0] == 'diff':
            it_diff = extra[1].split(':')
        elif extra[0] == 'unordered':
            raise Exception(f"Sorry; unordered options not implemented.")

    # Wrap all of this into an options dictionary for ease of handling.
    it_options = {
        'key'           : it_key,
        'type'          : it_type,
        'iverilog_args' : it_args,
        'directory'     : it_directory,
        'modulename'    : it_modulename,
        'gold'          : it_gold,
        'diff'          : it_diff
    }

    if it_type == "NI":
        res = f"{it_key}: Not Implemented."

    elif it_type == "normal":
        res = run_ivl.run_normal(it_options)

    elif it_type == "CE":
        res = run_ivl.run_CE(it_options)

    elif it_type == "EF":
        res = run_ivl.run_EF(it_options)

    else:
        res = f"{it_key}: I don't understand the test type ({it_type})."
        raise Exception(res)

    return res


def report_results(results: list) -> None:
    width = 0
    for item in results:
        if len(item[0]) > width:
            width = len(item[0])

    for item in results:
        key = item[0]
        value = item[1]
        print(f"{key:>{width}}: {value}")


if __name__ == "__main__":
    args = docopt(__doc__)

    # This returns [13, 0] or similar
    ivl_version = run_ivl.get_ivl_version()
    ivl_version_major = ivl_version[0]

    # Select the lists to use.
    if "<list-paths>" in args:
        list_paths = args["<list-paths>"]
    else:
        list_paths = list()
        list_paths += ["regress-ivl1.list"]
        list_paths += ["regress-vlg.list"]
        list_paths += ["regress-vams.list"]
        list_paths += ["regress-sv.list"]
        list_paths += ["regress-vhdl.list"]
        list_paths += [f"regress-v{ivl_version_major}.list"]
        
    print(f"Use lists: {list_paths}")

    # Read the list files, to get the tests.
    tests_list = test_lists.read_lists(list_paths)

    results = []
    error_count = 0
    for cur in tests_list:
        result = process_test(cur)
        error_count += result[0]
        results.append([cur[0], result[1]])


    report_results(results)
    exit(error_count)
    
