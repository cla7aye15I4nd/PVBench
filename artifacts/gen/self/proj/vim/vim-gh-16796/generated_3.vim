" Test for heap buffer overflow in tag jumping with 'nostartofline'
" The fix resets both cursor column and coladd before executing the tag's Ex command.
" We verify:
"  - No crash when executing a tag whose Ex command is :ascii while cursor is at EOL
"  - Cursor column is reset to 1 and coladd to 0 before executing the Ex command
"  - Same behavior when cursor is in virtual columns past EOL (coladd > 0)

" Prepare test files
call writefile(["!_TAG_FILE_ENCODING\tutf-8\t//",
      \ "f\tXfile\tascii"],
      \ 'Xtags')
call writefile(['f', 'foobar'], 'Xfile')

" Helper: assert equal with message
func s:AssertEqual(actual, expected, msg)
  if a:actual != a:expected
    echoerr a:msg . ' Expected: ' . string(a:expected) . ', got: ' . string(a:actual)
    cquit 1
  endif
endfunc

" ---------- Test 1: nostartofline with cursor at end-of-line ----------
set nostartofline
new Xfile
setlocal tags=Xtags
normal! G$

try
  " This used to cause a heap-buffer-overflow; reaching here means no crash
  tag f
catch
  echoerr 'Unexpected error during tag jump (EOL case): ' . v:exception
  cquit 1
endtry

" Verify we are in the right buffer and at start of line with no coladd
call s:AssertEqual(expand('%:t'), 'Xfile', 'Wrong buffer after tag jump (EOL case).')
call s:AssertEqual(line('.'), 1, 'Cursor line not reset to 1 before executing Ex cmd (EOL case).')
call s:AssertEqual(col('.'), 1, 'Cursor column not reset to 1 before executing Ex cmd (EOL case).')
let pos = getcurpos()
call s:AssertEqual(pos[3], 0, 'coladd not reset to 0 before executing Ex cmd (EOL case).')

" Clean up window before next subtest
bwipe!
set startofline&

" ---------- Test 2: nostartofline with virtual edit placing cursor past EOL ----------
set nostartofline
set virtualedit=all
new Xfile
setlocal tags=Xtags
normal! G$10l
let pos2 = getcurpos()
if pos2[3] <= 0
  echoerr 'Failed to place cursor in virtual columns past EOL; setup issue.'
  cquit 1
endif

try
  tag f
catch
  echoerr 'Unexpected error during tag jump (virtual columns case): ' . v:exception
  cquit 1
endtry

" Verify cursor reset and coladd cleared
call s:AssertEqual(expand('%:t'), 'Xfile', 'Wrong buffer after tag jump (virtual columns case).')
call s:AssertEqual(line('.'), 1, 'Cursor line not reset to 1 before executing Ex cmd (virtual columns case).')
call s:AssertEqual(col('.'), 1, 'Cursor column not reset to 1 before executing Ex cmd (virtual columns case).')
let pos3 = getcurpos()
call s:AssertEqual(pos3[3], 0, 'coladd not reset to 0 before executing Ex cmd (virtual columns case).')

" Reset options and cleanup test files
set virtualedit&
set startofline&
call delete('Xtags')
call delete('Xfile')

qall!
