from ctypes import Structure

class MyStructure(Structure):
    _align_ = 0
    _fields_ = []