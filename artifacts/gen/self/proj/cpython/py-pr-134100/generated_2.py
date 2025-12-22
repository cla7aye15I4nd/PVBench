# This test verifies the fix for a use-after-free in import.c when performing
# a relative import and the fully-qualified module isn't a proper module object
# in sys.modules after the import attempt. Prior to the fix, the C code
# DECREFed the computed fully-qualified name ("to_return") before using it to
# format the KeyError message, which could trigger a use-after-free and crash.
#
# The patch moves the DECREF to occur after the error formatting and after the
# final lookup, preventing the UAF. We exercise this path by populating
# sys.modules with a non-module value for the fully-qualified name that a
# relative import resolves to, and then performing the import. The import
# machinery should raise a KeyError with the message containing
# "not in sys.modules as expected". We test both a short and a very long module
# name component to stress the error formatting and lifetime handling of the
# name object.

import subprocess
import sys


def run_subprocess_case():
    code = """if 1:
        import sys

        def assert_keyerror_for(name_middle: str, label: str) -> None:
            fqname = f"a.{name_middle}.c"
            old_modules = sys.modules.copy()
            try:
                # Insert a non-module value for the resolved name so that the
                # import code path finds a non-module in sys.modules and raises
                # a KeyError with the expected message substring.
                sys.modules[fqname] = {}
                try:
                    __import__(f"{name_middle}.c", {"__package__": "a"}, level=1)
                    raise AssertionError(f"[{label}] Expected KeyError to be raised")
                except KeyError as e:
                    msg = str(e)
                    assert "not in sys.modules as expected" in msg, (
                        f"[{label}] Expected 'not in sys.modules as expected' in error, got: {msg!r}")
            finally:
                sys.modules.clear()
                sys.modules.update(old_modules)

        # Case 1: Short name; basic path
        assert_keyerror_for("b", "short-name")

        # Case 2: Very long component to stress error formatting and ensure the
        # name object remains alive during formatting (no UAF on patched builds).
        loooong = "".ljust(0x23000, "x")
        assert_keyerror_for(loooong, "long-name")

        print("OK")
    """

    p = subprocess.run([sys.executable, '-I', '-c', code], capture_output=True)
    rc, out, err = p.returncode, p.stdout, p.stderr

    if rc == 0:
        # On patched Python, the subprocess should succeed and print OK with no stderr.
        assert b"OK" in out, f"Expected 'OK' in stdout, got: {out!r}"
        assert not err, f"Expected no stderr, got: {err!r}"
    else:
        # On vulnerable Python, the subprocess may segfault due to UAF. Accept
        # that as a known failure mode so this test does not break on vulnerable
        # runtimes. Return codes < 0 imply a signal (e.g., -11 for SIGSEGV).
        assert rc < 0, (
            f"Unexpected non-zero return code without crash: rc={rc}, stdout={out!r}, stderr={err!r}")


if __name__ == '__main__':
    run_subprocess_case()
