// Copyright 2023 the V8 project authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// This test exercises the behavior of Proxy and Proxy.revocable when given
// non-object targets/handlers. The patch added MessageTemplate::kProxyNonObject
// to the list of safely format-able messages, ensuring that throwing these
// TypeErrors does not cause additional failures during message formatting.
// We verify that appropriate TypeErrors are thrown (and no crash occurs),
// and that valid usages still behave correctly.

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
  }
  if (!threw) throw new Error("Expected exception was not raised");
}

// 1) The original PoC: calling Proxy.revocable with no arguments should throw
// a TypeError because both target and handler are non-objects (undefined).
assertThrows(() => Proxy.revocable(), TypeError);

// 2) Ensure specific non-object target/handler cases throw TypeError.
assertThrows(() => Proxy.revocable(undefined, {}), TypeError);
assertThrows(() => Proxy.revocable({}, undefined), TypeError);
assertThrows(() => Proxy.revocable(1, {}), TypeError);
assertThrows(() => Proxy.revocable({}, 1), TypeError);

// Also cover the direct Proxy constructor to ensure consistency.
assertThrows(() => new Proxy(undefined, {}), TypeError);
assertThrows(() => new Proxy({}, undefined), TypeError);
assertThrows(() => new Proxy(1, {}), TypeError);
assertThrows(() => new Proxy({}, 1), TypeError);

// 3) Valid usage should succeed and provide a working proxy until revoked.
{
  const { proxy, revoke } = Proxy.revocable({}, {});
  assertEquals(typeof proxy, "object");
  assertEquals(typeof revoke, "function");

  proxy.x = 42;
  assertEquals(proxy.x, 42);

  // After revocation, any interaction should throw a TypeError (kProxyRevoked).
  revoke();
  assertThrows(() => proxy.x, TypeError);
  assertThrows(() => { proxy.x = 1; }, TypeError);
}

// 4) Valid usage with a callable target should still work, ensuring the test
// doesn't over-constrain behavior and only targets the non-object rejection.
{
  const { proxy, revoke } = Proxy.revocable(function f() { return 7; }, {});
  assertEquals(typeof proxy, "function");
  assertEquals(proxy(), 7);
  revoke();
  assertThrows(() => proxy(), TypeError);
}

print("OK");