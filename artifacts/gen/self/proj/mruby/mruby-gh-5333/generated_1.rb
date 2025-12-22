# mruby test for Hash#rehash fix when hash shrinks below AR_MAX_SIZE
# The patch ensures that when a hash in table-representation (ht) shrinks to
# AR_MAX_SIZE or less, ht_rehash converts it to array-representation (ar)
# before rehashing, preventing invalid ib_bit calculations and crashes.

# Simple assertion helpers (mruby-friendly)
def assert_equal(expected, actual, msg=nil)
  unless expected == actual
    raise (msg || "Expected #{expected.inspect}, got #{actual.inspect}")
  end
end

def assert(cond, msg)
  raise msg unless cond
end

# 1) Rehash after shrinking from >AR_MAX_SIZE (17) down to 1 element
#    This used to crash. Now it must not crash and must preserve content.
begin
  h = {}
  (1..17).each { |i| h[i] = i }
  (1..16).each { |i| h.delete(i) }
  # Only key 17 remains
  begin
    h.rehash
  rescue => e
    raise "Unexpected error during rehash after shrink to 1: #{e.class}: #{e.message}"
  end
  assert_equal(1, h.size, "Hash size should be 1 after rehash")
  assert_equal(17, h[17], "Key 17 should be preserved after rehash")
  (1..16).each { |i| assert(h[i].nil?, "Key #{i} should be absent after rehash") }
end

# 2) Rehash after shrinking from >AR_MAX_SIZE down to exactly 2 elements
#    Ensure both entries are intact and no crash occurs.
begin
  h = {}
  (1..17).each { |i| h[i] = i * 2 }
  (2..16).each { |i| h.delete(i) }
  # Keys 1 and 17 remain
  begin
    h.rehash
  rescue => e
    raise "Unexpected error during rehash with 2 elements: #{e.class}: #{e.message}"
  end
  assert_equal(2, h.size, "Hash size should be 2 after rehash")
  assert_equal(2,  h[1],  "Value for key 1 incorrect after rehash")
  assert_equal(34, h[17], "Value for key 17 incorrect after rehash")
  ks = h.keys
  assert(ks.include?(1),  "Keys should include 1 after rehash")
  assert(ks.include?(17), "Keys should include 17 after rehash")
  assert_equal(2, ks.size, "Keys array should have exactly 2 entries after rehash")
end

# 3) Rehash after shrinking from >AR_MAX_SIZE down to exactly AR_MAX_SIZE elements
#    Start with 17, delete one (17), leaving 16. Must not crash and preserve all entries.
begin
  h = {}
  (1..17).each { |i| h[i] = i }
  h.delete(17)
  begin
    h.rehash
  rescue => e
    raise "Unexpected error during rehash with 16 elements: #{e.class}: #{e.message}"
  end
  assert_equal(16, h.size, "Hash size should be 16 after rehash")
  (1..16).each { |i| assert_equal(i, h[i], "Key #{i} missing or wrong after rehash") }
end

# 4) Rehash after deleting all entries (size becomes 0) from a previously large hash
#    Must not crash; result should be an empty hash.
begin
  h = {}
  (1..17).each { |i| h[i] = i }
  (1..17).each { |i| h.delete(i) }
  begin
    h.rehash
  rescue => e
    raise "Unexpected error during rehash on empty hash: #{e.class}: #{e.message}"
  end
  assert_equal(0, h.size, "Empty hash should remain empty after rehash")
  assert_equal([], h.keys, "Empty hash should have no keys after rehash")
end

# 5) Rehash stability and further mutations after a shrink-triggered rehash
#    After shrinking to 1 and rehashing, add a couple of entries and rehash again.
begin
  h = {}
  (1..17).each { |i| h[i] = i }
  (1..16).each { |i| h.delete(i) }
  h.rehash  # first rehash at size 1

  # Add more entries; ensure operations remain stable
  h[18] = 180
  h[1]  = 10
  begin
    h.rehash  # second rehash at size 3
  rescue => e
    raise "Unexpected error during second rehash with 3 elements: #{e.class}: #{e.message}"
  end
  assert_equal(3, h.size, "Hash size should be 3 after second rehash")
  assert_equal(17, h[17], "Key 17 value incorrect after second rehash")
  assert_equal(180, h[18], "Key 18 value incorrect after second rehash")
  assert_equal(10, h[1],  "Key 1 value incorrect after second rehash")
end

puts "OK"
