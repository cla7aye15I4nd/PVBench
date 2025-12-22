# Comprehensive test for _curses.resizeterm/resize_term overflow handling and state integrity
# This script validates the patch that changed the argument types from int to short
# and added explicit OverflowError checks for out-of-range values.

import sys


def test_overflow_handling_in_subprocess():
    # Use subprocess isolation to run with curses initialized (if possible),
    # and verify OverflowError is raised with a helpful message for both
    # resizeterm and resize_term on both parameters (too big and too small).
    from test.support.script_helper import assert_python_ok

    code = """if 1:
    import sys
    import curses

    def check_overflow_messages(func, name):
        # Greater-than-maximum checks
        try:
            func(35000, 1)
            raise AssertionError(f"Expected OverflowError from {name}(35000, 1)")
        except OverflowError as e:
            s = str(e)
            if ('greater than maximum' not in s) and ('signed short integer' not in s):
                raise AssertionError(f"OverflowError message (height) unexpected for {name}: {e!r}")

        try:
            func(1, 35000)
            raise AssertionError(f"Expected OverflowError from {name}(1, 35000)")
        except OverflowError as e:
            s = str(e)
            if ('greater than maximum' not in s) and ('signed short integer' not in s):
                raise AssertionError(f"OverflowError message (width) unexpected for {name}: {e!r}")

        # Less-than-minimum checks
        try:
            func(-40000, 1)
            raise AssertionError(f"Expected OverflowError from {name}(-40000, 1)")
        except OverflowError as e:
            s = str(e)
            if ('less than minimum' not in s) and ('signed short integer' not in s):
                raise AssertionError(f"OverflowError message (height<min) unexpected for {name}: {e!r}")

        try:
            func(1, -40000)
            raise AssertionError(f"Expected OverflowError from {name}(1, -40000)")
        except OverflowError as e:
            s = str(e)
            if ('less than minimum' not in s) and ('signed short integer' not in s):
                raise AssertionError(f"OverflowError message (width<min) unexpected for {name}: {e!r}")

    try:
        curses.initscr()
    except curses.error:
        print('SKIP: no terminal available')
    else:
        try:
            check_overflow_messages(curses.resizeterm, 'resizeterm')
            if hasattr(curses, 'resize_term'):
                check_overflow_messages(curses.resize_term, 'resize_term')
            print('OK: overflow messages verified')
        finally:
            try:
                curses.endwin()
            except Exception:
                pass
    """

    rc, out, err = assert_python_ok('-c', code)
    assert rc == 0, f"Expected return code 0, got: {rc}"
    assert not err, f"Expected no stderr, got: {err}"
    assert (b'OK' in out) or (b'SKIP' in out) or (out == b''), (
        f"Expected 'OK' or 'SKIP' in stdout, got: {out!r}")


def test_no_crash_and_state_ok_after_overflow_in_subprocess():
    # Use subprocess isolation to mimic the original PoC behavior which could crash
    # or leave curses in a bad state. We run a small script that:
    #  - initializes curses
    #  - triggers OverflowError in resizeterm/resize_term with out-of-range args
    #  - calls initscr() again and performs a simple operation (erase)
    # If there is no terminal, the script gracefully skips.
    from test.support.script_helper import assert_python_ok

    code = """if 1:
    import sys
    import curses

    def run_sequence(func):
        # Initialize the screen
        stdscr = curses.initscr()
        try:
            try:
                func(35000, 1)
                raise AssertionError("Expected OverflowError for height overflow")
            except OverflowError:
                pass

            try:
                func(1, 35000)
                raise AssertionError("Expected OverflowError for width overflow")
            except OverflowError:
                pass

            # Emulate PoC sequence: call initscr() again after an overflow failure
            # This used to break internal state (see GH-120378)
            tmp = curses.initscr()
            tmp.erase()
        finally:
            # Always try to restore terminal state
            try:
                curses.endwin()
            except Exception:
                pass

    try:
        # If we cannot initialize curses, skip the test in this subprocess
        curses.initscr()
    except curses.error:
        print('SKIP: no terminal available')
    else:
        try:
            run_sequence(curses.resizeterm)
            if hasattr(curses, 'resize_term'):
                run_sequence(curses.resize_term)
            print('OK: state intact after overflow')
        finally:
            try:
                curses.endwin()
            except Exception:
                pass
    """

    rc, out, err = assert_python_ok('-c', code)
    assert rc == 0, f"Expected return code 0, got: {rc}"
    # Ensure no unexpected stderr output
    assert not err, f"Expected no stderr, got: {err}"
    # Either we successfully ran (OK) or we skipped due to no terminal
    assert (b'OK' in out) or (b'SKIP' in out) or (out == b''), (
        f"Expected 'OK' or 'SKIP' in stdout, got: {out!r}")


def main():
    # Run subprocess-based tests that handle terminal availability gracefully
    test_overflow_handling_in_subprocess()
    test_no_crash_and_state_ok_after_overflow_in_subprocess()


if __name__ == '__main__':
    main()
