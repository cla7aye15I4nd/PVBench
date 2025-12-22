from test.support.script_helper import assert_python_ok

# This test verifies the fix for GH-120378 where _curses.resizeterm/resize_term
# now accept only signed short range and raise OverflowError on out-of-range
# values. It also ensures that after such failures, curses remains usable.

def run_subprocess_test():
    code = """if 1:
        import sys
        try:
            import curses
        except Exception:
            # curses not available, skip
            sys.exit(0)

        try:
            stdscr = curses.initscr()
        except Exception:
            # No usable terminal, skip test
            sys.exit(0)
        else:
            try:
                # Test resizeterm() raises OverflowError for too-large values
                if hasattr(curses, 'resizeterm'):
                    try:
                        curses.resizeterm(35000, 1)
                        raise AssertionError("Expected OverflowError for resizeterm(nlines)")
                    except OverflowError as e:
                        msg = str(e)
                        assert "signed short" in msg or msg == "", f"Unexpected OverflowError message: {msg}"

                    try:
                        curses.resizeterm(1, 35000)
                        raise AssertionError("Expected OverflowError for resizeterm(ncols)")
                    except OverflowError as e:
                        msg = str(e)
                        assert "signed short" in msg or msg == "", f"Unexpected OverflowError message: {msg}"

                    try:
                        curses.resizeterm(-40000, 1)
                        raise AssertionError("Expected OverflowError for resizeterm(nlines < SHRT_MIN)")
                    except OverflowError as e:
                        msg = str(e)
                        assert "signed short" in msg or msg == "", f"Unexpected OverflowError message: {msg}"

                    try:
                        curses.resizeterm(1, -40000)
                        raise AssertionError("Expected OverflowError for resizeterm(ncols < SHRT_MIN)")
                    except OverflowError as e:
                        msg = str(e)
                        assert "signed short" in msg or msg == "", f"Unexpected OverflowError message: {msg}"

                # Test resize_term() raises OverflowError for too-large values
                if hasattr(curses, 'resize_term'):
                    try:
                        curses.resize_term(35000, 1)
                        raise AssertionError("Expected OverflowError for resize_term(nlines)")
                    except OverflowError as e:
                        msg = str(e)
                        assert "signed short" in msg or msg == "", f"Unexpected OverflowError message: {msg}"

                    try:
                        curses.resize_term(1, 35000)
                        raise AssertionError("Expected OverflowError for resize_term(ncols)")
                    except OverflowError as e:
                        msg = str(e)
                        assert "signed short" in msg or msg == "", f"Unexpected OverflowError message: {msg}"

                    try:
                        curses.resize_term(-40000, 1)
                        raise AssertionError("Expected OverflowError for resize_term(nlines < SHRT_MIN)")
                    except OverflowError as e:
                        msg = str(e)
                        assert "signed short" in msg or msg == "", f"Unexpected OverflowError message: {msg}"

                    try:
                        curses.resize_term(1, -40000)
                        raise AssertionError("Expected OverflowError for resize_term(ncols < SHRT_MIN)")
                    except OverflowError as e:
                        msg = str(e)
                        assert "signed short" in msg or msg == "", f"Unexpected OverflowError message: {msg}"

                # After overflow failures, curses should still be usable (GH-120378)
                tmp = curses.initscr()
                tmp.erase()
            finally:
                try:
                    curses.endwin()
                except Exception:
                    pass
    """

    rc, out, err = assert_python_ok('-c', code)
    assert rc == 0, f"Expected return code 0, got: {rc}"
    # No output expected; test uses assertions internally
    assert err == b'' or err is None or err == b'\n', f"Expected no stderr, got: {err}"


if __name__ == '__main__':
    run_subprocess_test()
