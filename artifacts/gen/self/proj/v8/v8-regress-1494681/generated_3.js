// Copyright 2023 the V8 project authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// This test verifies that MessageFormatter can correctly format
// kUnexpectedTokenIdentifier errors (added in the patch), ensuring
// the thrown SyntaxError messages are properly produced instead of
// generic or misformatted messages.

function assertEquals(actual, expected, message) {
  if (actual !== expected) {
    throw new Error((message || "Assertion failed") + ": expected " + expected + ", got " + actual);
  }
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
    if (typeof expectedMessage !== 'undefined') {
      assertEquals(e.message, expectedMessage, 'Wrong exception message');
    }
  }
  if (!threw) throw new Error("Expected exception was not raised");
}

// Original PoC scenario: two tokens without an operator in between.
// According to the patch, this should be formatted using
// kUnexpectedTokenIdentifier, which (in this particular case) results
// in the identifier name being unavailable and printed as 'undefined'.
assertThrows(
  () => eval('A interface'), SyntaxError,
  "Unexpected identifier 'undefined'"
);

// Additional edge case: use a regular identifier as the unexpected token
// to ensure the identifier name is included in the message.
assertThrows(
  () => eval('A B'), SyntaxError,
  "Unexpected identifier 'B'"
);

// The same check, but through the Function constructor to ensure that
// compilation paths other than direct eval also format the message correctly.
assertThrows(
  () => Function('A B'), SyntaxError,
  "Unexpected identifier 'B'"
);

print('OK');
