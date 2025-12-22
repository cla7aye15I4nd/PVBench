try:
    int("10", 2, 1)
    assert False, "Expected TypeError"
except TypeError:
    pass
