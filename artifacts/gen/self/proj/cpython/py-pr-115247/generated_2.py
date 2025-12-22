# This generated test verifies the fix for a potential crash in collections.deque.index
# when the deque is mutated during the equality comparison. The upstream patch
# ensures a strong reference is held to the item being compared, preventing use-after-free
# and crashes, and the operation should raise RuntimeError("deque mutated during iteration").

from test.support.script_helper import assert_python_ok


def run_subprocess_test(code: str, expect_in_stdout: bytes = b"PASS"):
    """Run the provided code in a subprocess and assert it completes successfully
    with expected stdout and no stderr. This isolates potential crashes.
    """
    rc, out, err = assert_python_ok('-c', code)
    assert rc == 0, f"Expected return code 0, got: {rc}. stderr: {err!r}"
    assert expect_in_stdout in out, f"Expected {expect_in_stdout!r} in stdout, got: {out!r}"
    assert not err, f"Expected no stderr, got: {err!r}"


def test_clear_mutation_raises_runtimeerror_no_crash():
    # Mutate by clearing the deque during __eq__.
    code = """if 1:
        from collections import deque
        class A:
            def __eq__(self, other):
                d.clear()  # concurrent mutation
                return NotImplemented
        d = deque([A()])
        try:
            d.index(0)
        except RuntimeError as e:
            msg = str(e)
            assert "mutated during iteration" in msg, f"Expected 'mutated during iteration' in message, got: {msg!r}"
            print("PASS")
        else:
            raise AssertionError("Expected RuntimeError when deque is mutated during index comparison")
    """
    run_subprocess_test(code)


def test_popleft_mutation_raises_runtimeerror_no_crash():
    # Mutate by popleft during __eq__, on a longer deque so the mutation removes a different element.
    code = """if 1:
        from collections import deque
        class A:
            def __eq__(self, other):
                d.popleft()  # concurrent mutation of a separate element
                return NotImplemented
        d = deque([1, A(), 2])
        try:
            d.index(0)
        except RuntimeError as e:
            msg = str(e)
            assert "mutated during iteration" in msg, f"Expected 'mutated during iteration' in message, got: {msg!r}"
            print("PASS")
        else:
            raise AssertionError("Expected RuntimeError when deque is mutated during index comparison with popleft")
    """
    run_subprocess_test(code)


def test_rotate_mutation_raises_runtimeerror_no_crash():
    # Mutate by rotating during __eq__.
    code = """if 1:
        from collections import deque
        class A:
            def __eq__(self, other):
                d.rotate(1)  # concurrent mutation of order
                return NotImplemented
        d = deque([A(), 1])
        try:
            d.index(0)
        except RuntimeError as e:
            msg = str(e)
            assert "mutated during iteration" in msg, f"Expected 'mutated during iteration' in message, got: {msg!r}"
            print("PASS")
        else:
            raise AssertionError("Expected RuntimeError when deque is mutated during index comparison with rotate")
    """
    run_subprocess_test(code)


def test_clear_with_start_stop_raises_runtimeerror_no_crash():
    # Use start/stop parameters while mutating during comparison.
    code = """if 1:
        from collections import deque
        class A:
            def __eq__(self, other):
                d.clear()  # concurrent mutation
                return NotImplemented
        d = deque([1, A(), 2, 3])
        try:
            # broad start/stop to ensure we hit A.__eq__ and mutate mid-search
            d.index(0, -10, 10)
        except RuntimeError as e:
            msg = str(e)
            assert "mutated during iteration" in msg, f"Expected 'mutated during iteration' in message, got: {msg!r}"
            print("PASS")
        else:
            raise AssertionError("Expected RuntimeError when deque is mutated during index search with start/stop")
    """
    run_subprocess_test(code)


def test_non_mutating_case_still_works():
    # Sanity check: when not mutated, index should work normally.
    code = """if 1:
        from collections import deque
        d = deque([0, 1, 2])
        i = d.index(0)
        assert i == 0, f"Expected index 0, got: {i}"
        # Also ensure not-found raises ValueError, normal behavior
        try:
            d.index(99)
        except ValueError:
            print("PASS")
        else:
            raise AssertionError("Expected ValueError for missing element")
    """
    run_subprocess_test(code)


if __name__ == '__main__':
    # Run all tests
    test_clear_mutation_raises_runtimeerror_no_crash()
    test_popleft_mutation_raises_runtimeerror_no_crash()
    test_rotate_mutation_raises_runtimeerror_no_crash()
    test_clear_with_start_stop_raises_runtimeerror_no_crash()
    test_non_mutating_case_still_works()
    print("All subprocess tests passed.")
