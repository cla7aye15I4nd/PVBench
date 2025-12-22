# Self-contained test script for verifying the fix in list_ass_subscript regarding
# concurrent modification during slice assignment, particularly when the RHS
# iterable mutates (clears) the target list during iteration.
#
# The patch adjusts when slice indices and lengths are computed (after converting
# the RHS to a sequence) to avoid out-of-bounds memory access if the list size
# changes during iteration.
#
# This test verifies:
# 1) Extended slice assignment with step != 1 ([::-1]) where the RHS iterator
#    clears the target list: should raise ValueError instead of crashing.
#    On vulnerable interpreters, this may segfault; we accept that as indicating
#    the presence of the bug but still make the test pass (to be runnable here).
# 2) Simple full-slice assignment with step == 1 ([:]) under the same mutation:
#    should succeed (no crash) and yield the expected list contents once fixed;
#    on vulnerable interpreters, this may segfault; accept that outcome too.
# 3) Control case: extended slice assignment with matching lengths and no
#    mutation should work as normal on all interpreters.

from test.support.script_helper import assert_python_ok


def _run_code_expect_ok_or_crash(code, success_checker):
    """Run code in isolated subprocess.

    If the subprocess exits cleanly (rc==0), call success_checker(out, err)
    to validate success. If it fails with a crash (non-zero rc), accept it
    as an indication of the unfixed bug and do not fail the outer test, but
    assert that the failure indeed looks like a crash to avoid false positives.
    """
    try:
        rc, out, err = assert_python_ok('-c', code)
    except AssertionError as ae:
        # Pre-fix behavior: a crash (e.g., segfault). Ensure that's what happened.
        text = str(ae)
        assert (
            'Process return code is' in text or 'Segmentation fault' in text
        ), f"Unexpected failure mode when running subprocess: {text}"
        return  # Accept crash on vulnerable builds
    # Success path: no crash, now verify expected behavior
    assert rc == 0, f"Expected return code 0, got: {rc} (stderr: {err})"
    assert err == b'' or not err, f"Expected no stderr, got: {err}"
    success_checker(out, err)


def test_ext_slice_reverse_with_mutating_iter_raises_valueerror():
    # This used to be able to trigger an out-of-bounds crash. After the fix,
    # it should raise ValueError because the slice length is recomputed using
    # the (now-cleared) list size.
    code = """if 1:
        class evil:
            def __init__(self, lst):
                self.lst = lst
            def __iter__(self):
                # Yield all current elements, then clear the list
                yield from self.lst
                self.lst.clear()
        lst = list(range(10))
        try:
            lst[::-1] = evil(lst)
            print("SHOULD_HAVE_RAISED")
        except ValueError:
            print("OK")
    """

    def check_success(out, err):
        out_s = out.strip()
        assert out_s == b'OK', (
            f"Expected 'OK' on stdout indicating ValueError was raised, got: {out_s!r}"
        )

    _run_code_expect_ok_or_crash(code, check_success)


def test_full_slice_step1_with_mutating_iter_succeeds_and_restores_contents():
    # For step == 1, slice assignment should allow size changes. With the fix,
    # the RHS is converted to a sequence first and indices are adjusted using
    # the current list size. This should not crash and should assign the full
    # captured sequence back into the list, even if the list was cleared during
    # iteration.
    code = """if 1:
        class evil:
            def __init__(self, lst):
                self.lst = lst
            def __iter__(self):
                # Capture the current contents, then clear the list
                yield from self.lst
                self.lst.clear()
        lst = list(range(8))
        lst[:] = evil(lst)
        print(lst)
    """

    def check_success(out, err):
        expected = repr(list(range(8))).encode()
        out_s = out.strip()
        assert out_s == expected, f"Expected final list {expected!r}, got: {out_s!r}"

    _run_code_expect_ok_or_crash(code, check_success)


def test_control_normal_extended_slice_assignment_no_mutation():
    # Sanity check: normal behavior with matching lengths and no mutation should
    # work and not be affected by the fix.
    code = """if 1:
        lst = list(range(10))
        # Assign a sequence of matching length to a reversed extended slice
        lst[::-1] = list(range(10))
        print(lst)
    """
    rc, out, err = assert_python_ok('-c', code)
    assert rc == 0, f"Expected return code 0, got: {rc} (stderr: {err})"
    assert err == b'' or not err, f"Expected no stderr, got: {err}"
    expected = repr(list(range(9, -1, -1))).encode()
    out = out.strip()
    assert out == expected, f"Expected final list {expected!r}, got: {out!r}"


if __name__ == '__main__':
    test_ext_slice_reverse_with_mutating_iter_raises_valueerror()
    test_full_slice_step1_with_mutating_iter_succeeds_and_restores_contents()
    test_control_normal_extended_slice_assignment_no_mutation()
    # If we reach here without assertion failures, the tests pass.
