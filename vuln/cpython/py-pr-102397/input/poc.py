import gc
import _thread

gc.set_threshold(1, 0, 0)

def cb(*args):
    _thread.interrupt_main()


gc.callbacks.append(cb)

def gen():
    yield 1

g = gen()
g.__next__()