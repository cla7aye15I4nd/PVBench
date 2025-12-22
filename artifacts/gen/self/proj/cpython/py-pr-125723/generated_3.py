# Self-contained generated test verifying fix for generator frame f_locals crash
# The fix (gh-125723) ensures that accessing frame.f_locals or locals() snapshots
# that outlive the generator does not crash the interpreter. It also handles
# generator close/dealloc paths safely by clearing frames correctly.

from test.support.script_helper import assert_python_ok


def test_generator_frames_and_locals_outlive_generator_no_crash():
    """
    Run a suite of scenarios in a subprocess to ensure process isolation,
    as previous behavior could crash the interpreter.
    The subprocess code:
      - obtains frames from inside generators in several ways and validates f_locals
      - obtains f_locals objects that outlive the generator and validates them
      - repeatedly uses exec to call a generator that returns locals() and f_locals
        and then validates those objects after the generator is destroyed
    If any scenario fails or crashes, the subprocess will non-zero exit.
    """
    code = """if 1:
        import sys

        # 1) Frames retrieved from generators, frame outlives generator
        def g1():
            a = 42
            # Return the current frame object itself
            yield sys._getframe()

        def g2():
            a = 42
            # Yield control; caller will read gen.gi_frame
            yield

        def g3(obj):
            a = 42
            # Stash frame into an external object
            obj.frame = sys._getframe()
            yield

        class Holder:
            def __init__(self):
                self.frame = None

        def get_frame(index):
            if index == 1:
                return next(g1())
            elif index == 2:
                gen = g2()
                next(gen)
                # Access the generator's frame while it's suspended
                return gen.gi_frame
            elif index == 3:
                h = Holder()
                next(g3(h))
                return h.frame
            else:
                return None

        for index in (1, 2, 3):
            frame = get_frame(index)
            # Access f_locals of the frame and validate content
            frame_locals = frame.f_locals
            assert 'a' in frame_locals, f"Missing 'a' in frame.f_locals for case {index}: {frame_locals}"
            assert frame_locals['a'] == 42, f"Unexpected value for 'a' in case {index}: {frame_locals}"

        # 2) f_locals objects outlive the generator object
        frame_locals_cell = [None]

        def g4():
            # Assign first to ensure the mapping reflects the variable
            a = 42
            # Capture a live f_locals mapping from the running frame
            frame_locals_cell[0] = sys._getframe().f_locals
            yield

        def g5():
            a = 42
            # Return the f_locals mapping directly
            yield sys._getframe().f_locals

        def get_frame_locals(index):
            if index == 1:
                next(g4())
                return frame_locals_cell[0]
            elif index == 2:
                return next(g5())
            else:
                return None

        for index in (1, 2):
            fl = get_frame_locals(index)
            assert 'a' in fl, f"Missing 'a' in f_locals for case {index}: {fl}"
            assert fl['a'] == 42, f"Unexpected value for 'a' in f_locals for case {index}: {fl}"

        # 3) Repeated exec pattern (similar to poc) where the generator is not retained
        # and thus gets destroyed while the returned locals live on.
        def g():
            a = 42
            yield locals(), sys._getframe().f_locals

        env = {'g': g}
        for i in range(10):
            # Each call creates a fresh generator that is not retained after next(),
            # so its frame/generator is cleaned up while locals() and f_locals survive.
            exec("snapshot, live_locals = next(g())", env)
            for name in ('snapshot', 'live_locals'):
                l = env[name]
                assert 'a' in l, f"Missing 'a' in {name} on iteration {i}: {l}"
                assert l['a'] == 42, f"Unexpected value for 'a' in {name} on iteration {i}: {l}"

        print('OK')
    """

    rc, out, err = assert_python_ok('-c', code)
    assert rc == 0, f"Expected return code 0, got: {rc}"
    assert b'OK' in out, f"Expected 'OK' in stdout, got: {out!r}"
    assert not err, f"Expected no stderr, got: {err!r}"


if __name__ == '__main__':
    test_generator_frames_and_locals_outlive_generator_no_crash()
    print('All tests passed.')
