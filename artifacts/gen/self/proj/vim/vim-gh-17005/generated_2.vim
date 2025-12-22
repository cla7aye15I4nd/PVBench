" Test for popup menu ellipsis handling when st_end == st (patch in popupmenu.c)
" The patch adds an extra condition to avoid operating on an empty range
" which previously could cause a crash for certain pummaxwidth values.

set nocompatible
set shortmess+=I
set noswapfile

" Basic omnifunc with short menu/kind entries
func! Omni_basic(findstart, base)
  if a:findstart
    return col('.')
  endif
  return [
    \ #{word: 'foo', menu: 'fooMenu', kind: 'fooKind'},
    \ #{word: 'bar', menu: 'barMenu', kind: 'barKind'},
    \ #{word: 'baz', menu: 'bazMenu', kind: 'bazKind'},
    \ ]
endfunc

" Omnifunc with empty menu/kind strings to exercise st_end == st cases
func! Omni_empty(findstart, base)
  if a:findstart
    return col('.')
  endif
  return [
    \ #{word: 'empty1', menu: '', kind: ''},
    \ #{word: 'empty2', menu: '', kind: ''},
    \ #{word: 'empty3', menu: '', kind: ''},
    \ ]
endfunc

" Omnifunc with long menu/kind to force truncation/ellipsis paths
func! Omni_long(findstart, base)
  if a:findstart
    return col('.')
  endif
  let l:longmenu = repeat('MenuX', 40)
  let l:longkind = repeat('KindY', 40)
  return [
    \ #{word: 'long1', menu: l:longmenu, kind: l:longkind},
    \ #{word: 'long2', menu: l:longmenu, kind: l:longkind},
    \ #{word: 'long3', menu: l:longmenu, kind: l:longkind},
    \ ]
endfunc

set completeopt=menuone

" Helper to invoke omni completion safely for a given width
func! DoComplete(width)
  execute 'set pummaxwidth=' . a:width
  try
    execute "normal! S\<C-X>\<C-O>\<ESC>"
  catch
    echoerr 'Unexpected error during completion at width=' . a:width . ': ' . v:exception
    cquit 1
  endtry
endfunc

" Start with a fresh buffer
enew

" 1) Exercise various widths with basic entries (regression for original PoC)
set omnifunc=Omni_basic
for w in [20, 19, 18, 16, 15, 14, 12, 10, 5, 4, 3, 2, 1]
  call DoComplete(w)
endfor

" 2) Exercise empty menu/kind entries to ensure no crash when there is nothing
"    between st and st_end (this targets the exact condition fixed in the patch)
set omnifunc=Omni_empty
for w in [20, 10, 5, 3, 2, 1]
  call DoComplete(w)
endfor

" 3) Exercise very long menu/kind entries to force truncation/ellipsis logic
set omnifunc=Omni_long
for w in [50, 30, 20, 15, 12, 10, 8, 5, 3, 2, 1]
  call DoComplete(w)
endfor

" If we reached here without an error or crash, consider the test passed.
echo 'OK: popup menu ellipsis handling does not crash for tested cases'
qall!
