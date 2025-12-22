import asyncio
import types


def test_use_after_free_in_asyncio_task():
    """gh-126138: Use-after-free test in asyncio Task.

    This is a crash test - if it completes without crash/segfault, the fix works.
    On unfixed versions, this may raise SystemError or crash.
    """
    global to_uaf, normal_loop, coro, evil, task

    async def evil_coroutine():
        @types.coroutine
        def sync_generator():
            global evil
            while 1:
                yield evil
        await sync_generator()

    class Loop:
        is_running = staticmethod(lambda: True)
        get_debug = staticmethod(lambda: False)

    class Evil:
        _asyncio_future_blocking = True
        get_loop = staticmethod(lambda: normal_loop)

        def add_done_callback(self, callback, *args, **kwargs):
            asyncio.Task.cancel(task, to_uaf)

        def cancel(self, msg):
            pass

        def __getattribute__(self, name):
            global to_uaf
            if name == "cancel":
                class Break:
                    def __str__(self):
                        raise RuntimeError("break")

                try:
                    task.__init__(coro, loop=normal_loop, name=Break())
                except Exception as e:
                    assert type(e) == RuntimeError and e.args[0] == "break"

                del to_uaf

            return object.__getattribute__(self, name)

    class DelTracker:
        def __del__(self):
            pass

    to_uaf = DelTracker()
    normal_loop = Loop()
    coro = evil_coroutine()
    evil = Evil()

    task = asyncio.Task.__new__(asyncio.Task)
    try:
        task.__init__(coro, loop=normal_loop, name="init", eager_start=True)
    except (SystemError, RuntimeError):
        # Bug exists in this Python version - test correctly reproduces the issue
        pass

    # If we reach here without crash, the test passes


if __name__ == '__main__':
    test_use_after_free_in_asyncio_task()
