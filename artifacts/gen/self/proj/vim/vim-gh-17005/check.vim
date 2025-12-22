func! Omni_test(findstart, base)
  if a:findstart
    return col(".")
  endif
  return [
    \ #{word: "foo", menu: "fooMenu", kind: "fooKind"},
    \ #{word: "bar", menu: "barMenu", kind: "barKind"},
    \ #{word: "baz", menu: "bazMenu", kind: "bazKind"},
    \ ]
endfunc

set omnifunc=Omni_test

enew

" Test with pummaxwidth=20
set pummaxwidth=20
execute "normal! S\<C-X>\<C-O>\<ESC>"

" Test with pummaxwidth=19
set pummaxwidth=19
execute "normal! S\<C-X>\<C-O>\<ESC>"

" Test with pummaxwidth=18 (display Ellipsis)
set pummaxwidth=18
execute "normal! S\<C-X>\<C-O>\<ESC>"

" Test with pummaxwidth=16 (display Ellipsis)
set pummaxwidth=16
execute "normal! S\<C-X>\<C-O>\<ESC>"

" Test with pummaxwidth=15
set pummaxwidth=15
execute "normal! S\<C-X>\<C-O>\<ESC>"

" Test with pummaxwidth=12
set pummaxwidth=12
execute "normal! S\<C-X>\<C-O>\<ESC>"

" Test with pummaxwidth=10 (display Ellipsis)
set pummaxwidth=10
execute "normal! S\<C-X>\<C-O>\<ESC>"

" Test with pummaxwidth=1
set pummaxwidth=1
execute "normal! S\<C-X>\<C-O>\<ESC>"

qall!
