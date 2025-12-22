from test.support.script_helper import assert_python_ok

# This test verifies the fix for a crash when calling next() on an exhausted
# template string iterator. The underlying bug (in templateobject.c) occurred
# when the iterator was exhausted and then next() was called again: the C code
# would unconditionally access the item returned by PyIter_Next without
# checking for NULL, leading to a crash. The patch adds a NULL check and returns
# NULL to correctly raise StopIteration.
#
# We run the checks in a subprocess using assert_python_ok to ensure isolation
# from potential crashes. If the running interpreter does not support template
# strings (t"..."), we skip the behavioral assertions and exit successfully.


def run_subprocess_tests():
    code = """if 1:
        import sys

        # Helper that builds template iterators without embedding t-strings
        # directly in source (so this file can be parsed by older interpreters).
        def make_iter(template_expr: str):
            # template_expr is a Python expression string like 't"{1}"'
            return eval(f"iter({template_expr})")

        # Skip gracefully if template strings are not supported by this interpreter
        try:
            eval('t""')
        except SyntaxError:
            print('ok')
            sys.exit(0)

        from string.templatelib import Interpolation

        # Test 1: Repro from PoC: iter(t"{1}")
        # Expect: first item is an Interpolation; second next raises StopIteration;
        # a third next (after exhaustion) should also raise StopIteration (no crash).
        it = make_iter('t"{1}"')
        first = next(it)
        assert isinstance(first, Interpolation), f"Expected Interpolation, got {type(first)}"

        try:
            next(it)
            assert False, "Expected StopIteration on second next(t'{1}')"
        except StopIteration:
            pass

        try:
            next(it)
            assert False, "Expected StopIteration on third next(t'{1}') (should not crash)"
        except StopIteration:
            pass

        # Test 2: Template with no interpolations: iter(t"abc")
        # Expect: yields the full string 'abc', then StopIteration on further nexts;
        # repeated nexts after exhaustion should continue to raise StopIteration.
        it2 = make_iter('t"abc"')
        got = next(it2)
        assert isinstance(got, str) and got == "abc", f"Expected 'abc' string, got {got!r}"

        try:
            next(it2)
            assert False, "Expected StopIteration after exhausting t'abc'"
        except StopIteration:
            pass

        try:
            next(it2)
            assert False, "Expected StopIteration after exhaustion (t'abc')"
        except StopIteration:
            pass

        # Test 3: Interpolation with trailing string: iter(t"{1}X")
        # Drain the iterator and validate items, then verify repeated nexts
        # after exhaustion still raise StopIteration.
        it3 = make_iter('t"{1}X"')
        items = []
        try:
            while True:
                items.append(next(it3))
        except StopIteration:
            pass

        assert len(items) == 2, f"Expected 2 items, got {len(items)}: {items!r}"
        assert isinstance(items[0], Interpolation), f"First item should be Interpolation, got {type(items[0])}"
        assert items[1] == "X", f"Second item should be 'X', got {items[1]!r}"

        for i in range(2):
            try:
                next(it3)
                assert False, f"Expected StopIteration after exhaustion on iteration {i}"
            except StopIteration:
                pass

        print('ok')
    """

    rc, out, err = assert_python_ok('-c', code)
    assert rc == 0, f"Expected return code 0, got: {rc} with stderr: {err!r}"
    assert b'ok' in out, f"Expected 'ok' in stdout, got: {out!r}"
    assert not err, f"Expected no stderr, got: {err!r}"


if __name__ == '__main__':
    run_subprocess_tests()
