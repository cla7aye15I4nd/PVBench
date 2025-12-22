// Copyright 2023 the V8 project authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// This test is derived from a PoC that exercised V8's message/exception
// formatting during iterator closing. The patch ensures that when error
// formatting paths internally throw (e.g., due to self-referential messages
// or failing stack formatting), V8 clears both the pending exception and the
// pending message, so subsequent user-visible exceptions are correct and no
// crash occurs.

// Minimal self-contained assertions (do not rely on mjsunit).
function assertTrue(cond, msg) {
  if (!cond) throw new Error("Assertion failed: " + (msg || "expected true"));
}
function assertEquals(actual, expected, msg) {
  if (actual !== expected) {
    throw new Error((msg || "Assertion failed") + ": expected " + expected + ", got " + actual);
  }
}
function assertThrows(fn, ctor, re) {
  let threw = false;
  try {
    fn();
  } catch (e) {
    threw = true;
    if (ctor && !(e instanceof ctor)) {
      throw new Error("Wrong exception type: expected " + (ctor && ctor.name) + ", got " + (e && e.constructor && e.constructor.name));
    }
    if (re && !re.test(String(e))) {
      throw new Error("Exception message did not match. Got: " + String(e));
    }
  }
  if (!threw) throw new Error("Expected exception was not raised");
}

// Utility that triggers the problematic internal path from the PoC: creating
// an Error with a self-referential message and accessing its stack (which
// forces formatting/stringification of the error). This used to leave stale
// pending message/exception in some code paths.
function createErrorAndTouchStack() {
  const e = Error();
  e.message = e;  // Self-referential message can cause ToString/formatting to throw internally.
  // Force formatting; this must not throw to JS and must not leave pending
  // exception/message state behind.
  const s = e.stack;
  return s; // Should be a string (e.g., "Error\n<frames>" or "<error>")
}

(function test_iterator_close_path_preserves_original_exception() {
  // Arrange: Override ArrayIteratorPrototype.return to run code that creates an
  // Error with a self-referential message and forces stack formatting, exactly
  // like the PoC, but make sure we return an object to avoid masking the main
  // error with the IteratorClose TypeError about non-object return values.
  const iteratorProto = Object.getPrototypeOf([].values());
  const oldReturn = iteratorProto.return;
  function f0() {
    function f1() {
      const v4 = Error();
      v4.message = v4;
      // Touch stack to force C++ error formatting paths.
      v4.stack;
    }
    new f1();
    // Ensure return() returns an object so IteratorClose does not introduce a
    // secondary TypeError that could mask the original exception.
    return {};
  }
  iteratorProto.return = f0;

  try {
    // Act + Assert: Constructing WeakSet from a list containing a non-object
    // should throw a TypeError. During iterator closing, our custom return()
    // will run and internally attempt to format the error stack (which causes
    // nested exception handling). With the fix, V8 clears pending
    // message/exception appropriately so the original TypeError still surfaces
    // and there is no crash.
    assertThrows(() => { new WeakSet([1]); }, TypeError);
  } finally {
    // Restore to avoid global side effects.
    if (oldReturn === undefined) {
      delete iteratorProto.return;
    } else {
      iteratorProto.return = oldReturn;
    }
  }
})();

(function test_self_referential_message_stack_is_string_and_no_throw() {
  // Accessing .stack must not throw even if message stringification fails.
  const s = createErrorAndTouchStack();
  assertTrue(typeof s === 'string', 'stack should be a string');
})();

(function test_no_stale_pending_state_affects_subsequent_errors() {
  // First, exercise error formatting that may throw internally.
  const s = createErrorAndTouchStack();
  assertTrue(typeof s === 'string');
  // Then, immediately perform an operation that throws a well-defined error
  // and verify it is not impacted by any stale pending message/exception.
  assertThrows(() => { new WeakSet([1]); }, TypeError);
})();

print('OK');
