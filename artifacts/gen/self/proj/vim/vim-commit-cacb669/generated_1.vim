" Test for patch that updates msgbuflen after adjusting msgbuf in do_search()
" The bug manifested when reversing messages for 'rightleft' windows, e.g.
" during search wrap or not-found messages. The pointer to the reversed text
" was moved past leading spaces, but the corresponding length was not updated,
" which could lead to reading past NUL and crash. This test exercises those
" code paths under 'rightleft' to ensure no crash and correct search results.

set nomore
set shortmess=
set wrapscan
set rightleft

" Prepare a simple buffer
enew!
call setline(1, ['foo', 'bar', 'foo'])

" 1) Forward search that wraps (from last line to first) under 'rightleft'.
try
  normal! G0
  execute "normal! /foo\<CR>"
  let lnum = line('.')
  if lnum != 1
    echoerr 'Forward wrap search failed: expected line 1, got ' . lnum
    cquit 1
  endif
catch
  echoerr 'Unexpected error during forward wrap search: ' . v:exception
  cquit 1
endtry

" 2) Backward search that wraps (from first line to last) under 'rightleft'.
try
  normal! gg0
  execute "normal! ?foo\<CR>"
  let lnum = line('.')
  if lnum != 3
    echoerr 'Backward wrap search failed: expected line 3, got ' . lnum
    cquit 1
  endif
catch
  echoerr 'Unexpected error during backward wrap search: ' . v:exception
  cquit 1
endtry

" 3) Not-found search message under 'rightleft' with a very long pattern.
" This stresses message reversing logic. We ignore the error, just ensure no crash.
try
  let @/ = repeat('x', 1000) . 'y'
  silent! normal! n
catch
  echoerr 'Unexpected error during long-pattern search: ' . v:exception
  cquit 1
endtry

" 4) Also trigger wrap message multiple times to cover both BOTTOM->TOP and TOP->BOTTOM paths again.
try
  " From last line search forward wraps to first.
  normal! G0
  silent! execute "normal! /bar\<CR>"
  " Now from first line search backward wraps to last.
  normal! gg0
  silent! execute "normal! ?bar\<CR>"
catch
  echoerr 'Unexpected error during repeated wrap searches: ' . v:exception
  cquit 1
endtry

qall!
