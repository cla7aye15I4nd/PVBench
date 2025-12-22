# Generated test for _curses resizeterm/resize_term short bounds fix
# Verifies that overly large/small dimensions raise OverflowError and do not
# leave curses in a bad state (e.g., allowing a subsequent initscr and basic ops).

from test.support.script_helper import assert_python_ok

# Test 1: curses.resizeterm bounds and re-initscr safety
code_resizeterm = """if 1:
    import sys
    try:
        import curses
    except Exception:
        # _curses/curses not available, skip
        sys.exit(0)

    # Ensure required APIs exist
    if not hasattr(curses, 'initscr') or not hasattr(curses, 'resizeterm'):
        sys.exit(0)

    try:
        curses.initscr()
    except Exception:
        # No terminal available or initialization failed; skip
        sys.exit(0)
    else:
        def expect_overflow(call, which):
            try:
                call()
                raise AssertionError(f"Expected OverflowError for {which}")
            except OverflowError as e:
                msg = str(e)
                if 'greater' in which:
                    assert 'greater than maximum' in msg, (
                        f"Expected 'greater than maximum' in error, got: {msg}")
                elif 'less' in which:
                    assert 'less than minimum' in msg, (
                        f"Expected 'less than minimum' in error, got: {msg}")

        # Values beyond SHRT_MAX should raise OverflowError
        expect_overflow(lambda: curses.resizeterm(35000, 1), 'nlines greater than maximum')
        expect_overflow(lambda: curses.resizeterm(1, 35000), 'ncols greater than maximum')

        # Values less than SHRT_MIN should raise OverflowError
        expect_overflow(lambda: curses.resizeterm(-40000, 1), 'nlines less than minimum')
        expect_overflow(lambda: curses.resizeterm(1, -40000), 'ncols less than minimum')

        # After failure, ensure we can still call initscr and perform operations
        tmp = curses.initscr()
        # A simple operation should succeed without raising
        tmp.erase()
        # Clean up
        curses.endwin()

    # Best-effort cleanup if still initialized
    try:
        curses.endwin()
    except Exception:
        pass
"""

# Test 2: curses.resize_term bounds
code_resize_term = """if 1:
    import sys
    try:
        import curses
    except Exception:
        # _curses/curses not available, skip
        sys.exit(0)

    # Ensure required APIs exist
    if not hasattr(curses, 'initscr') or not hasattr(curses, 'resize_term'):
        sys.exit(0)

    try:
        curses.initscr()
    except Exception:
        # No terminal available or initialization failed; skip
        sys.exit(0)
    else:
        def expect_overflow(call, which):
            try:
                call()
                raise AssertionError(f"Expected OverflowError for {which}")
            except OverflowError as e:
                msg = str(e)
                if 'greater' in which:
                    assert 'greater than maximum' in msg, (
                        f"Expected 'greater than maximum' in error, got: {msg}")
                elif 'less' in which:
                    assert 'less than minimum' in msg, (
                        f"Expected 'less than minimum' in error, got: {msg}")

        # Values beyond SHRT_MAX should raise OverflowError
        expect_overflow(lambda: curses.resize_term(35000, 1), 'nlines greater than maximum')
        expect_overflow(lambda: curses.resize_term(1, 35000), 'ncols greater than maximum')

        # Values less than SHRT_MIN should raise OverflowError
        expect_overflow(lambda: curses.resize_term(-40000, 1), 'nlines less than minimum')
        expect_overflow(lambda: curses.resize_term(1, -40000), 'ncols less than minimum')

        # Clean up
        curses.endwin()

    # Best-effort cleanup if still initialized
    try:
        curses.endwin()
    except Exception:
        pass
"""

# Run tests in isolated subprocesses to guard against crashes/segfaults
rc, out, err = assert_python_ok('-c', code_resizeterm)
assert rc == 0, f"Expected return code 0, got: {rc}"
assert not err, f"Expected no stderr, got: {err}"

rc, out, err = assert_python_ok('-c', code_resize_term)
assert rc == 0, f"Expected return code 0, got: {rc}"
assert not err, f"Expected no stderr, got: {err}"
