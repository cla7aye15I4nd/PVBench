" Test for popupmenu truncation guard (pum_redraw): ensure no crash when
" st_end == st by exercising very small 'pummaxwidth' values.

func! Omni_test(findstart, base)
  if a:findstart
    return col('.')
  endif
  return [
    \ #{word: 'foo', menu: 'fooMenu', kind: 'fooKind'},
    \ #{word: 'bar', menu: 'barMenu', kind: 'barKind'},
    \ #{word: 'baz', menu: 'bazMenu', kind: 'bazKind'},
    \ ]
endfunc

set omnifunc=Omni_test
" Make sure popupmenu is used consistently
set completeopt=menu,menuone

enew

" Try a range of pummaxwidth values, including extremely small ones to hit the
" corner case where nothing fits and ellipsis handling is triggered.
let widths = [20, 19, 18, 16, 15, 14, 12, 10, 5, 3, 2, 1]

for w in widths
  exe 'set pummaxwidth=' . w
  " Use Substitute line command to start Insert mode on a fresh line, then
  " trigger omni-completion and exit Insert mode. If a crash occurs, Vim would
  " terminate; if an error is thrown, catch it and fail the test.
  try
    execute "normal! S\<C-X>\<C-O>\<ESC>"
  catch
    echoerr 'Unexpected error with pummaxwidth=' . string(w) . ': ' . v:exception
    cquit 1
  endtry
endfor

" Also test with a very long menu/kind to stress truncation and ellipsis logic.
func! Omni_test_long(findstart, base)
  if a:findstart
    return col('.')
  endif
  let long = repeat('X', 200)
  return [
    \ #{word: 'w', menu: long, kind: long},
    \ #{word: 'x', menu: long, kind: long},
    \ ]
endfunc

set omnifunc=Omni_test_long

for w in [50, 30, 20, 10, 5, 3, 2, 1]
  exe 'set pummaxwidth=' . w
  try
    execute "normal! S\<C-X>\<C-O>\<ESC>"
  catch
    echoerr 'Unexpected error (long) with pummaxwidth=' . string(w) . ': ' . v:exception
    cquit 1
  endtry
endfor

qall!
