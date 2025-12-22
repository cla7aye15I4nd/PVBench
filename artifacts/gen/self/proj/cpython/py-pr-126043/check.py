import asyncio


class ReachableCode(Exception):
    """Exception to raise to indicate that some code was reached."""
    pass


class SimpleEvilEventLoop(asyncio.base_events.BaseEventLoop):
    """Base class for UAF and other evil stuff requiring an evil event loop."""

    def get_debug(self):
        return False

    def __del__(self):
        if not self.is_closed() and not self.is_running():
            self.close()


def test_use_after_free_on_fut_callback_0_with_evil__getattribute__():
    """gh-125984: Use-after-free test with evil __getattribute__."""

    class EvilEventLoop(SimpleEvilEventLoop):
        def call_soon(self, *args, **kwargs):
            super().call_soon(*args, **kwargs)
            raise ReachableCode

        def __getattribute__(self, name):
            nonlocal fut_callback_0
            if name == 'call_soon':
                fut.remove_done_callback(fut_callback_0)
                del fut_callback_0
            return object.__getattribute__(self, name)

    evil_loop = EvilEventLoop()
    fut = asyncio.Future(loop=evil_loop)
    assert fut.get_loop() is evil_loop

    fut_callback_0 = lambda: ...
    fut.add_done_callback(fut_callback_0)

    try:
        fut.set_result("boom")
        assert False, "Expected ReachableCode exception"
    except ReachableCode:
        pass


def test_use_after_free_on_fut_context_0_with_evil__getattribute__():
    """gh-125984: Use-after-free test with evil __getattribute__ on context."""

    class EvilEventLoop(SimpleEvilEventLoop):
        def call_soon(self, *args, **kwargs):
            super().call_soon(*args, **kwargs)
            raise ReachableCode

        def __getattribute__(self, name):
            if name == 'call_soon':
                # resets the future's event loop
                fut.__init__(loop=SimpleEvilEventLoop())
            return object.__getattribute__(self, name)

    evil_loop = EvilEventLoop()
    fut = asyncio.Future(loop=evil_loop)
    assert fut.get_loop() is evil_loop

    fut_callback_0 = lambda: ...
    fut_context_0 = None  # Mock context
    fut.add_done_callback(fut_callback_0)
    del fut_context_0
    del fut_callback_0

    try:
        fut.set_result("boom")
        assert False, "Expected ReachableCode exception"
    except ReachableCode:
        pass


if __name__ == '__main__':
    test_use_after_free_on_fut_callback_0_with_evil__getattribute__()
    test_use_after_free_on_fut_context_0_with_evil__getattribute__()
