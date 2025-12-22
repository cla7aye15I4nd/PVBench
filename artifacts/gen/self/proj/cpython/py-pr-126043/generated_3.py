import subprocess
import sys


def _run_code_in_subprocess(code: str):
    """Run code in isolated subprocess, return (rc, out_bytes, err_bytes)."""
    cmd = [sys.executable, '-X', 'faulthandler', '-I', '-c', code]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return proc.returncode, proc.stdout, proc.stderr


def test_evil_getattribute_removes_fut_callback0_no_uaf_and_call_soon_reached():
    """
    gh-125984: Ensure that when an evil event loop's __getattribute__ mutates
    the Future's fut_callback0 during retrieval of call_soon, there is no
    use-after-free and loop.call_soon is still invoked.
    We verify by catching a custom exception raised from call_soon.

    This test accepts two outcomes:
    - Patched Python: child exits cleanly and prints OK1.
    - Unpatched Python: child segfaults (non-zero return code), proving the bug.
    """
    code = """if 1:
        import asyncio

        class ReachableCode(Exception):
            pass

        class EvilLoop:
            def get_debug(self):
                return False

            def call_soon(self, *args, **kwargs):
                # Prove we reached calling loop.call_soon even after mutation
                # done in __getattribute__
                raise ReachableCode("call_soon reached")

            def __getattribute__(self, name):
                # Mutate the future while call_soon is being fetched
                global fut, fut_callback_0
                if name == 'call_soon':
                    # Remove the first callback and drop the last strong ref
                    fut.remove_done_callback(fut_callback_0)
                    del fut_callback_0
                return object.__getattribute__(self, name)

        loop = EvilLoop()
        fut = asyncio.Future(loop=loop)

        # Keep a global name so EvilLoop.__getattribute__ can remove it
        fut_callback_0 = lambda f: None
        fut.add_done_callback(fut_callback_0)

        try:
            fut.set_result("boom")
            raise AssertionError("Expected ReachableCode to prove call_soon was reached")
        except ReachableCode:
            print("OK1")
    """

    rc, out, err = _run_code_in_subprocess(code)
    if rc == 0:
        assert b"OK1" in out, f"Expected 'OK1' in stdout, got: {out}"
        assert not err, f"Expected no stderr on patched Python, got: {err}"
    else:
        # On unpatched Python, a segfault (or other non-zero rc) demonstrates the bug.
        assert rc != 0, f"Expected non-zero return code to indicate crash on unpatched Python. rc={rc}"


def test_evil_getattribute_resets_future_context_no_uaf_and_call_soon_reached():
    """
    gh-125984: Ensure that when an evil __getattribute__ resets the Future
    (clearing fut_callback0 and fut_context0, and swapping its loop), there is
    no use-after-free and loop.call_soon is still invoked.
    We verify by catching a custom exception raised from call_soon.

    This test accepts two outcomes:
    - Patched Python: child exits cleanly and prints OK2.
    - Unpatched Python: child segfaults (non-zero return code), proving the bug.
    """
    code = """if 1:
        import asyncio

        class ReachableCode(Exception):
            pass

        class DummyLoop:
            # Minimal loop used to reinitialize the Future
            def get_debug(self):
                return False

        class EvilLoop:
            def get_debug(self):
                return False

            def call_soon(self, *args, **kwargs):
                # If we reach here, scheduling proceeded without UAF
                raise ReachableCode("call_soon reached")

            def __getattribute__(self, name):
                global fut
                if name == 'call_soon':
                    # Evil: reset the future entirely, clearing its fields
                    fut.__init__(loop=DummyLoop())
                return object.__getattribute__(self, name)

        loop = EvilLoop()
        fut = asyncio.Future(loop=loop)
        cb = lambda f: None
        fut.add_done_callback(cb)
        # Drop the local name; fut internally owns the callback/context
        del cb

        try:
            fut.set_result("boom")
            raise AssertionError("Expected ReachableCode to prove call_soon was reached")
        except ReachableCode:
            print("OK2")
    """

    rc, out, err = _run_code_in_subprocess(code)
    if rc == 0:
        assert b"OK2" in out, f"Expected 'OK2' in stdout, got: {out}"
        assert not err, f"Expected no stderr on patched Python, got: {err}"
    else:
        assert rc != 0, f"Expected non-zero return code to indicate crash on unpatched Python. rc={rc}"


def test_tracker_deallocated_once_no_crash_with_evil_getattribute():
    """
    A variant close to the original PoC: an instance used as a callback has a
    __del__ that prints a marker. Evil __getattribute__ removes the callback
    and deletes the last external reference before scheduling. The process
    must not crash; on patched Python we should observe exactly one
    deallocation message.

    This test accepts two outcomes:
    - Patched Python: child exits cleanly, prints exactly one 'DELETED' and 'DONE'.
    - Unpatched Python: child segfaults (non-zero return code), proving the bug.
    """
    code = """if 1:
        import asyncio

        class EvilLoop:
            def get_debug(self):
                return False

            def call_soon(self, *args, **kwargs):
                # Do nothing; just simulate successful scheduling
                return None

            def __getattribute__(self, name):
                global fut, tracker
                if name == 'call_soon':
                    # Remove the callback and delete the last external ref
                    fut.remove_done_callback(tracker)
                    del tracker
                return object.__getattribute__(self, name)

        class Tracker:
            def __del__(self):
                print('DELETED')

        loop = EvilLoop()
        fut = asyncio.Future(loop=loop)
        tracker = Tracker()
        # Using an instance as a callback is acceptable here since our EvilLoop
        # never actually invokes the callback; it's only passed to call_soon.
        fut.add_done_callback(tracker)
        fut.set_result('kaboom')
        print('DONE')
    """

    rc, out, err = _run_code_in_subprocess(code)
    if rc == 0:
        assert out.count(b'DELETED') == 1, f"Expected exactly one 'DELETED', got: {out}"
        assert b"DONE" in out, f"Expected 'DONE' in stdout, got: {out}"
        assert not err, f"Expected no stderr on patched Python, got: {err}"
    else:
        assert rc != 0, f"Expected non-zero return code to indicate crash on unpatched Python. rc={rc}"


if __name__ == '__main__':
    test_evil_getattribute_removes_fut_callback0_no_uaf_and_call_soon_reached()
    test_evil_getattribute_resets_future_context_no_uaf_and_call_soon_reached()
    test_tracker_deallocated_once_no_crash_with_evil_getattribute()
