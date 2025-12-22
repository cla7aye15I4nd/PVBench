from test.support.script_helper import assert_python_ok

# This test verifies the fix for possible crashes in collections.deque.index when
# the deque is mutated concurrently during comparisons (GH-115243).
#
# Prior to the fix, deque.index could crash if the deque was modified inside
# an element's __eq__. The fix ensures the item being compared is strongly
# referenced during comparison, preventing use-after-free and turning such
# situations into a safe RuntimeError instead of a crash.
#
# We run the potentially crashing scenarios in a subprocess using
# assert_python_ok to guarantee process isolation and to detect crashes.

def run_subprocess_tests():
    code = """if 1:
        from collections import deque

        # T1: Mutation via clear() in __eq__ should not crash and should raise RuntimeError
        class A1:
            def __eq__(self, other):
                d.clear()
                return NotImplemented
        d = deque([A1()])
        try:
            d.index(0)
            raise AssertionError("T1: Expected RuntimeError when deque is mutated during index() via clear()")
        except RuntimeError:
            print("T1_OK")

        # T2: Sanity check: normal behavior without mutation
        d = deque([1, 2, 3, 4])
        res = d.index(3)
        assert res == 2, f"T2: Expected index 2, got {res}"
        print("T2_OK")

        # T3: Mutation via append() in __eq__ should raise RuntimeError (no crash)
        class A3:
            def __eq__(self, other):
                d.append(99)
                return NotImplemented
        d = deque([A3(), 0])
        try:
            d.index(1)
            raise AssertionError("T3: Expected RuntimeError when deque is mutated during index() via append()")
        except RuntimeError:
            print("T3_OK")

        # T4: Mutation via popleft() in __eq__ with a start argument should raise RuntimeError (no crash)
        class A4:
            def __eq__(self, other):
                d.popleft()
                return NotImplemented
        d = deque([1, A4(), 2, 3])
        try:
            d.index(0, 1)  # start searching at position 1 where A4() resides
            raise AssertionError("T4: Expected RuntimeError when deque is mutated during index() via popleft() with start")
        except RuntimeError:
            print("T4_OK")
    """

    rc, out, err = assert_python_ok('-c', code)

    # Validate subprocess execution
    assert rc == 0, f"Expected return code 0, got: {rc}"
    assert b'T1_OK' in out, f"Missing T1_OK in stdout. Got: {out!r}"
    assert b'T2_OK' in out, f"Missing T2_OK in stdout. Got: {out!r}"
    assert b'T3_OK' in out, f"Missing T3_OK in stdout. Got: {out!r}"
    assert b'T4_OK' in out, f"Missing T4_OK in stdout. Got: {out!r}"
    assert not err, f"Expected no stderr, got: {err!r}"


if __name__ == '__main__':
    run_subprocess_tests()
