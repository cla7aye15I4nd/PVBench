# Comprehensive test for the int() multi-argument TypeError fix
# The patch fixed a crash due to an incorrect format string used when
# raising a TypeError for too many positional arguments to int().
# It also standardized the error message to:
#   "int expected at most 2 arguments, got N"
#
# This test verifies:
# - No crash occurs when calling int() with >2 positional args (run in subprocess)
# - The error message contains the expected information (supporting both old and new forms)
# - Edge cases: 4 arguments also produce the correct message
# - Valid calls with 1-2 arguments still work

from test.support.script_helper import assert_python_ok


def test_no_crash_and_message_for_three_args_subprocess():
    # Run in a subprocess to catch any potential crashes/segfaults.
    # We catch the TypeError in the subprocess and print its message.
    code = """if 1:
    import sys
    try:
        int('10', 2, 1)
    except TypeError as e:
        sys.stdout.write(str(e))
    else:
        sys.stdout.write('NO_EXCEPTION')
"""
    rc, out, err = assert_python_ok('-c', code)

    # Ensure the interpreter did not crash and exited cleanly
    assert rc == 0, f"Expected return code 0, got: {rc}\nstderr: {err}"
    # No stderr expected because the exception is handled inside the subprocess
    assert err == b'', f"Expected no stderr, got: {err}"

    # Verify the error message is one of the expected forms and contains the correct count
    variants = [
        b"int expected at most 2 arguments, got 3",
        b"int() takes at most 2 arguments (3 given)",
    ]
    assert any(v in out for v in variants), (
        f"Unexpected error message for int('10', 2, 1).\n"
        f"Expected one of: {variants!r}\nGot stdout: {out!r}"
    )


def test_message_for_four_args_direct():
    # Direct test (no subprocess needed) for 4 positional arguments
    try:
        int('10', 2, 1, 0)
        assert False, "Expected TypeError for 4 positional arguments"
    except TypeError as e:
        msg = str(e)
        # Must mention arguments and the correct count (support both forms)
        assert "arguments" in msg, f"Expected 'arguments' in message, got: {msg!r}"
        has_count = ("got 4" in msg) or ("(4 given)" in msg)
        assert has_count, f"Expected count indicator ('got 4' or '(4 given)') in message, got: {msg!r}"


def test_valid_two_args():
    # Sanity check: valid calls should still work
    res = int('10', 2)
    assert res == 2, f"int('10', 2) expected 2, got {res}"


if __name__ == '__main__':
    test_no_crash_and_message_for_three_args_subprocess()
    test_message_for_four_args_direct()
    test_valid_two_args()
    print('OK')
