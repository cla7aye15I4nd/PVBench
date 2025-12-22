# Test suite verifying asyncio.Task.get_coro behavior with eager task factory
# Based on patch that fixes segfault when task_coro is NULL by returning None
# instead of dereferencing NULL.

from test.support.script_helper import assert_python_ok


def run_and_assert(code: str, expected_markers: list):
    rc, out, err = assert_python_ok('-c', code)
    stdout = out.decode('utf-8', 'replace')
    # If feature is unavailable or version too old, allow the test to skip gracefully
    if 'SKIP' in stdout:
        return
    assert not err, f"Expected no stderr, got: {err}"
    for marker in expected_markers:
        assert marker in stdout, f"Expected '{marker}' in stdout, got: {stdout!r}"


def test_completed_eager_task_get_coro_none():
    # Verifies the core fix: after an eager task that completes immediately,
    # Task.get_coro() must not crash and should return None.
    code = """if 1:
    import asyncio, sys

    async def main():
        if sys.version_info < (3, 13) or not hasattr(asyncio, 'eager_task_factory'):
            print('SKIP')
            return
        loop = asyncio.get_running_loop()
        loop.set_task_factory(asyncio.eager_task_factory)

        async def foo():
            return 'done'

        t = asyncio.create_task(foo())
        # With eager task factory, task completes immediately (no suspension)
        assert t.done(), f"Expected task done with eager factory, got done={t.done()}"
        # Critical assertion per fix: get_coro must be safe and return None
        c1 = t.get_coro()
        assert c1 is None, f"Expected None from get_coro() on completed eager task, got {c1!r}"
        # Repeated calls must continue to be safe and return None
        c2 = t.get_coro()
        assert c2 is None, "Expected None on repeated get_coro() call"
        print('CORO_NONE_OK')

    asyncio.run(main())
"""
    run_and_assert(code, ["CORO_NONE_OK"]) 


def test_completed_eager_task_exception_get_coro_none():
    # Edge case: eager task raises immediately (no suspension). After it
    # finishes with an exception, get_coro should still return None and not crash.
    code = """if 1:
    import asyncio, sys

    async def main():
        if sys.version_info < (3, 13) or not hasattr(asyncio, 'eager_task_factory'):
            print('SKIP')
            return
        loop = asyncio.get_running_loop()
        loop.set_task_factory(asyncio.eager_task_factory)

        async def bad():
            raise RuntimeError('boom')

        t = asyncio.create_task(bad())
        try:
            await t
            assert False, 'Awaiting task should raise RuntimeError'
        except RuntimeError as e:
            assert 'boom' in str(e), f"Expected 'boom' in error, got: {e}"
        assert t.done(), 'Task should be done after exception'
        assert t.get_coro() is None, 'Expected None from get_coro() after exception'
        # Re-check to ensure stability
        assert t.get_coro() is None, 'Expected None again from get_coro() after exception'
        print('CORO_NONE_AFTER_EXCEPTION')

    asyncio.run(main())
"""
    run_and_assert(code, ["CORO_NONE_AFTER_EXCEPTION"]) 


def test_eager_factory_first_suspend_get_coro_before_and_after():
    # Task that suspends once; eager factory runs it to first await.
    # Before completion: get_coro() should be a coroutine object.
    # After completion: behavior may differ across implementations; the key is
    # that get_coro() must not crash. Accept either None or a coroutine object.
    code = """if 1:
    import asyncio, inspect, sys

    async def main():
        if sys.version_info < (3, 13) or not hasattr(asyncio, 'eager_task_factory'):
            print('SKIP')
            return
        loop = asyncio.get_running_loop()
        loop.set_task_factory(asyncio.eager_task_factory)

        async def bar():
            await asyncio.sleep(0)
            return 42

        t = asyncio.create_task(bar())
        # Eager factory runs until first suspension point
        assert not t.done(), "Expected task not done at first suspension point"
        c_before = t.get_coro()
        assert c_before is not None, "Expected non-None coroutine before completion"
        assert inspect.iscoroutine(c_before), f"Expected coroutine object, got {type(c_before)}"
        print('CORO_NOT_NONE_BEFORE')

        # Now let it finish and ensure get_coro() remains safe to call
        result = await t
        assert result == 42, f"Expected 42, got {result}"
        c_after = t.get_coro()
        # After completion, it must be either a coroutine object (implementation-dependent)
        # or None (if the coroutine reference is cleared). Both are acceptable.
        assert (c_after is None) or inspect.iscoroutine(c_after), (
            f"Expected None or coroutine after completion, got {c_after!r} of type {type(c_after)}"
        )
        print('CORO_AFTER_SAFE')

    asyncio.run(main())
"""
    run_and_assert(code, ["CORO_NOT_NONE_BEFORE", "CORO_AFTER_SAFE"]) 


if __name__ == '__main__':
    test_completed_eager_task_get_coro_none()
    test_completed_eager_task_exception_get_coro_none()
    test_eager_factory_first_suspend_get_coro_before_and_after()
    print('All tests passed.')
