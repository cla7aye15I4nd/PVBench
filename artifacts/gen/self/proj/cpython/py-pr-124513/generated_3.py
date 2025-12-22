import sys
from test.support.script_helper import assert_python_ok


def _get_FrameLocalsProxy_type():
    """Try to obtain the internal FrameLocalsProxy type.

    On some Python builds, f_locals of a function frame has a dedicated
    FrameLocalsProxy type. If not available, this may fall back to 'dict'.
    """
    def inner():
        # Use a function frame, not module frame
        a = 1  # ensure there is at least one local
        return sys._getframe().f_locals
    t = type(inner())
    if t is dict:
        # fallback: check current frame, but likely also dict at module level
        t = type(sys._getframe().f_locals)
    return t


FrameLocalsProxy = _get_FrameLocalsProxy_type()
HAVE_FRAMELOCALS_PROXY = (FrameLocalsProxy is not dict)


if not HAVE_FRAMELOCALS_PROXY:
    # Provide a clear skip message to aid debugging in environments without
    # FrameLocalsProxy exposure.
    print("SKIP: FrameLocalsProxy type not available (f_locals is dict)")


def test_no_args_does_not_crash_and_raises_typeerror_subprocess():
    """
    Historically, calling FrameLocalsProxy() with no arguments could crash
    because the constructor accessed args[0] without checking. The patch adds
    argument count validation. Use a subprocess to ensure no crash and that a
    TypeError is raised (caught inside the child process).
    """
    code = """if 1:
        import sys
        def _get_t():
            def inner():
                x = 1
                return sys._getframe().f_locals
            t = type(inner())
            if t is dict:
                t = type(sys._getframe().f_locals)
            return t
        T = _get_t()
        if T is dict:
            # Not available in this build; skip inside subprocess
            print('SKIP:NOARGS')
        else:
            try:
                T()  # no arguments; used to crash before the fix
            except TypeError as e:
                msg = str(e)
                # New message: "FrameLocalsProxy expected 1 argument, got 0"
                if "expected 1 argument" not in msg:
                    print("BAD_MSG:", msg)
                print("OK:NOARGS")
            else:
                raise AssertionError("Expected TypeError for no-arg constructor")
    """
    rc, out, err = assert_python_ok('-c', code)
    assert rc == 0, f"Expected return code 0, got: {rc}"
    # Either skipped or ok, but definitely no crash and no stderr
    assert (b"OK:NOARGS" in out) or (b"SKIP:NOARGS" in out), (
        f"Expected 'OK:NOARGS' or 'SKIP:NOARGS' in stdout, got: {out}")
    assert not err, f"Expected no stderr, got: {err}"


def make_frame():
    # Create a frame object whose locals are known
    x = 1
    y = 2
    return sys._getframe()


def test_valid_construction_and_mapping_behavior():
    if not HAVE_FRAMELOCALS_PROXY:
        return  # skip gracefully
    # Construct a proxy with a valid frame
    frame = make_frame()
    proxy = FrameLocalsProxy(frame)

    # It should behave like a mapping with the function's locals
    expected = {'x': 1, 'y': 2}
    # Check equality with a dict
    assert proxy == expected, f"Expected {expected}, got {proxy}"
    # Also check key membership and values explicitly
    for k, v in expected.items():
        assert k in proxy, f"Missing key {k} in proxy {proxy}"
        assert proxy[k] == v, f"For key {k}, expected {v}, got {proxy[k]}"


def test_constructor_argument_validation():
    if not HAVE_FRAMELOCALS_PROXY:
        return  # skip gracefully
    # 0 positional args -> TypeError with arity message
    try:
        FrameLocalsProxy()
        assert False, "Expected TypeError for 0 arguments"
    except TypeError as e:
        msg = str(e)
        assert "expected 1 argument" in msg, (
            f"Expected message to mention 'expected 1 argument', got: {msg}")

    # Too many positional args -> TypeError with arity message
    try:
        FrameLocalsProxy(sys._getframe(), 1)
        assert False, "Expected TypeError for too many arguments"
    except TypeError as e:
        msg = str(e)
        assert "expected 1 argument" in msg, (
            f"Expected message to mention 'expected 1 argument', got: {msg}")

    # Wrong type (non-frame) -> TypeError with type message
    try:
        FrameLocalsProxy(123)
        assert False, "Expected TypeError for wrong argument type"
    except TypeError as e:
        msg = str(e)
        # New error message mentions 'expect frame'
        assert "expect frame" in msg, (
            f"Expected message to mention 'expect frame', got: {msg}")

    # Keyword-only (no positional) -> TypeError with arity message according to the patch
    try:
        FrameLocalsProxy(frame=sys._getframe())
        assert False, "Expected TypeError for keyword-only invocation"
    except TypeError as e:
        msg = str(e)
        assert "expected 1 argument" in msg, (
            f"Expected message to mention 'expected 1 argument' for keyword-only call, got: {msg}")

    # Both positional and keyword supplied -> TypeError with keyword message
    try:
        FrameLocalsProxy(sys._getframe(), frame=sys._getframe())
        assert False, "Expected TypeError when mixing positional and keyword args"
    except TypeError as e:
        msg = str(e)
        assert "takes no keyword arguments" in msg, (
            f"Expected message to mention 'takes no keyword arguments', got: {msg}")


if __name__ == '__main__':
    test_no_args_does_not_crash_and_raises_typeerror_subprocess()
    test_valid_construction_and_mapping_behavior()
    test_constructor_argument_validation()
    print("All tests passed.")
