" Generated Vimscript test for append_command IObuff handling and NBSP display (patch 4895)
" Run with: vim -e -s -N -u NONE -S generated.vim

" Use UTF-8 when available to exercise multibyte paths
if has('multi_byte')
  set encoding=utf-8
endif

" Helper: execute a command string and verify E492 is reported, optionally
" checking for additional patterns in v:errmsg.
function! s:CheckExeErr(cmdstr, expect_pats) abort
  let v:errmsg = ''
  silent! execute a:cmdstr
  if v:errmsg !~# 'E492:'
    echoerr 'Expected E492 for: ' . string(a:cmdstr) . ' but got: ' . v:errmsg
    cquit 1
  endif
  for pat in a:expect_pats
    if type(pat) == type('') && pat !=# '' && v:errmsg !~ pat
      echoerr 'Missing pattern ' . string(pat) . ' in v:errmsg: ' . v:errmsg
      cquit 1
    endif
  endfor
endfunction

" 1) Original PoC: previously could write past end of IObuff when reporting the error
call s:CheckExeErr(repeat('0', 987) .. "0\xdd\x80\xdd\x80\xdd\x80\xdd\x80", [])

" 2) NBSP should be displayed as <a0> in the error message (regardless of encoding)
let s:nbsp = nr2char(0xa0)
call s:CheckExeErr('foo' .. s:nbsp .. 'bar', ['<a0>'])

" 3) Many NBSP characters: still safe and at least one <a0> should appear
call s:CheckExeErr('x' .. repeat(s:nbsp, 100) .. 'y', ['<a0>'])

" 4) Very long ASCII command: should not crash and must report E492
call s:CheckExeErr(repeat('A', 5000), [])

" 5) Multibyte-related edge cases (only when supported)
if has('multi_byte')
  " Trailing multibyte character near end: must not overflow or crash
  let s:e_acute = nr2char(0x00E9)
  call s:CheckExeErr(repeat('x', 2000) .. s:e_acute, [])

  " Many combining marks: should not overflow/crash while appending command
  let s:comb = nr2char(0x0301)  " COMBINING ACUTE ACCENT
  call s:CheckExeErr('a' .. repeat(s:comb, 80), [])

  " Long command mixing ASCII and multibyte; ensures boundary logic handles MB len
  call s:CheckExeErr(repeat('MB', 1500) .. s:nbsp .. s:e_acute .. repeat(s:comb, 10), ['<a0>'])
endif

qall!
