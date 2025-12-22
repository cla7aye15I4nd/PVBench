from test.support.script_helper import assert_python_ok

# This test verifies the fix for a refcounting bug in _asyncio._swap_current_task
# where the previous task's reference was INCREFed after the dict entry was
# modified. That could lead to a crash when the previous task was only
# referenced by the internal dict because the dict operation would decref and
# potentially destroy the object before INCREF, leading to use-after-free.
#
# The tests below exercise two critical scenarios that previously could crash:
# 1) Deleting the current task when it is only referenced by the mapping
# 2) Replacing the current task with a new task when the previous one is only
#    referenced by the mapping
#
# We also assert the returned previous task values are as expected.

code = """if 1:
    import _asyncio

    # Define simple dummy classes to use as loop and task identifiers
    class DummyLoop:
        pass

    class DummyTask:
        pass

    # 1) Deleting an ephemeral current task: should not crash and should return the previous task
    l1 = DummyLoop()
    # Set current task to an ephemeral instance (only referenced by the mapping)
    _asyncio._swap_current_task(l1, DummyTask())
    # Now clear it; previously this could crash due to INCREF after deletion
    prev = _asyncio._swap_current_task(l1, None)
    assert isinstance(prev, DummyTask), f"Expected previous task to be DummyTask instance, got: {type(prev)}"

    # 2) Replacing an ephemeral current task with a new task: should not crash and should return the old task
    l2 = DummyLoop()
    _asyncio._swap_current_task(l2, DummyTask())  # Old task only referenced by the mapping
    new_task = DummyTask()
    prev2 = _asyncio._swap_current_task(l2, new_task)
    assert isinstance(prev2, DummyTask), f"Expected previous task to be DummyTask instance, got: {type(prev2)}"
    assert prev2 is not new_task, "Previous task should not be the newly set task"

    # Verify that the mapping now holds new_task by clearing it and inspecting the returned previous task
    last = _asyncio._swap_current_task(l2, None)
    assert last is new_task, "Expected returned previous task to be the task that was just set"

    # 3) Initial set on a fresh loop should return None as previous task
    l3 = DummyLoop()
    first_prev = _asyncio._swap_current_task(l3, DummyTask())
    assert first_prev is None, f"Expected previous task to be None on first set, got: {first_prev!r}"
"""

rc, out, err = assert_python_ok('-c', code)
assert rc == 0, f"Expected return code 0, got: {rc}"
# The script should not produce any output or errors
assert out == b'', f"Expected empty stdout, got: {out}"
assert not err, f"Expected no stderr, got: {err}"
