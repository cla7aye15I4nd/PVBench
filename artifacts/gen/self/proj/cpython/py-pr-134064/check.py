import sys

try:
    sys.remote_exec(0, None)
    assert False, "Expected TypeError"
except TypeError:
    pass

try:
    sys.remote_exec(0, 123)
    assert False, "Expected TypeError"
except TypeError:
    pass
