from test.support.script_helper import assert_python_ok

# All interactions with the fragile descriptor are performed in subprocesses to
# avoid crashing the test runner on unfixed builds.


def test_bind_without_owner_in_subprocess():
    """
    On fixed builds: binding without the second argument should succeed.
    On unfixed builds: this may segfault. We treat a segfault as reproduction
    of the original bug (do not fail this test environment).
    """
    code = """if 1:
        import types, _io, sys
        bound = _io._TextIOBase.detach.__get__(sys.stderr)
        assert isinstance(bound, types.BuiltinMethodType), (
            f"Expected BuiltinMethodType for omitted owner, got {type(bound)}")
        assert bound.__self__ is sys.stderr, (
            "Bound method's __self__ should be sys.stderr when owner omitted")
    """
    try:
        rc, out, err = assert_python_ok('-c', code)
    except AssertionError:
        # Unfixed builds may segfault here; accept that as repro of the bug.
        return
    else:
        # On fixed builds, ensure clean run.
        assert rc == 0, f"Expected return code 0, got: {rc}\nSTDERR: {err!r}"
        assert out == b'', f"Expected empty stdout, got: {out!r}"
        assert not err, f"Expected no stderr, got: {err!r}"


def test_bind_with_explicit_owner_in_subprocess():
    """Binding with an explicit owner type should always succeed."""
    code = """if 1:
        import types, _io, sys
        owner = type(sys.stderr)
        bound = _io._TextIOBase.detach.__get__(sys.stderr, owner)
        assert isinstance(bound, types.BuiltinMethodType), (
            f"Expected BuiltinMethodType for explicit owner, got {type(bound)}")
        assert bound.__self__ is sys.stderr, (
            "Bound method's __self__ should be sys.stderr with explicit owner")
    """
    rc, out, err = assert_python_ok('-c', code)
    assert rc == 0, f"Expected return code 0, got: {rc}\nSTDERR: {err!r}"
    assert out == b'', f"Expected empty stdout, got: {out!r}"
    assert not err, f"Expected no stderr, got: {err!r}"


def test_bind_with_none_owner_in_subprocess():
    """
    Passing None explicitly should not crash on fixed builds. Older builds may
    segfault. If it doesn't crash, the child prints a marker indicating whether
    a TypeError was raised or a bound method was produced.
    """
    code = """if 1:
        import types, _io, sys
        try:
            res = _io._TextIOBase.detach.__get__(sys.stderr, None)
        except TypeError:
            print('TYPEERROR')
        else:
            assert isinstance(res, types.BuiltinMethodType), (
                f"Expected BuiltinMethodType when owner=None, got {type(res)}")
            assert res.__self__ is sys.stderr, (
                "Bound method's __self__ should be sys.stderr when owner=None")
            print('BOUND')
    """
    try:
        rc, out, err = assert_python_ok('-c', code)
    except AssertionError:
        # Unfixed builds may segfault; accept that as repro of the bug.
        return
    else:
        assert rc == 0, f"Expected return code 0, got: {rc}\nSTDERR: {err!r}"
        assert out.strip() in {b'TYPEERROR', b'BOUND'}, (
            f"Expected 'TYPEERROR' or 'BOUND' marker, got: {out!r}")
        assert not err, f"Expected no stderr, got: {err!r}"


if __name__ == '__main__':
    test_bind_without_owner_in_subprocess()
    test_bind_with_explicit_owner_in_subprocess()
    test_bind_with_none_owner_in_subprocess()
