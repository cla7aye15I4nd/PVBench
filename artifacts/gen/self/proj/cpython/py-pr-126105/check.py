import ast


def test_AST_fields_NULL_check():
    """gh-126105: Check that missing _fields attribute raises AttributeError."""
    old_value = ast.AST._fields

    try:
        del ast.AST._fields

        # Both examples used to crash:
        try:
            ast.AST(arg1=123)
            assert False, "Expected AttributeError"
        except AttributeError as e:
            assert "_fields" in str(e), f"Expected '_fields' in error message, got: {e}"

        try:
            ast.AST()
            assert False, "Expected AttributeError"
        except AttributeError as e:
            assert "_fields" in str(e), f"Expected '_fields' in error message, got: {e}"
    finally:
        ast.AST._fields = old_value


if __name__ == '__main__':
    test_AST_fields_NULL_check()
