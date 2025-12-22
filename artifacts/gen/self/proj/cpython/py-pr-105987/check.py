from test.support.script_helper import assert_python_ok

code = """if 1:
    from _asyncio import _swap_current_task, _set_running_loop

    class DummyTask:
        pass

    class DummyLoop:
        pass

    l = DummyLoop()
    _set_running_loop(l)
    _swap_current_task(l, DummyTask())
    t = _swap_current_task(l, None)
"""

rc, out, err = assert_python_ok("-c", code)
assert not err, f"Expected no stderr, got: {err}"
