import sys
from test.support import script_helper

# This test verifies fix for GH-109894: crash in subinterpreters when raising
# MemoryError due to improperly initialized static MemoryError object.
# The patch ensures that MemoryError preallocation/initialization also happens
# for subinterpreters and that the last-resort MemoryError has empty args.
#
# Strategy:
# - Trigger MemoryError inside subinterpreters using _testcapi.run_in_subinterp
#   with operations that attempt to allocate extremely large lists.
# - Ensure the process does not crash (rc == 0) and that stderr contains
#   'MemoryError' for each failing subinterpreter run.
# - Run another subinterpreter afterwards to ensure interpreter state remains
#   usable by printing to stdout.

SIZE_LIST = sys.maxsize

code = f"""if 1:
    import _testcapi

    # 1) Trigger MemoryError via huge list multiplication in a subinterpreter.
    _testcapi.run_in_subinterp("[0]*{SIZE_LIST}")

    # 2) Trigger MemoryError again via huge list multiplication to ensure the
    #    exception machinery remains valid for subsequent errors.
    _testcapi.run_in_subinterp("[0]*{SIZE_LIST}")

    # 3) Ensure we can still create and run another subinterpreter afterwards.
    _testcapi.run_in_subinterp("print('OK')")
"""

rc, out, err = script_helper.assert_python_ok("-c", code)

# The interpreter must not crash.
assert rc == 0, f"Expected return code 0, got: {rc}"

# We expect two MemoryError reports in stderr (one for each failing subinterpreter code)
memerr_count = err.count(b"MemoryError")
assert memerr_count >= 2, (
    f"Expected at least two 'MemoryError' occurrences in stderr, got {memerr_count}:\n{err!r}"
)

# The final subinterpreter should run fine and print to stdout
assert b"OK" in out, f"Expected 'OK' in stdout from subinterpreter, got: {out!r}"

# No unexpected fatal errors should be present
assert b"Fatal Python error" not in err, f"Unexpected fatal error in stderr: {err!r}"
