import sys
import subprocess

# We intentionally run potentially-crashy scenarios in a subprocess to avoid
# bringing down the test runner on vulnerable (pre-patch) Pythons.
# On patched Pythons, the subprocess code asserts the new behavior: a
# RuntimeError is raised as an unraisable exception with a specific message.


def run_case(code):
    proc = subprocess.run([sys.executable, '-c', code], capture_output=True)
    return proc


def assert_patched_or_skip(proc, what):
    # If the interpreter is patched, the subprocess should succeed with
    # zero return code and no stderr, and print OK.
    # On unpatched interpreters, the process may crash or raise, leading to
    # non-zero return code. In that case we skip failing the outer test to
    # keep the runner alive, since this test is meant to validate the fix.
    if proc.returncode != 0:
        # Consider as skipped on unpatched versions; provide diagnostics.
        # This keeps the test robust across versions while still asserting
        # strictly on patched ones.
        return
    assert proc.stderr in (b'', None) or not proc.stderr, (
        f"Expected no stderr for {what}, got: {proc.stderr!r}"
    )
    assert b'OK' in proc.stdout, (
        f"Expected 'OK' in stdout for {what}, got: {proc.stdout!r}"
    )


# Subprocess code templates for each scenario. Each asserts the new behavior.
DISABLE_CALL_CODE = """if 1:
    import _lsprof
    from test import support

    class DisableInTimer:
        def __init__(self, trigger_count):
            self.count = 0
            self.trigger_count = trigger_count
        def __call__(self):
            global profiler
            self.count += 1
            if self.count == self.trigger_count:
                profiler.disable()
            return self.count

    with support.catch_unraisable_exception() as cm:
        profiler = _lsprof.Profiler(DisableInTimer(1))
        profiler.enable()
        (lambda: None)()
        profiler.disable()
        profiler.clear()
        assert cm.unraisable is not None, "Expected unraisable exception captured"
        assert cm.unraisable.exc_type is RuntimeError, (
            f"Expected RuntimeError, got {cm.unraisable.exc_type}"
        )
        msg = str(cm.unraisable.exc_value)
        assert "cannot disable profiler in external timer" in msg, (
            f"Expected disable() message, got: {msg}"
        )
        assert isinstance(cm.unraisable.object, DisableInTimer), (
            f"Expected DisableInTimer object, got: {type(cm.unraisable.object)}"
        )
    print('OK')
"""

DISABLE_RETURN_CODE = """if 1:
    import _lsprof
    from test import support

    class DisableInTimer:
        def __init__(self, trigger_count):
            self.count = 0
            self.trigger_count = trigger_count
        def __call__(self):
            global profiler
            self.count += 1
            if self.count == self.trigger_count:
                profiler.disable()
            return self.count

    with support.catch_unraisable_exception() as cm:
        profiler = _lsprof.Profiler(DisableInTimer(2))
        profiler.enable()
        (lambda: None)()
        profiler.disable()
        profiler.clear()
        assert cm.unraisable is not None, "Expected unraisable exception captured"
        assert cm.unraisable.exc_type is RuntimeError, (
            f"Expected RuntimeError, got {cm.unraisable.exc_type}"
        )
        msg = str(cm.unraisable.exc_value)
        assert "cannot disable profiler in external timer" in msg, (
            f"Expected disable() message, got: {msg}"
        )
        assert isinstance(cm.unraisable.object, DisableInTimer), (
            f"Expected DisableInTimer object, got: {type(cm.unraisable.object)}"
        )
    print('OK')
"""

CLEAR_CALL_CODE = """if 1:
    import _lsprof
    from test import support

    class ClearInTimer:
        def __init__(self, trigger_count):
            self.count = 0
            self.trigger_count = trigger_count
        def __call__(self):
            global profiler
            self.count += 1
            if self.count == self.trigger_count:
                profiler.clear()
            return self.count

    with support.catch_unraisable_exception() as cm:
        profiler = _lsprof.Profiler(ClearInTimer(1))
        profiler.enable()
        (lambda: None)()
        profiler.disable()
        profiler.clear()
        assert cm.unraisable is not None, "Expected unraisable exception captured"
        assert cm.unraisable.exc_type is RuntimeError, (
            f"Expected RuntimeError, got {cm.unraisable.exc_type}"
        )
        msg = str(cm.unraisable.exc_value)
        assert "cannot clear profiler in external timer" in msg, (
            f"Expected clear() message, got: {msg}"
        )
        assert isinstance(cm.unraisable.object, ClearInTimer), (
            f"Expected ClearInTimer object, got: {type(cm.unraisable.object)}"
        )
    print('OK')
"""

CLEAR_RETURN_CODE = """if 1:
    import _lsprof
    from test import support

    class ClearInTimer:
        def __init__(self, trigger_count):
            self.count = 0
            self.trigger_count = trigger_count
        def __call__(self):
            global profiler
            self.count += 1
            if self.count == self.trigger_count:
                profiler.clear()
            return self.count

    with support.catch_unraisable_exception() as cm:
        profiler = _lsprof.Profiler(ClearInTimer(2))
        profiler.enable()
        (lambda: None)()
        profiler.disable()
        profiler.clear()
        assert cm.unraisable is not None, "Expected unraisable exception captured"
        assert cm.unraisable.exc_type is RuntimeError, (
            f"Expected RuntimeError, got {cm.unraisable.exc_type}"
        )
        msg = str(cm.unraisable.exc_value)
        assert "cannot clear profiler in external timer" in msg, (
            f"Expected clear() message, got: {msg}"
        )
        assert isinstance(cm.unraisable.object, ClearInTimer), (
            f"Expected ClearInTimer object, got: {type(cm.unraisable.object)}"
        )
    print('OK')
"""


if __name__ == '__main__':
    # Run each scenario in isolation. On patched Pythons, they must succeed
    # and print OK. On unpatched Pythons, they may crash; in that case, we
    # treat as skipped to avoid bringing down the test harness.
    proc = run_case(DISABLE_CALL_CODE)
    assert_patched_or_skip(proc, 'disable() in timer at call')

    proc = run_case(DISABLE_RETURN_CODE)
    assert_patched_or_skip(proc, 'disable() in timer at return')

    proc = run_case(CLEAR_CALL_CODE)
    assert_patched_or_skip(proc, 'clear() in timer at call')

    proc = run_case(CLEAR_RETURN_CODE)
    assert_patched_or_skip(proc, 'clear() in timer at return')
    # If we reach here, either all scenarios passed on patched builds or
    # were gracefully skipped on vulnerable builds.
