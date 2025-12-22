// Copyright 2023 the V8 project authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// This test is derived from a PoC that previously could crash V8 when
// iterator closing (Iterator.prototype.return) triggered nested exception
// formatting. The fix clears pending_message whenever pending_exception is
// cleared in various message/stack formatting paths. This test ensures that
// no crash occurs and that the original TypeError from Weak{Set,Map} is
// preserved and correctly reported even when Iterator.prototype.return
// performs error formatting (accessing .stack of a self-referential Error).

function assertThrows(fn, ctor, messagePattern) {
  let threw = false;
  try {
    fn();
  } catch (e) {
    threw = true;
    if (ctor && !(e instanceof ctor)) {
      throw new Error("Wrong exception type: expected " + (ctor && ctor.name) + ", got " + (e && e.constructor && e.constructor.name));
    }
    if (messagePattern) {
      const msg = String(e && e.message);
      if (!messagePattern.test(msg)) {
        throw new Error("Unexpected message: '" + msg + "' does not match " + messagePattern);
      }
    }
  }
  if (!threw) throw new Error("Expected exception was not thrown");
}

// Install a custom Iterator.prototype.return that triggers nested error
// stringification and stack trace formatting, similar to the original PoC.
const iteratorProto = [].values().__proto__;
const originalReturn = iteratorProto.return;

function triggeringReturn() {
  // Create an Error whose message is a self-reference, then touch .stack to
  // exercise MessageHandler / ErrorUtils formatting logic.
  const err = Error();
  err.message = err; // Self-referential message to complicate stringification
  // Accessing .stack triggers stack trace formatting machinery.
  void err.stack;
  // Do not throw here; the original error from the caller should be preserved.
  return { done: true };
}

iteratorProto.return = triggeringReturn;

try {
  // 1) Reproduce the PoC scenario: WeakSet with a primitive value must throw
  //    TypeError("Invalid value used in weak set"). IteratorClose will call our
  //    custom return(), which in turn triggers nested error formatting. The
  //    engine must not crash and must still report the original TypeError.
  assertThrows(() => { new WeakSet([1]); }, TypeError, /Invalid value used in weak set/);

  // 2) Stress: run multiple times to catch any statefulness around pending
  //    messages/exceptions. Previously, stale pending messages could cause
  //    reentrancy issues; this ensures they are cleared between attempts.
  for (let i = 0; i < 10; i++) {
    assertThrows(() => { new WeakSet([1]); }, TypeError, /Invalid value used in weak set/);
  }

  // 3) Similar scenario for WeakMap: using a primitive key must throw
  //    TypeError("Invalid value used as weak map key"). Ensure iterator closing
  //    still triggers our return() without interfering with the reported error.
  assertThrows(() => { new WeakMap([[1, 1]]); }, TypeError, /Invalid value used as weak map key/);

  for (let i = 0; i < 10; i++) {
    assertThrows(() => { new WeakMap([[1, 1]]); }, TypeError, /Invalid value used as weak map key/);
  }

  // 4) Control check: constructing a Set with valid inputs should not invoke
  //    Iterator.prototype.return (no abrupt completion), so this should simply
  //    work and not throw or crash.
  new Set([1, 2, 3]);

  // If we reach here without throwing, the engine handled nested exception
  // formatting correctly while clearing pending messages.
  print("OK");
} finally {
  // Restore original Iterator.prototype.return to avoid side effects.
  iteratorProto.return = originalReturn;
}
