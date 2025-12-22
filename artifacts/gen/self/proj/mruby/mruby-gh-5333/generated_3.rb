# This test verifies a fix in mruby's Hash rehash logic.
# The patch ensures that when a hash using the table (ht) representation
# shrinks to <= AR_MAX_SIZE entries, calling `rehash` converts it back to
# the array (ar) representation and avoids invalid ib_bit calculations.
#
# We create hashes that grow beyond AR_MAX_SIZE (e.g., 17 entries), then
# shrink to <= AR_MAX_SIZE and call `rehash`. The test asserts:
#  - No crash occurs
#  - Contents (size, keys, values, order) are preserved

# Simple assertion helpers
class TestFailure < StandardError; end

def assert_equal(expected, actual, msg=nil)
  unless expected == actual
    raise TestFailure, (msg || "Expected #{expected.inspect} but got #{actual.inspect}")
  end
end

# Build expected array of [k, v] pairs in order
def expected_pairs(range)
  a = []
  for i in range
    a << yield(i)
  end
  a
end

# Test 1: Direct POC — shrink to 1 entry then rehash. Should not crash and content preserved.
def test_poc_single_entry
  h = {}
  for i in 1..17
    h[i] = i
  end
  for i in 1..16
    h.delete(i)
  end

  begin
    h.rehash
  rescue => e
    raise TestFailure, "Unexpected error in poc rehash: #{e.class}: #{e.message}"
  end

  assert_equal(1, h.size, "poc: size should be 1 after rehash")
  assert_equal(17, h[17], "poc: value for key 17 should be 17")
  assert_equal([[17, 17]], h.to_a, "poc: to_a should contain only [17, 17]")
end

# Test 2: Leave two entries (1 and 17) to ensure order and values are intact after rehash.
def test_two_entries_order_and_values
  h = {}
  for i in 1..17
    h[i] = i * 2
  end
  for i in 2..16
    h.delete(i)
  end

  begin
    h.rehash
  rescue => e
    raise TestFailure, "Unexpected error with two-entries rehash: #{e.class}: #{e.message}"
  end

  assert_equal(2, h.size, "two-entries: size should be 2 after rehash")
  assert_equal(2, h[1], "two-entries: value for key 1 should be 2")
  assert_equal(34, h[17], "two-entries: value for key 17 should be 34")
  assert_equal([[1, 2], [17, 34]], h.to_a, "two-entries: order/content should be [[1,2],[17,34]]")
end

# Test 3: Boundary case — shrink from >AR_MAX_SIZE to exactly AR_MAX_SIZE (likely 16), then rehash.
# Ensures conversion back to array representation path works and preserves order/values.
def test_boundary_exact_16
  h = {}
  for i in 1..17
    h[i] = i * i
  end
  # Remove one entry to leave exactly 16
  h.delete(17)

  begin
    h.rehash
  rescue => e
    raise TestFailure, "Unexpected error at boundary 16 rehash: #{e.class}: #{e.message}"
  end

  assert_equal(16, h.size, "boundary-16: size should be 16 after rehash")

  for i in 1..16
    assert_equal(i*i, h[i], "boundary-16: value for key #{i} should be #{i*i}")
  end

  expected = []
  for i in 1..16
    expected << [i, i*i]
  end
  assert_equal(expected, h.to_a, "boundary-16: insertion order should be preserved for 1..16")
end

# Test 4: Call rehash twice after shrinking from ht to ar representation; should remain stable and not crash.
def test_multiple_rehash_idempotent
  h = {}
  for i in 1..20
    h[i] = -i
  end
  # Leave only two keys to ensure size <= AR_MAX_SIZE
  for i in 3..20
    h.delete(i)
  end

  begin
    h.rehash
    h.rehash
  rescue => e
    raise TestFailure, "Unexpected error on multiple rehash: #{e.class}: #{e.message}"
  end

  assert_equal(2, h.size, "multi-rehash: size should be 2")
  assert_equal(-1, h[1], "multi-rehash: value for key 1 should be -1")
  assert_equal(-2, h[2], "multi-rehash: value for key 2 should be -2")
  assert_equal([[1, -1], [2, -2]], h.to_a, "multi-rehash: order/content should be [[1,-1],[2,-2]]")
end

# Run tests
begin
  test_poc_single_entry
  test_two_entries_order_and_values
  test_boundary_exact_16
  test_multiple_rehash_idempotent
rescue TestFailure => tf
  raise tf
rescue => e
  raise TestFailure, "Unexpected error: #{e.class}: #{e.message}"
end

puts "OK"
