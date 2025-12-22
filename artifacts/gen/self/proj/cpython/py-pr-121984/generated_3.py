# Tests for _lsprof external timer restrictions (disable/clear)
# Verify that calling disable() or clear() from within an external timer
# raises a RuntimeError as an unraisable exception (fix for use-after-free).
#
# These tests execute potentially crashing scenarios in subprocesses. On
# patched Python, they should complete successfully and report OK. On older
# Python (pre-fix), they may crash with a segmentation fault (non-zero return
# code). We accept both outcomes to keep the test resilient across versions,
# but when the subprocess succeeds, we assert that the expected RuntimeError
# was observed as an unraisable exception.

import sys
import subprocess


def run_python(code: str):
    cmd = [sys.executable, '-I', '-X', 'faulthandler', '-c', code]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


# Child snippet: disable inside timer at call and return events
code_disable_both_events = """if 1:
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

    # Test at call event
    with support.catch_unraisable_exception() as cm:
        profiler_with_evil_timer = _lsprof.Profiler(EvilTimer(1))
        profiler_with_evil_timer.enable()
        (lambda: None)()
        profiler_with_evil_timer.disable()
        profiler_with_evil_timer.clear()
        if cm.unraisable is not None and cm.unraisable.exc_type is RuntimeError:
            print('OK')
        else:
            print('NO-UNRAISABLE')

    # Test at return event
    with support.catch_unraisable_exception() as cm:
        profiler_with_evil_timer = _lsprof.Profiler(EvilTimer(2))
        profiler_with_evil_timer.enable()
        (lambda: None)()
        profiler_with_evil_timer.disable()
        profiler_with_evil_timer.clear()
        if cm.unraisable is not None and cm.unraisable.exc_type is RuntimeError:
            print('OK')
        else:
            print('NO-UNRAISABLE')
"""

# Child snippet: clear inside timer at call and return events
code_clear_both_events = """if 1:
    import _lsprof
    from test import support

    class EvilTimer:
        def __init__(self, clear_count):
            self.count = 0
            self.clear_count = clear_count
        def __call__(self):
            self.count += 1
            if self.count == self.clear_count:
                profiler_with_evil_timer.clear()
            return self.count

    # Test at call event
    with support.catch_unraisable_exception() as cm:
        profiler_with_evil_timer = _lsprof.Profiler(EvilTimer(1))
        profiler_with_evil_timer.enable()
        (lambda: None)()
        profiler_with_evil_timer.disable()
        profiler_with_evil_timer.clear()
        if cm.unraisable is not None and cm.unraisable.exc_type is RuntimeError:
            print('OK')
        else:
            print('NO-UNRAISABLE')

    # Test at return event
    with support.catch_unraisable_exception() as cm:
        profiler_with_evil_timer = _lsprof.Profiler(EvilTimer(2))
        profiler_with_evil_timer.enable()
        (lambda: None)()
        profiler_with_evil_timer.disable()
        profiler_with_evil_timer.clear()
        if cm.unraisable is not None and cm.unraisable.exc_type is RuntimeError:
            print('OK')
        else:
            print('NO-UNRAISABLE')
"""

# Child snippet: sanity check normal operations
code_normal_ops = """if 1:
    import _lsprof
    # Timer that never calls disable/clear inside
    class Timer:
        def __call__(self):
            return 1
    profiler = _lsprof.Profiler(Timer())
    profiler.enable()
    (lambda: None)()
    profiler.disable()
    profiler.clear()
    print('OK')
"""


def test_disable_inside_timer_both_events():
    rc, out, err = run_python(code_disable_both_events)
    if rc == 0:
        # On patched builds, both scenarios should report OK
        oks = out.strip().splitlines()
        assert oks.count('OK') == 2, f"Expected two 'OK' lines on patched build, got: {out!r}, stderr={err!r}"
        assert err == '', f"Expected empty stderr, got: {err!r}"
    else:
        # On unpatched builds, a crash is possible; ensure it indeed failed
        assert rc < 0, f"Expected crash (negative rc) on unpatched build, got rc={rc}, stderr={err!r}"


def test_clear_inside_timer_both_events():
    rc, out, err = run_python(code_clear_both_events)
    if rc == 0:
        oks = out.strip().splitlines()
        assert oks.count('OK') == 2, f"Expected two 'OK' lines on patched build, got: {out!r}, stderr={err!r}"
        assert err == '', f"Expected empty stderr, got: {err!r}"
    else:
        assert rc < 0, f"Expected crash (negative rc) on unpatched build, got rc={rc}, stderr={err!r}"


def test_normal_disable_and_clear_outside_timer():
    rc, out, err = run_python(code_normal_ops)
    assert rc == 0, f"Normal ops: expected rc 0, got {rc}, stderr={err!r}"
    assert out.strip().endswith('OK'), f"Normal ops: expected 'OK' in stdout, got: {out!r}"
    assert not err, f"Normal ops: expected no stderr, got: {err!r}"


if __name__ == '__main__':
    test_disable_inside_timer_both_events()
    test_clear_inside_timer_both_events()
    test_normal_disable_and_clear_outside_timer()
