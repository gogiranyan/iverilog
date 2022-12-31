'''Functions for running Icarus Verilog

'''

import subprocess
import os
import re

def assemble_iverilog_cmd(key: str, it_dir: str, args: list) -> list:
    res = ["iverilog", "-o", os.path.join("work", "a.out")]
    res += ["-D__ICARUS_UNSIZED__"]
    res += args
    src = os.path.join(it_dir, key + '.v')
    res += [src]
    return res


def assemble_vvp_cmd() -> list:
    res = ["vvp", os.path.join("work", "a.out")]
    return res


def get_ivl_version () -> list:
    '''Figure out the version of the installed iverilog compler.

    The return value is a list of 2 numbers, the major and minor version
    numbers, or None if the version string couldn't be found.'''

    # Get the output from the "iverilog -V" command for the version string.
    text = subprocess.check_output(["iverilog", "-V"])
    match = re.search(b'Icarus Verilog version ([0-9]+)\.([0-9]+)', text)
    if not match:
        return None

    return [int(match[1]), int(match[2])]

def build_runtime(it_key: str) -> None:
    '''Check and prepare the runtime environment for a test

    This is called in front of tests to make sure that the directory
    structure is correct, and common temp files that might linger from
    a previous run are removed.'''

    try:
        os.mkdir("log")
    except FileExistsError:
        pass

    try:
        os.remove(os.path.join("log", it_key + ".log"))
    except FileNotFoundError:
        pass

    try:
        os.mkdir("work")
    except FileExistsError:
        pass

    try:
        os.remove(os.path.join("work", "a.out"))
    except FileNotFoundError:
        pass


def log_results(fd, title, res) -> None:
    fd.write(f"====== {title} (stdout) ======\n".encode('ascii'))
    fd.write(res.stdout)
    fd.write(f"\n====== {title} (stderr) ======\n".encode("ascii"))
    fd.write(res.stderr)
    fd.write(f"\n====== Return code: {res.returncode} =====\n".encode("ascii"))


def run_CE(options : dict) -> list:
    ''' Run the compiler, and expect an error

    In this case, we assert that the command fails to run and reports
    an error. This is to check that invalid input generates errors.'''

    it_key = options['key']
    it_dir = options['directory']
    it_args = options['iverilog_args']

    build_runtime(it_key)

    with open(os.path.join("log", it_key + ".log"), 'wb') as log_fd:
        
        cmd = assemble_iverilog_cmd(it_key, it_dir, it_args)
        res = subprocess.run(cmd, capture_output=True)
        log_results(log_fd, "iverilog", res)

        if res.returncode == 0:
            return [1, "Failed - CE (no error reported)"]
        elif res.returncode >= 256:
            return [1, "Failed - CE (execution error)"]
        else:
            return [0, "Passed - CE"]


def do_run_normal(options : dict, expected_fail : bool) -> list:
    '''Run the iverilog and vvp commands.

    In this case, run the compiler to generate a vvp output file, and
    run the vvp command to actually execute the simulation. Collect
    the results and look for a "PASSED" string.'''

    it_key = options['key']
    it_dir = options['directory']
    it_iverilog_args = options['iverilog_args']
    it_gold = options['gold']
    it_diff = options['diff']

    build_runtime(it_key)

    with open(os.path.join("log", it_key + ".log"), 'wb') as log_fd:
        
        # Run the iverilog command
        ivl_cmd = assemble_iverilog_cmd(it_key, it_dir, it_iverilog_args)
        ivl_res = subprocess.run(ivl_cmd, capture_output=True)

        log_results(log_fd, "iverilog", ivl_res)
        if ivl_res.returncode != 0:
            return [1, "Failed - Compile failed"]

        # run the vvp command
        vvp_cmd = assemble_vvp_cmd()
        vvp_res = subprocess.run(vvp_cmd, capture_output=True)
        log_results(log_fd, "vvp", vvp_res);
        
        if vvp_res.returncode != 0:
            return [1, "Failed - Vvp execution failed"]

    it_stdout = vvp_res.stdout.decode('ascii')

    # If there is a gold file, the test result depends on the stdout
    # matching the gold file.
    if it_gold is not None:
        with open(os.path.join("gold", it_gold), 'r') as gold_fd:
            stdout_gold = gold_fd.read()

        if expected_fail:
            if it_stdout == stdout_gold:
                return [1, "Failed - Passed, but expected failure"]
            else:
                return [0, "Passed - Expected fail"]
        else:
            if it_stdout == stdout_gold:
                return [0, "Passed"]
            else:
                return [1, "Failed - Gold output doesn't match stdout."]

    # If there is a diff description, then compare name files instead of
    # the stdout and a gold file.
    if it_diff is not None:
        diff_name1 = it_diff[0]
        diff_name2 = it_diff[1]
        diff_skip = int(it_diff[2])

        with open(diff_name1) as fd:
            for idx in range(diff_skip):
                fd.readline()
            diff_data1 = fd.read()

        with open(diff_name2) as fd:
            for idx in range(diff_skip):
                fd.readline()
            diff_data2 = fd.read()

        if expected_fail:
            if diff_data1 == diff_data2:
                return [1, "Failed - Passed, but expected failure"]
            else:
                return [0, "Passed"]
        else:
            if diff_data1 == diff_data2:
                return [0, "Passed"]
            else:
                return [1, f"Failed - Files {diff_name1} and {diff_name2} differ."]

    # Otherwise, look for the PASSED output string in stdout.
    for line in it_stdout.splitlines():
        if line == "PASSED":
            if expected_fail:
                return [1, "Failed - Passed, but expected failure"]
            else:
                return [0, "Passed"]

    # If there is no PASSED output, and nothing else to check, then
    # assume a failure.
    if expected_fail:
        return [0, "Passed"]
    else:
        return [1, "Failed - No PASSED output, and no gold file"]


def run_normal(options : dict) -> list:
    return do_run_normal(options, False)

def run_EF(options : dict) -> list:
    return do_run_normal(options, True)
