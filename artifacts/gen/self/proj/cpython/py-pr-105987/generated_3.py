from test.support.script_helper import assert_python_ok

# This test ensures that _asyncio._swap_current_task properly handles reference
# counting of the previously-set task when replacing or deleting the current task
# for a given loop. The CPython patch moved an INCREF of the previous task before
# mutating the internal dict and added proper DECREF on the error path. Without
# this, replacing or deleting when the previous task is only referenced by the
# dict could lead to it being deallocated and a dangling pointer being returned,
# potentially causing a crash.

code = """if 1:
    import _asyncio, gc

    class DummyLoop:
        pass

    class DummyTask:
        pass

    l = DummyLoop()
    # Ensure the asyncio module knows about this loop (mirrors reference check)
    if hasattr(_asyncio, '_set_running_loop'):
        _asyncio._set_running_loop(l)

    # 1) Set a task so that it is held only by the internal mapping
    t = DummyTask()
    _asyncio._swap_current_task(l, t)  # store t; returns previous (likely None)
    del t  # Drop external reference; only the internal dict should hold it now
    gc.collect()

    # 2) Replace with a new task. Previously, this could decref the old task to 0
    # before returning it, causing a crash. Verify we get a live object back.
    prev1 = _asyncio._swap_current_task(l, DummyTask())
    assert isinstance(prev1, DummyTask), f"Expected previous to be DummyTask on replace, got: {type(prev1)}"
    # Interact with the object to ensure it's alive and usable
    prev1.marker = 'alive'
    assert getattr(prev1, 'marker', None) == 'alive', "Previous task object not usable after replace"

    # 3) Now the current task is the newly set DummyTask() from step 2, and there
    # are no external references to it. Deleting the mapping should return that
    # task and it must still be alive.
    gc.collect()
    prev2 = _asyncio._swap_current_task(l, None)
    assert isinstance(prev2, DummyTask), f"Expected previous to be DummyTask on delete, got: {type(prev2)}"
    prev2.alive2 = True
    assert getattr(prev2, 'alive2', False) is True, "Previous task after delete not usable"

    # 4) With mapping empty, setting a new task should return None as previous
    prev3 = _asyncio._swap_current_task(l, DummyTask())
    assert prev3 is None, f"Expected None when setting new task on empty mapping, got: {prev3!r}"
"""

rc, out, err = assert_python_ok("-c", code)
assert rc == 0, f"Expected return code 0, got: {rc}"
assert not err, f"Expected no stderr, got: {err}"
