# This test verifies the fix for gh-108727: defining tp_dealloc for CounterOptimizer_Type
# in Python/optimizer.c. Previously, deallocating the object returned by
# _testinternalcapi.get_counter_optimizer() could segfault. The fix sets
# tp_dealloc to PyObject_Del. We validate that creating and deallocating these
# objects in several scenarios does not crash, and that the type disallows
# user instantiation (Py_TPFLAGS_DISALLOW_INSTANTIATION).

from test.support.script_helper import assert_python_ok


def run_subprocess_test():
    # Use a subprocess to catch potential crashes/segfaults reliably.
    code = """if 1:
        import sys, gc
        try:
            import _testinternalcapi
        except Exception as e:
            # If the module itself is unavailable, skip gracefully.
            print('SKIP: no _testinternalcapi', flush=True)
        else:
            if not hasattr(_testinternalcapi, 'get_counter_optimizer'):
                print('SKIP: no get_counter_optimizer', flush=True)
            else:
                # 1) Create and let the object drop out of scope.
                def make_and_drop():
                    obj = _testinternalcapi.get_counter_optimizer()
                    assert obj is not None, 'get_counter_optimizer returned None'
                    # Return the type for instantiation test later
                    return type(obj)
                typ = make_and_drop()
                print('ok1', flush=True)

                # 2) Create many objects and delete them, then force GC.
                objs = [_testinternalcapi.get_counter_optimizer() for _ in range(500)]
                assert len(objs) == 500, f'Expected 500 objects, got {len(objs)}'
                del objs
                gc.collect()
                print('ok2', flush=True)

                # 3) Deallocation during exception unwinding.
                try:
                    o = _testinternalcapi.get_counter_optimizer()
                    assert o is not None
                    raise RuntimeError('trigger cleanup')
                except RuntimeError:
                    pass
                print('ok3', flush=True)

                # 4) Ensure the type disallows user instantiation (Py_TPFLAGS_DISALLOW_INSTANTIATION).
                try:
                    typ()
                    assert False, 'Expected TypeError when instantiating CounterOptimizer'
                except TypeError:
                    pass
                print('ok4', flush=True)
    """

    rc, out, err = assert_python_ok('-c', code)
    # Basic process health checks
    assert rc == 0, f"Expected return code 0, got: {rc}"
    assert not err, f"Expected no stderr, got: {err}"

    # If feature is present, all markers must appear; otherwise we allow SKIP.
    if b'SKIP' not in out:
        for marker in (b'ok1', b'ok2', b'ok3', b'ok4'):
            assert marker in out, f"Missing {marker!r} in stdout. Got: {out!r}"


def main():
    run_subprocess_test()


if __name__ == '__main__':
    main()
