" The following used to crash Vim
func Test_import_invalid_tuple()
  let lines =<< trim END
    imp(",G0}11*f[+\x","#|
  END
  new
  call setline(1, lines)
  call assert_fails('source', 'E114: Missing double quote: "#|')
  bw!
endfunc

