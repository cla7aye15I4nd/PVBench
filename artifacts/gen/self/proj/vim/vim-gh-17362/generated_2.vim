" Test for the tuple evaluation double-free fixed in patch 1406.
" The bug was that after appending the first evaluated item to a tuple,
" the caller could free it again, causing a crash. The fix sets rettv->v_type
" to VAR_UNKNOWN after appending, so the caller won't free it.
"
" This test ensures that sourcing a crafted line which previously crashed
" now reliably fails with the expected parse error (E114) and does not crash,
" even when executed multiple times and with slight input variations.

set nocp
set shortmess+=I

func s:RunOne(line)
  let fname = tempname()
  " Write the single problematic line to a temporary script file (binary to
  " preserve any control bytes exactly)
  call writefile([a:line], fname, 'b')

  " Sourcing this file used to crash; now it should fail with a missing double
  " quote error (E114). Run it twice to catch any lifetime/double-free issues.
  for i in range(2)
    let l:got_err = 0
    let l:exc = ''
    try
      execute 'source ' . fnameescape(fname)
    catch
      let l:got_err = 1
      let l:exc = v:exception
    endtry

    if !l:got_err
      echoerr 'Expected failure (E114) but sourcing succeeded on iteration ' . (i + 1)
      echoerr 'Line: ' . a:line
      call delete(fname)
      cquit 1
    endif
    if match(l:exc, 'E114:') < 0
      echoerr 'Unexpected error when sourcing (expected E114): ' . l:exc
      echoerr 'Line: ' . a:line
      call delete(fname)
      cquit 1
    endif
  endfor

  call delete(fname)
endfunc

" Original PoC line
let l1 = 'imp(",G0}11*f[+\x","#|'
call s:RunOne(l1)

" Variant with a control character 0x1D (as in some reproductions), to exercise
" a nearby parsing path while still relying on tuple evaluation and the missing
" double quote error.
let l2 = 'imp(",G0}11*f' . nr2char(0x1d) . '[+\x","#|'
call s:RunOne(l2)

" Repeat the first case multiple times to further ensure no use-after-free when
" the same script is sourced repeatedly in the same process.
for _ in range(3)
  call s:RunOne(l1)
endfor

qall!
