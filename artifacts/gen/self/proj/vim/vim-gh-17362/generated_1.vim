" Test for tuple evaluation fix: ensure no crash and proper E114 error is reported
" The test runs in Ex mode (-e -s) and does not rely on the runtime.

" Helper: write a one-line script to a temp file, source it, and verify
" that it fails with E114 and that the message mentions the unterminated
" string starting with "#|. This exercises tuple argument evaluation where
" the first item is already evaluated and appended, and parsing fails while
" reading the next string.
func RunCase(line)
  let fname = tempname()
  call writefile([a:line], fname)
  try
    exe 'source' fnameescape(fname)
    echoerr 'Expected E114: Missing double quote error, but :source succeeded'
    call delete(fname)
    cquit 1
  catch
    let s = v:exception
    if s !~# 'E114:'
      echoerr 'Unexpected error (not E114): ' . s
      call delete(fname)
      cquit 1
    endif
    if s !~# 'Missing double quote'
      echoerr 'Unexpected E114 message: ' . s
      call delete(fname)
      cquit 1
    endif
    if s !~# '"#\|'
      echoerr 'Error text does not reference "#|: ' . s
      call delete(fname)
      cquit 1
    endif
  endtry
  call delete(fname)
endfunc

" 1) Minimal PoC: first tuple item is a valid string, second is an unterminated
" string starting with "#|. Parsing must stop with E114 and not crash.
call RunCase('echo imp("", "#|')

" 2) Use a builtin call where the first tuple item is evaluated and stored,
" then parsing of the second item fails. This checks that the first item is
" not freed twice (fix sets rettv->v_type = VAR_UNKNOWN after appending).
call RunCase('echo printf(["x"][0], "#|')

" 3) Stress with a larger allocated first argument to further exercise memory
" management for the first tuple item.
call RunCase('echo printf(repeat("a", 1000), "#|')

" 4) Repeat a case multiple times to ensure no use-after-free or double-free
" across repeated failures.
for i in range(1, 3)
  call RunCase('echo printf(["x"][0], "#|')
endfor

" Sanity check: make sure the interpreter still functions after the errors
let x = 1 + 2
if x != 3
  echoerr 'Interpreter state corrupted after error handling'
  cquit 1
endif

qall!
