// Copyright 2023 the V8 project authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// This test verifies that syntax error messages for unexpected identifiers are
// properly formatted. The patch added MessageTemplate::kUnexpectedTokenIdentifier
// to the list of templates that MessageFormatter::TryFormat can handle, ensuring
// the engine produces a specific, formatted message instead of a generic one.

function assertThrows(fn, errorType, expectedMessage) {
  let threw = false;
  try {
    fn();
  } catch (e) {
    threw = true;
    if (errorType && !(e instanceof errorType)) {
      throw new Error("Wrong exception type: expected " + (errorType && errorType.name) + ", got " + (e && e.constructor && e.constructor.name));
    }
    if (expectedMessage !== undefined) {
      const actual = String(e && e.message);
      if (actual !== expectedMessage) {
        throw new Error("Unexpected message: expected '" + expectedMessage + "', got '" + actual + "'");
      }
    }
  }
  if (!threw) throw new Error("Expected exception was not raised");
}

// Original PoC: eval('A interface') should throw a SyntaxError with a
// specifically formatted message. Prior to the fix, the message formatting
// could be incorrect; after the fix it should match exactly.
assertThrows(
  () => eval('A interface'), SyntaxError,
  "Unexpected identifier 'undefined'"
);

// Additional sanity: ensure that the error still occurs outside of eval when
// parsed by the Function constructor, and that the message formatting matches
// the same template.
assertThrows(
  () => Function('A interface'), SyntaxError,
  "Unexpected identifier 'undefined'"
);

print("OK");
