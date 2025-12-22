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

# Test at call event - in initContext in _lsprof.c
with support.catch_unraisable_exception() as cm:
    profiler_with_evil_timer = _lsprof.Profiler(EvilTimer(1))
    profiler_with_evil_timer.enable()
    (lambda: None)()
    profiler_with_evil_timer.disable()
    profiler_with_evil_timer.clear()
    assert cm.unraisable.exc_type == RuntimeError, f"Expected RuntimeError, got {cm.unraisable.exc_type}"

# Test at return event - in Stop in _lsprof.c
with support.catch_unraisable_exception() as cm:
    profiler_with_evil_timer = _lsprof.Profiler(EvilTimer(2))
    profiler_with_evil_timer.enable()
    (lambda: None)()
    profiler_with_evil_timer.disable()
    profiler_with_evil_timer.clear()
    assert cm.unraisable.exc_type == RuntimeError, f"Expected RuntimeError, got {cm.unraisable.exc_type}"
