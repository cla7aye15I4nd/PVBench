from test.support.script_helper import assert_python_ok

# This test verifies the fix for a use-after-free in list_richcompare when
# element comparisons mutate one of the lists (e.g., clearing it) during
# the final comparison step. The patch adds INCREFs to the items that are
# compared again so that mutations during rich comparison do not lead to
# use-after-free or crashes.
#
# We run the tests in a subprocess to guard against potential crashes on
# vulnerable interpreters. We assert that comparisons either raise
# TypeError or safely produce a boolean result, and that the interpreter
# does not crash or write to stderr.


def run_subprocess_tests():
    code = """if 1:
        def check_raises_typeerror(fn, label):
            try:
                fn()
                raise AssertionError(f"{label}: Expected TypeError")
            except TypeError:
                pass

        def check_boolean_result(fn, label):
            try:
                res = fn()
            except Exception as e:
                raise AssertionError(f"{label}: Expected boolean result without exception, got {type(e).__name__}: {e}")
            assert isinstance(res, bool), f"{label}: Expected bool result, got {type(res).__name__}: {res!r}"

        # Basic PoC: mutate the right-hand element during __lt__
        class EvilLT:
            def __lt__(self, other):
                other.clear()
                return NotImplemented

        a = [[EvilLT()]]
        check_raises_typeerror(lambda: (a[0] < a), "basic < with item clearing other")

        # Exercise all ordering operators, where the element clears the other
        class EvilAll:
            def __lt__(self, other):
                other.clear()
                return NotImplemented
            def __le__(self, other):
                other.clear()
                return NotImplemented
            def __gt__(self, other):
                other.clear()
                return NotImplemented
            def __ge__(self, other):
                other.clear()
                return NotImplemented

        b = [[EvilAll()]]
        check_raises_typeerror(lambda: (b[0] <= b), "<= with item clearing other")
        c = [[EvilAll()]]
        check_raises_typeerror(lambda: (c[0] > c), "> with item clearing other")
        d = [[EvilAll()]]
        check_raises_typeerror(lambda: (d[0] >= d), ">= with item clearing other")

        # Mutation during the equality check before the final operator compare.
        # Some Python versions may return a boolean rather than raising, but the
        # critical part is that there is no crash.
        class EvilEqThenLt:
            def __init__(self):
                self.cleared = False
            def __eq__(self, other):
                other.clear()  # mutate during the EQ pass in list_richcompare
                self.cleared = True
                return False   # force the "final item compare" path
            def __lt__(self, other):
                assert self.cleared, "__eq__ did not run before __lt__"
                return NotImplemented

        e = EvilEqThenLt()
        e_list = [e]
        big = [e_list]
        check_boolean_result(lambda: (e_list < big), "__eq__ mutation before final compare")

        # Mutate the outer (right) container during comparison
        class MutateOuter:
            def __init__(self, target=None):
                self.target = target
            def __lt__(self, other):
                # Clear the target container (if set); otherwise clear the other
                if self.target is not None:
                    self.target.clear()
                else:
                    other.clear()
                return NotImplemented

        outer = []
        m = MutateOuter(outer)
        inner = [m]
        outer.append(inner)
        # Compare inner list vs the outer list, mutating the outer list during item compare
        check_raises_typeerror(lambda: (inner < outer), "mutate outer right list in __lt__")

        # Mutate the outer (left) container via reversed comparison path
        outer2 = []
        m2 = MutateOuter()
        inner2 = [m2]
        outer2.append(inner2)
        # Configure m2 to clear the left (outer2) when its __lt__ is invoked via reversed op
        m2.target = outer2
        # Comparing list > list will end up calling m2.__lt__(left_item) in the element-wise step
        check_raises_typeerror(lambda: (outer2 > inner2), "mutate outer left list via reversed op")

        print("ALL_OK")
    """

    rc, out, err = assert_python_ok('-c', code)
    assert rc == 0, f"Expected return code 0, got: {rc}"
    assert b'ALL_OK' in out, f"Expected 'ALL_OK' in stdout, got: {out!r}"
    assert not err, f"Expected no stderr, got: {err!r}"


if __name__ == '__main__':
    run_subprocess_tests()
