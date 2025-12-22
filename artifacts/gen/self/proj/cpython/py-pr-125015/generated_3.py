# This test verifies the fix for a use-after-free in ast repr() when
# building the repr of nodes with values whose repr() fails.
#
# The regression was caused by an extra DECREF on the value when the
# value's repr() failed, leading to a potential use-after-free.
#
# We test three scenarios:
# 1) Very large integer constant: may raise ValueError due to digit limits, or succeed.
# 2) A custom object whose __repr__ raises a RuntimeError (only if AST has fancy repr).
# 3) A custom object whose __repr__ returns a non-string (TypeError) (only if AST has fancy repr).
#
# We detect whether a fancy AST repr is available by inspecting repr(ast.Constant(value=1)).
# If not available, we skip the exception-propagation checks but still ensure no crash.

import re
from test.support.script_helper import assert_python_ok


def run_subprocess_ast_repr_failure_tests():
    code = """if 1:
        import ast, re

        # Helper to assert exception type and message content
        def assert_raises(expected_exc, func, pattern=None):
            try:
                func()
                raise AssertionError(f"Expected {expected_exc.__name__}")
            except expected_exc as e:
                if pattern is not None:
                    if not re.search(pattern, str(e), flags=re.IGNORECASE):
                        raise AssertionError(f"Expected message to match /{pattern}/, got: {e}")

        # Detect whether AST nodes have a rich repr that includes field values
        probe = repr(ast.Constant(value=1))
        has_fancy_repr = ('Constant(' in probe) or ('value=' in probe)

        # 1) POC scenario: very large integer literal
        # Depending on Python version/settings, the ValueError may be raised
        # either while evaluating the literal or while repr() attempts to
        # render the large integer. Accept both behaviors; main goal: no crash.
        source = "0x0" + "e" * 10_000
        try:
            s = repr(ast.Constant(value=eval(source)))
        except ValueError as e:
            # The error message varies by version; match broadly for the digit limit wording
            poc_pattern = r"exceeds? the limit|limit \\([0-9]+ digits\\)"
            if not re.search(poc_pattern, str(e), flags=re.IGNORECASE):
                raise AssertionError(f"Expected message to mention digit limit, got: {e}")
        else:
            # If it succeeds, ensure it returned a string repr
            if not isinstance(s, str):
                raise AssertionError(f"Expected repr to return str, got: {type(s)}")
        print("POC_OK")

        # 2) Custom object whose __repr__ raises RuntimeError
        class Boom:
            def __repr__(self):
                raise RuntimeError("boom")

        def boom_call():
            return repr(ast.Constant(value=Boom()))

        if has_fancy_repr:
            assert_raises(RuntimeError, boom_call, pattern=r"boom")
        else:
            # Without fancy repr, repr() won't call value.__repr__, just ensure no crash
            s = boom_call()
            if not isinstance(s, str):
                raise AssertionError(f"Expected repr to return str, got: {type(s)}")
        print("BOOM_OK")

        # 3) Custom object whose __repr__ returns a non-string -> TypeError
        class BadRepr:
            def __repr__(self):
                return 123  # invalid: __repr__ must return str

        def badrepr_call():
            return repr(ast.Constant(value=BadRepr()))

        if has_fancy_repr:
            assert_raises(TypeError, badrepr_call, pattern=r"__repr__.*non-string|must be str|returned non-string")
        else:
            # Without fancy repr, repr() won't call value.__repr__, just ensure no crash
            s = badrepr_call()
            if not isinstance(s, str):
                raise AssertionError(f"Expected repr to return str, got: {type(s)}")
        print("BADREP_OK")

        # 4) Sanity: normal small constant should work
        s = repr(ast.Constant(value=42))
        if not isinstance(s, str):
            raise AssertionError(f"Expected repr to return str, got: {type(s)}")
        print("SANITY_OK")
        """

    rc, out, err = assert_python_ok('-c', code)

    # Basic subprocess checks
    assert rc == 0, f"Expected return code 0, got: {rc}"
    assert not err, f"Expected no stderr, got: {err}"

    # Verify that each sub-test reported success
    for token in (b'POC_OK', b'BOOM_OK', b'BADREP_OK', b'SANITY_OK'):
        assert token in out, f"Missing {token!r} in stdout. Got: {out!r}"


if __name__ == '__main__':
    run_subprocess_ast_repr_failure_tests()
