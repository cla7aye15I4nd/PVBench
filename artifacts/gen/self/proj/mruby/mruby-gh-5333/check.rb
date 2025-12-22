# Define assert_equal for standalone execution
def assert_equal(expected, actual)
  unless expected == actual
    raise "Expected #{expected.inspect} but got #{actual.inspect}"
  end
end

h = {}
(1..17).each{h[_1] = _1 * 2}
(2..16).each{h.delete(_1)}
h.rehash
assert_equal([[1, 2], [17, 34]], h.to_a)
assert_equal(2, h.size)
[1, 17].each{assert_equal(_1 * 2, h[_1])}

puts "All tests passed!"
