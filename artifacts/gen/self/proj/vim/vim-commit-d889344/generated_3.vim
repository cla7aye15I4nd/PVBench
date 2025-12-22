" Test for IObuff overrun in append_command() when reporting invalid commands (E492)
" The patch ensures we don't write past IObuff and avoid splitting multibyte chars.

set nocompatible
silent! try
  language messages C
catch
endtry
if exists('&encoding')
  set encoding=utf-8
endif

let g:failures = []

function! Expect_E492(cmdstr, label) abort
  let caught = 0
  try
    execute a:cmdstr
  catch /E492:/
    let caught = 1
  catch
    call add(g:failures, a:label . ': unexpected exception: ' . v:exception)
  endtry
  if !caught
    call add(g:failures, a:label . ': did not catch E492')
  endif
endfunction

" 1) Original PoC: used to go over the end of IObuff when reporting the error
call Expect_E492(repeat('0', 987) .. "0\xdd\x80\xdd\x80\xdd\x80\xdd\x80", 'poc_overflow_dd80')

" 2) Very long command: should be truncated safely without crash
call Expect_E492(repeat('x', 10000), 'very_long_command')

" 3) Include non-breaking space bytes; tests both UTF-8 (C2 A0) and single A0
call Expect_E492(repeat('x', 5000) .. "\xc2\xa0" .. repeat('x', 200) .. "\xa0" .. repeat('x', 200), 'nbsp_handling_long')

" 4) Multibyte UTF-8 char (emoji, 4 bytes) near/over buffer boundary
call Expect_E492(repeat('x', 5000) .. "\xf0\x9f\x98\x80" .. repeat('y', 500), 'utf8_emoji_boundary')

" 5) Two-byte UTF-8 char near/over boundary
call Expect_E492(repeat('x', 5000) .. "\xc3\xa9" .. repeat('z', 500), 'utf8_2byte_boundary')

if len(g:failures) > 0
  for msg in g:failures
    echoerr msg
  endfor
  cquit 1
endif

qall!
