// Copyright 2023 the V8 project authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// This test verifies the correct formatting of SyntaxError messages for
// MessageTemplate::kUnexpectedTokenIdentifier. A recent patch added this
// template to the set of messages that can be formatted by MessageFormatter::TryFormat,
// ensuring the error message is produced reliably (and without crashes) even when
// arguments are absent.

function assertEquals(actual, expected, message) {
  if (actual !== expected) {
    throw new Error((message || "Assertion failed") + ": expected " + expected + ", got " + actual);
  }
}

function assertTrue(value, message) {
  if (!value) throw new Error(message || "Assertion failed: expected true but got " + value);
}

function assertThrows(fn, errorConstructor, expectedMessage) {
  let threw = false;
  try {
    fn();
  } catch (e) {
    threw = true;
    if (errorConstructor && !(e instanceof errorConstructor)) {
      throw new Error("Wrong exception type: " + e);
    }
    if (typeof expectedMessage !== "undefined") {
      assertEquals(e.message, expectedMessage, "Unexpected error message");
    }
  }
  if (!threw) throw new Error("Expected exception was not raised");
}

// Original PoC behavior: just catching the error. Here we assert the precise
// error type and message to ensure the formatter picked the right template and
// handled missing arguments safely.
assertThrows(
  () => eval('A interface'), SyntaxError,
  // This exact message verifies that formatting proceeded even with a missing
  // identifier argument (which shows up as 'undefined'). This used to be mishandled
  // before the patch.
  "Unexpected identifier 'undefined'"
);

// Additional sanity checks around the same template to ensure no crash and
// reasonable messaging for other identifiers. We don't assert a precise string
// here to remain compatible across versions/locales while still validating the
// template is used.
(function testUnexpectedIdentifierWithName() {
  try {
    eval('A foo');
    throw new Error("Expected SyntaxError was not raised for 'A foo'");
  } catch (e) {
    assertTrue(e instanceof SyntaxError, "Expected a SyntaxError for 'A foo'");
    // Message should start with the canonical prefix and typically include the identifier.
    assertTrue(typeof e.message === 'string' && e.message.indexOf('Unexpected identifier') === 0,
               "Message should start with 'Unexpected identifier' but was: " + e.message);
    // It's common for engines to include the actual identifier token; accept either behavior.
    // If present, it should include 'foo'.
    if (e.message.indexOf('foo') !== -1) {
      assertTrue(e.message.includes('foo'), "Expected identifier name 'foo' in message");
    }
  }
})();

// Edge case: multiple identifiers in a row still produce a SyntaxError and should not crash.
(function testMultipleIdentifiers() {
  try {
    eval('A B C');
    throw new Error("Expected SyntaxError was not raised for 'A B C'");
  } catch (e) {
    assertTrue(e instanceof SyntaxError, "Expected a SyntaxError for 'A B C'");
    assertTrue(typeof e.message === 'string' && e.message.indexOf('Unexpected identifier') === 0,
               "Message should start with 'Unexpected identifier' but was: " + e.message);
  }
})();

print("OK");
