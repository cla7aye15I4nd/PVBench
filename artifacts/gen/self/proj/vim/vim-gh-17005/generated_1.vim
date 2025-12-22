" Test for popupmenu truncation with ellipsis when st_end == st (empty segment)
" This verifies no crash across various pummaxwidth values and with empty menu/kind.

set encoding=utf-8
set nomore

func! Omni_test(findstart, base)
  if a:findstart
    return col('.')
  endif
  return [
    \ #{word: 'foo',      menu: 'fooMenu',        kind: 'fooKind'},
    \ #{word: 'bar',      menu: '',               kind: 'barKind'},
    \ #{word: 'baz',      menu: 'bazMenu',        kind: ''},
    \ #{word: 'qux',      menu: '',               kind: ''},
    \ #{word: 'verylong', menu: repeat('M', 200), kind: 'K'},
    \ ]
endfunc

set omnifunc=Omni_test
set completeopt=menu,menuone,noselect

" Create a new buffer to run the tests
enew

" List of pummaxwidth values to exercise the ellipsis/truncation code paths,
" including the value from the original PoC (14) and very small/large values.
let widths = [20, 19, 18, 16, 15, 14, 12, 10, 1]

for w in widths
  exe 'set pummaxwidth=' . w
  try
    " Use S to start a fresh insert on a clean line each time, then trigger omni
    exe "normal! S\<C-X>\<C-O>\<ESC>"
  catch
    echoerr 'Unexpected error during omni completion at pummaxwidth=' . w . ': ' . v:exception
    cquit 1
  endtry
endfor

" Also exercise repeated calls to ensure stability when popupmenu is refreshed
" multiple times at the problematic width from the PoC.
exe 'set pummaxwidth=14'
for i in range(1, 5)
  try
    exe "normal! S\<C-X>\<C-O>\<ESC>"
  catch
    echoerr 'Unexpected error on repetition ' . i . ' at pummaxwidth=14: ' . v:exception
    cquit 1
  endtry
endfor

" If we reach here without errors or crashes, the fix works.
qall!
