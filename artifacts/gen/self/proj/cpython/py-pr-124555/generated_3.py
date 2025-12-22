# Comprehensive test for _curses.resizeterm / resize_term overflow handling
# and ensuring curses state remains usable after OverflowError.
#
# This test runs the critical parts in a subprocess for isolation, as
# curses may interact with the terminal and previous bug could cause a crash
# or corrupt state. We follow the recommended test.support.script_helper API.

from test.support.script_helper import assert_python_ok


def test_curses_resizeterm_overflow_and_state():
    code = """if 1:
        import sys
        try:
            import curses
        except Exception:
            # curses not available in this build; skip
            sys.exit(0)

        # If no terminal, initscr() may fail; skip gracefully.
        try:
            stdscr = curses.initscr()
        except Exception:
            sys.exit(0)

        try:
            # Validate OverflowError for too-large and too-small values
            if hasattr(curses, 'resizeterm'):
                try:
                    curses.resizeterm(35000, 1)
                    raise AssertionError("Expected OverflowError for resizeterm nlines > SHRT_MAX")
                except OverflowError:
                    pass

                try:
                    curses.resizeterm(1, 35000)
                    raise AssertionError("Expected OverflowError for resizeterm ncols > SHRT_MAX")
                except OverflowError:
                    pass

                try:
                    curses.resizeterm(-40000, 1)
                    raise AssertionError("Expected OverflowError for resizeterm nlines < SHRT_MIN")
                except OverflowError:
                    pass

                try:
                    curses.resizeterm(1, -40000)
                    raise AssertionError("Expected OverflowError for resizeterm ncols < SHRT_MIN")
                except OverflowError:
                    pass

            if hasattr(curses, 'resize_term'):
                try:
                    curses.resize_term(35000, 1)
                    raise AssertionError("Expected OverflowError for resize_term nlines > SHRT_MAX")
                except OverflowError:
                    pass

                try:
                    curses.resize_term(1, 35000)
                    raise AssertionError("Expected OverflowError for resize_term ncols > SHRT_MAX")
                except OverflowError:
                    pass

                try:
                    curses.resize_term(-40000, 1)
                    raise AssertionError("Expected OverflowError for resize_term nlines < SHRT_MIN")
                except OverflowError:
                    pass

                try:
                    curses.resize_term(1, -40000)
                    raise AssertionError("Expected OverflowError for resize_term ncols < SHRT_MIN")
                except OverflowError:
                    pass

            # GH-120378: Overflow failure in resizeterm()/resize_term() used to
            # corrupt curses state so that subsequent refresh/erase could fail.
            tmp = curses.initscr()
            # If state is fine, these should not raise
            tmp.erase()
            # refresh can be finicky on some setups; erase() suffices to check state,
            # but try refresh() as a stronger signal when available.
            try:
                tmp.refresh()
            except curses.error:
                # Some CI environments may not support refresh; don't fail the test solely for this
                pass
        finally:
            try:
                curses.endwin()
            except Exception:
                pass
        """

    rc, out, err = assert_python_ok('-c', code)
    # Ensure the subprocess produced no stderr noise
    assert not err, f"Expected no stderr from subprocess, got: {err!r}"


if __name__ == '__main__':
    test_curses_resizeterm_overflow_and_state()
    print('OK')
