# This test verifies the fix in _curses where resizeterm/resize_term now
# validate arguments as signed short and raise OverflowError when out of range.
# It also ensures that an overflow attempt does not corrupt curses state so that
# a subsequent initscr/erase still works (no crash).

from test.support.script_helper import assert_python_ok


def run_subprocess_test():
    code = """if 1:
        import sys
        try:
            import curses
        except Exception:
            # curses not available on this platform, skip
            sys.exit(0)

        try:
            curses.initscr()
        except curses.error:
            # No terminal available, skip the test gracefully
            sys.exit(0)
        else:
            # Validate OverflowError is raised for too-large values
            for func in (curses.resizeterm, curses.resize_term):
                try:
                    func(35000, 1)
                    assert False, f"Expected OverflowError for {func.__name__}(35000, 1)"
                except OverflowError as e:
                    msg = str(e)
                    assert "signed short" in msg, (
                        f"Expected 'signed short' in error message for {func.__name__}(35000, 1), got: {msg!r}")

                try:
                    func(1, 35000)
                    assert False, f"Expected OverflowError for {func.__name__}(1, 35000)"
                except OverflowError as e:
                    msg = str(e)
                    assert "signed short" in msg, (
                        f"Expected 'signed short' in error message for {func.__name__}(1, 35000), got: {msg!r}")

                # Also test too-small (less than SHRT_MIN)
                try:
                    func(-40000, 1)
                    assert False, f"Expected OverflowError for {func.__name__}(-40000, 1)"
                except OverflowError as e:
                    msg = str(e)
                    assert "signed short" in msg, (
                        f"Expected 'signed short' in error message for {func.__name__}(-40000, 1), got: {msg!r}")

                try:
                    func(1, -40000)
                    assert False, f"Expected OverflowError for {func.__name__}(1, -40000)"
                except OverflowError as e:
                    msg = str(e)
                    assert "signed short" in msg, (
                        f"Expected 'signed short' in error message for {func.__name__}(1, -40000), got: {msg!r}")

            # GH-120378 regression: after overflow failure, a subsequent initscr and erase
            # operation should still succeed (no crash, no exception)
            tmp = curses.initscr()
            # The erase call should not raise; return value isn't critical
            tmp.erase()
            curses.endwin()
    """

    rc, out, err = assert_python_ok('-c', code)
    # Ensure subprocess did not crash and produced no stderr
    assert rc == 0, f"Expected return code 0, got: {rc} with stderr: {err!r}"
    assert not err, f"Expected no stderr, got: {err!r}"


if __name__ == '__main__':
    run_subprocess_test()
