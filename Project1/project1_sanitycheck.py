# project1_sanitycheck.py
#
# ICS 33 Fall 2023
# Project 1: Calling All Stations
#
# This is a sanity checker for your Project 1 solution, which checks whether
# your solution meets some basic requirements with respect to reading input
# and formatting its output, as well as verifying that at least one example
# can be run all the way to completion.  It creates an input file containing
# one legal input, runs your program and passes it the path of that input
# file, then assesses whether the output is exactly correct.
#
# In order for the sanity check to run successfully, you'll need to meet
# these requirements:
#
# * You're running the correct version of Python (3.11)
# * This module is in the project directory alongside "project1.py" and
#   whatever additional modules comprise your solution.
# * It's possible to run the program by executing that "project1.py" module.
# * Your program generates precisely correct output for one scenario.
#
# If your program is unable to pass this sanity checker, it will certainly be
# unable to pass all of our automated tests (and it may well fail all of them).
# On the other hand, there are other tests you'll want to run besides the one
# scenario here, because we'll be testing more than just one when we grade
# your work.
#
# YOU DO NOT NEED TO READ OR UNDERSTAND THIS CODE, though you can certainly
# feel free to take a look at it.

from collections.abc import Sequence
import contextlib
import locale
from pathlib import Path
import platform
import queue
import subprocess
import sys
import tempfile
import threading
import time
import traceback



_REQUIRED_PYTHON_VERSION = ('3', '11')



class TextProcessReadTimeout(Exception):
    pass



class TextProcess:
    _READ_INTERVAL_IN_SECONDS = 0.025


    def __init__(self, args: [str], working_directory: str):
        self._process = subprocess.Popen(
            args, cwd = working_directory, bufsize = 0,
            stdin = subprocess.PIPE, stdout = subprocess.PIPE,
            stderr = subprocess.STDOUT)

        self._stdout_read_trigger = queue.Queue()
        self._stdout_buffer = queue.Queue()

        self._stdout_thread = threading.Thread(
            target = self._stdout_read_loop, daemon = True)

        self._stdout_thread.start()


    def __enter__(self):
        return self


    def __exit__(self, tr, exc, val):
        self.close()


    def close(self):
        self._stdout_read_trigger.put('stop')
        self._process.terminate()
        self._process.wait()
        self._process.stdout.close()
        self._process.stdin.close()


    def write_line(self, line: str) -> None:
        try:
            self._process.stdin.write((line + '\n').encode(locale.getpreferredencoding(False)))
            self._process.stdin.flush()
        except OSError:
            pass


    def read_line(self, timeout: float = None) -> tuple[str, bool] or None:
        self._stdout_read_trigger.put('read')
        
        sleep_time = 0
        
        while timeout is None or sleep_time < timeout:
            try:
                next_result = self._stdout_buffer.get_nowait()

                if next_result is None:
                    return None
                elif isinstance(next_result, Exception):
                    raise next_result
                else:
                    line = next_result.decode(locale.getpreferredencoding(False))
                    had_newline = False

                    if line.endswith('\r\n'):
                        line = line[:-2]
                        had_newline = True
                    elif line.endswith('\n'):
                        line = line[:-1]
                        had_newline = True

                    return line, had_newline
            except queue.Empty:
                time.sleep(TextProcess._READ_INTERVAL_IN_SECONDS)
                sleep_time += TextProcess._READ_INTERVAL_IN_SECONDS

        raise TextProcessReadTimeout()


    def _stdout_read_loop(self):
        try:
            while self._process.returncode is None:
                if self._stdout_read_trigger.get() == 'read':
                    line = self._process.stdout.readline()

                    if line == b'':
                        self._stdout_buffer.put(None)
                    else:
                        self._stdout_buffer.put(line)
                else:
                    break
        except Exception as e:
            self._stdout_buffer.put(e)



class TestFailure(Exception):
    pass



class TestInputLine:
    def __init__(self, text: str):
        self._text = text

    
    def execute(self, process: TextProcess) -> None:
        try:
            process.write_line(self._text)
        except Exception:
            print_labeled_output(
                'EXCEPTION',
                *[tb_line.rstrip() for tb_line in traceback.format_exc().split('\n')])

            raise TestFailure()

        print_labeled_output('INPUT', self._text)



class TestOutputLines:
    def __init__(self, *text: str, timeout: float):
        self._text = text
        self._timeout = timeout


    def execute(self, process: TextProcess) -> None:
        try:
            lines, missing_newline, timed_out = self._read_lines(process, len(self._text))
        except Exception:
            print_labeled_output(
                'EXCEPTION',
                [tb_line.rstrip() for tb_line in traceback.format_exc().split('\n')])

            raise TestFailure()

        for index, output in enumerate(lines):
            output_label = 'OUTPUT' if index == 0 else ''
            print_labeled_output(output_label, output)

        incorrect = False

        if len(lines) != len(self._text):
            incorrect = True
        else:
            for output, expected in zip(sorted(lines), sorted(self._text)):
                if output != expected:
                    incorrect = True

        if incorrect:
            for index, expected in enumerate(self._text):
                expected_label = 'EXPECTED' if index == 0 else ''
                print_labeled_output(expected_label, expected)

            print_labeled_output(
                'ERROR',
                'The most recent lines of output did not match what was expected.',
                '(If you don\'t see a difference, perhaps your program printed',
                'extra whitespace on the end of one of these lines.)')

            raise TestFailure()
        elif missing_newline:
            print_labeled_output(
                'ERROR',
                'The last line of output was required to have a newline',
                'on the end of it, but it did not.')
        elif timed_out:
            print_labeled_output(
                'ERROR',
                'The most recent lines of output were expected to be printed, but',
                'the program did not generate any additional output after waiting',
                f'for {self._timeout} seconds.')


    def _read_lines(self, process: TextProcess, line_count: int) -> tuple[list[str], bool, bool]:
        lines = []
        missing_newline = True
        timed_out = False

        for _ in range(line_count):
            try:
                output_line = process.read_line(self._timeout)
            except TextProcessReadTimeout:
                output_line = None
                timed_out = True

            if output_line is not None:
                output_text, had_newline = output_line
                missing_newline = not had_newline
                lines.append(output_text)

        return lines, missing_newline, timed_out




class TestEndOfOutput:
    def __init__(self, timeout: float):
        self._timeout = timeout


    def execute(self, process: TextProcess) -> None:
        output_line = process.read_line(self._timeout)

        if output_line is not None:
            print_labeled_output('OUTPUT', output_line)

            print_labeled_output(
                'ERROR',
                'Extra output was printed after the program should not have generated',
                'any additional output')

            raise TestFailure()



def run_test() -> None:
    input_file_path = None

    try:
        check_python_version()

        with contextlib.closing(start_process()) as process:
            input_file_path = make_test_input_file()
            test_lines = make_test_lines(input_file_path)
            run_test_lines(process, test_lines)

            print_labeled_output(
                'PASSED',
                'Your Project 1 implementation passed the sanity checker.  Note that',
                'there are many other tests you\'ll want to run on your own, because',
                'a number of other scenarios exist that are legal and interesting.')
    except TestFailure:
        print_labeled_output(
            'FAILED',
            'The sanity checker has failed, for the reasons described above.')
    finally:
        if input_file_path is not None:
            input_file_path.unlink(missing_ok = True)



def check_python_version() -> None:
    major, minor, _ = platform.python_version_tuple()
    req_major, req_minor = _REQUIRED_PYTHON_VERSION

    if (major, minor) != (req_major, req_minor):
        print_labeled_output(
            'ERROR',
            f'The version of Python in use is {platform.python_version()}.',
            f'This course requires the use of a {req_major}.{req_minor} version instead.')

        raise TestFailure()



def start_process() -> TextProcess:
    module_path = Path.cwd() / 'project1.py'

    if not module_path.exists() or not module_path.is_file():
        print_labeled_output(
            'ERROR',
            'Cannot find an executable "project1.py" file in this directory.',
            'Make sure that the sanity checker is in the same directory as the',
            'files that comprise your Project 1 solution.')

        raise TestFailure()
    else:
        return TextProcess(
            [sys.executable, str(module_path)],
            str(Path.cwd()))



def print_labeled_output(label: str, *msg_lines: Sequence[str]) -> None:
    showed_first = False

    for msg_line in msg_lines:
        if not showed_first:
            print('{:10}|{}'.format(label, msg_line))
            showed_first = True
        else:
            print('{:10}|{}'.format(' ', msg_line))

    if not showed_first:
        print(label)



def make_test_input_file() -> Path:
    with tempfile.NamedTemporaryFile(mode = 'w', encoding = 'utf-8', delete = False) as input_file:
        input_file.write('LENGTH 900\n')
        input_file.write('DEVICE 1\n')
        input_file.write('DEVICE 2\n')
        input_file.write('PROPAGATE 1 2 100\n')
        input_file.write('PROPAGATE 2 1 100\n')
        input_file.write('ALERT 1 Badness 200\n')
        input_file.write('CANCEL 1 Badness 450\n')

    return Path(input_file.name)


def make_test_lines(input_path: Path) -> list[TestInputLine | TestOutputLines]:
    return [
        TestInputLine(str(input_path)),
        TestOutputLines('@200: #1 SENT ALERT TO #2: Badness', timeout = 10.0),
        TestOutputLines(
            '@300: #2 RECEIVED ALERT FROM #1: Badness',
            '@300: #2 SENT ALERT TO #1: Badness',
            timeout = 10.0),
        TestOutputLines(
            '@400: #1 RECEIVED ALERT FROM #2: Badness',
            '@400: #1 SENT ALERT TO #2: Badness',
            timeout = 10.0),
        TestOutputLines('@450: #1 SENT CANCELLATION TO #2: Badness', timeout = 10.0),
        TestOutputLines(
            '@500: #2 RECEIVED ALERT FROM #1: Badness',
            '@500: #2 SENT ALERT TO #1: Badness',
            timeout = 10.0),
        TestOutputLines(
            '@550: #2 RECEIVED CANCELLATION FROM #1: Badness',
            '@550: #2 SENT CANCELLATION TO #1: Badness',
            timeout = 10.0),
        TestOutputLines('@600: #1 RECEIVED ALERT FROM #2: Badness', timeout = 10.0),
        TestOutputLines('@650: #1 RECEIVED CANCELLATION FROM #2: Badness', timeout = 10.0),
        TestOutputLines('@900: END', timeout = 10.0),
        TestEndOfOutput(2.0)
    ]



def run_test_lines(process: TextProcess, test_lines: list[TestInputLine | TestOutputLines]) -> None:
    for line in test_lines:
        line.execute(process)



if __name__ == '__main__':
    run_test()
