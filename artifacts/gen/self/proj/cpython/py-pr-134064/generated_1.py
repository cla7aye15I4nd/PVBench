import sys

# This test verifies that sys.remote_exec properly validates the 'script' argument
# using PyUnicode_FSConverter. The CPython bug was checking for < 0 (negative)
# return code instead of == 0 from PyUnicode_FSConverter, which returns 0 on
# failure. As a result, invalid script arguments like None or integers could slip
# through and potentially cause crashes or undefined behavior. The fix changes
# the check to == 0, ensuring a proper exception (TypeError) is raised.


def require_remote_exec():
    if not hasattr(sys, 'remote_exec'):
        # Feature not available in this Python build; skip tests gracefully.
        # Using SystemExit(0) to report success/skip in this standalone test.
        raise SystemExit(0)


def assert_typeerror_with_message(obj):
    """Assert that sys.remote_exec(0, obj) raises TypeError with a helpful message.

    We check that the message mentions that a path-like or (str/bytes/os.PathLike)
    is expected and includes the provided type name when appropriate.
    """
    try:
        sys.remote_exec(0, obj)
        assert False, f"Expected TypeError for script={obj!r}"
    except TypeError as e:
        msg = str(e)
        # Require message to indicate bad type and expected kinds.
        expected_markers = ("path-like", "os.PathLike", "str, bytes")
        assert any(m in msg for m in expected_markers), (
            f"Error message should mention expected path types; got: {msg!r}")
        # Also require that the actual type name appears in the message when it's a simple type
        # (this is typical of PyUnicode_FSConverter: "..., not NoneType" / "..., not int").
        tname = type(obj).__name__
        assert (tname in msg) or (tname == 'NoneType' and 'NoneType' in msg) or ('NoneType' in msg), (
            f"Error message should mention offending type; expected to find {tname!r} in {msg!r}")


def test_none_script_raises_typeerror():
    require_remote_exec()
    # Core PoC: passing None must raise TypeError (no crash, no undefined behavior)
    assert_typeerror_with_message(None)


def test_int_script_raises_typeerror():
    require_remote_exec()
    assert_typeerror_with_message(123)


def test_object_script_raises_typeerror():
    require_remote_exec()
    try:
        sys.remote_exec(0, object())
        assert False, "Expected TypeError for script=object()"
    except TypeError:
        pass


def test_list_script_raises_typeerror():
    require_remote_exec()
    try:
        sys.remote_exec(0, [])
        assert False, "Expected TypeError for script=[]"
    except TypeError:
        pass


def test_pathlike_returning_bad_type_raises_typeerror():
    require_remote_exec()

    class BadPathLike:
        def __fspath__(self):
            # Returning an invalid type from __fspath__ should also fail conversion
            return 42

    try:
        sys.remote_exec(0, BadPathLike())
        assert False, "Expected TypeError for script=BadPathLike() returning non-str/bytes"
    except TypeError as e:
        # Message may vary; ensure TypeError is raised at least
        msg = str(e)
        # often mentions the offending type ('int')
        assert 'int' in msg or 'str' in msg or 'bytes' in msg or 'os.PathLike' in msg or 'path-like' in msg, (
            f"Unexpected TypeError message for bad __fspath__ return: {msg!r}")


if __name__ == '__main__':
    test_none_script_raises_typeerror()
    test_int_script_raises_typeerror()
    test_object_script_raises_typeerror()
    test_list_script_raises_typeerror()
    test_pathlike_returning_bad_type_raises_typeerror()
    
    # If we reach here without assertion failures, the fix is considered verified.
