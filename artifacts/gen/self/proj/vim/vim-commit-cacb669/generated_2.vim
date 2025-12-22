" Test for patch that fixes reversed-text handling in do_search()
" Specifically, ensure that very long not-found search patterns with many
" trailing spaces under 'rightleft' do not crash and properly set E486.

set nocompatible
set nomore
set shortmess=
set nohlsearch

" Prepare a simple buffer
enew!
call setline(1, ['foo here', 'middle', 'end'])
normal! gg

" Enable right-to-left to exercise reverse_text path in message handling
set rightleft
set wrapscan

function! DoFailSearch(pat) abort
  let v:errmsg = ''
  let @/ = a:pat
  " Use 'n' to repeat the search for @/; it will try and fail, producing E486
  silent! normal! n
  if v:errmsg !~# 'E486:'
    echoerr 'Expected E486 for failing search, got: ' . v:errmsg
    cquit 1
  endif
endfunction

" 1) Long pattern with many trailing spaces
call DoFailSearch(repeat('X', 32) . repeat(' ', 2000))

" 2) Even longer pattern and more trailing spaces to stress the message buffer
call DoFailSearch(repeat('Y', 128) . repeat(' ', 4000))

" 3) Extra-long to further stress reversed-text shifting logic
call DoFailSearch(repeat('Z', 256) . repeat(' ', 8000))

" Also confirm that a successful search still works (sanity check)
let v:errmsg = ''
let @/ = 'foo'
silent! normal! n
if v:errmsg != ''
  echoerr 'Unexpected error during successful search: ' . v:errmsg
  cquit 1
endif
if getline('.') !~# 'foo'
  echoerr 'Expected to be on a line containing "foo" after search, got line ' . line('.')
  cquit 1
endif

qall!
