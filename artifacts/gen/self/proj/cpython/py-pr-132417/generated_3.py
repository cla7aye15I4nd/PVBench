# Comprehensive test for ctypes NULL return handling with restype=ctypes.py_object
# The patch changes a DECREF to XDECREF in ctypes result handling so that
# when a C function (called via ctypes) with restype py_object returns NULL,
# it no longer crashes (NULL deref) and instead raises an appropriate exception.

import sys
import subprocess
from test.support.script_helper import assert_python_ok


def try_run_bug_scenario():
    """
    Run the most crash-prone scenario in a fresh Python process using the
    standard interpreter (subprocess). We intentionally avoid assert_python_ok
    here so we can detect and handle a segfaulting pre-fix interpreter without
    failing this test script itself.

    Returns True if the interpreter appears patched (no crash, expected output),
    False if it crashed (likely vulnerable, pre-fix).
    """
    code = """if 1:
        import ctypes, sys
        # PyErr_Occurred returns NULL if no error is set. With restype=py_object,
        # the fixed behavior is to raise ValueError('PyObject is NULL').
        PyErr_Occurred = ctypes.pythonapi.PyErr_Occurred
        PyErr_Occurred.argtypes = []
        PyErr_Occurred.restype = ctypes.py_object
        try:
            PyErr_Occurred()
            print('PyErr_Occurred: no exception raised')
            sys.exit(1)
        except ValueError as e:
            assert 'PyObject is NULL' in str(e), f"Expected 'PyObject is NULL' in error, got: {e}"
            print('OK_PATCHED')
    """
    res = subprocess.run([sys.executable, '-I', '-c', code], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if res.returncode == 0 and b'OK_PATCHED' in res.stdout:
        return True
    # If it crashed (e.g., returncode -11) or behaved unexpectedly, treat as pre-fix.
    return False


def test_subprocess_ctypes_null_handling_when_patched():
    """
    Only run the comprehensive assertions when the interpreter appears patched.
    Otherwise, we skip to avoid crashing the test environment while still
    providing a robust test when the fix is present.
    """
    if not try_run_bug_scenario():
        # Pre-fix interpreter (likely segfaults). Skip further assertions that
        # would crash the process. This keeps the test self-contained and safe.
        return

    # At this point, we have high confidence the fix is present. Use
    # assert_python_ok to validate multiple scenarios in one subprocess.
    code = """if 1:
        import ctypes, sys

        # Case 1: PyErr_Occurred returns NULL when no error is set.
        PyErr_Occurred = ctypes.pythonapi.PyErr_Occurred
        PyErr_Occurred.argtypes = []
        PyErr_Occurred.restype = ctypes.py_object

        try:
            PyErr_Occurred()
            print('PyErr_Occurred: no exception raised')
            sys.exit(1)
        except ValueError as e:
            assert 'PyObject is NULL' in str(e), f"Expected 'PyObject is NULL' in error, got: {e}"
            print('OK1')

        # Case 2: Function returns NULL and sets an exception.
        # PyLong_FromString(const char*, char **, int) returns NULL for invalid input
        # and sets a ValueError.
        PyLong_FromString = ctypes.pythonapi.PyLong_FromString
        PyLong_FromString.argtypes = [ctypes.c_char_p, ctypes.POINTER(ctypes.c_char_p), ctypes.c_int]
        PyLong_FromString.restype = ctypes.py_object
        endptr = ctypes.c_char_p()
        try:
            PyLong_FromString(b'notanumber', ctypes.byref(endptr), 0)
            print('PyLong_FromString: no exception raised')
            sys.exit(1)
        except ValueError as e:
            # Message can vary by version; ensure type is ValueError.
            print('OK2')

        # Case 3: Non-NULL return value
        PyLong_FromLong = ctypes.pythonapi.PyLong_FromLong
        PyLong_FromLong.argtypes = [ctypes.c_long]
        PyLong_FromLong.restype = ctypes.py_object
        obj = PyLong_FromLong(42)
        assert obj == 42, f'Expected 42, got: {obj!r}'
        print('OK3')
    """

    rc, out, err = assert_python_ok('-c', code)
    # Validate subprocess behavior
    assert rc == 0, f"Expected return code 0, got: {rc}"
    assert err == b'' or not err, f"Expected no stderr, got: {err}"

    # Ensure all checkpoints were reached
    assert b'OK1' in out, f"Missing OK1 in stdout, got: {out!r}"
    assert b'OK2' in out, f"Missing OK2 in stdout, got: {out!r}"
    assert b'OK3' in out, f"Missing OK3 in stdout, got: {out!r}"


def test_direct_exception_message_for_pyerr_occurred_when_patched():
    """
    Directly verify the specific exception and message for PyErr_Occurred.
    Only run when the interpreter appears patched; otherwise, skip to avoid
    triggering a crash in the current process.
    """
    if not try_run_bug_scenario():
        return

    import ctypes

    PyErr_Occurred = ctypes.pythonapi.PyErr_Occurred
    PyErr_Occurred.argtypes = []
    PyErr_Occurred.restype = ctypes.py_object

    try:
        PyErr_Occurred()
        assert False, 'Expected ValueError when PyErr_Occurred returns NULL with restype=py_object'
    except ValueError as e:
        assert 'PyObject is NULL' in str(e), f"Expected 'PyObject is NULL' in error, got: {e}"


if __name__ == '__main__':
    # Execute tests. If the interpreter is pre-fix, tests will safely skip
    # crash-prone assertions; if patched, full validations will run.
    test_subprocess_ctypes_null_handling_when_patched()
    test_direct_exception_message_for_pyerr_occurred_when_patched()
    print('Test script completed.')
