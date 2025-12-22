from test.support.script_helper import assert_python_ok

# This test verifies the fix for reference counting in _asyncio._swap_current_task.
# Prior to the fix, deleting or replacing the current task could decref the
# previous task to zero (free it) and then Py_INCREF it afterwards, causing a crash.
# The fix increments the reference to the previous task before mutating the dict,
# and decrefs on error. We validate that:
#  - No crash occurs when deleting or replacing the current task.
#  - The returned previous task is the exact object previously set.
#  - The returned previous task keeps the object alive even if the mapping was
#    deleted/replaced and other refs are removed.

code = """if 1:
    import _asyncio
    import weakref
    import gc

    swap = _asyncio._swap_current_task
    set_running = getattr(_asyncio, '_set_running_loop', None)

    class DummyTask:
        pass

    class DummyLoop:
        pass

    def test_set_then_delete_returns_prev_and_no_crash():
        l = DummyLoop()
        if set_running:
            set_running(l)

        # Initially no current task for this loop: setting returns None
        t1 = DummyTask()
        prev = swap(l, t1)
        assert prev is None, f"Expected None previous task on first set, got: {prev!r}"

        # Deleting should return t1; ensure no crash and object identity preserved
        wr = weakref.ref(t1)
        prev_del = swap(l, None)
        assert prev_del is not None, "Expected a previous task object on delete, got None"
        assert prev_del is t1, "Deleting current task should return the previously set task object"

        # Ensure the object remains alive at least via the returned reference
        assert wr() is t1, "Weakref should resolve before dropping other strong references"
        del t1
        gc.collect()
        assert wr() is prev_del, (
            "Previous task should remain alive after deletion via the returned reference"
        )

        if set_running:
            set_running(None)

    def test_replace_returns_prev_and_no_crash():
        l = DummyLoop()
        if set_running:
            set_running(l)

        # Set initial task
        t1 = DummyTask()
        prev = swap(l, t1)
        assert prev is None, f"Expected None previous task on first set, got: {prev!r}"

        # Replace with a new task and verify the previous is returned and alive
        t2 = DummyTask()
        wr1 = weakref.ref(t1)
        prev_replace = swap(l, t2)
        assert prev_replace is t1, "Replacing current task should return the previous task object"
        del t1
        gc.collect()
        assert wr1() is prev_replace, (
            "Previous task (t1) should remain alive via the returned reference after replace"
        )

        # Finally, clear the current task and ensure t2 is returned
        wr2 = weakref.ref(t2)
        prev_clear = swap(l, None)
        assert prev_clear is t2, "Clearing current task should return the last set task (t2)"
        # Keep t2 alive via the returned reference
        del t2
        gc.collect()
        assert wr2() is prev_clear, (
            "Latest task (t2) should remain alive via the returned reference after clear"
        )

        if set_running:
            set_running(None)

    # Run tests
    test_set_then_delete_returns_prev_and_no_crash()
    test_replace_returns_prev_and_no_crash()
"""

rc, out, err = assert_python_ok("-c", code)
assert rc == 0, f"Expected return code 0, got: {rc}"
assert out == b"", f"Expected empty stdout, got: {out}"
assert not err, f"Expected no stderr, got: {err}"
