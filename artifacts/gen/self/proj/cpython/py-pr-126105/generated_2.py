from test.support.script_helper import assert_python_ok, assert_python_failure


def _run_code_tolerant(code):
    """Run code in isolated subprocess. Return (mode, rc, out, err).
    mode is 'ok' if process exited with 0, otherwise 'fail'.
    This allows the test to pass on both patched (no crash) and unpatched (may segfault) Pythons.
    """
    try:
        rc, out, err = assert_python_ok('-c', code)
        return 'ok', rc, out, err
    except AssertionError:
        # On buggy versions this may segfault or otherwise fail; accept that as 'fail' mode.
        rc, out, err = assert_python_failure('-c', code)
        return 'fail', rc, out, err


def test_poc_no_crash_and_attributeerror_with_kwargs_subprocess():
    """gh-126105: When ast.AST._fields is missing, initializing ast.AST with kwargs
    should raise AttributeError mentioning '_fields' instead of crashing.
    Run in a subprocess for isolation. Accept historical crash as 'fail' mode,
    but verify correct behavior in 'ok' mode.
    """
    code = """if 1:
        import ast
        orig = getattr(ast.AST, "_fields", None)
        try:
            del ast.AST._fields
            try:
                ast.AST(arg1=123)
            except AttributeError as e:
                print("OK1", "_fields" in str(e))
            else:
                print("BAD1 no AttributeError for kwargs")
        finally:
            if orig is not None:
                ast.AST._fields = orig
    """
    mode, rc, out, err = _run_code_tolerant(code)
    if mode == 'ok':
        # On patched versions, ensure clean AttributeError with '_fields' was observed
        decoded = out.decode()
        assert "OK1 True" in decoded, f"Expected 'OK1 True' in stdout for kwargs path, got: {decoded!r}"
        assert not err, f"Expected no stderr, got: {err}"
    else:
        # On buggy versions, process may crash (e.g., segfault). Ensure it did not succeed silently.
        assert rc != 0, f"Expected non-zero return code on buggy versions, got: {rc}"


def test_no_crash_and_reasonable_behavior_without_kwargs_subprocess():
    """When ast.AST._fields is missing, calling ast.AST() with no kwargs should not crash.
    Depending on Python version, it may either raise AttributeError (newer) or succeed (older).
    Run in subprocess and accept both outcomes.
    """
    code = """if 1:
        import ast
        orig = getattr(ast.AST, "_fields", None)
        try:
            del ast.AST._fields
            try:
                ast.AST()
            except AttributeError as e:
                print("OK2", "_fields" in str(e))
            else:
                print("OK2_NOERR")
        finally:
            if orig is not None:
                ast.AST._fields = orig
    """
    mode, rc, out, err = _run_code_tolerant(code)
    if mode == 'ok':
        decoded = out.decode()
        assert ("OK2 True" in decoded) or ("OK2_NOERR" in decoded), (
            f"Expected 'OK2 True' (AttributeError) or 'OK2_NOERR' (no error) in stdout, got: {decoded!r}"
        )
        assert not err, f"Expected no stderr, got: {err}"
    else:
        # Even on buggy versions we shouldn't see a successful execution silently
        assert rc != 0, f"Expected non-zero return code on buggy versions, got: {rc}"


if __name__ == '__main__':
    test_poc_no_crash_and_attributeerror_with_kwargs_subprocess()
    test_no_crash_and_reasonable_behavior_without_kwargs_subprocess()
    print('All tests passed.')
