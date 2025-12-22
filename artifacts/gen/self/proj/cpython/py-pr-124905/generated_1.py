# This test verifies the fix for argument bounds checking in _curses.resizeterm
# and _curses.resize_term where parameters were changed from int to short and
# now raise OverflowError when out of the C short range. It also checks that
# after such failures, the curses state remains usable (no crash and basic
# operations work).

from test.support.script_helper import assert_python_ok


def run_subprocess_test():
    code = """if 1:
        import curses

        def check_overflow(func, name):
            # Too large nlines
            try:
                func(35000, 1)
                raise AssertionError(f"{name}: Expected OverflowError for nlines > SHRT_MAX")
            except OverflowError:
                pass

            # Too large ncols
            try:
                func(1, 35000)
                raise AssertionError(f"{name}: Expected OverflowError for ncols > SHRT_MAX")
            except OverflowError:
                pass

            # Too small (below SHRT_MIN)
            try:
                func(-40000, 1)
                raise AssertionError(f"{name}: Expected OverflowError for nlines < SHRT_MIN")
            except OverflowError:
                pass

            try:
                func(1, -40000)
                raise AssertionError(f"{name}: Expected OverflowError for ncols < SHRT_MIN")
            except OverflowError:
                pass

        # Initialize curses first; without a terminal this may fail and we skip.
        try:
            stdscr = curses.initscr()
        except curses.error:
            # No terminal available, skip the test body.
            pass
        else:
            try:
                # Validate overflow behavior through the public curses API
                if hasattr(curses, 'resizeterm'):
                    check_overflow(curses.resizeterm, 'curses.resizeterm')
                if hasattr(curses, 'resize_term'):
                    check_overflow(curses.resize_term, 'curses.resize_term')

                # Also validate via the underlying _curses module if available
                try:
                    import _curses as _cur
                except Exception:
                    _cur = None
                if _cur is not None:
                    if hasattr(_cur, 'resizeterm'):
                        check_overflow(_cur.resizeterm, '_curses.resizeterm')
                    if hasattr(_cur, 'resize_term'):
                        check_overflow(_cur.resize_term, '_curses.resize_term')

                # GH-120378: Overflow failure should not corrupt state.
                stdscr.erase()
            finally:
                curses.endwin()
    """

    rc, out, err = assert_python_ok('-c', code)
    assert rc == 0, f"Expected return code 0, got: {rc}"
    assert out == b'', f"Expected empty stdout, got: {out}"
    assert not err, f"Expected no stderr, got: {err}"


if __name__ == '__main__':
    run_subprocess_test()
