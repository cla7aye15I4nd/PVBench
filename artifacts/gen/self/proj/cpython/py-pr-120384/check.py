class evil:
    def __init__(self, lst):
        self.lst = lst
    def __iter__(self):
        yield from self.lst
        self.lst.clear()

lst = list(range(5))
operand = evil(lst)
try:
    lst[::-1] = operand
    assert False, "Expected ValueError"
except ValueError:
    pass
