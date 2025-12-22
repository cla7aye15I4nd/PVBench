# Comprehensive test for _curses argument range checks in resizeterm/resize_term
# This test verifies that passing values outside of the C 'short' range to
# curses.resizeterm and curses.resize_term raises OverflowError with the
# correct messages, and that a failed call does not corrupt the curses state.

from test.support.script_helper import assert_python_ok


def run_subprocess_test_for_curses():
    """Run a subprocess test for the high-level 'curses' module.

    The subprocess performs:
      - Import and initscr(); skip if unavailable
      - Call resizeterm/resize_term (if present) with values > SHRT_MAX and < SHRT_MIN
        and assert OverflowError with specific messages
      - Ensure subsequent curses operations still work (erase and endwin)
    """
    code = """if 1:
    import sys
    try:
        import curses as m
    except Exception:
        print('SKIP: import')
        raise SystemExit(0)

    # initscr may fail if no terminal is available
    try:
        stdscr = m.initscr()
    except Exception:
        print('SKIP: initscr')
        raise SystemExit(0)

    def check_func(func, fname):
        # Test positive overflow (> SHRT_MAX)
        try:
            func(35000, 1)
            print(f'NO_RAISE_POS {fname}')
        except OverflowError as e:
            msg = str(e)
            assert 'greater than maximum' in msg, f"Expected 'greater than maximum' in OverflowError for {fname}, got: {msg}"
            print(f'OK_POS {fname}')

        # Test negative overflow (< SHRT_MIN)
        try:
            func(-40000, 1)
            print(f'NO_RAISE_NEG {fname}')
        except OverflowError as e:
            msg = str(e)
            assert 'less than minimum' in msg, f"Expected 'less than minimum' in OverflowError for {fname}, got: {msg}"
            print(f'OK_NEG {fname}')

    # Test both API spellings if available
    for name in ('resizeterm', 'resize_term'):
        if hasattr(m, name):
            check_func(getattr(m, name), name)

    # Ensure that a failed call due to overflow did not corrupt state; do a simple op
    # that should succeed if the screen remains usable.
    try:
        tmp = m.initscr()
        tmp.erase()
    finally:
        # endwin even if erase failed, to be safe
        try:
            m.endwin()
        except Exception:
            pass

    print('DONE')
"""

    rc, out, err = assert_python_ok('-c', code)
    assert rc == 0, f"curses: Expected return code 0, got: {rc}"
    assert not err, f"curses: Expected no stderr, got: {err}"
    # If module not available or initscr unavailable, accept SKIP
    if b'SKIP' in out:
        return
    # Otherwise, ensure checks and finalization ran
    assert b'OK_POS' in out, f"curses: Expected positive overflow to be detected. Stdout: {out!r}"
    assert b'OK_NEG' in out, f"curses: Expected negative overflow to be detected. Stdout: {out!r}"
    assert b'DONE' in out, f"curses: Expected completion marker 'DONE' in stdout, got: {out!r}"


def test_high_level_curses():
    run_subprocess_test_for_curses()


if __name__ == '__main__':
    # Run test
    test_high_level_curses()
    print('All tests completed')
