import ctypes
PyErr_Occurred = ctypes.pythonapi.PyErr_Occurred
PyErr_Occurred.argtypes = []
PyErr_Occurred.restype = ctypes.py_object
PyErr_Occurred()