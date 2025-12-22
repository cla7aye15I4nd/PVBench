import sys
from test.support import script_helper

code = f"""if 1:
    import _testcapi
    _testcapi.run_in_subinterp("[0]*{sys.maxsize}")
    exit(0)
"""

rc, out, err = script_helper.assert_python_ok("-c", code)
assert b'MemoryError' in err, f"Expected MemoryError in stderr, got: {err}"
