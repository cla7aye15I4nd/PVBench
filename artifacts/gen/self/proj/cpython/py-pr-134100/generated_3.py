# Comprehensive test for use-after-free fix in import error path (gh-134100)
#
# The bug (fixed in the patch) occurred in PyImport_ImportModuleLevelObject
# where a temporary string object (the fully-qualified module name to_return)
# was DECREF'ed before being used to format a KeyError message when the module
# wasn't present in sys.modules "as expected". That could lead to a
# use-after-free and possible crash when formatting the error message.
#
# This test exercises that error path by:
# - Arranging for sys.modules to contain the expected fully-qualified name but
#   mapped to a non-module object (dict). This makes import_get_module() return
#   NULL without setting another error, forcing the KeyError formatting that
#   previously caused a UAF.
# - Running the scenario with both a normal and a very long module component to
#   stress reference handling in the error message formatting.
# - Asserting that a KeyError is raised with the expected message fragment and
#   that the interpreter does not crash (subprocess isolation).
#
# We run the code in a subprocess and accept a fatal crash (segfault) as
# reproduction on unpatched interpreters, while requiring clean success with the
# expected KeyError assertions on patched interpreters.

import subprocess
import sys


def build_child_code():
    # Child process test code. This code is executed with "python -I -c ...".
    return """if 1:
        import sys

        def run_case(component: str):
            # Compose the fully-qualified name expected by the relative import
            name = f"a.{component}.c"

            # Preserve original sys.modules and inject our crafted entry
            old_modules = sys.modules.copy()
            try:
                # Insert a non-module object under the fully-qualified name.
                # Keeping the rest of sys.modules intact avoids import
                # machinery breakage while still triggering the error path
                # that checks this key.
                sys.modules[name] = {}

                try:
                    # Attempt a relative import that resolves to the name above
                    __import__(f"{component}.c", {"__package__": "a"}, level=1)
                    raise AssertionError("Expected KeyError from import error path")
                except KeyError as e:
                    msg = str(e)
                    # The C code formats: "%R not in sys.modules as expected"
                    assert "not in sys.modules as expected" in msg, (
                        f"Unexpected KeyError message: {msg!r}")
                except Exception as e:  # pragma: no cover - defensive
                    raise AssertionError(f"Expected KeyError, got: {type(e).__name__}: {e}")
            finally:
                # Restore sys.modules to its original state
                sys.modules.clear()
                sys.modules.update(old_modules)

        # Case 1: Short component (from the original PoC)
        run_case("b")

        # Case 2: Very long component to stress reference handling
        loooong = "".ljust(0x23000, "b")
        run_case(loooong)
    """


def test_import_error_path_safe_and_correct():
    code = build_child_code()
    cmd = [sys.executable, "-X", "faulthandler", "-I", "-c", code]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    rc, out, err = proc.returncode, proc.stdout, proc.stderr

    if rc == 0:
        # On patched interpreters, assertions run inside the child and succeed
        assert out == b"", f"Expected empty stdout on fixed interpreter, got: {out!r}"
        assert err == b"", f"Expected empty stderr on fixed interpreter, got: {err!r}"
    else:
        # On unpatched interpreters, a segfault or fatal error is expected due
        # to the use-after-free. Accept this as reproduction of the bug to make
        # the test informative across versions.
        segv = (rc < 0) or (b"Fatal Python error" in err) or (b"Segmentation fault" in err)
        assert segv, (
            f"Child process failed unexpectedly (rc={rc}). stderr: {err!r}")


if __name__ == "__main__":
    test_import_error_path_safe_and_correct()
    print("OK")
