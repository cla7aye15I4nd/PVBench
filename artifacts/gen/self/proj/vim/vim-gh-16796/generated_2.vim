" Test for heap buffer overflow when executing tag ex command with 'nostartofline'
" and cursor at (or beyond) end of line. The fix ensures both column and
" coladd are reset before executing the tag's ex command.

" Setup test files
call writefile(["!_TAG_FILE_ENCODING\tutf-8\t//",
      \ "f\tXfile\tascii"],
      \ 'Xtags')
call writefile(['f', 'foobar'], 'Xfile')

" Helper to run :tag f and capture output
function! s:RunTagFOutput() abort
  let l:out = ''
  redir => l:out
  try
    silent! tag f
  catch
    redir END
    echoerr 'Unexpected error during :tag f: ' . v:exception
    cquit 1
  endtry
  redir END
  return l:out
endfunction

" Test 1: With 'nostartofline' and cursor at last column on last line
set nostartofline
new Xfile
setlocal tags=Xtags
normal! G$
let out1 = s:RunTagFOutput()
if out1 !~# '0x66' && out1 !~# '\<102\>'
  echoerr 'Test1: Expected ASCII of "f" (0x66/102), got: ' . out1
  cquit 1
endif
bwipe!

" Test 2: With virtualedit allowing cursor beyond end of line (coladd > 0)
set virtualedit=all
set nostartofline
new Xfile
setlocal tags=Xtags
normal! G$5l
let out2 = s:RunTagFOutput()
if out2 !~# '0x66' && out2 !~# '\<102\>'
  echoerr 'Test2 (virtualedit): Expected ASCII of "f" (0x66/102), got: ' . out2
  cquit 1
endif
bwipe!

" Cleanup and reset options
set startofline&
set virtualedit&
call delete('Xtags')
call delete('Xfile')

qall!
