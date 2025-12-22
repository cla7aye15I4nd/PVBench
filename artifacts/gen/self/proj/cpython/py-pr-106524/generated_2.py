# This test verifies the fix for a crash in _sre.template when handling
# invalid group indices or non-integer indices within the internal template
# representation. The patch ensures that partially-constructed template
# objects are resized appropriately before errors are raised, preventing
# crashes. We validate that the function raises the correct exceptions and
# does not crash across multiple edge cases.

from test.support.script_helper import assert_python_ok


def run_case(label: str, code: str, expect_token: bytes):
    rc, out, err = assert_python_ok('-c', code)
    assert rc == 0, f"{label}: Expected return code 0, got: {rc} (stdout={out!r}, stderr={err!r})"
    assert err == b'' or not err, f"{label}: Expected no stderr, got: {err!r}"
    assert expect_token in out, f"{label}: Expected {expect_token!r} in stdout, got: {out!r}"


def test_invalid_negative_index_first():
    # Simple invalid group index (-1). Previously could crash; now must raise
    # TypeError with 'invalid template'.
    code = """if 1:
    import _sre
    try:
        _sre.template("", ["", -1, ""])
    except TypeError as e:
        msg = str(e)
        assert "invalid template" in msg, f"Expected 'invalid template' in error, got: {msg!r}"
        print("OK A")
    else:
        raise SystemExit("Expected TypeError for invalid template (negative index)")
    """
    run_case("A", code, b"OK A")


def test_invalid_type_tuple():
    # Non-integer index (tuple). Should raise TypeError with 'an integer is required'.
    code = """if 1:
    import _sre
    try:
        _sre.template("", ["", (), ""])
    except TypeError as e:
        msg = str(e)
        assert "an integer is required" in msg, f"Expected 'an integer is required' in error, got: {msg!r}"
        print("OK B")
    else:
        raise SystemExit("Expected TypeError for non-integer index (tuple)")
    """
    run_case("B", code, b"OK B")


def test_invalid_negative_index_later_element():
    # Failure at a later index to exercise partial object resizing logic added
    # by the patch: first index valid (0), second invalid (-1). Should raise
    # TypeError('invalid template') without crashing.
    code = """if 1:
    import _sre
    try:
        _sre.template("", ["", 0, "", -1, ""])  # later invalid element
    except TypeError as e:
        msg = str(e)
        assert "invalid template" in msg, f"Expected 'invalid template' in error, got: {msg!r}"
        print("OK C")
    else:
        raise SystemExit("Expected TypeError for invalid template at later element")
    """
    run_case("C", code, b"OK C")


def test_overflow_large_index():
    # Extremely large positive index triggers conversion failure in
    # PyLong_AsSsize_t and should raise OverflowError (and not crash).
    code = """if 1:
    import _sre
    big = 1 << 1000
    try:
        _sre.template("", ["", big, ""])  # overflow for Py_ssize_t
    except OverflowError:
        print("OK D")
    else:
        raise SystemExit("Expected OverflowError for oversized index")
    """
    run_case("D", code, b"OK D")


if __name__ == '__main__':
    test_invalid_negative_index_first()
    test_invalid_type_tuple()
    test_invalid_negative_index_later_element()
    test_overflow_large_index()
