template_iter = iter(t"{1}")
next(template_iter)
try:
    next(template_iter)
except StopIteration:
    pass
next(template_iter)