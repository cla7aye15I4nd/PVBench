# Self-contained test script verifying fix for int() with more than two arguments
# The patch fixed a crash caused by an incorrect format string in the
# TypeError raised when int() receives more than two positional arguments.
# This test ensures:
#  - No crash occurs (process isolation via subprocess)
#  - A TypeError is raised and the message contains reasonable content
#    indicating too many arguments, including the count provided
#  - Normal behavior for valid two-argument usage remains correct

from test.support.script_helper import assert_python_ok


def _run_in_subprocess(call_src: str):
    """Run a code snippet in a subprocess and capture stdout/stderr.
    The snippet prints the exception message if TypeError occurs, otherwise prints NO_ERROR.
    """
    code = f"""if 1:
    try:
        {call_src}
    except TypeError as e:
        import sys
        sys.stdout.write(str(e))
    else:
        print('NO_ERROR')
    """
    rc, out, err = assert_python_ok('-c', code)
    return rc, out, err


def _assert_message_indicates_too_many_args(msg: str, got_n: int):
    # The exact wording may differ across versions. Accept either the new style
    # "int expected at most 2 arguments, got N" or the older style
    # "int() takes at most 2 arguments (N given)".
    msg_lower = msg.lower()
    assert 'argument' in msg_lower, f"Expected 'argument' substring in error message: {msg!r}"
    assert '2' in msg_lower, f"Expected '2' in error message: {msg!r}"
    # Accept either of the numeric indications for the number of provided args
    ok_count = (f"got {got_n}" in msg_lower) or (f"({got_n} given)" in msg_lower)
    assert ok_count, (
        f"Error message should indicate provided count {got_n}: {msg!r}")
    # Ensure no raw format placeholders like '%s' are present (guard against the original bug)
    assert '%s' not in msg, f"Unexpected raw format placeholder in message: {msg!r}"


def test_int_more_than_two_args_three():
    # int with three positional args should not crash, should raise TypeError with a proper message
    rc, out, err = _run_in_subprocess("int('10', 2, 1)")
    assert rc == 0, f"Expected return code 0, got: {rc}"
    assert not err, f"Expected no stderr, got: {err}"
    msg = out.decode('utf-8', 'replace')
    _assert_message_indicates_too_many_args(msg, 3)


def test_int_more_than_two_args_four():
    # int with four positional args should also give the correct message
    rc, out, err = _run_in_subprocess("int('10', 2, 1, 0)")
    assert rc == 0, f"Expected return code 0, got: {rc}"
    assert not err, f"Expected no stderr, got: {err}"
    msg = out.decode('utf-8', 'replace')
    _assert_message_indicates_too_many_args(msg, 4)


def test_int_two_args_valid_behavior():
    # Valid two-argument behavior should remain unchanged
    # int('10', 2) should be 2
    result = int('10', 2)
    assert result == 2, f"Expected int('10', 2) == 2, got {result}"


if __name__ == '__main__':
    test_int_more_than_two_args_three()
    test_int_more_than_two_args_four()
    test_int_two_args_valid_behavior()
    print('OK')
