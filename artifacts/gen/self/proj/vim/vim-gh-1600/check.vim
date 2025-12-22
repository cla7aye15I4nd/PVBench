" Test for heap buffer overflow with very long filename in completion (#1600)
" The vulnerability was in displaying the "match in file" message when the
" filename was very long.
func Test_edit_complete_very_long_name()
  let save_columns = &columns
  set columns=5000
  call assert_equal(5000, &columns)
  set noswapfile
  let dirname = getcwd() . "/Xdir"
  let longdirname = dirname . repeat('/' . repeat('d', 255), 4)
  let longfilename = longdirname . '/' . repeat('a', 255)
  call mkdir(longdirname, 'p')
  call writefile(['Totum', 'Table'], longfilename)
  new
  exe "next Xfile " . longfilename
  " This used to cause heap-buffer-overflow when displaying filename
  exe "normal iT\<C-N>"
  " If we reach here without crash, the fix is working
  call assert_true(1)

  bwipe!
  exe 'bwipe! ' . longfilename
  call delete(dirname, 'rf')
  let &columns = save_columns
  set swapfile&
endfunc
