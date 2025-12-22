# Comprehensive test for GH-120378: ensure _curses.resizeterm / resize_term validate
# arguments as signed short and raise OverflowError on overflow, without leaving
# curses in a broken state.

from test.support.script_helper import assert_python_ok

# Run the actual curses interactions in a subprocess to avoid terminal state issues
CODE = """if 1:
    import sys
    try:
        import curses
    except Exception:
        # curses not available on this platform, skip
        sys.exit(0)

    # Try to initialize curses; if there's no terminal, skip the test gracefully
    try:
        stdscr = curses.initscr()
    except Exception as e:
        # No terminal available (e.g., non-interactive CI), skip
        sys.exit(0)

    import ctypes

    # Compute SHRT_MIN / SHRT_MAX dynamically from the platform's c_short
    bits = ctypes.sizeof(ctypes.c_short) * 8
    SHRT_MAX = (1 << (bits - 1)) - 1
    SHRT_MIN = -(1 << (bits - 1))
    too_big = SHRT_MAX + 1
    too_small = SHRT_MIN - 1

    # Determine which APIs are present; both should be, but be defensive
    funcs = []
    if hasattr(curses, 'resizeterm'):
        funcs.append(('resizeterm', curses.resizeterm))
    if hasattr(curses, 'resize_term'):
        funcs.append(('resize_term', curses.resize_term))

    # If neither function is present, nothing to test
    if not funcs:
        curses.endwin()
        sys.exit(0)

    # 1) OverflowError must be raised for values > SHRT_MAX and < SHRT_MIN
    for name, func in funcs:
        # too_big in first arg
        try:
            func(too_big, 1)
            raise AssertionError(f"{name}({too_big}, 1) did not raise OverflowError")
        except OverflowError as e:
            msg = str(e)
            assert 'signed short integer' in msg, (
                f"{name} first-arg too_big: expected 'signed short integer' in error, got: {msg!r}")
            assert 'greater than maximum' in msg, (
                f"{name} first-arg too_big: expected 'greater than maximum' in error, got: {msg!r}")

        # too_big in second arg
        try:
            func(1, too_big)
            raise AssertionError(f"{name}(1, {too_big}) did not raise OverflowError")
        except OverflowError as e:
            msg = str(e)
            assert 'signed short integer' in msg, (
                f"{name} second-arg too_big: expected 'signed short integer' in error, got: {msg!r}")
            assert 'greater than maximum' in msg, (
                f"{name} second-arg too_big: expected 'greater than maximum' in error, got: {msg!r}")

        # too_small in first arg
        try:
            func(too_small, 1)
            raise AssertionError(f"{name}({too_small}, 1) did not raise OverflowError")
        except OverflowError as e:
            msg = str(e)
            assert 'signed short integer' in msg, (
                f"{name} first-arg too_small: expected 'signed short integer' in error, got: {msg!r}")
            assert 'less than minimum' in msg, (
                f"{name} first-arg too_small: expected 'less than minimum' in error, got: {msg!r}")

        # too_small in second arg
        try:
            func(1, too_small)
            raise AssertionError(f"{name}(1, {too_small}) did not raise OverflowError")
        except OverflowError as e:
            msg = str(e)
            assert 'signed short integer' in msg, (
                f"{name} second-arg too_small: expected 'signed short integer' in error, got: {msg!r}")
            assert 'less than minimum' in msg, (
                f"{name} second-arg too_small: expected 'less than minimum' in error, got: {msg!r}")

    # 2) After overflow failures, curses should remain usable.
    # GH-120378: Overflow in resizeterm() previously left the terminal state
    # inconsistent so subsequent screen operations could fail. Validate that we
    # can still initialize and use the screen.
    tmp = curses.initscr()
    tmp.erase()  # a simple operation that should succeed

    # Clean up terminal state
    curses.endwin()
"""


def main():
    rc, out, err = assert_python_ok('-c', CODE)
    assert rc == 0, f"Expected return code 0, got: {rc}"
    assert err == b'', f"Expected no stderr, got: {err}"


if __name__ == '__main__':
    main()
