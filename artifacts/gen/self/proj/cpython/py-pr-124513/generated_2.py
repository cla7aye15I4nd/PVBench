# Self-contained test verifying FrameLocalsProxy constructor validations and crash fix
# The patch adds argument/type/kw checks to framelocalsproxy_new in CPython.

import sys

# Obtain the FrameLocalsProxy type from a real frame locals mapping
FrameLocalsProxy = type([sys._getframe().f_locals for _ in range(1)][0])


def have_framelocalsproxy_type():
    return FrameLocalsProxy.__name__ == 'FrameLocalsProxy'


def make_frame():
    # Create a frame with known locals
    x = 1
    y = 2
    return sys._getframe()


def test_successful_construction_and_contents():
    # Ensure a valid frame argument constructs correctly and exposes locals
    f = make_frame()
    proxy = FrameLocalsProxy(f)
    expected = {'x': 1, 'y': 2}
    # The proxy should compare equal to the expected locals mapping
    assert dict(proxy) == expected, (
        f"Expected locals {expected}, got {dict(proxy)}")


def test_argument_count_checks():
    # 0 positional arguments -> TypeError with specific message
    try:
        FrameLocalsProxy()
        assert False, "Expected TypeError for missing argument"
    except TypeError as e:
        msg = str(e)
        assert 'expected 1 argument' in msg, (
            f"Missing-arg TypeError message should mention 'expected 1 argument', got: {msg}")
        assert 'got 0' in msg, (
            f"Missing-arg TypeError message should mention 'got 0', got: {msg}")

    # Too many positional arguments -> TypeError with the count in message
    try:
        FrameLocalsProxy(sys._getframe(), 1)
        assert False, "Expected TypeError for too many arguments"
    except TypeError as e:
        msg = str(e)
        assert 'expected 1 argument' in msg and 'got 2' in msg, (
            f"Too-many-args message should mention 'expected 1 argument' and 'got 2', got: {msg}")

    try:
        FrameLocalsProxy(sys._getframe(), 1, 2)
        assert False, "Expected TypeError for too many arguments"
    except TypeError as e:
        msg = str(e)
        assert 'expected 1 argument' in msg and 'got 3' in msg, (
            f"Too-many-args message should mention 'expected 1 argument' and 'got 3', got: {msg}")


def test_type_check_for_frame_argument():
    # Wrong type should raise TypeError with a helpful message
    try:
        FrameLocalsProxy(123)
        assert False, "Expected TypeError for non-frame argument (int)"
    except TypeError as e:
        msg = str(e)
        assert 'expect frame' in msg, (
            f"Wrong-type TypeError should mention 'expect frame', got: {msg}")
        # The message should include the offending type name
        assert 'int' in msg, f"Message should mention 'int', got: {msg}"

    try:
        FrameLocalsProxy(None)
        assert False, "Expected TypeError for non-frame argument (None)"
    except TypeError as e:
        msg = str(e)
        assert 'expect frame' in msg, (
            f"Wrong-type TypeError should mention 'expect frame', got: {msg}")
        assert 'NoneType' in msg, f"Message should mention 'NoneType', got: {msg}"


def test_no_keyword_arguments_allowed():
    # Keywords only: implementation first checks positional count, so error may
    # be about argument count or keywords; accept either but TypeError must be raised
    try:
        FrameLocalsProxy(frame=sys._getframe())
        assert False, "Expected TypeError when using keyword-only argument"
    except TypeError as e:
        msg = str(e)
        assert ('expected 1 argument' in msg) or ('takes no keyword' in msg), (
            f"Keyword-only error should mention arg count or no keywords, got: {msg}")

    # Both positional and keyword: should specifically reject keywords
    try:
        FrameLocalsProxy(sys._getframe(), frame=sys._getframe())
        assert False, "Expected TypeError when passing any keyword arguments"
    except TypeError as e:
        msg = str(e)
        assert 'takes no keyword' in msg, (
            f"Expected message to mention no keyword arguments, got: {msg}")


def test_no_crash_in_subprocess_for_missing_argument():
    # The original bug was a crash when calling the constructor with wrong args.
    # Verify in a subprocess that calling with 0 args raises cleanly and does not crash.
    from test.support.script_helper import assert_python_ok

    code = """if 1:
    import sys
    FrameLocalsProxy = type([sys._getframe().f_locals for _ in range(1)][0])
    if FrameLocalsProxy.__name__ != 'FrameLocalsProxy':
        print('SKIP-NoFrameLocalsProxy')
    else:
        try:
            FrameLocalsProxy()
        except TypeError as e:
            # Print a simple marker so the parent can assert success
            print('OK-no-crash')
        else:
            # If no error is raised, that's unexpected for this call
            print('UNEXPECTED')
    """
    rc, out, err = assert_python_ok('-c', code)
    assert rc == 0, f"Expected return code 0, got: {rc}"
    # Accept either skip or the OK marker
    assert (b'OK-no-crash' in out) or (b'SKIP-NoFrameLocalsProxy' in out), (
        f"Expected 'OK-no-crash' or skip marker in stdout, got: {out!r}")
    assert not err, f"Expected no stderr, got: {err!r}"


if __name__ == '__main__':
    if not have_framelocalsproxy_type():
        # Older/intermediate builds may not expose FrameLocalsProxy; skip gracefully.
        print('skipped: FrameLocalsProxy not available')
        sys.exit(0)

    # Run tests
    test_successful_construction_and_contents()
    test_argument_count_checks()
    test_type_check_for_frame_argument()
    test_no_keyword_arguments_allowed()
    test_no_crash_in_subprocess_for_missing_argument()
    # If we reach here, all tests passed
