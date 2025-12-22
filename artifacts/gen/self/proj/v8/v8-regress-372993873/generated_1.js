// Copyright 2024 the V8 project authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// This test verifies the behavior of WebAssembly.Exception's options handling
// for the "traceStack" property. The patch ensures that if accessing the
// "traceStack" property on the options object throws, that exception is
// propagated (instead of being ignored or causing engine issues). It also
// validates that truthy/falsey values are respected for stack capturing.

(function() {
  // Basic assertion helpers
  function assertTrue(cond, msg) {
    if (!cond) throw new Error("Assertion failed: " + (msg || "expected true"));
  }
  function assertFalse(cond, msg) {
    if (cond) throw new Error("Assertion failed: " + (msg || "expected false"));
  }
  function assertEquals(actual, expected, msg) {
    if (actual !== expected) {
      throw new Error((msg || "Assertion failed") + ": expected " + expected + ", got " + actual);
    }
  }
  function assertThrows(fn, ctor, messageSubstring) {
    let threw = false;
    try {
      fn();
    } catch (e) {
      threw = true;
      if (ctor && !(e instanceof ctor)) {
        throw new Error("Wrong exception type: expected " + (ctor && ctor.name) + ", got " + e);
      }
      if (messageSubstring !== undefined) {
        const msg = String(e && e.message !== undefined ? e.message : e);
        if (!msg.includes(messageSubstring)) {
          throw new Error("Exception message does not include '" + messageSubstring + "': " + msg);
        }
      }
    }
    if (!threw) throw new Error("Expected exception was not raised");
  }
  function assertThrowsValue(fn, expected) {
    let threw = false;
    try {
      fn();
    } catch (e) {
      threw = true;
      if (e !== expected) {
        throw new Error("Wrong thrown value: expected " + expected + ", got " + e);
      }
    }
    if (!threw) throw new Error("Expected exception was not raised");
  }

  // Prepare a basic tag for constructing WebAssembly.Exception instances.
  let tag = new WebAssembly.Tag({ parameters: [] });

  // 1) Main regression: If accessing options.traceStack throws, the constructor
  //    must propagate that exception. Previously, the engine ignored the failure
  //    and could proceed with a pending exception, leading to incorrect behavior.
  {
    let proxy = new Proxy({}, {
      get() { throw new Error('boom'); }
    });
    assertThrows(() => new WebAssembly.Exception(tag, [], proxy), Error, 'boom');
  }

  // 1b) Also check propagation for non-Error thrown values.
  {
    let proxy = new Proxy({}, {
      get() { throw "kapow"; }
    });
    assertThrowsValue(() => new WebAssembly.Exception(tag, [], proxy), "kapow");
  }

  // 2) If traceStack is truthy, a stack should be captured (stack is a string).
  {
    let getCount = 0;
    const options = new Proxy({}, {
      get(target, prop, receiver) {
        if (prop === 'traceStack') {
          getCount++;
          // Return a truthy value that is not a boolean to ensure coercion happens.
          return { valueOf() { return 1; } };
        }
        return Reflect.get(target, prop, receiver);
      }
    });
    const ex = new WebAssembly.Exception(tag, [], options);
    assertEquals(getCount, 1, 'traceStack getter should be called exactly once');
    assertEquals(typeof ex.stack, 'string', 'stack should be a string when traceStack is truthy');
    assertTrue(ex.stack.length > 0, 'stack string should be non-empty');
  }

  // 3) If traceStack is falsy, stack should not be captured.
  {
    let getCount = 0;
    const options = new Proxy({}, {
      get(target, prop, receiver) {
        if (prop === 'traceStack') {
          getCount++;
          return 0; // falsy
        }
        return Reflect.get(target, prop, receiver);
      }
    });
    const ex = new WebAssembly.Exception(tag, [], options);
    assertEquals(getCount, 1, 'traceStack getter should be called exactly once');
    assertEquals(ex.stack, undefined, 'stack should be undefined when traceStack is falsy');
  }

  // 4) If options are omitted, construction should succeed (default: no stack capture).
  {
    const ex = new WebAssembly.Exception(tag, []);
    assertTrue(ex instanceof WebAssembly.Exception, 'constructed object should be a WebAssembly.Exception');
    // stack likely undefined; do not assert strongly here beyond non-throwing construction.
  }

  print('OK');
})();