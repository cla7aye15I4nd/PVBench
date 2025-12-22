import sys
from test.support.script_helper import assert_python_ok


# This test suite verifies the fix for a crash when accessing gi_frame.f_locals
# after the generator has been closed or collected, as per the patch:
#   "Fix crash with gi_frame.f_locals when generator frames outlive their generator".
#
# The tests exercise several scenarios:
# - Accessing f_locals while the generator is alive (should contain local vars)
# - Accessing f_locals after generator.close() (must not crash)
# - Accessing f_locals after the generator is garbage-collected (must not crash)
# - Repeated access via exec using both locals() snapshot and f_locals mapping
#
# Subprocess isolation is used for cases that historically crashed.


def test_frame_outlives_generator_variants_alive_locals_visible():
    """
    When a frame object is obtained from a generator that is still alive and
    suspended, its f_locals mapping should contain the local variable 'a'.

    We test 3 ways to obtain a frame tied to a generator:
      1) yielding sys._getframe() from inside the generator
      2) reading gen.gi_frame after advancing to the first yield
      3) storing sys._getframe() into an external object's attribute
    """
    code = """if 1:
        import sys

        def g1():
            a = 42
            yield sys._getframe()

        def g2():
            a = 42
            yield

        def g3(o):
            a = 42
            o.frm = sys._getframe()
            yield

        class Holder:
            frm = None

        def get_frame(i):
            if i == 1:
                return next(g1())
            if i == 2:
                gen = g2()
                next(gen)
                return gen.gi_frame
            if i == 3:
                h = Holder()
                next(g3(h))
                return h.frm

        for i in (1, 2, 3):
            f = get_frame(i)
            loc = f.f_locals
            # Do not assert exact type; it can be a proxy/mapping
            assert 'a' in loc, f"Missing 'a' in f_locals for variant {i}: {loc!r}"
            assert loc['a'] == 42, f"Expected a==42 for variant {i}, got: {loc.get('a')}"
        print('OK1')
    """
    rc, out, err = assert_python_ok('-c', code)
    assert rc == 0, f"Expected return code 0, got: {rc}"
    assert b'OK1' in out, f"Expected 'OK1' in stdout, got: {out!r}"
    assert not err, f"Expected no stderr, got: {err!r}"


def test_gi_frame_f_locals_safe_after_close_and_gc():
    """
    Accessing gi_frame.f_locals after generator.close() and after the generator
    is garbage collected must be safe (no crash). Contents after close/GC are
    implementation-defined, so we only perform harmless operations.
    """
    code = """if 1:
        import sys, gc, weakref

        def g():
            a = 123
            yield

        gen = g()
        next(gen)
        frame = gen.gi_frame
        assert frame is not None, 'Expected non-None frame'

        # While generator is alive, 'a' should be visible
        alive_locals = frame.f_locals
        assert 'a' in alive_locals and alive_locals['a'] == 123, f"Unexpected locals while alive: {alive_locals!r}"

        # Close: previously accessing f_locals here could crash
        gen.close()
        loc_after_close = frame.f_locals
        # Exercise the mapping without assuming contents
        _ = len(loc_after_close)
        _ = repr(loc_after_close)
        _ = list(loc_after_close.keys())

        # Ensure generator object is collected
        wr = weakref.ref(gen)
        del gen
        gc.collect()
        assert wr() is None, 'Generator should be collected after del + gc'

        # Still safe to access f_locals of the outliving frame
        loc_after_gc = frame.f_locals
        _ = len(loc_after_gc)
        _ = repr(loc_after_gc)
        _ = list(loc_after_gc.items())

        print('OK2')
    """
    rc, out, err = assert_python_ok('-c', code)
    assert rc == 0, f"Expected return code 0, got: {rc}"
    assert b'OK2' in out, f"Expected 'OK2' in stdout, got: {out!r}"
    assert not err, f"Expected no stderr, got: {err!r}"


def test_gi_frame_f_locals_safe_after_gc_without_explicit_close():
    """
    If the generator is dropped without close(), gen_dealloc clears the frame.
    Accessing the outliving frame.f_locals must still be safe (no crash).
    """
    code = """if 1:
        import gc, weakref

        def g():
            a = 7
            yield

        gen = g()
        next(gen)
        frame = gen.gi_frame

        wr = weakref.ref(gen)
        del gen
        gc.collect()
        assert wr() is None, 'Generator should be collected'

        loc = frame.f_locals
        _ = len(loc)
        _ = repr(loc)
        _ = list(loc.values())
        print('OK3')
    """
    rc, out, err = assert_python_ok('-c', code)
    assert rc == 0, f"Expected return code 0, got: {rc}"
    assert b'OK3' in out, f"Expected 'OK3' in stdout, got: {out!r}"
    assert not err, f"Expected no stderr, got: {err!r}"


def test_frame_locals_outlive_generator_with_exec_repeat():
    """
    Enrich the provided PoC: fetch both locals() snapshot and f_locals from
    inside the generator using exec repeatedly, and ensure 'a' is present.
    """
    code = """if 1:
        import sys

        def g():
            a = 42
            yield locals(), sys._getframe().f_locals

        ns = {'g': g}
        for i in range(10):
            exec('snapshot, live_locals = next(g())', ns)
            snap = ns['snapshot']
            live = ns['live_locals']
            for d in (snap, live):
                assert 'a' in d, f"Missing 'a' in locals at iter {i}: {d!r}"
                assert d['a'] == 42, f"Expected a==42 at iter {i}, got: {d.get('a')}"
        print('OK4')
    """
    rc, out, err = assert_python_ok('-c', code)
    assert rc == 0, f"Expected return code 0, got: {rc}"
    assert b'OK4' in out, f"Expected 'OK4' in stdout, got: {out!r}"
    assert not err, f"Expected no stderr, got: {err!r}"


if __name__ == '__main__':
    test_frame_outlives_generator_variants_alive_locals_visible()
    test_gi_frame_f_locals_safe_after_close_and_gc()
    test_gi_frame_f_locals_safe_after_gc_without_explicit_close()
    test_frame_locals_outlive_generator_with_exec_repeat()
