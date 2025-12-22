class evil:
    def __init__(self, lst):
        self.lst = lst
    def __iter__(self):
        yield from self.lst
        self.lst.clear()


lst = list(range(10))
lst[::-1] = evil(lst)