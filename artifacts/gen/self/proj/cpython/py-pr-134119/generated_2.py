from test.support.script_helper import assert_python_ok

# This test verifies the fix for a crash when calling next() on an exhausted
# template string iterator. It runs target code in a subprocess to ensure
# isolation from potential crashes. If the running interpreter does not support
# template strings (t"..." literals) or the associated library, the test is
# skipped gracefully.

code = """if 1:
    import sys

    # Skip if template strings are not supported by this interpreter
    try:
        # Try to create a template string via eval to avoid parse-time SyntaxError
        _tmp = eval('t"{1}"')
    except SyntaxError:
        print("SKIP: template strings not supported")
        sys.exit(0)
    except Exception as e:
        # Any other unexpected error should fail the test to surface issues
        raise

    # Import Interpolation type; skip if unavailable
    try:
        from string.templatelib import Interpolation
    except Exception:
        print("SKIP: string.templatelib not available")
        sys.exit(0)

    def drain_and_check_repeated_stop(it, label):
        # Drain the iterator to the first StopIteration
        try:
            while True:
                next(it)
        except StopIteration:
            pass

        # After exhaustion, repeated next() calls must continue to raise StopIteration
        for i in range(3):
            try:
                next(it)
                raise AssertionError(f"{label}: Expected StopIteration on extra next call {i}")
            except StopIteration:
                pass

    # Case 1: Minimal reproducer t"{1}". Historically, this triggered the crash
    # on a next() call after StopIteration.
    it1 = iter(eval('t"{1}"'))
    first = next(it1)
    assert isinstance(first, Interpolation), f"case1: Expected Interpolation first, got {type(first)}"
    # Second next should raise StopIteration
    try:
        next(it1)
        raise AssertionError("case1: Expected StopIteration on second next()")
    except StopIteration:
        pass
    # Third and subsequent next() calls should also raise StopIteration and not crash
    for i in range(3):
        try:
            next(it1)
            raise AssertionError(f"case1: Expected StopIteration on extra next call {i}")
        except StopIteration:
            pass
    print("case1_ok")

    # Case 2: Starts with a string then an interpolation, to exercise switching
    # between strings and interpolations. Ensures post-exhaustion next() continues
    # to raise StopIteration.
    it2 = iter(eval('t"a{1}"'))
    first = next(it2)
    assert isinstance(first, str) and first == "a", f"case2: Expected first 'a' string, got {first!r} ({type(first)})"
    second = next(it2)
    assert isinstance(second, Interpolation), f"case2: Expected Interpolation second, got {type(second)}"
    drain_and_check_repeated_stop(it2, label="case2")
    print("case2_ok")

    # Case 3: Interpolation followed by a trailing string, to exercise the code
    # path that switches back to strings right before exhaustion.
    it3 = iter(eval('t"{1}b"'))
    first = next(it3)
    assert isinstance(first, Interpolation), f"case3: Expected Interpolation first, got {type(first)}"
    second = next(it3)
    assert isinstance(second, str) and second == "b", f"case3: Expected trailing 'b' string, got {second!r} ({type(second)})"
    drain_and_check_repeated_stop(it3, label="case3")
    print("case3_ok")

    # Case 4: Multiple interpolations, ensures exhaustion happens after all
    # interpolations and repeated next() remains safe.
    it4 = iter(eval('t"{1}{2}"'))
    first = next(it4)
    assert isinstance(first, Interpolation), f"case4: Expected Interpolation first, got {type(first)}"
    second = next(it4)
    assert isinstance(second, Interpolation), f"case4: Expected Interpolation second, got {type(second)}"
    drain_and_check_repeated_stop(it4, label="case4")
    print("case4_ok")
"""

rc, out, err = assert_python_ok('-c', code)

# Validate subprocess execution
assert rc == 0, f"Expected return code 0, got: {rc}"
assert not err, f"Expected no stderr, got: {err}"

# If skipped, ensure skip message appears and don't require markers
if b"SKIP" in out:
    # Skip is acceptable on interpreters without template strings support
    assert b"template strings" in out or b"templatelib" in out, f"Unexpected SKIP reason: {out!r}"
else:
    # Ensure all cases executed successfully
    expected_markers = [b'case1_ok', b'case2_ok', b'case3_ok', b'case4_ok']
    for marker in expected_markers:
        assert marker in out, f"Missing marker {marker!r} in stdout. Got: {out!r}"
