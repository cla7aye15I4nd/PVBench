# Self-contained tests for ctypes _align_ handling with empty _fields_.
# This test verifies the fix for a crash when using _align_ = 0 and _fields_ = []
# in ctypes.Structure (and Union). The patch ensures total_align is treated as 1
# instead of 0 when there are no fields, preventing a division-by-zero.

from ctypes import (
    Structure, LittleEndianStructure, BigEndianStructure, Union,
    c_ubyte, alignment,
)
from test.support.script_helper import assert_python_ok


def test_no_crash_zero_align_empty_fields_in_subprocess():
    """
    Validate that defining classes with _align_ = 0 and _fields_ = [] does not crash
    and that their alignment is treated as 1. Run in a subprocess to guard against
    potential crashes in unfixed interpreters.
    """
    code = """if 1:
        from ctypes import Structure, LittleEndianStructure, BigEndianStructure, Union, alignment

        def check_base(base):
            class S(base):
                _align_ = 0
                _fields_ = []
            a_cls = alignment(S)
            a_inst = alignment(S())
            if a_cls == 1 and a_inst == 1:
                print("OK:", base.__name__, a_cls, a_inst)
            else:
                print("BAD:", base.__name__, a_cls, a_inst)

        for base in (Structure, LittleEndianStructure, BigEndianStructure):
            check_base(base)

        # Also verify Union separately
        check_base(Union)
    """
    rc, out, err = assert_python_ok('-c', code)
    assert rc == 0, f"Expected return code 0, got: {rc} with stderr: {err!r}"
    stdout = out.decode('utf-8', 'replace')
    assert not err, f"Expected no stderr, got: {err}"
    # Ensure there are four OK lines and no BAD lines; be flexible about base names
    lines = [ln for ln in stdout.strip().splitlines() if ln.startswith('OK:')]
    assert len(lines) == 4, f"Expected 4 OK lines, got {len(lines)}: {lines!r}; stdout: {stdout!r}"
    assert 'BAD:' not in stdout, f"Unexpected BAD line(s) in stdout: {stdout!r}"
    assert 'Union' in stdout, f"Expected Union to be checked; got stdout: {stdout!r}"


def test_zero_align_with_single_byte_field_alignment_is_one():
    """
    With _align_ = 0 and a single c_ubyte field, alignment should be 1
    for both class and instance across structures and unions.
    """
    for base in (Structure, LittleEndianStructure, BigEndianStructure, Union):
        class T(base):
            _align_ = 0
            _fields_ = [("x", c_ubyte)]
        a_cls = alignment(T)
        a_inst = alignment(T())
        assert a_cls == 1, (
            f"Expected alignment 1 for {base.__name__} class with c_ubyte field and _align_=0, got {a_cls}"
        )
        assert a_inst == 1, (
            f"Expected alignment 1 for {base.__name__} instance with c_ubyte field and _align_=0, got {a_inst}"
        )


if __name__ == '__main__':
    # Run tests
    test_no_crash_zero_align_empty_fields_in_subprocess()
    test_zero_align_with_single_byte_field_alignment_is_one()
    print('OK')
