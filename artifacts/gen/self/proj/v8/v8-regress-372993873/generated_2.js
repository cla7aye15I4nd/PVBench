// Copyright 2024 the V8 project authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// This test verifies that WebAssembly.Exception properly propagates exceptions
// thrown while accessing the `traceStack` property of the options object.
//
// Patch summary:
// Prior to the fix, exceptions thrown when reading options.traceStack were
// swallowed because a failed Get() was treated like "no property". The patch
// changes the code to assert/propagate the exception when the property access
// fails. This test ensures such exceptions are now observable and not ignored.

(function() {
  function assertEquals(actual, expected, message) {
    if (actual !== expected) {
      throw new Error((message || "Assertion failed") + ": expected " + expected + ", got " + actual);
    }
  }

  function assertTrue(cond, message) {
    if (!cond) throw new Error(message || "Assertion failed: expected true, got false");
  }

  function assertThrows(fn, errorConstructor, messageSubstring) {
    let threw = false;
    try {
      fn();
    } catch (e) {
      threw = true;
      if (errorConstructor && !(e instanceof errorConstructor)) {
        throw new Error("Wrong exception type: " + e);
      }
      if (messageSubstring !== undefined) {
        const msg = String(e && e.message);
        if (!msg.includes(String(messageSubstring))) {
          throw new Error("Unexpected exception message: '" + msg + "' does not include '" + messageSubstring + "'");
        }
      }
    }
    if (!threw) throw new Error("Expected exception was not raised");
  }

  // Prepare a simple tag with no parameters (as in the PoC).
  let tag = new WebAssembly.Tag({parameters: []});

  // Test 1 (PoC): Proxy whose generic get trap throws. The constructor must
  // propagate the error instead of swallowing it.
  {
    let proxy = new Proxy({}, {
      get() { throw new Error('boom'); }
    });
    assertThrows(() => new WebAssembly.Exception(tag, [], proxy), Error, 'boom');
  }

  // Test 2: Ensure that the property access is performed for the exact key
  // 'traceStack' and that the thrown exception is propagated. Also ensure the
  // property is accessed only once.
  {
    let getCount = 0;
    let proxy = new Proxy({}, {
      get(target, prop, receiver) {
        if (prop === 'traceStack') {
          getCount++;
          throw new Error('trace boom');
        }
        return Reflect.get(target, prop, receiver);
      }
    });
    assertThrows(() => new WebAssembly.Exception(tag, [], proxy), Error, 'trace boom');
    assertEquals(getCount, 1, 'traceStack should be accessed exactly once');
  }

  // Test 3: A plain object with an accessor getter for traceStack that throws.
  // The exception must be propagated.
  {
    let count = 0;
    let options = {};
    Object.defineProperty(options, 'traceStack', {
      get() {
        count++;
        throw new Error('getter boom');
      }
    });
    assertThrows(() => new WebAssembly.Exception(tag, [], options), Error, 'getter boom');
    assertEquals(count, 1, 'traceStack getter should be invoked exactly once');
  }

  // Test 4: Getter returns a falsy value (false). No exception should be thrown,
  // and the instance should be created successfully. Also, ensure the getter is
  // accessed exactly once.
  {
    let count = 0;
    let options = {
      get traceStack() { count++; return false; }
    };
    let ex;
    try {
      ex = new WebAssembly.Exception(tag, [], options);
    } catch (e) {
      throw new Error('Should not throw for falsy traceStack: ' + e);
    }
    assertEquals(count, 1, 'traceStack getter (falsy) should be invoked once');
    assertTrue(ex instanceof WebAssembly.Exception, 'Expected a WebAssembly.Exception instance');
  }

  // Test 5: Getter returns a truthy value (true). No exception should be thrown,
  // and the instance should be created successfully. We cannot easily verify the
  // stack capture itself here, but we verify no crash/throw and that the getter
  // was observed.
  {
    let count = 0;
    let options = {
      get traceStack() { count++; return true; }
    };
    let ex;
    try {
      ex = new WebAssembly.Exception(tag, [], options);
    } catch (e) {
      throw new Error('Should not throw for truthy traceStack: ' + e);
    }
    assertEquals(count, 1, 'traceStack getter (truthy) should be invoked once');
    assertTrue(ex instanceof WebAssembly.Exception, 'Expected a WebAssembly.Exception instance');
  }

  print('OK');
})();
