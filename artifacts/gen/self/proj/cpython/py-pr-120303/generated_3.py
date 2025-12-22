# This test verifies the fix for a use-after-free in list_richcompare_impl
# (Objects/listobject.c). The bug could be triggered by mutating lists during
# a list comparison when the final item comparison is re-attempted with the
# requested operator (e.g., <). The fix increfs the two items before calling
# PyObject_RichCompare to keep them alive even if the container list is mutated
# during comparison.
#
# We use subprocess isolation via test.support.script_helper.assert_python_ok
# to ensure that if there is a crash/segfault on buggy interpreters, it doesn't
# take down the whole test run. We assert that the code completes successfully
# and that the expected TypeError is raised (i.e., comparison between unrelated
# types when all __lt__ paths return NotImplemented).

from test.support.script_helper import assert_python_ok


def run_in_subprocess(code: str):
    rc, out, err = assert_python_ok('-c', code)
    assert rc == 0, f"Expected return code 0, got: {rc}"
    assert not err, f"Expected no stderr, got: {err}"
    return out


def test_poc_clears_sublist_other():
    # Original PoC: the element comparison calls evil.__lt__, which clears the
    # right-hand sublist (the item being compared), and returns NotImplemented.
    # On fixed Python this should not crash and should raise TypeError for the
    # unsupported comparison between evil and list.
    code = """if 1:
        class evil:
            def __lt__(self, other):
                other.clear()  # mutate the compared item (sublist)
                return NotImplemented

        a = [[evil()]]
        try:
            a[0] < a
            print("NO_EXCEPTION")
        except TypeError:
            print("TYPEERROR")
    """
    out = run_in_subprocess(code)
    assert b"TYPEERROR" in out, f"Expected TypeError to be caught, stdout: {out!r}"
    assert b"NO_EXCEPTION" not in out, f"Unexpectedly no exception, stdout: {out!r}"


def test_mutate_outer_right_list_during_compare():
    # Stronger variant: mutate the right-hand OUTER list during the final
    # comparison of items. This used to risk a UAF if the items were not kept
    # alive across the PyObject_RichCompare call.
    code = """if 1:
        class Evil:
            def __lt__(self, other):
                a.clear()  # mutate the outer right-hand list during comparison
                return NotImplemented

        a = [[Evil()]]
        try:
            a[0] < a
            print("NO_EXCEPTION")
        except TypeError:
            print("TYPEERROR")
        print("LEN:", len(a))  # ensure the mutation actually happened
    """
    out = run_in_subprocess(code)
    assert b"TYPEERROR" in out, f"Expected TypeError when comparing, stdout: {out!r}"
    assert b"LEN: 0" in out, f"Expected right outer list to be cleared, stdout: {out!r}"
    assert b"NO_EXCEPTION" not in out, f"Unexpectedly no exception, stdout: {out!r}"


def test_mutate_outer_left_list_during_compare():
    # Mutate the left-hand OUTER list during the final comparison of items.
    # The fix should cover both sides being mutated.
    code = """if 1:
        # global L will be mutated from within Evil.__lt__
        L = None

        class Evil:
            def __lt__(self, other):
                # mutate the outer left-hand list during comparison
                L.clear()
                return NotImplemented

        # Build left and right lists so that the first comparison is between an
        # Evil instance and a sublist; the comparison will then call __lt__.
        L = [Evil()]
        R = [[]]  # a simple sublist on the right is enough to trigger the path
        try:
            L < R  # triggers final comparison with '<' and calls Evil.__lt__
            print("NO_EXCEPTION")
        except TypeError:
            print("TYPEERROR")
        print("LEN:", len(L))  # ensure the mutation actually happened
    """
    out = run_in_subprocess(code)
    assert b"TYPEERROR" in out, f"Expected TypeError when comparing with '<', stdout: {out!r}"
    assert b"LEN: 0" in out, f"Expected left outer list to be cleared, stdout: {out!r}"
    assert b"NO_EXCEPTION" not in out, f"Unexpectedly no exception, stdout: {out!r}"


if __name__ == '__main__':
    # Run tests
    test_poc_clears_sublist_other()
    test_mutate_outer_right_list_during_compare()
    test_mutate_outer_left_list_during_compare()
    # If we reach here without crash and assertions hold, the fix works.
    print("OK")
