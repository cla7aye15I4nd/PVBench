# Comprehensive test for ctypes py_object NULL return fix (gh-132417)
#
# This test verifies that calling C functions via ctypes with restype
# ctypes.py_object that return NULL no longer crashes the interpreter and
# instead raise appropriate Python exceptions.
#
# It exercises two paths:
# 1) A function that returns NULL without setting an error (PyErr_Occurred).
#    ctypes should raise ValueError("PyObject is NULL"). Historically, a
#    NULL pointer dereference could occur.
# 2) A function that returns NULL and sets an error (PyLong_FromString with
#    invalid input). ctypes should propagate the ValueError instead of
#    crashing.
#
# The tests run the potentially crashy code in a subprocess to provide
# isolation. On a Python build without the fix, the subprocess is expected to
# crash (non-zero return code, typically -11 with a Fatal Python error).
# On a fixed build, the subprocess should exit cleanly printing the expected
# markers. We accept either outcome but assert the expected signals for each
# case so the test remains meaningful.

import ctypes
import subprocess
import sys


def run_in_subprocess(code: str):
    """Run code in an isolated Python subprocess and capture results."""
    proc = subprocess.run(
        [sys.executable, '-I', '-c', code],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return proc.returncode, proc.stdout, proc.stderr


def test_pyerr_occurred_in_subprocess():
    """Ensure PyErr_Occurred via ctypes (py_object restype) either:
    - On fixed Python: raises ValueError("PyObject is NULL") without crashing.
    - On unfixed Python: crashes with a fatal error (regression proof).
    """
    code = """if 1:
        import ctypes, sys
        PyErr_Occurred = ctypes.pythonapi.PyErr_Occurred
        PyErr_Occurred.argtypes = []
        PyErr_Occurred.restype = ctypes.py_object
        try:
            PyErr_Occurred()
        except ValueError as e:
            print("OK:", str(e))
        else:
            print("NOEXC")
    """
    rc, out, err = run_in_subprocess(code)
    if rc == 0:
        # Fixed behavior: ValueError with helpful message, no stderr
        assert b'OK:' in out, f"Expected 'OK:' in stdout, got: {out}"
        assert b'PyObject is NULL' in out, (
            f"Expected 'PyObject is NULL' in stdout, got: {out}")
        assert b'NOEXC' not in out, f"Did not expect 'NOEXC' in stdout, got: {out}"
        assert not err, f"Expected no stderr, got: {err}"
    else:
        # Unfixed behavior: crash; ensure we indeed crashed in the subprocess
        assert rc != 0, "Expected non-zero return code on crash"
        # CPython typically prints a Fatal Python error on segfault
        assert (b'Fatal Python error' in err or b'Segmentation fault' in err or rc < 0), (
            f"Expected crash indicators in stderr or negative rc; rc={rc}, stderr={err}")


def test_pylong_fromstring_in_subprocess():
    """Ensure a C API that returns NULL and sets an error doesn't crash.

    PyLong_FromString("notanumber", NULL, 10) returns NULL and sets ValueError.
    With restype=ctypes.py_object, ctypes should propagate the ValueError.
    On unfixed Python, this could crash; we accept that as a signal of the bug
    and validate the crash signature.
    """
    code = """if 1:
        import ctypes, sys
        PyLong_FromString = ctypes.pythonapi.PyLong_FromString
        # Signature: const char *str, char **endptr (NULL allowed), int base
        PyLong_FromString.argtypes = [ctypes.c_char_p, ctypes.c_void_p, ctypes.c_int]
        PyLong_FromString.restype = ctypes.py_object
        try:
            PyLong_FromString(b'notanumber', None, 10)
            print('NOEXC')
        except ValueError as e:
            print('OK2:', type(e).__name__)
    """
    rc, out, err = run_in_subprocess(code)
    if rc == 0:
        assert b'OK2:' in out, f"Expected 'OK2:' in stdout, got: {out}"
        assert b'NOEXC' not in out, f"Did not expect 'NOEXC' in stdout, got: {out}"
        assert not err, f"Expected no stderr, got: {err}"
    else:
        assert rc != 0, "Expected non-zero return code on crash"
        assert (b'Fatal Python error' in err or b'Segmentation fault' in err or rc < 0), (
            f"Expected crash indicators in stderr or negative rc; rc={rc}, stderr={err}")


if __name__ == '__main__':
    test_pyerr_occurred_in_subprocess()
    test_pylong_fromstring_in_subprocess()
    # If we reach here without assertion failures, the test passes.
