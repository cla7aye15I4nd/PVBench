import sys
sys.modules = {f"a.b.c": {}}
__import__(f"b.c", {"__package__": "a"}, level=1)