" Test for heap buffer overflow when accessing outside of a line end in visual
" mode with virtualedit=all (GHSA-5rgf-26wj-48v8)
func Test_visual_pos_buffer_heap_overflow()
  set virtualedit=all
  args Xa Xb
  all
  call setline(1, ['', '', ''])
  call cursor(3, 1)
  wincmd w
  call setline(1, 'foobar')
  normal! $lv0
  all
  call setreg('"', 'baz')
  " This used to cause heap-buffer-overflow
  normal! [P
  " If we reach here without crash, the fix is working
  call assert_true(1)
  set virtualedit=
  bw! Xa Xb
endfunc
