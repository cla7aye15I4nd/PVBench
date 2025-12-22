# Comprehensive test for sys.remote_exec argument conversion fix
# The patch changes the error check of PyUnicode_FSConverter from <0 to ==0,
# ensuring that invalid "script" arguments (e.g., None, integers) are handled
# by raising a TypeError instead of proceeding and potentially crashing.

from test.support.script_helper import assert_python_ok

# Use subprocess isolation because the pre-fix behavior could segfault.
code = """if 1:
    import sys

    # Some builds or versions might not have sys.remote_exec; guard to avoid false failures.
    if not hasattr(sys, 'remote_exec'):
        print('SKIP: sys.remote_exec not available')
    else:
        def expect_typeerror(arg, label):
            try:
                # pid value is irrelevant for this test; we focus on the script arg conversion.
                sys.remote_exec(0, arg)
                print('NO_TYPEERROR', label)
            except TypeError as e:
                # Ensure we got a TypeError, which indicates the converter failure is now correctly handled.
                print('TypeError', label)

        # These arguments are not valid path-like objects and should cause TypeError
        expect_typeerror(None, 'NoneType')
        expect_typeerror(123, 'int')
        expect_typeerror(object(), 'object')
"""

rc, out, err = assert_python_ok('-c', code)

# Basic process checks
assert rc == 0, f"Expected return code 0, got: {rc}"
assert not err, f"Expected no stderr, got: {err}"

# If the feature is missing, accept the skip.
if b'SKIP: sys.remote_exec not available' in out:
    # Environment does not support this feature; nothing further to assert.
    pass
else:
    # Validate that TypeError was raised for each invalid argument.
    for label in (b'NoneType', b'int', b'object'):
        expected = b'TypeError ' + label
        assert expected in out, f"Missing expected output {expected!r}. Full stdout: {out!r}"
        unexpected = b'NO_TYPEERROR ' + label
        assert unexpected not in out, f"Unexpected success for {label.decode()}: got {unexpected!r} in stdout {out!r}"
