# This test exercises a historical use-after-free bug in list comparisons (list_richcompare_impl)
# where comparing the final differing items could access freed memory if a user-defined
# comparison mutated (e.g., cleared) one of the lists during the preliminary equality checks.
#
# The patch IncRefs the items before re-comparing them with the requested operator, ensuring
# they stay alive even if the container list is mutated during comparison.
#
# We verify:
# - The original PoC no longer crashes and raises the expected TypeError.
# - Mutations during the equality check phase (clearing either the left or right list)
#   do not crash and produce a deterministic boolean result for the comparison.

from test.support.script_helper import assert_python_ok


def run_in_subprocess_and_check():
    code = """if 1:
        # Test 1: Original PoC from the report - should raise TypeError, not crash.
        class evil:
            def __lt__(self, other):
                # Mutate the other operand (a list) during comparison
                other.clear()
                return NotImplemented

        a = [[evil()]]
        try:
            a[0] < a
            raise AssertionError("Expected TypeError from comparing list and custom object")
        except TypeError:
            print("T1 OK")

        # Test 2: Mutate the LEFT container during the preliminary equality check.
        # The equality check should call __eq__ first, which clears the left list.
        # Then the final item comparison should use the requested operator safely.
        class Mut:
            def __init__(self, to_clear, result_lt):
                self.to_clear = to_clear
                self.result_lt = result_lt
            def __eq__(self, other):
                # Mutate during equality check to simulate the UAF scenario
                self.to_clear.clear()
                return False  # Force inequality so the final comparison is performed
            def __lt__(self, other):
                return self.result_lt

        left = []
        left.append(Mut(left, True))
        right = [Mut(left, True)]
        # During left[0] == right[0], left is cleared; then left[0] < right[0] returns True
        print("T2", left < right)

        # Test 3: Mutate the RIGHT container during the preliminary equality check (clear 'right').
        right2 = []
        # Prepare the list first so we can reference it from the object
        item_left = Mut(right2, False)  # __lt__ returns False for determinism
        right2.append(Mut(right2, False))
        left2 = [item_left]
        # During left2[0] == right2[0], right2 is cleared; final compare uses cached items and returns False
        print("T3", left2 < right2)
    """

    rc, out, err = assert_python_ok('-c', code)

    assert rc == 0, f"Expected return code 0, got: {rc}"
    assert b"T1 OK" in out, f"Did not see PoC TypeError confirmation in stdout. Got: {out!r}"
    assert b"T2 True" in out, f"Expected 'T2 True' in stdout, got: {out!r}"
    assert b"T3 False" in out, f"Expected 'T3 False' in stdout, got: {out!r}"
    assert not err, f"Expected no stderr, got: {err!r}"


if __name__ == '__main__':
    run_in_subprocess_and_check()
