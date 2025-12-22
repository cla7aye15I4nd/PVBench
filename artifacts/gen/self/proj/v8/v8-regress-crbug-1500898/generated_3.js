// This test is derived from a PoC that used iterator closing (via return)
// during WeakSet construction to trigger nested error formatting. The V8 fix
// clears pending_message alongside pending_exception in multiple formatting
// paths to avoid crashes or inconsistent states when exceptions occur while
// formatting other exceptions.

// No V8 flags were present in the original PoC; keep it flagless here.

(function(){
  function assertEquals(actual, expected, msg) {
    if (actual !== expected) {
      throw new Error((msg || "Assertion failed") + ": expected " + expected + ", got " + actual);
    }
  }

  function assertTrue(cond, msg) {
    if (!cond) throw new Error(msg || "Assertion failed: expected true");
  }

  function assertThrows(fn, ctor, regex) {
    let threw = false;
    try {
      fn();
    } catch (e) {
      threw = true;
      if (ctor && !(e instanceof ctor)) {
        throw new Error("Wrong exception type: expected " + ctor.name + ", got " + (e && e.constructor && e.constructor.name));
      }
      if (regex && !regex.test(String(e))) {
        throw new Error("Exception message did not match. Got: " + String(e) + ", expected pattern: " + regex);
      }
    }
    if (!threw) throw new Error("Expected exception was not raised");
  }

  // The function installed as Iterator.prototype.return. It purposefully
  // triggers error stack formatting while there may already be a pending
  // exception from the WeakSet constructor path.
  let return_call_count = 0;
  function f0() {
    return_call_count++;
    function f1() {
      const v4 = Error();
      // Make the message self-referential to exercise tricky formatting paths.
      v4.message = v4;
      // Access stack, which forces formatting of the error object.
      void v4.stack;
    }
    new f1();
    // Deliberately return undefined (not an object) to stress the closing path.
  }

  // Install our custom return on %IteratorPrototype%.
  const iterProto = [].values().__proto__;
  const originalReturn = iterProto.return;
  iterProto.return = f0;

  try {
    // Core regression: constructing a WeakSet from an array containing a
    // non-object must throw a TypeError. While the constructor throws, it
    // will IteratorClose the iterator, which calls our custom return, which
    // in turn triggers error formatting of another Error object. The engine
    // must not crash and must still deliver the correct TypeError.
    assertThrows(() => { new WeakSet([1]); }, TypeError, /Invalid value used in weak set/i);

    // Ensure Iterator.prototype.return was actually called (IteratorClose ran).
    assertTrue(return_call_count >= 1, "Iterator.prototype.return was not called");

    // Additional no-crash sanity: error formatting with self-referential
    // message should yield a string stack and not throw.
    (function() {
      const e = new Error("boom");
      e.message = e; // self-reference
      const s = e.stack;
      assertTrue(typeof s === 'string', "Expected Error.stack to be a string");
    })();

    // Another pass to ensure stability on repeated executions.
    assertThrows(() => { new WeakSet([null]); }, TypeError, /Invalid value used in weak set/i);
    assertTrue(return_call_count >= 2, "Iterator.prototype.return should be called again");
  } finally {
    // Restore original state to avoid side effects if the harness runs more tests.
    iterProto.return = originalReturn;
  }

  print("OK");
})();
