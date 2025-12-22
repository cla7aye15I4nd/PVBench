h = {}
(1..17).each{h[_1] = _1}
(1..16).each{h.delete(_1)}
h.rehash