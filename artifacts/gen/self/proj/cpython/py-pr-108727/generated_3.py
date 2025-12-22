# Comprehensive test for CounterOptimizer_Type deallocation fix
# The patch adds tp_dealloc=(destructor)PyObject_Del to CounterOptimizer_Type
# to avoid a segfault on deallocation. This test ensures that creating and
# deleting the optimizer object does not crash, both in normal operation and
# under stress, and also verifies that the type cannot be directly instantiated.

from test.support.script_helper import assert_python_ok


def _run(code):
    rc, out, err = assert_python_ok('-c', code)
    # If the feature is not available, we expect the child to print 'SKIP'.
    if b'SKIP' in out:
        # Skip this subtest: environment/feature not available in this build.
        return rc, out, err, True
    # Otherwise, the test must complete cleanly without stderr.
    assert rc == 0, f"Expected return code 0, got: {rc} (stderr: {err!r})"
    assert not err, f"Expected no stderr, got: {err}"
    return rc, out, err, False


def test_single_create_and_delete():
    # Create and delete a single optimizer instance. If the bug is present,
    # this can segfault on deallocation. Also verify that the type disallows
    # direct instantiation (Py_TPFLAGS_DISALLOW_INSTANTIATION).
    code = """if 1:
        __lltrace__ = True
        import sys, gc
        try:
            import _testinternalcapi as m
        except Exception:
            print('SKIP')
        else:
            if not hasattr(m, 'get_counter_optimizer'):
                print('SKIP')
            else:
                obj = m.get_counter_optimizer()
                tp = type(obj)
                # Verify that direct instantiation is disallowed
                try:
                    tp()
                    print('INSTANTIATION_ALLOWED')  # Should not happen
                except TypeError:
                    print('INST_TYPEERROR')
                # Drop the only reference and force collection
                del obj
                gc.collect()
                # If we reach here, no crash occurred
                print('DONE')
    """
    rc, out, err, skipped = _run(code)
    if skipped:
        return
    assert b'INST_TYPEERROR' in out, f"Expected 'INST_TYPEERROR' in stdout, got: {out!r}"
    assert b'DONE' in out, f"Expected 'DONE' in stdout, got: {out!r}"


def test_stress_many_creations():
    # Stress test: create and delete many optimizer instances to exercise
    # repeated allocations and deallocations. Previously, a missing tp_dealloc
    # could cause a segfault on deallocation.
    code = """if 1:
        __lltrace__ = True
        import sys, gc
        try:
            import _testinternalcapi as m
        except Exception:
            print('SKIP')
        else:
            if not hasattr(m, 'get_counter_optimizer'):
                print('SKIP')
            else:
                for i in range(10000):
                    o = m.get_counter_optimizer()
                    # Immediately drop reference
                    if (i % 1000) == 0:
                        gc.collect()
                gc.collect()
                print('STRESS_OK')
    """
    rc, out, err, skipped = _run(code)
    if skipped:
        return
    assert b'STRESS_OK' in out, f"Expected 'STRESS_OK' in stdout, got: {out!r}"


def test_dealloc_at_shutdown():
    # Create an optimizer instance and keep it alive until interpreter shutdown.
    # If deallocation at shutdown crashed previously, the process would exit
    # abnormally. We assert clean exit and presence of markers in stdout.
    code = """if 1:
        __lltrace__ = True
        import sys
        try:
            import _testinternalcapi as m
        except Exception:
            print('SKIP')
        else:
            if not hasattr(m, 'get_counter_optimizer'):
                print('SKIP')
            else:
                g = m.get_counter_optimizer()  # Keep alive until shutdown
                print('CREATED')
                # Program ends here; g will be deallocated at shutdown.
    """
    rc, out, err, skipped = _run(code)
    if skipped:
        return
    # If we got here, the interpreter exited cleanly and printed our marker.
    assert b'CREATED' in out, f"Expected 'CREATED' in stdout, got: {out!r}"


if __name__ == '__main__':
    test_single_create_and_delete()
    test_stress_many_creations()
    test_dealloc_at_shutdown()
    print('All tests passed.')
