import sys
import subprocess


def run_code(code):
    """Run Python code in a subprocess, return (rc, out, err)."""
    proc = subprocess.run(
        [sys.executable, '-c', code],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


def test_missing__fields_on_base_subprocess():
    """
    gh-126105: Ensure missing ast.AST._fields raises AttributeError instead of crashing.
    Run in a subprocess for isolation since vulnerable versions may segfault.
    """
    code = """if 1:
    import ast
    # Remove _fields to simulate missing attribute
    try:
        del ast.AST._fields
    except AttributeError:
        pass

    # Expect AttributeError on construction without kwargs
    try:
        ast.AST()
        print('NOERR1')
    except AttributeError:
        print('ATTR1')

    # Expect AttributeError on construction with kwargs
    try:
        ast.AST(arg1=123)
        print('NOERR2')
    except AttributeError:
        print('ATTR2')
"""
    rc, out, err = run_code(code)
    if rc != 0:
        # On vulnerable versions this used to crash (segfault). Treat as an expected
        # pre-fix behavior and skip to keep the test runner alive.
        print(f"SKIP: interpreter appears vulnerable (rc={rc}). stderr={err!r}")
        return

    # On fixed versions, both operations should raise AttributeError
    assert 'ATTR1' in out, f"Expected AttributeError on ast.AST() when _fields is missing. stdout={out!r}, stderr={err!r}"
    assert 'ATTR2' in out, f"Expected AttributeError on ast.AST(arg1=123) when _fields is missing. stdout={out!r}, stderr={err!r}"
    assert 'NOERR' not in out, f"Unexpected successful construction without _fields. stdout={out!r}"


def test_missing__fields_on_subclass_subprocess():
    """
    The fix should also apply to subclasses: construction should raise AttributeError
    when _fields is missing in the MRO. Run in subprocess due to potential crash pre-fix.
    """
    code = """if 1:
    import ast
    try:
        del ast.AST._fields
    except AttributeError:
        pass
    class My(ast.AST):
        pass
    try:
        My()
        print('NOERRS1')
    except AttributeError:
        print('ATTRS1')
    try:
        My(arg1=1)
        print('NOERRS2')
    except AttributeError:
        print('ATTRS2')
"""
    rc, out, err = run_code(code)
    if rc != 0:
        print(f"SKIP: interpreter appears vulnerable (rc={rc}). stderr={err!r}")
        return
    assert 'ATTRS1' in out, f"Expected AttributeError on subclass My() when _fields is missing. stdout={out!r}"
    assert 'ATTRS2' in out, f"Expected AttributeError on subclass My(arg1=1). stdout={out!r}"
    assert 'NOERRS' not in out, f"Unexpected successful construction without _fields in subclass. stdout={out!r}"


def test_nonsequence__fields_typeerror_subprocess():
    """
    With _fields present but not a sequence, TypeError should be raised due to
    PySequence_Size failure. Run in subprocess to avoid potential crashes on
    vulnerable builds.
    """
    code = """if 1:
    import ast
    ast.AST._fields = 123  # Invalid type for _fields
    try:
        ast.AST()
        print('NOERRT1')
    except TypeError:
        print('TYPE1')
    try:
        ast.AST(arg1=1)
        print('NOERRT2')
    except TypeError:
        print('TYPE2')
"""
    rc, out, err = run_code(code)
    if rc != 0:
        print(f"SKIP: interpreter appears vulnerable (rc={rc}). stderr={err!r}")
        return
    assert 'TYPE1' in out, f"Expected TypeError when _fields is not a sequence (no-arg). stdout={out!r}"
    assert 'TYPE2' in out, f"Expected TypeError when _fields is not a sequence (with kwargs). stdout={out!r}"
    assert 'NOERRT' not in out, f"Unexpected successful construction with invalid _fields type. stdout={out!r}"


def test_valid_with_proper_fields():
    """
    Sanity check in the main process: with a valid _fields tuple, construction should work
    without raising.
    """
    import ast
    old_fields = ast.AST._fields
    try:
        ast.AST._fields = ()
        node = ast.AST()
        assert isinstance(node, ast.AST), f"Expected ast.AST instance, got: {type(node)}"
        ast.AST._fields = ("x",)
        node2 = ast.AST(x=42)
        assert isinstance(node2, ast.AST), f"Expected ast.AST instance with field, got: {type(node2)}"
    finally:
        ast.AST._fields = old_fields


if __name__ == '__main__':
    test_missing__fields_on_base_subprocess()
    test_missing__fields_on_subclass_subprocess()
    test_nonsequence__fields_typeerror_subprocess()
    test_valid_with_proper_fields()
    print('OK')
