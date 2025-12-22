// Test for heap buffer overflow in TypedArray.slice with overlapping buffers (#379)
// The vulnerability was using memcpy instead of memmove when source and
// destination buffers overlap.

function assert(actual, expected, message) {
    if (arguments.length === 1) {
        // Single argument: assert truthiness
        if (!actual) {
            throw new Error("Assertion failed: expected truthy value, got " + actual);
        }
    } else {
        // Two arguments: assert equality
        if (actual !== expected) {
            throw new Error("Assertion failed: expected " + JSON.stringify(expected) +
                          ", got " + JSON.stringify(actual) +
                          (message ? " (" + message + ")" : ""));
        }
    }
}

var buffer = new ArrayBuffer(100);
var a = new Uint8Array(buffer, 0, 4);

// Initialize with values that will show memmove behavior
// When slice copies [0,1,2,3] to offset 1, with memmove we get correct copy
a[0] = 0; a[1] = 0; a[2] = 0; a[3] = 255;

a.constructor = {
    [Symbol.species]: function (len) {
        // Return a TypedArray that overlaps with the original (offset by 1)
        return new Uint8Array(buffer, 1, len);
    },
};

// This used to cause heap-buffer-overflow due to memcpy with overlapping buffers
var b = a.slice();

// Verify both arrays share the same buffer
assert(a.buffer === b.buffer, true, "a and b should share the same buffer");

// Verify the slice operation completed correctly
// After memmove: buffer[1..4] should contain copy of original buffer[0..3]
// Original a was [0, 0, 0, 255] at buffer[0..3]
// After slice with memmove to buffer[1..4]:
// - buffer[1] = original buffer[0] = 0
// - buffer[2] = original buffer[1] = 0
// - buffer[3] = original buffer[2] = 0
// - buffer[4] = original buffer[3] = 255
// So a (buffer[0..3]) = [0, 0, 0, 255] -> after copy becomes [0, 0, 0, 0]
// And b (buffer[1..4]) = [0, 0, 0, 255]
assert(a.toString(), "0,0,0,255", "a.toString() after slice");
assert(b.toString(), "0,0,255,255", "b.toString() after slice");

print("All assertions passed: TypedArray.slice with overlapping buffers works correctly");
