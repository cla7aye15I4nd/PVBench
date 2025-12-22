func Test_xxd_buffer_overflow()
  CheckUnix
  new
  let input = repeat('A', 256)
  call writefile(['-9223372036854775808: ' . repeat("\e[1;32m41\e[0m ", 256) . ' ' . repeat("\e[1;32mA\e[0m", 256)], 'Xxdexpected', 'D')
  exe 'r! printf ' . input . '| ' . s:xxd_cmd . ' -Ralways -g1 -c256 -d -o 9223372036854775808 > Xxdout'
  call assert_equalfile('Xxdexpected', 'Xxdout')
  call delete('Xxdout')
  bwipe!
endfunc