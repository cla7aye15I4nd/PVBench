from test.support.script_helper import assert_python_ok

code = """if 1:
    import _thread
    class Foo():
        def __del__(self):
            _thread.interrupt_main()
    x = Foo()
"""

rc, out, err = assert_python_ok('-c', code)
assert b'OSError: Signal 2 ignored due to race condition' in err, f"Expected OSError message in stderr, got: {err}"

code = """if 1:
    import _thread
    import signal
    class Foo():
        def __del__(self):
            signal.signal(signal.SIGINT, lambda *args: print("SIGINT"))
            _thread.interrupt_main()
    x = Foo()
"""

rc, out, err = assert_python_ok('-c', code)
assert rc == 0, f"Expected return code 0, got: {rc}"
assert b'SIGINT' in out, f"Expected 'SIGINT' in stdout, got: {out}"
assert err == b'', f"Expected empty stderr, got: {err}"