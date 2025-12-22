# Self-contained test script for verifying MemoryError initialization in subinterpreters.
# It uses subprocess isolation since the original bug could crash the interpreter.

from test.support import script_helper


def test_unhandled_memoryerror_in_subinterp():
    # This test triggers a MemoryError inside a subinterpreter without catching it.
    # Prior to the fix, this could crash due to improperly initialized static MemoryError.
    code = """if 1:
        import _testcapi
        # Trigger a MemoryError in a subinterpreter; the exception should be printed to stderr
        _testcapi.run_in_subinterp("import sys; [0]*sys.maxsize")
    """
    rc, out, err = script_helper.assert_python_ok("-c", code)
    assert rc == 0, f"Expected return code 0, got: {rc}"
    assert b"MemoryError" in err, f"Expected 'MemoryError' in stderr, got: {err!r}"


def test_caught_memoryerror_has_empty_args_in_subinterp():
    # Ensure that when MemoryError is caught inside a subinterpreter, it has empty args
    # and converting it to str() does not crash and yields an empty string.
    code = """if 1:
        import _testcapi
        sub = '''\
import sys
try:
    [0]*sys.maxsize
except MemoryError as e:
    import sys
    # We expect empty args and empty string representation
    print("OK", len(e.args), str(e) == "")
'''
        _testcapi.run_in_subinterp(sub)
    """
    rc, out, err = script_helper.assert_python_ok("-c", code)
    assert rc == 0, f"Expected return code 0, got: {rc}"
    # Should not produce an unhandled traceback in stderr in this test
    assert b"Traceback" not in err, f"Did not expect traceback in stderr, got: {err!r}"
    assert b"OK 0 True" in out, f"Expected 'OK 0 True' in stdout, got: {out!r}"


def test_multiple_subinterpreters_preallocated_memerrors():
    # Run multiple subinterpreters to ensure each initializes MemoryError properly and
    # unhandled MemoryError in each does not crash and is reported.
    code = """if 1:
        import _testcapi
        src = "import sys; [0]*sys.maxsize"
        _testcapi.run_in_subinterp(src)
        _testcapi.run_in_subinterp(src)
        _testcapi.run_in_subinterp(src)
    """
    rc, out, err = script_helper.assert_python_ok("-c", code)
    assert rc == 0, f"Expected return code 0, got: {rc}"
    count = err.count(b"MemoryError")
    assert count >= 2, f"Expected at least two 'MemoryError' mentions in stderr, got {count}; stderr: {err!r}"


if __name__ == "__main__":
    test_unhandled_memoryerror_in_subinterp()
    test_caught_memoryerror_has_empty_args_in_subinterp()
    test_multiple_subinterpreters_preallocated_memerrors()
    # If we reach here without assertion failures, the tests pass.
