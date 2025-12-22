# Self-contained test script for verifying fix in _sre.template handling of invalid group indices
# The patch ensures no crashes when encountering invalid indices by properly adjusting
# the partially constructed object's size before cleanup.

import _sre


def test_negative_index_raises_typeerror_with_message():
    # A negative group index in the template should raise TypeError("invalid template")
    try:
        _sre.template("", ["", -1, ""])  # minimal invalid template (single pair)
        assert False, "Expected TypeError for negative group index"
    except TypeError as e:
        msg = str(e)
        assert "invalid template" in msg, f"Expected 'invalid template' in error, got: {msg}"


def test_non_integer_index_raises_typeerror_with_message():
    # A non-integer index should raise TypeError indicating an integer is required
    try:
        _sre.template("", ["", (), ""])  # use a tuple to trigger conversion error
        assert False, "Expected TypeError for non-integer group index"
    except TypeError as e:
        msg = str(e)
        assert "an integer is required" in msg, (
            f"Expected 'an integer is required' in error, got: {msg}"
        )


def test_oversized_integer_index_raises_overflowerror():
    # Extremely large integers will fail PyLong_AsSsize_t conversion and raise OverflowError.
    # The patch ensures this failure path does not crash due to improper cleanup.
    big = 1 << 1000
    try:
        _sre.template("", ["", big, ""])  # conversion should fail
        assert False, "Expected OverflowError for too large integer"
    except OverflowError as e:
        msg = str(e)
        # Be lenient on message content but ensure it indicates the size issue
        assert "too large" in msg or "overflow" in msg.lower(), (
            f"Expected message to indicate size problem, got: {msg}"
        )


def test_no_crash_with_partial_template_in_subprocess():
    # Use subprocess isolation to ensure that code path which previously crashed does not.
    # Construct a template with some valid entries followed by an invalid negative index,
    # to exercise the partial-construction cleanup logic introduced by the patch.
    from test.support.script_helper import assert_python_ok

    code = """if 1:
    import _sre, sys
    # valid then invalid to ensure partially constructed internal object before failure
    try:
        _sre.template("", ["", 0, "middle", -1, "tail"])  # -1 should trigger TypeError
    except TypeError as e:
        assert "invalid template" in str(e), f"Expected 'invalid template' in error, got: {e}"
        print("OK")
    else:
        print("NOERROR")
        sys.exit(1)
"""
    rc, out, err = assert_python_ok('-c', code)
    assert rc == 0, f"Expected return code 0, got: {rc}"
    assert b"OK" in out, f"Expected 'OK' in stdout, got: {out!r}"
    assert not err, f"Expected no stderr, got: {err!r}"


def main():
    test_negative_index_raises_typeerror_with_message()
    test_non_integer_index_raises_typeerror_with_message()
    test_oversized_integer_index_raises_overflowerror()
    test_no_crash_with_partial_template_in_subprocess()


if __name__ == '__main__':
    main()
