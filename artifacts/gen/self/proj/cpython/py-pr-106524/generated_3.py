# Self-contained test verifying fix for _sre.template crash with invalid group indices
# The patch ensures that on errors (non-integer index or negative index), the
# internal template object is safely cleaned up without crashing, and proper
# exceptions are raised.

from test.support.script_helper import assert_python_ok


def test_no_crash_and_typeerror_on_negative_index_subprocess():
    # Use subprocess isolation to ensure that historically crashing inputs
    # do not segfault the interpreter. We catch the exception inside the
    # child process so it exits cleanly with rc == 0 when behavior is correct.
    code = """if 1:
        import _sre
        try:
            _sre.template("", ["", -1, ""])  # invalid negative group index
        except TypeError as e:
            # Print marker to stdout to assert behavior and avoid non-zero exit
            print("OK:TypeError", str(e))
        else:
            print("FAIL: no exception")
    """
    rc, out, err = assert_python_ok('-c', code)
    assert rc == 0, f"Expected return code 0, got: {rc}"
    assert b'OK:TypeError' in out, f"Expected TypeError marker in stdout, got: {out!r}"
    assert not err, f"Expected no stderr, got: {err!r}"


def test_no_crash_and_typeerror_on_non_integer_index_subprocess():
    # Non-integer index should raise TypeError (conversion error) and not crash.
    code = """if 1:
        import _sre
        try:
            _sre.template("", ["", (), ""])  # non-integer index
        except TypeError as e:
            print("OK:TypeError", str(e))
        else:
            print("FAIL: no exception")
    """
    rc, out, err = assert_python_ok('-c', code)
    assert rc == 0, f"Expected return code 0, got: {rc}"
    assert b'OK:TypeError' in out, f"Expected TypeError marker in stdout, got: {out!r}"
    assert not err, f"Expected no stderr, got: {err!r}"


def test_negative_index_direct_exception_and_message():
    import _sre
    # Direct testing in-process: ensure we get the intended TypeError
    try:
        _sre.template("", ["", -1, ""])  # invalid negative index
        assert False, "Expected TypeError"
    except TypeError as e:
        # Historically this raised a crash; after the fix it must be a clean TypeError
        msg = str(e)
        assert "invalid template" in msg, (
            f"Expected 'invalid template' in error, got: {e!r}")


def test_non_integer_index_direct_exception_and_message():
    import _sre
    try:
        _sre.template("", ["", (), ""])  # non-integer should fail conversion
        assert False, "Expected TypeError"
    except TypeError as e:
        msg = str(e)
        # CPython error message for non-integer index conversion
        assert "an integer is required" in msg, (
            f"Expected 'an integer is required' in error, got: {e!r}")


essentially_infinite = 1 << 200  # definitely larger than Py_ssize_t

def test_too_large_index_overflowerror():
    import _sre
    # PyLong_AsSsize_t should raise OverflowError for an index larger than Py_ssize_t
    try:
        _sre.template("", ["", essentially_infinite, ""])  # huge index
        assert False, "Expected OverflowError"
    except OverflowError:
        # Type is sufficient; message may vary across platforms
        pass


def test_multiple_invalid_indices_still_no_crash_subprocess():
    # A template with multiple entries, the first invalid should fail gracefully
    code = """if 1:
        import _sre
        # Multiple items; the first invalid should trigger error handling without crash
        try:
            _sre.template("", ["a", -123, "b", 1, "c"])  # invalid negative at first index
        except TypeError as e:
            print("OK:TypeError", str(e))
        else:
            print("FAIL: no exception")
    """
    rc, out, err = assert_python_ok('-c', code)
    assert rc == 0, f"Expected return code 0, got: {rc}"
    assert b'OK:TypeError' in out, f"Expected TypeError marker in stdout, got: {out!r}"
    assert not err, f"Expected no stderr, got: {err!r}"


def main():
    test_no_crash_and_typeerror_on_negative_index_subprocess()
    test_no_crash_and_typeerror_on_non_integer_index_subprocess()
    test_negative_index_direct_exception_and_message()
    test_non_integer_index_direct_exception_and_message()
    test_too_large_index_overflowerror()
    test_multiple_invalid_indices_still_no_crash_subprocess()


if __name__ == '__main__':
    main()
