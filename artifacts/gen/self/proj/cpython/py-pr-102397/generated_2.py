from test.support.script_helper import assert_python_ok

# This test verifies the fix for a segfault caused by a race condition in signal handling
# during garbage collection (see gh-102397). The patch adds NULL checks in
# signalmodule.c:compare_handler() to avoid dereferencing NULL pointers when comparing
# signal handlers while a signal is delivered concurrently (e.g., via _thread.interrupt_main)
# during GC callbacks.
#
# Strategy:
# - Use subprocess isolation via assert_python_ok because the original bug could crash the
#   interpreter. If the subprocess exits cleanly (rc==0), then no segfault happened.
# - Trigger SIGINT from within a gc callback many times to increase the chance of hitting
#   the previously racy path.
# - Install Python-level SIGINT handlers and assert they run (check stdout), with no stderr.
# - Also exercise rapid handler changes inside the gc callback to stress compare_handler().

# Test 1: Trigger SIGINT from a GC callback with a Python handler installed.
# Expect: process should not crash, SIGINT handler should run at least once, no stderr.
code1 = """if 1:
    import gc, signal, _thread

    # Make GC very eager to trigger callbacks frequently.
    gc.set_threshold(1, 0, 0)

    def handler(signum, frame):
        print("SIGINT")

    signal.signal(signal.SIGINT, handler)

    def cb(*args):
        # Interrupt main thread: this schedules SIGINT delivery.
        _thread.interrupt_main()

    gc.callbacks.append(cb)

    # Trigger many GC cycles by allocating container objects.
    for i in range(200):
        [0, 1, 2, 3]  # list allocation (container) -> tracked by GC

    # Cleanup: remove the callback so interpreter shutdown isn't noisy.
    gc.callbacks.remove(cb)

    print("DONE1")
"""

rc, out, err = assert_python_ok('-c', code1)
assert rc == 0, f"Expected return code 0, got: {rc}"
assert b"SIGINT" in out, f"Expected SIGINT handler to run (stdout), got: {out!r}"
assert b"DONE1" in out, f"Expected 'DONE1' marker in stdout, got: {out!r}"
assert not err, f"Expected no stderr, got: {err!r}"

# Test 2: Rapidly change SIGINT handler within the GC callback before interrupting main.
# This stresses signalmodule.c's compare_handler and ensures the added NULL checks prevent
# crashes if internal handler objects are temporarily NULL during comparison.
# Expect: process should not crash, the final handler (h2) should run, no stderr.
code2 = """if 1:
    import gc, signal, _thread

    gc.set_threshold(1, 0, 0)

    def h1(signum, frame):
        print("H1")

    def h2(signum, frame):
        print("H2")

    # Install an initial handler so we also test transition away from Python -> DFL/IGN -> Python
    signal.signal(signal.SIGINT, h1)

    def cb(*args):
        # Change handlers quickly to exercise handler comparison logic.
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        signal.signal(signal.SIGINT, h2)
        _thread.interrupt_main()

    gc.callbacks.append(cb)

    # Trigger many GC cycles to invoke the callback.
    for i in range(200):
        {}  # dict allocation (also GC-tracked)

    gc.callbacks.remove(cb)

    print("DONE2")
"""

rc, out, err = assert_python_ok('-c', code2)
assert rc == 0, f"Expected return code 0, got: {rc}"
# Ensure that the final handler ran at least once.
assert b"H2" in out, f"Expected final SIGINT handler 'H2' to run, got stdout: {out!r}"
assert b"DONE2" in out, f"Expected 'DONE2' marker in stdout, got: {out!r}"
assert not err, f"Expected no stderr, got: {err!r}"
