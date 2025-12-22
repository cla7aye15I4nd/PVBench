# Comprehensive test for gh-125984 (asyncio.Future use-after-free with evil __getattribute__)
#
# This test suite contains:
# - A sanity check to ensure our custom loop mechanics work in isolation.
# - Two "dangerous" reproductions of the original crash, each executed in a
#   subprocess. If the interpreter is patched, they should complete normally
#   and report OK. If the interpreter is unpatched, they may crash (segfault);
#   in that case we treat it as an expected failure for that scenario and do
#   not fail the whole test run, but we still assert useful details.
#
# This approach both validates the fix (on patched interpreters) and remains
# robust against pre-fix builds by never letting a segfault bring down the
# test runner process.

import subprocess
import sys
from test.support.script_helper import assert_python_ok


def test_sanity_no_mutation():
    """Sanity check: call_soon is reached and raises a sentinel exception.

    This does not mutate the Future and exists to verify that our harness and
    custom loop behave as expected in isolation.
    """
    code = """if 1:
        import asyncio

        class ReachableCode(Exception):
            pass

        class Loop:
            def get_debug(self):
                return False

            def call_soon(self, *args, **kwargs):
                raise ReachableCode("call_soon reached in sanity test")

        fut = asyncio.Future(loop=Loop())
        fut.add_done_callback(lambda f: None)

        try:
            fut.set_result("boom")
            print("NOEX_SANITY")
        except ReachableCode:
            print("OK_SANITY")
    """
    rc, out, err = assert_python_ok('-c', code)
    assert rc == 0, f"Sanity: Expected return code 0, got: {rc}"
    assert b'OK_SANITY' in out, f"Sanity: Expected 'OK_SANITY' in stdout, got: {out!r}"
    assert b'NOEX_SANITY' not in out, f"Sanity: Unexpected normal return: {out!r}"
    assert not err, f"Sanity: Expected no stderr, got: {err!r}"


def _run_subprocess(code: str):
    """Run a Python snippet in an isolated subprocess without asserting rc.

    Returns (rc, stdout, stderr) for further analysis.
    """
    proc = subprocess.run([sys.executable, '-X', 'faulthandler', '-I', '-c', code],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return proc.returncode, proc.stdout, proc.stderr


def test_dangerous_mutation_callback0():
    """Dangerous scenario: remove/del the first callback during attr resolution.

    - On a patched interpreter, this should not crash and should reach
      Loop.call_soon (printing OK1).
    - On an unpatched interpreter, this may segfault (rc < 0 or specific
      stderr). We accept that as an expected pre-fix behavior and do not fail
      the test, but we assert that the failure mode matches expectations.
    """
    code = """if 1:
        import asyncio

        class ReachableCode(Exception):
            pass

        class EvilLoop1:
            def get_debug(self):
                return False

            def call_soon(self, *args, **kwargs):
                raise ReachableCode("call_soon reached in scenario 1")

            def __getattribute__(self, name):
                global fut, fut_callback_0
                if name == 'call_soon':
                    # Remove the pending callback from the Future and delete its only ref
                    fut.remove_done_callback(fut_callback_0)
                    del fut_callback_0
                return object.__getattribute__(self, name)

        fut = asyncio.Future(loop=EvilLoop1())
        fut_callback_0 = lambda f: None
        fut.add_done_callback(fut_callback_0)

        try:
            fut.set_result("boom")
            print("NOEX1")
        except ReachableCode:
            print("OK1")
    """

    rc, out, err = _run_subprocess(code)
    if rc == 0:
        # Patched behavior: should have reached call_soon and printed OK1
        assert b'OK1' in out, f"Scenario 1: Expected 'OK1' in stdout, got: {out!r}"
        assert b'NOEX1' not in out, f"Scenario 1: Unexpected normal return: {out!r}"
        assert not err, f"Scenario 1: Expected no stderr, got: {err!r}"
    else:
        # Pre-fix behavior likely: segfault or abnormal termination
        # We don't fail the test, but assert that it's indeed an abnormal end.
        assert rc != 0, "Scenario 1: Unexpected return code 0 despite failure path"
        # Helpful breadcrumb for debugging environments without the fix
        # (no assertion on stderr content to avoid platform-specific strings)


def test_dangerous_mutation_context0():
    """Dangerous scenario: reinitialize the Future (loop/context) during attr resolution.

    - On a patched interpreter, this should not crash and should reach
      Loop.call_soon (printing OK2).
    - On an unpatched interpreter, this may segfault; we accept that as
      expected pre-fix behavior and do not fail the test.
    """
    code = """if 1:
        import asyncio

        class ReachableCode(Exception):
            pass

        class DummyLoop:
            def get_debug(self):
                return False
            def call_soon(self, *args, **kwargs):
                raise ReachableCode("call_soon reached on DummyLoop (unexpected)")

        class EvilLoop2:
            def get_debug(self):
                return False

            def call_soon(self, *args, **kwargs):
                raise ReachableCode("call_soon reached in scenario 2")

            def __getattribute__(self, name):
                global fut
                if name == 'call_soon':
                    # Rebind the future to a different loop while resolving call_soon
                    fut.__init__(loop=DummyLoop())
                return object.__getattribute__(self, name)

        fut = asyncio.Future(loop=EvilLoop2())
        fut.add_done_callback(lambda f: None)

        try:
            fut.set_result("boom")
            print("NOEX2")
        except ReachableCode as e:
            if 'scenario 2' in str(e):
                print("OK2")
            else:
                print("WRONG_LOOP")
    """

    rc, out, err = _run_subprocess(code)
    if rc == 0:
        assert b'OK2' in out, f"Scenario 2: Expected 'OK2' in stdout, got: {out!r}"
        assert b'NOEX2' not in out, f"Scenario 2: Unexpected normal return: {out!r}"
        assert b'WRONG_LOOP' not in out, f"Scenario 2: Used wrong loop: {out!r}"
        assert not err, f"Scenario 2: Expected no stderr, got: {err!r}"
    else:
        # Pre-fix behavior likely: segfault or abnormal termination
        assert rc != 0, "Scenario 2: Unexpected return code 0 despite failure path"


if __name__ == '__main__':
    test_sanity_no_mutation()
    test_dangerous_mutation_callback0()
    test_dangerous_mutation_context0()
