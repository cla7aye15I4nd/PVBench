import _sre

try:
    _sre.template("", ["", -1, ""])
    assert False, "Expected TypeError"
except TypeError as e:
    assert "invalid template" in str(e), f"Expected 'invalid template' in error, got: {e}"

try:
    _sre.template("", ["", (), ""])
    assert False, "Expected TypeError"
except TypeError as e:
    assert "an integer is required" in str(e), f"Expected 'an integer is required' in error, got: {e}"
