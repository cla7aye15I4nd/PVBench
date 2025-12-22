# Generated test for CPython fix: define tp_dealloc for CounterOptimizer_Type
# The bug: CounterOptimizer objects (created via _testinternalcapi.get_counter_optimizer)
# could segfault on deallocation because the type lacked a tp_dealloc. The fix assigns
# tp_dealloc = PyObject_Del. This test exercises various deallocation paths to ensure
# no crash occurs.

from test.support.script_helper import assert_python_ok


def run_subprocess(code: str, label: str):
    rc, out, err = assert_python_ok('-c', code)
    assert rc == 0, f"{label}: Expected return code 0, got: {rc}"
    assert err == b'', f"{label}: Expected no stderr, got: {err!r}"
    assert out == b'', f"{label}: Expected empty stdout, got: {out!r}"


def main():
    # Check feature availability in this interpreter before spawning subprocesses
    try:
        import _testinternalcapi as _t
        has_feature = hasattr(_t, 'get_counter_optimizer')
    except Exception:
        has_feature = False

    if not has_feature:
        # Feature not available; nothing to test.
        return

    # 1) Minimal PoC scenario: create the object and let it be deallocated at function end
    code1 = """if 1:
        import _testinternalcapi, gc
        def f():
            obj = _testinternalcapi.get_counter_optimizer()
            assert obj is not None, "get_counter_optimizer() returned None"
            # Drop the reference to trigger deallocation promptly
            del obj
            # Run several GC cycles to ensure timely finalization in debug builds
            for _ in range(3):
                gc.collect()
        f()
    """
    run_subprocess(code1, label="simple_dealloc")

    # 2) Stress scenario: allocate many objects, place them in a cycle-containing container,
    #    then drop all references and force collection. Previously, any deallocation could
    #    segfault; this stresses numerous deallocations and interaction with cyclic GC.
    code2 = """if 1:
        import _testinternalcapi, gc
        objs = [_testinternalcapi.get_counter_optimizer() for _ in range(1000)]
        assert len(objs) == 1000, f"Expected 1000 objects, got {len(objs)}"
        # Create a simple reference cycle involving a list that holds the objects
        holder = [objs]
        holder.append(holder)
        # Drop references and collect
        del objs
        del holder
        for _ in range(5):
            gc.collect()
    """
    run_subprocess(code2, label="stress_many_deallocs_with_cycle")

    # 3) Interpreter shutdown scenario: create an object and rely on interpreter shutdown
    #    to deallocate it. Previously this path could also hit the segfault.
    code3 = """if 1:
        import _testinternalcapi
        # Create and allow interpreter shutdown to handle deallocation
        _testinternalcapi.get_counter_optimizer()
    """
    run_subprocess(code3, label="shutdown_dealloc")


if __name__ == '__main__':
    main()
