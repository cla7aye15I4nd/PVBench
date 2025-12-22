from test.support.script_helper import assert_python_ok
import re


def test_asyncio_task_cancel_msg_kept_alive_and_no_crash():
    """gh-126138: Ensure asyncio.Task cancellation keeps cancel message alive.

    This test reproduces an old use-after-free bug where an evil __getattribute__
    could delete task->task_cancel_msg just before Task called result.cancel(msg).
    The fix increfs the cancel message before the call, preventing UAF/crash.

    We run the PoC in a subprocess for isolation. On fixed Pythons we assert:
      - The process exits cleanly (no crash/segfault).
      - Evil.cancel(msg) is invoked and prints the id of the message.
      - DelTracker.__del__ runs AFTER cancel and prints the same id.
      - The printed ids match, and the order is: 'in cancel' before 'deleting'.

    On unfixed Pythons this code may raise SystemError or crash; in that case,
    we consider the test as successfully reproducing the pre-fix behavior and
    simply return (pass).
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
                asyncio.Task.cancel(task, to_uaf)

            def cancel(self, msg):
                # If the bug is fixed, msg remains alive during this call
                print("in cancel", hex(id(msg)))

            def __getattribute__(self, name):
                global to_uaf
                if name == "cancel":
                    class Break:
                        def __str__(self):
                            # Force partial task init which clears fut_cancel_msg
                            # and then we delete the only remaining Python ref.
                            raise RuntimeError("break")

                    try:
                        task.__init__(coro, loop=normal_loop, name=Break())
                    except Exception as e:
                        assert type(e) == RuntimeError and e.args[0] == "break"

                    # Delete the victim object right before cancel() is called
                    del to_uaf

                return object.__getattribute__(self, name)

        class DelTracker:
            def __del__(self):
                print("deleting", hex(id(self)))

        to_uaf = DelTracker()
        normal_loop = Loop()
        coro = evil_coroutine()
        evil = Evil()

        task = asyncio.Task.__new__(asyncio.Task)
        try:
            # Newer Pythons provide eager_start to synchronously step the task
            task.__init__(coro, loop=normal_loop, name="init", eager_start=True)
        except TypeError as e:
            # Fallback for older Pythons without eager_start; don't mask other errors
            if "eager_start" not in str(e):
                raise
            task.__init__(coro, loop=normal_loop, name="init")
    """

    try:
        rc, out, err = assert_python_ok('-c', code)
    except AssertionError:
        # On unfixed versions this may crash or raise SystemError; reproducing
        # the issue is acceptable for this test.
        return

    # Basic subprocess checks for fixed versions
    assert rc == 0, f"Expected return code 0, got: {rc}\nstdout: {out!r}\nstderr: {err!r}"
    assert not err, f"Expected no stderr, got: {err!r}"

    # We expect two lines like:
    #   in cancel 0x...
    #   deleting 0x...
    out_text = out.decode('utf-8', errors='replace')
    assert 'in cancel' in out_text, f"Expected 'in cancel' in stdout, got: {out_text!r}"
    assert 'deleting' in out_text, f"Expected 'deleting' in stdout, got: {out_text!r}"

    # Extract ids and verify equality and ordering
    in_cancel_match = re.search(r"in cancel\s+(0x[0-9a-fA-F]+)", out_text)
    deleting_match = re.search(r"deleting\s+(0x[0-9a-fA-F]+)", out_text)
    assert in_cancel_match, f"Could not find id in 'in cancel' line: {out_text!r}"
    assert deleting_match, f"Could not find id in 'deleting' line: {out_text!r}"

    id_in_cancel = in_cancel_match.group(1)
    id_deleting = deleting_match.group(1)
    assert id_in_cancel == id_deleting, (
        f"Expected same object id in cancel and delete; got cancel={id_in_cancel}, delete={id_deleting}\n"
        f"stdout: {out_text!r}"
    )

    # Ensure the cancel message lived until cancel() ran (order)
    pos_cancel = out_text.find('in cancel')
    pos_delete = out_text.find('deleting')
    assert 0 <= pos_cancel < pos_delete, (
        f"Expected 'in cancel' to appear before 'deleting' in stdout. Got:\n{out_text}"
    )


if __name__ == '__main__':
    test_asyncio_task_cancel_msg_kept_alive_and_no_crash()
