import sys


def test_frame_outlives_generator():
    def g1():
        a = 42
        yield sys._getframe()

    def g2():
        a = 42
        yield

    def g3(obj):
        a = 42
        obj.frame = sys._getframe()
        yield

    class ObjectWithFrame():
        def __init__(self):
            self.frame = None

    def get_frame(index):
        if index == 1:
            return next(g1())
        elif index == 2:
            gen = g2()
            next(gen)
            return gen.gi_frame
        elif index == 3:
            obj = ObjectWithFrame()
            next(g3(obj))
            return obj.frame
        else:
            return None

    for index in (1, 2, 3):
        frame = get_frame(index)
        frame_locals = frame.f_locals
        assert 'a' in frame_locals
        assert frame_locals['a'] == 42


def test_frame_locals_outlive_generator():
    frame_locals1 = None

    def g1():
        nonlocal frame_locals1
        frame_locals1 = sys._getframe().f_locals
        a = 42
        yield

    def g2():
        a = 42
        yield sys._getframe().f_locals

    def get_frame_locals(index):
        if index == 1:
            nonlocal frame_locals1
            next(g1())
            return frame_locals1
        if index == 2:
            return next(g2())
        else:
            return None

    for index in (1, 2):
        frame_locals = get_frame_locals(index)
        assert 'a' in frame_locals
        assert frame_locals['a'] == 42


def test_frame_locals_outlive_generator_with_exec():
    def g():
        a = 42
        yield locals(), sys._getframe().f_locals

    locals_ = {'g': g}
    for i in range(10):
        exec("snapshot, live_locals = next(g())", locals_)
        for l in (locals_['snapshot'], locals_['live_locals']):
            assert 'a' in l
            assert l['a'] == 42


if __name__ == '__main__':
    test_frame_outlives_generator()
    test_frame_locals_outlive_generator()
    test_frame_locals_outlive_generator_with_exec()
