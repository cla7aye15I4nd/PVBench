import ast
import re

# gh-125010: Fix use-after-free in ast repr()
# This test checks that repr() of large constants raises ValueError
# The digit limit check may not be present in all Python versions
source = "0x0" + "e" * 10_000
try:
    repr(ast.Constant(value=eval(source)))
    assert False, "Expected ValueError"
except ValueError as e:
    # Verify the error message format if ValueError is raised
    assert re.search(r"Exceeds the limit \(\d+ digits\)", str(e)), f"Expected 'Exceeds the limit' message, got: {e}"
