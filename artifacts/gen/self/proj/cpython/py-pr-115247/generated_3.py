# Self-contained test verifying fix for deque.index mutation handling
# The bug fix ensures collections.deque.index does not crash when the deque
# is mutated during item comparison. The expected behavior is to raise
# RuntimeError ("deque mutated during iteration") rather than crashing.

from test.support.script_helper import assert_python_ok


def run_subprocess_tests():
    code = """if 1:
        from collections import deque
        import sys

        results = []

        # Test 1: Single-element deque, __eq__ clears deque during index search
        class A:
            def __eq__(self, other):
                d.clear()  # concurrent modification
                return NotImplemented
        d = deque([A()])
        try:
            d.index(0)
            results.append("t1:FAIL-no-error")
        except RuntimeError:
            results.append("t1:OK")
        except Exception as e:
            results.append(f"t1:FAIL-{type(e).__name__}:{e}")

        # Test 2: Multi-element deque, mid comparison triggers clear()
        class B:
            def __eq__(self, other):
                d.clear()
                return NotImplemented
        d = deque([0, B(), 1, 2])
        try:
            d.index(2)
            results.append("t2:FAIL-no-error")
        except RuntimeError:
            results.append("t2:OK")
        except Exception as e:
            results.append(f"t2:FAIL-{type(e).__name__}:{e}")

        # Test 3: Using start argument so the first compared element mutates
        class C:
            def __eq__(self, other):
                d.clear()
                return NotImplemented
        d = deque([99, C(), 100])
        try:
            d.index(100, 1)
            results.append("t3:FAIL-no-error")
        except RuntimeError:
            results.append("t3:OK")
        except Exception as e:
            results.append(f"t3:FAIL-{type(e).__name__}:{e}")

        # Test 4: Different mutation pattern: pop during comparison
        class D:
            def __eq__(self, other):
                # mutate without clearing: remove one element
                try:
                    d.popleft()
                except IndexError:
                    pass
                return NotImplemented
        d = deque([D(), 1, 2, 3])
        try:
            d.index(None)
            results.append("t4:FAIL-no-error")
        except RuntimeError:
            results.append("t4:OK")
        except Exception as e:
            results.append(f"t4:FAIL-{type(e).__name__}:{e}")

        # Control tests to ensure normal behavior unaffected by the fix
        # Test 5: Normal successful search
        d = deque([10, 20, 30])
        try:
            idx = d.index(30)
            if idx == 2:
                results.append("t5:OK")
            else:
                results.append(f"t5:FAIL-wrong-index:{idx}")
        except Exception as e:
            results.append(f"t5:FAIL-{type(e).__name__}:{e}")

        # Test 6: Value not found raises ValueError
        d = deque([1, 2, 3])
        try:
            d.index(99)
            results.append("t6:FAIL-no-ValueError")
        except ValueError:
            results.append("t6:OK")
        except Exception as e:
            results.append(f"t6:FAIL-{type(e).__name__}:{e}")

        # Emit results for the outer test to assert on
        for r in results:
            print(r)
    """

    rc, out, err = assert_python_ok('-c', code)
    assert rc == 0, f"Expected return code 0, got: {rc}"
    assert err == b'' or not err, f"Expected no stderr, got: {err}"

    out_lines = out.decode().strip().splitlines()
    # Collect results into a dict for easy checks
    results = {line.split(':', 1)[0]: line for line in out_lines}

    # Ensure all tests ran
    expected_keys = {f"t{i}" for i in range(1, 7)}
    assert expected_keys.issubset(results.keys()), f"Missing test results. Got: {sorted(results)}"

    # Verify each mutation test reported OK
    for key in ["t1", "t2", "t3", "t4"]:
        assert results[key].endswith(":OK"), f"{key} failed: {results[key]}"

    # Verify control tests
    assert results["t5"].endswith(":OK"), f"t5 failed: {results['t5']}"
    assert results["t6"].endswith(":OK"), f"t6 failed: {results['t6']}"


def main():
    run_subprocess_tests()


if __name__ == '__main__':
    main()
