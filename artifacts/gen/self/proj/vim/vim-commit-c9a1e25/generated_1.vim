" Generated test for heap buffer overflow fixes related to Visual mode state across :all,
" safe char access beyond end of line, and block prep start beyond line end.
" Runs in Ex mode. The test passes if no unexpected errors occur (i.e. no crash).

" Helper: finish with error
function! s:Fail(msg)
  echoerr a:msg
  cquit 1
endfunction

let s:save_ve = &virtualedit

" Test 1: Reproduce original PoC and verify no crash after :all and [P
try
  set virtualedit=all
  args Xa Xb
  all
  call setline(1, ['', '', ''])
  call cursor(3, 1)
  wincmd w
  call setline(1, 'foobar')
  " Go past end of line (via l after $ with virtualedit=all), start Visual and go to col 0
  silent! normal! $lv0
  " Running :all while Visual was active used to leave invalid VIsual/cursor state
  all
  call setreg('"', 'baz')
  " This used to cause a heap-buffer-overflow / crash
  try
    silent! normal! [P
  catch
    call s:Fail('Unexpected error after :all and [P: ' . v:exception)
  endtry
finally
  let &virtualedit = s:save_ve
  silent! bw! Xa Xb
endtry

" Test 2: Accessing character when cursor column is beyond line end should be safe
try
  set virtualedit=all
  new
  call setline(1, 'x')
  call cursor(1, 50)
  try
    " ga queries the character under (virtual) cursor; should not crash and should be NUL
    silent! normal! ga
  catch
    call s:Fail('ga at col>len crashed: ' . v:exception)
  endtry
  " Do not assert specific message content, just ensure no crash
finally
  let &virtualedit = s:save_ve
  silent! bwipe!
endtry

" Test 3: Visual charwise selection starting beyond line end and pasting should be safe
try
  set virtualedit=all
  new
  call setline(1, 'abc')
  call cursor(1, 999)
  " Start a charwise Visual selection back to column 0
  silent! normal! v0
  call setreg('"', 'ZZ')
  try
    silent! normal! [P
  catch
    call s:Fail('[P in Visual with startcol>len crashed: ' . v:exception)
  endtry
  " Basic sanity: buffer should remain a valid string line
  let l = getline(1)
  if type(l) != type('')
    call s:Fail('Unexpected line type after paste')
  endif
finally
  let &virtualedit = s:save_ve
  silent! bwipe!
endtry

qall!
