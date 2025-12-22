from test.support.script_helper import assert_python_ok

# This test targets a race condition in signal handling that could cause a segfault
# when a SIGINT (via _thread.interrupt_main) is triggered during garbage collection
# callbacks. The patch adds a NULL check in signalmodule.c's compare_handler to avoid
# dereferencing NULL during such races.
#
# We validate two scenarios:
# 1) Without a custom SIGINT handler: the signal is safely ignored during the race and
#    an informative OSError message is written to stderr. No crash should occur.
# 2) With a custom SIGINT handler installed inside the GC callback: the handler should
#    run and produce observable output, again with no crash.


def test_signal_during_gc_is_ignored_safely():
    code = """if 1:
        import gc
        import _thread

        # Cause frequent GC to make callback execution deterministic.
        gc.set_threshold(1, 0, 0)

        # GC callback that triggers a SIGINT delivery to the main thread.
        def cb(*args):
            _thread.interrupt_main()

        gc.callbacks.append(cb)

        # Trigger the GC callback synchronously.
        gc.collect()
    """

    rc, out, err = assert_python_ok('-c', code)
    # The interpreter should not crash and should report the race condition.
    assert rc == 0, f"Expected return code 0, got: {rc} (stderr: {err!r})"
    # Expect the known diagnostic message for a SIGINT ignored due to race condition.
    expected = b'OSError: Signal 2 ignored due to race condition'
    assert expected in err, (
        f"Expected diagnostic in stderr. Missing {expected!r} in stderr: {err!r}"
    )


def test_custom_sigint_handler_runs_inside_gc_callback():
    code = """if 1:
        import gc
        import _thread
        import signal

        # Cause frequent GC to make callback execution deterministic.
        gc.set_threshold(1, 0, 0)

        def cb(*args):
            # Install a custom SIGINT handler and immediately interrupt main.
            signal.signal(signal.SIGINT, lambda *a: print('SIGINT'))
            _thread.interrupt_main()

        gc.callbacks.append(cb)

        # Trigger the GC callback synchronously.
        gc.collect()
    """

    rc, out, err = assert_python_ok('-c', code)
    # No crash and the custom handler should be invoked.
    assert rc == 0, f"Expected return code 0, got: {rc} (stderr: {err!r})"
    assert b'SIGINT' in out, f"Expected 'SIGINT' in stdout, got: {out!r}"
    # No unexpected errors should appear on stderr in this case.
    assert err == b'' or b'Signal 2 ignored due to race condition' not in err, (
        f"Did not expect race-condition diagnostic when a custom handler is installed. stderr: {err!r}"
    )


if __name__ == '__main__':
    test_signal_during_gc_is_ignored_safely()
    test_custom_sigint_handler_runs_inside_gc_callback()
    print('OK')
