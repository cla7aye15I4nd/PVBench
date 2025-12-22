import sys
import subprocess

# This test verifies the fix for a use-after-free in _lsprof (cProfile) where
# calling profiler.disable() or profiler.clear() from within an external timer
# could previously crash. The patch prevents this by raising RuntimeError in
# the external timer context. Exceptions from the external timer are unraisable
# (routed to sys.unraisablehook), so child processes validate the exception via
# test.support.catch_unraisable_exception and print PASS markers.
#
# We run each scenario in a subprocess to isolate potential crashes on
# unpatched interpreters. If the interpreter is patched, the subprocesses should
# exit with rc == 0 and print the expected PASS markers. If unpatched, the
# subprocess may crash or fail; we avoid failing the main test process in that
# case, but still provide diagnostics.

CASES = [
    ("disable", 1, b"PASS disable call"),   # call event
    ("disable", 2, b"PASS disable return"), # return event
    ("clear",   1, b"PASS clear call"),     # call event
    ("clear",   2, b"PASS clear return"),   # return event
]


def indent_block(s: str, prefix: str = "    ") -> str:
    return "\n".join(prefix + line if line else prefix for line in s.splitlines())


def build_code(kind: str, trigger: int) -> str:
    msg = (
        "cannot disable profiler in external timer"
        if kind == "disable"
        else "cannot clear profiler in external timer"
    )
    label = f"{kind} {'call' if trigger == 1 else 'return'}"
    body_call = (
        "profiler.disable()" if kind == "disable" else "profiler.clear()"
    )
    block = f"""
import _lsprof
from test import support

# Global profiler reference used by timer callbacks
profiler = None

class EvilTimer:
    def __init__(self, trigger):
        self.c = 0
        self.trigger = trigger
    def __call__(self):
        global profiler
        self.c += 1
        if self.c == self.trigger:
            {body_call}
        return self.c

with support.catch_unraisable_exception() as cm:
    profiler = _lsprof.Profiler(EvilTimer({trigger}))
    profiler.enable()
    (lambda: None)()
    # Normal calls outside of the external timer should work
    profiler.disable()
    profiler.clear()
    assert cm.unraisable is not None, 'Expected an unraisable exception, got None'
    assert cm.unraisable.exc_type is RuntimeError, f"Expected RuntimeError, got {{cm.unraisable.exc_type}}"
    assert '{msg}' in str(cm.unraisable.exc_value), f"Unexpected message: {{cm.unraisable.exc_value!r}}"
print('PASS {label}')
"""
    return "if 1:\n" + indent_block(block)


def run_child(code: str):
    proc = subprocess.run([sys.executable, "-c", code], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return proc.returncode, proc.stdout, proc.stderr


def run_case(kind: str, trigger: int, expected_marker: bytes):
    code = build_code(kind, trigger)
    rc, out, err = run_child(code)
    # If the interpreter is patched, the child should succeed and print marker.
    if rc == 0:
        assert expected_marker in out, (
            f"Missing expected marker {expected_marker!r} in stdout: {out!r}"
        )
        assert not err, f"Expected no stderr, got: {err!r}"
    else:
        # On unpatched interpreters this scenario may crash or fail.
        print(
            f"Subprocess for {kind} with trigger={trigger} exited rc={rc};\n"
            f"stdout={out!r}\nstderr={err!r}\nThis likely indicates the bug is present.")


def main():
    for kind, trigger, marker in CASES:
        run_case(kind, trigger, marker)
    print('OK')


if __name__ == '__main__':
    main()
