" Test for heap-buffer-overflow when jumping to a tag with 'nostartofline'
" The fix resets cursor column and coladd before executing the tag's ex command.

" Setup test files
call writefile(["!_TAG_FILE_ENCODING\tutf-8\t//",
      \ "f\tXfile\tascii"],
      \ 'Xtags')
call writefile(['f', 'foobar'], 'Xfile')

set nomore
set nostartofline

" Test 1: Basic reproduction without virtualedit - ensure no crash and cursor reset
new Xfile
setlocal tags=Xtags
normal! G$

" Sanity check position before tag
if line('.') != 2
  echoerr 'Pre-check: expected to be on line 2 before tag, got ' . line('.')
  cquit 1
endif

let pre_pos = getcurpos()
if col('.') < 1
  echoerr 'Pre-check: invalid column before tag: ' . col('.')
  cquit 1
endif

try
  " This used to crash; with fix it should not. Also suppress error from invalid excmd.
  silent! tag f
catch
  echoerr 'Unexpected error during tag jump (no VE): ' . v:exception
  cquit 1
endtry

let pos = getcurpos()
if pos[1] != 1
  echoerr 'After tag (no VE): expected line 1, got ' . pos[1]
  cquit 1
endif
if col('.') != 1
  echoerr 'After tag (no VE): expected column 1, got ' . col('.')
  cquit 1
endif
if pos[3] != 0
  echoerr 'After tag (no VE): expected coladd 0, got ' . pos[3]
  cquit 1
endif

bwipe!

" Test 2: With virtualedit to ensure coladd is reset too
set ve=all
new Xfile
setlocal tags=Xtags
normal! G$
" Move far past end-of-line to create a non-zero coladd
normal! 50l

let ve_pre = getcurpos()
if ve_pre[3] == 0
  echoerr 'Pre-check (VE): expected coladd > 0 before tag, got 0'
  cquit 1
endif

try
  silent! tag f
catch
  echoerr 'Unexpected error during tag jump (with VE): ' . v:exception
  cquit 1
endtry

let ve_pos = getcurpos()
if ve_pos[1] != 1
  echoerr 'After tag (VE): expected line 1, got ' . ve_pos[1]
  cquit 1
endif
if col('.') != 1
  echoerr 'After tag (VE): expected column 1, got ' . col('.')
  cquit 1
endif
if ve_pos[3] != 0
  echoerr 'After tag (VE): expected coladd 0, got ' . ve_pos[3]
  cquit 1
endif

bwipe!

" Reset options and cleanup
set ve&
set startofline&
call delete('Xfile')
call delete('Xtags')

qall!
