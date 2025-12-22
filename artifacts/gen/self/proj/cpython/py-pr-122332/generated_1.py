# This test verifies the fix for asyncio.Task.get_coro when using the eager task
# factory. The original bug caused a potential segfault because get_coro attempted
# to return a NULL task_coro pointer. The patch updates get_coro to return None
# when task_coro is NULL. We validate several scenarios:
#
# 1) POC behavior: with eager task factory, a task that completes immediately
#    should cause task.get_coro() to return None (instead of crashing). We also
#    verify stdout for the POC-like code path.
# 2) Eager task factory with a coroutine that suspends once: get_coro() should be
#    available before awaiting. After completion, it must not crash and may be
#    either None or a coroutine/generator depending on implementation details.
# 3) Default (non-eager) factory: get_coro() should return a coroutine/generator
#    both before and after completion (legacy behavior), and must not be None.
#
# We use subprocess isolation via assert_python_ok because the original issue could
# result in a segfault. Each child process prints OK:/SKIP: markers for robustness.

from test.support.script_helper import assert_python_ok


def run_subproc_with_markers(code: str, expect_markers: list[str]):
    rc, out, err = assert_python_ok('-c', code)
    # Return code already validated by assert_python_ok; keep explicit check per guidelines.
    assert rc == 0, f"Expected return code 0, got: {rc} (stderr: {err!r})"
    text_out = out.decode('utf-8', 'replace')
    for marker in expect_markers:
        ok = f"OK:{marker}"
        skip = f"SKIP:{marker}"
        assert (ok in text_out) or (skip in text_out), (
            f"Expected either '{ok}' or '{skip}' in stdout, got: {text_out!r}"
        )
    assert not err, f"Expected no stderr, got: {err!r}"


def run_subproc_and_check_stdout(code: str, expected_bytes: bytes, skip_token: bytes | None = None):
    rc, out, err = assert_python_ok('-c', code)
    assert rc == 0, f"Expected return code 0, got: {rc} (stderr: {err!r})"
    if skip_token and skip_token in out:
        # Skipped: nothing further to assert
        return
    # Otherwise, ensure the expected stdout appears (exact or as substring)
    out_stripped = out.strip()
    assert expected_bytes in out_stripped, (
        f"Expected {expected_bytes!r} in stdout, got: {out!r}"
    )
    assert not err, f"Expected no stderr, got: {err!r}"


def test_poc_prints_none():
    # Replicate the POC style: print task.get_coro() after awaiting a task that
    # completes immediately under the eager task factory. Expect 'None' on stdout
    # (previously could segfault).
    code = """if 1:
    import asyncio, sys

    async def main():
        # Skip on Python versions older than 3.13 where the bug is present.
        if sys.version_info < (3, 13):
            print('SKIP:poc')
            return

        loop = asyncio.get_running_loop()
        if not hasattr(asyncio, 'eager_task_factory'):
            print('SKIP:poc')
            return
        loop.set_task_factory(asyncio.eager_task_factory)

        async def foo():
            # completes immediately (no suspension)
            return 42

        task = asyncio.create_task(foo())
        await task
        # Should print 'None' after the fix; previously could segfault.
        print(task.get_coro())

    asyncio.run(main())
"""
    # Either we get a skip marker (older Python without eager_task_factory or version), or we see 'None' printed.
    run_subproc_and_check_stdout(code, expected_bytes=b'None', skip_token=b'SKIP:poc')


def test_eager_immediate_returns_none():
    # Using eager task factory with a coroutine that completes immediately.
    # get_coro must return None both before and after awaiting (and must not crash).
    code = """if 1:
    import asyncio
    import sys

    async def main():
        # Skip on Python versions older than 3.13 where the bug is present.
        if sys.version_info < (3, 13):
            print('SKIP:eager_immediate_none')
            return

        loop = asyncio.get_running_loop()
        if not hasattr(asyncio, 'eager_task_factory'):
            print('SKIP:eager_immediate_none')
            return
        loop.set_task_factory(asyncio.eager_task_factory)

        async def foo():
            return 123

        t = asyncio.create_task(foo())

        before = t.get_coro()
        assert before is None, f"eager immediate: expected None before await, got {before!r}"

        res = await t
        assert res == 123, f"Unexpected result: {res}"

        after = t.get_coro()
        assert after is None, f"eager immediate: expected None after await, got {after!r}"

        print('OK:eager_immediate_none')

    asyncio.run(main())
"""
    run_subproc_with_markers(code, ["eager_immediate_none"])


def test_eager_pending_then_valid_after():
    # Using eager task factory with a coroutine that suspends once.
    # Before awaiting, get_coro should be a coroutine/generator (not None).
    # After awaiting, it must not crash; it may be None or remain a coroutine/generator
    # depending on implementation details. We accept either, but verify type when present.
    code = """if 1:
    import asyncio
    import inspect
    import sys

    async def main():
        # Skip on Python versions older than 3.13 where the bug is present.
        if sys.version_info < (3, 13):
            print('SKIP:eager_pending_ok')
            return

        loop = asyncio.get_running_loop()
        if not hasattr(asyncio, 'eager_task_factory'):
            print('SKIP:eager_pending_ok')
            return
        loop.set_task_factory(asyncio.eager_task_factory)

        async def bar():
            await asyncio.sleep(0)
            return 'done'

        t = asyncio.create_task(bar())

        before = t.get_coro()
        assert before is not None, "eager pending: expected a coroutine before await"
        assert inspect.iscoroutine(before) or inspect.isgenerator(before), (
            f"eager pending: expected coroutine/generator, got {type(before)}"
        )

        res = await t
        assert res == 'done'

        after = t.get_coro()
        # After completion it must not crash; either None or a coroutine/generator is acceptable.
        if after is not None:
            assert inspect.iscoroutine(after) or inspect.isgenerator(after), (
                f"eager pending: expected coroutine/generator or None after await, got {type(after)}"
            )

        print('OK:eager_pending_ok')

    asyncio.run(main())
"""
    run_subproc_with_markers(code, ["eager_pending_ok"])


def test_default_factory_coroutine_available():
    # With the default factory (non-eager), get_coro should be a coroutine/generator
    # both before and after awaiting task completion.
    code = """if 1:
    import asyncio
    import inspect

    async def main():
        async def foo():
            return 5

        t = asyncio.create_task(foo())

        before = t.get_coro()
        assert before is not None, "default: expected coroutine before await"
        assert inspect.iscoroutine(before) or inspect.isgenerator(before), (
            f"default: expected coroutine/generator, got {type(before)}"
        )

        res = await t
        assert res == 5

        after = t.get_coro()
        assert after is not None, "default: expected coroutine after await to remain available"
        assert inspect.iscoroutine(after) or inspect.isgenerator(after), (
            "default: expected coroutine/generator after await"
        )

        print('OK:default_non_eager_non_none')

    asyncio.run(main())
"""
    run_subproc_with_markers(code, ["default_non_eager_non_none"])


if __name__ == '__main__':
    test_poc_prints_none()
    test_eager_immediate_returns_none()
    test_eager_pending_then_valid_after()
    test_default_factory_coroutine_available()
    print('All tests passed.')
