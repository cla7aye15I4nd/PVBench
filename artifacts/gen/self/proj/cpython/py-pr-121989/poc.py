import _lsprof


class EvilTimer:
    def __init__(self, disable_count):
        self.count = 0
        self.disable_count = disable_count

    def __call__(self):
        self.count += 1
        if self.count == self.disable_count:
            profiler_with_evil_timer.disable()
        return self.count


profiler_with_evil_timer = _lsprof.Profiler(EvilTimer(1))
profiler_with_evil_timer.enable()
(lambda: None)()
profiler_with_evil_timer.disable()
profiler_with_evil_timer.clear()

profiler_with_evil_timer = _lsprof.Profiler(EvilTimer(2))
profiler_with_evil_timer.enable()
(lambda: None)()
profiler_with_evil_timer.disable()
profiler_with_evil_timer.clear()
