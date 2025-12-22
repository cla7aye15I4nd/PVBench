from string.templatelib import Interpolation

template_iter = iter(t"{1}")
first = next(template_iter)
assert isinstance(first, Interpolation), f"Expected Interpolation, got {type(first)}"

try:
    next(template_iter)
    assert False, "Expected StopIteration"
except StopIteration:
    pass

try:
    next(template_iter)
    assert False, "Expected StopIteration"
except StopIteration:
    pass
