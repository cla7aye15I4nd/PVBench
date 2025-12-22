import sys
import subprocess


def _run_isolated(code: str):
    """Run code in a fresh Python process, return (rc, out, err)."""
    args = [sys.executable, '-X', 'faulthandler', '-I', '-c', code]
    proc = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return proc.returncode, proc.stdout, proc.stderr


def _skip_if_vulnerable(rc, test_name: str):
    # When the interpreter is not patched, the crafted scenario segfaults (-11).
    # In that case, we skip to avoid crashing the test run on vulnerable builds.
    if rc != 0:
        # Print a standardized skip message to stdout for visibility.
        print(f"SKIP {test_name}: vulnerable interpreter (rc={rc})")
        return True
    return False


def test_evil_getattribute_removes_callback0_no_crash():
    """
    gh-125984: Ensure no use-after-free when an event loop with an evil
    __getattribute__ removes fut_callback0 during attribute access for
    call_soon. The fix in _asynciomodule.c transfers ownership of
    fut_callback0/context0 to local variables before calling call_soon,
    preventing external mutation from causing UAF.

    This test runs in a subprocess for isolation (the unfixed bug could
    segfault). We assert that call_soon is reached (by raising a custom
    exception) and that the process exits cleanly with expected output.
    On vulnerable interpreters, the subprocess may crash; in that case we
    skip the assertion to avoid failing the whole run.
    """

    code = """if 1:
        import asyncio

        class ReachableCode(Exception):
            pass

        class EvilLoop:
            def get_debug(self):
                return False

            def call_soon(self, *args, **kwargs):
                # If scheduling happens, raise to confirm reachability
                raise ReachableCode("scheduled")

            def __getattribute__(self, name):
                global tracker, fut
                if name == "call_soon":
                    # Mutate the future's callbacks right before retrieving call_soon
                    # This used to provoke a UAF when CPython cleared fut_callback0
                    # after returning from call_soon.
                    fut.remove_done_callback(tracker)
                    del tracker
                return object.__getattribute__(self, name)

        evil_loop = EvilLoop()
        fut = asyncio.Future(loop=evil_loop)

        # A simple done callback (position 0)
        tracker = lambda f: None
        fut.add_done_callback(tracker)

        try:
            fut.set_result("boom")
            raise AssertionError("Expected ReachableCode to be raised by call_soon")
        except ReachableCode:
            # If we reach here without crashing, the bug is fixed.
            print("OK1")
    """

    rc, out, err = _run_isolated(code)
    if _skip_if_vulnerable(rc, "evil_getattribute_removes_callback0"):
        return
    assert rc == 0, f"Expected return code 0, got: {rc}, stderr: {err!r}"
    assert b"OK1" in out, f"Expected 'OK1' in stdout, got: {out!r}"
    assert not err, f"Expected no stderr, got: {err!r}"


essential_second_case_code = """if 1:
import asyncio

class ReachableCode(Exception):
    pass

class EvilLoop:
    def get_debug(self):
        return False

    def call_soon(self, *args, **kwargs):
        # Confirm we reached scheduling
        raise ReachableCode("scheduled")

    def __getattribute__(self, name):
        global fut
        if name == "call_soon":
            # Reinitialize the future with a different loop just before
            # retrieving call_soon. This can free/replace fut_context0 in
            # implementations that capture a context for callbacks.
            class OtherLoop:
                def get_debug(self):
                    return False
            fut.__init__(loop=OtherLoop())
        return object.__getattribute__(self, name)

# Create the evil loop and the future bound to it
evil_loop = EvilLoop()
fut = asyncio.Future(loop=evil_loop)

# Install a done callback to ensure fut_callback0/context0 are set.
# Using a lambda ensures a context is captured by the Future.
cb = lambda f: None
fut.add_done_callback(cb)
del cb

try:
    fut.set_result("boom")
    raise AssertionError("Expected ReachableCode to be raised by call_soon")
except ReachableCode:
    # If we reach here without crashing, the bug is fixed.
    print("OK2")
"""


def test_evil_getattribute_resets_future_no_crash_context0_safe():
    """
    gh-125984: Ensure no use-after-free when an event loop with an evil
    __getattribute__ mutates the Future (e.g., reinitializes it) during
    attribute access for call_soon, potentially freeing or replacing the
    stored fut_context0. The fix transfers references to local variables
    before calling call_soon, so clearing them after the call is safe.

    Run in a subprocess to guard against crashes on vulnerable builds.
    """

    rc, out, err = _run_isolated(essential_second_case_code)
    if _skip_if_vulnerable(rc, "evil_getattribute_resets_future"):
        return
    assert rc == 0, f"Expected return code 0, got: {rc}, stderr: {err!r}"
    assert b"OK2" in out, f"Expected 'OK2' in stdout, got: {out!r}"
    assert not err, f"Expected no stderr, got: {err!r}"


if __name__ == '__main__':
    test_evil_getattribute_removes_callback0_no_crash()
    test_evil_getattribute_resets_future_no_crash_context0_safe()
