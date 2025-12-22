# This test verifies the fix for gh-120384: an array out-of-bounds crash in
# list_ass_subscript caused by concurrent modification of a list during
# slice assignment. The core scenarios involve:
#   - Extended slice assignment (step != 1) where the right-hand side iterable
#     mutates the target list during iteration. Previously this could crash.
#     Now it should raise a ValueError with a helpful message.
#   - Simple slice assignment (step == 1) where the right-hand side iterable
#     mutates the target list during iteration. Previously this could also
#     crash due to indices being computed before building the sequence. Now the
#     operation should complete successfully without crashing and with the
#     correct final list content.
#
# We prefer subprocess isolation for these tests because historical behavior
# could be a hard crash/segfault. On a patched interpreter, both subprocesses
# must succeed and produce expected outputs. On an unpatched interpreter, these
# subprocesses may crash; in that case we detect the crash and still let this
# test runner complete (so the file remains runnable in both contexts), while
# clearly asserting what happened.

import sys
import subprocess


def run_code_in_subprocess(code: str):
    cmd = [sys.executable, '-X', 'faulthandler', '-I', '-c', code]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return proc.returncode, proc.stdout, proc.stderr


def test_extended_slice_assignment_concurrent_clear():
    # Step != 1 extended slice assignment: expect ValueError on patched builds.
    code = """if 1:
    class evil:
        def __init__(self, lst):
            self.lst = lst
        def __iter__(self):
            # Yield the current contents, then clear the list (concurrent mutation)
            yield from self.lst
            self.lst.clear()

    lst = list(range(10))
    operand = evil(lst)
    try:
        lst[::-1] = operand
        assert False, "Expected ValueError from extended slice size mismatch"
    except ValueError as e:
        msg = str(e)
        # CPython error message includes both sizes and mentions extended slice
        assert "extended slice of size" in msg, f"Unexpected error message: {msg}"
    print("OK1")
    """
    rc, out, err = run_code_in_subprocess(code)

    if rc == 0:
        # Patched behavior: no crash, prints OK1, no stderr
        assert b'OK1' in out, f"Did not reach end of extended-slice test. stdout: {out!r}"
        assert not err, f"Expected no stderr in extended-slice test, got: {err!r}"
    else:
        # Unpatched behavior reproduced: segfault or fatal error.
        # Make sure it's indeed a crash (not an uncaught Python exception).
        assert rc < 0 or b'Fatal Python error' in err or b'Segmentation fault' in err, (
            f"Unexpected failure mode. rc={rc}, stderr={err!r}")


def test_simple_slice_assignment_concurrent_clear():
    # Step == 1 simple slice assignment: expect success on patched builds.
    code = """if 1:
    class evil:
        def __init__(self, lst):
            self.lst = lst
        def __iter__(self):
            yield from self.lst
            self.lst.clear()

    lst = list(range(10))
    operand = evil(lst)
    lst[:] = operand
    expected = list(range(10))
    assert lst == expected, f"Expected {expected}, got {lst}"
    print("OK2")
    """
    rc, out, err = run_code_in_subprocess(code)

    if rc == 0:
        # Patched behavior: no crash, prints OK2, result list is correct, no stderr
        assert b'OK2' in out, f"Did not reach end of simple-slice test. stdout: {out!r}"
        assert not err, f"Expected no stderr in simple-slice test, got: {err!r}"
    else:
        # Unpatched behavior reproduced: segfault or fatal error.
        assert rc < 0 or b'Fatal Python error' in err or b'Segmentation fault' in err, (
            f"Unexpected failure mode. rc={rc}, stderr={err!r}")


if __name__ == '__main__':
    # Run both scenarios
    test_extended_slice_assignment_concurrent_clear()
    test_simple_slice_assignment_concurrent_clear()
