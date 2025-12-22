# Generated test for mruby String#bytesplice fix (overflow and negative length handling)
# This test validates behaviors introduced in the patch to str_bytesplice (string.c):
# - Guard against integer overflow in idx+len calculations (both for source and replacement)
# - Treat negative lengths (len1/len2) as zero instead of causing undefined behavior
# - Ensure no crashes for extremely large lengths on both MRB_INT32 and MRB_INT64 builds

# Minimal assertion helpers compatible with mruby

def assert_equal(expected, actual, msg=nil)
  unless expected == actual
    raise (msg || "Expected #{expected.inspect}, got #{actual.inspect}")
  end
end

# For code that must not crash. Some builds may raise ArgumentError/RangeError for
# integers that don't fit into mrb_int; those are acceptable and should not fail the test.

def assert_nocrash_allow_range(label)
  begin
    yield
  rescue ArgumentError, RangeError
    # acceptable for builds where the integer cannot be represented
  rescue => e
    raise "#{label}: Unexpected error: #{e.class}: #{e.message}"
  end
end

# 1) Overflow tests for deletion length (len1)
# These must not crash. The actual content may vary if the integer does not
# fit in mrb_int on the target, so we only check for non-crash semantics.

# MRB_INT32 path (large positive length)
assert_nocrash_allow_range("INT32 overflow len1 should not crash") do
  "0123456789".dup.bytesplice(8, ~(-1 << 31), "ab")
end

# MRB_INT64 path (very large positive length). On 32-bit builds this may raise.
assert_nocrash_allow_range("INT64 overflow len1 should not crash") do
  "0123456789".dup.bytesplice(8, ~(-1 << 63), "ab")
end

# 2) Negative deletion length (len1) should be treated as zero: insertion only
begin
  s = "0123456789"
  s.bytesplice(3, -5, "ab")
  # Expect insertion at index 3 without deleting existing bytes
  assert_equal("012ab3456789", s, "negative len1 should act as zero (insertion only)")
rescue => e
  raise "negative len1 insertion test failed: #{e.class}: #{e.message}"
end

# Also verify with a large negative length near the end of the string
begin
  s = "0123456789"
  s.bytesplice(8, -999999999, "ab")
  assert_equal("01234567ab89", s, "large negative len1 should act as zero (insertion only)")
rescue => e
  raise "large negative len1 insertion test failed: #{e.class}: #{e.message}"
end

# 3) Negative replacement length (len2) should be treated as zero.
# The internal function returns early when len2 == 0, so the string should remain unchanged.
# Not all builds may support the 5-argument form; treat ArgumentError/RangeError as acceptable.
assert_nocrash_allow_range("negative len2 should be treated as zero and leave string unchanged") do
  s = "012345"
  begin
    s.bytesplice(2, 2, "ABCD", 1, -10)
    assert_equal("012345", s, "len2 < 0 should act as zero; string should be unchanged")
  rescue ArgumentError, RangeError
    # acceptable if this arity is unsupported or value cannot be represented
  end
end

# 4) Overflow tests for replacement length (len2) should not crash.
assert_nocrash_allow_range("INT32 overflow len2 should not crash") do
  s = "012345"
  s.bytesplice(2, 1, "AB", 0, ~(-1 << 31))
end

assert_nocrash_allow_range("INT64 overflow len2 should not crash") do
  s = "012345"
  s.bytesplice(2, 1, "AB", 0, ~(-1 << 63))
end

puts "OK"
