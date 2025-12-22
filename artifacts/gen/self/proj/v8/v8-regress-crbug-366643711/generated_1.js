// Copyright 2024 the V8 project authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// Flags: --harmony-struct --allow-natives-syntax

// This test verifies the behavior of Atomics.Condition.notify when given
// non-positive counts. According to the fix in patch.diff, notify must
// return 0 immediately and must not wake any waiters when count <= 0.
// We also verify that a large count (greater than the number of waiters)
// wakes only the existing waiters and returns the correct number.

(function() {
  'use strict';

  // Minimal assertion helpers.
  function assertEquals(expected, actual, message) {
    if (actual !== expected) {
      throw new Error((message || 'Assertion failed') + ': expected ' + expected + ', got ' + actual);
    }
  }
  function assertTrue(v, message) {
    if (!v) throw new Error(message || 'Assertion failed: expected true, got ' + v);
  }
  function assertFalse(v, message) {
    if (v) throw new Error(message || 'Assertion failed: expected false, got ' + v);
  }

  let pending = 2;
  function finish() {
    pending--;
    if (pending === 0) {
      print('OK');
    }
  }

  // Helper to spin the d8 event loop until a condition holds.
  function spinUntil(cond, then) {
    if (cond()) return then();
    setTimeout(() => spinUntil(cond, then), 0);
  }

  // Test 1: Non-positive counts (negative, -0, 0, NaN) must be a no-op and return 0.
  (function TestNotifyNonPositiveIsNoop() {
    const mutex = new Atomics.Mutex;
    const cv = new Atomics.Condition;
    let done = false;

    // Set up one waiter.
    const p = Atomics.Mutex.lockAsync(mutex, async () => {
      await Atomics.Condition.waitAsync(cv, mutex);
    });
    p.then(() => { done = true; });

    // Wait until the waiter is actually queued.
    function notifyLoop() {
      if (%AtomicsSynchronizationPrimitiveNumWaitersForTesting(cv) === 1) {
        // count < 0
        let r = Atomics.Condition.notify(cv, -14);
        assertEquals(0, r, 'negative count should return 0');
        assertEquals(1, %AtomicsSynchronizationPrimitiveNumWaitersForTesting(cv), 'negative count should not wake');
        assertFalse(done, 'waiter should still be pending after negative notify');

        // count = -0
        r = Atomics.Condition.notify(cv, -0);
        assertEquals(0, r, 'negative zero count should return 0');
        assertEquals(1, %AtomicsSynchronizationPrimitiveNumWaitersForTesting(cv), 'negative zero should not wake');
        assertFalse(done, 'waiter should still be pending after -0 notify');

        // count = 0
        r = Atomics.Condition.notify(cv, 0);
        assertEquals(0, r, 'zero count should return 0');
        assertEquals(1, %AtomicsSynchronizationPrimitiveNumWaitersForTesting(cv), 'zero should not wake');
        assertFalse(done, 'waiter should still be pending after zero notify');

        // count = NaN (ToInteger(NaN) => +0), should be treated as <= 0
        r = Atomics.Condition.notify(cv, NaN);
        assertEquals(0, r, 'NaN should be coerced then treated as <= 0 and return 0');
        assertEquals(1, %AtomicsSynchronizationPrimitiveNumWaitersForTesting(cv), 'NaN should not wake');
        assertFalse(done, 'waiter should still be pending after NaN notify');

        // Now actually wake one waiter with default count (1).
        r = Atomics.Condition.notify(cv);
        assertEquals(1, r, 'default notify should wake one');

        // Wait until the waiter is removed and the async scope completes.
        spinUntil(() => %AtomicsSynchronizationPrimitiveNumWaitersForTesting(cv) === 0 && done,
                  finish);
        return;
      }
      setTimeout(notifyLoop, 0);
    }
    notifyLoop();
  })();

  // Test 2: Large positive count should be capped; with a single waiter it should wake exactly 1 and return 1.
  (function TestNotifyLargeCountCapsToWaiters() {
    const mutex = new Atomics.Mutex;
    const cv = new Atomics.Condition;
    let done = false;

    const p = Atomics.Mutex.lockAsync(mutex, async () => {
      await Atomics.Condition.waitAsync(cv, mutex);
    });
    p.then(() => { done = true; });

    function notifyLoop() {
      if (%AtomicsSynchronizationPrimitiveNumWaitersForTesting(cv) === 1) {
        // Use a very large count; only one waiter exists.
        const r = Atomics.Condition.notify(cv, 1e9);
        assertEquals(1, r, 'large count should only wake existing waiters (1)');
        // Wait for the waiter to be removed and completion to propagate.
        spinUntil(() => %AtomicsSynchronizationPrimitiveNumWaitersForTesting(cv) === 0 && done,
                  finish);
        return;
      }
      setTimeout(notifyLoop, 0);
    }
    notifyLoop();
  })();
})();
