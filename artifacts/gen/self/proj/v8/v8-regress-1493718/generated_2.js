// Copyright 2023 the V8 project authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// This test verifies the fix related to MessageFormatter handling of
// MessageTemplate::kProxyNonObject. The patch added kProxyNonObject to the
// whitelist of message templates that can be safely formatted. Previously,
// certain Proxy errors (e.g., calling Proxy.revocable without proper object
// arguments) could cause issues during message formatting. This test ensures
// that appropriate TypeErrors are thrown and that message formatting does not
// crash for various invalid argument combinations.

// Provide a print fallback for non-d8 environments.
if (typeof print === 'undefined') {
  var print = function(...args) { console.log(...args); };
}

function assertEquals(actual, expected, message) {
  if (actual !== expected) {
    throw new Error((message || "Assertion failed") + ": expected " + expected + ", got " + actual);
  }
}

function assertThrows(fn, errorCtor) {
  let threw = false;
  try {
    fn();
  } catch (e) {
    threw = true;
    if (errorCtor && !(e instanceof errorCtor)) {
      throw new Error("Wrong exception type: " + e);
    }
    // Ensure the error message is a non-empty string, exercising the
    // MessageFormatter path that was fixed.
    if (typeof e.message !== 'string' || e.message.length === 0) {
      throw new Error("Error message should be a non-empty string, got: " + String(e.message));
    }
  }
  if (!threw) throw new Error("Expected exception was not thrown");
}

function assertDoesNotThrow(fn) {
  try {
    fn();
  } catch (e) {
    throw new Error("Did not expect exception, but got: " + e);
  }
}

// Original PoC scenario: calling Proxy.revocable() without arguments.
// Should throw a TypeError (non-object target/handler) and not crash while
// formatting the message.
assertThrows(() => Proxy.revocable(), TypeError);

// Additional negative tests for non-object target/handler combinations.
assertThrows(() => Proxy.revocable({}, undefined), TypeError);  // handler non-object
assertThrows(() => Proxy.revocable(undefined, {}), TypeError);  // target non-object
assertThrows(() => new Proxy(1, {}), TypeError);                // target non-object
assertThrows(() => new Proxy({}, 1), TypeError);                // handler non-object

// Positive control tests to ensure correct behavior when both are objects.
assertDoesNotThrow(() => {
  const p = Proxy.revocable({}, {});
  // Validate basic shape of the revocable result.
  assertEquals(typeof p, 'object');
  assertEquals(typeof p.proxy, 'object');
  assertEquals(typeof p.revoke, 'function');
  // Revoke and access proxy to ensure no unexpected crashes occur here.
  p.revoke();
  // Access after revoke should throw a TypeError due to revoked proxy traps.
  assertThrows(() => { p.proxy.foo; }, TypeError);
});

assertDoesNotThrow(() => {
  // A working proxy with empty handler.
  // This ensures the positive path isn't affected by the fix.
  const target = { x: 1 };
  const prox = new Proxy(target, {});
  assertEquals(prox.x, 1);
});

print("OK");
