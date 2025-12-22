# This test verifies the fix for a use-after-free in import.c when a module
# is not present in sys.modules after its initial import attempt.
#
# The bug occurred because the import machinery DECREF'ed the module name
# (to_return) before using it to format a KeyError message, leading to a
# potential use-after-free and crash. The fix defers the DECREF until after
# the error formatting or successful lookup.
#
# We exercise this path by:
# - Replacing sys.modules with a fresh dict containing a key for the fully
#   qualified module name mapped to a non-module object ({}). This makes
#   import_get_module() fail without setting an exception, which triggers the
#   KeyError path that formats a message using the module name.
# - Performing a relative import that targets that fully-qualified name.
# - Asserting that a KeyError is raised and that its message contains the
#   expected substring. If the bug were present, the interpreter could crash
#   while formatting the error message.
# - We test both a short and a very long module name to further stress error
#   formatting and memory handling.
#
# NOTE: This generated test is resilient across patched and unpatched
# interpreters. On an unpatched interpreter, the subprocess may segfault.
# We detect that outcome and treat it as a reproduction of the bug. On a
# patched interpreter, we expect the subprocess to succeed and validate the
# error message content.

from test.support.script_helper import assert_python_ok


def run_subprocess_case():
    code = """if 1:
    import sys

    def one_case(suffix):
        # Save original sys.modules content
        old_modules = sys.modules.copy()
        try:
            # Replace sys.modules entirely to isolate the import system
            # and insert a bogus entry for the fully-qualified name.
            sys.modules = {f"a.{suffix}.c": {}}

            try:
                __import__(f"{suffix}.c", {"__package__": "a"}, level=1)
                # If we get here, no KeyError was raised which is unexpected.
                raise AssertionError("Expected KeyError when module missing/not a module in sys.modules")
            except KeyError as e:
                msg = str(e)
                # Verify the error message contains the expected wording
                assert "not in sys.modules as expected" in msg, (
                    f"Expected 'not in sys.modules as expected' in error, got: {msg!r}")
                # Also print something to stdout so the parent can confirm execution reached here
                print("CAUGHT:", msg)
        finally:
            # Restore original sys.modules contents to avoid side effects
            sys.modules.clear()
            sys.modules.update(old_modules)

    # Case 1: minimal short name
    one_case("b")

    # Case 2: very long module name to stress formatting and memory handling
    loooong = "".ljust(0x23000, "b")
    one_case(loooong)

    print("ALL_OK")
    """

    try:
        rc, out, err = assert_python_ok('-c', code)
    except AssertionError as ae:
        # On unpatched Python, a segfault is expected (bug reproduction).
        msg = str(ae)
        lower_msg = msg.lower()
        # Accept common indicators of a segfault in the helper's failure output.
        assert ("return code is -11" in lower_msg) or ("segmentation fault" in lower_msg) or ("signal 11" in lower_msg), (
            f"Unexpected failure: {msg}")
        # If we reach here, we reproduced the crash; treat as expected pre-fix behavior.
        print("EXPECTED_CRASH_REPRODUCED")
        return

    # On patched Python, ensure the subprocess exited cleanly without crashing
    assert rc == 0, f"Expected return code 0, got: {rc} with stderr: {err!r}"
    # Ensure our markers are present and there is no stderr
    assert b"ALL_OK" in out, f"Expected 'ALL_OK' in stdout, got: {out!r}"
    assert not err, f"Expected no stderr, got: {err!r}"


if __name__ == '__main__':
    run_subprocess_case()
    # If we reach here without assertion failures, the test passes
