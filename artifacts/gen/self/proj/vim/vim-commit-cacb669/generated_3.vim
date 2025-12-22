" Test for search.c fix: update msgbuflen after replacing msgbuf when reversing text
" The patch adjusts message buffer length handling in do_search(), which is
" triggered for search messages under 'rightleft', especially when the pattern
" ends with many spaces (they become leading spaces after reversal and are
" skipped). Previously this could cause a crash. This test ensures no crash and
" correct error reporting for such patterns in both forward and backward search.

set nomore
set nowrapscan
set wrapscan
set rightleft
set nohlsearch
set shortmess&
" Ensure search messages are not overly suppressed
set shortmess-=s

" Prepare a small buffer
new
call setline(1, ['foo', 'bar', 'foo'])

function! s:Assert(cond, msg)
  if !(a:cond)
    echoerr a:msg
    cquit 1
  endif
endfunction

" Helper to run a normal search command safely and verify E486 is set for not-found
function! s:SearchExpectNotFound(cmdstr) abort
  let v:errmsg = ''
  try
    execute a:cmdstr
  catch
    echoerr 'Unexpected exception: ' . v:exception
    cquit 1
  endtry
  call s:Assert(v:errmsg =~# '^E486:', 'Expected E486, got: ' . v:errmsg)
endfunction

" 1) Forward search that wraps from bottom to top (exercise do_search path)
call cursor(3, col('$'))
let v:errmsg = ''
try
  execute "silent! normal! /foo\<CR>"
catch
  echoerr 'Unexpected error in forward wrap search: ' . v:exception
  cquit 1
endtry
call s:Assert(line('.') == 1, 'Forward wrap search did not wrap to top, line=' . line('.'))

" 2) Backward search that wraps from top to bottom
call cursor(1, 1)
let v:errmsg = ''
try
  execute "silent! normal! ?foo\<CR>"
catch
  echoerr 'Unexpected error in backward wrap search: ' . v:exception
  cquit 1
endtry
call s:Assert(line('.') == 3, 'Backward wrap search did not wrap to bottom, line=' . line('.'))

" 3) Very long pattern (not present) forward: ensure no crash and proper error set
let longpat = repeat('a', 5000)
call s:SearchExpectNotFound('silent! normal! /' . longpat . "\<CR>")

" 4) Long pattern with many escaped trailing spaces (not present) forward
let longspacepat = repeat('x', 200) . repeat('\ ', 300)
call s:SearchExpectNotFound('silent! normal! /' . longspacepat . "\<CR>")

" 5) Same long space pattern backward
call s:SearchExpectNotFound('silent! normal! ?' . longspacepat . "\<CR>")

" 6) Pattern consisting only of many spaces (escaped) forward
let onlyspaces = repeat('\ ', 400)
call s:SearchExpectNotFound('silent! normal! /' . onlyspaces . "\<CR>")

" 7) Pattern with trailing spaces right at end of line to ensure message handling
let trailspaces = 'foo' . repeat('\ ', 200)
call s:SearchExpectNotFound('silent! normal! /' . trailspaces . "\<CR>")
call s:SearchExpectNotFound('silent! normal! ?' . trailspaces . "\<CR>")

" If we reached here without crashing and with expected errors, the fix works.
qall!
