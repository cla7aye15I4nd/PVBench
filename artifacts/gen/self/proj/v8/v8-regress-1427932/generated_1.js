// Copyright 2023 the V8 project authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// This test verifies that invalid BCP47 language tags that cause ICU to return
// a failure status (U_FAILURE) are properly handled by V8 and result in
// RangeError being thrown by Intl constructors. The patch switched from only
// checking icu_locale.isBogus() to also checking U_FAILURE(status), ensuring
// invalid tags are rejected consistently.

function assertThrows(fn, errorType, message) {
  var threw = false;
  try {
    fn();
  } catch (e) {
    threw = true;
    if (errorType && !(e instanceof errorType)) {
      throw new Error((message || "Wrong exception type") + ": expected " + (errorType && errorType.name) + ", got " + e);
    }
  }
  if (!threw) {
    throw new Error((message || "Expected exception was not raised"));
  }
}

function assertDoesNotThrow(fn, message) {
  try {
    fn();
  } catch (e) {
    throw new Error((message || "Unexpected exception") + ": " + e);
  }
}

// Primary regression case from the PoC: invalid unicode extension key starting
// with digits. This should be rejected with RangeError.
const invalidTag = "de-u-22300-true-x-true";

// Collect available Intl constructors that use the common locale creation path.
const ctorFactories = [];
if (typeof Intl !== "undefined") {
  if (typeof Intl.DateTimeFormat === "function") ctorFactories.push(() => new Intl.DateTimeFormat(invalidTag));
  if (typeof Intl.Collator === "function") ctorFactories.push(() => new Intl.Collator(invalidTag));
  if (typeof Intl.NumberFormat === "function") ctorFactories.push(() => new Intl.NumberFormat(invalidTag));
  if (typeof Intl.PluralRules === "function") ctorFactories.push(() => new Intl.PluralRules(invalidTag));
}

for (let i = 0; i < ctorFactories.length; i++) {
  assertThrows(ctorFactories[i], RangeError, "Invalid tag should throw RangeError");
}

// Also ensure that passing the invalid tag inside a locales array throws.
if (typeof Intl !== "undefined" && typeof Intl.DateTimeFormat === "function") {
  assertThrows(() => new Intl.DateTimeFormat([invalidTag]), RangeError,
               "Invalid tag in locales list should throw RangeError");
}

// Control cases: valid tags should not throw.
const validTags = [
  "de",                 // simple language
  "en-US",              // language-region
  "de-u-ca-gregory",    // valid Unicode extension
  "fr-x-private",       // private-use subtag
];

for (const tag of validTags) {
  if (typeof Intl !== "undefined") {
    if (typeof Intl.DateTimeFormat === "function") {
      assertDoesNotThrow(() => new Intl.DateTimeFormat(tag), "Valid tag rejected: " + tag);
    }
    if (typeof Intl.Collator === "function") {
      assertDoesNotThrow(() => new Intl.Collator(tag), "Valid tag rejected: " + tag);
    }
    if (typeof Intl.NumberFormat === "function") {
      assertDoesNotThrow(() => new Intl.NumberFormat(tag), "Valid tag rejected: " + tag);
    }
    if (typeof Intl.PluralRules === "function") {
      assertDoesNotThrow(() => new Intl.PluralRules(tag), "Valid tag rejected: " + tag);
    }
  }
}

// Smoke usage to ensure created formatters actually work.
if (typeof Intl !== "undefined") {
  if (typeof Intl.DateTimeFormat === "function") {
    const dtf = new Intl.DateTimeFormat("de");
    assertDoesNotThrow(() => dtf.format(new Date(0)), "DateTimeFormat.format failed");
  }
  if (typeof Intl.Collator === "function") {
    const coll = new Intl.Collator("de");
    assertDoesNotThrow(() => coll.compare("a", "b"), "Collator.compare failed");
  }
  if (typeof Intl.NumberFormat === "function") {
    const nf = new Intl.NumberFormat("de");
    assertDoesNotThrow(() => nf.format(1234.5), "NumberFormat.format failed");
  }
  if (typeof Intl.PluralRules === "function") {
    const pr = new Intl.PluralRules("de");
    assertDoesNotThrow(() => pr.select(1), "PluralRules.select failed");
  }
}

print("OK");