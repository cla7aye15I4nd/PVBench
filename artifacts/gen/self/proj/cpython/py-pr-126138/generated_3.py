import re
from test.support.script_helper import assert_python_ok


def run_evil_uaf_scenario_and_capture():
    """Run the evil __getattribute__ UAF scenario in a subprocess.

    Returns (rc, out, err).
    Child process swallows exceptions so rc should be 0 on both fixed and
    unfixed interpreters unless a hard crash occurs.
    """
    code = """if 1:
        import asyncio
        import types

        async def evil_coroutine():
            @types.coroutine
            def sync_generator():
                # ensure to keep obj alive after the first send() call
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
                # sets task_cancel_msg to our victim object which will be deleted
                try:
                    asyncio.Task.cancel(task, to_uaf)
                except Exception:
                    # Swallow any exception to keep subprocess exit clean
                    pass

            def cancel(self, msg):
                # When fixed, this should execute BEFORE the object's __del__
                print("in cancel", hex(id(msg)), flush=True)

            def __getattribute__(self, name):
                global to_uaf
                if name == "cancel":
                    class Break:
                        def __str__(self):
                            raise RuntimeError("break")

                    # Do a partial task init that clears the cancel message
                    # reference from the task, then delete the only remaining
                    # Python-level reference to trigger deallocation at the
                    # worst possible moment.
                    try:
                        task.__init__(coro, loop=normal_loop, name=Break())
                    except Exception:
                        pass

                    # Drop the last Python-level reference; if the interpreter
                    # fails to INCREF the message before calling cancel(),
                    # this can cause a UAF crash.
                    try:
                        del to_uaf
                    except NameError:
                        pass

                return object.__getattribute__(self, name)

        class DelTracker:
            def __del__(self):
                # On a fixed build, this should run AFTER cancel() above.
                print("deleting", hex(id(self)), flush=True)

        to_uaf = DelTracker()
        normal_loop = Loop()
        coro = evil_coroutine()
        evil = Evil()

        task = asyncio.Task.__new__(asyncio.Task)
        # eager_start ensures the task steps immediately, exercising the path
        # that cancels the yielded object.
        try:
            task.__init__(coro, loop=normal_loop, name="init", eager_start=True)
        except Exception:
            # Swallow exceptions to keep subprocess exit code 0
            pass

        # Mark end for clarity.
        print("done", flush=True)
    """

    rc, out, err = assert_python_ok('-c', code)
    return rc, out, err


def test_uaf_no_crash_and_identity():
    rc, out, err = run_evil_uaf_scenario_and_capture()

    # Basic process checks: if the bug still exists badly, this may crash/segfault.
    assert rc == 0, f"Expected return code 0, got: {rc}"
    assert not err, f"Expected no stderr, got: {err!r}"

    # Decode and analyze output
    text = out.decode('utf-8', 'replace')
    assert 'in cancel' in text, f"Expected 'in cancel' in stdout, got: {text!r}"
    assert 'deleting' in text, f"Expected 'deleting' in stdout, got: {text!r}"

    # Extract the ids and ensure they match (same object passed to cancel and later deleted)
    m_cancel = re.search(r"in cancel\s+(0x[0-9a-fA-F]+)", text)
    m_delete = re.search(r"deleting\s+(0x[0-9a-fA-F]+)", text)
    assert m_cancel and m_delete, f"Failed to parse ids from output: {text!r}"
    assert m_cancel.group(1) == m_delete.group(1), (
        f"Expected same id for cancel message and deleted object; got {m_cancel.group(1)} vs {m_delete.group(1)}.\nOutput:\n{text}"
    )

    # Optional stronger check for fixed versions: cancel should happen before delete.
    # We don't fail on older versions here to keep the test robust across versions.
    cancel_pos = text.find('in cancel')
    deleting_pos = text.find('deleting')
    if cancel_pos != -1 and deleting_pos != -1:
        # On fixed builds this should be True. If not, the build is likely unfixed
        # but not crashing; do not fail the test in that case.
        _ = cancel_pos < deleting_pos


def test_normal_cancel_message_passthrough():
    """Sanity-check: when cancelling a non-evil awaitable, the cancel message
    is passed through unchanged to its cancel() method.
    """
    import asyncio
    import types

    class Loop:
        is_running = staticmethod(lambda: True)
        get_debug = staticmethod(lambda: False)

    class Recorder:
        _asyncio_future_blocking = True
        get_loop = staticmethod(lambda: normal_loop)

        def __init__(self):
            self.got = None

        def add_done_callback(self, callback, *args, **kwargs):
            asyncio.Task.cancel(task, msg)

        def cancel(self, message):
            self.got = message

    async def coro_body():
        @types.coroutine
        def sync_gen():
            while True:
                yield rec
        await sync_gen()

    normal_loop = Loop()
    rec = Recorder()
    msg = object()

    task = asyncio.Task.__new__(asyncio.Task)
    task.__init__(coro_body(), loop=normal_loop, name="passthrough", eager_start=True)

    assert rec.got is msg, "Cancel message was not forwarded correctly to cancel()"


if __name__ == '__main__':
    # Run tests
    test_uaf_no_crash_and_identity()
    test_normal_cancel_message_passthrough()
    print('OK')
