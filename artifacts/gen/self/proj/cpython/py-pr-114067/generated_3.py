# This test verifies the fix for a segmentation fault in int() when more than
# two positional arguments are passed. The original bug was caused by an
# incorrect format string in the TypeError message ("argument%s" with only one
# formatting argument provided), which could lead to a crash. The patch changes
# the error message to a static plural form and ensures safe formatting.
#
# We run the core check in a subprocess using assert_python_ok to guard against
# potential crashes and to validate the error message content. We also validate
# that valid two-argument usage of int() still works.

from test.support.script_helper import assert_python_ok


def run_subprocess_tests():
    code = """if 1:
        # Trigger int() with more than two positional arguments and validate
        # that it raises TypeError with a sensible message and does not crash.
        def check(n):
            # Build args like: int('10', 2, 0, 0, ...)
            args = ['10', 2] + [0] * (n - 2)
            try:
                int(*args)
                raise AssertionError(f"Expected TypeError for {n} args, but no exception was raised")
            except TypeError as e:
                msg = str(e)
                # Validate contents of the error message. Different Python versions
                # may have slightly different phrasings, e.g.:
                # - "int expected at most 2 arguments, got 3"
                # - "int() takes at most 2 arguments (3 given)"
                # We assert the essentials to ensure the bug is fixed and message is sane.
                assert 'int' in msg, f"Error message missing 'int': {msg!r}"
                assert '2' in msg, f"Error message missing '2': {msg!r}"
                assert 'argument' in msg, f"Error message missing 'argument(s)': {msg!r}"
                assert str(n) in msg, f"Error message missing arg count {n}: {msg!r}"
                assert ('got' in msg) or ('given' in msg), (
                    f"Expected 'got' or 'given' in message, got: {msg!r}")
        for n in (3, 4, 5):
            check(n)

        # Sanity check: two-argument form should succeed and return the expected value
        v = int('10', 2)
        assert v == 2, f"Expected int('10', 2) == 2, got {v}"

        print('SUBPROCESS_OK')
    """

    rc, out, err = assert_python_ok('-c', code)

    # Ensure the subprocess succeeded without crashing and without stderr noise
    assert rc == 0, f"Expected return code 0, got: {rc}"
    assert b'SUBPROCESS_OK' in out, f"Expected 'SUBPROCESS_OK' in stdout, got: {out!r}"
    assert not err, f"Expected no stderr, got: {err!r}"


def main():
    # Execute the subprocess-based tests that would have crashed before the fix
    run_subprocess_tests()


if __name__ == '__main__':
    main()
