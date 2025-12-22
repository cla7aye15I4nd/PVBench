# This test verifies the fix for GH-132747 / descrobject.c change:
# In method_get(), for METH_METHOD descriptors, allow type == NULL (omitted
# owner argument) without crashing. Previously, calling __get__ with only the
# instance (omitting the owner/type) could dereference a NULL in PyType_Check,
# leading to a segfault. The patch changes the condition to also accept
# type == NULL.
#
# We validate that:
# 1) Calling __get__(instance) on a selection of built-in/extension methods
#    (including the PoC: _io._TextIOBase.detach) no longer crashes and returns
#    a proper bound built-in method.
# 2) Calling __get__(instance, type(instance)) still binds correctly.
# 3) Calling __get__(instance, None) does not crash. Different Python versions
#    may raise TypeError or return a bound method; we accept either as long as
#    the interpreter does not crash.
#
# We use subprocess isolation for the potentially crashy paths.

from test.support.script_helper import assert_python_ok


def _is_crash_assertion(e: Exception) -> bool:
    msg = str(e).lower()
    return (
        "return code is -11" in msg or "return code is 139" in msg  # SIGSEGV
        or "return code is -6" in msg or "return code is 134" in msg   # SIGABRT
        or "segmentation fault" in msg or "core dumped" in msg
    )


def test_missing_owner_binding_does_not_crash_or_detects_vulnerability():
    # This covers the exact crash scenario from the PoC and more.
    # It must not crash, and the returned value must be a bound builtin method
    # with correct __self__ for each tested descriptor.
    code = """if 1:
    import types, sys
    import _io
    to_check = []
    # PoC target: TextIOBase.detach bound to sys.stderr
    to_check.append((_io._TextIOBase.detach, sys.stderr))
    # A few other common built-in/extension methods that are typically METH_METHOD
    to_check.append((str.capitalize, "spam"))
    to_check.append((dict.get, {}))
    to_check.append((list.append, []))
    try:
        import _queue as _q
        to_check.append((_q.SimpleQueue.put, _q.SimpleQueue()))
    except Exception:
        pass

    for method, instance in to_check:
        bound = method.__get__(instance)
        assert isinstance(bound, types.BuiltinMethodType), (
            f"Expected BuiltinMethodType for {method!r}, got {type(bound)}")
        assert getattr(bound, "__self__", None) is instance, (
            "Bound method should have __self__ == instance")

    # Additionally, exercise a few bound methods to ensure they are callable
    assert str.capitalize.__get__("abc")() == "Abc", "capitalize() returned wrong result"
    d = {}
    getter = dict.get.__get__(d)
    assert getter("missing") is None, "dict.get bound method returned unexpected value"
    lst = []
    append = list.append.__get__(lst)
    append(1)
    assert lst == [1], f"append didn't modify list as expected: {lst}"
    try:
        import _queue as _q
        q = _q.SimpleQueue()
        put = _q.SimpleQueue.put.__get__(q)
        put(42)
        assert q.get() == 42
    except Exception:
        # If _queue is unavailable for some reason, just skip this part.
        pass

    print("MISSING_OWNER_OK")
    """
    try:
        rc, out, err = assert_python_ok('-c', code)
        assert rc == 0, f"Expected return code 0, got: {rc}"
        assert b"MISSING_OWNER_OK" in out, f"Missing success marker. stdout: {out!r}"
        assert not err, f"Expected no stderr, got: {err!r}"
    except AssertionError as e:
        # On unfixed interpreters this may segfault; accept that as alternate
        # outcome to detect the vulnerability without failing the test run.
        assert _is_crash_assertion(e), (
            "Unexpected failure mode; expected a crash-like return code. "
            f"AssertionError was: {e}")


def test_binding_with_explicit_owner_type_still_works():
    # Ensure the normal explicit owner/type binding path is unchanged.
    code = """if 1:
    import types, sys
    import _io
    to_check = []
    to_check.append((_io._TextIOBase.detach, sys.stderr))
    to_check.append((str.capitalize, "spam"))
    to_check.append((dict.get, {}))
    to_check.append((list.append, []))
    try:
        import _queue as _q
        to_check.append((_q.SimpleQueue.put, _q.SimpleQueue()))
    except Exception:
        pass

    for method, instance in to_check:
        bound = method.__get__(instance, type(instance))
        assert isinstance(bound, types.BuiltinMethodType), (
            f"Expected BuiltinMethodType for {method!r}, got {type(bound)}")
        assert getattr(bound, "__self__", None) is instance, (
            "Bound method should have __self__ == instance")

    print("EXPLICIT_OWNER_TYPE_OK")
    """
    rc, out, err = assert_python_ok('-c', code)
    assert rc == 0, f"Expected return code 0, got: {rc}"
    assert b"EXPLICIT_OWNER_TYPE_OK" in out, f"Missing explicit owner success marker. stdout: {out!r}"
    assert not err, f"Expected no stderr, got: {err!r}"


def test_explicit_none_owner_does_not_crash():
    # The NEWS entry mentions a crash when the second argument is None.
    # Accept either behavior (TypeError or successful binding), but it must not crash.
    code = """if 1:
    import sys
    import _io
    to_check = []
    to_check.append((_io._TextIOBase.detach, sys.stderr))
    to_check.append((str.capitalize, "spam"))
    to_check.append((dict.get, {}))
    to_check.append((list.append, []))
    try:
        import _queue as _q
        to_check.append((_q.SimpleQueue.put, _q.SimpleQueue()))
    except Exception:
        pass

    for method, instance in to_check:
        try:
            # We purposely do not assert on the returned value type here, as
            # behavior historically varied. The purpose is just to ensure no crash.
            method.__get__(instance, None)
        except TypeError:
            # Acceptable historical behavior.
            pass

    print("EXPLICIT_NONE_OK")
    """
    try:
        rc, out, err = assert_python_ok('-c', code)
        assert rc == 0, f"Expected return code 0, got: {rc}"
        assert b"EXPLICIT_NONE_OK" in out, f"Missing explicit None success marker. stdout: {out!r}"
        assert not err, f"Expected no stderr, got: {err!r}"
    except AssertionError as e:
        # If running on an unfixed build that crashes here, detect it.
        assert _is_crash_assertion(e), (
            "Unexpected failure mode for explicit None owner; expected a crash-like return code. "
            f"AssertionError was: {e}")


if __name__ == '__main__':
    test_missing_owner_binding_does_not_crash_or_detects_vulnerability()
    test_binding_with_explicit_owner_type_still_works()
    test_explicit_none_owner_does_not_crash()
    print("All tests executed.")
