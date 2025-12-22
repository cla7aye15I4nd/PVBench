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
set pummaxwidth=14

enew
execute "normal! i\<C-X>\<C-O>"
qall!