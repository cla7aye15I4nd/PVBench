" Verify xxd colored output no buffer overflow and correct formatting
set nomore

function! s:Fail(msg)
  echoerr a:msg
  cquit 1
endfunction

" Find xxd executable
let s:xxd_cmd = 'xxd'
if !executable(s:xxd_cmd)
  " Try relative path from Vim runtime if available
  if exists('*exepath')
    let s:xxd_cmd = exepath('xxd')
  endif
endif
if !executable(s:xxd_cmd)
  echo "SKIP: xxd executable not found"
  qall!
endif

" Prepare 256 bytes of 'A' without newline
let infile = 'Xinput_xxd_overflow.bin'
call writefile([repeat('A', 256)], infile, 'b')

" Run xxd with options that used to trigger a buffer overflow when writing
" colored output to a buffer. We capture the output directly.
let cmd = s:xxd_cmd . ' -Ralways -g1 -c256 -d -o 9223372036854775808 ' . fnameescape(infile)
let out = systemlist(cmd)
if v:shell_error != 0
  call s:Fail('xxd failed with exit code ' . v:shell_error)
endif

if len(out) != 1
  call s:Fail('Unexpected number of output lines from xxd: ' . len(out))
endif
let line = out[0]

" Strip ANSI color escape sequences: ESC [ ... m
let line_nocol = substitute(line, '\%x1b\[[0-9;]\+m', '', 'g')

" 1) Verify ASCII column contains exactly 256 'A' characters at the end
let L = strlen(line_nocol)
if L < 256
  call s:Fail('Output line too short: ' . L)
endif
let ascii_tail = strpart(line_nocol, L - 256)
if ascii_tail != repeat('A', 256)
  call s:Fail('ASCII column mismatch at end of line')
endif

" 2) Verify there are exactly 256 hex byte tokens "41 " in the hex area
let count_41sp = len(split(line_nocol, '41 ', 1)) - 1
if count_41sp != 256
  call s:Fail('Expected 256 occurrences of "41 ", got ' . count_41sp)
endif

" 3) Basic sanity: address and separator present (colon and two spaces before ASCII)
if match(line_nocol, ': ') < 0
  call s:Fail('Missing address separator ": " in output')
endif

" Clean up
call delete(infile)

qall!
