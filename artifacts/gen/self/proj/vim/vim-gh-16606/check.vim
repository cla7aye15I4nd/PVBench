" Test for heap buffer overflow when --log option is used with non-existent
" file before buffers are allocated (#16606)
" The vulnerability was that common_init_1() was not called before processing
" --log option, leading to accessing uninitialized IObuff.
func Test_log_nonexistent()
  " Run vim with --log pointing to non-existent directory
  " This used to crash Vim before the fix
  let result = system(v:progpath .. ' --log /nonexistent/Xlogfile -c qa! 2>&1')
  " Should get an error about not being able to open the file, not a crash
  call assert_match("Can't open file", result)
endfunc
