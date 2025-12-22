// Comprehensive test for QuickJS TypedArray.slice overlapping copy fix
// The patch replaces memcpy with memmove in the optimized path of
// js_typed_array_slice() so overlapping copies within the same ArrayBuffer
// are handled correctly. This test ensures overlapping cases work across
// different TypedArray element sizes and slice argument variants.

function assert(condition, message) {
    if (!condition) {
        throw new Error(message || "Assertion failed");
    }
}

function assertEq(actual, expected, message) {
    if (actual !== expected) {
        throw new Error(
            (message ? message + ": " : "") +
            "expected " + JSON.stringify(expected) + ", got " + JSON.stringify(actual)
        );
    }
}

function computeSliceRange(len, start, end) {
    // Normalize slice arguments like TypedArray.prototype.slice
    var from;
    if (start === undefined) {
        from = 0;
    } else if (start < 0) {
        from = Math.max(len + start, 0);
    } else {
        from = Math.min(start, len);
    }
    var to;
    if (end === undefined) {
        to = len;
    } else if (end < 0) {
        to = Math.max(len + end, 0);
    } else {
        to = Math.min(end, len);
    }
    if (to < from) to = from;
    return { from: from, to: to, count: to - from };
}

function fillSequential(ta, startValue) {
    startValue = startValue || 1;
    for (var i = 0; i < ta.length; i++) ta[i] = startValue + i;
}

function toArray(ta, from, to) {
    var out = [];
    for (var i = from; i < to; i++) out.push(ta[i]);
    return out;
}

function arraysEqual(a, b) {
    if (a.length !== b.length) return false;
    for (var i = 0; i < a.length; i++) if (a[i] !== b[i]) return false;
    return true;
}

// Core test helper: validates that slice copies the original source values to the
// destination view even when buffers overlap. It also ensures the result length
// and shared buffer expectations are correct.
function testOverlap(params) {
    var Type = params.Type;                    // TypedArray constructor
    var elemCount = params.elemCount;          // source TypedArray length (elements)
    var srcOffsetBytes = params.srcOffsetBytes;// byte offset of source view
    var dstOffsetBytes = params.dstOffsetBytes;// byte offset of destination view
    var sliceArgs = params.sliceArgs || [];    // arguments to slice()

    var BPE = Type.BYTES_PER_ELEMENT;

    // Compute expected slice range
    var range = computeSliceRange(elemCount, sliceArgs[0], sliceArgs[1]);

    // Buffer size must accommodate both source and destination ranges
    var neededSrc = srcOffsetBytes + elemCount * BPE;
    var neededDst = dstOffsetBytes + range.count * BPE;
    var bufSize = Math.max(neededSrc, neededDst) + 64; // slack space

    var buffer = new ArrayBuffer(bufSize);

    // Create source view and initialize
    var a = new Type(buffer, srcOffsetBytes, elemCount);
    fillSequential(a, 1);

    // Snapshot expected values BEFORE slice (important for overlap correctness)
    var expected = toArray(a, range.from, range.to);

    // Install Symbol.species to force destination to overlap within the same buffer
    a.constructor = {
        [Symbol.species]: function (len) {
            return new Type(buffer, dstOffsetBytes, len);
        },
    };

    var b;
    try {
        b = a.slice.apply(a, sliceArgs);
    } catch (e) {
        throw new Error("slice threw unexpectedly: " + e);
    }

    // Basic validations
    assertEq(b.buffer, a.buffer, "Result should share the same ArrayBuffer");
    assertEq(b.length, range.count, "Result length should match slice count");

    // Ensure the destination contains the ORIGINAL source values (memmove semantics)
    var actual = toArray(b, 0, b.length);
    assert(arraysEqual(actual, expected),
           "Destination data mismatch. Expected=" + JSON.stringify(expected) +
           ", got=" + JSON.stringify(actual));
}

// Test 1: Uint8Array forward overlap (destination starts inside source, higher address)
(function testForwardOverlapUint8() {
    var Type = Uint8Array;
    var BPE = Type.BYTES_PER_ELEMENT; // 1
    // Source at 0, destination at +1 byte, full slice
    testOverlap({
        Type: Type,
        elemCount: 16,
        srcOffsetBytes: 0,
        dstOffsetBytes: 1 * BPE,
        sliceArgs: [],
    });
})();

// Test 2: Uint8Array backward overlap (destination starts before source, lower address)
(function testBackwardOverlapUint8() {
    var Type = Uint8Array;
    var BPE = Type.BYTES_PER_ELEMENT; // 1
    // Source at +2 bytes, destination at 0, full slice
    testOverlap({
        Type: Type,
        elemCount: 16,
        srcOffsetBytes: 2 * BPE,
        dstOffsetBytes: 0,
        sliceArgs: [],
    });
})();

// Test 3: Uint16Array forward overlap with non-trivial slice range
(function testUint16WithRange() {
    var Type = Uint16Array;
    var BPE = Type.BYTES_PER_ELEMENT; // 2
    // Source at 0, destination offset by 1 element (2 bytes)
    // Slice a subrange [1, 9) to verify start/end handling on fast path
    testOverlap({
        Type: Type,
        elemCount: 12,
        srcOffsetBytes: 0,
        dstOffsetBytes: 1 * BPE,
        sliceArgs: [1, 9],
    });
})();

// Test 4: Float64Array backward overlap, full slice
(function testBackwardOverlapFloat64() {
    var Type = Float64Array;
    var BPE = Type.BYTES_PER_ELEMENT; // 8
    // Source at +16 bytes (2 elements), destination at 0
    testOverlap({
        Type: Type,
        elemCount: 8,
        srcOffsetBytes: 2 * BPE,
        dstOffsetBytes: 0,
        sliceArgs: [],
    });
})();

print("OK");