" Test for user-defined completion restoring cursor safely (patch adds check_cursor)
" Runs in Ex mode (-e -s)

let s:errors_before = len(v:errors)

func s:CheckCursorValid(ctx) abort
  let lnum = line('.')
  let coln = col('.')
  let eol = col('$')
  call assert_true(lnum >= 1, 'Cursor line invalid ' . a:ctx . ': ' . lnum)
  call assert_true(coln >= 1, 'Cursor column < 1 ' . a:ctx . ': ' . coln)
  call assert_true(coln <= eol, 'Cursor column > EOL ' . a:ctx . ': ' . coln . ' > ' . eol)
endfunc

" Test 1: Original PoC should no longer crash; may give E840 but cursor must be valid
new

func Complete(findstart, base) abort
  if a:findstart
    let coln = col('.')
    call complete_add('#')
    return coln - 1
  else
    return []
  endif
endfunc

set completeopt=longest completefunc=Complete
try
  " This used to cause a heap-buffer-overflow; now it should not crash
  call feedkeys("ifoo#\<C-X>\<C-U>", "xt")
catch /.*/
  " Accept errors (often E840) but continue to verify cursor validity
endtry
" Ensure we leave Insert mode and check cursor bounds
call feedkeys("\<Esc>", "xt")
call s:CheckCursorValid('after PoC sequence')

" Clean up
set completeopt& completefunc&
delfunc Complete
bwipe!

" Test 2: Edge case - completion function returns start position 0
" check_cursor() should clamp cursor position to a valid column
new

func Complete2(findstart, base) abort
  if a:findstart
    " Return an invalid start position deliberately
    call complete_add('x')
    return 0
  else
    return []
  endif
endfunc

set completeopt=longest completefunc=Complete2
" Trigger user completion at start of a new empty buffer/line
try
  call feedkeys("i\<C-X>\<C-U>", "xt")
catch /.*/
  " Ignore any error, only check that cursor is valid afterwards
endtry
" Leave Insert mode and validate cursor
call feedkeys("\<Esc>", "xt")
call s:CheckCursorValid('after return 0 start pos')

" Also ensure we can keep editing without errors
try
  call feedkeys("aZ", "xt")
  call feedkeys("\<Esc>", "xt")
catch /.*/
  call assert_true(0, 'Append failed after completion: ' . v:exception)
endtry
let line2 = getline('.')
call assert_match('Z$', line2)

" Clean up
set completeopt& completefunc&
delfunc Complete2
bwipe!

" Test 3: Long line boundary with invalid start pos 0
new
call setline(1, repeat('x', 1000))
call cursor(1, 1)

func Complete3(findstart, base) abort
  if a:findstart
    call complete_add('y')
    return 0
  else
    return []
  endif
endfunc

set completeopt=longest completefunc=Complete3
try
  call feedkeys("i\<C-X>\<C-U>", "xt")
catch /.*/
endtry
call feedkeys("\<Esc>", "xt")
call s:CheckCursorValid('after long line return 0')

" Clean up
set completeopt& completefunc&
delfunc Complete3
bwipe!

" Report any errors
if len(v:errors) > s:errors_before
  for s:err in v:errors[s:errors_before : ]
    echoerr s:err
  endfor
  cquit 1
endif

qall!
