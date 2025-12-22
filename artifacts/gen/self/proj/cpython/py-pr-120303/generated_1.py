# Comprehensive test for use-after-free fix in list_richcompare_impl
# This test exercises comparisons between lists where the item comparison
# mutates (clears) one of the lists during the comparison, which previously
# could trigger a use-after-free. The patch adds INCREFs to the items before
# the final comparison, preventing crashes.

from test.support.script_helper import assert_python_ok


def run_crash_isolation_tests():
    # Use subprocess isolation because the original bug could segfault.
    code = """if 1:
        # Case 1: Mutate the left-hand list (aliasing scenario)
        # The 'other' passed to __lt__ is the right-hand item, which in this
        # construction aliases the left list itself (a[0] is the same object
        # on both sides). Clearing it during comparison used to corrupt state.
        class Evil:
            def __lt__(self, other):
                other.clear()  # clears the aliased list used in comparison
                return NotImplemented

        a = [[Evil()]]
        try:
            a[0] < a
            raise AssertionError("Expected TypeError in aliasing-left mutation case")
        except TypeError:
            print("ok1")

        # Case 2: Mutate the right-hand list (outer container) during comparison
        # Here, we clear the outer list being compared. The patch must ensure
        # items used for the final compare are kept alive (INCREFed).
        holder = {}
        class Evil2:
            def __lt__(self, other):
                holder['outer'].clear()  # clears the right-hand list container
                return NotImplemented

        b = [[Evil2()]]
        holder['outer'] = b
        try:
            b[0] < b
            raise AssertionError("Expected TypeError when outer list cleared during compare")
        except TypeError:
            print("ok2")

        # Case 3: Use a different operator (<=) to ensure the final comparison
        # path also handles mutation safely and raises TypeError instead of crashing.
        c = [[Evil()]]
        try:
            c[0] <= c
            raise AssertionError("Expected TypeError with <= operator during mutation")
        except TypeError:
            print("ok3")
    """

    rc, out, err = assert_python_ok('-c', code)
    assert rc == 0, f"Expected return code 0, got: {rc}"
    # Ensure all markers printed (no crash and correct exception behavior)
    assert b"ok1" in out, f"Missing ok1 marker in stdout, got: {out!r}"
    assert b"ok2" in out, f"Missing ok2 marker in stdout, got: {out!r}"
    assert b"ok3" in out, f"Missing ok3 marker in stdout, got: {out!r}"
    assert not err, f"Expected no stderr, got: {err!r}"


def main():
    run_crash_isolation_tests()


if __name__ == '__main__':
    main()
