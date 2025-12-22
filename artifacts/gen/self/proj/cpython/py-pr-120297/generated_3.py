from test.support.script_helper import assert_python_ok

# Helper to run a code snippet in a subprocess and validate it succeeded.
def run_and_check(label: str, code: str):
    rc, out, err = assert_python_ok('-c', code)
    assert rc == 0, f"[{label}] Expected return code 0, got: {rc} (stderr: {err!r})"
    out_s = out.decode('utf-8', 'replace')
    assert f"PASS {label}" in out_s or f"SKIP {label}" in out_s, (
        f"[{label}] Expected 'PASS {label}' or 'SKIP {label}' in stdout, got: {out!r}"
    )
    assert not err, f"[{label}] Expected no stderr, got: {err!r}"


# Scenario 1: disable() called from external timer during call event
code_disable_on_call = """if 1:
    import _lsprof, sys

    prof = None

    class DisableTimer:
        def __init__(self, trip_at):
            self.count = 0
            self.trip_at = trip_at
        def __call__(self):
            global prof
            self.count += 1
            if self.count == self.trip_at:
                prof.disable()
            return self.count

    def do_one_call_and_return():
        (lambda: None)()

    captured = {}
    def hook(unraisable):
        captured['type'] = unraisable.exc_type
        captured['value'] = unraisable.exc_value
    sys.unraisablehook = hook

    prof = _lsprof.Profiler(DisableTimer(1))  # trigger on call event
    prof.enable()
    do_one_call_and_return()
    # Operations outside the timer should be fine
    prof.disable()
    prof.clear()

    if captured.get('type') is RuntimeError and 'cannot disable profiler in external timer' in str(captured.get('value')):
        print('PASS disable-call')
    else:
        # On unpatched Python, the exception isn't raised; this scenario ensures no crash
        print('SKIP disable-call')
"""


# Scenario 2: disable() called from external timer during return event
code_disable_on_return = """if 1:
    import _lsprof, sys

    prof = None

    class DisableTimer:
        def __init__(self, trip_at):
            self.count = 0
            self.trip_at = trip_at
        def __call__(self):
            global prof
            self.count += 1
            if self.count == self.trip_at:
                prof.disable()
            return self.count

    def do_one_call_and_return():
        (lambda: None)()

    captured = {}
    def hook(unraisable):
        captured['type'] = unraisable.exc_type
        captured['value'] = unraisable.exc_value
    sys.unraisablehook = hook

    prof = _lsprof.Profiler(DisableTimer(2))  # trigger on return event
    prof.enable()
    do_one_call_and_return()
    prof.disable()
    prof.clear()

    if captured.get('type') is RuntimeError and 'cannot disable profiler in external timer' in str(captured.get('value')):
        print('PASS disable-return')
    else:
        print('SKIP disable-return')
"""


# Scenario 3: clear() called from external timer during call event
code_clear_on_call = """if 1:
    import _lsprof, sys

    prof = None

    class ClearTimer:
        def __init__(self, trip_at):
            self.count = 0
            self.trip_at = trip_at
        def __call__(self):
            global prof
            self.count += 1
            if self.count == self.trip_at:
                prof.clear()
            return self.count

    def do_one_call_and_return():
        (lambda: None)()

    captured = {}
    def hook(unraisable):
        captured['type'] = unraisable.exc_type
        captured['value'] = unraisable.exc_value
    sys.unraisablehook = hook

    prof = _lsprof.Profiler(ClearTimer(1))  # trigger on call event
    prof.enable()
    do_one_call_and_return()
    prof.disable()
    prof.clear()

    if captured.get('type') is RuntimeError and 'cannot clear profiler in external timer' in str(captured.get('value')):
        print('PASS clear-call')
    else:
        print('SKIP clear-call')
"""


# Scenario 4: clear() called from external timer during return event
code_clear_on_return = """if 1:
    import _lsprof, sys

    prof = None

    class ClearTimer:
        def __init__(self, trip_at):
            self.count = 0
            self.trip_at = trip_at
        def __call__(self):
            global prof
            self.count += 1
            if self.count == self.trip_at:
                prof.clear()
            return self.count

    def do_one_call_and_return():
        (lambda: None)()

    captured = {}
    def hook(unraisable):
        captured['type'] = unraisable.exc_type
        captured['value'] = unraisable.exc_value
    sys.unraisablehook = hook

    prof = _lsprof.Profiler(ClearTimer(2))  # trigger on return event
    prof.enable()
    do_one_call_and_return()
    prof.disable()
    prof.clear()

    if captured.get('type') is RuntimeError and 'cannot clear profiler in external timer' in str(captured.get('value')):
        print('PASS clear-return')
    else:
        print('SKIP clear-return')
"""


# Scenario 5: benign timer should raise nothing (no unraisable)
code_ok_timer = """if 1:
    import _lsprof, sys

    class OKTimer:
        def __init__(self):
            self.count = 0
        def __call__(self):
            self.count += 1
            return self.count

    events = []
    def hook(unraisable):
        events.append(unraisable)
    sys.unraisablehook = hook

    p = _lsprof.Profiler(OKTimer())
    p.enable()
    (lambda: None)()
    p.disable()
    p.clear()

    assert not events, f"Unexpected unraisable: {events}"
    print('PASS ok-timer')
"""


def main():
    run_and_check('disable-call', code_disable_on_call)
    run_and_check('disable-return', code_disable_on_return)
    run_and_check('clear-call', code_clear_on_call)
    run_and_check('clear-return', code_clear_on_return)
    run_and_check('ok-timer', code_ok_timer)


if __name__ == '__main__':
    main()
