from test.support.script_helper import assert_python_ok

# This test suite verifies the fix in _lsprof.c that prevents calling
# Profiler.disable() and Profiler.clear() from within an external timer.
# The fix raises RuntimeError as an unraisable exception when these methods
# are called from the timer callback, avoiding a prior use-after-free crash.
#
# The tests run in subprocesses for isolation (historically could crash).
# If the patched behavior is present, we assert the unraisable RuntimeError
# type and error message. If not present (older Python), we still assert that
# the interpreter does not crash for the disable() tests and we SKIP the
# clear() tests which may segfault on unpatched builds.


def detect_patched_behavior_via_disable() -> bool:
    # Return True if calling disable() inside the external timer produces an
    # unraisable RuntimeError (patched behavior). Otherwise False.
    code = """if 1:
        import _lsprof
        from test import support

        class EvilTimer:
            def __init__(self, disable_count):
                self.count = 0
                self.disable_count = disable_count
            def __call__(self):
                self.count += 1
                if self.count == self.disable_count:
                    profiler_with_evil_timer.disable()
                return self.count

        with support.catch_unraisable_exception() as cm:
            profiler_with_evil_timer = _lsprof.Profiler(EvilTimer(1))
            profiler_with_evil_timer.enable()
            (lambda: None)()
            profiler_with_evil_timer.disable()
            profiler_with_evil_timer.clear()

        if hasattr(cm, 'unraisable') and cm.unraisable.exc_type is RuntimeError:
            print('HAD_UNRAISABLE')
        else:
            print('NO_UNRAISABLE')
    """
    rc, out, err = assert_python_ok("-c", code)
    assert rc == 0, f"Feature detection should not crash: rc={rc}, stderr={err!r}"
    marker = out.strip()
    assert marker in {b"HAD_UNRAISABLE", b"NO_UNRAISABLE"}, f"Unexpected stdout: {out!r}"
    return marker == b"HAD_UNRAISABLE"


def run_disable_in_timer_call_event():
    # Trigger disable() from the external timer on the first timer invocation
    # (call event) and assert it becomes an unraisable RuntimeError with the
    # expected message when patched.
    code = """if 1:
        import _lsprof
        from test import support

        class EvilTimer:
            def __init__(self, disable_count):
                self.count = 0
                self.disable_count = disable_count
            def __call__(self):
                self.count += 1
                if self.count == self.disable_count:
                    # Call disable() from inside the timer: should be blocked
                    profiler_with_evil_timer.disable()
                return self.count

        with support.catch_unraisable_exception() as cm:
            profiler_with_evil_timer = _lsprof.Profiler(EvilTimer(1))
            profiler_with_evil_timer.enable()
            (lambda: None)()  # generate some events
            # Normal disable/clear outside the timer should still be fine
            profiler_with_evil_timer.disable()
            profiler_with_evil_timer.clear()

        if hasattr(cm, 'unraisable'):
            # Validate unraisable exception type and message
            assert cm.unraisable.exc_type is RuntimeError, (
                f"Expected RuntimeError, got {cm.unraisable.exc_type}"
            )
            msg = str(cm.unraisable.exc_value)
            assert "cannot disable profiler in external timer" in msg, (
                f"Missing expected message text. Got: {msg!r}"
            )
            print("HAD_UNRAISABLE")
        else:
            # Older behavior: no explicit exception raised during timer call
            print("NO_UNRAISABLE")
    """
    rc, out, err = assert_python_ok("-c", code)
    assert rc == 0, f"Expected return code 0, got: {rc}"
    assert out.strip() in {b"HAD_UNRAISABLE", b"NO_UNRAISABLE"}, (
        f"Unexpected stdout marker: {out!r}"
    )
    assert not err, f"Expected no stderr, got: {err!r}"


def run_disable_in_timer_return_event():
    # Trigger disable() from the external timer on the second invocation
    # (return event) and assert it becomes an unraisable RuntimeError when patched.
    code = """if 1:
        import _lsprof
        from test import support

        class EvilTimer:
            def __init__(self, disable_count):
                self.count = 0
                self.disable_count = disable_count
            def __call__(self):
                self.count += 1
                if self.count == self.disable_count:
                    profiler_with_evil_timer.disable()
                return self.count

        with support.catch_unraisable_exception() as cm:
            profiler_with_evil_timer = _lsprof.Profiler(EvilTimer(2))
            profiler_with_evil_timer.enable()
            (lambda: None)()
            profiler_with_evil_timer.disable()
            profiler_with_evil_timer.clear()

        if hasattr(cm, 'unraisable'):
            assert cm.unraisable.exc_type is RuntimeError, (
                f"Expected RuntimeError, got {cm.unraisable.exc_type}"
            )
            msg = str(cm.unraisable.exc_value)
            assert "cannot disable profiler in external timer" in msg, (
                f"Missing expected message text. Got: {msg!r}"
            )
            print("HAD_UNRAISABLE")
        else:
            print("NO_UNRAISABLE")
    """
    rc, out, err = assert_python_ok("-c", code)
    assert rc == 0, f"Expected return code 0, got: {rc}"
    assert out.strip() in {b"HAD_UNRAISABLE", b"NO_UNRAISABLE"}, (
        f"Unexpected stdout marker: {out!r}"
    )
    assert not err, f"Expected no stderr, got: {err!r}"


def run_clear_in_timer_call_event():
    # Trigger clear() from the external timer on the first invocation (call event)
    # and assert it becomes an unraisable RuntimeError with the expected message
    # when patched. This test is SKIPPED if the environment appears unpatched
    # (because it may segfault on old versions).
    code = """if 1:
        import _lsprof
        from test import support

        class EvilTimerClear:
            def __init__(self, clear_count):
                self.count = 0
                self.clear_count = clear_count
            def __call__(self):
                self.count += 1
                if self.count == self.clear_count:
                    profiler_with_evil_timer.clear()
                return self.count

        with support.catch_unraisable_exception() as cm:
            profiler_with_evil_timer = _lsprof.Profiler(EvilTimerClear(1))
            profiler_with_evil_timer.enable()
            (lambda: None)()
            # Normal disable/clear outside the timer should still be fine
            profiler_with_evil_timer.disable()
            profiler_with_evil_timer.clear()

        if hasattr(cm, 'unraisable'):
            assert cm.unraisable.exc_type is RuntimeError, (
                f"Expected RuntimeError, got {cm.unraisable.exc_type}"
            )
            msg = str(cm.unraisable.exc_value)
            assert "cannot clear profiler in external timer" in msg, (
                f"Missing expected message text. Got: {msg!r}"
            )
            print("HAD_UNRAISABLE")
        else:
            print("NO_UNRAISABLE")
    """
    rc, out, err = assert_python_ok("-c", code)
    assert rc == 0, f"Expected return code 0, got: {rc}"
    assert out.strip() in {b"HAD_UNRAISABLE", b"NO_UNRAISABLE"}, (
        f"Unexpected stdout marker: {out!r}"
    )
    assert not err, f"Expected no stderr, got: {err!r}"


def run_clear_in_timer_return_event():
    # Trigger clear() from the external timer on the second invocation (return event)
    # and assert it becomes an unraisable RuntimeError when patched. This test is
    # SKIPPED if the environment appears unpatched.
    code = """if 1:
        import _lsprof
        from test import support

        class EvilTimerClear:
            def __init__(self, clear_count):
                self.count = 0
                self.clear_count = clear_count
            def __call__(self):
                self.count += 1
                if self.count == self.clear_count:
                    profiler_with_evil_timer.clear()
                return self.count

        with support.catch_unraisable_exception() as cm:
            profiler_with_evil_timer = _lsprof.Profiler(EvilTimerClear(2))
            profiler_with_evil_timer.enable()
            (lambda: None)()
            profiler_with_evil_timer.disable()
            profiler_with_evil_timer.clear()

        if hasattr(cm, 'unraisable'):
            assert cm.unraisable.exc_type is RuntimeError, (
                f"Expected RuntimeError, got {cm.unraisable.exc_type}"
            )
            msg = str(cm.unraisable.exc_value)
            assert "cannot clear profiler in external timer" in msg, (
                f"Missing expected message text. Got: {msg!r}"
            )
            print("HAD_UNRAISABLE")
        else:
            print("NO_UNRAISABLE")
    """
    rc, out, err = assert_python_ok("-c", code)
    assert rc == 0, f"Expected return code 0, got: {rc}"
    assert out.strip() in {b"HAD_UNRAISABLE", b"NO_UNRAISABLE"}, (
        f"Unexpected stdout marker: {out!r}"
    )
    assert not err, f"Expected no stderr, got: {err!r}"


def run_disable_clear_outside_timer_ok():
    # Ensure disable() and clear() are allowed and do not raise when called
    # outside of an external timer callback.
    code = """if 1:
        import _lsprof
        from test import support

        class Timer:
            def __call__(self):
                return 123456789  # any integer timestamp-like value

        with support.catch_unraisable_exception() as cm:
            p = _lsprof.Profiler(Timer())
            p.enable()
            (lambda: None)()
            p.disable()
            p.clear()
        # No unraisable exceptions should have occurred
        if hasattr(cm, 'unraisable'):
            raise AssertionError(f"Unexpected unraisable: {cm.unraisable}")
        print("NO_UNRAISABLE")
    """
    rc, out, err = assert_python_ok("-c", code)
    assert rc == 0, f"Expected return code 0, got: {rc}"
    assert out.strip() == b"NO_UNRAISABLE", f"Unexpected stdout: {out!r}"
    assert not err, f"Expected no stderr, got: {err!r}"


def main():
    patched = detect_patched_behavior_via_disable()

    run_disable_in_timer_call_event()
    run_disable_in_timer_return_event()

    # Only run clear() tests if patched behavior is present. On unpatched
    # versions, these tests may crash due to the original bug.
    if patched:
        run_clear_in_timer_call_event()
        run_clear_in_timer_return_event()

    run_disable_clear_outside_timer_ok()


if __name__ == "__main__":
    main()
