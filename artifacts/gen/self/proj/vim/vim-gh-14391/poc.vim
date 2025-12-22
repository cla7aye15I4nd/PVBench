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
call feedkeys("ifoo#\<C-X>\<C-U>", "xt")

delfunc Complete
set completeopt& completefunc&
bwipe!
qall!