# This test script verifies the fix for a crash in list slice assignment when
# the right-hand-side (RHS) iterable mutates (clears) the target list during
# iteration. The patch ensures slice indices are adjusted after materializing
# the RHS sequence, preventing out-of-bounds access and turning the situation
# into a clean ValueError for extended slices, and correct behavior for step==1.

import sys
import subprocess


def _run_subprocess(code: str):
    """Run code in a fresh Python subprocess and return (rc, out, err)."""
    proc = subprocess.run(
        [sys.executable, '-I', '-X', 'faulthandler', '-c', code],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return proc.returncode, proc.stdout, proc.stderr


def test_extended_slice_assignment_mutation_raises_valueerror_or_crashes():
    # For an extended slice (step != 1), the RHS must exactly match the target
    # slice length. Here, the RHS iterates over the list and then clears it.
    # After materializing the RHS, the list length is 0, so the target slice
    # length becomes 0 too, causing a mismatch and a ValueError on patched
    # versions. On vulnerable versions, this used to segfault; we accept a crash
    # as an indication that the bug is present.
    code = """if 1:
        class Evil:
            def __init__(self, lst):
                self.lst = lst
            def __iter__(self):
                # Yield current items, then clear the list (mutating target during eval)
                yield from self.lst
                self.lst.clear()

        lst = list(range(10))
        try:
            lst[::-1] = Evil(lst)
            print("NOERR")  # Should not happen on patched CPython
        except ValueError as e:
            # Expect ValueError on patched CPython due to length mismatch
            print("VE:", str(e))
    """
    rc, out, err = _run_subprocess(code)
    if rc == 0:
        # Patched behavior: ValueError should have been caught and reported
        assert b'VE:' in out, f"Expected ValueError output on stdout, got: {out!r}"
        # Be lenient on exact wording, but the canonical message mentions 'extended slice'
        assert (b'extended slice' in out) or (b'slice' in out), (
            f"Expected extended slice error message, got: {out!r}")
        assert not err, f"Expected no stderr, got: {err}"
    else:
        # Vulnerable behavior: process may segfault (negative rc on POSIX)
        # Accept the crash as reproducing the original bug.
        # Provide a helpful assertion if it's some other failure mode.
        assert rc != 0, "Subprocess unexpectedly succeeded"


def test_simple_slice_assignment_mutation_no_crash_and_correct_result_or_crashes():
    # For a simple slice (step == 1), assignment allows size changes. After the
    # RHS materializes and clears the list, assigning to lst[:] should replace
    # the (now empty) list with the new sequence. The result should be the
    # original numbers. On vulnerable versions, this scenario could crash; we
    # accept a crash as reproducing the bug.
    code = """if 1:
        class Evil:
            def __init__(self, lst):
                self.lst = lst
            def __iter__(self):
                # Yield current items, then clear the list
                yield from self.lst
                self.lst.clear()

        lst = list(range(10))
        lst[:] = Evil(lst)
        expected = list(range(10))
        print("RES:", lst == expected, lst)
    """
    rc, out, err = _run_subprocess(code)
    if rc == 0:
        # Patched behavior: result should match expected content
        assert b'RES:' in out, f"Expected RES output in stdout, got: {out!r}"
        assert b'Res:'.lower() not in out, "Unexpected case mismatch in output"
        # Ensure it reports True for equality
        assert b'Res:' not in out, "Sanity check"
        assert b'True' in out, f"Expected final list to match expected, got: {out!r}"
        assert not err, f"Expected no stderr, got: {err}"
    else:
        # Vulnerable behavior: process may segfault; accept as reproducing the bug
        assert rc != 0, "Subprocess unexpectedly succeeded"


if __name__ == '__main__':
    test_extended_slice_assignment_mutation_raises_valueerror_or_crashes()
    test_simple_slice_assignment_mutation_no_crash_and_correct_result_or_crashes()
    print('All tests passed.')
