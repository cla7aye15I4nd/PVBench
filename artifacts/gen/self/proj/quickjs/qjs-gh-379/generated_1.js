// Comprehensive tests for TypedArray.prototype.slice overlapping copy fix (memcpy -> memmove)
// The patch replaces memcpy with memmove in the optimized slice path when the
// constructor species returns a TypedArray that aliases the same ArrayBuffer and
// the source/destination ranges overlap. These tests verify correctness and that
// no crash occurs, across several overlap patterns and element sizes.

function assert() {
    if (arguments.length === 1) {
        if (!arguments[0]) throw new Error("Assertion failed: expected truthy value");
        return;
    }
    var actual = arguments[0];
    var expected = arguments[1];
    var message = arguments[2] || "";
    if (actual !== expected) {
        throw new Error("Assertion failed: expected " + JSON.stringify(expected) + ", got " + JSON.stringify(actual) + (message ? " (" + message + ")" : ""));
    }
}

function assertArrayEq(a, expected, label) {
    var got = Array.prototype.join.call(a, ',');
    var exp = expected.join(',');
    if (got !== exp) {
        throw new Error("Array mismatch" + (label ? " [" + label + "]" : "") + ": expected [" + exp + "], got [" + got + "]");
    }
}

function resetValues(ta, values) {
    for (var i = 0; i < values.length; i++) ta[i] = values[i];
}

// Test 1: Forward overlapping copy on Uint8Array with full slice
// Source at offset 0, destination (species) at offset +1 element. This used to
// trigger undefined behavior with memcpy; with memmove, it must work and produce
// correct results.
(function testForwardOverlapUint8() {
    var buffer = new ArrayBuffer(16);
    var a = new Uint8Array(buffer, 0, 4);
    resetValues(a, [0, 0, 0, 255]);

    a.constructor = {
        [Symbol.species]: function (len) {
            // Overlap forward by 1 element
            return new Uint8Array(buffer, 1, len);
        }
    };

    var b;
    try {
        b = a.slice();
    } catch (e) {
        throw new Error("Unexpected error during forward overlap slice: " + e);
    }

    assert(a.buffer === b.buffer, true, "Buffers should be identical (aliased)");
    // After memmove backward copy: buffer[1..4] = original buffer[0..3]
    // a (0..3) becomes [0,0,0,0]; b (1..4) becomes [0,0,0,255]
    assertArrayEq(a, [0, 0, 0, 0], "forward overlap a after slice");
    assertArrayEq(b, [0, 0, 0, 255], "forward overlap b after slice");
})();

// Test 2: Backward overlapping copy on Uint8Array
// Source at offset 1, destination species at offset 0 (dest before src).
(function testBackwardOverlapUint8() {
    var buffer = new ArrayBuffer(16);
    // Initialize a at positions 1..4
    var a = new Uint8Array(buffer, 1, 4);
    resetValues(a, [5, 6, 7, 8]);

    a.constructor = {
        [Symbol.species]: function (len) {
            // Destination before source, overlapping by 1 element
            return new Uint8Array(buffer, 0, len);
        }
    };

    var b;
    try {
        b = a.slice();
    } catch (e) {
        throw new Error("Unexpected error during backward overlap slice: " + e);
    }

    assert(a.buffer === b.buffer, true, "Buffers should be identical (aliased)");
    // After memmove forward copy: dest[0..3] = original src[1..4] = [5,6,7,8]
    // a view (1..4) becomes [6,7,8,8]
    assertArrayEq(b, [5, 6, 7, 8], "backward overlap b after slice");
    assertArrayEq(a, [6, 7, 8, 8], "backward overlap a after slice");
})();

// Test 3: Overlap with non-zero start/end on Uint8Array
(function testOverlapWithStartUint8() {
    var buffer = new ArrayBuffer(16);
    var a = new Uint8Array(buffer, 0, 6);
    resetValues(a, [10, 20, 30, 40, 50, 60]);

    a.constructor = {
        [Symbol.species]: function (len) {
            // Destination starts at offset 2, will overlap with src start=1
            return new Uint8Array(buffer, 2, len);
        }
    };

    var b;
    try {
        b = a.slice(1, 5); // count = 4, src region: [20,30,40,50]
    } catch (e) {
        throw new Error("Unexpected error during overlap with start slice: " + e);
    }

    assert(a.buffer === b.buffer, true);
    assertArrayEq(b, [20, 30, 40, 50], "slice result");
    // After copy, buffer should be [10,20,20,30,40,50]
    assertArrayEq(a, [10, 20, 20, 30, 40, 50], "source view after overlapping slice");
})();

// Test 4: Forward overlapping copy on Uint16Array (element size > 1)
(function testForwardOverlapUint16() {
    var buffer = new ArrayBuffer(32);
    var a = new Uint16Array(buffer, 0, 4);
    resetValues(a, [100, 200, 300, 400]);

    a.constructor = {
        [Symbol.species]: function (len) {
            // Overlap forward by 1 element (byteOffset = 2)
            return new Uint16Array(buffer, 2, len);
        }
    };

    var b;
    try {
        b = a.slice();
    } catch (e) {
        throw new Error("Unexpected error during Uint16 forward overlap slice: " + e);
    }

    assert(a.buffer === b.buffer, true);
    assertArrayEq(b, [100, 200, 300, 400], "Uint16 slice result");
    assertArrayEq(a, [100, 100, 200, 300], "Uint16 source after overlapping slice");
})();

// Test 5: Overlap with non-zero start on Uint16Array
(function testStartUint16() {
    var buffer = new ArrayBuffer(32);
    var a = new Uint16Array(buffer, 0, 6);
    resetValues(a, [1, 2, 3, 4, 5, 6]);

    a.constructor = {
        [Symbol.species]: function (len) {
            // Destination starts at +2 elements (byteOffset = 4)
            return new Uint16Array(buffer, 4, len);
        }
    };

    var b;
    try {
        b = a.slice(1, 5); // src elements [2,3,4,5]
    } catch (e) {
        throw new Error("Unexpected error during Uint16 overlap with start slice: " + e);
    }

    assert(a.buffer === b.buffer, true);
    assertArrayEq(b, [2, 3, 4, 5], "Uint16 slice result with start");
    // After memmove, a becomes [1,2,2,3,4,5]
    assertArrayEq(a, [1, 2, 2, 3, 4, 5], "Uint16 source after overlapping slice with start");
})();

print("OK");
