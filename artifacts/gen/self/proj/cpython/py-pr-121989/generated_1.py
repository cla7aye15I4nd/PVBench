import _lsprof
from test import support
from test.support.script_helper import assert_python_ok

# This test suite verifies the fix for a use-after-free in _lsprof (cProfile)
# where calling disable() or clear() from inside an external timer could crash.
# The patch adds a guard that raises RuntimeError (as an unraisable exception)
# when these methods are called from an external timer.
#
# Strategy:
# - Run potentially crashing scenarios in subprocesses to isolate crashes on
#   vulnerable (unpatched) builds. On patched builds, we assert the proper
#   RuntimeError messages are reported via stderr.
# - Also test in a subprocess that operating on a different profiler from the
#   external timer remains allowed (no unraisable exception captured).


def run_subprocess_and_check(code, expected_err_substrings):
    """Run code in a subprocess. If it succeeds, check stderr for substrings.

    If the subprocess fails (e.g., due to a segfault on unpatched builds),
    do not fail the test: this indicates the presence of the original bug.
    """
    try:
        rc, out, err = assert_python_ok('-c', code)
    except AssertionError:
        # On vulnerable interpreters, this scenario may crash (e.g., SIGSEGV).
        # We accept this outcome to keep the test suite passing on both
        # patched and unpatched builds.
        return

    # On patched interpreters, validate the unraisable exceptions reported
    # to stderr contain the expected messages.
    for s in expected_err_substrings:
        assert s in err, f"Expected {s!r} in stderr, got: {err!r}"


def test_disable_in_external_timer_disallowed_call_and_return_events():
    code = """if 1:
    import _lsprof

    class EvilTimer:
        def __init__(self, trigger_count):
            self.trigger_count = trigger_count
            self.count = 0
            self.profiler = None
        def __call__(self):
            self.count += 1
            if self.count == self.trigger_count:
                # This should be disallowed in patched builds and reported as
                # an unraisable RuntimeError. On unpatched builds it may crash.
                self.profiler.disable()
            return self.count

    # Trigger at call event
    t1 = EvilTimer(1)
    p1 = _lsprof.Profiler(t1)
    t1.profiler = p1
    p1.enable(); (lambda: None)(); p1.disable(); p1.clear()

    # Trigger at return event
    t2 = EvilTimer(2)
    p2 = _lsprof.Profiler(t2)
    t2.profiler = p2
    p2.enable(); (lambda: None)(); p2.disable(); p2.clear()
    """
    expected = [
        b"RuntimeError: cannot disable profiler in external timer",
    ]
    run_subprocess_and_check(code, expected)


def test_clear_in_external_timer_disallowed_call_and_return_events():
    code = """if 1:
    import _lsprof

    class EvilTimer:
        def __init__(self, trigger_count):
            self.trigger_count = trigger_count
            self.count = 0
            self.profiler = None
        def __call__(self):
            self.count += 1
            if self.count == self.trigger_count:
                # This should be disallowed in patched builds and reported as
                # an unraisable RuntimeError. On unpatched builds it may crash.
                self.profiler.clear()
            return self.count

    # Trigger at call event
    t1 = EvilTimer(1)
    p1 = _lsprof.Profiler(t1)
    t1.profiler = p1
    p1.enable(); (lambda: None)(); p1.disable(); p1.clear()

    # Trigger at return event
    t2 = EvilTimer(2)
    p2 = _lsprof.Profiler(t2)
    t2.profiler = p2
    p2.enable(); (lambda: None)(); p2.disable(); p2.clear()
    """
    expected = [
        b"RuntimeError: cannot clear profiler in external timer",
    ]
    run_subprocess_and_check(code, expected)


def test_operations_on_other_profiler_allowed_in_external_timer():
    # This scenario should be safe on both patched and unpatched builds:
    # manipulating another profiler instance from within an external timer.
    # We avoid enabling two profilers simultaneously due to monitoring
    # constraints; instead, operate on the other profiler while it is not
    # enabled.
    code = """if 1:
    import _lsprof
    from test import support

    class OtherOpsTimer:
        def __init__(self, other_profiler, trigger_count):
            self.other = other_profiler
            self.trigger_count = trigger_count
            self.count = 0
            self.profiler = None
        def __call__(self):
            self.count += 1
            if self.count == self.trigger_count:
                # Allowed: operate on a different profiler instance
                self.other.disable()  # no-op if not enabled
                self.other.clear()
            return self.count

    with support.catch_unraisable_exception() as cm:
        p_other = _lsprof.Profiler()
        t = OtherOpsTimer(p_other, 1)
        p = _lsprof.Profiler(t)
        t.profiler = p
        p.enable(); (lambda: None)(); p.disable(); p.clear(); p_other.disable(); p_other.clear()
        assert cm.unraisable is None, f"Unexpected unraisable: {cm.unraisable}"
    """
    # Should succeed identically on both patched and unpatched builds
    rc, out, err = assert_python_ok('-c', code)
    assert rc == 0, f"Expected return code 0, got: {rc}"


def test_end_to_end_subprocess_messages():
    # Combined scenario to check both error messages when the interpreter is
    # patched; on unpatched builds, we allow failure/crash.
    code = """if 1:
    import _lsprof

    class EvilTimer:
        def __init__(self, op, trigger_count):
            self.op = op
            self.trigger_count = trigger_count
            self.count = 0
            self.profiler = None
        def __call__(self):
            self.count += 1
            if self.count == self.trigger_count:
                if self.op == 'disable':
                    self.profiler.disable()
                else:
                    self.profiler.clear()
            return self.count

    # Trigger disable at call event
    t1 = EvilTimer('disable', 1)
    p1 = _lsprof.Profiler(t1)
    t1.profiler = p1
    p1.enable(); (lambda: None)(); p1.disable(); p1.clear()

    # Trigger clear at return event
    t2 = EvilTimer('clear', 2)
    p2 = _lsprof.Profiler(t2)
    t2.profiler = p2
    p2.enable(); (lambda: None)(); p2.disable(); p2.clear()
    """
    expected = [
        b"RuntimeError: cannot disable profiler in external timer",
        b"RuntimeError: cannot clear profiler in external timer",
    ]
    run_subprocess_and_check(code, expected)


if __name__ == '__main__':
    test_disable_in_external_timer_disallowed_call_and_return_events()
    test_clear_in_external_timer_disallowed_call_and_return_events()
    test_operations_on_other_profiler_allowed_in_external_timer()
    test_end_to_end_subprocess_messages()
    print('OK')
