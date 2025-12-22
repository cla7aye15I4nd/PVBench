" Generated Vim test for user-defined completion cursor validation
" Verifies no crash and valid cursor after completion callbacks that
" misbehave (calling complete_add() in findstart, modifying text/cursor).

set nocompatible

" ---- Test 1: PoC scenario: complete_add() during findstart ----
new

func CompleteMisuse(findstart, base) abort
  if a:findstart
    let l:col = col('.')
    " Misuse: add candidate during findstart
    call complete_add('#')
    return l:col - 1
  else
    return []
  endif
endfunc

set completeopt=longest completefunc=CompleteMisuse

try
  " This used to cause a heap-buffer-overflow / crash.
  call feedkeys("ifoo#\<C-X>\<C-U>", "xt")
  " Ensure we return to Normal mode to make following checks deterministic
  call feedkeys("\<C-\\>\<C-N>", "xt")
catch
  " Any error is acceptable here; test focuses on no crash and cursor validity
endtry

" Validate cursor position is within current line bounds
if line('.') < 1 || line('.') > line('$')
  echoerr 'Test1: Cursor line out of range after completion'
  cquit 1
endif
if col('.') < 1 || col('.') > col('$') + 1
  echoerr 'Test1: Cursor column out of range after completion'
  cquit 1
endif

" Cleanup for Test 1
silent! delfunc CompleteMisuse
set completeopt& completefunc&
bwipe!

" ---- Test 2: Modify text and place cursor far beyond EOL during findstart ----
new
call setline(1, ['abcdef'])

func CompleteChangeCursor(findstart, base) abort
  if a:findstart
    " Shorten the current line drastically
    call setline('.', 'x')
    " Move cursor way past end of line to create an invalid position
    call cursor(line('.'), 1000)
    " Also misuse complete_add() here
    call complete_add('Y')
    return 1
  else
    return []
  endif
endfunc

set completeopt=longest completefunc=CompleteChangeCursor

try
  call feedkeys("iabcdef\<C-X>\<C-U>", "xt")
  call feedkeys("\<C-\\>\<C-N>", "xt")
catch
  " An error may be thrown (e.g. E840) due to text/cursor changes; that's fine.
endtry

" Validate cursor position is within current buffer bounds
if line('.') < 1 || line('.') > line('$')
  echoerr 'Test2: Cursor line out of range after completion'
  cquit 1
endif
if col('.') < 1 || col('.') > col('$') + 1
  echoerr 'Test2: Cursor column out of range after completion'
  cquit 1
endif

" Cleanup for Test 2
silent! delfunc CompleteChangeCursor
set completeopt& completefunc&
bwipe!

qall!
