# Test for mruby Hash#rehash fix in ht_rehash when size <= AR_MAX_SIZE
# The patch ensures that when a hash table (HT) shrinks to <= AR_MAX_SIZE
# and rehash is called, it converts to the array representation (AR) and
# performs ar_rehash instead of continuing with ht_rehash which could crash.
#
# This test verifies no-crash behavior and correctness across edge cases:
#  - Leaving 1 entry after previously exceeding AR_MAX_SIZE (POC scenario)
#  - Leaving exactly AR_MAX_SIZE entries (boundary case)
#  - Leaving 0 entries (empty hash case)
#  - Rehash on an already-small hash (AR path) remains correct

# Simple assertion helpers for standalone mruby execution

def assert_equal(expected, actual, msg = nil)
  unless expected == actual
    raise (msg || "Expected #{expected.inspect}, got #{actual.inspect}")
  end
end

def assert_true(cond, msg)
  raise msg unless cond
end

def assert_nil(val, msg = nil)
  unless val.nil?
    raise (msg || "Expected nil, got #{val.inspect}")
  end
end

# Utility to build a hash with mappings k => v_fn(k)

def build_hash(range, &v_fn)
  h = {}
  range.each do |i|
    h[i] = v_fn ? v_fn.call(i) : i
  end
  h
end

# Verify content: for each expected key, value matches; for some missing keys, nil

def verify_contents(h, expected_keys, &v_fn)
  expected_keys.each do |k|
    ev = v_fn ? v_fn.call(k) : k
    av = h[k]
    assert_equal(ev, av, "Value mismatch for key #{k}: expected #{ev.inspect}, got #{av.inspect}")
  end
end

# 1) POC scenario: start > AR_MAX_SIZE (17), delete to 1 entry, then rehash
# Should not crash and contents must remain correct. Also, rehash should return self.
begin
  h = build_hash(1..17) { |i| i }
  (1..16).each { |i| h.delete(i) }
  r = h.rehash
  assert_true(r.equal?(h), "rehash should return self")
  assert_equal(1, h.size, "Size should be 1 after deletions and rehash")
  assert_equal(17, h[17], "Key 17 should remain mapped to 17")
  assert_nil(h[1], "Deleted key 1 should not exist")
rescue => e
  raise "POC scenario failed: #{e.class}: #{e.message}"
end

# 2) Boundary scenario: start > AR_MAX_SIZE (17), delete one => size 16, then rehash
# Ensures conversion HT -> AR path on rehash for boundary size and data integrity.
begin
  v_fn = proc { |i| i * 2 }
  h = build_hash(1..17, &v_fn)
  h.delete(1) # size now 16 (boundary)
  h.rehash    # should not crash and should preserve contents
  assert_equal(16, h.size, "Boundary case size should be 16 after rehash")
  verify_contents(h, (2..17).to_a, &v_fn)
  assert_nil(h[1], "Deleted key 1 should not exist after rehash")
rescue => e
  raise "Boundary scenario failed: #{e.class}: #{e.message}"
end

# 3) Empty scenario: start > AR_MAX_SIZE (17), delete all => size 0, then rehash
# Ensures no-crash and empty hash remains empty after rehash.
begin
  h = build_hash(1..17) { |i| i * 3 }
  (1..17).each { |i| h.delete(i) }
  h.rehash
  assert_equal(0, h.size, "Empty case size should be 0 after rehash")
  assert_nil(h[10], "No keys should exist after deleting all and rehashing")
rescue => e
  raise "Empty scenario failed: #{e.class}: #{e.message}"
end

# 4) AR-path scenario: small hash (<= AR_MAX_SIZE) rehash should work and preserve content
begin
  v_fn = proc { |i| -i }
  h = build_hash(1..5, &v_fn)
  r = h.rehash
  assert_true(r.equal?(h), "rehash should return self for small hash as well")
  assert_equal(5, h.size, "Small hash size should remain 5 after rehash")
  verify_contents(h, (1..5).to_a, &v_fn)
rescue => e
  raise "Small hash AR scenario failed: #{e.class}: #{e.message}"
end

# 5) Idempotency: repeated rehash calls should not alter contents
begin
  h = build_hash(1..20) { |i| i + 1 }
  (2..19).each { |i| h.delete(i) } # leave keys 1 and 20 (size 2, still HT representation before rehash)
  3.times { h.rehash }
  assert_equal(2, h.size, "Size should remain 2 after repeated rehash calls")
  assert_equal(2, h[1], "Key 1 should map to 2 after repeated rehash")
  assert_equal(21, h[20], "Key 20 should map to 21 after repeated rehash")
  assert_nil(h[10], "Deleted key 10 should not exist after repeated rehash")
rescue => e
  raise "Idempotency scenario failed: #{e.class}: #{e.message}"
end

puts "OK"
