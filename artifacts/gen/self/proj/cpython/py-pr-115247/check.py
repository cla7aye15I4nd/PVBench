from collections import deque

class A:
    def __eq__(self, other):
        d.clear()
        return NotImplemented

d = deque([A()])
try:
    d.index(0)
    assert False, "Expected RuntimeError"
except RuntimeError:
    pass
