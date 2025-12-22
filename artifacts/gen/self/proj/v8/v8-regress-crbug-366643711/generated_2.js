// Copyright 2024 the V8 project authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// Flags: --harmony-struct --allow-natives-syntax

// Simple assertion helpers (self-contained, no test harness dependencies).
function assertEquals(expected, actual, msg) {
  if (expected !== actual) {
    throw new Error((msg || "assertEquals failed") + ": expected " + expected + ", got " + actual);
  }
}
function assertTrue(v, msg) {
  if (v !== true) throw new Error(msg || ("assertTrue failed: got " + v));
}
function assertFalse(v, msg) {
  if (v !== false) throw new Error(msg || ("assertFalse failed: got " + v));
}

let __async_test_done__ = false;
let __sync_test_done__ = false;

(function TestNegativeAndZeroNotifyDoNotWakeAndReturnZero() {
  // This test validates the fix in AtomicsConditionNotify where counts <= 0
  // should return 0 immediately and must not wake any waiters.
  const mutex = new Atomics.Mutex;
  const cv = new Atomics.Condition;
  let done = false;

  // Spawn a waiter that will block on the condition variable.
  let promise = Atomics.Mutex.lockAsync(mutex, async () => {
    await Atomics.Condition.waitAsync(cv, mutex);
  });
  promise.then(() => { done = true; });

  // Wait until exactly one waiter is queued on the condition variable.
  const notifyWhenOneWaiter = () => {
    const waiters = %AtomicsSynchronizationPrimitiveNumWaitersForTesting(cv);
    if (waiters === 1) {
      // After the patch, notify with <= 0 should:
      //  - return 0
      //  - not change the number of waiters
      //  - not resolve the waiter (done stays false)
      assertEquals(0, Atomics.Condition.notify(cv, -14), "negative count should return 0");
      assertEquals(1, %AtomicsSynchronizationPrimitiveNumWaitersForTesting(cv), "negative count should not wake");
      assertFalse(done, "negative count should not resolve waiter");

      assertEquals(0, Atomics.Condition.notify(cv, -0), "-0 count should return 0");
      assertEquals(1, %AtomicsSynchronizationPrimitiveNumWaitersForTesting(cv), "-0 should not wake");
      assertFalse(done, "-0 should not resolve waiter");

      assertEquals(0, Atomics.Condition.notify(cv, 0), "zero count should return 0");
      assertEquals(1, %AtomicsSynchronizationPrimitiveNumWaitersForTesting(cv), "zero should not wake");
      assertFalse(done, "zero should not resolve waiter");

      assertEquals(0, Atomics.Condition.notify(cv, NaN), "NaN coerces to 0 -> return 0");
      assertEquals(1, %AtomicsSynchronizationPrimitiveNumWaitersForTesting(cv), "NaN->0 should not wake");
      assertFalse(done, "NaN->0 should not resolve waiter");

      assertEquals(0, Atomics.Condition.notify(cv, "-5"), "string -5 -> -5 -> return 0");
      assertEquals(1, %AtomicsSynchronizationPrimitiveNumWaitersForTesting(cv), "string -5 should not wake");
      assertFalse(done, "string -5 should not resolve waiter");

      assertEquals(0, Atomics.Condition.notify(cv, "-0"), "string -0 -> -0 -> return 0");
      assertEquals(1, %AtomicsSynchronizationPrimitiveNumWaitersForTesting(cv), "string -0 should not wake");
      assertFalse(done, "string -0 should not resolve waiter");

      // Now perform a real notify with count=1 and verify it wakes the waiter.
      assertEquals(1, Atomics.Condition.notify(cv, 1), "positive count 1 should return 1");
      // After a successful notify, the waiter should have been dequeued immediately.
      assertEquals(0, %AtomicsSynchronizationPrimitiveNumWaitersForTesting(cv), "notify(1) should dequeue the waiter");

      // The waiter completion (and promise resolution) is async; poll until done.
      const waitDone = () => {
        if (done) { __async_test_done__ = true; return; }
        setTimeout(waitDone, 0);
      };
      waitDone();
      return;
    }
    // Keep spinning until the waiter is installed.
    setTimeout(notifyWhenOneWaiter, 0);
  };
  notifyWhenOneWaiter();
})();

(function TestZeroAndNegativeWithNoWaitersReturnZeroAndNoop() {
  // With no waiters, counts <= 0 should be a no-op and return 0.
  const cv = new Atomics.Condition;
  assertEquals(0, %AtomicsSynchronizationPrimitiveNumWaitersForTesting(cv));

  assertEquals(0, Atomics.Condition.notify(cv, -1), "negative with no waiters should return 0");
  assertEquals(0, %AtomicsSynchronizationPrimitiveNumWaitersForTesting(cv));

  assertEquals(0, Atomics.Condition.notify(cv, 0), "zero with no waiters should return 0");
  assertEquals(0, %AtomicsSynchronizationPrimitiveNumWaitersForTesting(cv));

  assertEquals(0, Atomics.Condition.notify(cv, NaN), "NaN->0 with no waiters should return 0");
  assertEquals(0, %AtomicsSynchronizationPrimitiveNumWaitersForTesting(cv));

  __sync_test_done__ = true;
})();

// Final watchdog to ensure the asynchronous part completed and no crash occurred.
(function FinishWhenIdle() {
  const checkDone = () => {
    if (__async_test_done__ && __sync_test_done__) {
      print("OK");
      return;
    }
    setTimeout(checkDone, 0);
  };
  checkDone();
})();
