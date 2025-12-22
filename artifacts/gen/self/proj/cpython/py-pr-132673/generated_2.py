from ctypes import (
    Structure, LittleEndianStructure, BigEndianStructure,
    c_ubyte, alignment
)
from test.support.script_helper import assert_python_ok


def test_no_crash_zero_align_no_fields_subprocess():
    """Ensure that using _align_ = 0 and _fields_ = [] does not crash the interpreter.

    This specifically targets the bug fixed in stgdict.c where total_align could
    become 0 and lead to a crash during size alignment calculation. We run in a
    subprocess for isolation, and also assert resulting alignment is 1.
    """
    code = """if 1:
        from ctypes import Structure, LittleEndianStructure, BigEndianStructure, alignment

        for base in (Structure, LittleEndianStructure, BigEndianStructure):
            class MyStructure(base):
                _align_ = 0
                _fields_ = []

            # Alignment must be 1 and object creation should not crash
            assert alignment(MyStructure) == 1, f"Expected alignment 1 for {base.__name__}, got {alignment(MyStructure)}"
            assert alignment(MyStructure()) == 1, f"Expected alignment 1 for {base.__name__}(), got {alignment(MyStructure())}"

        print('OK')
    """
    rc, out, err = assert_python_ok('-c', code)
    assert rc == 0, f"Expected return code 0, got: {rc}"
    assert out.strip() == b'OK', f"Expected 'OK' in stdout, got: {out!r}"
    assert not err, f"Expected no stderr, got: {err!r}"


essential_bases = (Structure, LittleEndianStructure, BigEndianStructure)


def test_zero_align_with_fields_alignment_one():
    """Setting _align_ = 0 should not force zero alignment even when fields exist."""
    for base in essential_bases:
        class S(base):
            _align_ = 0
            _fields_ = [("x", c_ubyte)]
        assert alignment(S) == 1, f"Expected alignment 1 for {base.__name__}, got {alignment(S)}"
        assert alignment(S()) == 1, f"Expected alignment 1 for {base.__name__}(), got {alignment(S())}"


if __name__ == '__main__':
    # Run the tests
    test_no_crash_zero_align_no_fields_subprocess()
    test_zero_align_with_fields_alignment_one()
    print('All tests passed.')
