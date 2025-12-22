func Test_completefunc_first_call_complete_add()
  new

  func Complete(findstart, base) abort
    if a:findstart
      let col = col('.')
      call complete_add('#')
      return col - 1
    else
      return []
    endif
  endfunc

  set completeopt=longest completefunc=Complete
  " This used to cause heap-buffer-overflow
  call assert_fails('call feedkeys("ifoo#\<C-X>\<C-U>", "xt")', 'E840:')

  delfunc Complete
  set completeopt& completefunc&
  bwipe!
endfunc

