import readline

# Negative values should be disallowed
try:
    readline.append_history_file(-42, __file__)
    assert False, "Expected ValueError"
except ValueError:
    pass

# gh-122431: using the minimum signed integer value caused a segfault
try:
    readline.append_history_file(-2147483648, __file__)
    assert False, "Expected ValueError"
except ValueError:
    pass

readline.append_history_file(0, __file__)