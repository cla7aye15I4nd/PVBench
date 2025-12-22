import sys
from test.support.script_helper import assert_python_ok

# This test suite verifies the fix for a crash involving generator frames and
# f_locals when the frame or its locals outlive the generator object.
# The patch introduced gen_clear_frame() and used it in generator deallocation
# and close() paths to ensure the frame is cleared safely without leaving
# dangling state that could crash when accessing f_locals.


def test_frame_outlives_generator():
    """
    Obtain frames from generators in three different ways and ensure that
    accessing frame.f_locals succeeds after the generator object is gone.
    """
    code = """if 1:
        import sys, gc

        def g1():
            a = 42
            yield sys._getframe()

        def g2():
            a = 42
            yield

        def g3(container):
            a = 42
            container['frame'] = sys._getframe()
            yield

        def get_frame(index):
            if index == 1:
                # Frame captured directly from inside the generator
                return next(g1())
            elif index == 2:
                # Use gi_frame after advancing the generator
                gen = g2()
                next(gen)
                return gen.gi_frame
            elif index == 3:
                # Store frame externally so it outlives the generator
                box = {}
                next(g3(box))
                return box['frame']
            else:
                return None

        for i in (1, 2, 3):
            f = get_frame(i)
            # Force GC to ensure the generator is collected
            gc.collect()
            locals_map = f.f_locals
            assert 'a' in locals_map, f"Missing 'a' in f_locals for case {i}: {locals_map}"
            assert locals_map['a'] == 42, (
                f"Unexpected value for 'a' in case {i}: {locals_map.get('a')}"
            )
        print('FRAME_OK')
    """
    rc, out, err = assert_python_ok('-c', code)
    assert rc == 0, f"Expected return code 0, got: {rc}"
    assert b'FRAME_OK' in out, f"Expected 'FRAME_OK' in stdout, got: {out}"
    assert not err, f"Expected no stderr, got: {err}"


def test_frame_locals_outlive_generator():
    """
    Capture f_locals mapping objects from generator frames and ensure they
    remain functional (and contain 'a' == 42) after the generator is gone.
    """
    code = """if 1:
        import sys, gc

        frame_locals1_box = [None]

        def g1():
            a = 42
            # Capture mapping after assigning 'a'
            frame_locals1_box[0] = sys._getframe().f_locals
            yield

        def g2():
            a = 42
            yield sys._getframe().f_locals

        def get_frame_locals(index):
            if index == 1:
                next(g1())
                # Ensure generator is collected
                gc.collect()
                return frame_locals1_box[0]
            elif index == 2:
                mapping = next(g2())
                # Drop the generator and collect
                gc.collect()
                return mapping
            else:
                return None

        for i in (1, 2):
            mapping = get_frame_locals(i)
            assert 'a' in mapping, f"Missing 'a' in f_locals mapping (case {i}): {mapping}"
            assert mapping['a'] == 42, (
                f"Unexpected 'a' value in f_locals (case {i}): {mapping.get('a')}"
            )
        print('LOCALS_OK')
    """
    rc, out, err = assert_python_ok('-c', code)
    assert rc == 0, f"Expected return code 0, got: {rc}"
    assert b'LOCALS_OK' in out, f"Expected 'LOCALS_OK' in stdout, got: {out}"
    assert not err, f"Expected no stderr, got: {err}"


def test_frame_locals_outlive_generator_with_exec():
    """
    Reproduce the PoC using exec: capture both a snapshot of locals() and the
    live f_locals mapping repeatedly, ensuring both report the expected content.
    """
    code = """if 1:
        import sys
        def g():
            a = 42
            yield locals(), sys._getframe().f_locals

        locals_ = {'g': g}
        for i in range(10):
            exec("snapshot, live_locals = next(g())", locals_)
            for l in (locals_['snapshot'], locals_['live_locals']):
                assert 'a' in l, f"Iteration {i}: missing 'a' in locals: {l}"
                assert l['a'] == 42, f"Iteration {i}: unexpected 'a' value: {l}"
        print('EXEC_OK')
    """
    rc, out, err = assert_python_ok('-c', code)
    assert rc == 0, f"Expected return code 0, got: {rc}"
    assert b'EXEC_OK' in out, f"Expected 'EXEC_OK' in stdout, got: {out}"
    assert not err, f"Expected no stderr, got: {err}"


def test_gen_close_does_not_crash_locals_mapping():
    """
    Ensure that accessing f_locals mapping after closing a generator does not
    crash. The contents after close are implementation-defined; we only assert
    operations succeed without errors.
    """
    code = """if 1:
        import sys

        def h():
            a = 123
            # Return live mapping to generator frame locals
            yield sys._getframe().f_locals

        gen = h()
        mapping = next(gen)
        # While generator is alive, mapping should reflect 'a'
        assert mapping['a'] == 123, f"Expected 123 before close, got: {mapping.get('a')}"
        # Close the generator; previously this could leave a bad state
        gen.close()

        # Perform a handful of read operations that would crash if the mapping
        # referenced cleared memory/state. We don't assert on content here.
        _ = repr(mapping)
        _ = len(mapping)
        _ = list(mapping.items())
        _ = dict(mapping)
        _ = mapping.get('a', None)

        # Also test the gi_frame path: acquire frame then close generator
        def h2():
            a = 7
            yield
        gen2 = h2()
        next(gen2)
        f = gen2.gi_frame
        gen2.close()
        # Access f_locals after close; ensure it can be materialized and read
        m = f.f_locals
        _ = repr(m)
        _ = len(m)
        _ = list(m.items())
        _ = dict(m)
        print('CLOSE_OK')
    """
    rc, out, err = assert_python_ok('-c', code)
    assert rc == 0, f"Expected return code 0, got: {rc}"
    assert b'CLOSE_OK' in out, f"Expected 'CLOSE_OK' in stdout, got: {out}"
    assert not err, f"Expected no stderr, got: {err}"


if __name__ == '__main__':
    # Run all tests
    test_frame_outlives_generator()
    test_frame_locals_outlive_generator()
    test_frame_locals_outlive_generator_with_exec()
    test_gen_close_does_not_crash_locals_mapping()
    print('All tests passed.')
