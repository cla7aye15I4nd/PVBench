# This test verifies the fix in sys.remote_exec argument conversion logic.
# The patch changed the check for PyUnicode_FSConverter from `< 0` to `== 0`.
# Previously, passing an invalid script (e.g., None, int, objects without a path)
# could bypass error handling and potentially crash. After the fix, such inputs
# must raise TypeError cleanly.

from test.support.script_helper import assert_python_ok


def has_remote_exec():
    probe = """if 1:
    import sys
    print('HAS_REMOTE_EXEC', hasattr(sys, 'remote_exec'))
    """
    rc, out, err = assert_python_ok('-c', probe)
    assert rc == 0, f"Probe failed with rc={rc}, stderr={err!r}"
    assert not err, f"Expected no stderr in probe, got: {err!r}"
    return b'HAS_REMOTE_EXEC True' in out


def test_invalid_script_types_raise_typeerror_without_crash():
    if not has_remote_exec():
        # Feature not available in this build; nothing to test.
        return

    # Run the potentially crashing calls in a subprocess to ensure isolation.
    code = """if 1:
    import sys

    class BadPathRaises:
        def __fspath__(self):
            raise TypeError('fs boom')

    class PathReturnsNone:
        def __fspath__(self):
            return None

    cases = [
        ('None', None),
        ('int', 123),
        ('object', object()),
        ('BadPathRaises', BadPathRaises()),
        ('PathReturnsNone', PathReturnsNone()),
    ]

    for name, arg in cases:
        try:
            # pid value is irrelevant here; we are probing argument conversion of script.
            sys.remote_exec(0, arg)
            print('NOEXC', name)
        except TypeError as e:
            # Expected after the fix: TypeError should be raised for all invalid types.
            print('TYPEERROR', name, str(e))
        except BaseException as e:
            # Any other exception type indicates unexpected behavior.
            print('OTHER', name, type(e).__name__, str(e))
    """

    rc, out, err = assert_python_ok('-c', code)

    # Basic subprocess expectations
    assert rc == 0, f"Expected return code 0, got: {rc} with stderr: {err!r} and stdout: {out!r}"
    assert not err, f"Expected no stderr, got: {err}"

    # Validate that all scenarios produced a TypeError and nothing else.
    expected = [
        b'TYPEERROR None',
        b'TYPEERROR int',
        b'TYPEERROR object',
        b'TYPEERROR BadPathRaises',
        b'TYPEERROR PathReturnsNone',
    ]
    for marker in expected:
        assert marker in out, f"Missing expected output marker {marker!r}. Got stdout: {out!r}"

    assert b'NOEXC' not in out, f"Unexpected successful call without exception. Stdout: {out!r}"
    assert b'OTHER' not in out, f"Unexpected non-TypeError exception. Stdout: {out!r}"


if __name__ == '__main__':
    test_invalid_script_types_raise_typeerror_without_crash()
    # If we reach here without assertion failures, the test passes.
