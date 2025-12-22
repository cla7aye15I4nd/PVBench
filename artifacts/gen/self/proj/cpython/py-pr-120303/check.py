class evil:
    def __lt__(self, other):
        other.clear()
        return NotImplemented

a = [[evil()]]
try:
    a[0] < a
    assert False, "Expected TypeError"
except TypeError:
    pass
