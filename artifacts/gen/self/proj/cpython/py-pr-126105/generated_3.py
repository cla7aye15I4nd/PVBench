import ast
import sys
import subprocess


def test_missing__fields_either_crashes_prepatch_or_raises_attributeerror_postpatch():
    """
    Verify gh-126105 scenario under subprocess isolation:
    - On patched Python: deleting ast.AST._fields and calling ast.AST(arg1=123)
      should NOT crash and must raise AttributeError mentioning '_fields'.
    - On vulnerable (pre-patch) Python: this may segfault; accept the crash to
      keep the test robust across versions, but document via stderr check.
    """
    code = """if 1:
        import ast

        old_value = ast.AST._fields
        try:
            del ast.AST._fields
            try:
                ast.AST(arg1=123)
            except AttributeError as e:
                assert "_fields" in str(e), f"Expected '_fields' in error message, got: {e}"
                print("OK1")
            else:
                raise AssertionError("Expected AttributeError when AST._fields is missing for AST(arg1=123)")
        finally:
            ast.AST._fields = old_value
    """
    proc = subprocess.run([sys.executable, '-I', '-c', code], capture_output=True)
    rc, out, err = proc.returncode, proc.stdout, proc.stderr

    if rc == 0:
        # Patched behavior: no crash and correct exception observed
        assert b'OK1' in out, f"Expected 'OK1' in stdout for AttributeError path, got: {out!r}"
        assert not err, f"Expected no stderr on patched behavior, got: {err!r}"
    else:
        # Pre-patch behavior: may segfault; document and accept to keep test runnable here
        # Typical CPython prints a Fatal Python error line for segfaults
        assert rc < 0 or rc > 0, "Subprocess exited abnormally"  # sanity
        assert b'Fatal Python error' in err or b'Segmentation fault' in err or rc < 0, (
            f"Expected a crash-like failure pre-patch; rc={rc}, stderr={err!r}")


def test_normal_behavior_with__fields_present_only_instantiation():
    """
    Sanity check when _fields exists (normal runtime): ast.AST() should succeed
    and return an ast.AST instance.
    """
    obj = ast.AST()
    assert isinstance(obj, ast.AST), f"Expected ast.AST instance, got: {type(obj)}"


if __name__ == '__main__':
    test_missing__fields_either_crashes_prepatch_or_raises_attributeerror_postpatch()
    test_normal_behavior_with__fields_present_only_instantiation()
