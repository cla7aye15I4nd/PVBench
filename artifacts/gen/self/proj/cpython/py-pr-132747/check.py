import types
import _io
import io
import _queue

to_check = [
    (_io._TextIOBase.read, io.StringIO()),
    (_queue.SimpleQueue.put, _queue.SimpleQueue()),
    (str.capitalize, "nobody expects the spanish inquisition")
]

for method, instance in to_check:
    bound = method.__get__(instance)
    assert isinstance(bound, types.BuiltinMethodType), f"Expected BuiltinMethodType, got {type(bound)}"
