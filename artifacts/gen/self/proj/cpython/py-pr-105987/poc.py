import _asyncio

class DummyLoop:
    pass

class DummyTask:
    pass

l = DummyLoop()
_asyncio._swap_current_task(l, DummyTask())
t = _asyncio._swap_current_task(l, None)