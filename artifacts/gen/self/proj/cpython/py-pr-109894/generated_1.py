import sys
from test.support.script_helper import assert_python_ok

# This test verifies the fix for GH-109894: a crash caused by an improperly
# initialized static MemoryError in subinterpreters.
#
# The patch ensures that:
# - Global exception objects (including preallocated MemoryError instances)
#   are initialized for all interpreters, not just the main interpreter.
# - The last_resort_memory_error has its .args set to the empty tuple, so that
#   printing or accessing it does not crash.
#
# We validate the fix by:
# 1) Triggering an unhandled MemoryError in a subinterpreter and asserting that
#    the process does not crash and that the exception is reported on stderr.
# 2) Triggering a MemoryError in a subinterpreter, catching it, and asserting
#    that basic properties (type name, args being a tuple and empty, str/repr)
#    are safe to use and produce expected output.


def test_unhandled_memoryerror_in_subinterp():
    # Use a very large repeat count to trigger MemoryError from within the subinterpreter.
    # Using sys.maxsize mirrors the reference and is a reliable trigger across platforms.
    big_n = sys.maxsize
    code = f"""if 1:
    import _testcapi
    # This should raise MemoryError inside the subinterpreter and be printed to stderr
    _testcapi.run_in_subinterp("[0]*{big_n}")
    # If the subinterpreter crashed, we won't reach here; assert_python_ok will fail.
    print("DONE")
"""
    rc, out, err = assert_python_ok('-c', code)
    assert rc == 0, f"Expected return code 0, got: {rc}"
    assert b'MemoryError' in err, f"Expected 'MemoryError' in stderr, got: {err}"
    assert b'DONE' in out, f"Expected 'DONE' in stdout to confirm normal return, got: {out}"


def test_caught_memoryerror_properties_in_subinterp():
    big_n = sys.maxsize
    # Build the subinterpreter code that catches MemoryError and prints properties
    sub_code = f"""if 1:
        try:
            _ = [0]*{big_n}
        except MemoryError as e:
            # Validate basic properties of the exception object are safe to access
            print(type(e).__name__)
            print(isinstance(e.args, tuple))
            print(len(e.args))
            # Ensure str() and repr() are safe and have expected shapes
            print("STR:", str(e))
            print("REPR:", repr(e))
    """

    code = f"""if 1:
    import _testcapi
    _testcapi.run_in_subinterp({sub_code!r})
"""

    rc, out, err = assert_python_ok('-c', code)
    assert rc == 0, f"Expected return code 0, got: {rc}"
    # No unhandled exception should occur in the subinterpreter for this test
    assert not err, f"Expected no stderr, got: {err}"

    # Parse stdout lines
    lines = out.decode().splitlines()
    # Expect exactly these 5 lines in order
    # 1: exception type name
    # 2: isinstance(e.args, tuple)
    # 3: len(e.args)
    # 4: 'STR: ' followed by the (usually empty) string form
    # 5: 'REPR: MemoryError()'
    assert len(lines) >= 5, f"Expected at least 5 lines of output, got {len(lines)}: {lines!r}"

    assert lines[0] == 'MemoryError', f"Expected 'MemoryError' type name, got: {lines[0]!r}"
    assert lines[1] == 'True', f"Expected 'True' for isinstance(e.args, tuple), got: {lines[1]!r}"
    assert lines[2] == '0', f"Expected '0' for len(e.args), got: {lines[2]!r}"
    assert lines[3] == 'STR: ', f"Expected 'STR: ' (empty message), got: {lines[3]!r}"
    assert lines[4] == 'REPR: MemoryError()', f"Expected 'REPR: MemoryError()', got: {lines[4]!r}"


if __name__ == '__main__':
    test_unhandled_memoryerror_in_subinterp()
    test_caught_memoryerror_properties_in_subinterp()
    print('OK')
