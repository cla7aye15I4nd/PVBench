# Comprehensive test for FrameLocalsProxy constructor argument validation and behavior
# This test is based on the provided poc.py and the patch which adds robust
# argument checking in framelocalsproxy_new (Objects/frameobject.c).
#
# The patch ensures:
# - Exactly 1 positional argument is required (a frame), otherwise TypeError with
#   message "FrameLocalsProxy expected 1 argument, got N".
# - The single positional argument must be a frame, otherwise TypeError with
#   message containing "expect frame, not <type>".
# - No keyword arguments are accepted: TypeError with message containing
#   "FrameLocalsProxy takes no keyword arguments".
#
# Some Python builds may not expose FrameLocalsProxy (e.g., f_locals is a plain dict).
# In that case, we detect the absence and skip the specific tests.

import sys
from test.support.script_helper import assert_python_ok


def get_FrameLocalsProxy_type():
    # Obtain the internal FrameLocalsProxy type from a real frame's f_locals
    return type([sys._getframe().f_locals for _ in range(1)][0])


FrameLocalsProxyType = get_FrameLocalsProxy_type()
FEATURE_AVAILABLE = (getattr(FrameLocalsProxyType, '__name__', '') == 'FrameLocalsProxy')


def test_type_name():
    if not FEATURE_AVAILABLE:
        # Feature not available in this interpreter; skip
        return
    assert FrameLocalsProxyType.__name__ == 'FrameLocalsProxy', (
        f"Unexpected type name: {FrameLocalsProxyType.__name__}")


def test_valid_construction_and_mapping_equality():
    if not FEATURE_AVAILABLE:
        return
    FrameLocalsProxy = FrameLocalsProxyType

    def make_frame():
        x = 1
        y = 2
        return sys._getframe()

    proxy = FrameLocalsProxy(make_frame())
    expected = {'x': 1, 'y': 2}
    assert proxy == expected, f"Expected {expected}, got {proxy}"


def test_no_args_raises_typeerror_no_crash_subprocess():
    if not FEATURE_AVAILABLE:
        return
    # Use subprocess isolation to ensure that older/buggy versions which might
    # crash (as demonstrated by the PoC) do not crash anymore and raise TypeError.
    code = """if 1:
        import sys
        FrameLocalsProxy = type([sys._getframe().f_locals for _ in range(1)][0])
        try:
            FrameLocalsProxy()  # no arguments: previously crashed
        except TypeError as e:
            # Print markers to stdout so the parent can assert on them
            print('TypeError:', e.__class__.__name__)
            if 'expected 1 argument' in str(e):
                print('msg_ok')
        else:
            raise AssertionError('Expected TypeError for no-arg FrameLocalsProxy()')
    """
    rc, out, err = assert_python_ok('-c', code)
    assert rc == 0, f"Expected return code 0, got: {rc}"
    assert b'TypeError: TypeError' in out, f"Expected TypeError marker in stdout, got: {out}"
    assert b'msg_ok' in out, f"Expected 'expected 1 argument' in error message, got: {out}"
    assert not err, f"Expected no stderr, got: {err}"


def test_argument_validation_messages():
    if not FEATURE_AVAILABLE:
        return
    FrameLocalsProxy = FrameLocalsProxyType

    # 1) No positional args (direct): TypeError, message mentions expected 1 argument
    try:
        FrameLocalsProxy()
        assert False, 'Expected TypeError for no positional arguments'
    except TypeError as e:
        msg = str(e)
        assert 'expected 1 argument' in msg, f"Unexpected message: {msg}"

    # 2) Too many positional args: TypeError, message mentions got 2
    try:
        FrameLocalsProxy(sys._getframe(), 1)
        assert False, 'Expected TypeError for too many positional arguments'
    except TypeError as e:
        msg = str(e)
        assert 'expected 1 argument' in msg and 'got 2' in msg, (
            f"Unexpected message for too many args: {msg}")

    # 3) Wrong type: TypeError, message mentions expect frame
    try:
        FrameLocalsProxy(123)
        assert False, 'Expected TypeError for wrong argument type'
    except TypeError as e:
        msg = str(e)
        assert 'expect frame' in msg, f"Unexpected message for wrong type: {msg}"

    # 4) Positional + keyword args: TypeError, message mentions no keyword arguments
    try:
        FrameLocalsProxy(sys._getframe(), frame=sys._getframe())
        assert False, 'Expected TypeError when keyword arguments are provided'
    except TypeError as e:
        msg = str(e)
        assert 'no keyword arguments' in msg, (
            f"Unexpected message for keyword arguments: {msg}")

    # 5) Keyword-only (no positional): still a TypeError, count check triggers first
    try:
        FrameLocalsProxy(frame=sys._getframe())
        assert False, 'Expected TypeError for keyword-only invocation'
    except TypeError as e:
        msg = str(e)
        # Arg count check runs before kwarg check in the patched code
        assert 'expected 1 argument' in msg, (
            f"Unexpected message for keyword-only call: {msg}")


if __name__ == '__main__':
    if not FEATURE_AVAILABLE:
        # Feature not available in this interpreter; skip with a friendly note
        print('FrameLocalsProxy not available; skipping tests.')
    else:
        test_type_name()
        test_valid_construction_and_mapping_equality()
        test_no_args_raises_typeerror_no_crash_subprocess()
        test_argument_validation_messages()
        # If we reach here without assertion failures, the test passes.
