import sys

loooong = "".ljust(0x23000, "b")
name = f"a.{loooong}.c"

old_modules = sys.modules.copy()
try:
    sys.modules[name] = {}
    try:
        __import__(f"{loooong}.c", {"__package__": "a"}, level=1)
        assert False, "Expected KeyError"
    except KeyError as e:
        assert "not in sys.modules as expected" in str(e), f"Expected 'not in sys.modules as expected' in error, got: {e}"
finally:
    sys.modules.clear()
    sys.modules.update(old_modules)
