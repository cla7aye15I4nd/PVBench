from test.support.script_helper import assert_python_ok

# Test 1: Trigger SIGINT via _thread.interrupt_main from within a GC callback.
# Historically this could segfault due to a race condition in signal handling
# during garbage collection (see CPython issue gh-102397). The fix adds NULL
# checks in compare_handler to avoid dereferencing NULL pointers.
# Expected behavior after the fix: no crash. Depending on platform/version,
# the signal raised during GC may be reported as an ignored KeyboardInterrupt
# (unraisable in the callback) or logged as an OSError explaining the race.
code1 = """if 1:
    import gc, _thread

    # Make GC very aggressive so callbacks are invoked promptly.
    gc.set_threshold(1, 0, 0)

    def cb(*args):
        # Interrupt the main thread (simulate SIGINT) from within GC callback
        _thread.interrupt_main()

    gc.callbacks.append(cb)
    try:
        # Force a full collection which will invoke the callback (both start/stop phases)
        gc.collect()
    finally:
        gc.callbacks.remove(cb)
"""

rc, out, err = assert_python_ok('-c', code1)
assert rc == 0, f"Expected return code 0 for GC-callback interrupt_main test (no crash), got: {rc}"
# Accept either the explicit OSError race message or an ignored KeyboardInterrupt
# emitted from the GC callback as valid outcomes post-fix. The critical part is
# the absence of a crash.
expected_oserror = b'OSError: Signal 2 ignored due to race condition' in err
expected_kbi = b'KeyboardInterrupt' in err
assert expected_oserror or expected_kbi, (
    f"Expected either an OSError race message or an ignored KeyboardInterrupt in stderr; got: {err!r}"
)

# Test 2: If a Python-level SIGINT handler is installed inside the GC callback
# before interrupt_main is called, the handler should run (no crash) and print
# to stdout. Stderr should not contain unhandled exceptions.
code2 = """if 1:
    import gc, _thread, signal

    gc.set_threshold(1, 0, 0)

    def cb(*args):
        # Install a custom handler and then interrupt main
        signal.signal(signal.SIGINT, lambda *a: print("SIGINT"))
        _thread.interrupt_main()

    gc.callbacks.append(cb)
    try:
        gc.collect()
    finally:
        gc.callbacks.remove(cb)
"""

rc, out, err = assert_python_ok('-c', code2)
assert rc == 0, f"Expected return code 0 for custom SIGINT handler test, got: {rc}"
assert b'SIGINT' in out, f"Expected 'SIGINT' in stdout from custom handler, got: {out!r}"
# Allow empty stderr or benign noise, but must not contain a crash or unhandled KeyboardInterrupt
assert b'Traceback' not in err, f"Unexpected traceback in stderr: {err!r}"
assert b'Segmentation fault' not in err and b'Fatal Python error' not in err, (
    f"Detected crash-related output in stderr: {err!r}"
)

# If we reached this point, both scenarios behaved as expected following the fix.
