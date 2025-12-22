from ctypes import (
    Structure, LittleEndianStructure, BigEndianStructure,
    c_ubyte, alignment
)


def test_negative_align():
    """Test that negative _align_ raises ValueError."""
    for base in (Structure, LittleEndianStructure, BigEndianStructure):
        try:
            class MyStructure(base):
                _align_ = -1
                _fields_ = []
            assert False, f"Expected ValueError for {base.__name__}"
        except ValueError as e:
            assert '_align_ must be a non-negative integer' in str(e)


def test_zero_align_no_fields():
    """Test _align_ = 0 with no fields has alignment 1."""
    for base in (Structure, LittleEndianStructure, BigEndianStructure):
        class MyStructure(base):
            _align_ = 0
            _fields_ = []

        assert alignment(MyStructure) == 1, \
            f"Expected alignment 1 for {base.__name__}, got {alignment(MyStructure)}"
        assert alignment(MyStructure()) == 1, \
            f"Expected alignment 1 for {base.__name__}(), got {alignment(MyStructure())}"


def test_zero_align_with_fields():
    """Test _align_ = 0 with fields has alignment 1."""
    for base in (Structure, LittleEndianStructure, BigEndianStructure):
        class MyStructure(base):
            _align_ = 0
            _fields_ = [
                ("x", c_ubyte),
            ]

        assert alignment(MyStructure) == 1, \
            f"Expected alignment 1 for {base.__name__}, got {alignment(MyStructure)}"
        assert alignment(MyStructure()) == 1, \
            f"Expected alignment 1 for {base.__name__}(), got {alignment(MyStructure())}"


if __name__ == '__main__':
    test_negative_align()
    test_zero_align_no_fields()
    test_zero_align_with_fields()
