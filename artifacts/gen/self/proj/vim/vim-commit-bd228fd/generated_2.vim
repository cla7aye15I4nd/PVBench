" Test for help argument overflow handling and special pattern escaping
" Runs in Ex mode. Verifies that long help topics do not crash and errors are sane.

set nocp nomore

func! s:CloseHelpBuffers()
  for l:bn in range(1, bufnr('$'))
    if bufexists(l:bn) && getbufvar(l:bn, '&buftype') ==# 'help'
      silent! execute 'bwipeout!' l:bn
    endif
  endfor
endfunc

func! s:TryHelp(topic) abort
  " Execute :help on a topic and ensure no crash. If it errors, it should be E149.
  try
    execute 'help ' . a:topic
  catch
    if match(v:exception, 'E149:') < 0
      echoerr 'Unexpected error for topic: ' . a:topic . ' -> ' . v:exception
      cquit 1
    endif
  endtry
  call s:CloseHelpBuffers()
endfunc

" 1) Original PoC: very long topic starting with \% ... should not crash
call s:TryHelp('\%' . repeat('0', 1021))

" 2) Even longer to ensure snprintf bounding works well beyond IOSIZE
call s:TryHelp('\%' . repeat('0', 5000))

" 3) Exercise other special prefixes handled by the code path: '_', 'z', '@'
"    Append long tails so arg[2] is not NUL and length is excessive
call s:TryHelp('\_' . repeat('x', 3000))
call s:TryHelp('\z' . repeat('z', 3000))
call s:TryHelp('\@=' . repeat('y', 3000))

" 4) Specific edge: ensure \\_$ is treated as literal $ ("/\\_$" -> "/\\_\\$")
"    Use a non-existent extension to avoid opening help; just ensure no crash
call s:TryHelp('\_$X')

qall!
