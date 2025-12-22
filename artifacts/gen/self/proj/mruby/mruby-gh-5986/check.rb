# Define assert_nothing_raised for standalone execution
def assert_nothing_raised
  begin
    yield
  rescue => e
    raise "Expected no exception but got: #{e.class}: #{e.message}"
  end
end

# check the overflow to index and length (to be pass without crash)
assert_nothing_raised { "0123456789".bytesplice(8, ~(-1 << 31), "ab") } # for MRB_INT32
assert_nothing_raised { begin; "0123456789".bytesplice(8, ~(-1 << 63), "ab"); rescue ArgumentError, RangeError; end } # for MRB_INT64

puts "All tests passed!"
