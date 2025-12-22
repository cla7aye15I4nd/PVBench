import sys

FrameLocalsProxy = type([sys._getframe().f_locals for x in range(1)][0])
assert FrameLocalsProxy.__name__ == 'FrameLocalsProxy'

def make_frame():
    x = 1
    y = 2
    return sys._getframe()

proxy = FrameLocalsProxy(make_frame())
assert proxy == {'x': 1, 'y': 2}, f"Expected {{'x': 1, 'y': 2}}, got {proxy}"

# constructor expects 1 frame argument
try:
    FrameLocalsProxy()  # no arguments
    assert False, "Expected TypeError"
except TypeError:
    pass

try:
    FrameLocalsProxy(sys._getframe(), 1)  # too many arguments
    assert False, "Expected TypeError"
except TypeError:
    pass

try:
    FrameLocalsProxy(sys._getframe(), frame=sys._getframe())  # no keyword arguments
    assert False, "Expected TypeError"
except TypeError:
    pass

try:
    FrameLocalsProxy(123)  # wrong type
    assert False, "Expected TypeError"
except TypeError:
    pass

try:
    FrameLocalsProxy(frame=sys._getframe())  # no keyword arguments
    assert False, "Expected TypeError"
except TypeError:
    pass
