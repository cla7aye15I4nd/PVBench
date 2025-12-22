" Test for patch 9.1.1406: avoid freeing first tuple item twice (crash with invalid import/tuple)

" The following used to crash Vim. Now it should fail with a proper error.

" Case 1: Original PoC line
new
call setline(1, ['imp(",G0}11*f[+\x","#|'])
let s:caught = 0
try
  %source
  " If no error, that's a failure
  echoerr 'Expected an error when sourcing invalid line (case 1)'
  cquit 1
catch /.*/
  let s:caught = 1
  " Accept either in v:exception or v:errmsg
  if v:exception !~# 'E114: Missing double quote: "#|' && v:errmsg !~# 'E114: Missing double quote: "#|'
    echoerr 'Unexpected error (case 1): ' . v:exception . ' errmsg=' . v:errmsg
    cquit 1
  endif
endtry
if !s:caught
  echoerr 'Expected an error, but none was thrown (case 1)'
  cquit 1
endif
bwipe!

" Case 2: Variant with a CTRL-] (0x1D) character as in reference
new
let s = 'imp(",G0}11*f' . nr2char(29) . '[+\x","#|'
call setline(1, [s])
let s:caught = 0
try
  %source
  echoerr 'Expected an error when sourcing invalid line (case 2)'
  cquit 1
catch /.*/
  let s:caught = 1
  if v:exception !~# 'E114: Missing double quote: "#|' && v:errmsg !~# 'E114: Missing double quote: "#|'
    echoerr 'Unexpected error (case 2): ' . v:exception . ' errmsg=' . v:errmsg
    cquit 1
  endif
endtry
if !s:caught
  echoerr 'Expected an error, but none was thrown (case 2)'
  cquit 1
endif
bwipe!

qall!
