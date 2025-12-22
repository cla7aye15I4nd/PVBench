# This test verifies the fix for a use-after-free in list_richcompare_impl.
# The bug could be triggered when the final element-wise comparison between two
# lists ends up calling a user-defined rich comparison that mutates (clears)
# one of the lists being compared. The patch adds INCREF/DECREF around the
# final items before comparing them to avoid use-after-free.
#
# We use subprocess isolation via assert_python_ok because the unfixed bug could
# crash the interpreter. We assert that:
# - The comparisons do not crash.
# - The appropriate TypeError is raised when the element-wise comparison returns
#   NotImplemented (common behavior when comparing unrelated types).
# - Side effects (clearing the list) actually occurred, proving the path was hit.
# - A variant where the comparison returns a concrete boolean also works and
#   yields the expected result without crashing.

from test.support.script_helper import assert_python_ok


def test_lt_notimplemented_mutates_other():
    # This triggers the final-item comparison for '<'. The element comparator
    # clears the other list and returns NotImplemented, so list comparison
    # should raise TypeError but not crash, and the inner list should be cleared.
    code = """if 1:
        class Evil:
            def __lt__(self, other):
                # Mutate the other operand (list) during comparison
                other.clear()
                return NotImplemented

        a = [[Evil()]]
        try:
            a[0] < a
        except TypeError:
            # Ensure side-effect happened (inner list cleared)
            print("OK_LT", a)
        else:
            print("NO_TYPEERROR", a)
    """
    rc, out, err = assert_python_ok('-c', code)
    assert rc == 0, f"Expected return code 0, got: {rc}"
    assert b'OK_LT' in out, f"Expected TypeError to be caught and 'OK_LT' in stdout, got: {out!r}"
    assert b'[[]]' in out, f"Expected mutated list representation '[[]]' in stdout, got: {out!r}"
    assert not err, f"Expected no stderr, got: {err!r}"


def test_gt_notimplemented_mutates_other():
    # Same as above but for the '>' operator, invoking __gt__.
    code = """if 1:
        class Evil:
            def __gt__(self, other):
                # Mutate the other operand (list) during comparison
                other.clear()
                return NotImplemented

        a = [[Evil()]]
        try:
            a[0] > a
        except TypeError:
            # Ensure side-effect happened (inner list cleared)
            print("OK_GT", a)
        else:
            print("NO_TYPEERROR", a)
    """
    rc, out, err = assert_python_ok('-c', code)
    assert rc == 0, f"Expected return code 0, got: {rc}"
    assert b'OK_GT' in out, f"Expected TypeError to be caught and 'OK_GT' in stdout, got: {out!r}"
    assert b'[[]]' in out, f"Expected mutated list representation '[[]]' in stdout, got: {out!r}"
    assert not err, f"Expected no stderr, got: {err!r}"


def test_lt_boolean_result_after_mutation():
    # Variant where the element comparator mutates the other list but returns
    # a concrete boolean (False). The comparison should succeed and return False
    # without crashing, and the inner list should still be cleared.
    code = """if 1:
        class Evil:
            def __lt__(self, other):
                other.clear()
                return False  # Explicit boolean result

        a = [[Evil()]]
        res = a[0] < a
        print("RES_LT", res, a)
    """
    rc, out, err = assert_python_ok('-c', code)
    assert rc == 0, f"Expected return code 0, got: {rc}"
    assert b'RES_LT False' in out, f"Expected 'RES_LT False' in stdout, got: {out!r}"
    assert b'[[]]' in out, f"Expected mutated list representation '[[]]' in stdout, got: {out!r}"
    assert not err, f"Expected no stderr, got: {err!r}"


if __name__ == '__main__':
    # Run tests
    test_lt_notimplemented_mutates_other()
    test_gt_notimplemented_mutates_other()
    test_lt_boolean_result_after_mutation()
    print('All tests passed.')
