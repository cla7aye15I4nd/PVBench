import ast
dir(ast.AST)
del ast.AST._fields
dir(ast.AST)
t = ast.AST(arg1=123)
