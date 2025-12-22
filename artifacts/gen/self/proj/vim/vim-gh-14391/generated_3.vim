" Test for user-defined completion cursor restoration validity (patch adds check_cursor())
" Runs in Ex mode

" Helper: validate cursor is within buffer bounds
func! s:CheckCursorValid(context) abort
  let pos = getpos('.')
  let lnum = pos[1]
  let coln = pos[2]
  let last = line('$')
  if lnum < 1 || lnum > last
    echoerr a:context . ': Cursor lnum out of range: ' . lnum . ' (lines: ' . last . ')'
    cquit 1
  endif
  let line_text = getline(lnum)
  let maxcol = len(line_text) + 1
  if coln < 1 || coln > maxcol
    echoerr a:context . ': Cursor col out of range: ' . coln . ' (max: ' . maxcol . ')'
    cquit 1
  endif
endfunc

" === Scenario 1: Original PoC - complete_add() called during findstart ===
new

func Complete_PoC(findstart, base) abort
  if a:findstart
    let col = col('.')
    call complete_add('#')
    return col - 1
  else
    return []
  endif
endfunc

set completeopt=longest completefunc=Complete_PoC

" This used to crash (heap-buffer-overflow). After the fix it should not crash;
" it may raise an error (e.g. E840), which is acceptable. Ensure Vim continues
" and the cursor position is valid afterwards.
try
  call feedkeys("ifoo#\<C-X>\<C-U>", "xt")
catch
  " Any error is acceptable here; the key point is: no crash.
endtry

call <SID>CheckCursorValid('Scenario 1')

" Cleanup for scenario 1
silent! delfunc Complete_PoC
set completeopt& completefunc&
bwipe!


" === Scenario 2: Make saved cursor position invalid by deleting lines in findstart ===
new
call setline(1, ['alpha', 'beta', 'gamma'])
call cursor(2, 1)

func Complete_DeleteLines(findstart, base) abort
  if a:findstart
    let c = col('.')
    " Try to make the original saved cursor position invalid by changing text.
    " This may cause an error (E523) due to textlock; that's fine for this test.
    try
      call deletebufline('', 1, '$')
    catch
      " ignore errors from text changes during completion setup
    endtry
    return c - 1
  else
    return []
  endif
endfunc

set completeopt=menuone,preview completefunc=Complete_DeleteLines

try
  call feedkeys("iZZZ\<C-X>\<C-U>", "xt")
catch
  " Errors are acceptable; ensure no crash and cursor is sane afterwards
endtry

call <SID>CheckCursorValid('Scenario 2')

" Cleanup for scenario 2
silent! delfunc Complete_DeleteLines
set completeopt& completefunc&
bwipe!

qall!
