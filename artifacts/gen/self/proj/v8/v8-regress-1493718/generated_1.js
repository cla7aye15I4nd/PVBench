// Copyright 2023 the V8 project authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// This test verifies that throwing TypeError for invalid Proxy/Proxy.revocable
// arguments formats the error message correctly (no crash during message
// formatting). The patch adds MessageTemplate::kProxyNonObject to the
// MessageFormatter, so we assert that such errors are thrown and have a
// non-empty message string.

function assert(condition, message) {
  if (!condition) throw new Error(message || "Assertion failed");
}

function assertEquals(actual, expected, message) {
  if (actual !== expected) {
    throw new Error((message || "Assertion failed") + ": expected " + expected + ", got " + actual);
  }
}

function assertThrows(fn, errorConstructor, message) {
  let threw = false;
  try {
    fn();
  } catch (e) {
    threw = true;
    if (errorConstructor) {
      assert(e instanceof errorConstructor, (message || "Wrong exception type") + ": " + e);
    }
    // The bug fix ensures proper message formatting for Proxy non-object errors.
    assert(typeof e.message === 'string', 'Error message should be a string');
    assert(e.message.length > 0, 'Error message should be non-empty');
    // Accessing toString should also not crash and return a string.
    const s = String(e);
    assert(typeof s === 'string' && s.length > 0, 'Error toString() should produce non-empty string');
    return;
  }
  if (!threw) throw new Error((message || "Expected exception was not raised"));
}

// 1) Direct PoC: calling Proxy.revocable() with no arguments should throw TypeError
// and produce a formatted error message without crashing.
assertThrows(() => Proxy.revocable(), TypeError, 'Proxy.revocable() without args should throw TypeError');

// 2) Various invalid target/handler combinations should throw TypeError and have
// properly formatted messages. These exercise the kProxyNonObject template.
const nonObjects = [undefined, null, 0, 1, true, false, "str", Symbol('s'), 10n, NaN];

for (const badTarget of nonObjects) {
  assertThrows(() => Proxy.revocable(badTarget, {}), TypeError, 'Non-object target should throw');
}
for (const badHandler of nonObjects) {
  assertThrows(() => Proxy.revocable({}, badHandler), TypeError, 'Non-object handler should throw');
}
// Both invalid
for (const a of nonObjects) {
  for (const b of nonObjects) {
    assertThrows(() => Proxy.revocable(a, b), TypeError, 'Non-object target and handler should throw');
  }
}

// 3) The constructor path should also throw TypeError with proper formatting.
assertThrows(() => new Proxy(), TypeError, 'new Proxy() should throw');
assertThrows(() => new Proxy(undefined, {}), TypeError, 'Undefined target should throw');
assertThrows(() => new Proxy({}, undefined), TypeError, 'Undefined handler should throw');
assertThrows(() => new Proxy(1, {}), TypeError, 'Primitive target should throw');
assertThrows(() => new Proxy({}, 1), TypeError, 'Primitive handler should throw');

// 4) Sanity check: valid usage should succeed and not throw.
let called = false;
const target = { x: 1 };
const handler = { get(t, p, r) { called = true; return Reflect.get(t, p, r); } };
const rec = Proxy.revocable(target, handler);
assert(typeof rec === 'object' && rec !== null, 'revocable should return an object');
assert(typeof rec.proxy === 'object' && rec.proxy !== null, 'revocable.proxy should be an object');
assertEquals(typeof rec.revoke, 'function', 'revocable.revoke should be a function');
// Using the proxy should work.
assertEquals(rec.proxy.x, 1, 'Proxy should forward property access');
assertEquals(called, true, 'Handler get trap should be called');

print('OK');
