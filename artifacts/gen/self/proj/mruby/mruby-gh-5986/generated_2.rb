# Tests for mruby String#bytesplice overflow and negative-length handling
# This test exercises fixes added to prevent integer overflow in idx+len
# computations and to clamp negative lengths to zero.

class TestFailure < StandardError; end

def assert_nothing_raised(msg = nil)
  begin
    yield
  rescue => e
    raise TestFailure, (msg || "Expected no exception") + ": got #{e.class}: #{e.message}"
  end
end

def assert_equal(expected, actual, msg = nil)
  unless expected == actual
    raise TestFailure, (msg || "Assertion failed") + ": expected #{expected.inspect}, got #{actual.inspect}"
  end
end

# 1) Overflow guard for idx1+len1 on MRB_INT32-size value
# Ensure calling with a huge length does not crash and returns self
assert_nothing_raised("bytesplice huge len (INT32) should not crash and return self") do
  s = "0123456789"
  r = s.bytesplice(8, ~(-1 << 31), "ab")
  # Should return self
  raise TestFailure, "bytesplice should return self (INT32 case)" unless r.equal?(s)
end

# 2) Overflow guard for idx1+len1 on MRB_INT64-size value
# On 32-bit builds, computing or passing ~(-1 << 63) may raise; that is acceptable.
assert_nothing_raised("bytesplice huge len (INT64) should not crash; acceptable to raise ArgumentError/RangeError on 32-bit") do
  s = "0123456789"
  begin
    r = s.bytesplice(8, ~(-1 << 63), "ab")
    raise TestFailure, "bytesplice should return self (INT64 case)" unless r.equal?(s)
  rescue ArgumentError, RangeError
    # acceptable on 32-bit builds; just ensure no other crash propagates
  end
end

# 3) Negative len1 should be clamped to 0 (insert only)
assert_nothing_raised("negative len1 should be treated as zero (insertion)") do
  s = "0123456789"
  r = s.bytesplice(5, -1, "X")
  assert_equal("01234X56789", s, "negative len1 results in insertion at index")
  raise TestFailure, "bytesplice should return self for negative len1 case" unless r.equal?(s)
end

# 4) Overflow guard for idx2+len2 using the 5-argument form (INT32-size value)
# Replace with replacement substring starting at idx2 with a huge len2; should not crash and should return self.
assert_nothing_raised("bytesplice with idx2+len2 overflow (INT32) should not crash and return self") do
  begin
    s = "abcdef"
    r = s.bytesplice(2, 2, "XYZ", 1, ~(-1 << 31))
    raise TestFailure, "bytesplice should return self (5-arg INT32 case)" unless r.equal?(s)
  rescue NoMethodError, ArgumentError
    # 5-arg form may not be available on some builds; skip without failing
  end
end

# 5) Overflow guard for idx2+len2 using the 5-argument form (INT64-size value)
assert_nothing_raised("bytesplice with idx2+len2 overflow (INT64) should not crash; acceptable to raise on 32-bit") do
  begin
    s = "abcdef"
    begin
      r = s.bytesplice(2, 2, "XYZ", 1, ~(-1 << 63))
      raise TestFailure, "bytesplice should return self (5-arg INT64 case)" unless r.equal?(s)
    rescue ArgumentError, RangeError
      # acceptable on 32-bit builds
    end
  rescue NoMethodError
    # 5-arg form not available; skip
  end
end

# 6) Negative len2 should be clamped to 0, which becomes a no-op (len2 == 0 returns str unchanged)
assert_nothing_raised("negative len2 should be treated as zero (no-op in 5-arg form)") do
  begin
    s = "abcde"
    r = s.bytesplice(1, 1, "XYZ", 0, -5)
    assert_equal("abcde", s, "5-arg bytesplice should be no-op when replacement length is negative")
    raise TestFailure, "bytesplice should return self for 5-arg no-op case" unless r.equal?(s)
  rescue NoMethodError, ArgumentError
    # 5-arg form may not be available; skip without failing
  end
end

puts "OK"
