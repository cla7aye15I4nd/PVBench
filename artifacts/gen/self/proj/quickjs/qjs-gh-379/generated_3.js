// Comprehensive tests for TypedArray.prototype.slice with overlapping buffers
// Bug fixed: use memmove instead of memcpy when source and destination overlap.
// The patch changes memcpy -> memmove in js_typed_array_slice fast path.
// These tests validate content correctness and ensure no crashes in overlapping scenarios.

function assert(actual, expected, message) {
    if (arguments.length === 1) {
        if (!actual) {
            throw new Error("Assertion failed: expected truthy value, got " + actual);
        }
    } else {
        if (actual !== expected) {
            throw new Error("Assertion failed: expected " + JSON.stringify(expected) +
                            ", got " + JSON.stringify(actual) +
                            (message ? " (" + message + ")" : ""));
        }
    }
}

function toStr(ta) {
    // Stable string representation of typed array contents
    return Array.prototype.join.call(ta, ",");
}

function fillTA(ta, arr) {
    for (var i = 0; i < arr.length; i++) ta[i] = arr[i];
}

// Test 1: Forward-overlap copy (dest starts after src). Should behave like memmove backward copy.
(function testForwardOverlap() {
    var ab = new ArrayBuffer(16);
    var a = new Uint8Array(ab, 0, 4);
    fillTA(a, [1, 2, 3, 4]);

    a.constructor = {
        [Symbol.species]: function(len) {
            // Create a view overlapping by +1 byte
            return new Uint8Array(ab, 1, len);
        }
    };

    var b;
    try {
        b = a.slice();
    } catch (e) {
        throw new Error("testForwardOverlap: slice threw unexpectedly: " + e);
    }

    // Both arrays should share the same buffer due to custom species
    assert(a.buffer === b.buffer, true, "buffers should be identical");
    assert(b.length, a.length, "length should match source length");

    // After memmove from [0..3] to [1..4], buffer becomes [1,1,2,3,4]
    // So a (view [0..3]) = [1,1,2,3]
    // and b (view [1..4]) = [1,2,3,4] (copy of original a)
    assert(toStr(b), "1,2,3,4", "b contents after overlapping slice");
    assert(toStr(a), "1,1,2,3", "a mutated as per memmove semantics");
})();

// Test 2: Exact-overlap (src and dest pointers are equal). Should be a safe no-op.
(function testExactOverlap() {
    var ab = new ArrayBuffer(32);
    var a = new Uint8Array(ab, 0, 5);
    fillTA(a, [9, 8, 7, 6, 5]);

    a.constructor = {
        [Symbol.species]: function(len) {
            // When slicing from index 1, src will point at offset 1.
            // Return a view that also starts at offset 1 so src===dest.
            return new Uint8Array(ab, 1, len);
        }
    };

    var b = a.slice(1); // count = 4, src offset = 1, dest offset = 1

    assert(b.length, 4, "b length for slice(1)");
    assert(b.byteOffset, 1, "b.byteOffset should be 1");

    // Contents should remain intact
    assert(toStr(b), "8,7,6,5", "b contents after exact-overlap slice");
    assert(toStr(a), "9,8,7,6,5", "a should be unchanged in exact overlap");
})();

// Test 3: Backward-overlap copy (dest starts before src). Should behave like memmove forward copy.
(function testBackwardOverlap() {
    var ab = new ArrayBuffer(16);
    var a = new Uint8Array(ab, 1, 4); // a covers buffer[1..4]
    fillTA(a, [10, 20, 30, 40]);

    a.constructor = {
        [Symbol.species]: function(len) {
            // Return view starting earlier, so dest<src
            return new Uint8Array(ab, 0, len); // b will cover buffer[0..3]
        }
    };

    var b = a.slice(); // copy from src[1..4] to dest[0..3]

    // b should contain original a values
    assert(toStr(b), "10,20,30,40", "b contents in backward-overlap slice");

    // a should be shifted forward: [20,30,40,40]
    assert(toStr(a), "20,30,40,40", "a mutated as per forward memmove");
})();

// Test 4: Overlap with element size > 1 (Uint16Array, shift=1)
(function testUint16Overlap() {
    var ab = new ArrayBuffer(32);
    var a = new Uint16Array(ab, 0, 4);
    fillTA(a, [0x1111, 0x2222, 0x3333, 0x4444]);

    a.constructor = {
        [Symbol.species]: function(len) {
            // Overlap by one 16-bit element (2 bytes)
            return new Uint16Array(ab, 2, len);
        }
    };

    var b = a.slice();

    // b should be an exact copy of original a
    var expectedB = [0x1111, 0x2222, 0x3333, 0x4444];
    for (var i = 0; i < b.length; i++) {
        assert(b[i], expectedB[i], "Uint16 b[" + i + "]");
    }

    // a should be shifted: [0x1111, 0x1111, 0x2222, 0x3333]
    var expectedA = [0x1111, 0x1111, 0x2222, 0x3333];
    for (var i = 0; i < a.length; i++) {
        assert(a[i], expectedA[i], "Uint16 a[" + i + "] after slice");
    }
})();

// Test 5: No-crash large overlapping copy (regression safety)
(function testNoCrashLarge() {
    var ab = new ArrayBuffer(100);
    var a = new Uint8Array(ab, 0, 20);
    // Fill with a simple pattern
    for (var i = 0; i < a.length; i++) a[i] = i;

    a.constructor = {
        [Symbol.species]: function(len) {
            return new Uint8Array(ab, 1, len);
        }
    };

    try {
        var b = a.slice();
        // Quick sanity: b should equal original pattern [0..19]
        // and a should have been shifted by 1 with the last element duplicated
        for (var i = 0; i < b.length; i++) {
            assert(b[i], i, "large overlap b[" + i + "]");
        }
        assert(a[0], 0, "large overlap a[0]");
        assert(a[1], 0, "large overlap a[1]");
        assert(a[2], 1, "large overlap a[2]");
        assert(a[19], 18, "large overlap a[19]");
        // Also check the element just after a's view reflects the last value
        var tail = new Uint8Array(ab, 0, 21);
        assert(tail[20], 19, "buffer tail after memmove");
    } catch (e) {
        throw new Error("testNoCrashLarge: Unexpected error during slice: " + e.message);
    }
})();

print("OK");