# mruby test for bytesplice overflow and negative length handling
# This test is derived from a bug fixed in src/string.c where idx+len
# calculations could overflow and negative lengths were not clamped.
# The patch adds:
# - overflow checks for (idx1 + len1) and (idx2 + len2)
# - clamping len1/len2 to 0 when negative
# - early return when len2 == 0 (no modification)

# Minimal assertion helpers

def assert_nothing_raised(msg = nil)
  begin
    yield
  rescue => e
    raise (msg || "Expected no exception but got: #{e.class}: #{e.message}")
  end
end

def assert_equal(expected, actual, msg = nil)
  unless expected == actual
    raise (msg || "Expected #{expected.inspect}, got #{actual.inspect}")
  end
end

def assert_raises(*klasses)
  begin
    yield
  rescue => e
    unless klasses.any? { |k| e.is_a?(k) }
      raise "Expected #{klasses.map{|k| k.to_s}.join(' or ')}, got #{e.class}: #{e.message}"
    end
    return e
  end
  raise "Expected #{klasses.map{|k| k.to_s}.join(' or ')}, but nothing was raised"
end

# Helper to compute large values safely across MRB_INT32/MRB_INT64 builds
# Returns nil if computation itself is not supported in this build

def huge_for(bits)
  begin
    # ~(-1 << n) yields (2^n - 1) without allocating huge integers in many mruby builds
    return ~(-1 << bits)
  rescue => _
    return nil
  end
end

# 1) Overflow on len1 should be clamped to the remaining string length
#    bytesplice(8, huge, "ab") on "0123456789" should replace the tail with "ab"
#    Expected: "01234567ab"

def test_len1_overflow_clamped
  s = "0123456789".dup
  huge32 = huge_for(31)
  if huge32
    assert_nothing_raised("len1 overflow on MRB_INT32-like case should not raise") do
      s.bytesplice(8, huge32, "ab")
    end
    assert_equal "01234567ab", s, "len1 overflow should clamp deletion to end of string"
  else
    # If we cannot compute huge32, skip with a no-op assertion
    assert_nothing_raised { }
  end
end

# 2) Negative len1 should be clamped to 0 (i.e., insertion with no deletion)
#    Insert "X" at index 5 without removing anything

def test_negative_len1_clamped_to_zero
  s = "0123456789".dup
  assert_nothing_raised do
    s.bytesplice(5, -10, "X")
  end
  assert_equal "01234X56789", s, "negative len1 must be treated as 0 (pure insertion)"
end

# 3) Overflow on len2 in 5-arg form should clamp to available bytes from replacement
#    Replace 2 bytes at index 3 with replacement substring from idx2=1 to end
#    "0123456789" -> remove "34" and insert "XYZ" => "012XYZ56789"

def test_len2_overflow_clamped
  s = "0123456789".dup
  huge32 = huge_for(31)
  if huge32
    assert_nothing_raised do
      s.bytesplice(3, 2, "WXYZ", 1, huge32)
    end
    assert_equal "012XYZ56789", s, "len2 overflow should clamp to replacement length - idx2"
  else
    assert_nothing_raised { }
  end
end

# 4) Negative len2 should be clamped to 0 and the method should return the receiver without modification

def test_negative_len2_returns_unchanged
  s = "hello".dup
  ret = nil
  assert_nothing_raised do
    ret = s.bytesplice(1, 2, "abc", 0, -5)
  end
  # When len2 == 0, the implementation returns the receiver and does no modification
  assert_equal true, ret.equal?(s), "bytesplice should return self when len2 == 0"
  assert_equal "hello", s, "string should remain unchanged when len2 <= 0"
end

# 5) Explicit zero len2 should also be a no-op and return the receiver

def test_zero_len2_returns_unchanged
  s = "abcd".dup
  ret = s.bytesplice(2, 1, "zz", 0, 0)
  assert_equal true, ret.equal?(s), "bytesplice should return self when len2 == 0 (explicit)"
  assert_equal "abcd", s, "string should remain unchanged when len2 == 0"
end

# 6) Index checks remain intact: idx1 or idx2 out of bounds should raise IndexError

def test_index_checks
  # idx1 out of bounds
  assert_raises(IndexError) { "012345".dup.bytesplice(100, 1, "ab") }
  # idx2 out of bounds (greater than replacement length)
  assert_raises(IndexError) { "012345".dup.bytesplice(0, 1, "ab", 10, 1) }
end

# 7) Original PoC cases should not crash. For MRB_INT64, huge64 may be used.

def test_poc_no_crash
  # MRB_INT32-scale huge
  assert_nothing_raised { "0123456789".bytesplice(8, huge_for(31), "ab") if huge_for(31) }
  # MRB_INT64-scale huge: may raise RangeError/ArgumentError depending on build; ensure no crash
  begin
    h64 = huge_for(63)
    if h64
      "0123456789".bytesplice(8, h64, "ab")
    end
  rescue ArgumentError, RangeError
    # acceptable in some builds; the important part is that the interpreter doesn't crash
  end
end

# Run tests

test_len1_overflow_clamped

test_negative_len1_clamped_to_zero

test_len2_overflow_clamped

test_negative_len2_returns_unchanged

test_zero_len2_returns_unchanged

test_index_checks

test_poc_no_crash

puts "OK"
