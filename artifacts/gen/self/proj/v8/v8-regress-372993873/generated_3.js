// Copyright 2024 the V8 project authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// This test verifies that WebAssembly.Exception properly propagates exceptions
// thrown while accessing the "traceStack" property of the options object
// (3rd argument). The patch ensures that if options.traceStack getter throws,
// the constructor asserts and propagates the exception instead of silently
// swallowing it.

// Helper assertions
function assertTrue(cond, msg) {
  if (!cond) throw new Error("Assertion failed: " + (msg || "expected true"));
}
function assertFalse(cond, msg) {
  if (cond) throw new Error("Assertion failed: " + (msg || "expected false"));
}
function assertEquals(actual, expected, message) {
  if (actual !== expected) {
    throw new Error((message || "Assertion failed") + ": expected " + expected + ", got " + actual);
  }
}
function assertThrows(fn, errorCtor, messageSubstring) {
  let threw = false;
  try {
    fn();
  } catch (e) {
    threw = true;
    if (errorCtor && !(e instanceof errorCtor)) {
      throw new Error("Wrong exception type: " + e);
    }
    if (messageSubstring !== undefined) {
      const msg = String(e && e.message);
      if (!msg.includes(messageSubstring)) {
        throw new Error("Exception message mismatch. Expected substring '" + messageSubstring + "', got '" + msg + "'");
      }
    }
  }
  if (!threw) {
    throw new Error("Expected exception was not raised");
  }
}

// Minimal setup: a tag to construct WebAssembly.Exception instances
let tag = new WebAssembly.Tag({ parameters: [] });

// 1) Core regression: options object whose 'get' trap always throws.
//    Prior to the fix, the exception from accessing options.traceStack could be
//    swallowed. Now it must propagate.
{
  let proxy = new Proxy({}, {
    get() { throw new Error('boom'); }
  });
  assertThrows(() => new WebAssembly.Exception(tag, [], proxy), Error, 'boom');
}

// 2) Targeted regression: throwing only when 'traceStack' is accessed.
//    Ensures the property access is performed and its exception is propagated.
{
  let proxy = new Proxy({}, {
    get(target, prop, receiver) {
      if (prop === 'traceStack') throw new Error('traceStack-getter-throws');
      return Reflect.get(target, prop, receiver);
    }
  });
  assertThrows(() => new WebAssembly.Exception(tag, [], proxy), Error, 'traceStack-getter-throws');
}

// 3) Non-throwing case: options with traceStack: false should construct fine.
{
  const e = new WebAssembly.Exception(tag, [], { traceStack: false });
  assertTrue(e instanceof WebAssembly.Exception, 'Expected a WebAssembly.Exception instance');
  // If no trace is captured, the implementation typically omits the 'stack' property.
  // Do not assert strict absence to avoid depending on engine internals.
}

// 4) Non-throwing case: options with traceStack: true should also construct fine.
//    If a stack is captured, a 'stack' string may be present; if not, this should
//    at least not throw. We assert type only if present to be robust across builds.
{
  const e = new WebAssembly.Exception(tag, [], { traceStack: true });
  assertTrue(e instanceof WebAssembly.Exception, 'Expected a WebAssembly.Exception instance');
  if ('stack' in e) {
    assertEquals(typeof e.stack, 'string', 'stack should be a string when present');
  }
}

// 5) Edge: options object returns a non-boolean truthy value for traceStack.
//    Boolean conversion should not throw and should be treated as truthy.
{
  const options = { traceStack: { some: 'object' } }; // objects are truthy
  const e = new WebAssembly.Exception(tag, [], options);
  assertTrue(e instanceof WebAssembly.Exception);
}

print('OK');
