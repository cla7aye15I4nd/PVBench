from test.support.script_helper import assert_python_ok


def test_list_richcompare_use_after_free_regression():
    # This test verifies the fix for a use-after-free in list_richcompare_impl.
    # The bug could be triggered by comparing two lists where the element
    # comparison mutates (clears) one of the lists being compared. Prior to the
    # fix, CPython could crash/segfault due to borrowed references being used
    # after mutation. The patch increases the refcount of both items before the
    # final comparison, preventing the UAF.
    code = """if 1:
        # Base PoC: mutate the compared list (left list) via element __lt__
        class evil:
            def __lt__(self, other):
                # Mutate the list which is also the left parent list in the outer comparison
                other.clear()
                return NotImplemented

        a = [[evil()]]  # a[0] is the left-hand list being compared; a is the right-hand list
        try:
            a[0] < a
            raise AssertionError("Expected TypeError from list item comparison")
        except TypeError as e:
            # Ensure we indeed hit the comparison path that raises TypeError
            msg = str(e)
            assert ("not supported" in msg) or ("unorderable" in msg), f"Unexpected TypeError message: {msg}"
        # Ensure mutation happened so we know the dangerous path was executed
        assert a[0] == [], f"Expected inner list to be cleared, got: {a[0]}"

        # Edge case: ensure the fast-path skipping equal prefixes is taken, and then the final
        # item comparison (with the proper operator) still handles mutation safely.
        # Here, index 0 is equal (1 == 1), and at index 1 we compare evil() to the list 'b'.
        b = [1, evil()]
        c = [1, b]  # c[1] is 'b' itself, so element compare will get 'other' == b
        try:
            b < c
            raise AssertionError("Expected TypeError on b < c with equal prefix")
        except TypeError:
            pass
        assert b == [], f"Expected 'b' to be cleared, got: {b}"

        # Test for '>' operator: ensure we also cover the final-item compare using a different op
        class evilgt:
            def __gt__(self, other):
                other.clear()
                return NotImplemented

        d = [[evilgt()]]
        try:
            d[0] > d
            raise AssertionError("Expected TypeError on '>' comparison with mutation")
        except TypeError:
            pass
        assert d[0] == [], f"Expected inner list to be cleared in '>' case, got: {d[0]}"
        """

    rc, out, err = assert_python_ok('-c', code)
    assert rc == 0, f"Expected return code 0, got: {rc}"
    assert not err, f"Expected no stderr, got: {err}"
    # No output expected
    assert out == b'', f"Expected empty stdout, got: {out}"


if __name__ == '__main__':
    test_list_richcompare_use_after_free_regression()
    print('OK')
