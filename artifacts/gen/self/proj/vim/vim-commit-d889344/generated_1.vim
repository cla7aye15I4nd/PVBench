" Test for IObuff overflow when appending command in error messages (patch 4895)
" Run with: vim -e -s -N -u NONE -S generated.vim

set nocompatible
set encoding=utf-8
silent! set nomore

let s:fails = []

function! s:Fail(msg)
  call add(s:fails, a:msg)
endfunction

" Test 1: Original PoC should not crash and should raise E492
let caught = 'no'
let err = ''
try
  exe repeat('0', 987) . "0\xdd\x80\xdd\x80\xdd\x80\xdd\x80"
catch /E492:/
  let caught = 'yes'
  let err = v:exception
catch
  call s:Fail('Test1: Unexpected exception: ' . v:exception)
endtry
if caught != 'yes'
  call s:Fail('Test1: Expected to catch E492 for long/invalid multibyte command')
endif
if type(err) == type('') && err !~ 'E492:'
  call s:Fail('Test1: Exception does not mention E492: ' . string(err))
endif

" Test 2: NBSP should be shown as <a0> in the error message and not as raw NBSP
let caught = 'no'
let err = ''
let nbsp = nr2char(0xa0)
try
  exe nbsp
catch /E492:/
  let caught = 'yes'
  let err = v:exception
catch
  call s:Fail('Test2: Unexpected exception: ' . v:exception)
endtry
if caught != 'yes'
  call s:Fail('Test2: Expected to catch E492 for NBSP command')
endif
if type(err) == type('')
  if match(err, '<a0>') < 0
    call s:Fail('Test2: NBSP not rendered as <a0>: ' . string(err))
  endif
  if stridx(err, nbsp) >= 0
    call s:Fail('Test2: Error still contains raw NBSP instead of <a0>: ' . string(err))
  endif
endif

" Test 3: Very long UTF-8 multibyte command (emoji) should not crash and should raise E492
let caught = 'no'
let err = ''
let face = nr2char(0x1f600)
let s = repeat(face, 500)
try
  exe s
catch /E492:/
  let caught = 'yes'
  let err = v:exception
catch
  call s:Fail('Test3: Unexpected exception: ' . v:exception)
endtry
if caught != 'yes'
  call s:Fail('Test3: Expected to catch E492 for very long UTF-8 command')
endif
if type(err) == type('') && err !~ 'E492:'
  call s:Fail('Test3: Exception does not mention E492: ' . string(err))
endif

" Test 4: Long command near buffer limit with NBSP inside should not crash and still raise E492
let caught = 'no'
let err = ''
try
  exe repeat('x', 20000) . nbsp . 'x'
catch /E492:/
  let caught = 'yes'
  let err = v:exception
catch
  call s:Fail('Test4: Unexpected exception: ' . v:exception)
endtry
if caught != 'yes'
  call s:Fail('Test4: Expected to catch E492 for long command with NBSP near buffer limits')
endif
if type(err) == type('') && err !~ 'E492:'
  call s:Fail('Test4: Exception does not mention E492: ' . string(err))
endif

" Test 5: Long command near buffer limit with multi-byte char should not crash and still raise E492
let caught = 'no'
let err = ''
try
  exe repeat('x', 20000) . face . 'x'
catch /E492:/
  let caught = 'yes'
  let err = v:exception
catch
  call s:Fail('Test5: Unexpected exception: ' . v:exception)
endtry
if caught != 'yes'
  call s:Fail('Test5: Expected to catch E492 for long command with multibyte char near buffer limits')
endif
if type(err) == type('') && err !~ 'E492:'
  call s:Fail('Test5: Exception does not mention E492: ' . string(err))
endif

if len(s:fails) > 0
  for m in s:fails
    echoerr m
  endfor
  cquit 1
endif
qall!
