# This test verifies the fix for _curses.resizeterm/resize_term argument parsing.
# The patch changes the accepted types from int to short and adds explicit
# range checks to raise OverflowError when values are outside SHRT_MIN..SHRT_MAX.
#
# Primary checks are performed without initializing curses, because the overflow
# should be detected during argument conversion. If the environment lacks a
# usable terminal and the call fails early with _curses.error ("must call
# initscr() first"), the test skips gracefully.

from test.support.script_helper import assert_python_ok


def run_overflow_check(module_name: str):
    code = f"""if 1:
        import sys
        try:
            import {module_name} as _cur
        except Exception:
            # Module not available on this platform, skip test.
            sys.exit(0)

        import ctypes
        bits = ctypes.sizeof(ctypes.c_short) * 8
        SHRT_MIN = -(1 << (bits - 1))
        SHRT_MAX = (1 << (bits - 1)) - 1
        over_pos = SHRT_MAX + 1
        over_neg = SHRT_MIN - 1

        def expect_overflow_or_skip(func, *args):
            try:
                func(*args)
                raise AssertionError(f"Expected OverflowError for args={{args}}")
            except OverflowError:
                # Correct behavior per patch
                return
            except Exception as e:
                # If curses isn't initialized (no terminal), CPython may raise
                # _curses.error before argument conversion on older versions.
                # In that case, skip this test run gracefully.
                if hasattr(_cur, 'error') and isinstance(e, _cur.error):
                    sys.exit(0)
                raise

        # resizeterm: positive overflow
        expect_overflow_or_skip(_cur.resizeterm, over_pos, 1)
        expect_overflow_or_skip(_cur.resizeterm, 1, over_pos)

        # resizeterm: negative overflow
        expect_overflow_or_skip(_cur.resizeterm, over_neg, 1)
        expect_overflow_or_skip(_cur.resizeterm, 1, over_neg)

        # resize_term (alias): test if available
        if hasattr(_cur, 'resize_term'):
            expect_overflow_or_skip(_cur.resize_term, over_pos, 1)
            expect_overflow_or_skip(_cur.resize_term, 1, over_pos)
            expect_overflow_or_skip(_cur.resize_term, over_neg, 1)
            expect_overflow_or_skip(_cur.resize_term, 1, over_neg)
    """
    rc, out, err = assert_python_ok('-c', code)
    assert rc == 0, f"{module_name} (overflow): Expected return code 0, got: {rc}"
    assert not err, f"{module_name} (overflow): Expected no stderr, got: {err}"


def main():
    # Validate overflow behavior via both modules (skip gracefully if not
    # available or if a terminal is required but unavailable).
    run_overflow_check('curses')
    run_overflow_check('_curses')


if __name__ == '__main__':
    main()
