import re
import ast
from test.support.script_helper import assert_python_ok

# This test verifies the fix for a use-after-free in AST repr() error paths.
# The patch removed an erroneous Py_DECREF(value) when building the repr
# of AST objects fails (e.g., because repr(value) raises). Prior to the fix,
# calling repr() on an AST node with a value that raises during repr could
# crash due to use-after-free. We exercise scenarios that trigger a failure
# in repr(value) and ensure that:
# - The process does not crash (subprocess isolation).
# - If ValueError is raised, its message is reasonable when the digit-limit
#   protection is present.


def test_ast_repr_large_constant_no_crash_and_message():
    code = """if 1:
    import ast, re

    # Construct a very large integer via hex literal. Its decimal repr() may
    # hit the int-to-str digit limit and raise ValueError.
    source = "0x0" + "e" * 10_000

    # Case 1: repr() of a standalone Constant node with huge value
    node = ast.Constant(value=eval(source))
    try:
        repr(node)
    except ValueError as e:
        msg = str(e)
        # When the digit-limit protection is enabled, the message should match:
        if "Exceeds the limit" in msg:
            assert re.search(r"Exceeds the limit \\([0-9]+ digits\\)", msg), \
                f"Unexpected ValueError message: {msg}"

    # Case 2: repr() of a parsed Module containing the huge constant
    code_snip = "x = " + source
    mod = ast.parse(code_snip, mode='exec')
    try:
        repr(mod)
    except ValueError as e:
        msg = str(e)
        if "Exceeds the limit" in msg:
            assert re.search(r"Exceeds the limit \\([0-9]+ digits\\)", msg), \
                f"Unexpected ValueError message (module repr): {msg}"

    print("OK")
"""

    rc, out, err = assert_python_ok('-c', code)
    assert rc == 0, f"Expected return code 0, got: {rc}"
    assert b"OK" in out, f"Expected 'OK' in stdout, got: {out!r}"
    assert not err, f"Expected no stderr, got: {err!r}"


if __name__ == '__main__':
    test_ast_repr_large_constant_no_crash_and_message()
