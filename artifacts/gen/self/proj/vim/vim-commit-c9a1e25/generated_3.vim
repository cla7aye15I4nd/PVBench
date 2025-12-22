" Comprehensive test for Visual mode invalid position and out-of-bounds access
" Ensures fix for: resetting Visual mode on :all and bounds checks in gchar_pos()
" and charwise_block_prep() when operating beyond end of line with virtualedit=all.

set nocp
set hidden
set virtualedit=all

" Prepare two argument buffers
args Xa Xb
all

" Buffer Xa: create three empty lines and set cursor on line 3
execute 'buffer Xa'
call setline(1, ['', '', ''])
call cursor(3, 1)

" Buffer Xb: single line with text
execute 'buffer Xb'
call setline(1, 'foobar')

" Create a Visual selection that extends beyond end-of-line
normal! gg$lv0

" Trigger :all (used to leave stale Visual state and cause heap OOB)
all

" Visual mode should be reset after :all
if mode() =~# 'v'
  echoerr 'FAIL: Visual mode not reset by :all'
  cquit 1
endif

" Put before in Xb; used to crash or read OOB
call setreg('"', 'baz')
execute 'buffer Xb'
call cursor(1, 1)
try
  normal! [P
catch
  echoerr 'FAIL: Unexpected error during [P after :all: ' . v:exception
  cquit 1
endtry

let line = getline(1)
if line !=# 'bazfoobar'
  echoerr 'FAIL: Unexpected content after [P post-:all. Got: ' . string(line)
  cquit 1
endif

" Now test putting while Visual selection is active and extends past EOL
" This exercises charwise_block_prep() bounds logic.
call setline(1, 'foobar')
normal! gg$lv0
call setreg('"', 'baz')
try
  normal! [P
catch
  echoerr 'FAIL: Unexpected error during [P with active Visual selection: ' . v:exception
  cquit 1
endtry
let line2 = getline(1)
" Replacing a full-line Visual charwise selection with a charwise register should yield only the register text.
if line2 !=# 'baz'
  echoerr 'FAIL: Unexpected content after Visual [P. Got: ' . string(line2)
  cquit 1
endif

" Test for gchar_pos() bound check via the :normal ga command when cursor is beyond EOL.
" Expect reporting NUL instead of crashing or reading garbage.
execute 'buffer Xa'
call cursor(3, 100)
let msg = ''
redir => msg
" Use :silent! to avoid interfering with test output while still capturing via :redir
silent! normal! ga
redir END
if msg ==# ''
  echoerr 'FAIL: ga produced no output when cursor beyond EOL'
  cquit 1
endif
if match(msg, 'NUL') < 0 && match(msg, 'Hex 00') < 0 && match(msg, '0x00') < 0
  echo "ga output: " . msg
  echoerr 'FAIL: ga did not report NUL when cursor beyond EOL'
  cquit 1
endif

" Cleanup
set virtualedit=
bw! Xa Xb
qall!
