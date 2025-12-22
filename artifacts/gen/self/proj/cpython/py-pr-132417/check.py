import ctypes

PyErr_Occurred = ctypes.pythonapi.PyErr_Occurred
PyErr_Occurred.argtypes = []
PyErr_Occurred.restype = ctypes.py_object

try:
    PyErr_Occurred()
    assert False, "Expected ValueError"
except ValueError as e:
    assert "PyObject is NULL" in str(e), f"Expected 'PyObject is NULL' in error, got: {e}"
