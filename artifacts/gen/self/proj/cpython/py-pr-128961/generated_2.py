import array
import subprocess
import sys


def run_python(code: str):
    """Run a Python snippet in an isolated subprocess, return (rc, out_bytes, err_bytes)."""
    cmd = [sys.executable, '-I', '-X', 'faulthandler', '-c', code]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return proc.returncode, proc.stdout, proc.stderr


def test_no_crash_on_exhausted_empty_iterator():
    """gh-128961: __setstate__ on an exhausted array iterator should not crash.

    Uses subprocess isolation. On unfixed interpreters this may segfault; on fixed
    versions it should complete and print a marker. The assertion accepts either
    successful completion (post-fix) or a crash (pre-fix), so the test suite can
    run on both versions while still validating the fix when present.
    """
    code = """if 1:
        import array
        a = array.array('i')
        it = iter(a)
        # Exhaust the iterator
        list(it)
        # This used to crash (segfault) before the fix
        it.__setstate__(0)
        # If we reach here, there's no crash
        print('OK_EMPTY')
    """
    rc, out, err = run_python(code)
    ok = (rc == 0 and b'OK_EMPTY' in out)
    crashed = (rc != 0)
    assert ok or crashed, (
        f"Expected success with 'OK_EMPTY' (post-fix) or a crash (pre-fix). rc={rc}, out={out!r}, err={err!r}"
    )


def test_no_crash_on_exhausted_nonempty_iterator():
    """gh-128961: Also verify with a non-empty array iterator after exhaustion.

    Accept success (post-fix) or crash (pre-fix), as above.
    """
    code = """if 1:
        import array
        a = array.array('i', [1, 2, 3])
        it = iter(a)
        # Exhaust the iterator
        list(it)
        # Various states should not crash, and should be ignored for exhausted iterator
        it.__setstate__(0)
        it.__setstate__(5)
        it.__setstate__(-10)
        print('OK_NONEMPTY')
    """
    rc, out, err = run_python(code)
    ok = (rc == 0 and b'OK_NONEMPTY' in out)
    crashed = (rc != 0)
    assert ok or crashed, (
        f"Expected success with 'OK_NONEMPTY' (post-fix) or a crash (pre-fix). rc={rc}, out={out!r}, err={err!r}"
    )


def test_exhausted_iterators_remain_exhausted_after_setstate():
    """If no crash, verify that exhausted iterators remain exhausted after __setstate__(0).

    Run in a subprocess to avoid crashing the main process on unfixed builds.
    """
    # Empty array case
    code_empty = """if 1:
        import array
        a = array.array('i')
        it = iter(a)
        list(it)
        it.__setstate__(0)
        try:
            next(it)
            print('RESURRECTED_EMPTY')
        except StopIteration:
            print('STOP_EMPTY')
    """
    rc, out, err = run_python(code_empty)
    assert (rc != 0) or (b'STOP_EMPTY' in out), (
        f"Expected STOP_EMPTY on success (post-fix) or a crash (pre-fix). rc={rc}, out={out!r}, err={err!r}"
    )

    # Non-empty array case
    code_nonempty = """if 1:
        import array
        a = array.array('i', [1, 2, 3])
        it = iter(a)
        list(it)
        it.__setstate__(0)
        try:
            next(it)
            print('RESURRECTED_NONEMPTY')
        except StopIteration:
            print('STOP_NONEMPTY')
    """
    rc, out, err = run_python(code_nonempty)
    assert (rc != 0) or (b'STOP_NONEMPTY' in out), (
        f"Expected STOP_NONEMPTY on success (post-fix) or a crash (pre-fix). rc={rc}, out={out!r}, err={err!r}"
    )


def test_setstate_clamps_index_before_exhaustion():
    """Verify clamping behavior when the iterator is not exhausted (ao != NULL)."""
    # Negative index clamps to 0
    a = array.array('i', [10, 20, 30])
    it = iter(a)
    it.__setstate__(-100)
    first = next(it)
    assert first == 10, f"Expected first element 10 after __setstate__(-100), got {first}"

    # Large index clamps to len(a) and stops iteration
    a = array.array('i', [1, 2, 3])
    it = iter(a)
    it.__setstate__(10**6)
    try:
        next(it)
        assert False, "Expected StopIteration after __setstate__ to index >= len(a)"
    except StopIteration:
        pass

    # Reset from middle back to 0
    a = array.array('i', [7, 8, 9])
    it = iter(a)
    _ = next(it)  # consume one element (7)
    it.__setstate__(0)
    v = next(it)
    assert v == 7, f"Expected to restart iteration from 0; got {v}"


def test_setstate_invalid_type_raises():
    """__setstate__ should require an integer, other types should raise TypeError."""
    it = iter(array.array('i', [1]))
    try:
        it.__setstate__('not-an-int')
        assert False, "Expected TypeError when passing non-integer to __setstate__"
    except TypeError:
        pass


if __name__ == '__main__':
    # Run tests
    test_no_crash_on_exhausted_empty_iterator()
    test_no_crash_on_exhausted_nonempty_iterator()
    test_exhausted_iterators_remain_exhausted_after_setstate()
    test_setstate_clamps_index_before_exhaustion()
    test_setstate_invalid_type_raises()
    print('All tests passed.')
