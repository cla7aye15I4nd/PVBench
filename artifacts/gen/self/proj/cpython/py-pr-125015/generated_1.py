import ast
import re
import sys

# This test verifies the fix for a use-after-free/double-decref in ast repr()
# when formatting a Constant whose value's repr() fails (e.g., due to the
# integer string digit limit). The original bug decref'ed the value on the
# error path and then again later, which could lead to a crash. The fix
# removed the extra decref.
#
# Notes for cross-version robustness:
# - Some Python versions (e.g., 3.13+) implement a rich repr() for AST nodes
#   that includes field names/values and may call repr() on Constant.value.
#   On these versions, very large integers can cause ValueError due to the
#   integer string conversion digit limit; this exercises the error path.
# - Other versions may not have a rich repr() for AST nodes; repr() then
#   returns the default object repr and does not touch Constant.value.
#   On such versions, we only verify that no crash occurs.

from test.support.script_helper import assert_python_ok


def test_large_constant_repr_no_crash_subprocess():
    # Use subprocess to ensure that any potential crash or segfault is isolated.
    code = """if 1:
    import ast, re
    source = "0x0" + "e" * 10_000
    value = eval(source)
    try:
        r = repr(ast.Constant(value=value))
        # repr succeeded; verify it's a string (content may vary by version)
        assert isinstance(r, str), f"repr should return str, got: {type(r)}"
        print("REPR_OK")
    except ValueError as e:
        msg = str(e)
        # Known message pattern on modern Pythons; accept others but record it
        if re.search(r"Exceeds the limit \\((\\d+) digits\\)", msg):
            print("VALUEERROR_LIMIT:" + msg)
        else:
            # Accept non-standard messages, but still confirm it is ValueError
            print("VALUEERROR_OTHER:" + msg)
    """
    rc, out, err = assert_python_ok('-c', code)
    assert rc == 0, f"Expected return code 0, got: {rc}"
    assert not err, f"Expected no stderr, got: {err}"
    # Must have printed one of the markers
    assert (b"REPR_OK" in out) or (b"VALUEERROR_LIMIT:" in out) or (b"VALUEERROR_OTHER:" in out), (
        f"Expected one of 'REPR_OK' or 'VALUEERROR_*' in stdout, got: {out!r}"
    )


def test_basic_constant_repr_is_string():
    # Sanity check: repr returns a string; structure is version-specific
    r = repr(ast.Constant(value=123))
    assert isinstance(r, str), f"repr should return str, got: {type(r)}"


def test_valueerror_path_with_adjusted_digit_limit_if_available():
    # If available, force a small digit limit to trigger ValueError while
    # formatting repr() of a Constant with a large integer value. On versions
    # without rich AST repr(), accept that no ValueError is raised.
    set_limit = getattr(sys, 'set_int_max_str_digits', None)
    get_limit = getattr(sys, 'get_int_max_str_digits', None)
    if not (set_limit and get_limit):
        return  # Feature not available on this Python; nothing to test here.

    old = get_limit()
    try:
        # Try setting a very small limit; if not allowed, fall back to 641
        try:
            set_limit(50)
            chosen_limit = 50
        except ValueError:
            chosen_limit = 641
            set_limit(chosen_limit)
        # Create a big integer via bit shifting (avoid string parsing limits)
        big_int = 1 << 4000  # ~1205 decimal digits, exceeds 641 comfortably
        try:
            r = repr(ast.Constant(value=big_int))
            # If no ValueError raised, ensure repr returned a string
            assert isinstance(r, str), f"repr should return str, got: {type(r)}"
        except ValueError as e:
            msg = str(e)
            # Accept known wording or any message that mentions a limit.
            assert (
                "Exceeds the limit" in msg or "limit" in msg.lower()
            ), f"Unexpected ValueError message: {msg!r}"
    finally:
        set_limit(old)


if __name__ == '__main__':
    test_large_constant_repr_no_crash_subprocess()
    test_basic_constant_repr_is_string()
    test_valueerror_path_with_adjusted_digit_limit_if_available()
    # If we reach here without assertion failures, all tests passed.
