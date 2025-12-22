# This test verifies the fix for a crash when calling next() on an exhausted
# template string iterator (see patch in templateobject.c).
#
# Strategy:
# - Run the core checks in a subprocess using assert_python_ok to isolate any
#   potential crashes (as per the CHECK APIs instructions).
# - The subprocess compiles a source snippet containing template literals to
#   detect feature availability. If unavailable, it prints "SKIP" and exits
#   successfully so the test suite can skip gracefully on older interpreters.
# - When available, we verify:
#   * Iteration over t"{1}" yields an Interpolation first, then StopIteration
#     on subsequent next() calls, and crucially, repeated next() calls after
#     exhaustion continue to raise StopIteration (no crash).
#   * Additional edge cases around leading/trailing interpolations and mixtures
#     with literal strings.

from test.support.script_helper import assert_python_ok


def run_subprocess_template_iter_checks():
    code = r"""if 1:
        import sys

        # Entire test body as a string so we can compile and gracefully skip
        # if the interpreter doesn't support template strings.
        inner = r'''from string.templatelib import Interpolation

# Minimal regression from poc: t"{1}" should yield Interpolation first
# and then be exhausted. Repeated next() must not crash.
template_iter = iter(t"{1}")
first = next(template_iter)
assert isinstance(first, Interpolation), f"Expected Interpolation, got {type(first)}"

try:
    next(template_iter)
    raise AssertionError("Expected StopIteration on second next for t\"{1}\"")
except StopIteration:
    pass

# Previously this could crash; ensure it consistently raises StopIteration.
for i in range(10):
    try:
        next(template_iter)
        raise AssertionError(f"Expected StopIteration after exhaustion at repeat {i}")
    except StopIteration:
        pass

# Edge case: trailing interpolation only -> after yielding the final
# Interpolation, iterator is exhausted.
it2 = iter(t"abc{1}")
s = next(it2)
assert s == "abc", f"Expected 'abc', got {s!r}"
tok = next(it2)
assert isinstance(tok, Interpolation), f"Expected Interpolation, got {type(tok)}"
for i in range(3):
    try:
        next(it2)
        raise AssertionError("Expected StopIteration after trailing interpolation in 'abc{1}'")
    except StopIteration:
        pass

# Edge case: leading interpolation with trailing string
it3 = iter(t"{1}xyz")
tok = next(it3)
assert isinstance(tok, Interpolation), f"Expected Interpolation, got {type(tok)}"
tail = next(it3)
assert tail == "xyz", f"Expected 'xyz', got {tail!r}"
for i in range(2):
    try:
        next(it3)
        raise AssertionError("Expected StopIteration at end of '{1}xyz'")
    except StopIteration:
        pass

# Mixed: string, interpolation, string
it4 = iter(t"foo{1}bar")
s1 = next(it4)
assert s1 == "foo", f"Expected 'foo', got {s1!r}"
tok = next(it4)
assert isinstance(tok, Interpolation), f"Expected Interpolation, got {type(tok)}"
s2 = next(it4)
assert s2 == "bar", f"Expected 'bar', got {s2!r}"
for i in range(2):
    try:
        next(it4)
        raise AssertionError("Expected StopIteration at end of 'foo{1}bar'")
    except StopIteration:
        pass
'''

        try:
            co = compile(inner, '<template-tests>', 'exec')
        except SyntaxError:
            print('SKIP: template strings not available')
            raise SystemExit(0)

        ns = {}
        exec(co, ns, ns)
        print('OK')
    """

    rc, out, err = assert_python_ok('-c', code)
    # The subprocess should always exit cleanly (even when skipping)
    assert rc == 0, f"Expected return code 0, got: {rc} with stderr: {err!r}"
    # Ensure no unexpected stderr output
    assert not err, f"Expected no stderr, got: {err!r}"
    # Accept success or skip message depending on interpreter support
    assert (b'OK' in out) or (b'SKIP' in out), f"Expected 'OK' or 'SKIP' in stdout, got: {out!r}"


if __name__ == '__main__':
    run_subprocess_template_iter_checks()
