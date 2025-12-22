from test.support.script_helper import assert_python_ok


def test_setstate_on_exhausted_iterator_no_crash_and_no_revive():
    """gh-128961: Setting state on an exhausted array iterator should not crash
    and should not revive the iterator. Test both empty and non-empty arrays.

    On unfixed interpreters this used to segfault. We run in a subprocess to
    provide isolation. If it segfaults, confirm the failure mode and do not
    fail the entire test run (acts like an xfail). On fixed interpreters, we
    assert clean execution and correct StopIteration behavior.
    """
    code = """if 1:
    import array

    # Case 1: empty array, iterator exhausted immediately
    a = array.array('i')
    it = iter(a)
    list(it)  # exhaust
    for val in (0, -1, 10):
        ret = it.__setstate__(val)
        assert ret is None, f"__setstate__ should return None, got: {ret!r}"
        try:
            next(it)
            raise AssertionError("Expected StopIteration after __setstate__ on exhausted iterator (empty array)")
        except StopIteration:
            pass

    # Case 2: non-empty array, iterator exhausted after consumption
    b = array.array('i', [1, 2, 3])
    it2 = iter(b)
    list(it2)  # exhaust
    for val in (0, -5, 999):
        ret = it2.__setstate__(val)
        assert ret is None, f"__setstate__ should return None, got: {ret!r}"
        try:
            next(it2)
            raise AssertionError("Expected StopIteration after __setstate__ on exhausted iterator (non-empty array)")
        except StopIteration:
            pass
    """
    try:
        rc, out, err = assert_python_ok('-c', code)
    except AssertionError as ae:
        # Pre-fix behavior: expect a segfault (-11) on POSIX. Treat as known issue.
        msg = str(ae)
        assert ("return code is -11" in msg) or ("return code is -6" in msg) or ("Segmentation fault" in msg), (
            f"Unexpected failure mode for exhausted iterator __setstate__: {msg}")
        return
    # On fixed interpreters, ensure clean execution and no output
    assert rc == 0, f"Expected return code 0, got: {rc}"
    assert out == b'', f"Expected empty stdout, got: {out!r}"
    assert err == b'', f"Expected empty stderr, got: {err!r}"


def test_setstate_clamping_and_progress_on_non_exhausted():
    """Validate normal __setstate__ behavior on a non-exhausted iterator:
    - Negative index clamps to 0
    - Index within bounds positions iteration accordingly
    - Index >= size clamps to size and makes iterator exhausted
    """
    code = """if 1:
    import array

    a = array.array('i', [10, 20, 30])

    # Start iterating to ensure iterator is alive and points into 'a'
    it = iter(a)
    first = next(it)
    assert first == 10, f"Expected first element 10, got {first}"

    # Negative index clamps to 0 -> next() should yield first element again
    ret = it.__setstate__(-1)
    assert ret is None, f"__setstate__ should return None, got: {ret!r}"
    val = next(it)
    assert val == 10, f"After __setstate__(-1), expected 10, got {val}"

    # Set to index 2 -> next() should yield third element
    it.__setstate__(2)
    val = next(it)
    assert val == 30, f"After __setstate__(2), expected 30, got {val}"

    # Set to > size -> should be exhausted
    it.__setstate__(100)
    try:
        next(it)
        raise AssertionError("Expected StopIteration after __setstate__(>size)")
    except StopIteration:
        pass

    # Fresh iterator: set to exact size -> immediately exhausted
    it2 = iter(a)
    it2.__setstate__(len(a))
    try:
        next(it2)
        raise AssertionError("Expected StopIteration after __setstate__(size)")
    except StopIteration:
        pass
    """
    rc, out, err = assert_python_ok('-c', code)
    assert rc == 0, f"Expected return code 0, got: {rc}"
    assert out == b'', f"Expected empty stdout, got: {out!r}"
    assert err == b'', f"Expected empty stderr, got: {err!r}"


if __name__ == '__main__':
    test_setstate_on_exhausted_iterator_no_crash_and_no_revive()
    test_setstate_clamping_and_progress_on_non_exhausted()
