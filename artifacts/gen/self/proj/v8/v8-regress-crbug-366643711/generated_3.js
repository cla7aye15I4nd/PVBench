// Copyright 2024 the V8 project authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// Flags: --harmony-struct --allow-natives-syntax

// This test verifies the semantics of Atomics.Condition.notify when the count
// argument is non-positive. The patch changes the builtin to immediately return
// 0 for count <= 0 (including -0), without affecting the wait queue. We also
// verify that positive counts still behave correctly and the return value
// reflects the number of waiters actually woken.

(function() {
  function assertEquals(expected, actual, message) {
    if (expected !== actual) {
      throw new Error((message || "Assertion failed") + ": expected " + expected + ", got " + actual);
    }
  }
  function assertTrue(value, message) {
    if (!value) throw new Error(message || ("Assertion failed: expected true, got " + value));
  }
  function assertFalse(value, message) {
    if (value) throw new Error(message || ("Assertion failed: expected false, got " + value));
  }

  function numWaiters(cv) {
    return %AtomicsSynchronizationPrimitiveNumWaitersForTesting(cv);
  }

  // Poll until the condition variable has the expected number of waiters.
  function waitForWaiters(cv, expected, cb) {
    function poll() {
      if (numWaiters(cv) === expected) {
        cb();
      } else {
        setTimeout(poll, 0);
      }
    }
    poll();
  }

  // Start one waiter on the given mutex+cv. Returns a getter for completion state.
  function startWaiter(mutex, cv) {
    let done = false;
    const p = Atomics.Mutex.lockAsync(mutex, async () => {
      await Atomics.Condition.waitAsync(cv, mutex);
    });
    p.then(() => { done = true; });
    return () => done;
  }

  // Create n waiters on a fresh mutex+cv, and invoke cb when they are enqueued.
  function newWaiters(n, cb) {
    const mutex = new Atomics.Mutex;
    const cv = new Atomics.Condition;
    const dones = [];
    for (let i = 0; i < n; i++) {
      dones.push(startWaiter(mutex, cv));
    }
    waitForWaiters(cv, n, () => cb({mutex, cv, dones}));
  }

  // After waking, wait until no waiters remain and all waiter promises resolved.
  function drain(cv, dones, cb) {
    waitForWaiters(cv, 0, () => {
      // Allow the promise continuations to run and set done=true.
      setTimeout(() => {
        for (let i = 0; i < dones.length; i++) {
          assertTrue(dones[i](), "Waiter " + i + " should have completed");
        }
        cb();
      }, 0);
    });
  }

  const tests = [];
  function addTest(name, fn) { tests.push({name, fn}); }

  // Core scenario from the PoC: negative count is a strict no-op returning 0.
  addTest("Negative count (-14) is a no-op and returns 0", (done) => {
    newWaiters(1, ({cv, dones}) => {
      const ret = Atomics.Condition.notify(cv, -14);
      assertEquals(0, ret, "notify(cv, -14) should return 0");
      assertEquals(1, numWaiters(cv), "Waiters should be unchanged after notify(-14)");
      assertFalse(dones[0](), "Waiter should not be woken by notify(-14)");
      const ret2 = Atomics.Condition.notify(cv);
      assertEquals(1, ret2, "Default notify should wake exactly 1 waiter");
      drain(cv, dones, done);
    });
  });

  // Additional non-positive cases covered by the fix: 0, -0, NaN, -Infinity.
  function addNoopCountTest(countValue, description) {
    addTest(`Non-positive count ${description} is a no-op and returns 0`, (done) => {
      newWaiters(1, ({cv, dones}) => {
        const ret = Atomics.Condition.notify(cv, countValue);
        assertEquals(0, ret, `notify(cv, ${description}) should return 0`);
        assertEquals(1, numWaiters(cv), `Waiters should be unchanged after notify(${description})`);
        assertFalse(dones[0](), `Waiter should not be woken by notify(${description})`);
        const ret2 = Atomics.Condition.notify(cv);
        assertEquals(1, ret2, `Default notify should wake exactly 1 waiter after notify(${description})`);
        drain(cv, dones, done);
      });
    });
  }

  addNoopCountTest(0, "0");
  addNoopCountTest(-0, "-0");
  addNoopCountTest(NaN, "NaN");
  addNoopCountTest(-Infinity, "-Infinity");

  // Positive counts: with a single waiter, return value should be 1 regardless of count >= 1.
  function addPositiveCountSingleWaiter(countValue, description) {
    addTest(`Positive count ${description} with 1 waiter returns 1 and wakes 1`, (done) => {
      newWaiters(1, ({cv, dones}) => {
        const ret = Atomics.Condition.notify(cv, countValue);
        assertEquals(1, ret, `notify(cv, ${description}) should wake exactly 1 waiter`);
        drain(cv, dones, done);
      });
    });
  }

  addPositiveCountSingleWaiter(1, "1");
  addPositiveCountSingleWaiter(2, "2");
  addPositiveCountSingleWaiter(Infinity, "Infinity");

  // Two-waiter scenarios to ensure counts greater than 1 behave correctly.
  addTest("Two waiters: notify count 1 wakes exactly 1", (done) => {
    newWaiters(2, ({cv, dones}) => {
      const ret = Atomics.Condition.notify(cv, 1);
      assertEquals(1, ret, "notify(cv, 1) should wake 1 waiter");
      // After one wake, there should still be 1 waiter left.
      waitForWaiters(cv, 1, () => {
        // Let the woken promise resolve.
        setTimeout(() => {
          // Exactly one done should be true.
          const completed = dones.map(d => d()).filter(Boolean).length;
          assertEquals(1, completed, "Exactly one waiter should have completed after notify(1)");
          const ret2 = Atomics.Condition.notify(cv);
          assertEquals(1, ret2, "Second notify should wake the remaining waiter");
          drain(cv, dones, done);
        }, 0);
      });
    });
  });

  addTest("Two waiters: notify count 2 wakes both", (done) => {
    newWaiters(2, ({cv, dones}) => {
      const ret = Atomics.Condition.notify(cv, 2);
      assertEquals(2, ret, "notify(cv, 2) should wake 2 waiters");
      drain(cv, dones, done);
    });
  });

  addTest("Two waiters: non-positive counts are no-op and return 0", (done) => {
    newWaiters(2, ({cv, dones}) => {
      const ret0 = Atomics.Condition.notify(cv, 0);
      assertEquals(0, ret0, "notify(cv, 0) should return 0");
      assertEquals(2, numWaiters(cv), "notify(0) should not change waiters");
      assertFalse(dones[0]() || dones[1](), "No waiter should be woken by notify(0)");

      const retNeg0 = Atomics.Condition.notify(cv, -0);
      assertEquals(0, retNeg0, "notify(cv, -0) should return 0");
      assertEquals(2, numWaiters(cv), "notify(-0) should not change waiters");

      const retNeg = Atomics.Condition.notify(cv, -14);
      assertEquals(0, retNeg, "notify(cv, -14) should return 0");
      assertEquals(2, numWaiters(cv), "notify(-14) should not change waiters");

      const retNaN = Atomics.Condition.notify(cv, NaN);
      assertEquals(0, retNaN, "notify(cv, NaN) should return 0");
      assertEquals(2, numWaiters(cv), "notify(NaN) should not change waiters");

      // Now wake both to clean up.
      const ret2 = Atomics.Condition.notify(cv, 2);
      assertEquals(2, ret2, "notify(cv, 2) should wake the 2 waiters");
      drain(cv, dones, done);
    });
  });

  function runNext() {
    if (tests.length === 0) {
      // Final sanity: create one more waiter and ensure default notify drains it.
      newWaiters(1, ({cv, dones}) => {
        const ret = Atomics.Condition.notify(cv);
        assertEquals(1, ret, "Final default notify should wake 1 waiter");
        drain(cv, dones, () => {
          assertEquals(0, numWaiters(cv), "No stray waiters expected at end");
          print("OK");
        });
      });
      return;
    }
    const t = tests.shift();
    try {
      t.fn(() => setTimeout(runNext, 0));
    } catch (e) {
      throw e;
    }
  }

  // Kick off the test runner.
  runNext();
})();
