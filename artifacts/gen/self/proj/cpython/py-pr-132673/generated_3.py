# Self-contained generated test verifying ctypes.Structure _align_ = 0 with empty _fields_
# does not crash and has alignment 1, as fixed in the referenced patch.

from ctypes import (
    Structure, LittleEndianStructure, BigEndianStructure,
    Union, c_ubyte, alignment
)

# Subprocess isolation is used for the crash scenario to ensure that if it
# regresses into a crash/segfault, it won't take down the test runner process.
from test.support.script_helper import assert_python_ok


def test_subprocess_zero_align_empty_fields_no_crash():
    """Ensure _align_ = 0 with empty _fields_ does not crash and yields alignment 1.

    This specifically targets the bug fixed where total_align became 0 for
    empty structures/unions and caused a crash during alignment rounding.
    """
    code = """if 1:
        from ctypes import Structure, LittleEndianStructure, BigEndianStructure, Union, alignment

        # Build classes with unique names for clear output
        tests = []
        for name, base in (
            ("Struct", Structure),
            ("LEStruct", LittleEndianStructure),
            ("BEStruct", BigEndianStructure),
        ):
            class S(base):
                _align_ = 0
                _fields_ = []
            S.__name__ = name
            tests.append((name, S))

        class U(Union):
            _align_ = 0
            _fields_ = []
        U.__name__ = "U"
        tests.append(("Union", U))

        # Print alignment for type and instance so the parent process can assert
        for label, cls in tests:
            print(f"{label}:type_align={alignment(cls)}")
            print(f"{label}:inst_align={alignment(cls())}")
    """
    rc, out, err = assert_python_ok('-c', code)
    assert rc == 0, f"Expected return code 0, got: {rc}"
    assert not err, f"Expected no stderr, got: {err!r}"

    # Each printed line should show alignment 1
    expected_labels = [
        b"Struct:type_align=1", b"Struct:inst_align=1",
        b"LEStruct:type_align=1", b"LEStruct:inst_align=1",
        b"BEStruct:type_align=1", b"BEStruct:inst_align=1",
        b"Union:type_align=1", b"Union:inst_align=1",
    ]
    for label in expected_labels:
        assert label in out, f"Missing expected output {label!r}. Full stdout: {out!r}"


def test_zero_align_no_fields_alignment_is_one():
    """_align_ = 0 with no fields yields alignment 1 for Structure variants."""
    for base in (Structure, LittleEndianStructure, BigEndianStructure):
        class My(base):
            _align_ = 0
            _fields_ = []
        a_type = alignment(My)
        a_inst = alignment(My())
        assert a_type == 1, (
            f"Expected alignment 1 for {base.__name__} type with _align_=0 and empty _fields_, got {a_type}")
        assert a_inst == 1, (
            f"Expected alignment 1 for {base.__name__} instance with _align_=0 and empty _fields_, got {a_inst}")


def test_zero_align_with_fields_byte_alignment_is_one():
    """_align_ = 0 with a byte field yields alignment 1 for Structure variants."""
    for base in (Structure, LittleEndianStructure, BigEndianStructure):
        class My(base):
            _align_ = 0
            _fields_ = [("x", c_ubyte)]
        a_type = alignment(My)
        a_inst = alignment(My())
        assert a_type == 1, (
            f"Expected alignment 1 for {base.__name__} type with _align_=0 and c_ubyte field, got {a_type}")
        assert a_inst == 1, (
            f"Expected alignment 1 for {base.__name__} instance with _align_=0 and c_ubyte field, got {a_inst}")


def test_union_zero_align_no_fields_alignment_is_one():
    """_align_ = 0 with no fields yields alignment 1 for Union."""
    class U(Union):
        _align_ = 0
        _fields_ = []
    a_type = alignment(U)
    a_inst = alignment(U())
    assert a_type == 1, f"Expected alignment 1 for Union type, got {a_type}"
    assert a_inst == 1, f"Expected alignment 1 for Union instance, got {a_inst}"


def test_union_zero_align_with_fields_byte_alignment_is_one():
    """_align_ = 0 with a byte field yields alignment 1 for Union."""
    class U(Union):
        _align_ = 0
        _fields_ = [("x", c_ubyte)]
    a_type = alignment(U)
    a_inst = alignment(U())
    assert a_type == 1, f"Expected alignment 1 for Union type with c_ubyte field, got {a_type}"
    assert a_inst == 1, f"Expected alignment 1 for Union instance with c_ubyte field, got {a_inst}"


if __name__ == '__main__':
    # Run the tests
    test_subprocess_zero_align_empty_fields_no_crash()
    test_zero_align_no_fields_alignment_is_one()
    test_zero_align_with_fields_byte_alignment_is_one()
    test_union_zero_align_no_fields_alignment_is_one()
    test_union_zero_align_with_fields_byte_alignment_is_one()
    
    print("All tests passed.")
