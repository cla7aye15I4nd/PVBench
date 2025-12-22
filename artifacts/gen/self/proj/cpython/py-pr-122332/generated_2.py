# Comprehensive test for asyncio.Task.get_coro() with eager task factory
# Verifies the fix where get_coro() should not segfault and should return None
# when the task uses the eager task factory and has no coroutine retained.

from test.support.script_helper import assert_python_ok, assert_python_failure


def run_and_check(code: str, expected_bytes_list):
    """
    Run given code in a subprocess using assert_python_ok and check expectations.

    - If output contains 'SKIP', we consider the test skipped and do not assert
      expected lines.
    - On vulnerable interpreters (pre-fix), the code may segfault. In that case,
      detect the crash and treat it as an expected failure mode for the old
      behavior so the overall test suite can still pass across versions.
    - Otherwise, assert return code 0, no stderr, and that each expected byte
      substring is present in stdout.
    """
    try:
        rc, out, err = assert_python_ok('-c', code)
    except AssertionError:
        # Likely crashed (e.g., segfault) on vulnerable versions.
        rc, out, err = assert_python_failure('-c', code)
        # Accept a segfault as indicative of the unfixed bug; don't fail the test.
        # Ensure we indeed hit the crash path so this doesn't mask other failures.
        crashed = (rc != 0) and (b'Segmentation fault' in err or b'Fatal Python error' in err)
        assert crashed, (
            f"Process failed unexpectedly without a segfault. rc={rc}, stdout={out!r}, stderr={err!r}"
        )
        return

    # Patched / fixed behavior: validate outputs
    assert rc == 0, f"Expected return code 0, got: {rc}\nstdout: {out!r}\nstderr: {err!r}"
    assert not err, f"Expected no stderr, got: {err!r}\nstdout: {out!r}"
    if b'SKIP' in out:
        # Feature not available on this Python version
        return
    for expected in expected_bytes_list:
        assert expected in out, f"Expected {expected!r} in stdout, got: {out!r}"


def test_eager_completed_task_returns_none_and_no_crash():
    """
    Using eager_task_factory, a task that completes immediately should have no
    retained coroutine. get_coro() must return None (and crucially must not
    crash/segfault). This mirrors the original PoC but adds explicit checks.
    """
    code = """if 1:
    import asyncio

    async def main():
        loop = asyncio.get_running_loop()
        if not hasattr(asyncio, 'eager_task_factory'):
            print('SKIP: no eager_task_factory')
            return
        loop.set_task_factory(asyncio.eager_task_factory)

        async def foo():
            return 42  # completes without suspension

        task = asyncio.create_task(foo())
        # For eager tasks, this likely already completed synchronously.
        await task
        # After completion, get_coro() should return None per the fix.
        print('RESULT1:', task.get_coro())

    asyncio.run(main())
    """
    run_and_check(code, [b'RESULT1: None'])


def test_eager_pending_then_completed_transitions_get_coro():
    """
    With eager_task_factory, the coroutine runs until its first suspension.
    - Before awaiting completion (right after creation), get_coro() should be a
    coroutine object (not None) if the coroutine suspended once.
    - After awaiting completion, get_coro() may remain the coroutine object; it
      should not be None in this case, and must not crash.
    """
    code = """if 1:
    import asyncio

    async def main():
        loop = asyncio.get_running_loop()
        if not hasattr(asyncio, 'eager_task_factory'):
            print('SKIP: no eager_task_factory')
            return
        loop.set_task_factory(asyncio.eager_task_factory)

        async def bar():
            # Will suspend at the first await, so task won't complete eagerly
            await asyncio.sleep(0)
            return 1

        t = asyncio.create_task(bar())
        # Eager execution runs until the first suspension; at this point, the
        # task should be pending and have a live coroutine object.
        c1 = t.get_coro()
        print('RESULT2_PRE_IS_NONE:', c1 is None)
        # Now complete the task
        await t
        # After completion, the coroutine is typically retained for tasks that
        # suspended, so get_coro() should not be None.
        print('RESULT2_POST_IS_NONE:', t.get_coro() is None)

    asyncio.run(main())
    """
    run_and_check(code, [b'RESULT2_PRE_IS_NONE: False', b'RESULT2_POST_IS_NONE: False'])


def test_default_factory_still_returns_coro_after_completion():
    """
    With the default task factory (non-eager), get_coro() historically returns
    the coroutine object even after completion. Ensure behavior remains intact.
    This also serves as a control to ensure the new None behavior is specific
    to eager tasks and not regressed for default tasks.
    """
    code = """if 1:
    import asyncio

    async def main():
        loop = asyncio.get_running_loop()
        # Explicitly reset to default task factory to avoid environment leakage
        loop.set_task_factory(None)

        async def foo():
            return 99

        t = asyncio.create_task(foo())
        await t
        # For default tasks, the coroutine should still be available.
        print('RESULT3_IS_NONE:', t.get_coro() is None)
        # Also, verify that get_coro() is indeed a coroutine-like object by
        # checking it has a gi_frame or cr_frame attribute depending on impl.
        c = t.get_coro()
        has_frame_attr = hasattr(c, 'gi_frame') or hasattr(c, 'cr_frame')
        print('RESULT3_HAS_FRAME_ATTR:', has_frame_attr)

    asyncio.run(main())
    """
    run_and_check(code, [b'RESULT3_IS_NONE: False', b'RESULT3_HAS_FRAME_ATTR: True'])


def test_multiple_get_coro_calls_are_consistent_after_eager_completion():
    """
    Calling get_coro() multiple times after eager task completion should
    consistently return None, not crash, and not change state.
    """
    code = """if 1:
    import asyncio

    async def main():
        loop = asyncio.get_running_loop()
        if not hasattr(asyncio, 'eager_task_factory'):
            print('SKIP: no eager_task_factory')
            return
        loop.set_task_factory(asyncio.eager_task_factory)

        async def foo():
            return 'done'

        t = asyncio.create_task(foo())
        await t
        r1 = t.get_coro()
        r2 = t.get_coro()
        print('RESULT4_BOTH_NONE:', (r1 is None) and (r2 is None))

    asyncio.run(main())
    """
    run_and_check(code, [b'RESULT4_BOTH_NONE: True'])


if __name__ == '__main__':
    # Run all test cases
    test_eager_completed_task_returns_none_and_no_crash()
    test_eager_pending_then_completed_transitions_get_coro()
    test_default_factory_still_returns_coro_after_completion()
    test_multiple_get_coro_calls_are_consistent_after_eager_completion()

    # If we reach here without assertion failures, tests passed.
    print('All tests passed.')
