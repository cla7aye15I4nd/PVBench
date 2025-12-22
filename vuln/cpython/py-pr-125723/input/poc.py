import sys
def g():
    a = 1
    yield locals(), sys._getframe().f_locals
ns = {}
for i in range(10):
    exec("snapshot, live_locals = next(g())", locals=ns)
    print(ns)